# Dev Log — 2026-04-08 11:00 — Supabase Auth + FastAPI Backend + Cloud Run Deploy

## What Changed

### Frontend (Supabase Auth)
- Installed `@supabase/supabase-js` + `@supabase/ssr`
- Created `frontend/src/lib/supabase.ts` — browser client factory
- Created `frontend/src/components/AuthProvider.tsx` — initializes session, listens to `onAuthStateChange`, updates Zustand store
- Created `frontend/src/lib/api.ts` — authenticated fetch wrapper for backend API calls
- Modified `frontend/src/lib/store.ts`:
  - Replaced mock `signIn`/`signOut` with `setUser`/`clearUser`/`setAuthLoading`
  - Added `id` to `UserState`
  - Replaced mock pipeline timers with real API calls (upload → process → poll status)
  - Added `pipelineError` state
- Modified `frontend/src/app/signin/page.tsx`:
  - Real Supabase calls: `signInWithPassword`, `signUp`, `signInWithOtp`, `signInWithOAuth`
  - Google + Microsoft OAuth (removed Apple)
  - Error/success message display
- Modified `frontend/src/app/layout.tsx` — wrapped AppShell with AuthProvider
- Modified `frontend/src/components/AppShell.tsx` — route protection (guests can access `/`, protected: `/processing`, `/reader`)
- Modified `frontend/src/app/page.tsx` — "Transform Lecture" redirects guests to `/signin`
- Modified `frontend/src/components/AppSidebar.tsx` — real sign-out via `supabase.auth.signOut()`
- Modified `frontend/src/app/processing/page.tsx` — shows pipeline errors + "Try Again" button

### Backend (FastAPI)
- Created `backend/app/main.py` — FastAPI with CORS, endpoints: upload, process, status, sessions
- Created `backend/app/auth.py` — Supabase JWT verification via `python-jose`
- Created `backend/app/models.py` — Pydantic schemas
- Created `backend/app/pipeline.py` — background thread runner wrapping existing `src/` modules
- Created `backend/requirements.txt` — deps (removed `supabase` package due to httpx conflict with `google-genai`)

### Deploy
- Created `Dockerfile` at project root
- Created `.dockerignore` + `.gcloudignore` to keep builds small
- Created `backend/deploy.sh` for Cloud Run deployment
- Backend deployed to Cloud Run: `fxck-lectures-api-211270844056.australia-southeast1.run.app`
- Frontend deployed to Vercel: `fxck-lectures.vercel.app`

### Infrastructure Setup
- Google OAuth configured in GCP Console + Supabase
- GCP APIs enabled: Cloud Run, Cloud Build, Container Registry, Storage, Artifact Registry
- Artifact Registry repo created in `australia-southeast1`
- Service account permissions: storage.admin, artifactregistry.writer, logging.logWriter, run.admin, iam.serviceAccountUser
- GitHub repo made public (required for Vercel Hobby plan auto-deploy)
- Git email updated to `leewanghong0215@gmail.com` for Vercel committer matching

## What Works
- Google OAuth sign-in — user shows as "Ron Lee" with correct email
- Guest mode — upload page accessible without sign-in, "Transform Lecture" redirects to sign-in
- Route protection — `/processing` and `/reader` redirect to `/signin` when not logged in
- Sidebar shows real user name/email, sign-out works
- Cloud Run backend boots and responds to health checks and CORS preflight
- Frontend auto-deploys on push to `style-transfer-v1` branch

## What's Broken / Needs Fixing

### Pipeline stuck on "Chunking transcript"
- Upload OPTIONS preflight returns 200 from Cloud Run
- But no POST follows — likely CORS issue or frontend error swallowed
- Need to check: browser console errors during upload, Cloud Run logs for POST requests
- The `cancelPipeline` / "Try Again" flow may not reset state correctly

### Supabase redirect URL
- After Google OAuth, Supabase was redirecting to wrong project (printing whale)
- User needs to set **Site URL** to `https://fxck-lectures.vercel.app` in Supabase Dashboard > Auth > URL Configuration
- Also add redirect URLs: `https://fxck-lectures.vercel.app`, `http://localhost:3000`

### User modified UI files
- User made styling changes to `page.tsx`, `signin/page.tsx`, `processing/page.tsx`, `AppShell.tsx`, `AppSidebar.tsx` (glassmorphism, gradient text, animations, feature cards)
- These changes haven't been committed yet

## What to Try Next
1. Fix the pipeline: check browser network tab for failed API calls, check Cloud Run logs for errors
2. Verify Supabase Site URL is set correctly
3. Test end-to-end: upload transcript → pipeline runs → reader shows output
4. Add the `SUPABASE_JWT_SECRET` env var to Cloud Run if not already set (check with `gcloud run services describe`)
5. Commit user's UI styling changes

## Deploy Commands (for reference)

### Backend (Cloud Run)
```cmd
gcloud builds submit --project project-bc1fc31b-94c5-44b0-904 --tag australia-southeast1-docker.pkg.dev/project-bc1fc31b-94c5-44b0-904/fxck-lectures-api/backend --timeout=600s

gcloud run deploy fxck-lectures-api --project project-bc1fc31b-94c5-44b0-904 --image australia-southeast1-docker.pkg.dev/project-bc1fc31b-94c5-44b0-904/fxck-lectures-api/backend --region australia-southeast1 --platform managed --allow-unauthenticated --memory 2Gi --timeout 900
```

### Frontend (Vercel)
Auto-deploys on push to `style-transfer-v1` branch. Or manual:
```cmd
cd "C:\Claude Projects\Fxck Professors"
npx vercel --prod --yes
```

## Stack
| Service | Purpose | URL |
|---------|---------|-----|
| Vercel | Frontend hosting | fxck-lectures.vercel.app |
| GCP Cloud Run | Backend API | fxck-lectures-api-211270844056.australia-southeast1.run.app |
| GCP Vertex AI | LLM (Gemini Pro/Flash) | via google-genai SDK |
| Supabase | Auth + DB | husdhmaijvughqezlmjt.supabase.co |
| Groq | STT (Whisper) | via groq SDK |
