"""Pipeline runner — V3.1: slide-driven multi-agent pipeline.

Stages:
0. Transcribe (if video)
0.5. Extract screenshots (from video or PDF)
1. Multi-agent planning (Flash grouper → Flash scanner → Pro coordinator → Flash planner)
2. Textbook + image fetch (OpenStax + Wikimedia fallback)
3. Two-tier generation (Pro deep + Flash standard, parallel)

Falls back to V2 (transcript-driven) if no screenshots available.

Yields progress dicts for the SSE stream.
"""

import json
import sys
import threading
from pathlib import Path
from typing import Generator

# Project root — one level up from backend/
PROJECT_ROOT = Path(__file__).parent.parent


class PipelineCancelled(Exception):
    """Raised when the client disconnects and the pipeline should stop."""
    pass


def _check_cancelled(cancel_event: threading.Event | None):
    """Check if the pipeline has been cancelled by the client."""
    if cancel_event and cancel_event.is_set():
        raise PipelineCancelled("Client disconnected")


def _ensure_imports():
    """Add project root to sys.path so we can import src/ modules."""
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def run_pipeline(
    input_path: str,
    user_profile: dict | None = None,
    slides_path: str | None = None,
    cancel_event: threading.Event | None = None,
) -> Generator[dict, None, None]:
    """Run the V2 pipeline, yielding progress dicts at each stage.

    Each yield is a dict with: status, stage, progress, error, output.
    The caller (SSE endpoint) sends these to the client.

    Args:
        input_path: Path to .txt transcript or .mp4/.mkv video file
        user_profile: Optional dict with study_program, study_year from quiz
        slides_path: Optional path to uploaded slides PDF
    """
    _ensure_imports()

    output_dir = PROJECT_ROOT / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from src.chunker import chunk_transcript

        input_file = Path(input_path)
        job_id = input_file.stem
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
        audio_extensions = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}
        is_video = input_file.suffix in video_extensions
        is_audio = input_file.suffix in audio_extensions

        # ── Stage 0 (conditional): Transcribe video/audio ──
        if is_video or is_audio:
            yield {"status": "running", "stage": "Transcribing lecture", "progress": 2}
            from src.transcriber import transcribe
            result = transcribe(input_path)
            text = result["text"]

            transcript_path = output_dir / f"{job_id}_transcript.txt"
            transcript_path.write_text(text, encoding="utf-8")

            word_count = len(text.split())
            yield {"status": "running", "stage": "Transcribing lecture", "progress": 10,
                   "result": f"{word_count:,} words transcribed"}
            _check_cancelled(cancel_event)
        elif input_file.suffix == ".txt":
            text = input_file.read_text(encoding="utf-8")
        else:
            yield {"status": "error", "stage": "Reading file", "progress": 5,
                   "error": f"Unsupported file type: {input_file.suffix}. Use .txt, .mp4, .mp3, .mkv, .avi, .mov, or .webm"}
            return

        # Guard: reject too-short transcripts
        word_count = len(text.split())
        if word_count < 100:
            yield {"status": "error", "stage": "Chunking transcript", "progress": 5,
                   "error": f"Transcript too short ({word_count} words). Need at least 100 words."}
            return

        # ── Stage 1: Chunking ──
        yield {"status": "running", "stage": "Chunking transcript", "progress": 12}
        chunks = chunk_transcript(text)

        # Convert Pydantic models to dicts for V2
        chunks_dicts = [c.model_dump() for c in chunks]

        yield {"status": "running", "stage": "Chunking transcript", "progress": 15,
               "result": f"{len(chunks)} chunks"}
        _check_cancelled(cancel_event)

        # ── Stage 1.5: Extract screenshots from video (if no slides PDF uploaded) ──
        screenshots_json = None
        if not slides_path and is_video and not is_audio:
            yield {"status": "running", "stage": "Extracting lecture slides", "progress": 16}
            try:
                from src.screenshot_extractor import extract_all
                screenshots_dir = output_dir / "screenshots"
                screenshots_dir.mkdir(exist_ok=True)

                chunks_temp_path = output_dir / f"{job_id}_chunks.json"
                with open(chunks_temp_path, "w", encoding="utf-8") as f:
                    json.dump(chunks_dicts, f, indent=2, ensure_ascii=False)

                results = extract_all(
                    video_path=input_path,
                    chunks_path=str(chunks_temp_path),
                    output_dir=str(screenshots_dir),
                    output_json=str(output_dir / f"{job_id}_screenshots.json"),
                    job_id=job_id,
                )
                if results:
                    screenshots_json = str(output_dir / f"{job_id}_screenshots.json")
                    yield {"status": "running", "stage": "Extracting lecture slides", "progress": 19,
                           "result": f"{len(results)} slides extracted"}
                else:
                    yield {"status": "running", "stage": "Extracting lecture slides", "progress": 19,
                           "result": "No slide transitions detected"}
            except Exception as e:
                print(f"  Screenshot extraction failed: {e}")

        # ── Stage 2: Validate slides match (if PDF provided) ──
        if slides_path:
            yield {"status": "running", "stage": "Validating slides", "progress": 16}
            from src.generator_v2 import validate_content_match
            validation = validate_content_match(text[:2000], slides_path=slides_path)
            if not validation.is_match and validation.confidence > 0.7:
                yield {"status": "error", "stage": "Validating slides", "progress": 16,
                       "error": (
                           f"Slides don't match the transcript. "
                           f"Transcript topic: {validation.transcript_topic}. "
                           f"Slides topic: {validation.slides_topic}. "
                           f"Please upload the correct slides for this lecture."
                       )}
                return
            yield {"status": "running", "stage": "Validating slides", "progress": 18,
                   "result": "Slides match confirmed"}

            # Extract PDF pages as individual slide images
            yield {"status": "running", "stage": "Extracting slides from PDF", "progress": 19}
            _check_cancelled(cancel_event)
            try:
                from src.screenshot_extractor import extract_pdf_slides
                screenshots_dir = output_dir / "screenshots"
                screenshots_dir.mkdir(exist_ok=True)

                pdf_slides = extract_pdf_slides(
                    pdf_path=slides_path,
                    output_dir=str(screenshots_dir),
                    output_json=str(output_dir / f"{job_id}_screenshots.json"),
                    job_id=job_id,
                )

                if pdf_slides:
                    # Map pages to chunks round-robin
                    num_chunks = len(chunks_dicts)
                    for i, entry in enumerate(pdf_slides):
                        entry["matched_chunk_index"] = i % num_chunks
                        entry["image_filename"] = entry.get("image_filename", f"slide_{i+1:03d}.png")

                    ss_json_path = str(output_dir / f"{job_id}_screenshots.json")
                    with open(ss_json_path, "w", encoding="utf-8") as f:
                        json.dump(pdf_slides, f, indent=2, ensure_ascii=False)
                    screenshots_json = ss_json_path

                    yield {"status": "running", "stage": "Extracting slides from PDF", "progress": 20,
                           "result": f"{len(pdf_slides)} slide pages extracted"}
            except Exception as e:
                print(f"  PDF slide extraction failed (non-fatal): {e}")

        # ── Stage 3: Generation ──
        # V3.1 (slide-driven) when screenshots available, V2 (transcript-driven) as fallback
        _check_cancelled(cancel_event)

        # Derive subject hint from user profile if available
        subject = None
        if user_profile:
            program = user_profile.get("study_program", "")
            if program:
                subject = program

        textbook_images = {}  # Only used by V2 fallback

        if screenshots_json:
            # ── V3.1: Slide-driven multi-agent pipeline ──
            yield {"status": "running", "stage": "Planning lecture structure", "progress": 20}

            from src.generator_v3 import generate_lecture_v3
            from src.generator_v2 import assemble_api_response

            # Save transcript to temp file for V3 (it takes a path, not text)
            transcript_path = output_dir / f"{job_id}_transcript.txt"
            if not transcript_path.exists():
                transcript_path.write_text(text, encoding="utf-8")

            _check_cancelled(cancel_event)
            yield {"status": "running", "stage": "Generating lecture", "progress": 30}

            sections, groups = generate_lecture_v3(
                screenshots_json=screenshots_json,
                transcript_path=str(transcript_path),
                subject=subject,
                parallel=True,
                job_id=job_id,
            )
        else:
            # ── V2 fallback: transcript-driven (no screenshots) ──
            yield {"status": "running", "stage": "Preparing teaching context", "progress": 20}

            from src.generator_v2 import generate_lecture, assemble_api_response

            _check_cancelled(cancel_event)
            yield {"status": "running", "stage": "Generating lecture", "progress": 30}

            result = generate_lecture(
                chunks=chunks_dicts,
                lecture_slides_path=slides_path,
                screenshots_json=screenshots_json,
                subject=subject,
                parallel=True,
                job_id=job_id,
            )
            sections, textbook_images = result

        if not sections:
            yield {"status": "error", "stage": "Generating lecture", "progress": 30,
                   "error": "No sections generated. The lecture may be too short or entirely housekeeping."}
            return

        yield {"status": "running", "stage": "Assembling output", "progress": 90}

        # Build API response (same format for V2 and V3)
        api_response = assemble_api_response(sections)

        # Replace local screenshot refs with persistent GCS URLs
        if screenshots_json:
            try:
                with open(screenshots_json, "r", encoding="utf-8") as f:
                    ss_meta = json.load(f)
                # Build lookup by filename stem (Pro sometimes writes .jpg instead of .png)
                gcs_lookup = {}
                for s in ss_meta:
                    if s.get("gcs_url"):
                        fname = s['image_filename']
                        stem = fname.rsplit('.', 1)[0] if '.' in fname else fname
                        gcs_lookup[f"screenshots/{fname}"] = s["gcs_url"]
                        # Also index by stem so .jpg/.png mismatches still resolve
                        gcs_lookup[stem] = s["gcs_url"]
                if gcs_lookup:
                    replaced = 0
                    for slide in api_response.get("slides", []):
                        ref = slide.get("image_ref", "")
                        if ref in gcs_lookup:
                            slide["image_ref"] = gcs_lookup[ref]
                            replaced += 1
                        elif ref.startswith("screenshots/"):
                            # Try stem match: "screenshots/slide_005.jpg" → stem "slide_005"
                            ref_stem = ref.split("/", 1)[1].rsplit(".", 1)[0] if "." in ref else ref
                            if ref_stem in gcs_lookup:
                                slide["image_ref"] = gcs_lookup[ref_stem]
                                replaced += 1
                    print(f"  Replaced {replaced} screenshot refs with GCS URLs")
            except Exception as e:
                print(f"  Warning: GCS URL replacement failed: {e}")

        # Auto-fill diagram cards that have no image with the first available OpenStax figure
        if textbook_images:
            filled = 0
            for slide in api_response.get("slides", []):
                if slide.get("card_type") == "diagram" and not slide.get("image_ref"):
                    # Find which chunk this slide belongs to (by slide_id number)
                    try:
                        slide_num = int(slide["slide_id"].rstrip("abcdefgh")) - 1
                    except (ValueError, KeyError):
                        continue
                    # Get the chunk index from teaching order
                    chunk_idx = slide_num  # slide_number is 1-based, maps to teaching_chunks order
                    images = textbook_images.get(chunk_idx, [])
                    if not images:
                        # Try all chunk indices (textbook_images keyed by original chunk index)
                        for idx, imgs in textbook_images.items():
                            if imgs:
                                images = imgs
                                break
                    if images:
                        best = images[0]  # First figure is usually the most relevant
                        if best.get("gcs_url"):
                            slide["image_ref"] = best["gcs_url"]
                            filled += 1
            if filled:
                print(f"  Auto-filled {filled} diagram cards with OpenStax figures")

        # Serialize as JSON string into the markdown field (no schema migration needed)
        # Frontend detects JSON vs plain markdown and renders accordingly
        v2_json = json.dumps(api_response, ensure_ascii=False)

        yield {
            "status": "done",
            "stage": "Done",
            "progress": 100,
            "output": {
                "markdown": v2_json,
                "slides": api_response.get("slides", []),
                "transcript": api_response.get("transcript", []),
                "concept_groups": [],
                "verification_report": [],
            },
        }

    except PipelineCancelled:
        print(f"  Pipeline cancelled by client disconnect")
        yield {"status": "cancelled", "stage": "Cancelled", "progress": 0}
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"status": "error", "stage": "Pipeline error", "progress": 0, "error": str(e)}
