"""Single-writer pipeline — one Gemini Pro call replaces Agent 1 + Agent 2 +
Coordinator + Agent 3 + parallel writers.

Two entry points:
    generate_lecture_single()           — blocking, returns final tuple
    generate_lecture_single_streaming() — generator, yields sections as
        Pro completes each one (for progressive-rendering UX).

Architecture:
    transcript + slide images + creative brief
                    ↓
        ONE Gemini Pro call (with Google Search grounding + thinking)
                    ↓
            Structured JSON (slides + transcript)
                    ↓
        list[GeneratedSection] for downstream pipeline

Why this exists: empirical testing showed multi-agent decomposition was
solving a constraint (long-form coherence on older models) that no longer
applies with Gemini 3 Pro. Single-writer matches/beats multi-agent on
quality while running 5-7× faster and 5× cheaper.

Drop-in replacement for generate_lecture_v3() — same return signature,
same downstream contract. Pipeline can swap implementations behind a
feature flag (USE_SINGLE_WRITER env var).

Long-lecture handling: not yet implemented. Single-writer fits comfortably
within Gemini 3 Pro's 32k output cap for lectures up to ~50 slides /
~16k transcript words. For longer lectures, will need chunked-sequential
mode (write first half, then second half with first-half output as
context). Empirically not yet needed for typical undergraduate lectures.
"""
import json
import time
from pathlib import Path

from google import genai
from google.genai import types

from src.config import (
    GCP_PROJECT_ID,
    GCP_LOCATION,
    GENERATOR_MODEL,
)
from src.generator_v2 import GeneratedSection, SlideCard
from src.json_repair import extract_json


# ═══════════════════════════════════════════════════════════════════════════
# Creative brief — written for Pro as a smart writer, not as a rules list
# ═══════════════════════════════════════════════════════════════════════════


