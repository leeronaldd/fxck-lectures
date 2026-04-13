# 2026-04-12 23:45 — V3 Slide-Driven Architecture

## What Changed

### New V3 pipeline (slide-driven, replaces transcript-driven V2)

Built `src/generator_v3.py` and `run_v3.py` — a fundamentally different architecture where slides drive the document structure instead of transcript chunks.

**V2 pipeline** (transcript-driven):
```
Chunk transcript → Flash prefetch → Flash coordinator → Textbook fetch → Pro generation
(5 stages, fragile chunking, repetition across parallel writers)
```

**V3 pipeline** (slide-driven):
```
Flash sees ALL slides + transcript → Teaching plan → Textbook fetch → Pro generation
(3 stages, one planning call replaces 5 mechanical steps)
```

### How V3 works

1. **Flash planning (one call)**: Sees all slide descriptions, all slide images, and the full transcript simultaneously. Returns 8-15 topic groups with:
   - Which slides belong to each group
   - Depth allocation (deep/standard/bridge/skip)
   - EI% estimate
   - Teaching plan (3-5 sentences telling Pro what to focus on, what's hard, what to skip)
   - Key scientific terms (with first-introduction tracking)
   - Word count estimate

2. **Textbook fetch (parallel)**: Same as V2 — OpenStax + NCBI per group.

3. **Pro generation (parallel)**: Same creative brief + context caching as V2, but the user prompt leads with Flash's teaching plan instead of raw transcript. Pro sees: teaching plan → prior context → textbook → transcript excerpt → actual slide images.

### What V3 replaces

One Flash planning call replaces ALL of these V2 components:
- `chunker.py` — regex chunking + mega-chunk splitting
- `ci_scorer.py` — EI% scoring
- `concept_grouper.py` — merge/reorder/skip pass
- Flash prefetch — teaching summaries
- Flash coordinator — concept ownership assignment
- Depth nudge / bridge framing logic

### What stays from V2

- Creative brief (`_BRIEF_PREAMBLE`, `_ANATOMY_EXAMPLE_1`, `_TEACHING_OBSERVATIONS`) — identical
- `textbook_search.py` — identical
- Context caching — identical
- Output parser (`parse_output`) — identical
- Assembly functions (`assemble_slide_doc`, `assemble_transcript_doc`, `assemble_api_response`) — identical
- Frontend — unchanged

## Results

### Lecture 2 (Virology, ~2hr)

**Planning**: 12 teaching groups + 1 skip across 20 slides. Flash made intelligent pedagogical judgments:
- Baltimore classification → deep (EI 95%)
- Viral morphology → standard (EI 65%)
- Enveloped viruses → bridge (EI 70%)
- Lab methods → standard (EI 75%)
- HIV case study → deep (EI 95%)
- Flash even created transcript-only groups for Influenza, COVID, and bacterial topics the professor discussed without slides

**Generation**: 8 sections, 3,941 words in 263s total
- Planning: 138s (one Flash call with 20 images)
- Textbook: 54s (parallel)
- Pro generation: 63s (parallel, 8 workers)

### Output quality assessment

Strengths vs V2:
- **No repetition** — the #1 V2 problem is gone. Flash assigns each concept to one group, Pro never sees overlapping content.
- **Slide integration** — transcript physically walks through slides: "Look at diagram (a)...", "Notice the red circle...", "shift your attention to diagram (b)..."
- **Depth inversion working** — Baltimore gets 670w, capsid architecture gets 398w, enveloped viruses gets 391w
- **Forward momentum** — every section ends pulling into the next
- **Concrete → abstract** — every section opens with a hook, not a definition

Known issues:
- **Flash variability** — planning output varies between runs (8-12 groups). Some runs drop slides. Added retry mechanism for when >3 non-blank slides are missing.
- **Transcript matching** — for slide-less groups (topics covered verbally without slides), uses term-based search in transcript, which is approximate.
- **Planning time** — 70-140s for the planning call (sending 20 images to Flash). Acceptable but could optimize by reducing image resolution.

## Files

- `src/generator_v3.py` — complete V3 pipeline: Flash planner, Pro generation, orchestrator
- `run_v3.py` — CLI entry point with dry-run, preview, sequential modes
- `data/output/v3_transcript_*.md` — generated outputs
- `data/output/v3_plan_*.json` — teaching plans for debugging
- `data/output/_v3_raw_plan.txt` — raw Flash output for debugging

## Architecture Decisions

1. **Flash sees actual slide images, not just descriptions** — the AI-generated descriptions miss details. Sending all 20 images costs ~5K tokens but dramatically improves grouping accuracy.

2. **Teaching plan comes FIRST in Pro's user prompt** — before textbook, before transcript, before slides. Pro reads the plan, understands its role in the bigger document, THEN reads source material. This frames the entire generation.

3. **Term ownership via set arithmetic (same as V2)** — Flash lists key terms per group, Python assigns first-introduction ownership. Simple, deterministic, no LLM needed.

4. **Transcript-to-slide matching via timestamp proportions** — since transcripts don't have inline timestamps, we map slide timestamps to transcript character positions proportionally. Works well enough for ~2K word excerpts per group.

5. **Retry on missing slides** — if Flash drops >3 non-blank slides, retry with an explicit nudge listing the missing slides. Usually recovers them.

## What's Next

1. **Backend integration** — wire V3 into the FastAPI pipeline (`backend/app/pipeline.py`)
2. **PDF slide input** — currently requires screenshot_extractor output. Add direct PDF → slide grouping path.
3. **Planning stability** — explore using structured output (JSON mode) for Flash planning to reduce parse variability
4. **Lecture 3 test** — validate on the bacteria lecture (different professor style, different subject)

## Metrics

| Metric | V2 (Run 8, best) | V3 (this run) |
|--------|-------------------|---------------|
| Total words | 5,330 | 3,941 |
| Sections | ~12 | 8 |
| Baltimore depth | 428w | 670w |
| Repetitions | low | zero |
| Pipeline stages | 5 | 3 |
| Total time | ~180s | 263s |
| Planning time | ~30s (prefetch) | ~140s |
| Generation time | ~45s | ~63s |
| Slides integrated | partial | every section |
