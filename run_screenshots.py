"""
CLI entry point for Stage 1.5b: Screenshot Extractor.

Usage:
    python run_screenshots.py "Bad Professor Lecture.mp4" data/output/final_chunks_v5.json --preview
    python run_screenshots.py "Bad Professor Lecture.mp4" data/output/final_chunks_v5.json -o data/output/screenshots.json
    python run_screenshots.py "Bad Professor Lecture.mp4" data/output/final_chunks_v5.json --skip-describe --preview
"""

import argparse
import os
import sys

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import OUTPUT_DIR
from src.screenshot_extractor import extract_all


def main():
    parser = argparse.ArgumentParser(
        description="Stage 1.5b: Extract screenshots from lecture video and match to chunks"
    )
    parser.add_argument("video", help="Path to the lecture video file (e.g. .mp4)")
    parser.add_argument("chunks", help="Path to Stage 1 chunks JSON file")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: data/output/screenshots.json)")
    parser.add_argument("--preview", "-p", action="store_true", help="Print screenshot summary to console")
    parser.add_argument("--threshold", "-t", type=float, default=30.0,
                        help="Frame difference threshold for slide detection (default: 30.0)")
    parser.add_argument("--skip-describe", action="store_true",
                        help="Skip Gemini multimodal description (useful for testing frame detection)")
    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.video):
        print(f"ERROR: Video not found: {args.video}")
        sys.exit(1)
    if not os.path.exists(args.chunks):
        print(f"ERROR: Chunks file not found: {args.chunks}")
        sys.exit(1)

    # Default output path
    output_json = args.output or os.path.join(OUTPUT_DIR, "screenshots.json")

    # Run extraction
    results = extract_all(
        video_path=args.video,
        chunks_path=args.chunks,
        output_json=output_json,
        threshold=args.threshold,
        skip_describe=args.skip_describe,
    )

    # Print preview
    if args.preview and results:
        print("\n" + "=" * 80)
        print("SCREENSHOT SUMMARY")
        print("=" * 80)
        print(f"{'#':>3}  {'Time':>7}  {'Chunk':>5}  {'File':<22}  {'Topic / Description'}")
        print("-" * 80)
        for ss in results:
            desc_preview = ss.description[:40].replace("\n", " ")
            if len(ss.description) > 40:
                desc_preview += "..."
            print(
                f"{ss.screenshot_index:>3}  "
                f"{ss.timestamp_display:>7}  "
                f"{ss.matched_chunk_index:>5}  "
                f"{ss.image_filename:<22}  "
                f"{ss.matched_chunk_topic[:25]}: {desc_preview}"
            )
        print("-" * 80)
        print(f"Total: {len(results)} screenshots across "
              f"{len(set(r.matched_chunk_index for r in results))} chunks")

    if not results:
        print("\nNo screenshots extracted. Try lowering --threshold (default 30.0).")


if __name__ == "__main__":
    main()
