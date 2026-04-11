"""Pipeline runner — V2: 3-stage anatomy-professor pipeline.

Stages:
1. Transcribe (if video) + Chunk
2. Flash prefetch (teaching summaries + term tracking) + Flash textbook fetch
3. Pro generation (parallel, all chunks at once)

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

        # ── Stage 0 (conditional): Transcribe video ──
        if input_file.suffix in video_extensions:
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
                   "error": f"Unsupported file type: {input_file.suffix}. Use .txt, .mp4, .mkv, .avi, .mov, or .webm"}
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
        if not slides_path and input_file.suffix in video_extensions:
            yield {"status": "running", "stage": "Extracting lecture slides", "progress": 16}
            try:
                from src.screenshot_extractor import extract_all
                screenshots_dir = output_dir / "screenshots"
                screenshots_dir.mkdir(exist_ok=True)

                # Save chunks to temp file for extract_all
                chunks_temp_path = output_dir / f"{job_id}_chunks.json"
                with open(chunks_temp_path, "w", encoding="utf-8") as f:
                    json.dump(chunks_dicts, f, indent=2, ensure_ascii=False)

                results = extract_all(
                    video_path=input_path,
                    chunks_path=str(chunks_temp_path),
                    output_dir=str(screenshots_dir),
                    output_json=str(output_dir / f"{job_id}_screenshots.json"),
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
                # Non-fatal — continue without screenshots

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

        # ── Stage 3: V2 Generation (prefetch + textbook + Pro, all inside) ──
        _check_cancelled(cancel_event)
        yield {"status": "running", "stage": "Preparing teaching context", "progress": 20}

        from src.generator_v2 import generate_lecture, assemble_api_response

        # Derive subject hint from user profile if available
        subject = None
        if user_profile:
            program = user_profile.get("study_program", "")
            if program:
                subject = program

        _check_cancelled(cancel_event)
        yield {"status": "running", "stage": "Generating lecture", "progress": 30}

        sections = generate_lecture(
            chunks=chunks_dicts,
            lecture_slides_path=slides_path,
            screenshots_json=screenshots_json,
            subject=subject,
            parallel=True,
        )

        if not sections:
            yield {"status": "error", "stage": "Generating lecture", "progress": 30,
                   "error": "No sections generated. The lecture may be too short or entirely housekeeping."}
            return

        yield {"status": "running", "stage": "Assembling output", "progress": 90}

        # Build V2 API response
        api_response = assemble_api_response(sections)

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