def _build_brief(subject: str | None = None) -> str:
    """The single piece of guidance Pro reads. Mirror of how a smart
    writer would brief a freelance ghost-writer.
    """
    subject_label = subject or "medical/biomed/science"

    return f"""\
You're writing a lecture-replacement document for a {subject_label} student.
The student will read your output instead of watching a 2-hour lecture from
a professor who rambles, buries the exam-critical stuff, and yaps on the
easy stuff. You're the personal tutor talking to a friend.

VOICE — colloquial, warm, contractions always. Use "steal" not "takes a
portion", "hijack" not "commandeer", "pop open" not "lyse." Read like a
smart older sibling explaining a hard concept over coffee, not a textbook.

PHILOSOPHY — concrete-then-abstract. Never start a section with "X is
a Y that..." Start with WHY they should care or HOW it works. The
scientific term shows up AFTER the student understands what it does.
The student MUST walk away with the technical terminology so they can
write it on the exam — if you describe a process colloquially without
ever NAMING it (e.g. saying "wraps itself in a bubble of host membrane"
without ever saying "budding"), that's a bug worth fixing.

QUESTION-ANSWER FLOW — every sentence should answer the question the
previous sentence raised. The anatomy professor's best transcripts have
this property: sentence N creates curiosity, sentence N+1 satisfies it,
sentence N+1 raises the next question. If you write a sentence that
doesn't answer an implicit question AND doesn't raise one, delete it.
It's filler.

ABSTRACT MECHANISMS — when teaching invisible molecular/chemical
machinery (electron transport, protein folding, signal cascades, enzyme
kinetics), the anatomy prof's technique is: (a) functional description
— what each component DOES in sequence; (b) sequential framing ("as X
happens, Y happens"); (c) numerical/temporal anchors (how many, how
long, how much); (d) consequence linking (what this produces, why it
matters). Avoid extended visual analogies like "waterwheels" or "dams"
— they can mislead. A molecular turbine (ATP synthase) can be called a
turbine because biologists actually call it that; don't invent new
analogies.

EXAMPLES, NOT ANALOGIES — the anatomy prof uses real examples from the
domain (a sit-up IS a concentric contraction; lifting a car IS an
isometric contraction). She rarely reaches for analogies (X is like Y
where Y is unrelated). Prefer examples from the domain itself:
"forging a horseshoe on an anvil" beats "like squashing a marshmallow"
because the horseshoe actually IS forging. Two kinds she uses:
generative examples (placed AFTER the framework to introduce a
subdivision — "Let's use the sit-up as an example...") and
confirmatory examples (placed at the end to test understanding — "For
example, trying to lift a car..."). Keep analogies rare and only when
no domain example exists.

EARNED WORD COUNT — every sentence must teach a new beat. Don't restate
what you just said in different words. Don't hedge ("perhaps acidic or
non-polar"). Don't name things without teaching them ("This interaction
forms a temporary Enzyme-Substrate Complex" — if you're just naming,
delete the sentence and use the name inline). Don't negate concepts the
student never proposed ("This is not a rigid lock-and-key fit" — they
don't know about lock-and-key yet). Trust student intelligence on simple
categorizations — if three muscle types differ by location/control/
mechanism, one dense paragraph covers it, not three paragraphs with
hooks. When in doubt, delete. 200 earned words beat 400 padded ones.

NO META-COMMENTARY — never say "this is important," "this is complex,"
"this is commonly tested," "students frequently lose marks by X," or
"if you've studied this before, you likely learned Y." Anatomy prof
never does this. Just explain it well and let the student recognize
importance from the depth you give it. Framing something as "exam
critical" is a tell that you don't trust the explanation to land on
its own.

DEPTH INVERSION — professors get depth wrong. They ramble 800 words
on simple categorizations and rush 200 words on the complex mechanism
students actually struggle with. Invert this. If the prof spent a long
time on something and it's easy, condense aggressively. If the prof
skimmed something and it's a complex mechanism or standard curriculum
topic, expand into real depth. The amount of transcript tells you
nothing about how much space a topic deserves.

FORWARD MOMENTUM — never end a section with a summary paragraph
("In conclusion, we've covered…"). Beyond that, handle transitions
honestly. When two sections are genuinely causally or sequentially
linked (sliding filament → contraction types; pathogen entry →
replication → disease), the last sentence of one can and should open
the next — a real door, not a template. When two sections are parallel
categories (rolling vs forging, the 4 tissue types, Baltimore classes
I through VII), don't invent a fake bridge. "Rolling has limits, so
we need forging" is misleading — they're parallel tools, not a
dependency. In those cases, just… end the section cleanly and let the
next heading do the work. The rule is never "every section must seam
into the next"; it's "no section ends on a dead summary, and no section
opens with a cold definition when a real transition exists." If the
transition would be forced, skip it.

DENSITY — don't faithfully reproduce every point. Trim history, anecdotes,
repeated easy concepts. Where the prof skimmed exam-critical content
(Baltimore classes, fimbriae disease list, named entities), teach in real
depth — slides + standard curriculum, not just prof emphasis. The slides
are an entry-pass for full-depth teaching; if a topic is on a slide and
the prof skimmed, expand it properly using your knowledge.

PRACTICE QUESTIONS — if the transcript contains T/F rounds, MCQs,
practice questions, review quizzes, or exam-style items the professor
runs through (even briefly), every single item must land in the
document. Weave them into the relevant teaching section where natural,
or drop a short "worth drilling" callout at the end of the section
with the question and the answer explained in 1-2 sentences. Don't let
a 7-item T/F round collapse into "the professor reviewed key concepts"
— each item is a specific exam-testable fact and the student loses
marks if it's missing.

CALLBACKS — name concepts, not section numbers. Never write "as discussed
in Section 3" — write "the capsid we covered earlier." Real cross-references
across sections are good; numbered references are robotic.

ACCURACY — when you mention named pathogens, drug mechanisms, clinical
diseases, specific molecular structures, or named theories, verify with
web search if you're not 100% certain. Wrong clinical/technical facts
lose students marks. Don't make up gene names, enzyme names, or
classifications. The Google Search tool is enabled — use it for anything
you're not sure about.

SLIDE-CONTENT MATCHING (critical). The slide images you see below are
the actual screenshots from the lecture deck. Each one shows specific
content. Two cases:

(A) The transcript topic IS shown on a specific slide — your image_ref
    must point to that exact slide. Don't pick the next sequential
    number; match content. Wrong image_ref makes the frontend show a
    mismatched diagram.

(B) The transcript topic is discussed by the prof but NOT shown on any
    slide (the prof talked through it without flipping). For these,
    set card_type to "text_only" and leave image_ref as an empty string.
    The frontend renders text-only callouts cleanly. Don't invent or
    reuse an unrelated slide image.

OUTPUT FORMAT — strict JSON, two top-level arrays:

  "slides": [
    {{
      "slide_id": "1",                    // matches transcript slide_number
      "title": "Section title",           // 4-8 words
      "card_type": "professor_slide" or "text_only",
      "image_ref": "screenshots/screenshot_001.jpg" or "",
      "bullet_points": [                  // 2-4 short scannable bullets
        "Brief specific fact",
        "Another concrete point"
      ],
      "exam_tip": "One sentence on what to remember for the exam.",
      "ei_percent": 85
    }}
  ],
  "transcript": [
    {{
      "slide_number": 1,                  // matches slide_id (as integer)
      "title": "Section title",           // matches slide title
      "narrative": "Full prose, 250-500 words. Anatomy-prof voice. **Bold** key terms on first use.",
      "ei_percent": 85,
      "ei_reasoning": "One sentence: why this EI%."
    }}
  ]

Every slide MUST have ≥2 bullet_points and a real exam_tip — these render
as the student's study card. Empty arrays make the card look broken.

LENGTH — produce 14-22 paired sections covering the full lecture. Total
narrative 4,000-6,000 words. Deep sections (multi-step mechanisms,
exam-critical) get 400-600 words. Standard sections (single concept) get
200-300 words. Don't pad; don't compress what matters.

Identify the spine first (what's the ONE through-line of this lecture?),
plan sections in your head, then write. One author, full document in
mind, real callbacks across sections.

OUTPUT JSON ONLY — no preamble, no markdown fences, just the raw JSON
object starting with {{ and ending with }}.
"""


