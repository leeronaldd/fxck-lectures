# 2026-04-13 12:00 — V3.1 Multi-Agent Planning Pipeline

## What Changed

### Replaced single Flash planning call with 4-agent pipeline

The V3 single-call planner dropped slides non-deterministically (35% lecture coverage on one run). Root cause: attention overload from doing 4 jobs at once (group slides, read transcript, write plans, track terms).

**New pipeline:**

```
Agent 1: Slide Grouper (Flash, text-only, ~45s)
    → groups slides by topic from descriptions
    → validated: every non-blank slide in exactly one group
    → groups FROZEN after this step

Agent 2: Transcript Scanner (Flash, ~25s)
    → matches transcript to slide groups
    → discovers transcript-only topics (HIV, Influenza, COVID, Gram staining, etc.)
    → extracts sub-concepts per group (e.g. "7 sub-concepts: Class I through VII")
    → each transcript section assigned to AT MOST one group

COORDINATOR (Pro + thinking mode MEDIUM, ~60s)
    → reads full notebook (all groups + sub-concepts + transcript words + prof signals)
    → writes MASTER PLAN: depth, ownership, sequence, word budgets
    → plan is IMMUTABLE — downstream can't override
    → uses merge_into for low-importance topics (absorbed into adjacent sections)
    → NO bridges — every section either teaches or gets merged

Agent 3: Teaching Planner (Flash + slide images, parallel, ~30s)
    → writes pedagogical notes per group
    → notes are SUGGESTIONS — master plan is law
```

### Two-tier generation (Pro + Flash-thinking)

- **Pro** (deep groups): full creative brief via context cache, anatomy reference images, Google Search. For complex mechanisms.
- **Flash + thinking LOW** (standard groups): full creative brief as system instruction, anatomy reference images, thinking mode. Approaches Pro quality at Flash cost.
- **No bridges** — coordinator merges low-importance topics into adjacent groups. The anatomy professor never writes standalone transitions.

### Word count control

- Coordinator given hard budget: 5,500-6,500w total
- Standard sections get WORD CEILING in prompt (hard limit)
- Deep sections get word TARGET (flexible)
- Sub-concepts from Agent 2 help coordinator judge depth (7 Baltimore classes = deep, not standard)

### Key architectural decisions

1. **Kill bridge sections**: The anatomy professor doesn't write bridges (observation #20, #25). She ends each section pulling into the next. Standalone transitions are an anti-pattern. Low-importance topics get `merge_into` adjacent groups.

2. **Sub-concepts in notebook, not coordinator prompt**: Agent 2 extracts sub-concept counts. The coordinator SEES them in the notebook data (e.g. "7 sub-concepts") and uses that to judge depth. But sub-concepts don't go in the coordinator's instructions — that would add noise.

3. **Flash + thinking for standard sections**: Flash with thinking mode LOW gets the full creative brief and produces ~190-280w standard sections with adequate style transfer. Saves ~$0.18/lecture vs all-Pro.

4. **Coordinator thinking mode MEDIUM**: Fixes the depth-flattening bug where Baltimore got EI 70% instead of 90%. 2,500-4,000 thinking tokens per coordinator call, adds ~$0.01.

## Results — Lecture 2 (Virology + Cell Biology)

### Final run metrics

| Metric | Value |
|--------|-------|
| Sections | 15 |
| Total words | 6,144 |
| Coordinator target | 6,050 |
| Overshoot | 94w (2%) |
| Planning time | 190s |
| Textbook time | 43s |
| Generation time | 75s |
| Total time | 314s |
| Pro calls | 8 (deep) |
| Flash+thinking calls | 7 (standard) |
| Bridge calls | 0 |
| Estimated cost | ~$0.28 |

### Coverage (vs audit)

| Topic | V3 single-call | V3.1 final |
|-------|---------------|------------|
| Baltimore classification | 670w deep | 522w deep (EI 90%) |
| HIV/AIDS | MISSING | 514w deep (EI 100%) |
| Influenza | MISSING | 545w deep (EI 100%) |
| COVID-19 | MISSING | included in Epidemiology section |
| Gram staining | MISSING | 573w deep (EI 100%) |
| Membranes | MISSING | 606w deep (EI 95%) |
| Transport | MISSING | 771w deep (EI 100%) |
| Ebola | MISSING | merged into Epidemiology (595w section) |
| Eukaryotic morphology | MISSING | 486w deep (EI 85%) |

### Word budget compliance

- 12/15 sections within +/-50w of coordinator target
- 2 minor overshoots (+80w, +95w)
- 1 real overshoot: Transport at +171w (771w vs 600w — 6 distinct mechanisms)
- Standard sections average 219w (targets ~200-250w)
- Deep sections average 576w (targets ~500-600w)

## Cost evolution

| Version | Cost | Words | Coverage | Pro calls |
|---------|------|-------|----------|-----------|
| V2 | ~$0.20 | 5,330 | ~70% | 12 |
| V3 single-call | ~$0.25 | 3,941 | ~35% | 8 |
| V3.1 all-Pro | ~$0.40 | 8,481 | 100% | 17 |
| V3.1 3-tier | ~$0.34 | 9,529 | 100% | 16 |
| V3.1 tightened | ~$0.22 | 5,494 | 100% | 6 |
| **V3.1 final** | **~$0.28** | **6,144** | **100%** | **8** |

## What's NOT implemented yet

1. **Slide images for every section** — transcript-only groups (HIV, Influenza, COVID, Gram staining, membranes, transport) have no visual. Adding OpenStax figures or structured slide cards would let the transcript reference them and save ~500w, bringing total to ~5,500w. Agent 3 should assign each group a visual strategy: `professor_slide`, `openstax_figure`, or `structured_card`.

2. **"Your professor" meta-commentary** — still leaks into Pro output ~2-3 times per lecture. The creative brief's preamble references "your professor" and Pro echoes it. Needs a post-processing strip or prompt revision.

3. **Lecture 3 test** — V3.1 only tested on lecture 2. Lecture 3 (bacteria, different professor style) would validate generalization.

4. **Backend integration** — V3.1 runs via CLI only. Needs wiring into `backend/app/pipeline.py` for the web app.

5. **Slide numbering in output** — the coordinator's sequence_position reorders groups but slide numbers in the transcript text sometimes reference original group indices, creating confusion.

## Files modified

- `src/generator_v3.py` — complete rewrite of planning section:
  - `_agent1_group_slides()` — Flash slide grouper with JSON repair
  - `_agent2_scan_transcript()` — Flash transcript scanner with sub-concepts
  - `_coordinator_plan()` — Pro coordinator with thinking mode + merge_into
  - `_agent3_teaching_plans()` — Flash teaching planner (parallel)
  - `_assemble_groups()` — handles merge_into absorption
  - `generate_section_v3()` — two-tier: Pro deep, Flash+thinking standard
  - `generate_lecture_v3()` — updated orchestrator, no bridges
- `run_v3.py` — unchanged (CLI works as before)

## Git

Not committed yet — should commit this session's work.
