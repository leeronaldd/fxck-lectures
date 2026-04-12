# Dev Log: Self-Hosted Whisper GPU + Pipeline Speed Optimization
**Date:** 2026-04-12 11:00 AM
**Session:** ~5 hours

## What Changed

### Transcription: Gemini Flash → Self-Hosted Whisper on Cloud Run GPU
- **Problem:** Gemini Flash couldn't handle audio transcription reliably — 30s clips worked, anything >1 min timed out. Full 2-hour lecture never completed.
- **Solution:** Deployed faster-whisper on Cloud Run with NVIDIA L4 GPU in `asia-southeast1`
- **Model tested:** large-v3-turbo, medium, small — all on RTX 5070 locally
- **Final choice:** `small` + `int8` + `batch_size=64` — fastest config, pipeline corrects misspellings via textbook RAG
- **Result:** 2-hour lecture transcribed in **70 seconds** at 117x real-time, $0.016/lecture

#### Whisper Speed Progression
| Config | Time | Speed | Cost |
|--------|------|-------|------|
| Gemini Flash (before) | ∞ (never finished) | 💀 | N/A |
| Whisper turbo, beam=5, no batch | 188s | 38x | $0.041 |
| Whisper turbo, beam=1, batched | 101s | 76x | $0.021 |
| Whisper small, int8, batch64 | **70s** | **117x** | **$0.016** |

### Pipeline Cancellation
- Frontend: `AbortController` on SSE fetch — aborts on Cancel/Try Again
- Backend: `cancel_event` (threading.Event) — detects client disconnect via `request.is_disconnected()`
- Pipeline: `_check_cancelled()` between every stage — raises `PipelineCancelled` exception
- Files: `frontend/src/lib/api.ts`, `backend/app/main.py`, `backend/app/pipeline.py`

### Pipeline Parallelization
- Flash prefetch + textbook fetch now run simultaneously (saves ~20-30s)
- Pro generation bumped to `max_workers=8`
- Screenshot parallelization attempted but reverted — `extract_all()` requires chunks

### Multi-Session Pipeline (WIP)
- Zustand store refactored: `pipelineRuns` map keyed by fileId
- Sidebar shows "Processing" section with spinner + progress %
- `reset()` preserves running pipelines (New Session doesn't kill active runs)
- **Known issue:** Needs proper redesign — current approach is patches on a single-session UI

### Infrastructure
- GCP account activated (was on free trial, now full account with $377 credit)
- Cloud Run GPU quota obtained (L4 in asia-southeast1)
- Backend: `--cpu 4`, `--max-instances 50`
- Whisper service: `--gpu 1`, `--gpu-type nvidia-l4`, `--max-instances 10`
- Unified `deploy.bat` deploys both services + pushes frontend

## New Files
- `whisper-service/Dockerfile` — CUDA + faster-whisper, model baked in
- `whisper-service/main.py` — FastAPI `/transcribe` endpoint
- `whisper-service/requirements.txt`
- `whisper-service/deploy.sh`

## Modified Files
- `src/transcriber.py` — calls Whisper service (primary), Gemini Flash (fallback)
- `backend/app/main.py` — cancel_event + client disconnect detection
- `backend/app/pipeline.py` — cancellation checks + screenshot fix
- `src/generator_v2.py` — prefetch+textbook parallel, 8 workers for Pro
- `frontend/src/lib/store.ts` — per-session pipeline state
- `frontend/src/lib/api.ts` — AbortController
- `frontend/src/app/processing/page.tsx` — multi-session support
- `frontend/src/components/AppSidebar.tsx` — processing indicators
- `deploy.bat` — unified deploy for both services
- `backend/deploy.sh` — WHISPER_SERVICE_URL env var, --cpu 4

## What Worked
- **Whisper GPU transcription** — 70s for 2-hour lecture, rock solid, no rate limits
- **Pipeline cancellation** — Cancel button actually stops backend processing
- **Prefetch+textbook parallelization** — saves ~20-30s per lecture
- **Model benchmarking on RTX 5070** — tested all models, found small is fast enough

## What Broke
- **Screenshot parallelization** — `extract_all` needs chunks, can't run before chunking. Reverted.
- **Zustand computed getters** — JS `get` accessors don't work with Zustand. Fixed with `subscribe()` sync.
- **Vercel preview URLs** — each push creates new URL, old ones 404. Need to promote to production.

## Critical Finding: Depth Inversion Not Working
- Creative brief has the depth inversion instructions but Pro is ignoring them
- Every section gets ~100-200 words regardless of EI% or complexity
- Section 4 (Bacterial Envelope, EI 100%) got 117 words — should be 400+
- Section 5b (Transport, EI 95%) got 79 words — professor spent 1000+ words on this
- **Fix:** Pass EI% in per-chunk prompt with word count floors. E.g. "EI 90-100%: minimum 350 words"
- Test transcript saved: `data/transcripts/lecture2_local_turbo.txt` (14,688 words, lecture 2)
- Test video: `C:\Users\leewa\Downloads\lecture 2 .mp4`

## Still TODO (Next Session)
1. **UI overhaul** — study Claude/ChatGPT session management UX, redesign from scratch
   - Create session on "New Session" click (before upload)
   - Session persists regardless of navigation
   - Sidebar always shows all sessions with state indicators
   - Multi-upload support (upload into existing session)
2. **Promote Vercel to production** — latest preview has all changes
3. **Test full end-to-end on live site** — upload video, verify Whisper transcription → generation → reader
4. **Screenshot extraction during generation** — find a way to parallelize (maybe extract without chunk matching, match later)
5. **Deploy.bat needs testing** — unified deploy script untested end-to-end

## Architecture (Current)
```
User uploads video
    ↓
Backend (australia-southeast1, Cloud Run, 4 vCPU)
    ├── Extract audio (ffmpeg, ~25s)
    ├── Send to Whisper service (asia-southeast1, L4 GPU)
    │   └── faster-whisper small, int8, batch64 (~70s for 2hr lecture)
    ├── Chunk transcript (regex, ~10s)
    ├── Extract screenshots (OpenCV + Flash, ~30-60s)
    ├── Flash prefetch + textbook fetch (parallel, ~30s)
    └── Pro generation (8 workers parallel, ~45-60s)
    ↓
Frontend (Vercel) renders slides + transcript split view
```

## Metrics
| Metric | Before | After |
|--------|--------|-------|
| Transcription | Never finished (Gemini Flash) | 70s (Whisper GPU) |
| Transcription cost | N/A | $0.016 |
| Pipeline total (estimated) | 4-6 min | ~2.5-3 min |
| Max concurrent users | 3 | 50 (backend) / 10 (Whisper GPU) |
| Rate limits | Groq 2hr/hr, Gemini unreliable | None |
