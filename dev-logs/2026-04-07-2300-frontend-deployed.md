# Dev Log: 2026-04-07 — Frontend Built & Deployed

## What Changed

### Frontend built from scratch (Next.js 16 + Tailwind v4)
- **Phase 1: Static Reader** — renders v4 pipeline output as a reading experience
  - Rich markdown with inline slide images, click-to-zoom lightbox
  - Exam alert detection (yellow callout boxes for exam-relevant paragraphs)
  - Skip line rendering for low-CI% sections
  - Trust bar showing verification status
  - Dark mode with orange (#FF6B35) accent

- **Phase 2: Upload + Processing flow**
  - Upload page: drag-drop for lecture video (.mp4, primary) or transcript (.txt, secondary)
  - Processing screen: 9-stage pipeline stepper with weighted progress bar
  - Mock backend: simulates pipeline over ~7 seconds, loads existing v4 files as output
  - Auto-redirect: processing → reader when complete

- **App Shell (Claude-inspired)**
  - Collapsible sidebar with session history + "+ New Session" button
  - Account menu (bottom-left): Settings, Learn More, Upgrade Plan, Log Out
  - Top bar: hamburger toggle, "Klare" logo, model selector, "Sign In" button
  - Reader page auto-collapses app sidebar

- **Sign-In page (Leibniz-inspired)**
  - Tabs: Sign In | Sign Up | Magic Link
  - OAuth: Google, Microsoft, Apple buttons (mocked)
  - Email + password form
  - Magic Link tab: email-only (no OAuth, no password)

### Branding
- Company: **Klare**
- Product: **Fxck Lectures**
- Tagline: "Replace a 2 hour lecture with a 15 minute read"
- CTA: "Transform Lecture" (not "Generate Replacement")
- Skip lines: "Background context, low exam priority" (not "Professor rambled")
- Trust bar: "Sources verified against textbooks" (not raw claim counts)

### Deployment
- GitHub repo: `leeronaldd/fxck-lectures` (private)
- Vercel: auto-deploys from `style-transfer-v1` branch
- Live URL: https://fxck-lectures.vercel.app/
- Supabase project: `husdhmaijvughqezlmjt` (Fxck Lectures, Asia-Pacific)

## Tech Stack
- Next.js 16.2.2 + React 19 + Tailwind CSS v4
- Zustand for state management
- react-markdown + rehype-slug + remark-gfm for rendering
- Supabase (configured, not yet wired for real auth)
- Vercel (frontend hosting)

## What's Mocked (needs real implementation)
- Auth: clicking OAuth/email sets fake user in Zustand (needs Supabase Auth)
- Pipeline: simulates 9 stages with setTimeout (needs FastAPI on GCP Cloud Run)
- Sessions: 3 hardcoded mock sessions (needs Supabase database)
- File upload: stores File object in memory (needs Supabase Storage or backend upload)

## What to Do Next
1. **Real Supabase Auth** — wire up Google/Microsoft/Apple OAuth + email/password
2. **FastAPI backend** — wrap run_stage2.py as API, deploy to GCP Cloud Run
3. **Real pipeline connection** — upload triggers actual transcription + generation
4. **Session persistence** — save/load lectures from Supabase database
5. **Get sister's feedback** on reading experience with real lecture output

## Files Created
```
frontend/
  src/app/page.tsx              # Upload page (home)
  src/app/reader/page.tsx       # Document reader
  src/app/processing/page.tsx   # Pipeline progress
  src/app/signin/page.tsx       # Auth page
  src/app/layout.tsx            # Root layout with AppShell
  src/app/globals.css           # Design tokens + typography
  src/components/AppShell.tsx    # Global top bar + sidebar wrapper
  src/components/AppSidebar.tsx  # Session list + account menu
  src/components/UploadZone.tsx  # Drag-drop file upload
  src/components/PipelineStepper.tsx  # 9-stage progress display
  src/components/MarkdownRenderer.tsx # Custom markdown with lightbox
  src/components/TrustBar.tsx    # Bottom trust indicator
  src/components/SettingsModal.tsx # Pipeline settings (unused now)
  src/components/TOCSidebar.tsx  # Table of contents (unused now)
  src/lib/store.ts              # Zustand state (user, pipeline, files)
  src/lib/types.ts              # TypeScript interfaces
  src/lib/data.ts               # Data fetching helpers
  .env.local                    # Supabase credentials (gitignored)
```

## Competitor Research Summary
Researched: TurboLearn, Studley, Knowt, NotebookLM, Mindgrasp, Quizlet, Gamma, Napkin AI.
Key differentiator: competitors produce flashcards/quizzes (fragmented). Klare produces one long-form document (book-like reading experience). Pipeline transparency (9-stage progress) is unique trust signal.
