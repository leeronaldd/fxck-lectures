# 2026-04-13 21:00 — Visual Images, Wikimedia Fallback, Backend Integration

## What Changed

### 1. Every section gets a visual

Agent 3 assigns `visual_strategy` per group during planning. Three strategies:
- **professor_slide** — extracted screenshot is clear, writer points at it
- **openstax_figure** — OpenStax textbook diagram fetched and uploaded to GCS
- **structured_card** — no real image, Agent 3 writes card content (bullets + exam tip)

**Override logic**: If Agent 3 assigned `structured_card` but OpenStax/Wikimedia images were actually found during Stage 2 (after planning), the strategy is upgraded to `openstax_figure` at generation time.

### 2. Wikimedia Commons fallback

When OpenStax has no figure for a topic, `fetch_wikimedia_image()` searches Wikimedia Commons API for CC-licensed diagrams. Tries multiple query formulations (key terms, simplified topic name). Results uploaded to GCS under `wikimedia/` prefix.

Works well for: Gram staining, influenza drift/shift, HIV replication, cell walls.
Mediocre for: archaea membranes, transport mechanisms (Wikimedia search returns old textbook scans for niche topics).

### 3. Image URL validation pipeline

Three layers prevent broken images:
1. **Post-processing normalization** — hallucinated GCS paths like `/professor/screenshot_003.jpg` converted to relative `screenshots/` paths
2. **URL validation** — any GCS URL not in the provided figure list gets stripped. Raw Wikimedia URLs also stripped (we always upload to GCS).
3. **Stale job-id path fix** — regex corrects `test-job-456/openstax_Figure_X.jpg` to `openstax/Figure_X.jpg`

### 4. "Your professor" meta-commentary fix

- Changed creative brief example text (line 88, generator_v2.py)
- `_strip_professor_commentary()` post-processing catches remaining leaks
- Zero hits across all test runs

### 5. Agent 1 reliability fix

- **Checklist in prompt** — explicitly lists all slide indices with "verify before responding"
- **Surgical patch** — when slides ARE missed, tiny Flash call assigns them (~3-5s instead of 50s full retry)
- **Orphan fallback** — any remaining misses go to nearest group by index. Zero slides ever lost.
- Result: ~30% of runs that previously took 100s now take 55s. Zero data loss.

### 6. `original_group_index` bug fix

The core bug causing writers to not receive their textbook images: `_assemble_groups` reindexed groups by sequence position, but `textbook_imgs` was keyed by original group index. Added `original_group_index` field to SlideGroup to preserve the mapping.

### 7. Backend integration

`backend/app/pipeline.py` now routes to V3.1 when screenshots are available (video input or PDF slides), falls back to V2 for transcript-only uploads. Same `assemble_api_response()` output format — frontend doesn't need changes.

Dockerfile updated to include `docs/reference/` for anatomy style transfer images.

## Results

### Lecture 2 (Virology + Cell Biology) — Final Run

| Metric | Value |
|--------|-------|
| Sections | 13 |
| Words | 5,646 |
| Images working | 13/17 slides have images |
| Broken URLs | 0 |
| "your professor" hits | 0 |
| Planning time | 150s |
| Generation time | 73s |
| Total | 288s (~5 min) |
| Cost | ~$0.28 |

### Image sources per lecture

| Source | Count | Notes |
|--------|-------|-------|
| Professor slides (relative) | ~8-10 | Always work via API proxy |
| OpenStax figures (GCS) | ~2-4 | CC BY 4.0, uploaded to GCS |
| Wikimedia figures (GCS) | ~1-2 | CC BY-SA / Public Domain |
| Structured cards (no image) | ~3-4 | Abstract topics, card is better |

### Cost breakdown

| Component | Cost | % |
|-----------|------|---|
| Pro generation (6-8 sections) | ~$0.20 | 73% |
| Pro coordinator | ~$0.03 | 11% |
| Flash planning (3 agents) | ~$0.03 | 11% |
| Flash generation (5-8 sections) | ~$0.02 | 7% |
| APIs (OpenStax/Wikimedia/GCS) | ~$0.00 | 0% |

### Session cost

~$2-3 total across ~8 full pipeline runs + dry runs + standalone tests.

## Deploy checklist

1. `backend\deploy.bat` — deploys to Cloud Run (user runs manually)
2. Frontend — no changes needed, already handles GCS URLs + relative paths + cards
3. Verify GCS bucket permissions for service account on Cloud Run

## What's NOT implemented

1. **Frontend structured card component** — CARD visuals appear as plain text bullets. A styled card component would make them look intentional.
2. **CDC.gov as image source** — public domain, great for pathogen diagrams. Would fill remaining gaps for influenza, HIV.
3. **Smarter OpenStax figure selection** — Agent 3 suggests search terms but they're not used to filter. All figures for a page are passed, writer picks.
4. **Teacher-Student Agent Loop (Stages 3-5)** — evaluation + conditional revision. Not yet implemented.

## Files modified

- `src/generator_v3.py` — visual strategy, image validation, Agent 1 reliability, original_group_index
- `src/generator_v2.py` — Wikimedia upload, creative brief fix, fetch_textbook_images fallback
- `src/textbook_search.py` — fetch_wikimedia_image() with multi-query search
- `backend/app/pipeline.py` — V3.1 routing with V2 fallback
- `Dockerfile` — includes docs/reference/
- `CLAUDE.md` — updated architecture section
