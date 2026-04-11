"""Runner for Generator V2 — the 3-stage anatomy-professor pipeline.

Usage:
    # From existing Stage 1 chunks JSON
    python run_v2.py data/output/final_chunks_v5.json --subject microbiology

    # With lecture slides PDF
    python run_v2.py data/output/final_chunks_v5.json --slides lecture_slides.pdf

    # Dry run (prints prompts, no generation)
    python run_v2.py data/output/final_chunks_v5.json --dry-run

    # Single chunk test (run just chunk index 2)
    python run_v2.py data/output/final_chunks_v5.json --chunk 2
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.generator_v2 import (
    generate_lecture,
    generate_section,
    fetch_textbook_section,
    get_or_create_cache,
    clear_cache,
    build_system_instruction_text,
    assemble_slide_doc,
    assemble_transcript_doc,
    assemble_api_response,
    _is_housekeeping,
    _load_lecture_slides,
)
from src.config import GCP_PROJECT_ID, GCP_LOCATION, GENERATOR_MODEL, OUTPUT_DIR


def load_chunks(chunks_path: str) -> list[dict]:
    """Load Stage 1 chunks from JSON file."""
    with open(chunks_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    chunks = []
    for i, c in enumerate(raw):
        chunks.append({
            "chunk_index": c.get("chunk_index", i),
            "topic_name": c.get("topic_name", "Unknown"),
            "transcript_text": c.get("transcript_text", ""),
            "key_terms": c.get("key_terms", []),
            "emphasis_score": c.get("emphasis_score", "MEDIUM"),
            "word_count": c.get("word_count", 0),
        })
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Generator V2 — Anatomy Professor Pipeline")
    parser.add_argument("chunks_json", help="Path to Stage 1 chunks JSON file")
    parser.add_argument("--slides", help="Path to lecture slides (PDF or image directory, fallback)")
    parser.add_argument("--screenshots", help="Path to screenshots.json (per-chunk slide mapping)")
    parser.add_argument("--subject", default=None, help="Subject area for textbook search (e.g., 'microbiology')")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without generating")
    parser.add_argument("--chunk", type=int, default=None, help="Generate only this chunk index (for testing)")
    parser.add_argument("--model", default=None, help="Override generation model")
    parser.add_argument("--sequential", action="store_true", help="Run sequentially instead of parallel")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    # Load chunks
    print(f"\nLoading chunks from {args.chunks_json}...")
    all_chunks = load_chunks(args.chunks_json)
    print(f"  Loaded {len(all_chunks)} chunks")

    # Filter to single chunk if requested
    if args.chunk is not None:
        if 0 <= args.chunk < len(all_chunks):
            chunk = all_chunks[args.chunk]
            print(f"\n  Single chunk mode: [{args.chunk}] '{chunk['topic_name']}'")
            all_chunks = [chunk]
        else:
            print(f"  Error: chunk index {args.chunk} out of range (0-{len(all_chunks)-1})")
            sys.exit(1)

    # Generate
    sections = generate_lecture(
        chunks=all_chunks,
        lecture_slides_path=args.slides,
        screenshots_json=args.screenshots,
        subject=args.subject,
        model=args.model,
        dry_run=args.dry_run,
        parallel=not args.sequential,
    )

    if args.dry_run:
        print("\n  Dry run complete — no output files written.")
        return

    if not sections:
        print("\n  No sections generated.")
        return

    # Write output files
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(args.output_dir, exist_ok=True)

    # Slide document
    slide_doc = assemble_slide_doc(sections)
    slide_path = os.path.join(args.output_dir, f"v2_slides_{timestamp}.md")
    with open(slide_path, "w", encoding="utf-8") as f:
        f.write(slide_doc)
    print(f"\n  Slides: {slide_path}")

    # Transcript document
    transcript_doc = assemble_transcript_doc(sections)
    transcript_path = os.path.join(args.output_dir, f"v2_transcript_{timestamp}.md")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_doc)
    print(f"  Transcript: {transcript_path}")

    # API response JSON (what the frontend consumes)
    api_response = assemble_api_response(sections)
    api_path = os.path.join(args.output_dir, f"v2_api_response_{timestamp}.json")
    with open(api_path, "w", encoding="utf-8") as f:
        json.dump(api_response, f, indent=2, ensure_ascii=False)
    print(f"  API response: {api_path}")

    # Summary
    print(f"\n  {'='*40}")
    print(f"  Sections generated: {len(sections)}")
    for s in sections:
        ei_bar = "█" * (s.ei_percent // 10) + "░" * (10 - s.ei_percent // 10)
        strike = " ~~STRUCK~~" if s.ei_percent < 30 else ""
        print(f"    Slide {s.slide_number}: {s.group_name[:40]:<40} EI={s.ei_percent:>3}% {ei_bar}{strike}")
    print(f"  {'='*40}\n")


if __name__ == "__main__":
    main()
