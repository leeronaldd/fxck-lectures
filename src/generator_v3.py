"""Generator V3: Slide-driven architecture.

Slides drive the structure, transcript fills the gaps.

V2 was transcript-driven: chunk transcript → generate slides + transcript per chunk.
That created fragile chunking, bad depth allocation, and repetition across parallel
writers who independently covered the same concepts.

V3 flips it:
  1. Flash sees ALL slide descriptions + full transcript → groups slides by topic,
     writes a teaching plan for the whole lecture in one pass.
  2. Pro executes each group: receives slides + relevant transcript + textbook +
     teaching plan → writes the slide doc + transcript.

The Flash teaching plan IS the depth allocation. One planning call replaces the
chunker, EI scorer, depth nudge, bridge framing, and concept coordinator from V2.

What stays from V2:
  - Creative brief (system instruction) — identical
  - Textbook search — identical
  - Context caching — identical
  - Output parser — identical
  - Assembly + frontend format — identical
"""

import os
import re
import sys
import time
import json
from pathlib import Path
from dataclasses import dataclass, field

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import GCP_PROJECT_ID, GCP_LOCATION, GENERATOR_MODEL, CHUNKER_FALLBACK_MODEL, GCS_SCREENSHOTS_BUCKET

# Import shared components from V2
from src.generator_v2 import (
    build_system_instruction_text,
    build_creative_brief_image_parts,
    get_or_create_cache,
    clear_cache,
    parse_output,
    GeneratedSection,
    SlideCard,
    assemble_slide_doc,
    assemble_transcript_doc,
    assemble_api_response,
    fetch_textbook_section,
    fetch_textbook_images,
    _is_housekeeping,
)


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SlideGroup:
    """A topic group of slides with a teaching plan."""
    group_index: int                    # Sequential position in final document (0-based)
    title: str                          # e.g. "Baltimore Classification"
    slide_indices: list[int]            # indices into screenshots.json
    teaching_plan: str                  # Flash's teaching notes for Pro
    depth: str                          # "deep", "standard", "bridge", "skip"
    word_estimate: int = 300            # Flash's estimate of output length
    transcript_excerpt: str = ""        # Matched transcript for this group
    ei_estimate: int = 50               # Exam importance
    key_terms: list[str] = field(default_factory=list)
    new_terms: list[str] = field(default_factory=list)
    prior_terms: list[str] = field(default_factory=list)
    visual_strategy: str = ""              # "professor_slide", "openstax_figure", "structured_card"
    visual_data: dict = field(default_factory=dict)  # strategy-specific payload
    original_group_index: int = -1      # Original index in all_groups (for textbook lookup)


# ═══════════════════════════════════════════════════════════════════════════
# Multi-agent planning — 4 focused agents instead of 1 overloaded call
#
# Agent 1: Slide Grouper (Flash, text-only) — group slides by topic
# Agent 2: Transcript Scanner (Flash) — match transcript to groups + find gaps
# Coordinator: Pro — strategic decisions, ownership, depth allocation
# Agent 3: Teaching Planner (Flash + images) — pedagogical approach per group
#
# All agents write to a shared NOTEBOOK (Python dict). Each agent understands
# its role in the system and what happens if it fails.
# ═══════════════════════════════════════════════════════════════════════════


def plan_lecture(
    client,
    screenshots: list[dict],
    transcript: str,
    slide_image_parts: list | None = None,
) -> list[SlideGroup]:
    """Multi-agent planning: group slides → scan transcript → coordinate → plan.

    Four focused agents replace the single overloaded Flash call. Each agent
    has one job, understands the system it's part of, and writes to a shared
    notebook that accumulates intelligence for the Pro coordinator.

    Returns:
        Ordered list of SlideGroup objects ready for Pro generation.
    """
    from google.genai import types

    debug_dir = Path("data/output")
    debug_dir.mkdir(parents=True, exist_ok=True)

    # ── Identify non-blank slides ──
    non_blank = set()
    blank_indices = set()
    for i, s in enumerate(screenshots):
        desc = s.get("description", "").lower()
        if "blank" in desc or "no visible" in desc or "solid black" in desc:
            blank_indices.add(i)
        else:
            non_blank.add(i)

    # ═══════════════════════════════════════════════════
    # Agent 1: Slide Grouper (Flash, text-only)
    # ═══════════════════════════════════════════════════
    t0 = time.time()

    if non_blank:
        print(f"  Agent 1: Grouping {len(non_blank)} slides...")
        slide_groups_raw = _agent1_group_slides(client, screenshots, non_blank)
    else:
        print(f"  Agent 1: No slides — skipping (all groups will be transcript-only)")
        slide_groups_raw = []

    # Validate: every non-blank slide appears exactly once
    covered = set()
    for g in slide_groups_raw:
        covered.update(g.get("slides", []))
    missing = non_blank - covered
    if missing:
        # Surgical fix: ask Flash ONLY about the missing slides (fast, <5s)
        # instead of re-running the entire grouping call (~50s)
        print(f"    → Patching {len(missing)} missing slides: {sorted(missing)}")
        slide_groups_raw = _patch_missing_slides(
            client, slide_groups_raw, sorted(missing), screenshots
        )
        covered = set()
        for g in slide_groups_raw:
            covered.update(g.get("slides", []))
        still_missing = non_blank - covered
        if still_missing:
            # Final fallback: assign remaining orphans to nearest group by slide index
            for orphan in sorted(still_missing):
                best_group = None
                best_dist = float("inf")
                for g in slide_groups_raw:
                    for s in g.get("slides", []):
                        dist = abs(s - orphan)
                        if dist < best_dist:
                            best_dist = dist
                            best_group = g
                if best_group is not None:
                    best_group.setdefault("slides", []).append(orphan)
                    print(f"    → Orphan slide {orphan} → '{best_group.get('title', '?')}'")
                else:
                    slide_groups_raw.append({"title": f"Slide {orphan}", "slides": [orphan]})

    # FREEZE groups — no agent modifies these after this point
    notebook_groups = slide_groups_raw
    t1 = time.time()
    print(f"    → {len(notebook_groups)} groups in {t1 - t0:.1f}s")

    # ═══════════════════════════════════════════════════
    # Agent 2: Transcript Scanner (Flash, text-only)
    # ═══════════════════════════════════════════════════
    print(f"  Agent 2: Scanning transcript ({len(transcript.split())}w)...")
    t2 = time.time()

    notebook_groups, transcript_only_groups = _agent2_scan_transcript(
        client, notebook_groups, transcript, screenshots
    )

    # Add transcript-only groups to the notebook
    all_groups = notebook_groups + transcript_only_groups

    t3 = time.time()
    print(f"    → {len(transcript_only_groups)} transcript-only groups found in {t3 - t2:.1f}s")

    # ═══════════════════════════════════════════════════
    # Coordinator: Pro — strategic brain
    # ═══════════════════════════════════════════════════
    print(f"  Coordinator: Pro planning {len(all_groups)} groups...")
    t4 = time.time()

    master_plan = _coordinator_plan(client, all_groups, transcript)

    t5 = time.time()
    print(f"    → Master plan in {t5 - t4:.1f}s")

    # ═══════════════════════════════════════════════════
    # Agent 3: Teaching Planner (Flash + images)
    # ═══════════════════════════════════════════════════
    print(f"  Agent 3: Writing teaching plans...")
    t6 = time.time()

    teaching_plans, visual_strategies = _agent3_teaching_plans(
        client, all_groups, master_plan, screenshots, slide_image_parts, transcript
    )

    t7 = time.time()
    print(f"    → Teaching plans in {t7 - t6:.1f}s")

    # ═══════════════════════════════════════════════════
    # Assemble final SlideGroup objects
    # ═══════════════════════════════════════════════════
    groups = _assemble_groups(
        all_groups, master_plan, teaching_plans, visual_strategies, screenshots, transcript
    )

    # Save debug notebook
    _save_debug_notebook(debug_dir, all_groups, master_plan, teaching_plans, visual_strategies)

    total_t = time.time() - t0
    print(f"    → Total planning: {total_t:.1f}s")

    return groups


# ═══════════════════════════════════════════════════════════════════════════
# Agent 1: Slide Grouper
# ═══════════════════════════════════════════════════════════════════════════

