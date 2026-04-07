# Dev Log: 2026-04-07 — STT Transcription Pipeline (Stage 0)

## What Changed

### New: Speech-to-Text pipeline via Groq Whisper
- Added `src/transcriber.py` — Groq Whisper API wrapper with auto audio extraction + chunking for large files
- Added `run_transcribe.py` — standalone CLI for transcription
- Modified `run_stage1.py` — now accepts video/audio files directly (auto-transcribes before chunking)
- Updated `src/config.py` — added `GROQ_API_KEY` and `TRANSCRIPTION_MODEL` config
- Installed `groq` Python package

### Model chosen: `whisper-large-v3-turbo` on Groq
- **$0.04/hour** — cheapest hosted STT API available (April 2026)
- 216x real-time speed (~30 seconds for a 2-hour lecture)
- Distil-Whisper was even cheaper ($0.02/hr) but was **deprecated Aug 2025**

## Test Results: Groq Whisper vs Old Transcript (Turbo AI/NotebookLM)

Tested on `Bad Professor Lecture.mp4` (66MB video, 115 min lecture):

| Metric | Old (Turbo AI) | New (Groq Whisper) |
|--------|---------------|-------------------|
| Medical term errors | 12 misspellings | **0 misspellings** |
| Correct medical terms | 13 instances | **74 instances** |
| Filler words | 710 | 285 |
| Word count | 12,008 | 15,017 (more content captured) |
| Cost | Unknown | **$0.077** |

### Key medical terms now correctly transcribed:
- "kosahhedral" → **icosahedral** (correct)
- "viron" → **virion** (correct)
- "Khesi virus" → **Calicivirus** (correct)
- "oosahedral" → **icosahedral** (correct)

### Known Issue
- Whisper hallucinates ~50 words of gibberish during silent setup portion at start of lecture (before professor starts talking). Harmless — chunker ignores nonsensical text.

## Research: Full STT Landscape (April 2026)

### Pricing comparison (per hour of audio)
| Provider | Model | $/Hour |
|----------|-------|--------|
| **Groq** | whisper-large-v3-turbo | **$0.04** (winner) |
| Fireworks AI | Whisper v3 batch | $0.054 |
| Together AI | Whisper v3 | $0.09 |
| Soniox | v4 async | $0.10 |
| Alibaba | Qwen3-ASR-Flash | $0.126 |
| AssemblyAI | Universal-2 | $0.15 |
| OpenAI | GPT-4o Mini Transcribe | $0.18 |
| ElevenLabs | Scribe v2 | $0.22 (best accuracy: 2.3% WER) |
| Google Cloud | Chirp 3 | $0.96 |

### Models investigated but rejected:
- **Distil-Whisper (Groq)**: Deprecated Aug 2025
- **Qwen3-ASR (Alibaba)**: $0.126/hr — 3x more expensive than Groq for similar accuracy
- **SiliconFlow SenseVoice**: NOT free for STT (free tier only applies to LLMs <14B)
- **Google Cloud STT**: $0.96/hr — save Vertex AI credits for Gemini Pro generation
- **Self-hosted (faster-whisper, SenseVoice)**: Only economical at 500+ hrs/month
- **Chinese platforms (iFLYTEK, Baidu, Tencent)**: Free trials but limited/temporary

### Vertex AI option explored:
- Gemini Flash CAN transcribe audio directly (~$0.02-0.05/hr estimated)
- Would consolidate stack (one API, one bill) but untested accuracy on medical terms
- Worth exploring in future session

## What Works
- Full video-to-chunks pipeline: `python run_stage1.py lecture.mp4 --preview`
- Medical term accuracy dramatically better than previous Turbo AI transcripts
- Cost is negligible: ~$0.08 per lecture, ~$1.60/month projected

## What's Still Broken / Next Steps
- Whisper start-of-audio hallucination — could add trim logic to detect first real English sentence
- Filler word stripping — could add post-STT cleanup pass (cheap, regex-based)
- Haven't tested Gemini Flash as STT alternative (would eliminate Groq dependency)
- Stage 3-5 (teacher-student agent loop) still not implemented

## New Usage

```bash
# From video (new!)
python run_stage1.py "Bad Professor Lecture.mp4" --preview
python run_stage1.py lecture.mp4 --terms "icosahedral,peptidoglycan" --preview

# From transcript (unchanged)
python run_stage1.py "data/transcripts/Bad Professor transcript.txt" --preview

# Standalone transcription
python run_transcribe.py "Bad Professor Lecture.mp4" --timestamps --json
```

## Cost Summary
| Component | Cost per lecture |
|-----------|----------------|
| STT (Groq Whisper) | $0.08 |
| Gemini Flash (CI%, grouping, completeness) | ~$0.02 |
| Gemini Pro (generation) | ~$0.15 |
| **Total** | **~$0.25/lecture** |