# ═══════════════════════════════════════════════════════════════════════════
# Main entry point — drop-in replacement for generate_lecture_v3
# ═══════════════════════════════════════════════════════════════════════════


def generate_lecture_single(
    screenshots_json: str | Path,
    transcript_path: str | Path,
    subject: str | None = None,
    model: str | None = None,
    job_id: str = "",
    enable_grounding: bool = True,
) -> tuple[list[GeneratedSection], list]:
    """Single-writer pipeline. One Pro call writes the entire document.

    Drop-in replacement for generate_lecture_v3. Returns the same
    (sections, groups) tuple — groups is empty since there's no
    Agent 1 grouping step.

    Args:
        screenshots_json: Path to screenshots.json from screenshot_extractor.
            If None or empty, runs transcript-only (no slide images).
        transcript_path: Path to transcript .txt file.
        subject: Subject area hint (e.g. "microbiology", "engineering").
            Adjusts the brief's tone but not behavior.
        model: Override generation model. Defaults to GENERATOR_MODEL
            (gemini-3.1-pro-preview).
        job_id: Job ID for logging. Currently unused but kept for API
            compatibility with generate_lecture_v3.
        enable_grounding: Enable Google Search grounding for fact checking.
            Adds ~30s wall time and ~$0.05-0.10 cost. Default True.

    Returns:
        (sections, groups) where sections is list[GeneratedSection] and
        groups is an empty list (no Agent 1 step in this pipeline).
    """
    transcript_text = Path(transcript_path).read_text(encoding="utf-8")

    # Load slide images if available
    screenshots = []
    if screenshots_json:
        try:
            with open(screenshots_json, encoding="utf-8") as f:
                screenshots = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"  [single-writer] Could not load screenshots: {e}")
            screenshots = []

    # Resolve screenshots dir (where the actual JPG files live)
    screenshots_dir = None
    if screenshots:
        # screenshots.json typically sits next to the screenshots/ folder
        ss_path = Path(screenshots_json)
        for candidate in (ss_path.parent / "screenshots", ss_path.parent):
            if candidate.exists() and (candidate / screenshots[0].get("image_filename", "")).exists():
                screenshots_dir = candidate
                break

    print(f"  [single-writer] Loaded {len(transcript_text.split())} words transcript, "
          f"{len(screenshots)} slide images")
    if not screenshots_dir:
        print(f"  [single-writer] WARN: screenshots dir not found, slides will not be passed as images")

    # ── Build the prompt ──
    brief = _build_brief(subject)
    parts: list = [types.Part.from_text(text=brief)]
    parts.append(types.Part.from_text(
        text="\n\n=== PROFESSOR'S TRANSCRIPT ===\n\n" + transcript_text
    ))

    # Add each slide as multimodal Part with description label
    images_added = 0
    if screenshots_dir:
        for s in screenshots:
            img_path = screenshots_dir / s["image_filename"]
            if not img_path.exists():
                continue
            try:
                img_bytes = img_path.read_bytes()
            except OSError:
                continue
            full_ref = f"screenshots/{s['image_filename']}"
            label = (
                f"\n\n=== SLIDE: {full_ref} "
                f"[{s.get('timestamp_display', '')}] "
                f"(use this full path in image_ref — include the 'screenshots/' prefix) ==="
            )
            parts.append(types.Part.from_text(text=label))
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            images_added += 1

    parts.append(types.Part.from_text(text=
        "\n\nNow: identify the spine, plan sections, fact-check uncertain "
        "claims via search if needed, then write the full document with "
        "bullets and exam tips for every section. Output JSON only."
    ))

    print(f"  [single-writer] Prompt: {len(parts)} parts, {images_added} images")

    # ── Call Pro ──
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    model_name = model or GENERATOR_MODEL

    config_kwargs = {
        "temperature": 0.7,
        "max_output_tokens": 32768,  # Hard ceiling for Gemini 3 Pro
        "thinking_config": types.ThinkingConfig(thinking_budget=8192),
    }
    if enable_grounding:
        config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    start_time = time.time()
    resp = client.models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    elapsed = time.time() - start_time

    # ── Log usage + cost ──
    output = resp.text or ""
    finish = resp.candidates[0].finish_reason if resp.candidates else None
    usage = resp.usage_metadata if hasattr(resp, "usage_metadata") else None

    grounding_uses = 0
    if (resp.candidates and resp.candidates[0].grounding_metadata
        and hasattr(resp.candidates[0].grounding_metadata, "grounding_chunks")
        and resp.candidates[0].grounding_metadata.grounding_chunks):
        grounding_uses = len(resp.candidates[0].grounding_metadata.grounding_chunks)

    if usage:
        in_cost = usage.prompt_token_count / 1_000_000 * 2.50
        out_cost = usage.candidates_token_count / 1_000_000 * 10.00
        thinking = usage.thoughts_token_count if hasattr(usage, "thoughts_token_count") else 0
        think_cost = (thinking or 0) / 1_000_000 * 10.00
        print(f"  [single-writer] {elapsed:.0f}s, finish={finish}, "
              f"in={usage.prompt_token_count:,}t, out={usage.candidates_token_count:,}t, "
              f"think={thinking:,}t, grounding_uses={grounding_uses}, "
              f"cost=${in_cost+out_cost+think_cost:.3f}")

    # ── Parse JSON ──
    parsed = extract_json(output, expect_array=False)
    if not parsed or not isinstance(parsed, dict):
        print(f"  [single-writer] ERROR: failed to parse JSON output")
        print(f"  [single-writer] Raw output (first 500 chars): {output[:500]}")
        return [], []

    raw_slides = parsed.get("slides", [])
    raw_transcript = parsed.get("transcript", [])

    if not raw_slides or not raw_transcript:
        print(f"  [single-writer] ERROR: empty slides/transcript in output")
        return [], []

    print(f"  [single-writer] Generated {len(raw_slides)} slides + "
          f"{len(raw_transcript)} sections, "
          f"{sum(len(t.get('narrative','').split()) for t in raw_transcript)} words")

    # ── Convert to GeneratedSection objects ──
    sections = _convert_to_sections(raw_slides, raw_transcript)
    return sections, []