def _agent1_group_slides(
    client,
    screenshots: list[dict],
    non_blank: set[int],
    missing_hint: list[int] | None = None,
) -> list[dict]:
    """Flash groups slides by topic from descriptions only.

    Agent context: You're the first step in a 4-agent pipeline. Your groupings
    become the skeleton of the entire lecture document — a Pro coordinator and
    parallel writers will build on top of your decisions. You never see the
    transcript or the images — other agents handle those. Your job is purely
    structural: which slides belong together by topic.

    Returns list of dicts: [{"title": str, "slides": [int]}]
    """
    slide_listing = []
    for i, s in enumerate(screenshots):
        if i not in non_blank:
            continue
        desc = s.get("description", "").strip()
        ts = s.get("timestamp_display", "")
        slide_listing.append(f"  Slide {i} [{ts}]: {desc[:200]}")

    slides_text = "\n".join(slide_listing)

    missing_note = ""
    if missing_hint:
        missing_descs = []
        for idx in missing_hint:
            if idx < len(screenshots):
                d = screenshots[idx].get("description", "")[:100]
                missing_descs.append(f"  Slide {idx}: {d}")
        missing_note = (
            "\n\nCRITICAL: Your previous attempt missed these slides. "
            "They MUST appear in a group:\n" + "\n".join(missing_descs)
        )

    all_indices = sorted(non_blank)
    checklist = ", ".join(str(i) for i in all_indices)

    prompt = f"""\
You're the first step in a 4-agent lecture-planning pipeline. A Pro model \
will use your groupings to plan the entire lecture document, and 12 parallel \
writers will generate content based on your structure. If you miss a slide, \
the student never sees that content. If you merge two different topics, \
the writer gets confused trying to explain two things at once.

Your job: group these {len(non_blank)} slides by topic. Each group should be \
one teachable concept — something a tutor would cover in one sitting before \
moving to the next thing.

Rules:
- Every slide index below must appear in exactly ONE group
- Aim for 8-20 groups depending on how many distinct concepts exist
- Slides showing the same concept from different angles → same group
- Slides on different topics → different groups, even if consecutive
- Quiz, review, or activity slides → group with the nearest teaching slide
- Order groups in the sequence a student should learn them

SLIDES:
{slides_text}
{missing_note}

CHECKLIST — these {len(non_blank)} indices MUST all appear in your output:
[{checklist}]
Before writing your response, mentally verify every index from the checklist \
is assigned to exactly one group. If any are missing, add them now.

Output ONLY valid JSON — no markdown, no explanation:
[
  {{"title": "Topic Name", "slides": [0, 1, 2]}},
  {{"title": "Another Topic", "slides": [3, 4]}},
  ...
]"""

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 8192},
        )
        raw = response.text.strip()

        # Save raw for debugging
        with open(Path("data/output/_v3_agent1_raw.txt"), "w", encoding="utf-8") as f:
            f.write(raw)

        # Extract JSON from response — handle markdown wrapping, comments, trailing commas
        from src.json_repair import extract_json
        try:
            result = extract_json(raw, expect_array=True)
            if result and isinstance(result, list):
                return result
        except Exception:
            pass

        # Fallback: regex-based extraction
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            # Clean common Flash JSON issues: trailing commas, comments
            cleaned = re.sub(r",\s*([}\]])", r"\1", json_match.group(0))
            cleaned = re.sub(r"//.*?\n", "\n", cleaned)
            return json.loads(cleaned)
        return json.loads(raw)
    except Exception as e:
        print(f"    [agent1] Failed: {e}")
        # Fallback: one group per slide
        return [{"title": f"Slide {i}", "slides": [i]} for i in sorted(non_blank)]


def _patch_missing_slides(
    client,
    existing_groups: list[dict],
    missing_indices: list[int],
    screenshots: list[dict],
) -> list[dict]:
    """Surgical fix: assign missing slides to existing groups or create new ones.

    Instead of re-running the entire grouping call (~50s), this asks Flash
    a tiny question: "here are the groups, here are the orphans, where do
    they go?" Takes ~3-5s.
    """
    group_listing = "\n".join(
        f"  Group {i}: {g.get('title', '?')} (slides: {g.get('slides', [])})"
        for i, g in enumerate(existing_groups)
    )

    missing_descs = []
    for idx in missing_indices:
        if idx < len(screenshots):
            desc = screenshots[idx].get("description", "")[:150]
            missing_descs.append(f"  Slide {idx}: {desc}")

    prompt = f"""\
These slides were missed during grouping. For each one, either assign it to \
an existing group (by group number) or create a new group.

EXISTING GROUPS:
{group_listing}

MISSING SLIDES:
{chr(10).join(missing_descs)}

Output ONLY valid JSON — a list of assignments:
[
  {{"slide": 15, "assign_to_group": 3}},
  {{"slide": 17, "new_group": "Topic Name"}}
]"""

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 1024},
        )
        raw = response.text.strip()
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()

        from src.json_repair import extract_json
        try:
            assignments = extract_json(cleaned, expect_array=True)
        except Exception:
            json_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if json_match:
                assignments = json.loads(re.sub(r",\s*([}\]])", r"\1", json_match.group(0)))
            else:
                assignments = json.loads(cleaned)

        # Apply assignments
        for a in assignments:
            slide_idx = a.get("slide", -1)
            if a.get("assign_to_group") is not None:
                group_num = a["assign_to_group"]
                if 0 <= group_num < len(existing_groups):
                    existing_groups[group_num].setdefault("slides", []).append(slide_idx)
            elif a.get("new_group"):
                existing_groups.append({
                    "title": a["new_group"],
                    "slides": [slide_idx],
                })

    except Exception as e:
        print(f"    [agent1-patch] Failed: {e}")
        # Last resort: append each missing slide as its own group
        for idx in missing_indices:
            desc = screenshots[idx].get("description", "")[:50] if idx < len(screenshots) else ""
            existing_groups.append({"title": f"Slide {idx}: {desc}", "slides": [idx]})

    return existing_groups


# ═══════════════════════════════════════════════════════════════════════════
# Agent 2: Transcript Scanner
# ═══════════════════════════════════════════════════════════════════════════

def _agent2_scan_transcript(
    client,
    slide_groups: list[dict],
    transcript: str,
    screenshots: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Flash matches transcript to slide groups and finds transcript-only topics.

    Agent context: Agent 1 already grouped the slides — that structure is frozen.
    You're now matching the professor's words to those groups. You're also the
    safety net: if the professor discussed HIV for 1,200 words but there's no
    slide for it, you're the only one who catches that. A Pro coordinator reads
    your output next and decides depth and ownership. One critical rule: each
    chunk of transcript goes to exactly one group. If you assign lytic cycle
    content to both Group 4 and Group 7, two parallel writers will both explain
    it and the student reads it twice.

    Returns:
        (updated_slide_groups, transcript_only_groups)
    """
    # Build group listing for Flash
    group_listing = "\n".join(
        f"  Group {i}: {g['title']} (slides: {g.get('slides', [])})"
        for i, g in enumerate(slide_groups)
    )

    # Transcript — send full text (Flash handles 1M tokens)
    transcript_text = transcript[:80000]

    no_slides = len(slide_groups) == 0

    if no_slides:
        prompt = f"""\
You're the second agent in a 4-agent lecture-planning pipeline. There are \
NO lecture slides for this lecture — only a transcript. Your job is to \
identify EVERY distinct topic the professor covers and create a group for it.

Think of it like chunking the lecture into teachable units. Each topic should \
be one concept a tutor would cover before moving to the next. Aim for 8-15 \
groups depending on how many distinct topics exist in the transcript.

A Pro coordinator reads your output next. They need to know every topic so \
they can decide depth and sequencing. If you miss a topic, the student never \
learns it. If you merge two different concepts, the writer gets confused.

The transcript is auto-captioned and messy — extract the real scientific \
vocabulary, not filler. For each topic, list sub-concepts: the distinct \
mechanisms, classes, steps, or types a student needs to understand individually.

FULL TRANSCRIPT:
{transcript_text}

Output ONLY valid JSON:
{{
  "slide_groups": [],
  "transcript_only": [
    {{
      "title": "Topic Name",
      "key_terms": ["term1", "term2"],
      "sub_concepts": ["mechanism A does X", "mechanism B does Y"],
      "transcript_words": 800,
      "rationale": "Professor spent ~800 words explaining this concept"
    }}
  ]
}}"""
    else:
        prompt = f"""\
You're the second agent in a 4-agent lecture-planning pipeline. Agent 1 has \
already grouped the lecture slides by topic (those groups are frozen — you \
can't change them). Your job is two things:

1. For each slide group below, list the key scientific terms the professor \
discusses during those slides. The professor's transcript is auto-captioned \
and messy — extract the real scientific vocabulary, not filler.

2. Identify topics the professor covered extensively in the transcript that \
DON'T match any slide group. These are "transcript-only" topics — the \
professor talked about them but didn't show a dedicated slide. These are \
often the most important content: case studies (HIV, Influenza), applied \
concepts (Gram staining), or entire topic shifts (from viruses to bacteria).

