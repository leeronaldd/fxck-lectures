# 2026-04-12 23:15 — Chunker Fix + V3 Architecture Direction

## What Changed

### Chunker fixes (permanent, general-purpose)
- **Mega-chunk splitting**: Chunks over 1,500 words auto-flagged for Flash topic-aware splitting. Catches thematic topic changes the regex multi-concept detector misses. Previously: 3,000w chunks buried 4+ topics (Lipid A, spirochetes, storage bodies all lost).
- **LLM sub-chunk limit**: 4,000 → 12,000 chars (same bug as Flash's 3,000-char limit from earlier session).
- **Merge threshold**: 200 → 100 words. Small but important topics (150w) no longer get absorbed into adjacent chunks.

### Generator fixes
- **Professor signal extraction**: Flash now extracts "don't worry about X" and "you need to know Y" from the transcript and passes them to Pro. Pro respects the professor's own depth cues.

### Lecture 3 results
Before fix: 5 major topics missing (Lipid A 0 mentions, Archaeal walls 0, Spirochetes 0, Storage bodies 0, Eukaryotic walls 0). 4 topics the professor said to skip were over-expanded (Autolysins 390w, Chemotaxis details 400w).

After fix: All 5 topics present. 24 sections generated, 10,459 words. Lipid A: 13 mentions. Spirochetes: own section. Storage bodies: 6 mentions. Professor signals guide depth allocation.

### Root cause analysis
The virus lecture (lecture 2) worked because the professor used explicit slide transitions — clean chunk boundaries. Lecture 3's professor rambles across topic boundaries without clear markers, creating mega-chunks that bury distinct topics. The fix is general-purpose and handles both styles.

## V3 Architecture Direction

The current V2 pipeline is transcript-driven: chunk transcript → generate slides + transcript per chunk. This creates problems:
- Repetition (overlapping chunks generate same content)
- Bad depth allocation (chunk size ≠ topic importance)
- Fragile chunking (professor's speech patterns drive structure)

### V3 proposal: Slide-driven architecture
Instead of transcript driving structure, slides drive structure:

```
1. Extract/group slides by topic → 8-12 topic groups
2. Flash writes a teaching plan (one call, sees ALL slides):
   "Slides 1-3: Cell wall architecture. Walk through diagram. 200w."
   "Slides 4-5: Penicillin mechanism. Hard part. Step-by-step. 500w."
   "Slide 6: Archaeal walls. Quick comparison. 3 sentences."
   "Slide 7: Quiz slide. Skip."
3. Pro executes plan per group: slides + transcript gaps + textbook
```

This replaces: chunker, EI scorer, depth nudge, bridge framing, repetition prevention — all of which are clunky approximations of what a human tutor does naturally.

### Why this works
- **Slides are the skeleton** — professor already organized content visually
- **Transcript fills gaps** — "what would confuse a student looking at these slides?"
- **No duplication** — transcript knows what's on the slide and doesn't repeat it
- **Flash as tutor-planner** — one call sees the whole lecture, makes judgment calls
- **Same API calls** — Flash planning + Pro generation, same as V2

### What already exists for V3
- `screenshot_extractor.py` — extracts slides from video
- Creative brief — stays the same
- Textbook search — stays the same
- `build_user_prompt` — needs rewrite to lead with slides
- Context caching — stays the same

## Files Modified
- `src/chunker.py` — mega-chunk split threshold, merge threshold, LLM sub-chunk limit
- `src/generator_v2.py` — professor signal extraction in Flash prefetch

## Git
- `d2b1ae9` — chunker + generator fixes
- Previous: `42b369b` — depth inversion system, `cacb173` — experimental snapshot
