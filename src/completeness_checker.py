"""Completeness checker — final pipeline stage (V3 architecture).

After the generator produces a document, this checker compares the full
transcript against the generated output and identifies content that didn't
make it into the document. For each missed item it judges exam relevance
(high/medium/low) and produces a short markdown patch that gets appended
to the relevant section.

Strategy A only: patches are appended to existing sections, never
regenerated. This preserves the carefully-written narrative and only
adds the missed facts as small follow-ups (sentences, callout boxes).
Only HIGH-severity misses are patched — medium/low are logged for the
dev log but not auto-applied.

Why this exists: even with Agent 2's structured extraction (named_examples,
professor_emphasis, tangents_to_skip) and the coordinator's director notes,
some content gets dropped during Pro generation. The checker is the safety
net that catches the remaining 15-20%.

Architecture:
    Generated sections + raw transcript
        ↓ (one Flash call, ~$0.02, ~15s)
    List of missed items with severity + patch markdown
        ↓ (HIGH-severity patches applied in-place)
    Updated sections with critical content restored

NOTE: This file replaces the old V1 grep-based completeness_checker that
operated on Stage 2 chunks. The V1 logic was based on key-term extraction
from regex chunks; V3 uses LLM comparison against the full transcript,
which catches semantic omissions (named pathogens, MCQs, exam signals)
that grep can't see.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

from src.config import (
    CHUNKER_FALLBACK_MODEL as FLASH_MODEL,
    GCP_PROJECT_ID,
    GCP_LOCATION,
    COMPLETENESS_TIMEOUT_S,
    call_with_timeout,
)
from src.generator_v2 import GeneratedSection


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class MissedItem:
    """One piece of content the audit found missing from the generated doc."""

    description: str          # What the prof said that didn't land
    severity: str             # "high", "medium", "low"
    section_index: int        # Best-fit section to attach the patch to (0-based)
    patch_markdown: str       # Ready-to-paste markdown to append
    reason: str               # Why this matters (or doesn't)


@dataclass
class LectureScore:
    """Flash's honest assessment of how well the lecture was delivered.

    Shown to the student as a shareable card at the end of the document — the
    meme-y "your professor scored X/100" moment that drives classroom sharing.

    All four score fields are 0-100 integers. The label maps to a 5-tier scale:
        0-20:   rough
        20-40:  ok
        40-60:  good
        60-80:  great
        80-100: excellent

    The comment is Flash's one-line observation specific to this lecture
    (a real tangent, overemphasis, or bright moment it noticed). Not a
    hardcoded template — every run gets a unique one.

    time_saved_min is Flash's estimate of how many minutes Klare saved the
    student vs watching the raw lecture. Flash estimates from transcript
    word count (~150 wpm speech) minus generated doc word count (~200 wpm
    reading).
    """

    overall: int              # 0-100
    clarity: int              # 0-100 — were concepts explained well?
    focus: int                # 0-100 — did the lecture stay on topic?
    efficiency: int           # 0-100 — signal-to-noise ratio
    label: str                # rough | ok | good | great | excellent
    comment: str              # One-line personalised observation
    time_saved_min: int       # Minutes Klare saved the student


# ═══════════════════════════════════════════════════════════════════════════
# Checker prompt — written as a creative brief, not a checklist
# ═══════════════════════════════════════════════════════════════════════════


def _build_checker_prompt(transcript: str, sections_summary: str) -> str:
    return f"""\
You're the final quality gate on a lecture-replacement document. The pipeline
has already done the heavy lifting — Flash agents extracted topics, a Pro
coordinator wrote the master plan, and parallel Pro writers produced the
sections you'll read below. The student is going to use this document instead
of watching the lecture, so anything exam-critical that didn't make it into
the output is a future MCQ they fail.

Your job: compare what the professor actually said against what we wrote.
Find what's missing. Decide which omissions matter.

The patterns that matter most are domain-agnostic — they apply equally to
medical, engineering, physics, business, or any theory-based lecture:

1. Practice questions the prof literally ran during the lecture. T/F
   rounds, multiple choice, "who thinks it's A, B, or C?", scenarios the
   prof asked the class to evaluate. These are direct exam previews. Each
   one should appear as a callout box in the document.

