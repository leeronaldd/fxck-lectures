"""
CLI entry point for Stage 1: Transcript Chunker.

Accepts either a transcript .txt file OR a lecture video/audio file.
If given a video/audio, it transcribes first using Groq Whisper ($0.04/hr),
then chunks the transcript.

Usage:
    # From transcript (existing behavior)
    python run_stage1.py "data/transcripts/Bad Professor transcript.txt"

    # From video (auto-transcribes first)
    python run_stage1.py "Bad Professor Lecture.mp4"

    # From audio
    python run_stage1.py lecture.mp3 --terms "icosahedral,peptidoglycan"

    python run_stage1.py input_file --output data/output/chunks.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.chunker import chunk_transcript
from src.config import OUTPUT_DIR, TRANSCRIPTS_DIR

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac"}


def main():
    parser = argparse.ArgumentParser(
        description="Stage 1: Transcribe (if video/audio) and chunk a lecture"
    )
    parser.add_argument("input", help="Path to transcript .txt, or video/audio file")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: auto-generated)")
    parser.add_argument("--preview", "-p", action="store_true", help="Print chunk summary to console")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM calls (flag for Stage 2 expansion instead)")
    parser.add_argument("--terms", help="Comma-separated medical terms to boost STT accuracy")
    parser.add_argument("--language", default="en", help="Language code for STT (default: en)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    ext = input_path.suffix.lower()

    # --- If video/audio: transcribe first ---
    if ext in VIDEO_EXTS | AUDIO_EXTS:
        from src.transcriber import transcribe

        medical_terms = None
        if args.terms:
            medical_terms = [t.strip() for t in args.terms.split(",")]

        print(f"{'Video' if ext in VIDEO_EXTS else 'Audio'} detected → transcribing with Groq Whisper...")
        result = transcribe(
            str(input_path),
            language=args.language,
            medical_terms=medical_terms,
        )

        meta = result.get("metadata", {})
        print(f"  Duration:  {meta.get('duration_minutes', '?')} min")
        print(f"  Est. cost: ${meta.get('estimated_cost_usd', '?')}")
        print(f"  Words:     {len(result['text'].split())}")

        # Save transcript to data/transcripts/
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
        transcript_path = Path(TRANSCRIPTS_DIR) / f"{input_path.stem}_transcript.txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(result["text"])
        print(f"  Transcript saved: {transcript_path}")

        text = result["text"]
    else:
        # --- Existing behavior: read transcript file ---
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

    print(f"\nLoaded transcript: {len(text)} chars, ~{len(text.split())} words")

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
        basename = os.path.splitext(os.path.basename(args.input))[0]
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
