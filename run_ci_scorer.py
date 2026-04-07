"""
CLI entry point for Stage 1.5a: CI% (Curriculum Importance) Scorer.

Usage:
    python run_ci_scorer.py data/output/final_chunks_v5.json --preview
    python run_ci_scorer.py data/output/final_chunks_v5.json -o data/output/ci_scores.json
"""

import argparse
import json
import os
import sys

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.ci_scorer import score_all
from src.config import OUTPUT_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Stage 1.5a: Score chunks for Curriculum Importance (CI%)"
    )
    parser.add_argument("chunks", help="Path to the Stage 1 chunks JSON file")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: data/output/ci_scores.json)")
    parser.add_argument("--preview", "-p", action="store_true", help="Print CI score summary to console")
    args = parser.parse_args()

    if not os.path.exists(args.chunks):
        print(f"ERROR: File not found: {args.chunks}")
        sys.exit(1)

    # Default output path
    output_path = args.output or os.path.join(OUTPUT_DIR, "ci_scores.json")

    print(f"Scoring chunks from: {args.chunks}")
    print(f"Output: {output_path}")
    print()

    scores = score_all(args.chunks, output_path)
    print(f"\nScored {len(scores)} chunks")

    # Print preview
    if args.preview or not args.output:
        print("\n" + "=" * 70)
        print("CI% SCORES")
        print("=" * 70)

        for s in scores:
            # Color-coded bar based on depth recommendation
            if s.depth_recommendation == "deep":
                icon = "🔴"
            elif s.depth_recommendation == "standard":
                icon = "🟡"
            else:
                icon = "🟢"

            bar_len = s.ci_percent // 5
            bar = "█" * bar_len + "░" * (20 - bar_len)

            print(f"\n{icon} Chunk {s.chunk_index}: {s.topic_name}")
            print(f"   CI: {s.ci_percent:3d}% [{bar}]  Depth: {s.depth_recommendation}")
            print(f"   Prof emphasis: {s.professor_emphasis}")
            print(f"   Reasoning: {s.ci_reasoning}")

        # Summary stats
        print("\n" + "-" * 70)
        deep = sum(1 for s in scores if s.depth_recommendation == "deep")
        standard = sum(1 for s in scores if s.depth_recommendation == "standard")
        light = sum(1 for s in scores if s.depth_recommendation == "light")
        avg_ci = sum(s.ci_percent for s in scores) / len(scores) if scores else 0
        print(f"Summary: {deep} deep | {standard} standard | {light} light | avg CI: {avg_ci:.0f}%")

    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