def _convert_to_sections(
    raw_slides: list[dict],
    raw_transcript: list[dict],
) -> list[GeneratedSection]:
    """Convert single-writer's JSON output into GeneratedSection objects
    that downstream pipeline (assemble_api_response, completeness_checker)
    expects.
    """
    # Index slides by slide_id for matching
    slides_by_id = {str(s.get("slide_id", "")).lower(): s for s in raw_slides}

    sections = []
    for t in raw_transcript:
        sn = t.get("slide_number", t.get("slide_id", len(sections) + 1))
        try:
            slide_num = int(sn)
        except (ValueError, TypeError):
            slide_num = len(sections) + 1

        # Find matching slide card
        matching_slide = (
            slides_by_id.get(str(sn).lower())
            or slides_by_id.get(str(slide_num).lower())
            or {}
        )

        # Map our card_type to SlideCard's accepted vocabulary.
        # text_only → diagram (a bullet-point card without an image)
        raw_card_type = matching_slide.get("card_type", "professor_slide")
        if raw_card_type == "text_only":
            card_type = "diagram"
        elif raw_card_type in ("professor_slide", "diagram"):
            card_type = raw_card_type
        else:
            card_type = "professor_slide"

        slide_card = SlideCard(
            slide_id=str(matching_slide.get("slide_id", slide_num)),
            title=matching_slide.get("title", t.get("title", "")),
            card_type=card_type,
            image_ref=matching_slide.get("image_ref", ""),
            bullet_points=matching_slide.get("bullet_points", []) or [],
            exam_tip=matching_slide.get("exam_tip", "") or "",
            ei_percent=int(matching_slide.get("ei_percent", t.get("ei_percent", 50))),
        )

        # Build the slide_content markdown blob (for backward compat with
        # GeneratedSection.slide_content field — used by some downstream code)
        slide_content_md = _slide_card_to_markdown(slide_card, slide_num)

        # Embed image reference inside narrative if professor_slide and we
        # have a real image_ref. The frontend renders this inline.
        narrative = t.get("narrative", "")
        if (slide_card.card_type == "professor_slide"
            and slide_card.image_ref
            and slide_card.image_ref not in narrative):
            # Prepend the image so it renders at the top of the section
            narrative = f"![{slide_card.title}]({slide_card.image_ref})\n\n{narrative}"

        sections.append(GeneratedSection(
            slide_number=slide_num,
            slide_content=slide_content_md,
            slide_cards=[slide_card],
            transcript=narrative,
            ei_percent=int(t.get("ei_percent", matching_slide.get("ei_percent", 50))),
            ei_reasoning=t.get("ei_reasoning", ""),
            group_name=t.get("title", matching_slide.get("title", "")),
            raw_output="",  # Single-writer doesn't have per-section raw output
        ))

    return sections


