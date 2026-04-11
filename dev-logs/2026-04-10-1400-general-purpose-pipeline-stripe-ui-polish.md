# Dev Log: 2026-04-10 — General-Purpose Pipeline, Stripe, Quiz Funnel, UI Polish

## What Changed

### Pipeline Generalization (Backend + Python)
- **Removed all hardcoded virology** from chunker, concept grouper, generator, and fact checker
- **New `src/textbook_search.py`**: 89 keyword entries across 12 OpenStax textbooks (microbiology, anatomy, biology, chemistry, psychology, pharmacology, nursing x4, nutrition, psychiatric, population health). Multi-tier lookup: keyword match → Flash LLM pick → NCBI Bookshelf API → graceful skip
- **`src/fact_checker.py`**: Replaced hardcoded 35-URL dict with dynamic textbook search. Now logs which textbook sources were used. Saves verification reports as `{claims: [...], textbook_sources: [...]}`
- **`src/chunker.py`**: Expanded SEED_TERMS from ~150 to 265 (added biochemistry, immunology, genetics, neuroscience, endocrinology). 18 new topic patterns
- **`src/concept_grouper.py`**: Replaced hardcoded virology deterministic grouper with content-aware version using Jaccard similarity on key_terms
- **`src/generator.py`**: Added `set_student_context(program, year)` — year-based knowledge calibration (1st yr = build from scratch, 4th yr = clinical focus)
- **`backend/app/pipeline.py`**: Switched to LLM grouper with deterministic fallback, added transcript guard (<100 words rejection), fetches user profile from Supabase to pass to generator

### Quiz Onboarding Funnel
- **`frontend/src/app/quiz/page.tsx`** (NEW): 4-question quiz (program, year, frustration, referral) with fade transitions, auto-advance, progress bar
- Saves to localStorage → synced to Supabase `user_profiles` table on sign-in via AuthProvider
- Landing page CTA now routes to `/quiz` instead of `/signin`

### Settings Page
- **`frontend/src/app/settings/page.tsx`** (NEW): 5 tabs — Account, Billing, Usage, Privacy, Customization
- Account: avatar color picker, display name, email (read-only)
- Billing: Free vs Pro cards, Monthly/Yearly segmented toggle, Stripe checkout integration
- AUD pricing: $12.99/mo or $69.99/yr ($5.83/mo equivalent)
- Customization: editable quiz answers

### Stripe Integration
- **Backend**: `POST /api/checkout` creates Stripe Checkout session, redirects to hosted payment page
- Stripe secret key read from `.env.deploy` (gitignored), passed as env var during Cloud Run deploy
- **Frontend**: `createCheckoutSession()` API call, billing tab with plan selector
- **NOT YET DONE**: Webhook to update user plan in Supabase after payment

### Session Management
- **Rename**: Pencil icon on hover + double-click shortcut, inline input
- **Delete**: Confirmation with "Delete / Cancel" inline buttons
- Backend: `PATCH /api/sessions/{id}` (rename), `DELETE /api/sessions/{id}`
- **Supabase**: Needs update policy for sessions (SQL not yet run)

### UI Polish
- **Flash fix**: AppShell shows spinner during auth loading instead of flashing signin page
- **New Session**: Navigate first, reset after 100ms delay to prevent "No lecture loaded" flash
- **Reader**: Increased max-width from 820px → 1200px for wider reading
- **Removed**: Microsoft sign-in, "Powered by Gemini 3.1 Pro" badge, "Learn More" menu item, model selector dropdown
- **TrustBar**: Hides entirely when no verification data instead of showing "No verification data"
- **Landing page**: Sample preview section with browser mockup showing Baltimore Classification output with all 7 virus classes
- **Upload page**: Enhanced as dashboard with "Welcome back" greeting and recent sessions

### Auth Fixes
- Gmail dot normalization (`lee.wang.hong0215` = `leewanghong0215`)
- JWT email extraction: checks `payload.email`, `user_metadata.email`, `app_metadata.email`
- `FREE_USAGE_LIMIT` bumped to 2, `CUSTOM_LIMITS` dict for per-user limits
- Quiz profile sync on sign-in via AuthProvider

### Deploy Infrastructure
- `backend/deploy.bat`: Reads Stripe key from `.env.deploy`, passes as `--set-env-vars`
- Round logo created for Instagram (`logo-round.svg`, `logo-round.png`)

## What's Working
- Quiz funnel → signin → upload → processing → reader flow
- Session rename/delete (needs Supabase policy for rename)
- Settings page with all tabs
- Landing page with sample preview
- General-purpose textbook search (tested locally)
- Auth persistence with loading guard

## What's Broken / Pending

### CRITICAL: CORS Error on Production
- **Symptom**: All uploads fail on `fxck-lectures.vercel.app` — browser gets CORS error
- **Root cause**: Last `gcloud run services update` to add env vars created a new revision from the OLD container image (which didn't have correct CORS origins)
- **Fix**: Run `backend\deploy.bat` — this does a full image build + deploy with env vars in one command
- **User must run this manually** (Cloud Run deploy requires local gcloud auth)

### Other Pending
1. **Supabase SQL**: Run `CREATE POLICY "Users update own sessions" ON public.sessions FOR UPDATE USING (auth.uid() = user_id);`
2. **Stripe webhook**: Need to handle `checkout.session.completed` to update user plan in Supabase so Pro users get 15 lectures
3. **Mobile .mov upload**: Fails on phone — likely Cloud Run file size limit or missing MIME type
4. **Vercel production branch**: Should change from `style-transfer-v1` (deleted) to `master` in Vercel dashboard settings

## Files Modified (This Session)

| Area | Files |
|------|-------|
| Pipeline | `src/textbook_search.py` (NEW), `src/fact_checker.py`, `src/chunker.py`, `src/concept_grouper.py`, `src/generator.py`, `src/completeness_checker.py` |
| Backend | `backend/app/main.py`, `backend/app/pipeline.py`, `backend/app/auth.py`, `backend/requirements.txt`, `backend/deploy.bat`, `backend/supabase_setup.sql` |
| Frontend | `frontend/src/app/quiz/page.tsx` (NEW), `frontend/src/app/settings/page.tsx` (NEW), `frontend/src/app/page.tsx`, `frontend/src/app/signin/page.tsx`, `frontend/src/app/upload/page.tsx`, `frontend/src/app/reader/page.tsx` |
| Components | `AppShell.tsx`, `AppSidebar.tsx`, `TrustBar.tsx`, `AuthProvider.tsx` |
| Lib | `api.ts`, `store.ts`, `data.ts` |
| Config | `.env.deploy` (NEW, gitignored) |
| Assets | `frontend/public/brand/logo-round.svg`, `logo-round.png` |

## Next Session Priorities
1. **Run `backend\deploy.bat`** to fix CORS (blocker for everything)
2. Run Supabase SQL for session update policy
3. Stripe webhook for plan upgrades
4. Test end-to-end on production after deploy
5. Mobile upload fix (.mov support)
