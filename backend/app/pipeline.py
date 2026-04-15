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
import os
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
        from src.run_tracker import TRACKER

        input_file = Path(input_path)
        job_id = input_file.stem
        TRACKER.reset(job_id)
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
        audio_extensions = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}
        is_video = input_file.suffix.lower() in video_extensions
        is_audio = input_file.suffix.lower() in audio_extensions

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
        elif input_file.suffix.lower() == ".txt":
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
                    # Add synthetic timestamps (V3 uses these for transcript matching)
                    # Evenly space slides across an assumed 2-hour lecture
                    assumed_duration = 7200  # 2 hours in seconds
                    for i, entry in enumerate(pdf_slides):
                        entry["matched_chunk_index"] = i % len(chunks_dicts)
                        entry["image_filename"] = entry.get("image_filename", f"slide_{i+1:03d}.png")
                        entry["timestamp_seconds"] = int(i * assumed_duration / max(len(pdf_slides), 1))
                        entry["timestamp_display"] = f"{entry['timestamp_seconds'] // 60}:{entry['timestamp_seconds'] % 60:02d}"

                    yield {"status": "running", "stage": "Describing slides", "progress": 20,
                           "result": f"{len(pdf_slides)} slides — generating descriptions..."}
                    _check_cancelled(cancel_event)

                    # Flash multimodal descriptions — V3 needs these to group slides
                    # 8 workers — with retry+backoff in call_with_timeout and the
                    # per-worker 429-backoff loop in describe_screenshots, this
                    # is safe and roughly halves slide-description wallclock
                    # (~170s at 3 workers → ~65s at 8 on a 37-slide deck).
                    from src.screenshot_extractor import describe_screenshots
                    describe_screenshots(pdf_slides, max_workers=8)

                    ss_json_path = str(output_dir / f"{job_id}_screenshots.json")
                    with open(ss_json_path, "w", encoding="utf-8") as f:
                        json.dump(pdf_slides, f, indent=2, ensure_ascii=False)
                    screenshots_json = ss_json_path

                    described = sum(1 for s in pdf_slides if s.get("description"))
                    yield {"status": "running", "stage": "Describing slides", "progress": 22,
                           "result": f"{described}/{len(pdf_slides)} slides described"}
            except Exception as e:
                print(f"  PDF slide extraction failed (non-fatal): {e}")

        # ── Stage 3: V3.1 Generation (all formats) ──
        _check_cancelled(cancel_event)

        # Derive subject hint from user profile if available
        subject = None
        if user_profile:
            program = user_profile.get("study_program", "")
            if program:
                subject = program

        yield {"status": "running", "stage": "Planning lecture structure", "progress": 24}

        # Generator selection: USE_SINGLE_WRITER env var picks the single-Pro-call
        # pipeline (cheaper, faster, equivalent or better quality on tested
        # lectures) over the multi-agent pipeline (more breadth, more code,
        # more cost). Multi-agent stays as the safe default until single-writer
        # has been validated across the full lecture inventory.
        use_single_writer = os.environ.get("USE_SINGLE_WRITER", "").lower() in ("1", "true", "yes")

        from src.generator_v2 import assemble_api_response

        # Save transcript to temp file (both pipelines take a path, not text)
        transcript_path = output_dir / f"{job_id}_transcript.txt"
        if not transcript_path.exists():
            transcript_path.write_text(text, encoding="utf-8")

        _check_cancelled(cancel_event)
        yield {"status": "running", "stage": "Generating lecture", "progress": 30}

        if use_single_writer:
            # Load GCS URL lookup up front so we can patch image refs on each
            # streamed section as it arrives (not just at end-of-pipeline).
            gcs_lookup: dict[str, str] = {}
            if screenshots_json:
                try:
                    with open(screenshots_json, "r", encoding="utf-8") as f:
                        ss_meta = json.load(f)
                    for s in ss_meta:
                        if s.get("gcs_url"):
                            fname = s["image_filename"]
                            stem = fname.rsplit(".", 1)[0] if "." in fname else fname
                            gcs_lookup[f"screenshots/{fname}"] = s["gcs_url"]
                            gcs_lookup[fname] = s["gcs_url"]
                            gcs_lookup[stem] = s["gcs_url"]
                except Exception as e:
                    print(f"  [pipeline] GCS lookup prebuild failed: {e}")

            def _resolve_gcs(ref: str) -> str:
                """Map a local ref (screenshots/x.png, x.png, or stem) to GCS URL."""
                if not ref or not gcs_lookup:
                    return ref or ""
                if ref in gcs_lookup:
                    return gcs_lookup[ref]
                # Handle .jpg/.png mismatches via stem
                if ref.startswith("screenshots/"):
                    stem = ref.split("/", 1)[1].rsplit(".", 1)[0]
                    if stem in gcs_lookup:
                        return gcs_lookup[stem]
                return ref

            disable_streaming = os.environ.get("DISABLE_STREAMING", "").lower() in ("1", "true", "yes")

            if disable_streaming:
                print(f"  [pipeline] USE_SINGLE_WRITER=1 (non-streaming) → single-writer pipeline")
                from src.single_writer import generate_lecture_single
                sections, groups = generate_lecture_single(
                    screenshots_json=screenshots_json,
                    transcript_path=str(transcript_path),
                    subject=subject,
                    job_id=job_id,
                    enable_grounding=True,
                )
            else:
                print(f"  [pipeline] USE_SINGLE_WRITER=1 (streaming) → single-writer streaming pipeline")
                from src.single_writer import generate_lecture_single_streaming
                sections = []
                groups = []
                # Expected section count guides the progress bar; we update it
                # once we see sections flow in.
                for event in generate_lecture_single_streaming(
                    screenshots_json=screenshots_json,
                    transcript_path=str(transcript_path),
                    subject=subject,
                    job_id=job_id,
                    enable_grounding=True,
                ):
                    if event.get("kind") == "section":
                        # Convert the raw Pro JSON dicts into the frontend
                        # shape (matches what assemble_api_response emits per
                        # item). Apply GCS URL mapping so images render live.
                        tx = event.get("transcript_item", {}) or {}
                        sc = event.get("slide_card", {}) or {}
                        idx = event.get("index", 0)

                        # Map card_type: text_only → diagram for SlideCard compat
                        raw_card_type = sc.get("card_type", "professor_slide") if sc else "professor_slide"
                        if raw_card_type == "text_only":
                            card_type = "diagram"
                        elif raw_card_type in ("professor_slide", "diagram"):
                            card_type = raw_card_type
                        else:
                            card_type = "professor_slide"

                        image_ref = _resolve_gcs(sc.get("image_ref", "") if sc else "")

                        # Embed image at top of narrative for professor_slide cards
                        narrative = tx.get("narrative", "") or ""
                        if card_type == "professor_slide" and image_ref and image_ref not in narrative:
                            title = sc.get("title", tx.get("title", "")) if sc else tx.get("title", "")
                            narrative = f"![{title}]({image_ref})\n\n{narrative}"

                        slide_payload = {
                            "slide_id": str(sc.get("slide_id", tx.get("slide_number", idx + 1))) if sc else str(tx.get("slide_number", idx + 1)),
                            "title": sc.get("title", tx.get("title", "")) if sc else tx.get("title", ""),
                            "card_type": card_type,
                            "image_ref": image_ref,
                            "bullet_points": (sc.get("bullet_points", []) if sc else []) or [],
                            "exam_tip": (sc.get("exam_tip", "") if sc else "") or "",
                            "ei_percent": int((sc.get("ei_percent") if sc else None) or tx.get("ei_percent", 50)),
                        }
                        transcript_payload = {
                            "slide_number": int(tx.get("slide_number", idx + 1) or idx + 1),
                            "title": tx.get("title", ""),
                            "narrative": narrative,
                            "ei_percent": int(tx.get("ei_percent", 50)),
                            "ei_reasoning": tx.get("ei_reasoning", ""),
                        }

                        yield {
                            "status": "running",
                            "stage": "Writing sections",
                            # Scale 30 → 78 over ~20 sections
                            "progress": min(30 + idx * 2, 78),
                            "section": {
                                "index": idx,
                                "slide": slide_payload,
                                "transcript": transcript_payload,
                            },
                        }
                    elif event.get("kind") == "done":
                        sections = event.get("sections", []) or []
                        groups = event.get("groups", []) or []
        else:
            from src.generator_v3 import generate_lecture_v3
            sections, groups = generate_lecture_v3(
                screenshots_json=screenshots_json,  # None for transcript-only
                transcript_path=str(transcript_path),
                subject=subject,
                parallel=True,
                job_id=job_id,
            )

        if not sections:
            yield {"status": "error", "stage": "Generating lecture", "progress": 30,
                   "error": "No sections generated. The lecture may be too short or entirely housekeeping."}
            return

        # ── Completeness check (final safety net) ──
        # Compares generated output against raw transcript, patches HIGH-severity
        # missed content into the relevant sections. Strategy A only — patches
        # are appended to sections, no regeneration. Skipped silently on any
        # error so a failed check never kills the user's run.
        yield {"status": "running", "stage": "Verifying coverage", "progress": 85}
        try:
            from src.completeness_checker import check_completeness
            sections, _missed = check_completeness(
                sections, text, apply_patches=True
            )
        except Exception as e:
            print(f"  [completeness] Skipped due to error: {e}")

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
                        # Also index by bare filename — single-writer sometimes
                        # emits "slide_014.png" without the screenshots/ prefix.
                        gcs_lookup[fname] = s["gcs_url"]
                        # And by stem so .jpg/.png mismatches still resolve
                        gcs_lookup[stem] = s["gcs_url"]
                if gcs_lookup:
                    replaced = 0
                    # Replace in slide card image_refs
                    for slide in api_response.get("slides", []):
                        ref = slide.get("image_ref", "")
                        if ref in gcs_lookup:
                            slide["image_ref"] = gcs_lookup[ref]
                            replaced += 1
                        elif ref.startswith("screenshots/"):
                            ref_stem = ref.split("/", 1)[1].rsplit(".", 1)[0] if "." in ref else ref
                            if ref_stem in gcs_lookup:
                                slide["image_ref"] = gcs_lookup[ref_stem]
                                replaced += 1

                    # Also replace in transcript narrative text
                    # (writers embed ![desc](screenshots/slide_XXX.png) or
                    # ![desc](slide_XXX.png) in transcript)
                    for section in api_response.get("transcript", []):
                        if isinstance(section, dict):
                            for field in ("narrative", "text"):
                                val = section.get(field, "")
                                if not val:
                                    continue
                                # Replace both prefixed and bare filenames
                                for local_path, gcs_url in gcs_lookup.items():
                                    if local_path and local_path != gcs_url:
                                        val = val.replace(local_path, gcs_url)
                                section[field] = val

                    print(f"  Replaced {replaced} screenshot refs with GCS URLs")
            except Exception as e:
                print(f"  Warning: GCS URL replacement failed: {e}")

        # Serialize as JSON string into the markdown field (no schema migration needed)
        # Frontend detects JSON vs plain markdown and renders accordingly
        v2_json = json.dumps(api_response, ensure_ascii=False)

        # Per-run cost + time report — printed to logs, saved to JSON,
        # also returned in the SSE done payload so the frontend can show it.
        cost_report = None
        try:
            cost_report = TRACKER.report(job_id)
        except Exception as e:
            print(f"  Cost report failed: {e}")

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
                "cost_report": cost_report,
            },
        }

    except PipelineCancelled:
        print(f"  Pipeline cancelled by client disconnect")
        yield {"status": "cancelled", "stage": "Cancelled", "progress": 0}
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"status": "error", "stage": "Pipeline error", "progress": 0, "error": str(e)}
