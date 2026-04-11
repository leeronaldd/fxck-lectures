# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI tool that transforms bad medical/health lecture transcripts into lecture-replacement documents. A student reads the output instead of watching the lecture and understands 100% of the content. General-purpose for all medical, health, and science lectures — not limited to any specific subject.

Pipeline is personalized via a 4-question quiz onboarding (program, year, frustration, referral) stored in Supabase `user_profiles`. Generator adjusts depth/tone by year level.

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

V2 pipeline (3-stage parallel architecture, replaced V1's 8 stages):

```
Stage 0: Transcription (src/transcriber.py) — optional, if input is video/audio
    → Gemini Flash multimodal audio (~$0.02/2hr lecture, no rate limits)
    → auto audio extraction via ffmpeg, chunking for large files
    ↓
Stage 0.5: Screenshot Extraction (src/screenshot_extractor.py) — if video input
    → OpenCV frame detection + Gemini Flash descriptions
    → matched to chunks by timestamp
    ↓
Stage 1: Chunking (src/chunker.py)
    → regex splitting with Gemini Flash fallback
    ↓
Stage 2: V2 Generation (src/generator_v2.py) — all parallel
    ↓
    ├── Flash prefetch (parallel, ~10s)
    │   → teaching summaries + term tracking for all chunks
    │   → term ownership assigned by Python set arithmetic
    │
    ├── Flash textbook fetch (parallel, ~30s)
    │   → OpenStax content via Google Search grounding per chunk
    │
    └── Pro generation (parallel, ~60s)
        → creative brief with anatomy professor style transfer
        → context caching (system instruction cached once)
        → per-chunk: prior previews + textbook + transcript + slides
        → output: slide doc + transcript + EI% per section
    ↓
Assembly (Python parser, no LLM)
    → splits delimited output into slides.json + transcript.json
    → frontend renders two-panel layout
```

Old V1 files (src/generator.py, ci_scorer.py, concept_grouper.py, fact_checker.py, 
completeness_checker.py, slide_inserter.py) kept as fallback but not used by V2.

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
- **Textbook RAG during generation**: relevant OpenStax chapter fetched via `src/textbook_search.py` — 89 keyword entries across 12 OpenStax textbooks. Multi-tier: keyword match → Flash LLM pick → NCBI Bookshelf API → graceful skip. File-based cache with 90-day TTL. Rule: "textbook wins on facts, professor wins on scope"
- **Post-generation verification**: Flash + Google Search reads the entire output per section, flags errors against textbook + reputable medical sources (NIH, PubMed, NCBI, .edu)
- **Pro correction loop**: surgically rewrites flagged paragraphs while maintaining colloquial tone. Conditional — only runs when errors found
- Error rate: 11 → 1 across 6 prompt iterations + textbook RAG

### Textbook RAG (implemented — OpenStax + NCBI)
Uses `src/textbook_search.py` for dynamic retrieval:
- 89 keyword entries across 12 OpenStax textbooks (microbiology, anatomy, biology, chemistry, psychology, pharmacology, nursing, nutrition, psychiatric, population health)
- Multi-tier: keyword match (free) → Flash LLM numbered-list pick (cheap) → NCBI Bookshelf API (free) → graceful skip
- File-based cache in `data/textbook_cache/` with 90-day TTL
- Handles JavaScript-only pages with CNX API fallback
- Future: university-specific prescribed textbooks via vector DB

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
- Frontend: Next.js 16, React 19, Zustand, Tailwind v4, deployed on Vercel
- Backend: FastAPI on GCP Cloud Run (australia-southeast1)
- Auth: Supabase (Google OAuth + email/password + magic link)
- GCP Project: `project-bc1fc31b-94c5-44b0-904`
- Supabase Project: `husdhmaijvughqezlmjt`
- Live: https://fxck-lectures.vercel.app
- API: https://fxck-lectures-api-211270844056.australia-southeast1.run.app
- Repo: github.com/leeronaldd/fxck-lectures (public, branch: style-transfer-v1)

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
  textbook_search.py         # Dynamic OpenStax + NCBI textbook retrieval (89 keyword entries, 12 books)
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
backend/
  app/
    main.py                # FastAPI app — /api/upload, /api/run/{file_id} (SSE)
    auth.py                # Supabase JWT verification via JWKS (ES256)
    pipeline.py            # Pipeline runner — generator yielding progress dicts
    models.py              # Pydantic request/response schemas
  requirements.txt
  deploy.sh                # Cloud Run deploy script
  Dockerfile               # At project root (not in backend/)
frontend/
  src/
    app/
      page.tsx             # Landing page (sales page with sample preview)
      quiz/page.tsx        # 4-question onboarding quiz funnel
      reader/page.tsx      # Document reader
      processing/page.tsx  # Pipeline progress stepper
      signin/page.tsx      # Auth page (Google OAuth + email)
      settings/page.tsx    # Settings (Account, Billing, Usage, Privacy, Customization)
      upload/page.tsx      # Upload dashboard (drag-drop + recent sessions)
      layout.tsx           # Root layout with AuthProvider
    components/
      AuthProvider.tsx     # Supabase auth state listener
      AppShell.tsx         # Top bar + sidebar wrapper + route protection
      AppSidebar.tsx       # Session list + account menu
      UploadZone.tsx       # Drag-drop file upload
      PipelineStepper.tsx  # 9-stage progress display
      MarkdownRenderer.tsx # Custom markdown with exam alerts, skip lines
      TrustBar.tsx         # Verification status bar
    lib/
      supabase.ts          # Supabase browser client
      api.ts               # Backend API client (upload + SSE streaming)
      store.ts             # Zustand state management
      types.ts             # TypeScript interfaces
      data.ts              # Static data fetching helpers
docs/
  reference/               # Gold standard examples (anatomy slides, Studley output)
  anatomy-style-analysis.md  # Deep analysis of anatomy professor's teaching patterns
```

## Reference Documents

- `docs/anatomy-style-analysis.md` — 7 transferable teaching rules from the anatomy professor (question-answer chain, functional naming, inclusive language, etc.). Used selectively for complex concepts.
- `dev-logs/` — session snapshots: what changed, what worked, what failed, what to try next.



# How We Write System Prompts — Read This Before Writing Any Prompt

## The Rule

Never write a system prompt as a list of orders. No "YOU MUST", no "NEVER do X", no "ALWAYS do Y", no bullet-pointed commands. That produces robotic, rule-following output where the model is checking boxes instead of thinking.

Instead, write every system prompt like a creative brief you'd hand to a talented author before they ghost-write something for you. You're talking to a collaborator, not issuing commands to a machine.

## What a Good Prompt Looks Like

Share examples of writing you love and explain what makes them work. Describe the audience — who's reading this, what do they already know, what are they feeling. Talk about the three drives or principles behind the work, the way one writer talks to another about craft. Paste in reference samples so the model can absorb the style by reading it, the same way a new writer learns by reading good writing. Mention hard constraints (word count ranges, accuracy requirements, terms that must appear) at the end as contract terms — brief, firm, non-negotiable. Those stay directive because they're factual constraints, not style opinions.

## What a Bad Prompt Looks Like

50 bullet points starting with "MUST", "NEVER", "ALWAYS", "CRITICAL", "DO NOT". Numbered rules. Sections titled "=== REQUIREMENTS ===". Shouting in caps. Treating the model like a misbehaving employee instead of a skilled collaborator. The word "prompt" itself carries baggage — if you find yourself writing something that feels like a prompt, stop and rewrite it as a conversation.

## Variable Naming

Don't call it `SYSTEM_PROMPT`. Call it `CREATIVE_BRIEF` or `WRITING_GUIDE` or `AUTHOR_NOTES`. The variable name shapes how you write the content inside it. If the variable is called `SYSTEM_PROMPT`, you'll instinctively write orders. If it's called `CREATIVE_BRIEF`, you'll instinctively write like a human talking to another human.

## The 52 Observations Pattern

When we analyse a gold-standard example (like we did with the anatomy professor's transcript — 52 observations about what makes it exceptional), paste those observations into the prompt as-is. They read like analysis, like one writer talking to another about craft. Don't rewrite them as rules. "She never introduces a structure without placing it physically" produces better output than "YOU MUST place every structure physically before explaining function." The observation describes what great looks like. The rule describes what failure looks like. Always orient toward the positive example.

## Accuracy Constraints Are the Exception

Factual accuracy rules (verify via search, textbook wins on facts, correct misspellings, bold key terms on first use) stay firm and direct. These are contract terms, not style opinions. A brief section at the end of the creative brief with these constraints is fine. But even these should feel like "here are the non-negotiables we agreed on" not "YOU WILL BE PENALISED FOR FAILING TO COMPLY."

## Why This Matters

The quality difference is massive. A model reading a creative brief thinks like a writer. A model reading a list of orders thinks like a compliance checker. The first produces output with soul, rhythm, and judgment. The second produces output that technically follows every rule but feels dead. We want the first.