2. Named entities with applied context — a specific organism, drug,
   theorem, historical example, real-world case, named experiment, named
   product, or worked example the prof tied to a concrete consequence.
   "Bacillus cereus in rice" or "the Me 262 fighter jet" or "rolled vs
   machined threads" or "the Millikan oil drop experiment" all qualify.
   These are the concrete hooks students remember and exams test.

3. Memory hooks and exam signals — anything the prof flagged with "you'll
   need to know this", "remember this", "this is on the exam", "saved
   exam marks", "watch the trap here", "this trips students up". Direct
   signals from the person writing the exam.

4. Multi-slide teaching moments where the prof spent significant time
   (more than ~2 minutes) walking through a comparison, contrast, or
   worked example with class engagement. If the prof asked the class to
   pick between two options or vote on a question, that's a sign the
   topic mattered enough to test.

For each missed item, decide severity:

HIGH — content the prof literally tested in lecture (T/F, MCQ, class poll),
content the prof spent significant time on with engagement, named entities
the prof tied to applied context, items the prof verbally flagged as exam
material. These get patched.

MEDIUM — useful background, prof spent time on it, but not direct exam
material. These get logged for human review but not auto-patched.

LOW — trivia, asides, prof's personal anecdotes, things he himself said
were out of scope. Not patched.

For each HIGH-severity item, write a TIGHT markdown patch — 1-2 sentences
max for facts, or a single blockquote callout for MCQs. No preamble, no
"it's worth noting that" wind-ups. Match the document's voice: colloquial,
tutoring, no "the professor said" meta-commentary. Just teach the missed
fact in the fewest words that work.

For MEDIUM and LOW items, leave patch_markdown as an empty string — they
won't be applied, no need to write them. Only HIGH items need a patch.

Patch format examples:

For a missed named example:
"Worth knowing: *Bacillus cereus* is the classic culprit for food poisoning
in cooked rice and grains. Cooking kills competing bacteria but the
endospores survive — when the food cools, the spores germinate and the
bacterium grows uncontested."

For a missed MCQ (use a blockquote callout):
"> **Quick check.** Which is the only group of prokaryotes that contains
> N-acetyltalosaminuronic acid in their cell wall?
> Answer: **Archaea** — it's the defining sugar of pseudomurein."

For a missed mechanism detail:
"One subtle mechanism worth flagging: when the tetrapeptide chain is first
synthesized, it's actually a *pentapeptide* with an extra terminal D-alanine.
That fifth amino acid gets cleaved off during cross-linking — it's the
chemical lever the cross-link reaction uses."

GENERATED DOCUMENT (what we wrote):

{sections_summary}

PROFESSOR'S RAW TRANSCRIPT:

{transcript}

ALONGSIDE the missed-item audit, give the student a short Lecture Score.
This is the meme-y summary card students share with classmates at the end
of the document. It needs to feel honest, specific, and a little funny —
not clinical.

Score the lecture on three dimensions, each 0-100:

- clarity: were concepts actually explained or just named? Does the prof
  build from concrete to abstract, or define-first then hope you catch up?
  Deduct for jargon without setup, mumbled key terms, contradictory
  statements ("you don't need to memorise this but you need to understand").

- focus: did the lecture stay on topic? Deduct heavily for long history
  digressions, personal anecdotes unrelated to the concept, tangents that
  don't loop back. A lecture that spends 12 minutes on the history of
  penicillin before touching peptidoglycan is a focus score in the 20s.

- efficiency: signal-to-noise ratio — per minute of lecture, how much
  exam-useful content got delivered? A prof who rambles for an hour to
  teach what could be said in 20 minutes is ~30 on efficiency.

Compute overall as the simple average of the three, rounded to integer.

Map overall to a label (be honest, most professors land in ok/good):
  0-20   → "rough"      (genuine train wreck)
  20-40  → "ok"         (below average, the common case for 'bad prof')
  40-60  → "good"       (middle of the pack, most lectures)
  60-80  → "great"      (solid lecturer who builds concepts)
  80-100 → "excellent"  (rare, watch-this-twice quality)

Write a ONE-LINE comment that's specific to THIS lecture — quote a real
tangent, overemphasis, or bright moment you noticed. Not "the professor
rambled" but "spent 12 minutes on the history of penicillin before
touching peptidoglycan structure." Or "kept switching between 'fimbriae'
and 'pili' as if they were the same thing." Or on a good lecture:
"Used the Timmy-buys-oranges framing before naming the function — nice."
One sentence, under 20 words. No starting with "the professor" — just
state what happened.