A Pro coordinator reads your output next. They need to know what's in each \
group and what's missing so they can make depth and ownership decisions. \
If you miss a transcript topic, the student never learns it.

One critical rule: each major topic belongs to ONE group only. If the \
professor mentions "reverse transcriptase" in both the Baltimore section \
and the HIV section, pick the one where it's taught most thoroughly. The \
coordinator will handle cross-references.

SLIDE GROUPS (frozen):
{group_listing}

FULL TRANSCRIPT:
{transcript_text}

Output ONLY valid JSON:
{{
  "slide_groups": [
    {{
      "group_index": 0,
      "key_terms": ["term1", "term2"],
      "sub_concepts": ["Class I: dsDNA→mRNA via host RNA polymerase", "Class II: ssDNA→dsDNA→mRNA"],
      "transcript_words": 500,
      "professor_signals": "professor said 'you need to know this'"
    }}
  ],
  "transcript_only": [
    {{
      "title": "Topic Name",
      "key_terms": ["term1", "term2"],
      "sub_concepts": ["CD4 binding mechanism", "reverse transcription → integration", "triple drug therapy"],
      "transcript_words": 800,
      "rationale": "Professor spent ~800 words on HIV treatment but no slide exists"
    }}
  ]
}}

For sub_concepts: list the distinct mechanisms, classes, steps, or types a \
student needs to understand individually. Not just term names — include \
what each one DOES. "Class IV: +ssRNA = mRNA, direct translation" not just \
"Class IV." If a group has 7 distinct sub-concepts, the coordinator will \
know it needs deep treatment. If it has 1-2, it's standard."""

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 8192},
        )
        raw = response.text.strip()
        # Strip markdown wrappers
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                json_str = re.sub(r",\s*([}\]])", r"\1", json_match.group(0))
                data = json.loads(json_str)
            else:
                data = json.loads(cleaned)

        # Merge Agent 2's findings into the slide groups
        for sg_info in data.get("slide_groups", []):
            idx = sg_info.get("group_index", -1)
            if 0 <= idx < len(slide_groups):
                slide_groups[idx]["key_terms"] = sg_info.get("key_terms", [])
                slide_groups[idx]["sub_concepts"] = sg_info.get("sub_concepts", [])
                slide_groups[idx]["transcript_words"] = sg_info.get("transcript_words", 0)
                slide_groups[idx]["professor_signals"] = sg_info.get("professor_signals", "")

        # Build transcript-only groups
        transcript_only = []
        for to in data.get("transcript_only", []):
            transcript_only.append({
                "title": to.get("title", "Unknown Topic"),
                "slides": [],  # No slides
                "key_terms": to.get("key_terms", []),
                "sub_concepts": to.get("sub_concepts", []),
                "transcript_words": to.get("transcript_words", 0),
                "rationale": to.get("rationale", ""),
            })

        return slide_groups, transcript_only

    except Exception as e:
        print(f"    [agent2] Failed: {e}")
        return slide_groups, []


# ═══════════════════════════════════════════════════════════════════════════
# Coordinator: Pro — the strategic brain
# ═══════════════════════════════════════════════════════════════════════════

