# Dev Log: V2 Pipeline Full Rebuild
**Date:** 2026-04-12 01:00 AM
**Session:** ~6 hours

## What Changed

### Architecture: V1 → V2 Pipeline
Replaced the entire 8-stage V1 pipeline with a 3-stage V2 architecture:
- **Old:** Chunk → CI% Score → Concept Group → Generate → Fact Check → Completeness → Slide Insert → Assemble (~67 API calls, ~13 min)
- **New:** Flash Prefetch → Flash Textbook → Pro Generate (~16 API calls, ~3 min, all parallel)

### Core Files Created
- `src/generator_v2.py` — Full pipeline with creative brief (~1600 lines)
- `run_v2.py` — CLI runner for local testing
- `frontend/src/components/SlideCard.tsx` — Slide card renderer (professor_slide vs diagram types)
- `frontend/src/components/NarrativeSection.tsx` — Transcript renderer with inline markdown
- `frontend/src/components/ImageLightbox.tsx` — Click-to-expand image viewer

### Core Files Modified
- `backend/app/pipeline.py` — Swapped to V2's `generate_lecture()`
- `backend/app/main.py` — Added `/api/upload-slides` + `/api/screenshots/{filename}`
- `frontend/src/app/reader/page.tsx` — V2 slides+transcript split view (with V1 fallback)
- `frontend/src/app/preview/page.tsx` — Interactive V2 preview page with test data
- `frontend/src/app/page.tsx` — Landing page mockup updated to V2 layout
- `frontend/src/app/upload/page.tsx` — Optional slides PDF upload slot
- `frontend/src/lib/store.ts` — V2 stages (4-6 instead of 9), slides upload flow
- `frontend/src/lib/api.ts` — `uploadSlides()`, updated PipelineEvent type
- `frontend/src/lib/types.ts` — SlideCard, TranscriptSection interfaces
- `src/transcriber.py` — Replaced Groq Whisper with Gemini Flash multimodal
- `src/config.py` — Updated transcription model reference
- `src/screenshot_extractor.py` — Switched from JPEG to PNG output

### Creative Brief (System Prompt)
The entire generation quality comes from one creative brief in `generator_v2.py`:
- Role: "You are my anatomy professor" with style transfer from gold standard
- One full anatomy lecture transcript as example (Topic 2.5b)
- 50 teaching observations analyzing what makes her writing exceptional
- Three spotlighted habits that needed extra weight
- Professor unreliability on exam scope
- Textbook wins on scope (not just facts)
- Depth allocation inversion (transcript length = noise)
- Medical mnemonics (established ones only)
- No duplicate labels (exam tip prefix handled by frontend)

### Prompt Iterations Tested
1. Both examples + 50 observations → good but some habits missed
2. Added 3 spotlighted habits → gap-before-fact, never-end, slides-as-co-teacher landed
3. Stripped Example 2 → tighter output, less attention dilution
4. Professor slides priority → professor first, OpenStax fallback
5. Professor unreliability → EI% based on global curriculum, not professor claims
6. Textbook scope override → teach what professor skipped if commonly tested
7. Depth inversion → condense rambling, expand skimmed content

## What Worked
- **Quality:** V2 output reads like the anatomy professor. Gap-before-fact, forward momentum, slides as co-teachers all landing consistently
- **Speed:** 3 min for a full 2-hour lecture (vs 13 min V1)
- **Cost:** ~$0.15-0.20 per lecture (vs ~$0.25 V1)
- **Context caching:** Pays for the ~16K token creative brief once per lecture
- **Parallel execution:** Flash prefetch 10s (was 80s sequential), Pro all chunks at once
- **Professor slide integration:** Screenshots mapped to chunks, Pro references them spatially

## What Broke / Needs Fixing
- **Gemini Flash transcription:** `max_output_tokens=8192` caused 71% content loss (3,420 vs 12,008 words). Fixed to 65536 but untested after fix
- **Broken images on live site:** Screenshots on Cloud Run, frontend on Vercel. Fixed with `/api/screenshots/` endpoint but needs backend redeploy
- **Vercel preview-only deploys:** `master` branch → Preview, not Production. Must manually promote. User keeping this as staging workflow
- **Transcription quality:** Flash may still summarize instead of transcribing verbatim — needs testing with stronger prompt

## Still TODO (Next Session)
1. **Verify Flash transcription** — rerun comparison test after `max_output_tokens` fix
2. **Redeploy backend** — user needs to run `deploy.bat` for all backend changes
3. **Promote Vercel** — latest preview has all V2 frontend changes
4. **Test full end-to-end** — upload video on live site, verify screenshots extract, reader renders
5. **Transcript persistence** — raw transcripts lost when Cloud Run container scales down, consider saving to Supabase/GCS

## Metrics

| Metric | V1 | V2 |
|--------|----|----|
| Pipeline stages | 8 | 3 |
| API calls per lecture | ~67 | ~16 |
| Pipeline time (2hr lecture) | ~13 min | ~3 min |
| Cost per lecture | ~$0.25 | ~$0.15-0.20 |
| Transcription | Groq Whisper ($0.08/2hr, rate limited) | Gemini Flash ($0.02/2hr, no limit) |
| Output format | Single markdown string | Structured slides[] + transcript[] JSON |
| Frontend layout | Single-pane markdown | 50/50 slides + transcript split |
