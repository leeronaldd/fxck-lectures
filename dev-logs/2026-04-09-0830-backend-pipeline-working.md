# Dev Log — 2026-04-09 08:30 — Backend Pipeline Working End-to-End

## What Changed

### Critical Fixes (this session)
- **JWT auth**: Supabase uses ES256 (ECDSA), not HS256/RS256. Updated `backend/app/auth.py` to read `alg` from token header and use JWKS endpoint
- **Cloud Run instance death**: Pipeline ran in background thread, Cloud Run killed the instance. Fixed by running pipeline in a thread with SSE keepalive comments every 5 seconds from an async generator
- **Multi-instance file loss**: Upload went to instance A, `/api/run/` hit instance B. Fixed with `--max-instances 1`
- **Markdown assembly**: Generator saves JSON (not markdown). Added assembly step to extract `explanation_text` fields and format as markdown with `## headings`
- **Reader page crash**: Fallback to static files (`v4_*.json`) 404'd on Vercel. Added try/catch
- **XHR upload blocking**: Switched from XMLHttpRequest back to fetch for upload (XHR was silently failing after CORS preflight)
- **Proxy buffering**: Added `X-Accel-Buffering: no` and `Cache-Control: no-cache` to SSE response headers

### Architecture Change
**Before**: Upload → start background thread → poll `/api/status/` every 2s
**After**: Upload → single SSE stream via `/api/run/{file_id}` that runs pipeline synchronously with keepalive heartbeats

### Backend Endpoints (simplified)
- `POST /api/upload` — upload .txt file, returns file_id
- `GET /api/run/{file_id}` — SSE stream, runs full pipeline, yields progress events + final output
- `GET /api/health` — health check

Removed: `/api/process`, `/api/status/{job_id}`, `/api/sessions`, `/api/sessions/{id}` (no longer needed with SSE approach)

## What Works
- Full pipeline end-to-end: upload .txt → chunking → CI scoring → concept grouping → Gemini Pro generation (with textbook RAG from OpenStax) → fact checking → completeness → markdown assembly → reader page
- Google OAuth sign-in
- Guest mode (upload page accessible, sign-in required for processing)
- SSE streaming keeps Cloud Run alive during 2-3 minute generation
- Processing page shows stage progress in real-time
- Reader page renders generated markdown with proper formatting

## What's Broken / Needs Fixing
1. **Reader formatting**: narrow layout, missing sidebar/TOC, no trust bar, no concept group navigation — reader was designed for the original static data with extras
2. **Hamburger menu**: not working on reader page
3. **Video upload**: returns 413 (too large). Need Supabase Storage or browser audio extraction
4. **No session persistence**: outputs are lost when Cloud Run instance restarts
5. **Vertex AI rate limits**: 429 errors on CI scoring (falls back to heuristic, non-fatal)
6. **Processing page**: stages update but sometimes too fast to see (chunking/scoring/grouping happen in seconds, only generation takes time)
7. **Static fallback files**: removed from Vercel, old sessions in sidebar (Virology/Immunology/Anatomy) don't work

## Deploy Commands
```cmd
# Backend (from project root)
gcloud builds submit --project project-bc1fc31b-94c5-44b0-904 --tag australia-southeast1-docker.pkg.dev/project-bc1fc31b-94c5-44b0-904/fxck-lectures-api/backend --timeout=600s

gcloud run deploy fxck-lectures-api --project project-bc1fc31b-94c5-44b0-904 --image australia-southeast1-docker.pkg.dev/project-bc1fc31b-94c5-44b0-904/fxck-lectures-api/backend --region australia-southeast1 --platform managed --allow-unauthenticated --memory 2Gi --timeout 900 --no-cpu-throttling --max-instances 1

# Frontend auto-deploys on push to style-transfer-v1
```

## Costs This Session
- ~5-6 test pipeline runs with short transcripts (~$0.05-0.10 each)
- ~10 Cloud Run builds ($0.00 — free tier)
- Total: ~$0.50-0.60

## Late Fixes (same session)
- Fixed 283% progress bar — `subProgress` was backend's 0-100% but stepper treated it as sub-item count
- Removed fake mock sessions (Virology/Immunology/Anatomy) — sidebar now empty until session persistence is built
- Fixed reader page sidebar — hamburger now works on reader page
- Fixed QUIC protocol error — added `Alt-Svc: clear` header to SSE response

## Next Session Priorities
1. **Full UI audit** — sweep every button, link, and UI element; fix all non-functional ones in one go
2. Add video upload support (browser audio extraction or Supabase Storage)
3. Session persistence (save outputs to Supabase DB)
4. "Chunking transcript" stage takes too long to show progress — add intermediate progress events
