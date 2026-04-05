"""
CLI entry point for Stage 1: Transcript Chunker.

Usage:
    python run_stage1.py "data/transcripts/Bad Professor transcript.txt"
    python run_stage1.py "data/transcripts/Bad Professor transcript.txt" --output data/output/chunks.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.chunker import chunk_transcript
from src.config import OUTPUT_DIR


def main():
    parser = argparse.ArgumentParser(description="Stage 1: Chunk a lecture transcript")
    parser.add_argument("transcript", help="Path to the transcript .txt file")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: auto-generated)")
    parser.add_argument("--preview", "-p", action="store_true", help="Print chunk summary to console")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM calls (flag for Stage 2 expansion instead)")
    args = parser.parse_args()

    # Read transcript
    if not os.path.exists(args.transcript):
        print(f"ERROR: File not found: {args.transcript}")
        sys.exit(1)

    with open(args.transcript, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"Loaded transcript: {len(text)} chars, ~{len(text.split())} words")

    # Run chunker
    chunks = chunk_transcript(text, use_llm=not args.no_llm)
    print(f"Produced {len(chunks)} chunks")

    # Print preview
    if args.preview or not args.output:
        print("\n" + "=" * 70)
        print("CHUNK SUMMARY")
        print("=" * 70)
        for chunk in chunks:
            emphasis_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[chunk.emphasis_score]
            print(f"\n{emphasis_icon} Chunk {chunk.chunk_index}: {chunk.topic_name}")
            print(f"   Words: {chunk.word_count} | Emphasis: {chunk.emphasis_score}")
            if chunk.emphasis_signals:
                for sig in chunk.emphasis_signals:
                    icon = "⬆️" if sig.sentiment == "positive" else "⬇️"
                    print(f"   {icon} \"{sig.keyword}\" — {sig.context[:80]}...")
            if chunk.key_terms:
                print(f"   Terms: {', '.join(chunk.key_terms[:10])}")
            if chunk.prerequisites:
                print(f"   Prerequisites: {', '.join(chunk.prerequisites[:8])}")
            if chunk.forward_references:
                print(f"   ⚠️ Forward refs: {', '.join(chunk.forward_references[:5])}")
            if chunk.reorder_suggestion:
                print(f"   🔄 Reorder: {chunk.reorder_suggestion}")
            if chunk.needs_expansion:
                print(f"   📖 NEEDS EXPANSION: {chunk.expansion_hint}")
            # Show first 150 chars of transcript
            preview = chunk.transcript_text[:150].replace("\n", " ")
            print(f"   Preview: \"{preview}...\"")

    # Save output
    output_path = args.output
    if not output_path:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        basename = os.path.splitext(os.path.basename(args.transcript))[0]
        output_path = os.path.join(OUTPUT_DIR, f"{basename}_{timestamp}_chunks.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [chunk.model_dump() for chunk in chunks],
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
