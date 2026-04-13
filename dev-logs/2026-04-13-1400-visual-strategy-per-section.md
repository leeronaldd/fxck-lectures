# 2026-04-13 14:00 — Visual Strategy Per Section + Professor Commentary Fix

## What Changed

### 1. Visual strategy assignment via Agent 3

Agent 3 (Teaching Planner) now assigns a `visual_strategy` per group alongside its teaching notes. Three strategies:

- **professor_slide**: the extracted screenshot is a clear labeled diagram/table. Writer points at it rather than re-describing.
- **openstax_figure**: no usable professor slide, but a textbook diagram exists. OpenStax figures (already being fetched via `fetch_textbook_images()`) are wired into the prompt.
- **structured_card**: no real image works. Agent 3 writes card content (title, bullets, exam tip). Frontend renders as styled card.

Agent 3 output changed from plain text to JSON:
```json
{
  "teaching_notes": "...",
  "visual_strategy": "professor_slide",
  "visual_data": {"best_slide_index": 4, "description": "..."}
}
```

Writer prompts now include visual strategy context before the output instruction, guiding how to reference the visual in the transcript.

### 2. "Your professor" meta-commentary fix

- Changed creative brief line 88 in `generator_v2.py`: "Your professor glossed over this" → "This wasn't covered in much detail in the lecture"
- Added `_strip_professor_commentary()` post-processing function as safety net — regex strips any remaining "your professor" / "Your professor" from output
- Also strips echoed structured card instructions ("No real image available...") that the model sometimes parrots

### 3. SlideGroup dataclass extended

Added two fields:
- `visual_strategy: str` — "professor_slide", "openstax_figure", or "structured_card"
- `visual_data: dict` — strategy-specific payload (slide index, search terms, card content)

### 4. Defensive parsing fix

`g.get("slides", [])` instead of `g["slides"]` in the validation loop — Flash occasionally returns groups without a `slides` key.

## Results

### Lecture 2 (Virology + Cell Biology)

| Metric | V3.1 (prev) | V3.1 + visuals |
|--------|-------------|----------------|
| Sections | 15 | 17 |
| Words | 6,144 | 6,070 |
| Planning | 190s | 165s |
| Generation | 75s | 78s |
| Total | 314s | 309s |
| Cost | ~$0.28 | ~$0.28 |
| "your professor" hits | 2-3 | 0 |

Visual strategy distribution (L2):
- SLIDE: 10 groups (professor slides clear enough)
- FIGURE: 2 groups (Influenza, Eukaryotic morphology)
- CARD: 5 groups (SARS-CoV-2, Detection, Membranes, Transport, Prokaryotic envelope)

### Lecture 3 (Bacteria) — generalization test

| Metric | Value |
|--------|-------|
| Sections | 17 |
| Words | 6,240 |
| Planning | 174s |
| Generation | 101s |
| Total | 335s |
| Cost | ~$0.30 |
| "your professor" hits | 0 |

Visual strategy distribution (L3):
- SLIDE: 10 groups (virology review using L2 screenshots)
- FIGURE: 4 groups (LPS, peptidoglycan, flagella, endospores)
- CARD: 3 groups (acid-fast walls, lysozyme/penicillin, spirochetes)

Pipeline generalizes well — bacteria content is deep and accurate. Transcript-only groups (7 of 17) all get appropriate visuals.

### Student-Professor Audit Summary

Both lectures passed:
- Every section references its visual (slide, figure, or card)
- All topics covered — no gaps
- Key exam terms bolded and named
- Smooth section-to-section flow ("Remember the... from Section X")
- Zero meta-commentary leaks
- Structured card instruction text no longer echoed in output

### Issue found and fixed during audit

Structured card sections were echoing the prompt instruction ("No real image available — write a structured card...") as literal output text. Fixed with:
1. Clearer instruction in slide_type_hint (tells model to write content directly, not include meta-instructions)
2. Post-processing regex strip as safety net

## Files Modified

- `src/generator_v3.py` — SlideGroup dataclass, Agent 3 JSON output + parser, assembly, writer prompt visual strategy, post-processing strip, defensive `.get()` fix
- `src/generator_v2.py` — line 88 creative brief fix (one line)

## What's NOT implemented yet

1. **Backend integration** — V3.1 runs via CLI only. Needs wiring into `backend/app/pipeline.py`
2. **Frontend structured card rendering** — CARD visuals need a new component in the frontend. Currently the card content appears as plain text in the slide section.
3. **OpenStax figure selection** — Agent 3 suggests search terms for `openstax_figure` groups, but the system doesn't use them to filter the fetched images. All images are fetched and passed — the writer picks the best one. Could be more targeted.
4. **Word count compression from visuals** — Visual strategy is wired in and writers reference slides, but word count didn't drop significantly (6,070 vs 6,144). The "point at the slide" instruction helps, but more aggressive compression would need explicit word budget reduction for SLIDE groups.
5. **Slide numbering consistency** — coordinator's sequence_position reorders groups but slide numbers in transcript text sometimes reference original group indices.

## Git

Not committed yet — should commit this session's work.