# ═══════════════════════════════════════════════════════════════════════════
# Streaming variant — for progressive-rendering UX (ChatGPT-style section
# reveals). Uses Gemini's generate_content_stream with an incremental JSON
# scanner that detects complete transcript[i] objects as tokens arrive.
# ═══════════════════════════════════════════════════════════════════════════


class _ArrayObjectStreamer:
    """Incremental scanner: watches streaming JSON text for complete objects
    inside a named top-level array (e.g. "transcript": [...], "slides": [...]).

    Handles string literals (including escaped quotes/braces), brace counting,
    and only begins parsing once the named key + opening [ have been seen.

    Usage:
        streamer = _ArrayObjectStreamer(key="transcript")
        for chunk in response_stream:
            for obj in streamer.feed(chunk.text or ""):
                handle(obj)
    """

    def __init__(self, key: str):
        self.needle = f'"{key}"'
        self.buffer = ""
        self.pos = 0
        self.found_key = False
        self.found_array = False
        self.closed = False
        self.in_string = False
        self.escape = False
        self.depth = 0
        self.obj_start = -1

    def feed(self, chunk: str) -> list[dict]:
        if self.closed or not chunk:
            return []
        self.buffer += chunk
        results: list[dict] = []

        # Phase 1 — find the array key (e.g. `"transcript"`).
        if not self.found_key:
            idx = self.buffer.find(self.needle, self.pos)
            if idx < 0:
                # Keep buffer trim in the not-yet-found phase
                return results
            self.pos = idx + len(self.needle)
            self.found_key = True

        # Phase 2 — find the opening '[' after the key.
        if not self.found_array:
            while self.pos < len(self.buffer):
                ch = self.buffer[self.pos]
                if ch == '[':
                    self.found_array = True
                    self.pos += 1
                    break
                self.pos += 1
            if not self.found_array:
                return results

        # Phase 3 — brace-count inside the array. Each time depth returns to 0
        # after rising, we have a completed top-level object.
        while self.pos < len(self.buffer):
            ch = self.buffer[self.pos]

            if self.in_string:
                if self.escape:
                    self.escape = False
                elif ch == '\\':
                    self.escape = True
                elif ch == '"':
                    self.in_string = False
                self.pos += 1
                continue

            if ch == '"':
                self.in_string = True
                self.pos += 1
                continue

            if ch == '{':
                if self.depth == 0:
                    self.obj_start = self.pos
                self.depth += 1
                self.pos += 1
                continue

            if ch == '}':
                self.depth -= 1
                self.pos += 1
                if self.depth == 0 and self.obj_start >= 0:
                    raw = self.buffer[self.obj_start:self.pos]
                    try:
                        results.append(json.loads(raw))
                    except json.JSONDecodeError:
                        # Malformed slice — skip; the full-parse at end will
                        # still recover the canonical output.
                        pass
                    self.obj_start = -1
                continue

            if ch == ']' and self.depth == 0:
                self.closed = True
                self.pos += 1
                return results

            self.pos += 1

        return results


