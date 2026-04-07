# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI tool that transforms bad medical lecture transcripts into lecture-replacement documents. A student reads the output instead of watching the lecture and understands 100% of the content. Built for a 1st year Biomedical Science student at Griffith University.

The tool is NOT a summarizer or note-taker — it re-explains concepts from scratch using a teacher-student agent loop, producing output quality equivalent to the best human tutor.

## Critical Development Principles

### Teaching philosophy: concrete → abstract, never definition-first
A real tutor starts with a real-life example ("Timmy's mum gives him $10 to buy oranges"), gets the student thinking, THEN introduces the formal framework and terminology. The tool must do the same:
1. Hook with something concrete the student already understands
2. Build the concept using that concrete example
3. Introduce the scientific term AFTER the student understands what it does (functional naming)
4. Only then show the formal definition/framework

Never start a section with "X is a Y that..." — that's explaining to someone who already understands. Start with WHY they should care, then HOW it works, then WHAT it's called.

### The tool re-explains, it doesn't compress
This is NOT a summarizer or note-taker. Studley/Turbo AI compress the professor's words into cleaner notes, but they never ask "was this explained well?" If the professor rambles incoherently for 20 minutes, those tools produce cleaner rambling. This tool throws out the professor's explanation and teaches from scratch, using the transcript only as a source of WHAT to teach — not HOW.

### Fix the pipeline, not the output
When the output has a problem (wrong term, missing content, bad formatting), the fix MUST go into the code/prompts — never hand-edit the output markdown. Every fix should work for ALL future lectures, not just the current one. Ask: "if I ran this on a different lecture tomorrow, would this fix still apply?"

### Quality issues are prompt issues, not architecture issues
When the generated text is missing vivid hooks, uses the wrong tone, or misses a term — tune the system prompt or the pipeline logic. Don't iterate by manually editing output files. The system prompt in `src/generator.py` is the single source of truth for writing quality.

### Colloquial over clinical
The output should read like a personal tutor talking to a friend, not a textbook. Use "steal" not "takes a portion", "hijack" not "commandeer". Contractions always. If a revision makes the writing more formal/clinical, it's a regression even if it's more "accurate."

### The student must have exam vocabulary
It's not enough to describe a concept colloquially — the scientific term MUST appear so the student can use it on exams. If the output describes "pushing out and wrapping in host membrane" without saying "budding", that's a bug.

### Don't trust the professor
The professor skims hard stuff and yaps on easy stuff. CI% scoring must use curriculum standards as primary source, not professor emphasis. Scoring everything 70-90% is useless — differentiate aggressively (naming conventions = 10%, Baltimore = 95%).

