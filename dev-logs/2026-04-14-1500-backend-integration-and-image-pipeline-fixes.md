# 2026-04-14 15:00 — Backend Integration, Image Pipeline Fixes, Production Hardening

Long session focused on getting V3.1 live in production and fixing every issue
that surfaced once real users started uploading lectures with diverse formats.

## What Changed

### 1. Backend integration — V3.1 now serves all uploads

Previously the backend ran V2 (transcript-driven) regardless of input. Now
`backend/app/pipeline.py` always routes through V3.1 for every input format:

- **Video only** → extract screenshots + Flash describe → V3.1
- **Video + PDF slides** → extract PDF slides + Flash describe → V3.1 (video screenshots skipped)
- **Txt + PDF slides** → extract PDF slides + Flash describe → V3.1
- **Txt only** → Agent 1 skipped → Agent 2 finds all topics from transcript → V3.1
- **Audio (.mp3) only** → transcribe → Agent 1 skipped → V3.1
- **Audio + PDF slides** → transcribe + extract PDF slides → V3.1

V2 fallback removed entirely. Single unified pipeline.

### 2. PDF slide pipeline now produces V3-compatible output

`extract_pdf_slides()` was producing entries with empty `description` and no
`timestamp_seconds`. V3 Agent 1 needs descriptions to group, V3's transcript
matching needs timestamps. Now:

- `describe_screenshots()` runs on PDF slides (Flash multimodal, parallel)
- Synthetic timestamps spaced evenly across assumed 2hr lecture
- Mime type fixed: PNG screenshots no longer hardcoded as JPEG

### 3. Audio-only support (.mp3, .m4a, .wav, etc.)

Added audio extension set to pipeline. Audio files transcribe via Gemini Flash
multimodal (or Whisper if `WHISPER_SERVICE_URL` set), then run V3.1 in
transcript-only mode. Screenshot extraction skipped (no video frames).

### 4. Auto-include every professor slide

Writers only referenced 1-2 slides per group, so a 37-page PDF would produce
~10 slide cards in the output. Students missed 27 slides they saw in class.

New `_ensure_all_slides_included()` runs after generation:
- Collects all `image_ref` values writers used
- For each group, finds slides the writer didn't reference
- Auto-creates `SlideCard` objects with title from Flash description
- Writer-generated cards (with exam tips) come first, auto-filled cards follow

Result: every professor slide appears in the output. OpenStax/Wikimedia still
fill in for transcript-only groups (no professor slides).

### 5. Image URL pipeline hardening

Three issues fixed:

**Hallucinated GCS URLs** — writer sometimes invented `/professor/screenshot_X.jpg`
GCS paths that don't exist. Now `_validate_image_urls()` strips any GCS URL
not in the actual fetched-images set.

**Stale cache entries** — old `test-job-456/openstax_Figure_3.12.jpg` cache
files pointed to deleted GCS objects. Regex now corrects these to the canonical
`openstax/Figure_X.jpg` path.

**GCS URL replacement in transcript text** — only slide cards were getting
their `screenshots/` paths swapped to GCS URLs. Transcript narrative text
containing `![desc](screenshots/slide_X.png)` kept local paths that don't
resolve on Cloud Run after container restart. Now both are swapped.

### 6. Wikimedia Commons fallback

When OpenStax has no figure for a topic, `fetch_wikimedia_image()` searches
Wikimedia Commons API for CC-licensed diagrams. Multi-query strategy (key terms
→ simplified topic name → 2-word query). Filters to JPG/PNG ≥300px wide with
acceptable licenses (CC BY, CC BY-SA, CC0, Public Domain).

Works well for: Gram staining, influenza drift/shift, HIV replication, cell walls.
Mediocre for niche topics like archaea membranes (Wikimedia search returns old
textbook scans for those).

### 7. Pipeline survives client disconnect

Previously, reloading the page or closing the tab cancelled the pipeline
mid-run. Now:

- `cancel_event=None` passed to `run_pipeline` in worker thread (never cancel)
- Thread changed from `daemon=True` to `daemon=False` (survives request lifecycle)
- Auth token captured as string BEFORE pipeline starts (request object may be
  stale after disconnect)
- New `_save_session_direct()` takes token directly instead of reading from
  request headers
- Background worker saves session to Supabase regardless of SSE state

User can reload, close tab, navigate away — pipeline finishes and result
appears in session list.

### 8. Reader "still processing" state