Estimate time_saved_min honestly: transcript word count divided by 150
(speech pace) minus generated doc word count divided by 200 (reading
pace), rounded to the nearest integer. If the numbers suggest Klare
saved negative time (rare — only on very short lectures), return 0.

Output JSON only, this shape:
{{
  "missed_items": [
    {{
      "description": "Brief description of what was missed",
      "severity": "high",
      "section_index": 11,
      "patch_markdown": "Worth knowing: *Bacillus cereus*...",
      "reason": "Named pathogen with clinical food-safety context, exam favorite for MCQs"
    }}
  ],
  "lecture_score": {{
    "overall": 34,
    "clarity": 28,
    "focus": 40,
    "efficiency": 33,
    "label": "ok",
    "comment": "Spent 12 minutes on the history of penicillin before touching peptidoglycan structure.",
    "time_saved_min": 87
  }}
}}

Be honest about severity. Patching low-importance trivia bloats the
document. Missing high-importance content fails the student. Most
missed items in a typical run will be medium or low — that's expected.
A typical lecture has 1-4 high-severity misses worth patching.

Be honest about the score too. A "clear" 50-score professor who just
isn't flashy is more useful signal than scoring everyone 30 for meme
value. Students compare scores across their subjects."""


# ═══════════════════════════════════════════════════════════════════════════
# Section summary — what the checker sees of the generated doc
# ═══════════════════════════════════════════════════════════════════════════


def _build_sections_summary(sections: list[GeneratedSection]) -> str:
    """Concatenate sections in a form the checker can scan efficiently.

    We send the full transcript text per section (not a summary) so the
    checker can verify what's actually covered, not just topic headings.
    """
    blocks = []
    for i, s in enumerate(sections):
        blocks.append(
            f"=== Section {i}: {s.group_name} (EI {s.ei_percent}%) ===\n"
            f"{s.transcript.strip()}"
        )
    return "\n\n".join(blocks)


# ═══════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════


def check_completeness(
    sections: list[GeneratedSection],
    transcript: str,
    apply_patches: bool = True,
) -> tuple[list[GeneratedSection], list[MissedItem], LectureScore | None]:
    """Run the completeness check and (optionally) apply HIGH-severity patches.

    Args:
        sections: The generated document, in reading order.
        transcript: The full professor transcript.
        apply_patches: If True, append patch_markdown to matching sections in-place.

    Returns:
        (updated_sections, missed_items, lecture_score)
        missed_items includes ALL severities for logging — only HIGH ones
        get patched into the sections.
        lecture_score is None if Flash failed or skipped the scoring block.
    """
    if not sections:
        return sections, [], None

    print(f"  [completeness] Checking {len(sections)} sections "
          f"against {len(transcript.split())}w transcript...")
    t0 = time.time()

    from google import genai
    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )
    sections_summary = _build_sections_summary(sections)
    prompt = _build_checker_prompt(transcript, sections_summary)

    try:
        from google.genai import types as genai_types
        response = call_with_timeout(
            lambda: client.models.generate_content(
                model=FLASH_MODEL,
                contents=prompt,
                config={
                    "temperature": 0.2,
                    # 8k output gives room for 4-8 patches even when thinking
                    # tokens (which count separately on Gemini 3 Flash) eat
                    # into the budget. Real-world cost still under $0.05.
                    "max_output_tokens": 8192,
                    # Cap thinking so output has room. Without this cap,
                    # Flash sometimes burns 5k+ thinking tokens and only
                    # has 3k left for the actual JSON, hitting MAX_TOKENS
                    # mid-array.
                    "thinking_config": genai_types.ThinkingConfig(thinking_budget=2048),
                },
            ),
            timeout=COMPLETENESS_TIMEOUT_S,
            label="completeness.check",
        )
        raw = (response.text or "").strip()
        if not raw:
            # Empty response — Flash returned no content (rate limit, content
            # filter, or the model returned no candidates). Skip cleanly.
            print(f"  [completeness] Empty response from Flash — skipping check")
            return sections, [], None
    except Exception as e:
        print(f"  [completeness] Flash call failed: {e} — skipping check")
        return sections, [], None

    # Parse JSON (handle markdown wrappers + trailing commas + truncation)
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try lenient regex + trailing-comma fix
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", match.group(0)))
            except json.JSONDecodeError:
                data = None
        else:
            data = None

        # Last-resort fallback: json_repair handles truncation + bad escapes
        if data is None:
            try:
                from src.json_repair import extract_json
                data = extract_json(cleaned, expect_array=False)
                if not data:
                    print(f"  [completeness] All JSON parsers failed — skipping check")
                    print(f"  [completeness] Raw (first 300): {raw[:300]}")
                    return sections, [], None
            except Exception as e:
                print(f"  [completeness] JSON repair failed: {e} — skipping check")
                return sections, [], None

    raw_items = data.get("missed_items", [])
    missed: list[MissedItem] = []
    for item in raw_items:
        try:
            missed.append(MissedItem(
                description=item.get("description", "").strip(),
                severity=item.get("severity", "low").strip().lower(),
                section_index=int(item.get("section_index", 0)),
                patch_markdown=item.get("patch_markdown", "").strip(),
                reason=item.get("reason", "").strip(),
            ))
        except (TypeError, ValueError):
            continue

    high = [m for m in missed if m.severity == "high"]
    med = [m for m in missed if m.severity == "medium"]
    low = [m for m in missed if m.severity == "low"]

    elapsed = time.time() - t0
    print(f"  [completeness] {len(missed)} items found in {elapsed:.0f}s "
          f"({len(high)} high, {len(med)} medium, {len(low)} low)")

    # Apply HIGH-severity patches only (Strategy A)
    if apply_patches and high:
        for m in high:
            if 0 <= m.section_index < len(sections) and m.patch_markdown:
                target = sections[m.section_index]
                target.transcript = (
                    target.transcript.rstrip()
                    + "\n\n"
                    + m.patch_markdown.strip()
                    + "\n"
                )
                print(f"  [completeness] patched section {m.section_index} "
                      f"({target.group_name[:40]}): {m.description[:60]}")

    # Log medium/low for human review (don't auto-apply)
    if med:
        print(f"  [completeness] {len(med)} medium-severity items NOT patched "
              f"(logged for review):")
        for m in med[:5]:
            print(f"    - section {m.section_index}: {m.description[:80]}")

    # Parse lecture_score (optional — Flash might skip it if prompt truncated)
    lecture_score: LectureScore | None = None
    raw_score = data.get("lecture_score")
    if isinstance(raw_score, dict):
        try:
            overall = int(raw_score.get("overall", 0))
            # Derive label from overall if Flash didn't return one or returned
            # something outside our 5-tier scale (trust the number over the word)
            valid_labels = {"rough", "ok", "good", "great", "excellent"}
            flash_label = str(raw_score.get("label", "")).strip().lower()
            if flash_label not in valid_labels:
                if overall < 20:
                    flash_label = "rough"
                elif overall < 40:
                    flash_label = "ok"
                elif overall < 60:
                    flash_label = "good"
                elif overall < 80:
                    flash_label = "great"
                else:
                    flash_label = "excellent"

            lecture_score = LectureScore(
                overall=max(0, min(100, overall)),
                clarity=max(0, min(100, int(raw_score.get("clarity", 0)))),
                focus=max(0, min(100, int(raw_score.get("focus", 0)))),
                efficiency=max(0, min(100, int(raw_score.get("efficiency", 0)))),
                label=flash_label,
                comment=str(raw_score.get("comment", "")).strip()[:200],
                time_saved_min=max(0, int(raw_score.get("time_saved_min", 0))),
            )
            print(f"  [completeness] lecture_score: {lecture_score.overall}/100 "
                  f"({lecture_score.label}) — {lecture_score.comment[:60]}")
        except (TypeError, ValueError) as e:
            print(f"  [completeness] lecture_score parse failed: {e} — skipping score")

    return sections, missed, lecture_score


# ═══════════════════════════════════════════════════════════════════════════
# Debug helper — save full audit to disk
# ═══════════════════════════════════════════════════════════════════════════


def save_audit_log(missed: list[MissedItem], output_path) -> None:
    """Persist the full audit (all severities) to disk for the dev log."""
    payload = {
        "summary": {
            "total": len(missed),
            "high": sum(1 for m in missed if m.severity == "high"),
            "medium": sum(1 for m in missed if m.severity == "medium"),
            "low": sum(1 for m in missed if m.severity == "low"),
        },
        "items": [
            {
                "severity": m.severity,
                "section_index": m.section_index,
                "description": m.description,
                "reason": m.reason,
                "patch_markdown": m.patch_markdown,
            }
            for m in missed
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
