# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI tool that transforms bad medical lecture transcripts into lecture-replacement documents. A student reads the output instead of watching the lecture and understands 100% of the content. Built for a 1st year Biomedical Science student at Griffith University.

The tool is NOT a summarizer or note-taker — it re-explains concepts from scratch using a teacher-student agent loop, producing output quality equivalent to the best human tutor.

## Architecture

7-stage pipeline (only Stage 1 is implemented so far):

1. **Chunking** (`src/chunker.py`) — token-free regex splitting with Gemini Flash fallback for multi-concept sub-chunking
2. **Explanation Generation** — teacher agent writes tutor-quality explanations
3. **Evaluation** — 5-dimension scoring (hook quality, terminology timing, assumed knowledge, mechanism clarity, concreteness)
4. **Conditional Optimization** — revise only chunks scoring below 4/5
5. **Conditional Student Agent** — simulated student flags confusion, teacher patches
6. **Enrichment** — CI% (exam importance), slide references, dev-log update
7. **Assembly** — combine into one cohesive lecture-replacement document

## Running Stage 1

```bash
# Basic run (with LLM sub-chunking via Vertex AI)
python run_stage1.py "data/transcripts/Bad Professor transcript.txt" --preview

# Without LLM (flags multi-concept chunks for Stage 2 expansion instead)
python run_stage1.py "data/transcripts/Bad Professor transcript.txt" --no-llm --preview

# Custom output path
python run_stage1.py "path/to/transcript.txt" -o "data/output/my_chunks.json"
```

## Key Design Principles

- **Over-chunk > under-chunk**: An LLM can't explain 7 things at once. Each concept needs its own chunk so the generator focuses on ONE thing.
- **Don't trust professor emphasis blindly**: "Don't memorize" + "important" = understand deeply (contradictory emphasis). Professor skims hard stuff, yaps on easy stuff.
- **Save tokens for where quality matters**: Regex chunking is free. Use cheap models (Gemini Flash) for simple tasks. Save expensive models for explanation generation and evaluation.
- **CI% uses external knowledge**: Importance isn't just what the professor emphasized — it's what medical schools actually assess.

## Tech Stack

- Python 3.10+ with Pydantic
- Google Vertex AI (Gemini Flash for chunking fallback, Gemini Pro for generation)
- GCP Project: `project-bc1fc31b-94c5-44b0-904`
- Frontend (future): Supabase + Vercel

## File Structure

```
src/
  chunker.py      # Stage 1: marker detection, splitting, emphasis, prerequisites
  models.py       # Pydantic models (Chunk, EmphasisSignal)
  config.py       # Vertex AI project/model settings
run_stage1.py     # CLI entry point for Stage 1
data/
  transcripts/    # Input .txt transcript files
  output/         # Chunked JSON output
```
