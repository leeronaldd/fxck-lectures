"""Speech-to-text transcription using Gemini Flash multimodal.

Extracts audio from video files and transcribes using Gemini Flash's
native audio understanding — no rate limits, ~$0.02 per 2-hour lecture.

Falls back to Groq Whisper if Gemini fails (optional).
"""

import os
import subprocess
import tempfile
import math
from pathlib import Path

from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL


def extract_audio(video_path: str, output_path: str = None) -> str:
    """Extract audio from video file using ffmpeg. Returns path to audio file."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_path is None:
        output_path = str(video_path.with_suffix(".mp3"))

    # mp3 at 64kbps mono — small files, good enough for speech
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn",  # no video
        "-ac", "1",  # mono
        "-ab", "64k",  # 64kbps — speech doesn't need more
        "-ar", "16000",  # 16kHz sample rate
        "-y",  # overwrite
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return output_path


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def split_audio(audio_path: str, chunk_duration_s: int, overlap_s: int = 30) -> list[str]:
    """Split audio into overlapping chunks. Returns list of temp file paths."""
    total_duration = get_audio_duration(audio_path)
    step = chunk_duration_s - overlap_s
    chunks = []
    start = 0

    while start < total_duration:
        end = min(start + chunk_duration_s, total_duration)
        chunk_path = tempfile.mktemp(suffix=".mp3")

        cmd = [
            "ffmpeg", "-i", audio_path,
            "-ss", str(start),
            "-t", str(end - start),
            "-ac", "1", "-ab", "64k", "-ar", "16000",
            "-y", chunk_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg chunk split failed: {result.stderr}")

        chunks.append(chunk_path)
        start += step

    return chunks


def _transcribe_chunk_gemini(audio_bytes: bytes, chunk_index: int = 0, total_chunks: int = 1) -> str:
    """Transcribe a single audio chunk using Gemini Flash multimodal.

    Gemini natively understands audio — no separate STT API needed.
    Cost: ~32 tokens/second of audio at $0.10/M tokens = ~$0.01/hr.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )

    parts = [
        types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3"),
        types.Part.from_text(text=(
            "Transcribe this audio precisely. This is a university lecture. "
            "Output ONLY the transcription text — no timestamps, no speaker labels, "
            "no commentary. Preserve the speaker's exact words including filler words "
            "like 'um', 'so', 'okay'. Do not correct grammar or rephrase anything."
        )),
    ]

    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=parts,
        config={
            "temperature": 0.0,
            "max_output_tokens": 8192,
        },
    )

    return response.text.strip()


# Gemini has input limits — split audio into ~20 min chunks
CHUNK_DURATION_MINUTES = 20
MAX_SINGLE_FILE_MB = 20  # Send directly if under this size


def transcribe(
    input_path: str,
    language: str = "en",
    medical_terms: list[str] = None,
    timestamps: bool = False,
) -> dict:
    """Transcribe a video or audio file using Gemini Flash.

    Handles chunking for long files. No rate limits, no external API keys needed.

    Args:
        input_path: Path to video (.mp4, .mkv, etc.) or audio (.mp3, .wav, etc.)
        language: ISO-639-1 language code (currently unused — Gemini auto-detects)
        medical_terms: Optional list of expected medical terms (unused with Gemini)
        timestamps: If True, include segment-level timestamps (not supported with Gemini)

    Returns:
        dict with 'text' and 'metadata'
    """
    input_path = str(Path(input_path).resolve())
    ext = Path(input_path).suffix.lower()

    # Video formats need audio extraction
    video_exts = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
    audio_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac"}

    if ext in video_exts:
        print(f"Extracting audio from video...")
        audio_path = extract_audio(input_path)
        cleanup_audio = True
    elif ext in audio_exts:
        audio_path = input_path
        cleanup_audio = False
    else:
        raise ValueError(f"Unsupported format: {ext}. Supported: {video_exts | audio_exts}")

    try:
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        duration = get_audio_duration(audio_path)

        if file_size_mb <= MAX_SINGLE_FILE_MB:
            # Single file — no chunking needed
            print(f"Transcribing {duration/60:.1f} min audio ({file_size_mb:.1f}MB) with Gemini Flash...")
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            text = _transcribe_chunk_gemini(audio_bytes)
        else:
            # Split into chunks for long lectures
            chunk_duration_s = CHUNK_DURATION_MINUTES * 60
            chunk_paths = split_audio(audio_path, chunk_duration_s)
            n_chunks = len(chunk_paths)
            print(f"Audio is {file_size_mb:.1f}MB — splitting into {n_chunks} chunks...")

            all_text = []
            for i, chunk_path in enumerate(chunk_paths):
                print(f"  Transcribing chunk {i+1}/{n_chunks}...")
                try:
                    with open(chunk_path, "rb") as f:
                        chunk_bytes = f.read()
                    chunk_text = _transcribe_chunk_gemini(chunk_bytes, i, n_chunks)
                    all_text.append(chunk_text)
                finally:
                    os.unlink(chunk_path)

            text = " ".join(all_text)

        word_count = len(text.split())
        # Gemini Flash: ~32 tokens/sec audio, $0.10/M input tokens
        estimated_tokens = duration * 32
        estimated_cost = estimated_tokens / 1_000_000 * 0.10

        result = {
            "text": text,
            "metadata": {
                "duration_seconds": duration,
                "duration_minutes": round(duration / 60, 1),
                "file_size_mb": round(file_size_mb, 1),
                "model": CHUNKER_FALLBACK_MODEL,
                "estimated_cost_usd": round(estimated_cost, 4),
                "word_count": word_count,
            },
        }
        print(f"  Duration:  {duration/60:.1f} min")
        print(f"  Est. cost: ${estimated_cost:.3f}")
        print(f"  Words:     {word_count}")

        return result

    finally:
        if cleanup_audio and os.path.exists(audio_path):
            os.unlink(audio_path)