### Skip at two levels, not one
Skipping happens at **group level** (concept grouper marks entire sections as skip) AND **sub-topic level** (the generator autonomously trims yap within sections it's generating). The generator asks: "If I only had 1 hour per week with this student, would I spend time on this?" History-of-discovery stories, redundant examples, tangential trivia — cut or condense to one sentence. Don't faithfully reproduce every point just because the professor said it.

### Over-chunk > under-chunk
An LLM can't explain 7 things at once. Each concept needs its own chunk so the generator focuses on ONE thing.

### Transcripts are garbage
Auto-captioned transcripts are full of misspellings ("khesi virus" for Caliciviridae, "kosahhedral" for icosahedral). The generator must correct these, not parrot them. Key term extraction from transcripts produces noise — filter aggressively (sentence fragments, filler words, stutters).

### Slides contain content the transcript misses
The professor shows slides with content (plaque assay, RT-PCR diagrams) that the auto-caption doesn't capture. The pipeline must extract terms from slide descriptions and check them, not just transcript key terms.

### Save tokens for where quality matters
Regex chunking is free. Use cheap models (Gemini Flash) for simple tasks like CI% scoring, concept grouping, slide mapping. Save expensive models (Gemini Pro) for explanation generation.

## Architecture

V4 pipeline (Stages 0-2 implemented):

```
Stage 0: Transcription (src/transcriber.py) — optional, if input is video/audio
    → Groq Whisper Large v3 Turbo ($0.04/hr)
    → auto audio extraction via ffmpeg, chunking for large files
    → saves transcript to data/transcripts/
    ↓
Stage 1: Chunking (src/chunker.py)
    → regex splitting with Gemini Flash fallback
    ↓
Stage 1.5a: CI% Scoring (src/ci_scorer.py)
    → exam importance 0-100, recalibrated to use full range
    ↓
Stage 1.5b: Screenshot Extraction (src/screenshot_extractor.py)
    → OpenCV frame detection + Gemini Flash descriptions
    ↓
Concept Grouper (src/concept_grouper.py)
    → merges ~14 chunks into ~8 logical groups
    → marks skips, expansion targets, reorders for learning flow
    ↓
Stage 2: Explanation Generation (src/generator.py)
    → Gemini 3.1 Pro, v1 conversational tutor prompt
    → per concept group, not per chunk/slide
    → textbook chapter fetched from OpenStax as factual reference
    → Google Search grounding enabled during generation
    ↓
Fact-Check & Correct (src/fact_checker.py)
    → Flash reads entire output per section + textbook + Google Search
    → flags errors against reputable sources (NIH, PubMed, textbooks)
    → Pro surgically rewrites flagged paragraphs
    ↓
Completeness Checker (src/completeness_checker.py)
    → grep terms + slide-derived terms (Flash extraction)
    → inserts inline skip-lines for low-CI% misses
    ↓
Slide Reference Insertion (src/slide_inserter.py)
    → post-processing: maps slides to paragraphs
    ↓
Assembly (run_stage2.py → assemble_markdown)
    → inline slide images, skip lines, final markdown
```

Not yet implemented (Stage 3-5 — Teacher-Student Agent Loop):

```
Stage 3: Evaluation (EVERY chunk, cheap — Gemini Flash)
    → 5-dimension scoring:
      1. Hook quality (does it open with something engaging?)
      2. Terminology timing (terms introduced in context, not upfront?)
      3. Assumed knowledge (does it assume concepts not yet explained?)
      4. Mechanism clarity (are multi-step processes broken down?)
      5. Concreteness (real examples, not abstract definitions?)
    → Score each dimension 1-5
    ↓
    ├── ALL dimensions ≥ 4/5 → SHIP (skip Stage 4-5)
    └── ANY dimension < 4 → ACTIVATE Stage 4
    ↓
Stage 4: Conditional Optimization (teacher revises flagged dimensions)
    → Only rewrites the failing aspects, not the whole section
    → Re-evaluates after revision (confirm score improved)
    ↓
Stage 5: Conditional Student Agent (ONLY if Stage 4 output still < 4)
    → Simulated student reads the explanation
    → Flags specific confusion: "what are cytokines?" "why lipid A specifically?"
    → Teacher patches those specific gaps
    → Max 3 iterations, then ship
    → Re-evaluate with Stage 3 to confirm improvement
```

Key architecture decision: **Progressive escalation, not upfront routing.**
Don't use a master agent to guess complexity upfront. Let the evaluator scores
BE the routing signal. Simple chunks pass Stage 3 and skip everything else.
Complex chunks that fail evaluation enter the loop. This saves ~40% tokens
vs running all stages on every chunk.

Estimated token budget per lecture (~8 chunks):
- Stages 1-2 + completeness + slides: ~50K tokens (non-negotiable base quality)
- Stage 3 evaluation: ~8K tokens (cheap, always runs)
- Stages 4-5 (conditional): ~0-30K depending on how many chunks fail
- Total: ~60-90K tokens per lecture

### Factual Accuracy Strategy (implemented)
- **Generation-time grounding**: Gemini Pro has Google Search enabled during generation — it verifies claims while writing, not after
- **Textbook RAG during generation**: relevant OpenStax chapter fetched and included as primary factual context in the generation prompt. Hardcoded URL lookup table (100% reliable). Rule: "textbook wins on facts, professor wins on scope"
- **Post-generation verification**: Flash + Google Search reads the entire output per section, flags errors against textbook + reputable medical sources (NIH, PubMed, NCBI, .edu)
- **Pro correction loop**: surgically rewrites flagged paragraphs while maintaining colloquial tone. Conditional — only runs when errors found
- Error rate: 11 → 1 across 6 prompt iterations + textbook RAG

### Textbook RAG (planned — not yet implemented)
The gold standard for accuracy: use the student's prescribed textbook as the primary knowledge source.
- Student enters university + course during onboarding
- Pipeline searches for prescribed textbook (e.g., Prescott's Microbiology 16th ed)
- First priority: university's own textbook. Fallback: OpenStax or NCBI Bookshelf (free, peer-reviewed)
- Textbook chunks stored in vector DB, used as RAG context during generation
- Every claim grounded in the actual textbook the exam will test from

## Running

```bash
# Stage 0+1: From video (transcribes then chunks)
python run_stage1.py "data/input/Bad Professor Lecture.mp4" --preview
python run_stage1.py lecture.mp4 --terms "icosahedral,peptidoglycan" --preview

# Stage 1: From transcript (existing behavior)
python run_stage1.py "data/transcripts/Bad Professor transcript.txt" --preview

# Standalone transcription only
python run_transcribe.py "Bad Professor Lecture.mp4" --timestamps --json

# Stage 1.5a: CI% Scoring
python run_ci_scorer.py data/output/final_chunks_v5.json -o data/output/v4_ci_scores.json --preview

# Full V4 Pipeline (recommended)
python run_stage2.py data/output/final_chunks_v5.json --v4 \
  --ci data/output/v4_ci_scores.json \
  --screenshots data/output/screenshots.json \
  --preview

# V4 with deterministic grouping (no LLM for grouping step)
python run_stage2.py data/output/final_chunks_v5.json --v4 --no-llm-group \
  --ci data/output/v4_ci_scores.json \
  --screenshots data/output/screenshots.json \
  --preview

# Dry-run (print prompts, no generation)
python run_stage2.py data/output/final_chunks_v5.json --v4 --dry-run --no-llm-group --skip-ci
```

## Tech Stack

- Python 3.10+ with Pydantic
- Google Vertex AI via google-genai SDK (vertexai=True)
- Groq API for STT (Whisper Large v3 Turbo, $0.04/hr)
- ffmpeg for audio extraction from video
- Generation model: `gemini-3.1-pro-preview`
- Cheap/fast model: `gemini-3-flash-preview`
- STT model: `whisper-large-v3-turbo` (Groq)
- GCP Project: `project-bc1fc31b-94c5-44b0-904`
- Frontend (future): Supabase + Vercel

## File Structure

```
src/
  transcriber.py           # Stage 0: Groq Whisper STT with auto chunking
  chunker.py               # Stage 1: regex splitting, emphasis, prerequisites
  ci_scorer.py             # Stage 1.5a: CI% exam importance scoring
  screenshot_extractor.py  # Stage 1.5b: OpenCV slide extraction + Flash descriptions
  slide_chunker.py         # Slide-based chunking (legacy, superseded by concept grouper)
  concept_grouper.py       # Merge/reorder/skip pass on Stage 1 chunks
  generator.py             # Stage 2: system prompt + Gemini Pro generation
  fact_checker.py            # Textbook RAG + Google Search verification + Pro correction loop
  completeness_checker.py  # Grep + slide-term coverage check + auto-fix
  slide_inserter.py        # Post-processing slide references (companion doc only, inline done in assembly)
  json_repair.py           # Robust JSON extraction from truncated Flash responses
  models.py                # Pydantic models
  config.py                # Vertex AI + Groq config (env-var switchable models)
run_stage1.py              # CLI: Stage 0+1 (accepts video/audio OR transcript)
run_transcribe.py          # CLI: standalone transcription
run_ci_scorer.py           # CLI: CI% scoring
run_screenshots.py         # CLI: screenshot extraction
run_slide_chunker.py       # CLI: slide-based chunking
run_stage2.py              # CLI: full V4 pipeline
data/
  input/                   # Raw lecture files (video, audio)
  transcripts/             # Transcribed .txt files (from Stage 0 or manual)
  output/                  # Pipeline outputs (JSON, markdown)
    screenshots/           # Extracted lecture slide images
    _archive/              # Old iterations (kept for reference, not used by pipeline)
docs/
  reference/               # Gold standard examples (anatomy slides, Studley output)
  anatomy-style-analysis.md  # Deep analysis of anatomy professor's teaching patterns
```

## Reference Documents

- `docs/anatomy-style-analysis.md` — 7 transferable teaching rules from the anatomy professor (question-answer chain, functional naming, inclusive language, etc.). Used selectively for complex concepts.
- `dev-logs/` — session snapshots: what changed, what worked, what failed, what to try next.
