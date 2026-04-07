"""Slide-based chunking: map transcript text to detected lecture slides.

Uses slide transition timestamps from screenshot extraction to chunk the transcript
into slide-aligned segments. This replaces regex-based chunking when video is available.
"""

import json
import re
from pathlib import Path

from src.models import SlideChunk, EmphasisSignal
from src.chunker import extract_emphasis, extract_technical_terms


def _load_screenshots(screenshots_path: str) -> list[dict]:
    """Load screenshot metadata sorted by timestamp."""
    with open(screenshots_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data, key=lambda x: x["timestamp_seconds"])


def _load_transcript(transcript_path: str) -> str:
    """Load transcript text."""
    with open(transcript_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or H:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _snap_to_sentence(text: str, word_pos: int) -> int:
    """Snap a word position to the nearest sentence boundary.

    Looks for the nearest period/question mark/exclamation within ±50 words.
    Returns the word position just after the sentence boundary.
    """
    words = text.split()
    if word_pos >= len(words):
        return len(words)
    if word_pos <= 0:
        return 0

    # Search forward first (prefer not cutting mid-sentence)
    search_range = 50
    for i in range(word_pos, min(word_pos + search_range, len(words))):
        word = words[i]
        if word.endswith(('.', '?', '!')):
            return i + 1

    # Search backward
    for i in range(word_pos, max(word_pos - search_range, 0), -1):
        word = words[i]
        if word.endswith(('.', '?', '!')):
            return i + 1

    # No sentence boundary found, use raw position
    return word_pos


def _derive_topic_name(slide_description: str, transcript_segment: str) -> str:
    """Derive a short topic name from the slide description or transcript content."""
    if slide_description and len(slide_description) > 10:
        # Extract key phrases from the description
        desc = slide_description.strip()
        # Try to find a bolded term
        bold_match = re.search(r'\*\*(.+?)\*\*', desc)
        if bold_match:
            return bold_match.group(1).strip()[:60]
        # Use first meaningful clause
        first_sentence = desc.split('.')[0].strip()
        if len(first_sentence) > 60:
            first_sentence = first_sentence[:57] + "..."
        return first_sentence

    # Fallback: first few meaningful words from transcript
    words = transcript_segment.split()[:15]
    return " ".join(words)[:60]


def chunk_by_slides(
    transcript_path: str,
    screenshots_path: str,
    video_duration: float | None = None,
    sub_chunk_threshold: int = 800,
) -> list[SlideChunk]:
    """Chunk transcript text by detected slide transitions.

    Args:
        transcript_path: path to transcript text file
        screenshots_path: path to screenshots.json from Stage 1.5b
        video_duration: total video duration in seconds (auto-detected if None)
        sub_chunk_threshold: word count above which a slide gets flagged for sub-chunking
    """
    # Load data
    screenshots = _load_screenshots(screenshots_path)
    transcript = _load_transcript(transcript_path)
    words = transcript.split()
    total_words = len(words)

    if not screenshots:
        raise ValueError("No screenshots found — cannot chunk by slides")

    # Determine video duration
    if video_duration is None:
        # Estimate from last screenshot + some buffer
        last_ts = screenshots[-1]["timestamp_seconds"]
        video_duration = last_ts + 120  # assume ~2 min after last slide

    # Calculate average words per second
    wps = total_words / video_duration

    # Build slide time ranges
    slide_ranges = []
    for i, ss in enumerate(screenshots):
        t_start = ss["timestamp_seconds"]
        t_end = screenshots[i + 1]["timestamp_seconds"] if i + 1 < len(screenshots) else video_duration
        slide_ranges.append({
            "index": i,
            "screenshot": ss,
            "t_start": t_start,
            "t_end": t_end,
        })

    # Map word positions to slides
    slide_chunks = []
    for sr in slide_ranges:
        # Estimate word positions from timestamps
        w_start_raw = int(sr["t_start"] * wps)
        w_end_raw = int(sr["t_end"] * wps)

        # Clamp to valid range
        w_start_raw = max(0, min(w_start_raw, total_words))
        w_end_raw = max(w_start_raw, min(w_end_raw, total_words))

        # Snap to sentence boundaries
        w_start = _snap_to_sentence(transcript, w_start_raw)
        w_end = _snap_to_sentence(transcript, w_end_raw)

        # Ensure no overlap with previous chunk
        if slide_chunks and w_start < slide_chunks[-1]["w_end"]:
            w_start = slide_chunks[-1]["w_end"]

        # Ensure we have at least some words
        if w_end <= w_start:
            w_end = min(w_start + 10, total_words)

        segment_words = words[w_start:w_end]
        segment_text = " ".join(segment_words)
        word_count = len(segment_words)

        slide_chunks.append({
            "sr": sr,
            "w_start": w_start,
            "w_end": w_end,
            "text": segment_text,
            "word_count": word_count,
        })

    # Merge tiny slides (< 30 words) into their predecessor
    merged_chunks = []
    for sc in slide_chunks:
        if merged_chunks and sc["word_count"] < 30:
            # Merge into previous
            prev = merged_chunks[-1]
            prev["text"] += " " + sc["text"]
            prev["word_count"] += sc["word_count"]
            prev["w_end"] = sc["w_end"]
            prev["sr"]["t_end"] = sc["sr"]["t_end"]
            # Keep the previous slide's screenshot (the tiny one is usually a navigation artifact)
        else:
            merged_chunks.append(sc)
    slide_chunks = merged_chunks

    # Build SlideChunk objects
    result = []
    for i, sc in enumerate(slide_chunks):
        sr = sc["sr"]
        ss = sr["screenshot"]

        # Run emphasis detection (reuse from chunker.py)
        emphasis_score, emphasis_signals = extract_emphasis(sc["text"])

        # Extract technical terms
        key_terms = extract_technical_terms(sc["text"])

        # Derive topic name from slide description
        description = ss.get("description", "")
        topic_name = _derive_topic_name(description, sc["text"])

        # Check if needs sub-chunking
        needs_sub = sc["word_count"] > sub_chunk_threshold

        # Timestamp display
        ts_display = f"{_format_timestamp(sr['t_start'])} - {_format_timestamp(sr['t_end'])}"

        slide_chunk = SlideChunk(
            slide_index=i + 1,  # 1-based
            slide_image=ss.get("image_filename", f"screenshot_{i+1:03d}.jpg"),
            slide_description=description,
            timestamp_start=sr["t_start"],
            timestamp_end=sr["t_end"],
            timestamp_display=ts_display,
            transcript_text=sc["text"],
            word_count=sc["word_count"],
            topic_name=topic_name,
            emphasis_score=emphasis_score,
            emphasis_signals=emphasis_signals,
            key_terms=key_terms,
            needs_sub_chunking=needs_sub,
        )
        result.append(slide_chunk)

    return result


def chunk_all(
    transcript_path: str,
    screenshots_path: str,
    output_path: str | None = None,
    video_duration: float | None = None,
    sub_chunk_threshold: int = 800,
) -> list[SlideChunk]:
    """Main entry point: chunk transcript by slides, save results."""
    slides = chunk_by_slides(
        transcript_path, screenshots_path,
        video_duration=video_duration,
        sub_chunk_threshold=sub_chunk_threshold,
    )

    print(f"Chunked transcript into {len(slides)} slide-based chunks")

    # Save
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in slides], f, indent=2, ensure_ascii=False)
        print(f"Saved to {output_path}")

    return slides
