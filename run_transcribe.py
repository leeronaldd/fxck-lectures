#!/usr/bin/env python3
"""CLI: Transcribe a lecture video/audio file using Groq Whisper.

Usage:
    python run_transcribe.py path/to/lecture.mp4
    python run_transcribe.py lecture.mp3 -o data/transcripts/output.txt
    python run_transcribe.py lecture.mp4 --timestamps --terms "icosahedral,peptidoglycan,Caliciviridae"

Cost: ~$0.04 per hour of audio (Whisper Large v3 Turbo on Groq).
"""

import argparse
import json
import sys
from pathlib import Path

from src.transcriber import transcribe
from src.config import OUTPUT_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe lecture video/audio to text using Groq Whisper"
    )
    parser.add_argument("input", help="Path to video or audio file")
    parser.add_argument("-o", "--output", help="Output transcript path (default: data/output/<name>.txt)")
    parser.add_argument("--timestamps", action="store_true", help="Include segment timestamps")
    parser.add_argument("--terms", help="Comma-separated medical terms to boost accuracy")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of plain text")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # Parse medical terms
    medical_terms = None
    if args.terms:
        medical_terms = [t.strip() for t in args.terms.split(",")]

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        ext = ".json" if args.json else ".txt"
        output_path = Path(OUTPUT_DIR) / f"{input_path.stem}_transcript{ext}"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Model:  whisper-large-v3-turbo (Groq)")
    print()

    result = transcribe(
        str(input_path),
        language=args.language,
        medical_terms=medical_terms,
        timestamps=args.timestamps,
    )

    meta = result.get("metadata", {})
    print(f"\nDuration:  {meta.get('duration_minutes', '?')} min")
    print(f"File size: {meta.get('file_size_mb', '?')} MB")
    print(f"Est. cost: ${meta.get('estimated_cost_usd', '?')}")

    # Write output
    if args.json:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result["text"])

    word_count = len(result["text"].split())
    print(f"Words:     {word_count}")
    print(f"\nTranscript saved to: {output_path}")

    # Preview first 500 chars
    preview = result["text"][:500]
    try:
        print(f"\n--- Preview ---\n{preview}\n--- End preview ---")
    except UnicodeEncodeError:
        print(f"\n--- Preview ---\n{preview.encode('ascii', errors='replace').decode()}\n--- End preview ---")


if __name__ == "__main__":
    main()
