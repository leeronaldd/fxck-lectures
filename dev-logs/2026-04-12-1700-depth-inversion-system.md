# 2026-04-12 17:00 — Depth Inversion System

## What Changed

Built a depth inversion system for V2 generation. 12 pipeline runs, 2 sandbox experiments, 10 output versions compared.

### Problem
Pro allocated depth uniformly (~200-300w per section) regardless of exam importance. Baltimore classification (EI 92%) got the same depth as naming conventions (EI 55%). The anatomy professor inverts this — she gives titin one sentence and the cross-bridge cycle 400 words.

### Solution: 5 fixes on baseline generator_v2.py

1. **Flash transcript limit**: 1000 → 6000 chars. Flash was only seeing the first half of long chunks, causing it to miss Classes V-VII entirely in the sub-concept checklist.

2. **Flash outputs EI% + sub-concepts**: Each chunk now gets an exam importance estimate and a numbered list of mechanisms/processes. 7 sub-concepts for Baltimore = all 7 classes listed. This is the depth control — Pro writes a paragraph per sub-concept, so more sub-concepts = more depth naturally.

3. **Relevant-only hard constraint previews**: `_format_previews_for_pro()` now outputs "ALREADY TAUGHT — DO NOT RE-EXPLAIN" but only for prior concepts that overlap with the current chunk's content. Prevents the over-constraining problem where listing ALL prior slides made Pro think nothing was new.

4. **Bridge framing for EI < 60%**: Low-EI chunks get "You are writing a BRIDGE PARAGRAPH, not a teaching section." This reframes the task from "teach" to "transition" — Pro naturally writes 65-99 words instead of 400+. Tested in sandbox: bridge framing = 65w, word limit = 147w, style hint = 421w, baseline = 425w.

5. **Garbled term filter**: Strips trailing filler words from auto-caption key terms ("Ebola virus if" → "Ebola virus"). Also strips leading filler ("although some viruses" → removed). Deduplicates terms.

### What Worked (validated in sandbox)

| Method | Tested on | Result |
|--------|-----------|--------|
| Sub-concept checklist | Baltimore Classes | 371→770w, all 7 classes individually explained |
| Bridge framing | Animal Families | 425→65w compression |
| Hard constraint "DO NOT RE-EXPLAIN" | Lytic cycle | 0 re-explanations in sandbox |
| 6000-char Flash fix | Baltimore Classes | Classes V, VI, VII now always present |
| Garbled term filter | All key terms | 10+ artifacts cleaned |

### What Didn't Work

| Method | Why it failed |
|--------|---------------|
| Word count limits ("keep to 150 words") | Pro treats as suggestion, writes 400+ anyway |
| Style hints ("like naming bone markings") | 421w vs 425w — zero compression effect |
| Three-tier system (Tier 1/2/3 labels) | Collapsed Tier 1 sections to 60-90w stubs |
| Transcript truncation for low-EI | Pro writes 679w from parametric memory alone |
| _ei_depth_nudge word ranges | Partially followed, superseded by checklist approach |

### Remaining Issue: Parallel Processing Repetition

The single biggest remaining problem. When 3 chunks independently contain Baltimore content:
- Chunk 7: Baltimore overview
- Chunk 8: Baltimore Classes 1-7 detail
- Chunk 5: Virus classification (includes Baltimore intro)

All 3 chunks generate in parallel. Each independently explains Baltimore classification because they don't know the others already covered it. Result: Baltimore explained 3x, lytic cycle explained 3x, ~1,500 words of redundancy.

The hard constraint preview was designed to fix this, but it depends on string-matching sub-concepts across chunks. Flash describes the same concept differently in different chunks ("lytic cycle — 5 steps" vs "viral multiplication — attachment to lysis"), so the overlap detection misses it.

**Potential fixes for next session:**
1. **Sequential generation** for chunks that share sub-concept keywords (sacrifice parallelism for coherence)
2. **Post-generation dedup pass** — Flash reads all generated sections and flags redundant paragraphs
3. **Chunker-level merge** — detect overlapping chunks before generation and merge them
4. **Two-phase generation** — first pass generates all sections in parallel, second pass (Flash) removes redundant content

## Key Insight

Pro reads Flash previews and uses them for transitions ("remember the capsid we covered earlier") but treats them as conversational context, not constraints. It says "as we discussed" and then re-explains anyway. The fix isn't louder instructions — it's changing what Pro thinks its JOB is. "You're writing a bridge paragraph" works because it changes the task. "Keep to 150 words" fails because it's a constraint on an unchanged task.

## Best Output

Run 8 (`v2_transcript_20260412-130430.md`, 5,330 words) was rated best across all 10 versions by both student and professor criteria:
- All 7 Baltimore classes individually explained
- Every term defined before use
- Mnemonics: "Positive is Proficient", "AP-SAR" 
- No assumed prior knowledge
- "bacteria T4" factual error absent
- Best balance of depth inversion

## Files

- `src/generator_v2.py` — all 5 fixes applied to baseline
- `sandbox_compression.py` — 7 compression methods tested
- `sandbox_fixes.py` — 3 issue-specific sandbox tests
- `data/output/v2_transcript_20260412-*.md` — 10+ output versions for comparison
- Git: `cacb173` = experimental snapshot, `42b369b` = clean 5-fix version

## Metrics

| Run | Total Words | Baltimore 1-7 | Low-EI avg | Repetitions |
|-----|-------------|---------------|------------|-------------|
| Run 1 (baseline) | 3,710 | 371 | ~220 | unknown |
| Run 3 (checklist) | 6,787 | 541 | ~430 | unknown |
| Run 4 (compression) | 4,509 | 305 | ~190 | low |
| Run 8 (best) | 5,330 | 428 | ~200 | low |
| Run 5A (consistency) | 5,583 | 770 | ~195 | medium |
| Run 12 (all fixes) | 5,507 | 791 | ~90 | high |

## Next Session

1. Fix repetition — most likely via post-generation dedup or sequential generation for overlapping chunks
2. Test on a second lecture (different subject) to validate generalization
3. Consider: is the chunker creating the overlap problem? Maybe merge chunks that share >50% of their key terms before generation
