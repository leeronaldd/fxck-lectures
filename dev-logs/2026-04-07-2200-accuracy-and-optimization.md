# Dev Log: 2026-04-07 (late) — Accuracy Pipeline + Optimization

## What Changed

### Textbook RAG moved to generation time
- Previously: textbook only used during post-generation fact-checking
- Now: `build_group_prompt()` fetches relevant OpenStax chapter and includes it as primary factual context
- System prompt rule: "textbook wins on facts, professor wins on scope"
- Hardcoded OpenStax URL lookup table — 100% reliable, zero LLM calls for URL resolution
- Covers microbiology + anatomy chapters, easy to extend

### Pro correction loop
- `_correct_errors_with_pro()` in fact_checker.py — surgically rewrites flagged paragraphs
- Includes voice rules so corrections match colloquial tone
- Only runs when fact-checker finds errors (conditional — saves ~$0.05 when no errors)
- ~80% success rate on corrections sticking

### System prompt generalized
- Removed ALL 12 virology-specific error corrections (neuraminidase, lysozyme timing, lytic cycle order, etc.)
- Kept only 6 general accuracy principles that work for ANY medical lecture
- Key lesson: specific error corrections belong in the textbook RAG + fact-checker pipeline, not the system prompt
- Error rate with generalized prompt + textbook RAG: 4 detected → all corrected → 1 remaining

### Parallel generation
- `generate_from_groups()` now uses `ThreadPoolExecutor` (max 6 workers)
- All sections generate concurrently — textbook fetch + Pro generation happen in parallel
- Prior group names pre-computed from fixed group order
- Speed: ~60-90s → ~15-20s for generation step
- Zero effect on output quality

### Dropped Flash slide inserter
- Removed Step 6 (Flash-based `slide_inserter.py` paragraph mapping) — ~20 Flash calls, mostly failing
- Slides now inserted via `_insert_slides_inline()` in assembly — keyword matching, zero LLM calls
- Saves ~$0.01 per lecture + eliminates 20 JSON parse warnings

### DeepSeek V3.2 investigation
- Available on Vertex AI but self-deploy only (8x NVIDIA B200 GPUs — $thousands/hr)
- No managed API (pay-per-token) option
- Decision: stay on Gemini Flash. Cost difference would have been ~$0.02/lecture
- Config is env-var switchable: `CHEAP_MODEL=deepseek-v3-2` if managed API becomes available

### Emoji generation moved to Pro
- System prompt tells Pro to add relevant emojis on ### sub-headings
- Assembly no longer rotates emojis from a fixed list
- Emojis are now contextually chosen by Pro (🧬 for genetics, 💉 for infection, etc.)

## Error Rate Journey

| Version | Errors | What fixed it |
|---------|--------|---------------|
| v4 initial | 11 | — |
| + accuracy rules in prompt | 4 | Virology-specific rules prevented 7 errors |
| + generalized prompt (rules removed) | 7 | Errors recurred without specific rules |
| + textbook RAG during generation | 4 | Textbook context prevented recurring errors |
| + Pro correction loop | 1 | 3 of 4 corrected, 1 didn't stick |

The key insight: virology-specific rules in the prompt worked but don't generalize. Textbook RAG achieves the same accuracy while working for any lecture.

## Current Pipeline Cost: ~$0.28/lecture

| Step | Model | Cost |
|------|-------|------|
| CI% scoring | Flash × 14 | $0.01 |
| Concept grouping | Flash × 1 | $0.00 |
| Textbook fetch | HTTP × 6 | free |
| Generation | Pro × 6 (parallel) | $0.25 |
| Fact-checking | Flash × 6 | $0.02 |
| Pro corrections | Pro × ~2 (conditional) | $0.00-0.05 |
| Completeness | Flash × 1 | $0.00 |
| Assembly | Python | free |
| **Total** | | **~$0.28** |

## Current Pipeline Speed: ~1-1.5 min/lecture
- Generation: ~15-20s (parallel, was 60-90s sequential)
- Fact-checking: ~30s
- Everything else: ~15s
- Total: ~60-90s

## What's Next
- Stage 3-5: Teacher-student agent loop (evaluator → optimizer → student agent)
- Frontend: Supabase + Vercel (separate session)
- Textbook RAG: student enters university + course → auto-find prescribed textbook

## Files Modified This Session
- `src/generator.py` — system prompt (6 iterations), parallel generation, textbook context in prompts
- `src/fact_checker.py` — textbook RAG, Pro correction loop, OpenStax lookup table
- `src/completeness_checker.py` — general noise filter, slide term extraction via Flash
- `src/concept_grouper.py` — generalized grouping prompt
- `src/ci_scorer.py` — generalized scoring examples
- `src/chunker.py` — Flash term extraction, Flash topic naming, generalized patterns
- `src/json_repair.py` — NEW: robust JSON extraction from truncated Flash responses
- `src/config.py` — env-var configurable model selection
- `run_stage2.py` — parallel generation, slide dedup, inline slide placement, fact-check wiring, dropped Flash slide inserter