def generate_lecture_single_streaming(
    screenshots_json: str | Path,
    transcript_path: str | Path,
    subject: str | None = None,
    model: str | None = None,
    job_id: str = "",
    enable_grounding: bool = True,
):
    """Streaming variant of generate_lecture_single.

    Generator that yields events as Pro writes:

        {"kind": "section", "index": int, "transcript_item": dict,
         "slide_card": dict | {}}       # each completed transcript[i]

        {"kind": "done", "sections": list[GeneratedSection],
         "groups": []}                  # final canonical output

    The mid-stream "section" events let the frontend render sections one by
    one. The final "done" event carries the authoritative assembled list
    (same shape generate_lecture_single returns) so downstream code
    (completeness checker, session save) keeps working unchanged.

    If streaming fails for any reason (API rejects stream, parse fails,
    etc.), the generator still emits "done" with whatever could be
    recovered. Callers should treat "done" as mandatory and "section" as
    best-effort.
    """
    transcript_text = Path(transcript_path).read_text(encoding="utf-8")

    # Load slide images if available
    screenshots = []
    if screenshots_json:
        try:
            with open(screenshots_json, encoding="utf-8") as f:
                screenshots = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"  [single-writer-stream] Could not load screenshots: {e}")
            screenshots = []

    screenshots_dir = None
    if screenshots:
        ss_path = Path(screenshots_json)
        for candidate in (ss_path.parent / "screenshots", ss_path.parent):
            if candidate.exists() and (candidate / screenshots[0].get("image_filename", "")).exists():
                screenshots_dir = candidate
                break

    print(f"  [single-writer-stream] Loaded {len(transcript_text.split())} words transcript, "
          f"{len(screenshots)} slide images")

    # ── Build the prompt (identical to non-streaming) ──
    brief = _build_brief(subject)
    parts: list = [types.Part.from_text(text=brief)]
    parts.append(types.Part.from_text(
        text="\n\n=== PROFESSOR'S TRANSCRIPT ===\n\n" + transcript_text
    ))

    images_added = 0
    if screenshots_dir:
        for s in screenshots:
            img_path = screenshots_dir / s["image_filename"]
            if not img_path.exists():
                continue
            try:
                img_bytes = img_path.read_bytes()
            except OSError:
                continue
            full_ref = f"screenshots/{s['image_filename']}"
            label = (
                f"\n\n=== SLIDE: {full_ref} "
                f"[{s.get('timestamp_display', '')}] "
                f"(use this full path in image_ref — include the 'screenshots/' prefix) ==="
            )
            parts.append(types.Part.from_text(text=label))
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            images_added += 1

    parts.append(types.Part.from_text(text=
        "\n\nNow: identify the spine, plan sections, fact-check uncertain "
        "claims via search if needed, then write the full document with "
        "bullets and exam tips for every section. Output JSON only."
    ))

    print(f"  [single-writer-stream] Prompt: {len(parts)} parts, {images_added} images")

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    model_name = model or GENERATOR_MODEL

    config_kwargs = {
        "temperature": 0.7,
        "max_output_tokens": 32768,
        "thinking_config": types.ThinkingConfig(thinking_budget=8192),
    }
    if enable_grounding:
        config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    # ── Stream the response ──
    slides_streamer = _ArrayObjectStreamer(key="slides")
    transcript_streamer = _ArrayObjectStreamer(key="transcript")
    slides_by_id: dict[str, dict] = {}
    pending: list[dict] = []   # transcript items that arrived before their slide
    full_text = ""
    sections_emitted = 0
    last_usage = None
    start_time = time.time()

    def _emit_section(tx_item: dict) -> dict:
        nonlocal sections_emitted
        sn = tx_item.get("slide_number", tx_item.get("slide_id"))
        slide_card = slides_by_id.get(str(sn), {}) if sn is not None else {}
        event = {
            "kind": "section",
            "index": sections_emitted,
            "transcript_item": tx_item,
            "slide_card": slide_card,
        }
        sections_emitted += 1
        return event

    try:
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=parts,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        for chunk in stream:
            text = getattr(chunk, "text", None) or ""
            if text:
                full_text += text

                # Slides usually stream first (schema order). Every completed
                # slide lands in the lookup so subsequent transcript items
                # ship with their card attached.
                for slide in slides_streamer.feed(text):
                    sid = str(slide.get("slide_id", ""))
                    if sid:
                        slides_by_id[sid] = slide

                    # Any transcript items that were waiting on this slide?
                    still_pending = []
                    for tx in pending:
                        sn = tx.get("slide_number", tx.get("slide_id"))
                        if str(sn) == sid:
                            yield _emit_section(tx)
                        else:
                            still_pending.append(tx)
                    pending = still_pending

                # Completed transcript sections
                for tx in transcript_streamer.feed(text):
                    sn = tx.get("slide_number", tx.get("slide_id"))
                    if sn is not None and str(sn) in slides_by_id:
                        yield _emit_section(tx)
                    else:
                        # Slide hasn't streamed yet — buffer briefly.
                        pending.append(tx)

            # Usage metadata shows up on the final chunk
            u = getattr(chunk, "usage_metadata", None)
            if u is not None:
                last_usage = u

        # Any still-pending transcript items (slide never arrived) — emit
        # without a slide card rather than dropping them.
        for tx in pending:
            yield _emit_section(tx)
        pending = []
    except Exception as e:
        print(f"  [single-writer-stream] Stream error: {e}")

    elapsed = time.time() - start_time

    if last_usage is not None:
        try:
            in_cost = last_usage.prompt_token_count / 1_000_000 * 2.50
            out_cost = last_usage.candidates_token_count / 1_000_000 * 10.00
            thinking = getattr(last_usage, "thoughts_token_count", 0) or 0
            think_cost = thinking / 1_000_000 * 10.00
            print(f"  [single-writer-stream] {elapsed:.0f}s, "
                  f"streamed={sections_emitted}, "
                  f"in={last_usage.prompt_token_count:,}t, "
                  f"out={last_usage.candidates_token_count:,}t, "
                  f"think={thinking:,}t, "
                  f"cost=${in_cost+out_cost+think_cost:.3f}")
        except Exception:
            print(f"  [single-writer-stream] {elapsed:.0f}s, streamed={sections_emitted}")
    else:
        print(f"  [single-writer-stream] {elapsed:.0f}s, streamed={sections_emitted}")

    # ── Final parse + convert to canonical GeneratedSections ──
    parsed = extract_json(full_text, expect_array=False)
    if not parsed or not isinstance(parsed, dict):
        print(f"  [single-writer-stream] ERROR: failed to parse final JSON")
        print(f"  [single-writer-stream] Raw output (first 500 chars): {full_text[:500]}")
        yield {"kind": "done", "sections": [], "groups": []}
        return

    raw_slides = parsed.get("slides", [])
    raw_transcript = parsed.get("transcript", [])

    if not raw_slides or not raw_transcript:
        print(f"  [single-writer-stream] ERROR: empty slides/transcript in final parse")
        yield {"kind": "done", "sections": [], "groups": []}
        return

    print(f"  [single-writer-stream] Final: {len(raw_slides)} slides + "
          f"{len(raw_transcript)} sections, "
          f"{sum(len(t.get('narrative','').split()) for t in raw_transcript)} words")

    sections = _convert_to_sections(raw_slides, raw_transcript)
    yield {"kind": "done", "sections": sections, "groups": []}


def _slide_card_to_markdown(card: SlideCard, slide_num: int) -> str:
    """Render a SlideCard as the markdown blob format generator_v2/v3 emit.

    Used by some downstream code that expects slide_content as markdown.
    Format mirrors what existing writer prompts produce.
    """
    lines = [f"=== SLIDE ===", f"Slide {slide_num}: {card.title}"]
    lines.append(f"type: {card.card_type}")
    if card.image_ref:
        lines.append(f"![{card.title}]({card.image_ref})")
    for bp in card.bullet_points:
        lines.append(f"• {bp}")
    if card.exam_tip:
        lines.append(f"Exam tip: {card.exam_tip}")
    return "\n".join(lines)
