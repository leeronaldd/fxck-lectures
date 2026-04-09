"""Pipeline runner — runs the pipeline as a generator that yields progress."""

import json
import sys
from pathlib import Path
from typing import Generator

# Project root — one level up from backend/
PROJECT_ROOT = Path(__file__).parent.parent


def _ensure_imports():
    """Add project root to sys.path so we can import src/ modules."""
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def run_pipeline(input_path: str) -> Generator[dict, None, None]:
    """Run the v4 pipeline, yielding progress dicts at each stage.

    Each yield is a dict with: status, stage, progress, error, output.
    The caller (SSE endpoint) sends these to the client.
    """
    _ensure_imports()

    output_dir = PROJECT_ROOT / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from src.models import Chunk
        from src.chunker import chunk_transcript

        input_file = Path(input_path)
        job_id = input_file.stem
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

        # --- Step 0 (conditional): Transcribe video ---
        if input_file.suffix in video_extensions:
            yield {"status": "running", "stage": "Transcribing lecture", "progress": 2}
            from src.transcriber import transcribe
            result = transcribe(input_path)
            text = result["text"]

            # Save transcript for reference
            transcript_path = output_dir / f"{job_id}_transcript.txt"
            transcript_path.write_text(text, encoding="utf-8")

            word_count = len(text.split())
            yield {"status": "running", "stage": "Transcribing lecture", "progress": 10,
                   "result": f"{word_count:,} words transcribed"}
        elif input_file.suffix == ".txt":
            text = input_file.read_text(encoding="utf-8")
        else:
            yield {"status": "error", "stage": "Chunking transcript", "progress": 5,
                   "error": f"Unsupported file type: {input_file.suffix}. Use .txt, .mp4, .mkv, .avi, .mov, or .webm"}
            return

        # --- Step 1: Chunking ---
        yield {"status": "running", "stage": "Chunking transcript", "progress": 12}
        chunks = chunk_transcript(text)
        chunks_path = output_dir / f"{job_id}_chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in chunks], f, indent=2)

        yield {"status": "running", "stage": "Chunking transcript", "progress": 15,
               "result": f"{len(chunks)} chunks"}

        # --- Step 2: CI% Scoring ---
        yield {"status": "running", "stage": "Scoring exam importance", "progress": 15}
        from src.ci_scorer import score_all
        ci_output = str(output_dir / f"{job_id}_ci.json")
        try:
            ci_scores = score_all(str(chunks_path), output_path=ci_output)
            ci_map = {s.chunk_index: s for s in ci_scores}
        except Exception as e:
            # CI scoring is non-fatal — continue without scores
            ci_map = {}
            yield {"status": "running", "stage": "Scoring exam importance", "progress": 20,
                   "result": f"Skipped: {e}"}

        # --- Step 3: Concept Grouping ---
        yield {"status": "running", "stage": "Grouping concepts", "progress": 25}
        from src.concept_grouper import group_chunks_deterministic, save_groups
        groups = group_chunks_deterministic(chunks, ci_map or None)
        groups_path = output_dir / f"{job_id}_groups.json"
        save_groups(groups, str(groups_path))

        yield {"status": "running", "stage": "Grouping concepts", "progress": 30,
               "result": f"{len(groups)} groups"}

        # --- Step 4: Load groups with transcripts ---
        from src.concept_grouper import load_groups_with_transcripts
        groups_with_text = load_groups_with_transcripts(str(groups_path), str(chunks_path))

        # --- Step 5: Generation ---
        yield {"status": "running", "stage": "Generating explanations", "progress": 35}
        from src.generator import generate_from_groups

        output_path = str(output_dir / f"{job_id}_output.md")
        generate_from_groups(
            groups_with_text,
            output_path=output_path,
            dry_run=False,
        )
        yield {"status": "running", "stage": "Generating explanations", "progress": 80}

        # --- Step 6: Fact checking ---
        yield {"status": "running", "stage": "Verifying sources", "progress": 85}
        verification_path = output_dir / f"{job_id}_verification.json"
        try:
            from src.fact_checker import fact_check_document
            fact_check_document(output_path, str(verification_path))
        except Exception:
            pass  # Non-fatal

        # --- Step 7: Completeness check ---
        yield {"status": "running", "stage": "Checking completeness", "progress": 90}
        try:
            from src.completeness_checker import check_completeness
            check_completeness(output_path, str(chunks_path))
        except Exception:
            pass  # Non-fatal

        # --- Step 8: Assembly ---
        yield {"status": "running", "stage": "Assembling final document", "progress": 95}

        # Read outputs — the generator saves JSON, so assemble markdown from explanation_text fields
        markdown = ""
        concept_groups = []
        verification = []

        if Path(output_path).exists():
            raw = json.loads(Path(output_path).read_text(encoding="utf-8"))
            # Assemble markdown from explanation_text fields
            md_parts = []
            for exp in raw:
                if isinstance(exp, dict):
                    text = exp.get("explanation_text", "")
                    topic = exp.get("topic_name", "")
                    if text and not exp.get("was_skipped", False):
                        md_parts.append(f"## {topic}\n\n{text}")
            markdown = "\n\n---\n\n".join(md_parts)

        if groups_path.exists():
            concept_groups = json.loads(groups_path.read_text(encoding="utf-8"))
        if verification_path.exists():
            verification = json.loads(verification_path.read_text(encoding="utf-8"))

        yield {
            "status": "done",
            "stage": "Done",
            "progress": 100,
            "output": {
                "markdown": markdown,
                "concept_groups": concept_groups,
                "verification_report": verification,
            },
        }

    except Exception as e:
        yield {"status": "error", "stage": "Pipeline error", "progress": 0, "error": str(e)}