def _coordinator_plan(
    client,
    all_groups: list[dict],
    transcript: str,
) -> dict:
    """Pro coordinator reads the full notebook and writes the master plan.

    Agent context: You're the strategic brain. Flash agents have done the
    mechanical work — grouped slides, matched transcript, flagged overlaps.
    You see the full picture in a structured notebook. Your master plan is
    final — parallel writers execute against it simultaneously and can't see
    each other's output. If you assign 'Baltimore classes' to two groups,
    both writers teach it from scratch. The student reads the same explanation
    twice. Every concept must have exactly one owner.

    Returns master plan dict.
    """
    # Build the notebook — everything the coordinator needs to know
    notebook_lines = []
    for i, g in enumerate(all_groups):
        slides_str = ",".join(str(s) for s in g.get("slides", []))
        terms = ", ".join(g.get("key_terms", [])[:10])
        sub_concepts = g.get("sub_concepts", [])
        tw = g.get("transcript_words", 0)
        signals = g.get("professor_signals", "")
        rationale = g.get("rationale", "")

        line = f"Group {i}: \"{g['title']}\""
        if slides_str:
            line += f" | slides: [{slides_str}]"
        else:
            line += " | TRANSCRIPT-ONLY (no slides)"
        if sub_concepts:
            line += f" | {len(sub_concepts)} sub-concepts: [{'; '.join(sub_concepts[:8])}]"
        elif terms:
            line += f" | terms: {terms}"
        line += f" | ~{tw}w transcript"
        if signals:
            line += f" | prof: \"{signals}\""
        if rationale:
            line += f" | note: {rationale}"
        notebook_lines.append(line)

    notebook_text = "\n".join(notebook_lines)
    total_transcript_words = len(transcript.split())

    prompt = f"""\
You're the strategic coordinator in a lecture-replacement pipeline. Two Flash \
agents have already done the groundwork — they grouped {len(all_groups)} \
topics from the lecture slides and transcript. Now you decide the master plan.

Your plan is final and immutable. {len(all_groups)} parallel Pro writers will \
execute against it simultaneously. They can't see each other's output. The \
student reads all sections in order as one continuous document.

Four decisions only you can make:

1. DEPTH — every group is one of three things:
  - "deep" (400-600w): complex mechanisms with multiple steps, classification \
    systems with multiple distinct classes to explain individually, core exam \
    topics. If a group contains a framework with N distinct categories (e.g. \
    7 Baltimore classes, 4 Gram types, 5 lytic cycle stages), it is deep — \
    each category needs its own explanation.
  - "standard" (150-300w): important single concepts, structural descriptions, \
    comparisons. One focused teaching moment.
  - "merge_into" (0w): low-importance topics that don't deserve their own \
    section. Merged into an adjacent group as a 1-2 sentence mention. The \
    anatomy professor never writes standalone transitions — she ends each \
    section by pulling into the next one. If a topic is too small to teach, \
    absorb it into its neighbor. Set merge_target to the group_index it \
    should be absorbed into.

  There is NO "bridge" depth. Every section either teaches something or gets \
  merged. The student's reading experience should feel like one continuous \
  flow, not choppy alternation between full sections and throwaway transitions.

2. OWNERSHIP — which concepts belong to which group? If "lytic cycle" appears \
in the transcript for both Group 4 and Group 7, assign it to ONE. The other \
gets "callback_only: lytic cycle → Group 4".

3. SEQUENCE — what order should the student read these groups?

4. SLIDE QUALITY — for each group with professor slides, flag whether the \
slide is clear enough to carry teaching load ("slide_teaches": true) or \
whether the transcript must explain from scratch. Groups where the slide \
teaches well get LOWER word targets — the writer just points at it.

NOTEBOOK — everything the agents found:
{notebook_text}

Total transcript: {total_transcript_words} words.

WORD BUDGET: total across all groups must be 5,500-6,500 words. This \
produces a 25-minute read for a 2-hour lecture. Deep sections are where \
the value is — don't compress them. Standard sections should be tight. \
Merged sections cost 0 words.

Output ONLY valid JSON:
{{
  "groups": [
    {{
      "group_index": 0,
      "title": "Topic Name",
      "depth": "deep",
      "ei_percent": 90,
      "word_target": 600,
      "slide_teaches": false,
      "owns": ["concept A", "concept B"],
      "callback_only": ["concept C → Group 3"],
      "sequence_position": 1
    }},
    {{
      "group_index": 5,
      "title": "Minor Topic",
      "depth": "merge_into",
      "merge_target": 4,
      "ei_percent": 30,
      "word_target": 0,
      "slide_teaches": false,
      "owns": [],
      "callback_only": [],
      "sequence_position": 0
    }}
  ],
  "total_words": 6000
}}

Every group from the notebook must appear. Start output now:"""

    try:
        from google.genai import types as genai_types

        response = client.models.generate_content(
            model=GENERATOR_MODEL,
            contents=prompt,
            config={
                "temperature": 0.3,
                "max_output_tokens": 8192,
                # Thinking mode helps the coordinator reason through overlap
                # detection and depth allocation before committing to JSON.
                # This fixes the depth-flattening issue (e.g. Baltimore at 70%
                # instead of 95%) observed without thinking.
                "thinking_config": genai_types.ThinkingConfig(
                    thinking_level="MEDIUM",
                ),
            },
        )
        raw = response.text.strip()

        # Log thinking tokens for cost tracking
        usage = getattr(response, "usage_metadata", None)
        if usage:
            think_tokens = getattr(usage, "thoughts_token_count", 0) or 0
            out_tokens = getattr(usage, "candidates_token_count", 0) or 0
            print(f"    [coordinator] {think_tokens} thinking + {out_tokens} output tokens")

        # Save for debugging
        with open(Path("data/output/_v3_coordinator_plan.txt"), "w", encoding="utf-8") as f:
            f.write(raw)

        # Strip markdown wrappers (```json ... ```)
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fallback: extract JSON object
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            # Clean trailing commas
            json_str = re.sub(r",\s*([}\]])", r"\1", json_match.group(0))
            return json.loads(json_str)
        return json.loads(cleaned)
    except Exception as e:
        print(f"    [coordinator] Failed: {e}")
        # Fallback: standard depth for everything
        return {
            "groups": [
                {
                    "group_index": i,
                    "title": g["title"],
                    "depth": "standard",
                    "ei_percent": 70,
                    "word_target": 350,
                    "owns": g.get("key_terms", []),
                    "callback_only": [],
                    "sequence_position": i + 1,
                }
                for i, g in enumerate(all_groups)
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════
# Agent 3: Teaching Planner
# ═══════════════════════════════════════════════════════════════════════════

def _agent3_teaching_plans(
    client,
    all_groups: list[dict],
    master_plan: dict,
    screenshots: list[dict],
    slide_image_parts: list | None,
    transcript: str,
) -> dict[int, str]:
    """Flash writes teaching notes for each group, guided by the master plan.

    Agent context: The coordinator has already decided WHAT each section teaches
    and what's callback-only. You decide HOW to teach it — the pedagogical
    approach, the hooks, the analogies. You can see the actual slide images and
    transcript excerpts. Your teaching notes guide the Pro writers but cannot
    override the coordinator's ownership decisions. If the coordinator says
    'lytic cycle is callback-only for this group,' your teaching notes should
    not include a lytic cycle walkthrough.

    Returns dict mapping group_index → (teaching_notes, visual_strategy, visual_data).
    """
    from google.genai import types
    from concurrent.futures import ThreadPoolExecutor, as_completed

    plan_groups = {g["group_index"]: g for g in master_plan.get("groups", [])}

    def _plan_one(group_idx: int, group: dict) -> tuple[int, str, str, dict]:
        pg = plan_groups.get(group_idx, {})
        depth = pg.get("depth", "standard")

        if depth == "skip":
            return group_idx, "SKIP", "", {}

        owns = pg.get("owns", [])
        callbacks = pg.get("callback_only", [])
        word_target = pg.get("word_target", 300)

        # Get slide images for this group
        parts = []
        slide_indices = group.get("slides", [])
        if slide_indices and slide_image_parts:
            for idx in slide_indices:
                if idx < len(slide_image_parts):
                    parts.append(slide_image_parts[idx])

        # Get transcript excerpt
        key_terms = group.get("key_terms", [])
        excerpt = _extract_transcript_for_slides(
            slide_indices, screenshots, transcript, key_terms=key_terms
        )

        # Build slide descriptions
        slide_descs = ""
        if slide_indices:
            descs = []
            for idx in slide_indices:
                if idx < len(screenshots):
                    s = screenshots[idx]
                    descs.append(f"Slide {idx}: {s.get('description', '')[:150]}")
            slide_descs = "\n".join(descs)

        owns_str = ", ".join(owns) if owns else "all concepts in this group"
        cb_str = "\n".join(f"  - {cb}" for cb in callbacks) if callbacks else "  (none)"

        has_slides = bool(slide_indices)

        prompt = f"""\
You're the pedagogical planner in a lecture-replacement pipeline. A Pro \
coordinator has already assigned concept ownership — you cannot override \
those decisions. Your job is two things: (1) write teaching notes that tell \
a talented writer HOW to teach this section, and (2) decide the VISUAL \
STRATEGY — what image or card the student sees alongside the transcript.

GROUP: {group['title']}
DEPTH: {depth} (~{word_target} words)
THIS SECTION OWNS (teach fully): {owns_str}
CALLBACK ONLY (mention by name, don't re-explain):
{cb_str}

{"SLIDE DESCRIPTIONS:" + chr(10) + slide_descs if slide_descs else "NO SLIDES — transcript-only topic"}

{"TRANSCRIPT EXCERPT:" + chr(10) + excerpt[:4000] if excerpt else "No transcript excerpt available"}

VISUAL STRATEGY — pick one:
- "professor_slide": the professor's slide is a clear labeled diagram, table, \
or structured visual. The writer should point at it ('look at the three columns') \
rather than re-describe it. Pick this when the slide genuinely teaches.
- "openstax_figure": no usable professor slide, but a textbook diagram would \
help (e.g. HIV life cycle, cell membrane structure, Gram staining procedure). \
Include search_terms the system can use to find the right OpenStax figure.
- "structured_card": no real image works here. Write a card with a title, \
3-5 bullet points or a small comparison table, and one exam tip. The frontend \
renders this as a styled card — not an image.

Output ONLY valid JSON — no markdown, no explanation:
{{
  "teaching_notes": "3-5 sentences: core concept, hard part, hooks, connections...",
  "visual_strategy": "professor_slide OR openstax_figure OR structured_card",
  "visual_data": {{}}
}}

visual_data by strategy:
- professor_slide: {{"best_slide_index": <int>, "description": "what makes this slide useful"}}
- openstax_figure: {{"topic": "...", "search_terms": ["term1", "term2"]}}
- structured_card: {{"title": "...", "bullets": ["point 1", "point 2", "..."], "exam_tip": "..."}}

Do NOT include a walkthrough of callback-only concepts."""

        text_parts = [types.Part.from_text(text=prompt)]
        if parts:
            text_parts = parts + text_parts

        try:
            response = client.models.generate_content(
                model=CHUNKER_FALLBACK_MODEL,
                contents=text_parts,
                config={"temperature": 0.3, "max_output_tokens": 2048},
            )
            raw_text = response.text.strip()

            # Parse JSON response
            try:
                # Strip markdown wrappers
                cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).strip()
                cleaned = re.sub(r"```\s*$", "", cleaned).strip()
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if json_match:
                    json_str = re.sub(r",\s*([}\]])", r"\1", json_match.group(0))
                    parsed = json.loads(json_str)
                else:
                    # Fallback: treat entire response as teaching notes
                    parsed = {"teaching_notes": raw_text, "visual_strategy": "", "visual_data": {}}

            notes = parsed.get("teaching_notes", raw_text)
            vs = parsed.get("visual_strategy", "")
            vd = parsed.get("visual_data", {})

            # Validate visual_strategy
            if vs not in ("professor_slide", "openstax_figure", "structured_card"):
                # Auto-assign based on whether group has slides
                vs = "professor_slide" if has_slides else "openstax_figure"
                vd = {}

            return group_idx, notes, vs, vd
        except Exception as e:
            print(f"    [agent3] Failed for '{group['title']}': {e}")
            vs = "professor_slide" if has_slides else "structured_card"
            return group_idx, f"Teach {group['title']} at {depth} depth.", vs, {}

    # Run in parallel
    teaching_plans: dict[int, str] = {}
    visual_strategies: dict[int, tuple[str, dict]] = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_plan_one, i, g): i
            for i, g in enumerate(all_groups)
        }
        for future in as_completed(futures):
            idx, plan, vs, vd = future.result()
            teaching_plans[idx] = plan
            visual_strategies[idx] = (vs, vd)

    return teaching_plans, visual_strategies


# ═══════════════════════════════════════════════════════════════════════════
# Assembly — combine agent outputs into SlideGroup objects
# ═══════════════════════════════════════════════════════════════════════════

