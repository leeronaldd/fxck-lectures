# 2026-04-12 20:00 — Repetition Dedup Session

## Problem

Parallel processing repetition: when 3+ chunks independently contain Baltimore/lytic content, all explain it fully because they generate in parallel and don't know the others already covered it. Baltimore explained 3x, lytic cycle 3x, ~1,500 words of redundancy.

The existing `_format_previews_for_pro()` overlap detection uses string-matching between Flash sub-concepts. Flash describes the same concept differently across chunks ("lytic cycle — 5 steps" vs "viral multiplication — attachment to lysis"), so the overlap detector never fires and Pro never gets a "DO NOT RE-EXPLAIN" constraint for those concepts.

## What We Tested

Built `sandbox_dedup.py` with 4 fixes, tested on chunks 7-10 (Baltimore overview → Baltimore Classes 1-7 → Viral Evolution → Prokaryotic Infection).

### Fix 1: Post-generation dedup pass
Flash reads all generated sections after Pro finishes, identifies paragraphs that re-explain concepts already covered earlier. Python removes flagged paragraphs.

- Result: Baltimore 12→8 (33% reduction). Flash correctly identified duplicate class paragraphs.
- Problem: Only catches paragraph-level text duplication, not semantic overlap. Also fragile — first attempt Flash tried to reproduce all text and truncated at 1536 chars. Redesigned to have Flash output paragraph numbers to remove, Python does the cutting.
- Cost: +23s (one Flash call)

### Fix 2: Chunker-level merge
Before generation, compute Jaccard similarity of key terms between chunks. Merge pairs with >50% overlap into one combined chunk.

- Result: Chunks 7+8 merged (Jaccard 0.62). Baltimore 12→**0** (100% elimination).
- Problem: Changes slide structure — merged chunks produce one giant section instead of two slides. Chunk 9 (Viral Evolution) inflated to 386w when it should be a bridge (EI 65→75% shift). Breaks the slide-per-topic model the frontend expects.
- Cost: Saves one Pro call, but adds chunker complexity

### Fix 3: Sequential generation for related chunks
Generate overlapping chunks one-at-a-time instead of parallel. Each chunk sees the ACTUAL output of previous chunks (truncated to 800 chars), not just Flash summaries.

- Result: Baltimore 12→5 (58% reduction). Pro naturally adapted — chunk 8 dropped 252→182w, chunk 10 dropped 325→155w.
- Problem: 3x slower (177s vs 59s). Defeats the parallel architecture.

### Fix 4: Thinking mode MEDIUM
One config line: `thinking_config: types.ThinkingConfig(thinking_level="MEDIUM")` on Pro generation. Forces Pro to reason through constraints before generating.

**Sandbox results (4 chunks only):**
- Baltimore 12→1-3 (75-92% reduction). Dramatic.
- Fastest: 42-45s (even faster than 59s baseline in sandbox)
- Flash dedup (Fix 1) after thinking found zero paragraphs to remove

**Full pipeline results (12 chunks):**
- Baltimore 9→8, lytic 7→5. Modest improvement, not dramatic.
- Generation time: 60s→105s (+75% slower)
- Total pipeline: 140s→190s (+36% slower)

Also tested LOW thinking: Baltimore 12→9 (25% reduction). Not worth it — MEDIUM is the minimum useful level.

## Key Insight

Sandbox overstated thinking mode's impact because it only tested 4 overlapping chunks with tight constraints. In the full 12-chunk pipeline, the constraint text from `_format_previews_for_pro()` is based on Flash sub-concept string matching, which still misses semantic overlaps. Thinking mode helps Pro reason about constraints it *receives*, but can't help when the constraints don't list the overlap in the first place.

**The root cause is the overlap detector, not Pro's reasoning quality.**

## What's NOT Committed

Thinking mode config is in `generate_section()` but NOT committed. It's one line:
```python
"thinking_config": types.ThinkingConfig(thinking_level="MEDIUM"),
```
Decide whether +75% generation time is worth 1-2 fewer repetitions.

## Files

- `sandbox_dedup.py` — all 4 fixes + baseline + combo tests
- `data/output/_sandbox_baseline.json` — saved baseline for Fix 1 reuse
- `data/output/v2_transcript_20260412-172350.md` — full pipeline output with thinking MEDIUM
- `data/output/v2_transcript_20260412-130430.md` — Run 8 (best from depth inversion session, no thinking)

## Metrics

| Method | Words | Baltimore | Lytic | Time | Notes |
|--------|------:|----------:|------:|-----:|-------|
| Baseline (sandbox, 4 chunks) | 1,054 | 12 | 0 | 59s | Current parallel behavior |
| Fix 1 (post-gen dedup) | 922 | 8 | 0 | +23s | Flash paragraph removal |
| Fix 2 (chunker merge) | 1,253 | **0** | 1 | 116s | Merged 7+8, breaks slide structure |
| Fix 3 (sequential gen) | 1,577 | 5 | 0 | 177s | 3x slower |
| Fix 4 thinking MEDIUM (sandbox) | 1,539 | **3** | 2 | 42s | Dramatic in sandbox |
| Fix 4 thinking MEDIUM (full pipeline) | 4,421 | 8 | 5 | 190s total | Modest in full pipeline |
| Run 8 (full pipeline, no thinking) | 5,330 | 9 | 7 | ~140s total | Best from depth inversion |

## Next Session

The fix needs to happen in `_format_previews_for_pro()` overlap detection. Current approach: string-matching between sub-concept descriptions. Fails because Flash uses different words for the same concept.

Potential approaches:
1. **Embedding-based overlap** — compute embeddings for sub-concepts, use cosine similarity instead of word overlap. Catches "lytic cycle — 5 steps" ≈ "viral multiplication — attachment to lysis".
2. **Canonical concept normalization** — Flash outputs a canonical term alongside each sub-concept description (e.g., "lytic_cycle" for both phrasings). Match on canonical terms.
3. **Two-pass Flash** — first pass generates sub-concepts per chunk independently, second pass (with ALL chunks visible) normalizes and deduplicates the concept list. Assign ownership.
4. **Thinking mode as supplement** — keep thinking MEDIUM only if the overlap detector is fixed first. Without better constraints, thinking just adds cost.
