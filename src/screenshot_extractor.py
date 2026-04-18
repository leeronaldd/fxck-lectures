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
    GCS_SCREENSHOTS_BUCKET,
    SCREENSHOTS_DIR,
    FLASH_TIMEOUT_S,
    call_with_timeout,
    VertexTimeoutError,
)
from src.models import Chunk, Screenshot


# ---------------------------------------------------------------------------
# GCS upload
# ---------------------------------------------------------------------------

def _upload_to_gcs(local_path: str, job_id: str) -> str:
    """Upload a screenshot to GCS and return its public URL.

    Uses the default Cloud Run service account credentials.
    Falls back gracefully — returns empty string if upload fails.
    """
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(GCS_SCREENSHOTS_BUCKET)
        blob_name = f"{job_id}/{os.path.basename(local_path)}"
        blob = bucket.blob(blob_name)
        mime = "image/png" if local_path.endswith(".png") else "image/jpeg"
        blob.upload_from_filename(local_path, content_type=mime)
        return f"https://storage.googleapis.com/{GCS_SCREENSHOTS_BUCKET}/{blob_name}"
    except Exception as e:
        print(f"  Warning: GCS upload failed for {local_path}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------

def _ahash(image: Image.Image, size: int = 8) -> int:
    """8×8 average-hash fingerprint packed into a 64-bit int. Used for
    splitting time-gap clusters when the prof flips slides within the same
    ~10-second window (consecutive frames look very different even though
    close in time).
    """
    small = image.convert("L").resize((size, size), Image.LANCZOS)
    arr = np.asarray(small, dtype=np.uint8)
    mean = arr.mean()
    bits = (arr > mean).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(bool(b))
    return h


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def extract_frames(
    video_path: str,
    output_dir: str,
    threshold: float = 15.0,
    skip_seconds: int = 60,
    sample_fps: int = 2,
    time_gap_s: float = 10.0,
    hamming_split_threshold: int = 18,
) -> list[dict]:
    """
    Extract key frames from a lecture video by detecting visual transitions.

    Algorithm (tuned 2026-04-18 from experimentation on CHEM.mp4):

      1. Sample the video at *sample_fps* frames per second (default 2).
      2. For each sampled frame compute mean-absolute pixel difference
         against the previous sampled frame. Mark as a CANDIDATE if
         diff > *threshold* (default 15 — low enough to catch subtle
         build-ins and pen strokes; raised to 30 before this caused
         many slides to be missed).
      3. Cluster candidates by time proximity: if a candidate is within
         *time_gap_s* of the previous accepted candidate AND visually
         similar (Hamming distance ≤ *hamming_split_threshold* on an
         8×8 aHash), it joins the same cluster. This groups a drawing
         session or a PowerPoint build-in sequence into one cluster.
      4. Keep the LAST frame of each cluster — for a drawing, that's
         the completed drawing; for a build-in, that's the fully
         revealed slide.
      5. Re-capture each kept frame at a point 2 seconds BEFORE the
         next cluster's first transition. That's the final moment the
         slide was displayed — guaranteed to show the fully-built state
         before the prof flipped away.

    Why this matters: the old algorithm (threshold 30, 1 fps, 3s dedup,
    re-capture at 80%) missed ~30% of slides on lectures where the prof
    drew live on paper (each stroke registered as a transition and ate
    detection budget) and captured title-only frames on animated
    PowerPoint slides (re-capturing at 80% still landed mid-build).

    Args:
        video_path: Path to the lecture video file.
        output_dir: Directory to save extracted JPEG/PNG screenshots.
        threshold: Mean absolute difference threshold for detecting a
            transition candidate. 15 is tuned; lower = more noise,
            higher = misses subtle slide changes.
        skip_seconds: Seconds to skip at the start (title/loading screens).
        sample_fps: How many frames per second to sample for transition
            detection. 2 is tuned; 1 misses brief slides, 4 is wasteful.
        time_gap_s: Candidates within this many seconds of the previous
            accepted candidate join the same cluster.
        hamming_split_threshold: If two consecutive candidates in a time
            window differ by more than this many bits in their 8×8 aHash,
            split them into separate clusters (prof flipped slides
            mid-window).

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
    frame_interval = max(1, int(round(fps / max(1, sample_fps))))

    print(f"Video: {duration:.0f}s ({duration / 60:.1f} min), {fps:.1f} fps")
    print(f"Sampling every {frame_interval} frames ({sample_fps} fps), "
          f"skipping first {skip_seconds}s, threshold {threshold}")

    # ── Pass 1: collect candidates ──
    prev_gray = None
    candidates: list[dict] = []
    frame_idx = int(skip_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        timestamp = frame_idx / fps
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_gray is None:
            # Baseline: capture the first sampled frame
            candidates.append({
                "timestamp": round(timestamp, 2),
                "frame_bgr": frame.copy(),
                "diff": 0.0,
            })
        else:
            diff = float(np.mean(cv2.absdiff(prev_gray, gray)))
            if diff > threshold:
                candidates.append({
                    "timestamp": round(timestamp, 2),
                    "frame_bgr": frame.copy(),
                    "diff": round(diff, 1),
                })

        prev_gray = gray
        frame_idx += 1

    cap.release()
    print(f"Detected {len(candidates)} transition candidates")

    # ── Pass 2: time-gap clustering ──
    for c in candidates:
        frame_rgb = cv2.cvtColor(c["frame_bgr"], cv2.COLOR_BGR2RGB)
        c["hash"] = _ahash(Image.fromarray(frame_rgb))

    clusters: list[list[dict]] = [[candidates[0]]] if candidates else []
    for c in candidates[1:]:
        last = clusters[-1][-1]
        time_close = (c["timestamp"] - last["timestamp"]) <= time_gap_s
        visually_close = _hamming(c["hash"], last["hash"]) <= hamming_split_threshold
        if time_close and visually_close:
            clusters[-1].append(c)
        else:
            clusters.append([c])

    kept: list[dict] = []
    for cluster in clusters:
        last = cluster[-1]
        last["cluster_span_s"] = last["timestamp"] - cluster[0]["timestamp"]
        last["cluster_start_t"] = cluster[0]["timestamp"]
        kept.append(last)

    print(f"Collapsed {len(candidates)} candidates into {len(kept)} unique slides")

    # ── Pass 3: re-capture the settled state ──
    # Target: 2s BEFORE the next cluster's first transition. That's the
    # moment right before the prof flipped — slide is fully built. For
    # long-span clusters (drawings), the cluster's last frame is already
    # the final state, so skip re-capture.
    cap2 = cv2.VideoCapture(video_path)
    for i, d in enumerate(kept):
        span = d.get("cluster_span_s", 0.0)
        if span > 15.0:
            continue  # drawing — final frame already correct

        t = d["timestamp"]
        if i + 1 < len(kept):
            next_start = kept[i + 1].get("cluster_start_t", kept[i + 1]["timestamp"])
            target_t = next_start - 2.0
        else:
            target_t = min(duration - 5.0, t + 120.0)
        target_t = max(t + 3.0, target_t)

        cap2.set(cv2.CAP_PROP_POS_FRAMES, int(target_t * fps))
        ret, frame = cap2.read()
        if ret:
            d["frame_bgr"] = frame
    cap2.release()

    # ── Save images + return in the legacy-compatible shape ──
    detections: list[dict] = []
    for i, d in enumerate(kept):
        filename = f"screenshot_{i + 1:03d}.png"
        save_path = os.path.join(output_dir, filename)
        frame_rgb = cv2.cvtColor(d["frame_bgr"], cv2.COLOR_BGR2RGB)
        Image.fromarray(frame_rgb).save(save_path, "PNG")
        detections.append({
            "timestamp_seconds": round(d["timestamp"], 1),
            "image_path": save_path,
        })

    return detections


# ---------------------------------------------------------------------------
# Gemini Flash multimodal description
# ---------------------------------------------------------------------------

def describe_screenshots(
    screenshots: list[dict],
    batch_size: int = 5,
    delay: float = 0.5,
    max_workers: int = 4,
) -> list[dict]:
    """
    Use Gemini Flash multimodal to describe each screenshot in 1-2 sentences.

    Runs descriptions in parallel (6 workers) instead of sequentially.
    For 20 screenshots this cuts ~25s sequential down to ~5s parallel.

    Args:
        screenshots: List of dicts with 'image_path' key.
        batch_size: Log progress every N screenshots.
        delay: Unused (kept for API compatibility). Parallel calls handle rate limiting.
        max_workers: Number of parallel description workers.

    Returns:
        The same list with 'description' key added to each dict.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

    total = len(screenshots)

    def _describe_one(idx: int, ss: dict) -> tuple[int, str]:
        import time as _time
        img_path = ss["image_path"]
        with open(img_path, "rb") as f:
            image_bytes = f.read()

        mime = "image/png" if img_path.lower().endswith(".png") else "image/jpeg"

        # Retry with backoff for 429 RESOURCE_EXHAUSTED + hard per-call timeout.
        # Each describe is one image + 1-sentence prompt, normally <5s. We cap at
        # FLASH_TIMEOUT_S so a stuck call can never freeze the whole extraction
        # (this was the friend-stuck-at-20% bug).
        for attempt in range(4):
            try:
                from google.genai import types as genai_types
                response = call_with_timeout(
                    lambda: client.models.generate_content(
                        model=CHUNKER_FALLBACK_MODEL,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime),
                            # The downstream planner only needs a topic label,
                            # not an essay. But we MUST disable Flash 3 thinking
                            # here — otherwise thinking tokens eat the output
                            # budget and we get truncated "This lecture" strings
                            # (verified in run 5aaa4cc6: 14s per call, 0-18
                            # chars of visible output, all slides grouped wrong).
                            "In ONE short sentence, name the topic this lecture slide covers.",
                        ],
                        config={
                            "max_output_tokens": 200,
                            "temperature": 0.1,
                            # Thinking off — no reasoning needed for vision → label
                            "thinking_config": genai_types.ThinkingConfig(
                                thinking_budget=0,
                            ),
                        },
                    ),
                    timeout=FLASH_TIMEOUT_S,
                    label=f"slide_describe[{idx}]",
                    retries=0,  # we own the retry loop here for 429 backoff
                )
                return idx, response.text.strip()
            except VertexTimeoutError as e:
                # Treat timeout same as a transient failure — backoff and retry.
                if attempt < 3:
                    _time.sleep((attempt + 1) * 3)
                    continue
                print(f"  Warning: description timed out for screenshot {idx + 1}: {e}")
                return idx, "[Description unavailable]"
            except Exception as e:
                if "429" in str(e) and attempt < 3:
                    wait = (attempt + 1) * 5  # 5s, 10s, 15s
                    _time.sleep(wait)
                    continue
                print(f"  Warning: description failed for screenshot {idx + 1}: {e}")
                return idx, "[Description unavailable]"
        return idx, "[Description unavailable]"

    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_describe_one, i, ss): i
            for i, ss in enumerate(screenshots)
        }
        for future in as_completed(futures):
            idx, description = future.result()
            screenshots[idx]["description"] = description
            completed += 1
            if completed % batch_size == 0 or completed == total:
                print(f"  Described {completed}/{total} screenshots")

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
            gcs_url=ss.get("gcs_url", ""),
        ))

    return results


