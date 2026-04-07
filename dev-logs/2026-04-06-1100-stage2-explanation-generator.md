# Dev Log: 2026-04-06 — Stage 2 Explanation Generator

## What Was Built

### Stage 2: Explanation Generation (complete, needs v4 rework)
- `src/generator.py` — core generator with system prompt, prompt builder, Vertex AI (Gemini 3.1 Pro Preview) integration
- `run_stage2.py` — CLI with `--dry-run`, `--chunks`, `--preview`, `--ci`, `--screenshots`, `--slide-chunks` flags
- Multiple prompt iterations (v1→v2→v3→style-transfer), v1 original was actually the best

### Stage 1.5a: CI% Scorer
- `src/ci_scorer.py` — Gemini Flash scores each chunk 0-100 for exam importance
- `run_ci_scorer.py` — CLI
- Supports both Chunk and SlideChunk models
- **Issue:** Scoring is too conservative (everything 75-92%). Needs recalibration to use full 0-100 range.

### Stage 1.5b: Screenshot Extractor
- `src/screenshot_extractor.py` — OpenCV frame detection + Gemini Flash multimodal descriptions
- `run_screenshots.py` — CLI with `--skip-describe`, `--threshold` flags
- Extracts 20 slides from 115-min video, describes each, matches to chunks
- Re-captures frames near END of each slide for complete content
- Screenshots saved to `data/screenshots/`

### Slide-Based Chunking
- `src/slide_chunker.py` — maps transcript text to detected slide transitions by timestamp
- `run_slide_chunker.py` — CLI
- Merges tiny (<30 word) navigation artifacts into adjacent slides
- Flags >800 word slides for sub-chunking

### Deep Analysis
- `docs/anatomy-style-analysis.md` — forensic breakdown of anatomy professor's teaching patterns
- 7 transferable rules: question-answer chain, functional naming, inclusive language, temporal transitions, passive for naming, example placement, contrast via consequence

### Models Added (`src/models.py`)
- `Explanation` — Stage 2 output model with CI%, screenshot refs
- `Screenshot` — screenshot metadata model
- `CIScore` — exam importance model
- `SlideChunk` — slide-based chunk model

## What Worked
- V1 output quality was genuinely good — engaging, conversational, students can learn from it
- CI% concept is powerful — differentiates exam-critical from yap content
- Screenshot extraction works well — captures actual lecture slide content
- The anatomy professor analysis revealed specific, actionable patterns

## What Failed
- **Iterating on conciseness made output WORSE** — v2/v3 became clinical and dry
- **Slide-by-slide organization is wrong** — should group by concept, not follow professor's bad slide order
- **CI% scoring too conservative** — Gemini Flash is afraid to score anything below 30%
- **Word count targets killed natural flow** — hard limits made output feel constrained
- **Anatomy style transfer was applied too broadly** — should only be used for complex concepts

## Key Insight
V1's conversational "personal tutor" tone was the right base. The anatomy professor's patterns should ENHANCE that tone for complex concepts, not replace it. A real tutor:
- Skips yap ("professor rambled about naming history, not tested, skip")
- Expands where professor skimmed ("you need to know Baltimore for your exam")
- Uses colloquial language ("steal" not "takes a portion")
- Groups concepts logically, not following the professor's chaotic slide order

## Next Session: V4 Rework

### Architecture (approved plan in `.claude/plans/zippy-jingling-nest.md`)
```
Stage 1 chunks → CI% (recalibrated) → Concept Grouper → Stage 2 (v1 prompt enhanced) → Completeness Check → Slide References
```

### Key changes from current:
1. **Restore v1 system prompt** as base, ADD colloquial/skip/anatomy-flow rules
2. **Concept grouper** merges related chunks, reorders for learning flow, marks skips
3. **Skipped content stored** with raw transcript for on-demand frontend expansion
4. **No hard word limits** — let it flow naturally
5. **Completeness check** is grep-only (no Flash), inserts inline skip-lines
6. **Slide references** are post-processing, not in generation prompt
7. **CI% recalibrated** to actually use full 0-100 range

### Files to create/modify:
- `src/generator.py` — rewrite SYSTEM_PROMPT (restore v1 + enhancements)
- `src/concept_grouper.py` — new merge/reorder/skip module
- `src/completeness_checker.py` — new grep-based coverage check
- `src/slide_inserter.py` — new post-processing slide references
- `src/ci_scorer.py` — recalibrate prompt
- `run_stage2.py` — wire new pipeline

### Branch
Working on `style-transfer-v1` branch. Main/master has Stage 1 only.

## Data Artifacts
| File | Description |
|------|-------------|
| `data/output/final_chunks_v5.json` | Stage 1 output (14 chunks) |
| `data/output/ci_scores.json` | CI% scores for regex chunks |
| `data/output/slide_ci_scores.json` | CI% scores for slide chunks |
| `data/output/screenshots.json` | 20 screenshot metadata |
| `data/output/slide_chunks.json` | 18 slide-based chunks |
| `data/output/explanations_v1.json` | **BEST output** — v1 explanations |
| `data/output/explanations_v2.json` | v2 with CI% + screenshots (worse) |
| `data/output/explanations_v3.json` | v3 concise (worse) |
| `data/output/slide_explanations_v1.json` | Slide-based v1 (too long) |
| `data/output/slide_explanations_v2.json` | Slide-based v2 concise (too short/dry) |
| `data/output/slide_explanations_v3_style.json` | Style transfer (formulaic) |
| `data/output/lecture_replacement_v1.md` | **Readable markdown — best version** |
| `data/screenshots/*.jpg` | 20 extracted lecture slide images |
| `docs/anatomy-style-analysis.md` | Deep analysis of anatomy professor's style |

## Config
- GCP Project: `project-bc1fc31b-94c5-44b0-904`
- Generation model: `gemini-3.1-pro-preview`
- Scoring/cheap model: `gemini-3-flash-preview`
- Location: `global`
