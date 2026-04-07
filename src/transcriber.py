"""Speech-to-text transcription using Groq Whisper API.

Extracts audio from video files and transcribes using Whisper Large v3 Turbo
at $0.04/hour — 18x cheaper than OpenAI, 24x cheaper than Google Cloud STT.
"""

import os
import subprocess
import tempfile
import math
from pathlib import Path

from groq import Groq

from src.config import GROQ_API_KEY, TRANSCRIPTION_MODEL

# Groq limits: 25MB free tier, 100MB dev tier
MAX_FILE_SIZE_MB = 25
CHUNK_DURATION_MINUTES = 20  # safe chunk size for most audio formats
OVERLAP_SECONDS = 30  # overlap between chunks to avoid cutting mid-sentence


def get_client() -> Groq:
    api_key = GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Get one free at https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


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
        "-ar", "16000",  # 16kHz sample rate — Whisper's native rate
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


def split_audio(audio_path: str, chunk_duration_s: int, overlap_s: int) -> list[str]:
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


def transcribe_file(
    audio_path: str,
    language: str = "en",
    prompt: str = None,
    timestamps: bool = False,
) -> dict:
    """Transcribe a single audio file via Groq Whisper.

    Args:
        audio_path: Path to audio file (mp3, wav, etc.)
        language: ISO-639-1 language code
        prompt: Optional context hint for medical terms (max 224 tokens)
        timestamps: If True, return word-level timestamps

    Returns:
        dict with 'text' and optionally 'segments' keys
    """
    client = get_client()

    kwargs = {
        "model": TRANSCRIPTION_MODEL,
        "language": language,
        "temperature": 0.0,  # deterministic for accuracy
    }

    if timestamps:
        kwargs["response_format"] = "verbose_json"
        kwargs["timestamp_granularities"] = ["segment"]
    else:
        kwargs["response_format"] = "verbose_json"

    if prompt:
        kwargs["prompt"] = prompt[:800]  # 224 tokens ≈ ~800 chars

    with open(audio_path, "rb") as f:
        kwargs["file"] = (Path(audio_path).name, f)
        result = client.audio.transcriptions.create(**kwargs)

    output = {"text": result.text}
    if hasattr(result, "segments") and result.segments:
        output["segments"] = [
            {
                "start": s.start if hasattr(s, "start") else s.get("start"),
                "end": s.end if hasattr(s, "end") else s.get("end"),
                "text": s.text if hasattr(s, "text") else s.get("text"),
            }
            for s in result.segments
        ]

    return output


def transcribe(
    input_path: str,
    language: str = "en",
    medical_terms: list[str] = None,
    timestamps: bool = False,
) -> dict:
    """Transcribe a video or audio file. Handles chunking for large files.

    Args:
        input_path: Path to video (.mp4, .mkv, etc.) or audio (.mp3, .wav, etc.)
        language: ISO-639-1 language code
        medical_terms: Optional list of expected medical terms to improve accuracy
        timestamps: If True, include segment-level timestamps

    Returns:
        dict with 'text', optionally 'segments', and 'metadata'
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

    # Build prompt hint with medical terms for better accuracy
    prompt = None
    if medical_terms:
        prompt = "Medical lecture transcript. Key terms: " + ", ".join(medical_terms[:30])

    try:
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        duration = get_audio_duration(audio_path)

        if file_size_mb <= MAX_FILE_SIZE_MB:
            # Single file — no chunking needed
            print(f"Transcribing {duration/60:.1f} min audio ({file_size_mb:.1f}MB)...")
            result = transcribe_file(audio_path, language, prompt, timestamps)
        else:
            # Split into chunks
            chunk_duration_s = CHUNK_DURATION_MINUTES * 60
            n_chunks = math.ceil(duration / (chunk_duration_s - OVERLAP_SECONDS))
            print(f"Audio is {file_size_mb:.1f}MB — splitting into {n_chunks} chunks...")

            chunk_paths = split_audio(audio_path, chunk_duration_s, OVERLAP_SECONDS)
            all_text = []
            all_segments = []
            offset = 0.0

            for i, chunk_path in enumerate(chunk_paths):
                print(f"  Transcribing chunk {i+1}/{len(chunk_paths)}...")
                try:
                    chunk_result = transcribe_file(chunk_path, language, prompt, timestamps)
                    all_text.append(chunk_result["text"])

                    if "segments" in chunk_result:
                        for seg in chunk_result["segments"]:
                            seg["start"] += offset
                            seg["end"] += offset
                        all_segments.extend(chunk_result["segments"])
                finally:
                    os.unlink(chunk_path)

                offset += (CHUNK_DURATION_MINUTES * 60) - OVERLAP_SECONDS

            result = {"text": " ".join(all_text)}
            if all_segments:
                result["segments"] = all_segments

        result["metadata"] = {
            "duration_seconds": duration,
            "duration_minutes": round(duration / 60, 1),
            "file_size_mb": round(file_size_mb, 1),
            "model": TRANSCRIPTION_MODEL,
            "estimated_cost_usd": round(duration / 3600 * 0.04, 4),
        }
        return result

    finally:
        if cleanup_audio and os.path.exists(audio_path):
            os.unlink(audio_path)
