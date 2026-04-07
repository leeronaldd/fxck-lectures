#!/usr/bin/env python3
"""Slide-based chunking CLI: chunk transcript by detected slide transitions.

Usage:
    python run_slide_chunker.py "data/transcripts/Bad Professor transcript.txt" data/output/screenshots.json --preview
    python run_slide_chunker.py "data/transcripts/Bad Professor transcript.txt" data/output/screenshots.json -o data/output/slide_chunks.json
    python run_slide_chunker.py "data/transcripts/Bad Professor transcript.txt" data/output/screenshots.json --duration 6904
"""

import argparse
from src.slide_chunker import chunk_all


def main():
    parser = argparse.ArgumentParser(
        description="Chunk transcript by detected slide transitions from lecture video"
    )
    parser.add_argument("transcript_path", help="Path to transcript .txt file")
    parser.add_argument("screenshots_path", help="Path to screenshots.json from Stage 1.5b")
    parser.add_argument("-o", "--output", help="Output path for slide chunks JSON")
    parser.add_argument("--duration", type=float, default=None,
                        help="Video duration in seconds (auto-detected if omitted)")
    parser.add_argument("--threshold", type=int, default=800,
                        help="Word count threshold for sub-chunking (default: 800)")
    parser.add_argument("-p", "--preview", action="store_true",
                        help="Print summary table")

    args = parser.parse_args()

    output_path = args.output or "data/output/slide_chunks.json"

    slides = chunk_all(
        transcript_path=args.transcript_path,
        screenshots_path=args.screenshots_path,
        output_path=output_path,
        video_duration=args.duration,
        sub_chunk_threshold=args.threshold,
    )

    if args.preview:
        import sys, io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print(f"\n{'Slide':<6} {'Time':<18} {'Words':<7} {'Sub?':<5} {'Emph':<6} {'Topic'}")
        print("-" * 95)
        for s in slides:
            sub = "YES" if s.needs_sub_chunking else ""
            print(f"{s.slide_index:<6} {s.timestamp_display:<18} {s.word_count:<7} {sub:<5} {s.emphasis_score:<6} {s.topic_name[:50]}")
        print("-" * 90)
        total = sum(s.word_count for s in slides)
        sub_count = sum(1 for s in slides if s.needs_sub_chunking)
        print(f"Total: {total:,} words across {len(slides)} slides ({sub_count} flagged for sub-chunking)")


if __name__ == "__main__":
    main()