When user reloads during pipeline run and clicks the session, the markdown
field is empty (pipeline hasn't finished). Previously showed "No lecture
loaded" which was misleading.

Now detects `activeSessionId` and shows spinner + "Still processing... try
refreshing in a minute" with a Refresh button.

### 9. Agent 1 reliability

**Dynamic group count** — old prompt said "8-20 groups depending on how many
distinct concepts exist". For 35-slide lectures Flash would carefully group
the first 22 slides then dump the rest into one mega-group. Now scales to
slide count: roughly 1 group per 2-3 slides. For 35 slides → "11-17 groups".

**Equal attention rule** — explicit instruction that endospores and biofilms
deserve the same care as viral capsids. If Flash is making one large group
for "everything after slide 20," it must split.

**Tighter blank detection** — old `"blank" in desc` filter was catching slides
described as "blank header area with content below". Now only filters truly
empty descriptions, exact "blank slide" matches, or "solid black with no content".
This caused a 37-page PDF to be reduced to 22 slides on one run.

### 10. 429 rate limit handling

Back-to-back pipeline runs hit Vertex AI quota limits during PDF slide
description (37 slides × parallel Flash calls). Now:

- `describe_screenshots()` retries up to 3× with 5/10/15s backoff on 429
- Reduced parallelism: 6 → 4 workers default, 3 for PDF slides
- Pipeline catches describe failures gracefully (slides get
  "[Description unavailable]" instead of crashing)

### 11. Frontend stage names updated for V3.1

Backend now sends "Planning lecture structure" instead of V2's "Preparing
teaching context". Frontend stage list updated. `VIDEO_STAGES` includes
"Describing slides" for video+PDF combos. Stage aliases handle backend name
variations.

Also: `.mp3/.m4a/.wav` files now correctly trigger `VIDEO_STAGES` (with
transcription step shown).

### 12. Case-insensitive file extension check

`.MP4` was being rejected as "Unsupported file type" because the check used
exact string match. Now `.lower()` everywhere.

### 13. Deploy speed improvements

Backend builds were slow because Cloud Build uploaded ~140MB of context every
time (data/output/, frontend/, generated screenshots).

- `.dockerignore` now excludes `data/output/`, `data/textbook_cache/`,
  `frontend-v2/`, run scripts, all test files, all PDFs/audio/video
- Dockerfile creates data dirs at build time instead of `COPY data/`
- Net: ~130MB less upload, pip install layer always cached for code-only deploys

### 14. Rest of small fixes

- KeyError on `g['slides']` when Agent 1 returns groups without that key — defensive `.get('slides', [])` everywhere
- Surgical patch when Agent 1 misses slides (~5s Flash call instead of 50s full retry)
- Orphan fallback assigns any remaining missed slides to nearest group by index
- "your professor" meta-commentary stripped from output
- Structured card prompt instructions stripped from echo
- `original_group_index` field on `SlideGroup` so textbook images reach correct writer after sequence reordering

## Results

### Lecture 2 (virology) — final local run

| Metric | Value |
|--------|-------|
| Sections | 12 |
| Words | 6,094 |
| Planning | 148s |
| Generation | 67s |
| Total | 263s (~4.5 min) |
| Cost | ~$0.28 |
| Images | 25 slide cards (writer + auto-filled) |

### Lecture 3 2008 (live deploy) — successful run

| Metric | Value |
|--------|-------|
| Sections | 13 |
| Words | 5,324 |
| Planning | 157s |
| Generation | 56s |
| Total | 272s |
| Wikimedia fallback | 2 figures (HIV, Influenza) |
| Auto-filled professor slides | 1 |
| Session save | Successful (background) |

### Cost breakdown (unchanged)

| Component | Cost | % |
|-----------|------|---|
| Pro generation (6-8 sections) | ~$0.20 | 73% |
| Pro coordinator | ~$0.03 | 11% |
| Flash planning (3 agents) | ~$0.03 | 11% |
| Flash generation (5-8 sections) | ~$0.02 | 7% |

## What's Still NOT Implemented

1. **Frontend structured card component** — CARD visuals appear as plain text
   bullets. A styled card component would make them look intentional rather
   than like missing images.

2. **Live progress polling** — frontend can't tell when a background pipeline
   finishes without manual refresh. A poll-on-mount or websocket would auto-update
   the sidebar when sessions complete.

3. **Better Wikimedia for niche topics** — archaea membranes, transport
   mechanisms still return textbook scans. Could try CDC.gov for pathogen
   topics, or have Flash generate a search query instead of using key terms
   directly.

4. **Slide numbering consistency** — coordinator's `sequence_position` reorders
   groups but slide numbers in transcript text sometimes reference original
   group indices.

5. **Teacher-Student Agent Loop (V3.2 plan)** — evaluation + conditional
   revision (Stages 3-5 from CLAUDE.md). Not started.

## Files Modified This Session

- `backend/app/main.py` — pipeline survives disconnect, background save with token, `_save_session_direct()`
- `backend/app/pipeline.py` — V3.1 routing, `.mp3` support, case-insensitive extensions, PDF slide describe + timestamps, GCS URL replacement in transcripts, reduced Flash parallelism
- `src/generator_v3.py` — `_ensure_all_slides_included()`, Agent 1 dynamic group count + equal attention rule, tighter blank detection, transcript-only mode (no slides), `original_group_index` field
- `src/screenshot_extractor.py` — 429 retry with backoff, PNG mime type, reduced default workers
- `src/textbook_search.py` — `fetch_wikimedia_image()` with multi-query search
- `src/generator_v2.py` — `_upload_wikimedia_image_to_gcs()`, Wikimedia fallback in `fetch_textbook_images()`
- `frontend/src/lib/store.ts` — V3.1 stage names, video stage detection includes audio, stage aliases
- `frontend/src/app/reader/page.tsx` — "Still processing..." state when session has no markdown yet
- `frontend/src/components/AppSidebar.tsx` — removed dead `renaming` references (TS build error)
- `Dockerfile` — includes `docs/reference/`, creates data dirs at build instead of COPY
- `.dockerignore` — excludes ~130MB of unnecessary context
- `backend/deploy.bat` — added build log dir for caching

## Git State

Master branch, all commits pushed. ~15 commits this session covering each
fix as a discrete unit.

## Deploy Notes

Backend deploy still runs `gcloud builds submit` then `gcloud run deploy`.
Cloud Run replaces revision instantly (no preview/promotion step like Vercel).
Frontend auto-deploys from git push to master via Vercel.

Both frontend and backend need redeploy for any changes in this session to take
effect on production.