def _assemble_groups(
    all_groups: list[dict],
    master_plan: dict,
    teaching_plans: dict[int, str],
    visual_strategies: dict[int, tuple[str, dict]],
    screenshots: list[dict],
    transcript: str,
) -> list[SlideGroup]:
    """Combine agent outputs into final SlideGroup objects for Pro generation.

    Handles merge_into groups by absorbing their slides, terms, and transcript
    into the target group. Merged groups don't produce their own sections.
    """
    plan_by_idx = {g["group_index"]: g for g in master_plan.get("groups", [])}

    # First pass: collect merge_into relationships
    merge_map: dict[int, list[int]] = {}  # target_idx → [source_idxs]
    for pg in master_plan.get("groups", []):
        if pg.get("depth") == "merge_into":
            target = pg.get("merge_target", -1)
            if target >= 0:
                merge_map.setdefault(target, []).append(pg["group_index"])

    # Sort by coordinator's sequence position, excluding merged groups
    merged_indices = set()
    for sources in merge_map.values():
        merged_indices.update(sources)

    sorted_plan = sorted(
        [g for g in master_plan.get("groups", []) if g.get("depth") != "merge_into"],
        key=lambda g: g.get("sequence_position", 999)
    )
    ordered_indices = [g["group_index"] for g in sorted_plan]

    # Build SlideGroups in sequence order
    groups = []
    for seq, group_idx in enumerate(ordered_indices):
        if group_idx >= len(all_groups):
            continue

        ag = all_groups[group_idx]
        pg = plan_by_idx.get(group_idx, {})

        # Absorb merged groups' content
        merged_sources = merge_map.get(group_idx, [])
        for src_idx in merged_sources:
            if src_idx < len(all_groups):
                src = all_groups[src_idx]
                # Absorb slides
                ag.setdefault("slides", []).extend(src.get("slides", []))
                # Absorb key terms
                ag.setdefault("key_terms", []).extend(src.get("key_terms", []))
                # Note the merge in teaching plan
                src_title = src.get("title", f"Group {src_idx}")
                existing_plan = teaching_plans.get(group_idx, "")
                teaching_plans[group_idx] = (
                    existing_plan +
                    f"\n\nMERGED CONTENT from '{src_title}': mention briefly "
                    f"(1-2 sentences) as part of this section."
                )

        depth = pg.get("depth", "standard")
        slide_indices = ag.get("slides", [])
        key_terms = ag.get("key_terms", [])
        teaching_plan = teaching_plans.get(group_idx, "")

        # Match transcript excerpt
        transcript_excerpt = _extract_transcript_for_slides(
            slide_indices, screenshots, transcript, key_terms=key_terms
        )

        # Build ownership context into teaching plan
        owns = pg.get("owns", [])
        callbacks = pg.get("callback_only", [])
        ownership_note = ""
        if callbacks:
            cb_str = "\n".join(f"  - {cb}" for cb in callbacks)
            ownership_note = (
                "\n\nCALLBACK ONLY — another writer owns these. Mention by name "
                "only, do NOT re-explain:\n" + cb_str
            )
        if owns:
            owns_str = "\n".join(f"  - {o}" for o in owns)
            ownership_note += "\n\nYOUR SECTION OWNS — teach fully:\n" + owns_str

        full_plan = teaching_plan + ownership_note

        # Visual strategy from Agent 3
        vs, vd = visual_strategies.get(group_idx, ("", {}))
        # For merged groups, inherit the target's visual strategy if none set
        if not vs and merged_sources:
            for src_idx in merged_sources:
                src_vs, src_vd = visual_strategies.get(src_idx, ("", {}))
                if src_vs:
                    vs, vd = src_vs, src_vd
                    break

        groups.append(SlideGroup(
            group_index=seq,
            title=ag["title"],
            slide_indices=slide_indices,
            teaching_plan=full_plan,
            depth=depth,
            word_estimate=pg.get("word_target", 300),
            transcript_excerpt=transcript_excerpt,
            ei_estimate=pg.get("ei_percent", 50),
            key_terms=key_terms,
            visual_strategy=vs,
            visual_data=vd,
            original_group_index=group_idx,
        ))

    return groups


