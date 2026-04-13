#!/usr/bin/env python3
"""V3 CLI: Slide-driven lecture generation.

Usage:
    # Dry-run — see the Flash teaching plan without generating
    python run_v3.py data/output/screenshots.json data/transcripts/lecture2_transcript.txt --dry-run

    # Full generation
    python run_v3.py data/output/screenshots.json data/transcripts/lecture2_transcript.txt

    # With subject hint for textbook search
    python run_v3.py data/output/screenshots.json data/transcripts/lecture2_transcript.txt --subject microbiology

    # Sequential mode (slower, for debugging)
    python run_v3.py data/output/screenshots.json data/transcripts/lecture2_transcript.txt --sequential

    # With slides PDF for Flash to see actual images
    python run_v3.py data/output/screenshots.json data/transcripts/lecture2_transcript.txt --slides lecture2.pdf

    # Preview output in console
    python run_v3.py data/output/screenshots.json data/transcripts/lecture2_transcript.txt --preview
"""

import argparse
import json
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="V3: Slide-driven lecture generation"
    )
    parser.add_argument("screenshots_json", help="Path to screenshots.json")
    parser.add_argument("transcript", help="Path to transcript .txt file")
    parser.add_argument("--slides", help="Path to lecture slides PDF (optional)")
    parser.add_argument("--subject", help="Subject area for textbook search")
    parser.add_argument("--model", help="Override generation model")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    parser.add_argument("--sequential", action="store_true", help="No parallel")
    parser.add_argument("--preview", action="store_true", help="Print output to console")
    parser.add_argument("-o", "--output", help="Output directory", default="data/output")
    parser.add_argument("--job-id", help="Job ID for GCS uploads", default="")

    args = parser.parse_args()

    # Validate inputs
    screenshots_path = Path(args.screenshots_json)
    transcript_path = Path(args.transcript)

    if not screenshots_path.exists():
        print(f"Error: Screenshots file not found: {screenshots_path}")
        sys.exit(1)
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  V3 Slide-Driven Pipeline")
    print(f"  Screenshots: {screenshots_path}")
    print(f"  Transcript:  {transcript_path}")
    if args.slides:
        print(f"  Slides PDF:  {args.slides}")
    print(f"  Mode:        {'dry-run' if args.dry_run else 'parallel' if not args.sequential else 'sequential'}")
    print(f"{'='*60}\n")

    from src.generator_v3 import (
        generate_lecture_v3,
        assemble_slide_doc,
        assemble_transcript_doc,
        assemble_api_response,
    )

    t0 = time.time()

    sections, groups = generate_lecture_v3(
        screenshots_json=args.screenshots_json,
        transcript_path=args.transcript,
        lecture_slides_path=args.slides,
        subject=args.subject,
        model=args.model,
        dry_run=args.dry_run,
        parallel=not args.sequential,
        job_id=args.job_id,
    )

    if args.dry_run:
        return

    if not sections:
        print("No sections generated.")
        return

    # Save outputs
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")

    # Slide doc
    slide_doc = assemble_slide_doc(sections)
    slide_path = output_dir / f"v3_slides_{timestamp}.md"
    with open(slide_path, "w", encoding="utf-8") as f:
        f.write(slide_doc)
    print(f"  Slides: {slide_path}")

    # Transcript doc
    transcript_doc = assemble_transcript_doc(sections)
    transcript_out = output_dir / f"v3_transcript_{timestamp}.md"
    with open(transcript_out, "w", encoding="utf-8") as f:
        f.write(transcript_doc)
    print(f"  Transcript: {transcript_out}")

    # API response (JSON for frontend)
    api_response = assemble_api_response(sections)
    api_path = output_dir / f"v3_api_{timestamp}.json"
    with open(api_path, "w", encoding="utf-8") as f:
        json.dump(api_response, f, indent=2, ensure_ascii=False)
    print(f"  API JSON: {api_path}")

    # Teaching plan (for debugging)
    plan_data = []
    for g in groups:
        plan_data.append({
            "group_index": g.group_index,
            "title": g.title,
            "slide_indices": g.slide_indices,
            "depth": g.depth,
            "ei_estimate": g.ei_estimate,
            "word_estimate": g.word_estimate,
            "teaching_plan": g.teaching_plan,
            "key_terms": g.key_terms,
            "new_terms": g.new_terms,
            "prior_terms": g.prior_terms,
            "transcript_words": len(g.transcript_excerpt.split()),
        })
    plan_path = output_dir / f"v3_plan_{timestamp}.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, indent=2, ensure_ascii=False)
    print(f"  Plan: {plan_path}")

    total_words = sum(len(s.transcript.split()) for s in sections)
    t_total = time.time() - t0
    print(f"\n  Total: {len(sections)} sections, {total_words} words in {t_total:.0f}s")

    # Preview
    if args.preview:
        print(f"\n{'='*60}")
        print(f"  TRANSCRIPT PREVIEW")
        print(f"{'='*60}")
        for s in sections:
            print(f"\n--- Slide {s.slide_number}: {s.group_name} (EI{s.ei_percent}%) ---")
            # Show first 500 chars
            preview = s.transcript[:500]
            if len(s.transcript) > 500:
                preview += "..."
            print(preview)


if __name__ == "__main__":
    main()
