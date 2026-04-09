# Dev Log — 2026-04-09 11:00 — Full UI Audit, Video Upload, Sessions & Usage Limits

## What Changed

### UI Audit — Fixed all broken/non-functional buttons
- **Settings button** (sidebar): now opens SettingsModal (was built but never wired)
- **Learn More** (sidebar): navigates to /#how-it-works
- **Upgrade Plan** (sidebar): shows "coming soon" toast
- **Forgot password?** (signin): calls Supabase `resetPasswordForEmail()`
- **TrustBar**: shows actual verification stats with color-coded dot (was hardcoded "Sources verified")
- **Reader empty state**: shows "No lecture loaded" + upload CTA instead of blank page
- **Sidebar empty state**: shows "No sessions yet" instead of blank list
- **Fake sessions removed**: Virology/Immunology/Anatomy mock data gone

### Progress Bar Bugs Fixed
- **283% overall progress**: `subProgress` (backend's 0-100%) was used directly as percentage — `Math.min` cap was there but sub-progress display wasn't capped
- **35/8 sub-progress**: generation stage showed `subProgress/subTotal` = `35/8` — removed X/Y counter, replaced with simple progress bar
- **"Chunking" stuck during upload**: stage 0 was marked "running" immediately, before upload finished. Now shows "Uploading..." with progress bar, pipeline stages only appear after upload completes

### Video Upload Support
- Backend `pipeline.py`: added video transcription branch (mp4/mkv/avi/mov/webm)
- Uses existing `src/transcriber.py` (Groq Whisper) — extracts audio via ffmpeg, transcribes, then chunks
- Frontend: dynamic pipeline stages — text uploads show 8 stages (no "Transcribing"), video uploads show 9 stages
- Tested with 30-second clip: full pipeline works end-to-end

### Landing Page Redesign (user-driven)
- Home page (`/`) is now a pure marketing page — "Fxck Lectures" headline, no upload zone, no AppShell
- New `/upload` route for authenticated users with the upload zone
- Sign-in redirects to `/upload`, sidebar "New Session" goes to `/upload`
- AppShell bypasses landing page (like signin)

### Klare Logo Integration
- SVG logo (`frontend/public/brand/logo-full-dark.svg`) — orange K mark + "Klare" wordmark
- Replaced text "Klare" in landing page header, AppShell header, signin header

### TOCSidebar Removed
- User requested removal — Contents sidebar no longer renders on reader page

### Usage Limits
- Backend checks `usage` table in Supabase before running pipeline
- 1 free run per user, unlimited for `lee.wang.hong0215@gmail.com` and `lee.pak.wai0706@gmail.com`
- Returns 403 with "You've used your free lecture. Upgrade for unlimited access."
- Frontend handles 403 and shows error message

### Session Persistence
- Backend saves pipeline output to Supabase `sessions` table after completion
- New endpoints: `GET /api/sessions` (list), `GET /api/sessions/{id}` (full data)
- Frontend fetches sessions on login, displays in sidebar with name + date
- Clicking a session loads its markdown into the reader
- Sessions refresh after pipeline completes
- Session naming: uses original filename (not UUID) — fixed mid-session

### Deploy Infrastructure
- `deploy.bat` (root): pushes frontend + builds/deploys backend in one command
- `backend\deploy.bat`: backend-only deploy
- Fixed `gcr.io` → Artifact Registry (gcr.io deprecated)
- Fixed `call` keyword in .bat files (CMD was exiting after first gcloud command)
- Supabase SQL setup script: `backend/supabase_setup.sql`

## What Works
- Full pipeline: upload .txt or .mp4 → transcribe (video) → chunk → score → group → generate → verify → assemble → reader
- Google OAuth sign-in
- Session persistence (sidebar shows past sessions, clickable to load)
- Usage limits (1 free, unlimited for whitelisted emails)
- Video transcription via Groq Whisper
- Logo, empty states, all sidebar buttons functional
- Upload progress shown on processing page

## What's Still Broken / Needs Work
1. **Generator produces content from near-empty transcripts** — 30-sec silent video generated full virology lecture. Need minimum transcript length check
2. **Vercel production branch**: still deploys master as "Preview", must manually promote each time. No way to change on Hobby plan since `style-transfer-v1` was the original production branch (now deleted)
3. **Backend deploy**: Claude can't run gcloud from bash (auth doesn't carry over). User must run `backend\deploy.bat` manually
4. **Settings not sent to backend**: pipeline toggles (skipCI, skipVerify, etc.) are stored in Zustand but never passed to the API
5. **No session deletion**: sessions accumulate, no way to delete from UI

## Deploy Commands
```cmd
# Full deploy (frontend + backend)
deploy.bat

# Backend only
backend\deploy.bat

# If gcloud auth expired
gcloud auth login
```

## Supabase Tables Created
- `public.usage` — tracks pipeline runs per user (id, user_id, email, created_at)
- `public.sessions` — stores pipeline outputs (id, user_id, name, markdown, concept_groups, verification_report, created_at)
- RLS policies: users read own sessions, service role full access on usage

## Files Changed (this session)
```
backend/app/main.py          — usage limits, session save/fetch endpoints, original filename tracking
backend/app/pipeline.py      — video transcription branch
backend/deploy.bat            — new Windows CMD deploy script
backend/deploy.sh             — fixed Artifact Registry URL
backend/supabase_setup.sql    — usage + sessions table DDL
deploy.bat                    — root deploy script (frontend + backend)
frontend/src/app/page.tsx     — landing page redesign (user), logo
frontend/src/app/upload/page.tsx — new upload page for authenticated users
frontend/src/app/processing/page.tsx — upload progress bar, dynamic header text
frontend/src/app/reader/page.tsx — removed TOCSidebar, added empty state
frontend/src/app/signin/page.tsx — forgot password handler, logo, redirect to /upload
frontend/src/components/AppShell.tsx — logo, bypass landing page, /upload protected
frontend/src/components/AppSidebar.tsx — settings wired, learn more, upgrade plan, session loading, empty state
frontend/src/components/AuthProvider.tsx — load sessions on login
frontend/src/components/PipelineStepper.tsx — fixed 283% bug, removed X/Y counter
frontend/src/components/TrustBar.tsx — dynamic stats with color-coded dot
frontend/src/lib/api.ts — fetchSessions, fetchSession, 403 handling
frontend/src/lib/store.ts — dynamic stages, loadSessions, loadSession
```
