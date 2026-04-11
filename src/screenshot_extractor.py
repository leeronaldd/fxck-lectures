"""
Stage 1.5b: Screenshot Extractor

Detects slide/visual transitions in lecture videos, extracts representative
screenshots, describes them via Gemini Flash multimodal, and matches each
screenshot to the most relevant transcript chunk.
"""

import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from src.config import (
    CHUNKER_FALLBACK_MODEL,
    GCP_LOCATION,
    GCP_PROJECT_ID,
    SCREENSHOTS_DIR,
)
from src.models import Chunk, Screenshot


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------

def extract_frames(
    video_path: str,
    output_dir: str,
    threshold: float = 30.0,
    skip_seconds: int = 60,
    dedup_window: float = 3.0,
) -> list[dict]:
    """
    Extract key frames from a lecture video by detecting visual transitions.

    Reads the video at 1 fps, compares consecutive frames using mean absolute
    difference, and saves frames where the change exceeds *threshold*.

    Args:
        video_path: Path to the lecture video file.
        output_dir: Directory to save extracted JPEG screenshots.
        threshold: Mean absolute difference threshold for detecting a new slide.
        skip_seconds: Seconds to skip at the start (title/loading screens).
        dedup_window: Minimum seconds between two detections to keep both.

    Returns:
        List of dicts with keys: timestamp_seconds, image_path.
    """
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    frame_interval = max(1, int(round(fps)))  # read ~1 frame per second

    print(f"Video: {duration:.0f}s ({duration / 60:.1f} min), {fps:.1f} fps")
    print(f"Reading every {frame_interval} frames (~1 fps), skipping first {skip_seconds}s")

    prev_gray = None
    detections: list[dict] = []
    frame_idx = 0

    # Jump to skip_seconds
    start_frame = int(skip_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_idx = start_frame

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        # Only process at ~1 fps
        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            mean_diff = float(np.mean(diff))

            if mean_diff > threshold:
                # Dedup: skip if too close to last detection
                if detections and (timestamp - detections[-1]["timestamp_seconds"]) < dedup_window:
                    frame_idx += 1
                    prev_gray = gray
                    continue

                # Save frame
                idx_str = f"{len(detections) + 1:03d}"
                filename = f"screenshot_{idx_str}.png"
                save_path = os.path.join(output_dir, filename)

                # Use Pillow for JPEG quality control
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.save(save_path, "PNG")

                detections.append({
                    "timestamp_seconds": round(timestamp, 1),
                    "image_path": save_path,
                })
        else:
            # Always save the first frame after skip as a baseline
            idx_str = f"{len(detections) + 1:03d}"
            filename = f"screenshot_{idx_str}.png"
            save_path = os.path.join(output_dir, filename)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.save(save_path, "PNG")
            detections.append({
                "timestamp_seconds": round(timestamp, 1),
                "image_path": save_path,
            })

        prev_gray = gray
        frame_idx += 1

    cap.release()
    print(f"Detected {len(detections)} slide transitions")

    # Re-capture frames near the END of each slide (not the transition moment)
    # This ensures the slide content is fully rendered/visible
    print("Re-capturing frames near end of each slide for best content...")
    cap2 = cv2.VideoCapture(video_path)
    if cap2.isOpened():
        for i, det in enumerate(detections):
            # Target: 5 seconds before the next slide starts (or 80% through the slide)
            t_start = det["timestamp_seconds"]
            if i + 1 < len(detections):
                t_end = detections[i + 1]["timestamp_seconds"]
            else:
                t_end = duration

            slide_duration = t_end - t_start
            if slide_duration > 10:
                # Capture at 5 seconds before the end, or 80% through, whichever is earlier
                target_time = min(t_end - 5, t_start + slide_duration * 0.8)
            else:
                # Short slide: capture at midpoint
                target_time = t_start + slide_duration * 0.5

            target_frame = int(target_time * fps)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap2.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.save(det["image_path"], "JPEG", quality=85)

        cap2.release()

    return detections


# ---------------------------------------------------------------------------
# Gemini Flash multimodal description
# ---------------------------------------------------------------------------

def describe_screenshots(
    screenshots: list[dict],
    batch_size: int = 5,
    delay: float = 0.5,
) -> list[dict]:
    """
    Use Gemini Flash multimodal to describe each screenshot in 1-2 sentences.

    Args:
        screenshots: List of dicts with 'image_path' key.
        batch_size: Log progress every N screenshots.
        delay: Seconds to wait between API calls (rate limiting).

    Returns:
        The same list with 'description' key added to each dict.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    total = len(screenshots)
    for i, ss in enumerate(screenshots):
        try:
            with open(ss["image_path"], "rb") as f:
                image_bytes = f.read()

            response = client.models.generate_content(
                model=CHUNKER_FALLBACK_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    "Describe this lecture slide in 1-2 sentences. What topic/concept does it show?",
                ],
            )
            ss["description"] = response.text.strip()
        except Exception as e:
            print(f"  Warning: description failed for screenshot {i + 1}: {e}")
            ss["description"] = "[Description unavailable]"

        if (i + 1) % batch_size == 0 or (i + 1) == total:
            print(f"  Described {i + 1}/{total} screenshots")

        if delay > 0 and (i + 1) < total:
            time.sleep(delay)

    return screenshots


# ---------------------------------------------------------------------------
# Chunk matching
# ---------------------------------------------------------------------------

def match_to_chunks(
    screenshots: list[dict],
    chunks: list[Chunk],
    video_duration: float,
) -> list[Screenshot]:
    """
    Match each screenshot to the most relevant transcript chunk.

    Strategy:
    1. Assign each chunk a proportional timestamp range based on word count.
    2. For each screenshot, find the chunk whose range contains its timestamp.
    3. If the screenshot description mentions key_terms from a different chunk,
       prefer that chunk (keyword boost).

    Args:
        screenshots: List of dicts with timestamp_seconds, image_path, description.
        chunks: List of Chunk objects from Stage 1.
        video_duration: Total video duration in seconds.

    Returns:
        List of Screenshot model objects.
    """
    if not chunks:
        return []

    # Build timestamp ranges proportional to word counts
    total_words = sum(c.word_count for c in chunks)
    if total_words == 0:
        total_words = len(chunks)  # fallback: equal distribution

    ranges: list[tuple[float, float]] = []
    cursor = 0.0
    for c in chunks:
        proportion = c.word_count / total_words
        chunk_duration = proportion * video_duration
        ranges.append((cursor, cursor + chunk_duration))
        cursor += chunk_duration

    results: list[Screenshot] = []
    for ss in screenshots:
        ts = ss["timestamp_seconds"]
        desc = ss.get("description", "").lower()
        image_path = ss["image_path"]

        # Default: find chunk by timestamp range
        best_idx = 0
        for i, (start, end) in enumerate(ranges):
            if start <= ts < end:
                best_idx = i
                break
        else:
            # Past the last range — assign to last chunk
            best_idx = len(chunks) - 1

        # Keyword boost: check if description mentions key_terms from any chunk
        best_keyword_score = 0
        for i, c in enumerate(chunks):
            score = sum(1 for term in c.key_terms if term.lower() in desc)
            if score > best_keyword_score:
                best_keyword_score = score
                if score >= 2:  # require at least 2 matching terms to override
                    best_idx = i

        matched_chunk = chunks[best_idx]

        # Build display timestamp
        minutes = int(ts // 60)
        seconds = int(ts % 60)
        timestamp_display = f"{minutes}:{seconds:02d}"

        results.append(Screenshot(
            screenshot_index=len(results),
            timestamp_seconds=ts,
            timestamp_display=timestamp_display,
            image_filename=os.path.basename(image_path),
            description=ss.get("description", "[No description]"),
            matched_chunk_index=matched_chunk.chunk_index,
            matched_chunk_topic=matched_chunk.topic_name,
        ))

    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_all(
    video_path: str,
    chunks_path: str,
    output_dir: str | None = None,
    output_json: str | None = None,
    threshold: float = 30.0,
    skip_describe: bool = False,
) -> list[Screenshot]:
    """
    Full pipeline: extract frames, describe them, match to chunks.

    Args:
        video_path: Path to the lecture video.
        chunks_path: Path to Stage 1 chunks JSON.
        output_dir: Directory for screenshot images (default: data/screenshots/).
        output_json: Path for output metadata JSON.
        threshold: Frame difference threshold.
        skip_describe: If True, skip Gemini multimodal description step.

    Returns:
        List of Screenshot objects.
    """
    if output_dir is None:
        output_dir = SCREENSHOTS_DIR

    # Load chunks
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)
    chunks = [Chunk(**c) for c in chunks_data]
    print(f"Loaded {len(chunks)} chunks from {chunks_path}")

    # Get video duration
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps if fps > 0 else 6904.0
    cap.release()

    # Step 1: Extract frames
    print("\n--- Step 1: Extracting frames ---")
    screenshots = extract_frames(video_path, output_dir, threshold=threshold)

    if not screenshots:
        print("No slide transitions detected. Try lowering the threshold.")
        return []

    # Step 2: Describe screenshots (optional)
    if not skip_describe:
        print("\n--- Step 2: Describing screenshots with Gemini Flash ---")
        screenshots = describe_screenshots(screenshots)
    else:
        print("\n--- Step 2: Skipped (--skip-describe) ---")
        for ss in screenshots:
            ss["description"] = "[Description skipped]"

    # Step 3: Match to chunks
    print("\n--- Step 3: Matching screenshots to chunks ---")
    results = match_to_chunks(screenshots, chunks, video_duration)
    print(f"Matched {len(results)} screenshots to {len(set(r.matched_chunk_index for r in results))} unique chunks")

    # Save metadata JSON
    if output_json:
        os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(
                [s.model_dump() for s in results],
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"\nSaved metadata to: {output_json}")

    return results