# ---------------------------------------------------------------------------
# PDF slide extraction
# ---------------------------------------------------------------------------

def extract_pdf_slides(
    pdf_path: str,
    output_dir: str | None = None,
    output_json: str | None = None,
    job_id: str = "",
) -> list[dict]:
    """
    Extract each page of a PDF as a high-res PNG image.

    Renders every page at 300 DPI using PyMuPDF, saves locally, and optionally
    uploads to GCS. Returns metadata compatible with the video screenshot
    pipeline so downstream stages (Flash description, generation) can use
    PDF slides as a drop-in replacement for video screenshots.

    Args:
        pdf_path: Path to the lecture slides PDF.
        output_dir: Directory to save PNG images (default: SCREENSHOTS_DIR).
        output_json: Path to save metadata JSON (like extract_all does).
        job_id: GCS folder prefix. If provided, images are uploaded to GCS.

    Returns:
        List of dicts with keys: page_number, image_path, image_filename,
        gcs_url, description.
    """
    import fitz  # PyMuPDF

    if output_dir is None:
        output_dir = SCREENSHOTS_DIR
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"PDF: {total_pages} pages — {pdf_path}")

    # 150 DPI: sharp enough for both Pro (text recognition) and student
    # (slide panel is ~600px wide). 300 DPI was overkill and doubled render time.
    zoom = 150 / 72
    matrix = fitz.Matrix(zoom, zoom)

    results: list[dict] = []

    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)

        filename = f"slide_{page_num + 1:03d}.png"
        save_path = os.path.join(output_dir, filename)
        pix.save(save_path)

        entry = {
            "page_number": page_num + 1,
            "image_path": save_path,
            "image_filename": filename,
            "gcs_url": "",
            "description": "",
        }
        results.append(entry)

        if (page_num + 1) % 10 == 0 or (page_num + 1) == total_pages:
            print(f"  Rendered {page_num + 1}/{total_pages} pages")

    doc.close()

    # Upload to GCS if job_id provided (parallel)
    if job_id:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print(f"\nUploading {len(results)} slides to GCS...")

        def _upload_one(idx_entry):
            idx, entry = idx_entry
            return idx, _upload_to_gcs(entry["image_path"], job_id)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(_upload_one, (i, e)): i
                for i, e in enumerate(results)
            }
            uploaded = 0
            for future in as_completed(futures):
                idx, gcs_url = future.result()
                results[idx]["gcs_url"] = gcs_url
                if gcs_url:
                    uploaded += 1
        print(f"  Uploaded {uploaded}/{len(results)} slides to GCS")

    # Save metadata JSON
    if output_json:
        os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved PDF slide metadata to: {output_json}")

    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_all(
    video_path: str,
    chunks_path: str,
    output_dir: str | None = None,
    output_json: str | None = None,
    threshold: float = 15.0,
    skip_describe: bool = False,
    job_id: str = "",
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

    # Step 2.5: Upload to GCS for persistent access (parallel)
    if job_id:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print("\n--- Step 2.5: Uploading screenshots to GCS ---")

        def _upload_one(idx_ss):
            idx, ss = idx_ss
            return idx, _upload_to_gcs(ss["image_path"], job_id)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(_upload_one, (i, ss)): i
                for i, ss in enumerate(screenshots)
            }
            uploaded = 0
            for future in as_completed(futures):
                idx, gcs_url = future.result()
                screenshots[idx]["gcs_url"] = gcs_url
                if gcs_url:
                    uploaded += 1
        print(f"  Uploaded {uploaded}/{len(screenshots)} screenshots to GCS")
    else:
        for ss in screenshots:
            ss["gcs_url"] = ""

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
