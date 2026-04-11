"""Speech-to-text transcription via self-hosted Whisper on Cloud Run GPU.

Sends audio to our own faster-whisper service running on Cloud Run with
NVIDIA L4 GPU. No rate limits, no chunking, ~$0.035 per 2-hour lecture.

Falls back to Gemini Flash for local dev if WHISPER_SERVICE_URL is not set.
"""

import os
import subprocess
import time
from pathlib import Path

import requests
import google.auth
import google.auth.transport.requests


WHISPER_SERVICE_URL = os.environ.get("WHISPER_SERVICE_URL", "")


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


def _get_id_token(audience: str) -> str:
    """Get a Google ID token for authenticating to Cloud Run (no-allow-unauthenticated)."""
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    # Use the IAM credentials API to generate an ID token
    from google.oauth2 import id_token
    token = id_token.fetch_id_token(auth_req, audience)
    return token


def _transcribe_via_whisper_service(audio_path: str) -> dict:
    """Send audio file to our Whisper Cloud Run service for transcription."""
    print(f"Sending to Whisper service at {WHISPER_SERVICE_URL}...")
    start = time.time()

    # Get ID token for Cloud Run auth
    token = _get_id_token(WHISPER_SERVICE_URL)

    # Upload the audio file
    with open(audio_path, "rb") as f:
        response = requests.post(
            f"{WHISPER_SERVICE_URL}/transcribe",
            files={"file": (Path(audio_path).name, f, "audio/mpeg")},
            headers={"Authorization": f"Bearer {token}"},
            timeout=900,  # 15 min max for very long lectures
        )

    if response.status_code != 200:
        raise RuntimeError(f"Whisper service error {response.status_code}: {response.text}")

    result = response.json()
    elapsed = time.time() - start

    print(f"  Whisper transcription complete in {elapsed:.1f}s")
    print(f"  Words: {result['metadata']['word_count']}")
    print(f"  Speed: {result['metadata'].get('speed_factor', '?')}x real-time")

    return result


def _transcribe_via_gemini(audio_path: str, duration: float) -> dict:
    """Fallback: transcribe using Gemini Flash (for local dev without Whisper service)."""
    from google import genai
    from google.genai import types
    from src.config import GCP_PROJECT_ID, GCP_LOCATION, CHUNKER_FALLBACK_MODEL

    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"Transcribing {duration/60:.1f} min audio ({file_size_mb:.1f}MB) with Gemini Flash (fallback)...")
    print(f"  ⚠ Gemini Flash may be slow/unreliable for long audio. Set WHISPER_SERVICE_URL for production.")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    parts = [
        types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3"),
        types.Part.from_text(text=(
            "Transcribe this audio word for word. Do not summarize, do not skip "
            "anything, do not clean up the speaker's language. Output every single "
            "word as spoken, including filler words (um, uh, so, okay, right, like), "
            "repetitions, false starts, and incomplete sentences. Do not merge or "
            "paraphrase any content. Do not add punctuation that changes meaning. "
            "The output should have the SAME word count as the spoken audio. "
            "This is a university lecture recording — transcribe it as if you are "
            "a court stenographer capturing every utterance."
        )),
    ]

    response = client.models.generate_content(
        model=CHUNKER_FALLBACK_MODEL,
        contents=parts,
        config={
            "temperature": 0.0,
            "max_output_tokens": 65536,
        },
    )

    text = response.text.strip()
    word_count = len(text.split())
    estimated_tokens = duration * 32
    estimated_cost = estimated_tokens / 1_000_000 * 0.10

    return {
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


def transcribe(
    input_path: str,
    language: str = "en",
    medical_terms: list[str] = None,
    timestamps: bool = False,
) -> dict:
    """Transcribe a video or audio file.

    Primary: sends to self-hosted Whisper service on Cloud Run GPU.
    Fallback: Gemini Flash multimodal (for local dev).

    Args:
        input_path: Path to video (.mp4, .mkv, etc.) or audio (.mp3, .wav, etc.)
        language: ISO-639-1 language code
        medical_terms: Optional list of expected medical terms
        timestamps: If True, include segment-level timestamps

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

        # Primary: Whisper service (production)
        if WHISPER_SERVICE_URL:
            result = _transcribe_via_whisper_service(audio_path)
        else:
            # Fallback: Gemini Flash (local dev only)
            result = _transcribe_via_gemini(audio_path, duration)

        print(f"  Duration:  {duration/60:.1f} min")
        print(f"  Words:     {result['metadata']['word_count']}")

        return result

    finally:
        if cleanup_audio and os.path.exists(audio_path):
            os.unlink(audio_path)