def _save_debug_notebook(
    debug_dir: Path,
    all_groups: list[dict],
    master_plan: dict,
    teaching_plans: dict[int, str],
    visual_strategies: dict[int, tuple[str, dict]] | None = None,
) -> None:
    """Save the full notebook for debugging."""
    notebook = {
        "agent1_groups": all_groups,
        "coordinator_plan": master_plan,
        "agent3_teaching_plans": {str(k): v[:200] for k, v in teaching_plans.items()},
        "visual_strategies": {
            str(k): {"strategy": v[0], "data": v[1]}
            for k, v in (visual_strategies or {}).items()
        },
    }
    path = debug_dir / "_v3_notebook.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    print(f"  [debug] Notebook saved to {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Transcript extraction helpers
# ═══════════════════════════════════════════════════════════════════════════

def _extract_transcript_for_slides(
    slide_indices: list[int],
    screenshots: list[dict],
    full_transcript: str,
    key_terms: list[str] | None = None,
) -> str:
    """Extract the portion of transcript that corresponds to given slides.

    Uses slide timestamps to find the relevant transcript window.
    For slide-less groups (transcript-only), searches by key terms.
    """
    if not slide_indices:
        if key_terms and full_transcript:
            return _search_transcript_by_terms(full_transcript, key_terms)
        return ""

    if not screenshots:
        return ""

    timestamps = []
    for idx in slide_indices:
        if idx < len(screenshots):
            ts = screenshots[idx].get("timestamp_seconds", 0)
            timestamps.append(ts)

    if not timestamps:
        return ""

    start_ts = min(timestamps)
    end_ts = max(timestamps)

    all_timestamps = sorted(set(
        s.get("timestamp_seconds", 0) for s in screenshots
    ))
    for ts in all_timestamps:
        if ts > end_ts:
            end_ts = ts
            break
    else:
        end_ts = float("inf")

    total_duration = max(
        s.get("timestamp_seconds", 0) for s in screenshots
    ) or 1
    total_chars = len(full_transcript)

    start_frac = start_ts / total_duration
    end_frac = min(end_ts / total_duration, 1.0)

    padding = 0.05
    start_char = max(0, int((start_frac - padding) * total_chars))
    end_char = min(total_chars, int((end_frac + padding) * total_chars))

    excerpt = full_transcript[start_char:end_char].strip()

    if start_char > 0:
        space_idx = excerpt.find(" ")
        if space_idx > 0 and space_idx < 50:
            excerpt = excerpt[space_idx + 1:]

    return excerpt[:8000]


def _search_transcript_by_terms(
    full_transcript: str,
    key_terms: list[str],
    context_chars: int = 3000,
) -> str:
    """Find the best transcript excerpt matching a set of key terms."""
    if not key_terms:
        return ""

    transcript_lower = full_transcript.lower()
    positions = []
    for term in key_terms:
        term_lower = term.lower()
        start = 0
        while True:
            idx = transcript_lower.find(term_lower, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + len(term_lower)

    if not positions:
        return ""

    positions.sort()
    best_start = positions[0]
    best_count = 0

    for i, pos in enumerate(positions):
        count = sum(1 for p in positions if pos <= p < pos + context_chars)
        if count > best_count:
            best_count = count
            best_start = pos

    padding = 500
    start = max(0, best_start - padding)
    end = min(len(full_transcript), best_start + context_chars + padding)

    excerpt = full_transcript[start:end].strip()
    if start > 0:
        space = excerpt.find(" ")
        if 0 < space < 50:
            excerpt = excerpt[space + 1:]

    return excerpt[:8000]


def _assign_term_ownership_v3(groups: list[SlideGroup]) -> None:
    """Assign new vs prior terms across all groups using set arithmetic.

    Same logic as V2's _assign_term_ownership but for SlideGroups.
    First group to mention a term owns it as "new". Subsequent groups
    get it as "prior".
    """
    seen: set[str] = set()

    for group in groups:
        if group.depth == "skip":
            continue

        all_terms_lower = {t.lower(): t for t in group.key_terms}
        group.new_terms = [all_terms_lower[k] for k in all_terms_lower if k not in seen]
        group.prior_terms = [all_terms_lower[k] for k in all_terms_lower if k in seen]
        seen.update(t.lower() for t in group.new_terms)


# ═══════════════════════════════════════════════════════════════════════════
# Pro generation — one call per slide group
# ═══════════════════════════════════════════════════════════════════════════

def build_user_prompt_v3(
    group: SlideGroup,
    slide_number: int,
    screenshots: list[dict],
    screenshots_dir: Path,
    textbook_section: str,
    textbook_images: list[dict] | None = None,
    prior_groups: list[SlideGroup] | None = None,
) -> list:
    """Build the per-group user prompt as a list of Parts.

    V3 ordering: teaching plan (Flash's big-picture instructions) → prior context
    → textbook → transcript excerpt → actual slide images → output instruction.

    The teaching plan comes first because it frames the entire task. Pro reads
    Flash's plan, understands the role of this section in the bigger document,
    THEN reads the source material.
    """
    from google.genai import types

    parts = []

    # 1. Teaching plan — word target is a CEILING for standard, a TARGET for deep
    if group.depth == "standard":
        depth_instruction = (
            f"WORD CEILING: {group.word_estimate} words. This is a hard limit. "
            f"The anatomy professor covers a standard concept in 130 words per "
            f"slide — concise warmth, not verbose warmth. If the slide teaches "
            f"well, point at it and move on. Don't re-describe what the student "
            f"can already see."
        )
    else:  # deep
        depth_instruction = (
            f"Target: ~{group.word_estimate} words. This is a deep-dive section — "
            f"take the space you need to teach the mechanism step by step."
        )

    plan_text = (
        f"TEACHING PLAN FOR THIS SECTION\n"
        f"Topic: {group.title}\n"
        f"Exam Importance: {group.ei_estimate}%\n\n"
        f"{depth_instruction}\n\n"
        f"{group.teaching_plan}"
    )
    parts.append(types.Part.from_text(text=plan_text))

    # 1b. Visual strategy — how this section's slide works
    # Override: if Agent 3 said "structured_card" but we actually found
    # OpenStax/Wikimedia images during Stage 2, upgrade to "openstax_figure".
    # Agent 3 doesn't see fetched images (they're fetched after planning).
    effective_strategy = group.visual_strategy
    if effective_strategy == "structured_card" and textbook_images:
        has_real_images = any(img.get("gcs_url") for img in textbook_images)
        if has_real_images:
            effective_strategy = "openstax_figure"

    if effective_strategy == "professor_slide":
        best_slide = group.visual_data.get("best_slide_index", "")
        slide_desc = group.visual_data.get("description", "")
        parts.append(types.Part.from_text(text=
            "VISUAL STRATEGY: PROFESSOR SLIDE\n"
            f"The professor's slide{f' (slide {best_slide})' if best_slide != '' else ''} "
            f"is clear enough to carry teaching load{f': {slide_desc}' if slide_desc else ''}.\n"
            "Point at it in your transcript — 'look at the diagram', 'notice the three "
            "columns on the slide'. Don't re-describe what the student can already see. "
            "This lets you keep the transcript concise."
        ))
    elif effective_strategy == "openstax_figure":
        topic = group.visual_data.get("topic", group.title)
        parts.append(types.Part.from_text(text=
            "VISUAL STRATEGY: TEXTBOOK/REFERENCE FIGURE\n"
            f"No usable professor slide — a textbook or reference diagram for '{topic}' "
            "will be provided as the visual. Reference it in your transcript the same "
            "way you'd point at a professor's slide: 'Looking at the diagram, notice "
            "how...' The image URL will appear in the figures section below.\n"
            "You MUST embed at least one figure using ![caption](URL) in your slide card."
        ))
    elif effective_strategy == "structured_card":
        card_title = group.visual_data.get("title", group.title)
        bullets = group.visual_data.get("bullets", [])
        exam_tip = group.visual_data.get("exam_tip", "")
        card_content = f"Title: {card_title}"
        if bullets:
            card_content += "\nBullets:\n" + "\n".join(f"  - {b}" for b in bullets)
        if exam_tip:
            card_content += f"\nExam tip: {exam_tip}"
        parts.append(types.Part.from_text(text=
            "VISUAL STRATEGY: STRUCTURED CARD\n"
            "No real image works here. Your slide card should contain structured "
            "content the frontend renders as a card (not an image).\n\n"
            f"CARD CONTENT:\n{card_content}\n\n"
            "Your transcript can reference these points: 'as the summary card shows...'"
        ))

    # 2. What's been covered so far — natural backwards connections
    if prior_groups:
        prior_teaching = [g for g in prior_groups if g.depth != "skip"]
        if prior_teaching:
            prior_lines = []
            for pg in prior_teaching[-5:]:  # Last 5 groups for context
                terms_str = ", ".join(pg.new_terms[:5]) if pg.new_terms else ""
                prior_lines.append(
                    f"  Section {pg.group_index + 1}: {pg.title}"
                    + (f" (terms: {terms_str})" if terms_str else "")
                )
            parts.append(types.Part.from_text(text=
                "PREVIOUSLY COVERED SECTIONS:\n"
                + "\n".join(prior_lines) + "\n\n"
                "Connect backwards naturally where relevant — 'remember the capsid "
                "we covered earlier' if you'd already taught it."
            ))

    # Term tracking
    if group.new_terms:
        parts.append(types.Part.from_text(text=
            f"TERMS TO BOLD (first introduction): {', '.join(group.new_terms)}\n"
            "Bold these on first use — the student hasn't seen them before."
        ))
    if group.prior_terms:
        parts.append(types.Part.from_text(text=
            f"TERMS ALREADY INTRODUCED (don't re-bold): {', '.join(group.prior_terms)}\n"
            "Use casually without re-defining."
        ))

    # 3. Textbook reference
    if textbook_section:
        parts.append(types.Part.from_text(text=
            f"OPENSTAX TEXTBOOK REFERENCE (your factual source of truth — "
            f"if the professor contradicts this, go with the textbook):\n\n"
            f"{textbook_section}"
        ))

    # 4. Professor's transcript excerpt
    if group.transcript_excerpt:
        parts.append(types.Part.from_text(text=
            f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION.\n"
            f"Use this for WHAT to teach, not HOW. The transcript is auto-captioned "
            f"and full of garbled terms — always use correct scientific spelling.\n\n"
            f"{group.transcript_excerpt}"
        ))

    # 5. Actual slide images + metadata
    slide_parts, slide_meta = _get_group_slides(group, screenshots, screenshots_dir)
    if slide_parts and slide_meta:
        slide_listing = "\n".join(
            f"  - {s['image_filename']} [{s.get('timestamp_display', '')}]: "
            f"{s.get('description', '')[:120]}"
            for s in slide_meta
        )
        parts.append(types.Part.from_text(text=
            "PROFESSOR'S LECTURE SLIDES FOR THIS SECTION. These are the actual "
            "slides the student sees in class. Use them as the primary visual.\n\n"
            f"{slide_listing}\n\n"
            "Reference slide images like: ![description](screenshots/screenshot_00X.jpg)\n"
            "Your transcript should physically point at these slides — "
            "'Looking at the slide, notice...', 'On the diagram you can see...'."
        ))
        parts.extend(slide_parts)

    # 5b. Textbook / Wikimedia figures
    if textbook_images:
        img_lines = []
        for img in textbook_images:
            if not img.get("gcs_url"):
                continue
            source = img.get("source", "openstax")
            fig_id = img.get("figure_id") or "Figure"
            caption = img.get("caption", "")[:120]
            attribution = img.get("attribution", "")
            line = f"  - {fig_id}: {caption}\n    URL: {img['gcs_url']}"
            if source == "wikimedia" and attribution:
                line += f"\n    Attribution: {attribution}"
            img_lines.append(line)

        img_listing = "\n".join(img_lines)
        if img_listing:
            # Determine source attribution
            sources = {img.get("source", "openstax") for img in textbook_images if img.get("gcs_url")}
            if "wikimedia" in sources and "openstax" not in sources:
                source_line = "Source: Wikimedia Commons. License and attribution per figure above."
            elif "wikimedia" in sources:
                source_line = "Sources: OpenStax (CC BY 4.0) and Wikimedia Commons (license per figure)."
            else:
                source_line = "Source: OpenStax. Download free at openstax.org. CC BY 4.0"

            parts.append(types.Part.from_text(text=
                "TEXTBOOK/REFERENCE FIGURES AVAILABLE FOR THIS SECTION.\n"
                "IMPORTANT: You may ONLY use URLs from the list below. Do NOT "
                "invent or guess figure URLs — if the figure you want isn't "
                "listed here, write text instead of an image reference.\n\n"
                f"{img_listing}\n\n"
                f"{source_line}"
            ))

    # 6. Output instruction — word ceiling enforced here
    word_note = ""
    if group.depth == "standard":
        word_note = (
            f"\nWORD CEILING: {group.word_estimate} words for the transcript. "
            "Be concise. The anatomy professor covers a concept in 130 words per slide."
        )

    # Slide type guidance based on visual strategy
    if effective_strategy == "professor_slide":
        slide_type_hint = (
            "type: professor_slide\n"
            "The professor's slide is clear — just reference it with an image "
            "markdown and add one exam-relevant takeaway underneath. Don't duplicate "
            "the slide's labels or bullet points."
        )
    elif effective_strategy == "openstax_figure":
        slide_type_hint = (
            "type: diagram\n"
            "Embed the best matching figure using markdown: ![caption](URL). "
            "Add 2-3 dot points providing context around the figure."
        )
    elif effective_strategy == "structured_card":
        slide_type_hint = (
            "type: diagram\n"
            "[Write ONLY the card content below — title, bullet points, and exam tip. "
            "Do NOT include any meta-instructions like 'no image available' or "
            "'the frontend renders this'. Just write the actual content directly.]"
        )
    else:
        slide_type_hint = (
            "type: professor_slide OR diagram\n"
            "[If type is professor_slide: just the image reference and one exam tip.]\n"
            "[If type is diagram: dot points + embed OpenStax figure if available.]"
        )

    parts.append(types.Part.from_text(text=
        f"\nWrite this as Slide {slide_number}. "
        "Output in this exact format:\n\n"
        "=== SLIDE ===\n"
        f"Slide {slide_number}: [Your title]\n"
        f"{slide_type_hint}\n"
        f"[If this section needs multiple visuals, split as Slide {slide_number}a, "
        f"Slide {slide_number}b, etc.]\n\n"
        "=== TRANSCRIPT ===\n"
        f"Slide {slide_number}\n"
        "[Your transcript — written exactly how the anatomy professor writes]\n\n"
        "=== EI% ===\n"
        "[0-100]% — [One sentence: why this score.]"
        + word_note
    ))

    return parts


def _get_group_slides(
    group: SlideGroup,
    screenshots: list[dict],
    screenshots_dir: Path,
) -> tuple[list, list[dict]]:
    """Get image Parts and metadata for slides in a group."""
    from google.genai import types

    matched = []
    parts = []

    for idx in group.slide_indices:
        if idx < len(screenshots):
            s = screenshots[idx]
            matched.append(s)

            img_path = screenshots_dir / s["image_filename"]
            if img_path.exists():
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    return parts, matched


def generate_section_v3(
    client,
    group: SlideGroup,
    slide_number: int,
    screenshots: list[dict],
    screenshots_dir: Path,
    textbook_section: str,
    textbook_images: list[dict] | None = None,
    prior_groups: list[SlideGroup] | None = None,
    cache_name: str | None = None,
    model: str | None = None,
    tier: str = "pro",
) -> GeneratedSection:
    """Generate one section from a slide group.

    Two-tier generation (no bridges — coordinator merges low-importance topics):
    - "pro" (GENERATOR_MODEL): full creative brief via context cache, anatomy
      reference images, Google Search grounding. For deep sections where the
      anatomy professor's craft matters most.
    - "flash_thinking" (CHUNKER_FALLBACK_MODEL + thinking): full creative brief
      as system instruction, anatomy reference images, thinking mode for quality.
      For standard sections — approaches Pro quality at Flash cost.
    """
    from google.genai import types

    model = model or GENERATOR_MODEL
    is_pro = (tier == "pro")

    # Build user prompt
    all_parts = []

    # Anatomy reference images — for both Pro and Flash-thinking
    ref_image_parts = build_creative_brief_image_parts()
    all_parts.extend(ref_image_parts)

    # Per-group content
    group_parts = build_user_prompt_v3(
        group=group,
        slide_number=slide_number,
        screenshots=screenshots,
        screenshots_dir=screenshots_dir,
        textbook_section=textbook_section,
        textbook_images=textbook_images,
        prior_groups=prior_groups,
    )
    all_parts.extend(group_parts)

    # Build generation config — differs by tier
    if is_pro:
        gen_config = {
            "temperature": 0.7,
            "max_output_tokens": 8192,
        }
        if cache_name:
            gen_config["cached_content"] = cache_name
        else:
            gen_config["system_instruction"] = build_system_instruction_text()
            gen_config["tools"] = [{"google_search": {}}]

    else:  # flash_thinking (standard sections)
        # Flash with thinking — full creative brief, thinking mode for quality.
        # Gets the same style transfer as Pro but at Flash cost + thinking tokens.
        gen_config = {
            "temperature": 0.6,
            "max_output_tokens": 4096,
            "system_instruction": build_system_instruction_text(),
            "thinking_config": types.ThinkingConfig(
                thinking_level="LOW",
            ),
        }

    try:
        response = client.models.generate_content(
            model=model,
            contents=all_parts,
            config=gen_config,
        )
        raw = response.text
    except Exception as e:
        print(f"  [error] Generation failed for '{group.title}': {e}")
        raw = f"[Generation failed: {e}]"

    # Post-processing: strip "your professor" meta-commentary + normalize URLs
    raw = _strip_professor_commentary(raw)

    # Validate GCS image URLs — remove any the writer hallucinated
    valid_gcs_urls = set()
    if textbook_images:
        for img in textbook_images:
            url = img.get("gcs_url", "")
            if url:
                valid_gcs_urls.add(url)
    raw = _validate_image_urls(raw, valid_gcs_urls)

    return parse_output(raw, slide_number=slide_number, group_name=group.title)


def _validate_image_urls(text: str, valid_gcs_urls: set[str]) -> str:
    """Remove hallucinated GCS image URLs from output.

    The writer sometimes invents OpenStax figure URLs that weren't in the
    provided list. This strips any GCS URL that isn't in the valid set,
    while keeping relative screenshots/ paths and valid GCS URLs.
    """
    def _check_url(match):
        full_match = match.group(0)  # ![caption](url)
        url = match.group(2)

        # Relative screenshots/ paths are always valid
        if url.startswith("screenshots/"):
            return full_match

        # GCS URLs must be in the valid set
        if "storage.googleapis.com" in url:
            if url in valid_gcs_urls:
                return full_match
            else:
                caption = match.group(1)
                return f"[{caption}]" if caption else ""

        # Raw Wikimedia/Wikipedia URLs are not valid — we upload to GCS
        # The writer should use the GCS URL we provided, not the source URL
        if "wikimedia.org" in url or "wikipedia.org" in url:
            caption = match.group(1)
            return f"[{caption}]" if caption else ""

        # Non-GCS URLs (shouldn't happen, but pass through)
        return full_match

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _check_url, text)
    return text


def _strip_professor_commentary(text: str) -> str:
    """Remove 'your professor' meta-commentary that leaks from the creative brief.

    Replaces phrases like 'Your professor glossed over this' with neutral
    alternatives. Applied as a safety net after generation.
    """
    # Replace "Your/your professor" phrases with neutral alternatives
    replacements = [
        (r"[Yy]our professor glossed over this", "This wasn't covered in much detail in the lecture"),
        (r"[Yy]our professor (?:didn't cover|skipped|barely mentioned) this", "This wasn't covered in the lecture"),
        (r"[Yy]our professor(?:'s| is| was| said| mentioned| didn't| spent| talks| talked)", "The lecture"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    # Strip echoed structured card instructions from slide sections
    text = re.sub(
        r"No real image available[^.]*?styled card\.\s*\n*",
        "",
        text,
    )
    # Strip "CARD CONTENT:\n" header if echoed
    text = re.sub(r"CARD CONTENT:\s*\n", "", text)

    # Normalize image URLs — fix hallucinated GCS paths for professor slides
    # Writer sometimes invents GCS URLs like /professor/screenshot_003.jpg
    # or /fxck-lectures-screenshots/screenshot_004.jpg
    # These should all be relative screenshots/ paths
    text = re.sub(
        r"https://storage\.googleapis\.com/fxck-lectures-screenshots/(?:professor/)?(screenshot_\d+\.jpg)",
        r"screenshots/\1",
        text,
    )

    # Verify OpenStax GCS URLs point to /openstax/ prefix (not stale job paths)
    # e.g. test-job-456/openstax_Figure_3.12.jpg → openstax/Figure_3.12.jpg
    def _fix_openstax_path(match):
        full = match.group(0)
        # Extract the figure ID from the path
        fig_match = re.search(r"(Figure_[\d.]+\.(?:jpg|png))", full)
        if fig_match:
            return f"https://storage.googleapis.com/{GCS_SCREENSHOTS_BUCKET}/openstax/{fig_match.group(1)}"
        return full

    text = re.sub(
        r"https://storage\.googleapis\.com/fxck-lectures-screenshots/[^/]+/openstax_(Figure_[\d.]+\.(?:jpg|png))",
        _fix_openstax_path,
        text,
    )

    return text


# ═══════════════════════════════════════════════════════════════════════════
# Lecture generator — V3 orchestrator
# ═══════════════════════════════════════════════════════════════════════════

def generate_lecture_v3(
    screenshots_json: str | Path,
    transcript_path: str | Path,
    lecture_slides_path: str | Path | None = None,
    subject: str | None = None,
    model: str | None = None,
    dry_run: bool = False,
    parallel: bool = True,
    job_id: str = "",
) -> tuple[list[GeneratedSection], list[SlideGroup]]:
    """Generate a complete lecture replacement from slides + transcript.

    V3 Pipeline:
      1. Flash planning: one call sees all slides + transcript → teaching plan (~15s)
      2. Textbook fetch: parallel per group (~25s)
      3. Context cache: create once for creative brief
      4. Pro generation: parallel per group (~40s)
      5. Clean up

    Args:
        screenshots_json: Path to screenshots.json from screenshot_extractor
        transcript_path: Path to transcript .txt file
        lecture_slides_path: Optional path to slides PDF (for Flash to see actual images)
        subject: Subject area hint for textbook search
        model: Override generation model
        dry_run: Print plan but don't call Pro
        parallel: Run Pro calls in parallel
        job_id: Job ID for GCS uploads
    """
    from google import genai
    from google.genai import types
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )
    model = model or GENERATOR_MODEL

    # ── Load inputs ──
    if screenshots_json:
        screenshots_path = Path(screenshots_json)
        with open(screenshots_path, "r", encoding="utf-8") as f:
            screenshots = json.load(f)
        screenshots_dir = screenshots_path.parent / "screenshots"
        print(f"  [load] {len(screenshots)} slides from {screenshots_path.name}")
    else:
        screenshots = []
        screenshots_dir = Path("data/output/screenshots")
        print(f"  [load] No slides — transcript-only mode")

    transcript_path = Path(transcript_path)
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    print(f"  [load] Transcript: {len(transcript.split())} words from {transcript_path.name}")

    # Load slide images for Flash planning (optional but improves grouping)
    slide_image_parts = None
    if screenshots_dir.exists():
        slide_image_parts = []
        for s in screenshots:
            img_path = screenshots_dir / s["image_filename"]
            if img_path.exists():
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                slide_image_parts.append(
                    types.Part.from_bytes(data=img_bytes, mime_type=mime)
                )
        print(f"  [load] {len(slide_image_parts)} slide images for Flash planning")

    # ══════════════════════════════════════════════════════════════
    # Stage 1: Flash planning — one call, sees everything
    # ══════════════════════════════════════════════════════════════
    print(f"\n  Stage 1: Flash lecture planning...")
    t0_plan = time.time()

    groups = plan_lecture(client, screenshots, transcript, slide_image_parts)

    # Assign term ownership
    _assign_term_ownership_v3(groups)

    t_plan = time.time() - t0_plan

    teaching_groups = [g for g in groups if g.depth != "skip"]
    skip_groups = [g for g in groups if g.depth == "skip"]

    print(f"\n{'='*60}")
    print(f"  TEACHING PLAN ({t_plan:.1f}s)")
    print(f"  {len(teaching_groups)} teaching groups, {len(skip_groups)} skipped")
    print(f"{'='*60}")
    for g in groups:
        depth_icon = {"deep": "+", "standard": "=", "bridge": "-", "skip": "x"}
        icon = depth_icon.get(g.depth, "?")
        terms = ", ".join(g.new_terms[:5]) if g.new_terms else ""
        slides_str = ",".join(str(s) for s in g.slide_indices[:5])
        if len(g.slide_indices) > 5:
            slides_str += f"...+{len(g.slide_indices)-5}"
        vs_label = {"professor_slide": "SLIDE", "openstax_figure": "FIGURE", "structured_card": "CARD"}.get(g.visual_strategy, "?")
        print(f"  [{icon}] {g.group_index+1}. {g.title} "
              f"(slides:{slides_str}) EI={g.ei_estimate}% ~{g.word_estimate}w [{vs_label}]"
              + (f" [{terms}]" if terms else ""))
    print(f"{'='*60}")

    if dry_run:
        for g in teaching_groups:
            print(f"\n  [{g.group_index+1}] {g.title}")
            print(f"    Depth: {g.depth}, EI: {g.ei_estimate}%")
            print(f"    Plan: {g.teaching_plan[:150]}...")
            print(f"    Transcript: {len(g.transcript_excerpt.split())}w")
            print(f"    Terms: {', '.join(g.key_terms[:8])}")
        print("\n  [dry-run] Done.")
        return [], groups

    # ══════════════════════════════════════════════════════════════
    # Stage 2: Textbook fetch — all teaching groups (no bridges to skip)
    # ══════════════════════════════════════════════════════════════
    print(f"\n  Stage 2: Textbook fetch (parallel)...")
    t0_tb = time.time()

    textbook_sections: dict[int, str] = {}
    textbook_imgs: dict[int, list[dict]] = {}

    tb_groups = teaching_groups  # All groups get textbook (merged groups already excluded)

    def _fetch_tb(g: SlideGroup):
        return g.group_index, fetch_textbook_section(
            topic_name=g.title,
            key_terms=g.key_terms,
            subject=subject,
        )

    def _fetch_imgs(g: SlideGroup):
        return g.group_index, fetch_textbook_images(
            topic_name=g.title,
            key_terms=g.key_terms,
            job_id=job_id,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        tb_futures = {executor.submit(_fetch_tb, g): g.group_index for g in tb_groups}
        img_futures = {executor.submit(_fetch_imgs, g): g.group_index for g in tb_groups}

        for future in as_completed(tb_futures):
            idx, text = future.result()
            textbook_sections[idx] = text

        for future in as_completed(img_futures):
            idx, imgs = future.result()
            textbook_imgs[idx] = imgs

    t_tb = time.time() - t0_tb
    print(f"  → {len(textbook_sections)} textbooks + "
          f"{sum(len(v) for v in textbook_imgs.values())} images in {t_tb:.1f}s"
          )

    # ══════════════════════════════════════════════════════════════
    # Stage 3: Two-tier generation (no bridges — merged by coordinator)
    # ══════════════════════════════════════════════════════════════
    # Tier 1 "pro":            deep groups → Pro, full creative brief, cache
    # Tier 2 "flash_thinking": standard groups → Flash + thinking + full brief

    deep_groups = [g for g in teaching_groups if g.depth == "deep"]
    standard_groups = [g for g in teaching_groups if g.depth == "standard"]

    print(f"\n  Stage 3: Two-tier generation ({'parallel' if parallel else 'sequential'})...")
    print(f"    Pro:            {len(deep_groups)} deep groups")
    print(f"    Flash+thinking: {len(standard_groups)} standard groups")

    # Create cache for Pro groups only
    cache_name = get_or_create_cache(client, model=model) if deep_groups else None
    t0_gen = time.time()

    sections: list[GeneratedSection | None] = [None] * len(teaching_groups)

    def _classify_tier(g: SlideGroup) -> tuple[str, str]:
        """Returns (model_name, tier_name) for a group."""
        if g.depth == "deep":
            return model, "pro"
        else:  # standard (no bridges — coordinator merges those)
            return CHUNKER_FALLBACK_MODEL, "flash_thinking"

    def _generate_one(g: SlideGroup, slide_num: int, use_model: str, tier_name: str):
        prior = [pg for pg in teaching_groups if pg.group_index < g.group_index]
        # Use original_group_index for textbook lookup (before reindexing)
        orig_idx = g.original_group_index if g.original_group_index >= 0 else g.group_index
        return slide_num, tier_name, generate_section_v3(
            client=client,
            group=g,
            slide_number=slide_num,
            screenshots=screenshots,
            screenshots_dir=screenshots_dir,
            textbook_section=textbook_sections.get(orig_idx, ""),
            textbook_images=textbook_imgs.get(orig_idx, []),
            prior_groups=prior if prior else None,
            cache_name=cache_name if tier_name == "pro" else None,
            model=use_model,
            tier=tier_name,
        )

    tier_labels = {"pro": "Pro", "flash_thinking": "F+T", "flash_bridge": "Fla"}

    if parallel:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for slide_num, g in enumerate(teaching_groups, start=1):
                gen_model, tier_name = _classify_tier(g)
                futures[executor.submit(
                    _generate_one, g, slide_num, gen_model, tier_name
                )] = slide_num

            for future in as_completed(futures):
                slide_num, tier_name, section = future.result()
                sections[slide_num - 1] = section
                label = tier_labels.get(tier_name, tier_name)
                print(f"    [{label}] Slide {slide_num}: {section.group_name} "
                      f"EI={section.ei_percent}% ({len(section.transcript.split())}w)")
    else:
        for slide_num, g in enumerate(teaching_groups, start=1):
            gen_model, tier_name = _classify_tier(g)
            _, _, section = _generate_one(g, slide_num, gen_model, tier_name)
            sections[slide_num - 1] = section
            label = tier_labels.get(tier_name, tier_name)
            print(f"    [{label}] Slide {slide_num}: {section.group_name} "
                  f"EI={section.ei_percent}% ({len(section.transcript.split())}w)")

    t_gen = time.time() - t0_gen

    # Filter Nones
    sections = [s for s in sections if s is not None]

    # Clean up cache
    if cache_name:
        clear_cache(client)

    t_total = time.time() - t0_plan
    total_words = sum(len(s.transcript.split()) for s in sections)
    print(f"\n  {'='*50}")
    print(f"  Done. {len(sections)} sections, {total_words} words in {t_total:.0f}s")
    print(f"    Planning:   {t_plan:.1f}s")
    print(f"    Textbooks:  {t_tb:.1f}s")
    print(f"    Generation: {t_gen:.1f}s ({len(deep_groups)} Pro + {len(standard_groups)} F+T)")
    print(f"  {'='*50}\n")

    return sections, groups
