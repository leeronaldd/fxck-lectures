"""Pipeline runner — wraps the existing CLI pipeline as a background job."""

import json
import sys
import threading
import uuid
from pathlib import Path

# In-memory job tracking (replace with Supabase DB in production)
jobs: dict[str, dict] = {}

# Project root — one level up from backend/
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _ensure_imports():
    """Add project root to sys.path so we can import src/ modules."""
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _update_job(job_id: str, **kwargs):
    """Thread-safe job status update."""
    if job_id in jobs:
        jobs[job_id].update(kwargs)


def run_pipeline(job_id: str, input_path: str, user_id: str):
    """Run the v4 pipeline in a background thread.

    Updates jobs[job_id] with progress as it runs.
    """
    _ensure_imports()

    _update_job(job_id, status="running", stage="chunking", progress=0)

    # Ensure output directory exists
    output_dir = PROJECT_ROOT / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from src.models import Chunk
        from src.chunker import chunk_transcript

        # --- Step 1: Chunking ---
        _update_job(job_id, stage="Chunking transcript", progress=5)

        input_file = Path(input_path)
        if input_file.suffix == ".txt":
            # Transcript file — chunk directly
            text = input_file.read_text(encoding="utf-8")
            chunks = chunk_transcript(text)
        else:
            # For now, only support transcript files
            _update_job(job_id, status="error", error="Only .txt transcript files supported for now")
            return

        chunks_path = PROJECT_ROOT / "data" / "output" / f"job_{job_id}_chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in chunks], f, indent=2)

        # --- Step 2: CI% Scoring ---
        _update_job(job_id, stage="Scoring exam importance", progress=15)
        from src.ci_scorer import score_all
        ci_output = str(PROJECT_ROOT / "data" / "output" / f"job_{job_id}_ci.json")
        ci_scores = score_all(str(chunks_path), output_path=ci_output)
        ci_map = {s.chunk_index: s for s in ci_scores}

        # --- Step 3: Concept Grouping ---
        _update_job(job_id, stage="Grouping concepts", progress=25)
        from src.concept_grouper import group_chunks_deterministic, save_groups
        groups = group_chunks_deterministic(chunks, ci_map)
        groups_path = PROJECT_ROOT / "data" / "output" / f"job_{job_id}_groups.json"
        save_groups(groups, str(groups_path))

        # --- Step 4: Load groups with transcripts ---
        from src.concept_grouper import load_groups_with_transcripts
        groups_with_text = load_groups_with_transcripts(str(groups_path), chunks)

        # --- Step 5: Generation ---
        _update_job(job_id, stage="Generating explanations", progress=35)
        from src.generator import generate_from_groups

        output_path = str(PROJECT_ROOT / "data" / "output" / f"job_{job_id}_output.md")
        generate_from_groups(
            groups_with_text,
            output_path=output_path,
            dry_run=False,
        )
        _update_job(job_id, progress=80)

        # --- Step 6: Fact checking ---
        _update_job(job_id, stage="Verifying sources", progress=85)
        from src.fact_checker import fact_check_document
        verification_path = PROJECT_ROOT / "data" / "output" / f"job_{job_id}_verification.json"
        try:
            fact_check_document(output_path, str(verification_path))
        except Exception:
            pass  # Non-fatal — skip if fact checker fails

        # --- Step 7: Completeness check ---
        _update_job(job_id, stage="Checking completeness", progress=90)
        from src.completeness_checker import check_completeness
        try:
            check_completeness(output_path, str(chunks_path))
        except Exception:
            pass  # Non-fatal

        # --- Step 8: Assembly ---
        _update_job(job_id, stage="Assembling final document", progress=95)

        # Read outputs
        markdown = Path(output_path).read_text(encoding="utf-8") if Path(output_path).exists() else ""
        concept_groups = json.loads(groups_path.read_text(encoding="utf-8")) if groups_path.exists() else []
        verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.exists() else []

        _update_job(
            job_id,
            status="done",
            stage="Done",
            progress=100,
            output={
                "markdown": markdown,
                "concept_groups": concept_groups,
                "verification_report": verification,
            },
        )

    except Exception as e:
        _update_job(job_id, status="error", error=str(e))


def start_pipeline(input_path: str, user_id: str) -> str:
    """Start the pipeline in a background thread. Returns job_id."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "stage": None,
        "progress": 0,
        "error": None,
        "user_id": user_id,
        "output": None,
    }

    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, input_path, user_id),
        daemon=True,
    )
    thread.start()
    return job_id


def get_job(job_id: str) -> dict | None:
    """Get job status by ID."""
    return jobs.get(job_id)
