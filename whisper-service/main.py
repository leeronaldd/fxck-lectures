"""Whisper STT service — GPU-accelerated transcription on Cloud Run.

Receives audio file, returns full transcript. No chunking needed.
Uses faster-whisper with large-v3-turbo + batched inference for max speed.
"""

import os
import tempfile
import time

from fastapi import FastAPI, File, UploadFile
from faster_whisper import WhisperModel, BatchedInferencePipeline

app = FastAPI()

# Load model once at startup (already baked into Docker image)
MODEL = None
BATCHED = None


@app.on_event("startup")
def load_model():
    global MODEL, BATCHED
    print("Loading Whisper model...")
    start = time.time()
    MODEL = WhisperModel(
        "small",
        device="cuda",
        compute_type="int8",
    )
    # Batched pipeline processes multiple audio chunks in parallel on the GPU
    BATCHED = BatchedInferencePipeline(model=MODEL)
    print(f"Model loaded in {time.time() - start:.1f}s")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": MODEL is not None}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribe an uploaded audio/video file.

    Accepts any format ffmpeg can read (mp3, mp4, wav, etc.).
    Returns the full transcript as JSON.
    """
    start = time.time()

    # Save uploaded file to disk (faster-whisper needs a file path)
    suffix = os.path.splitext(file.filename or "audio.mp3")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        file_size_mb = len(content) / (1024 * 1024)
        print(f"Transcribing {file.filename} ({file_size_mb:.1f} MB)...")

        # Batched inference — processes audio chunks in parallel on GPU
        # batch_size=16 means 16 chunks at once (L4 has 24GB VRAM, plenty)
        segments, info = BATCHED.transcribe(
            tmp_path,
            language="en",
            beam_size=1,
            batch_size=64,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        # Collect all segments
        all_text = []
        for segment in segments:
            all_text.append(segment.text.strip())

        text = " ".join(all_text)
        word_count = len(text.split())
        elapsed = time.time() - start
        duration_min = info.duration / 60

        print(f"  Duration:  {duration_min:.1f} min")
        print(f"  Words:     {word_count}")
        print(f"  Time:      {elapsed:.1f}s")
        print(f"  Speed:     {info.duration / elapsed:.1f}x real-time")

        return {
            "text": text,
            "metadata": {
                "duration_seconds": info.duration,
                "duration_minutes": round(duration_min, 1),
                "word_count": word_count,
                "processing_seconds": round(elapsed, 1),
                "speed_factor": round(info.duration / elapsed, 1),
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
            },
        }
    finally:
        os.unlink(tmp_path)
