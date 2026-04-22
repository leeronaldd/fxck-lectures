@echo off
REM Deploy backend to GCP Cloud Run
cd /d "%~dp0\.."
SET PROJECT_ID=project-bc1fc31b-94c5-44b0-904
SET SERVICE_NAME=fxck-lectures-api
SET REGION=australia-southeast1
SET IMAGE=%REGION%-docker.pkg.dev/%PROJECT_ID%/fxck-lectures-api/backend

echo Building and pushing image (with layer caching)...
call gcloud builds submit --project=%PROJECT_ID% --tag=%IMAGE% --timeout=600s --gcs-log-dir=gs://fxck-lectures-screenshots/build-logs
if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED
    pause
    exit /b 1
)

echo Deploying to Cloud Run...
REM Read secrets from .env.deploy (not committed to git)
REM usebackq is required because the project path contains spaces
REM ("C:\Claude Projects\..."); without it, FOR /F interprets the quoted
REM path as a literal string to tokenise instead of a file to read, and
REM silently fails with "The system cannot find the file C:\Claude."
IF EXIST "%~dp0..\.env.deploy" (
    FOR /F "usebackq tokens=1,* delims==" %%A IN ("%~dp0..\.env.deploy") DO (
        IF "%%A"=="STRIPE_SECRET_KEY" SET STRIPE_KEY=%%B
        IF "%%A"=="STRIPE_WEBHOOK_SECRET" SET STRIPE_WH=%%B
        IF "%%A"=="STRIPE_PRICE_MAX_MONTHLY" SET MAX_M=%%B
        IF "%%A"=="STRIPE_PRICE_MAX_YEARLY" SET MAX_Y=%%B
        IF "%%A"=="STRIPE_PRICE_PRO_MONTHLY" SET PRO_M=%%B
        IF "%%A"=="STRIPE_PRICE_PRO_YEARLY" SET PRO_Y=%%B
        IF "%%A"=="SUPABASE_JWT_SECRET" SET SUPA_JWT=%%B
        IF "%%A"=="GROQ_API_KEY" SET GROQ_KEY=%%B
        IF "%%A"=="WHISPER_SERVICE_URL" SET WHISPER_URL=%%B
        IF "%%A"=="SUPABASE_SERVICE_KEY" SET SUPA_SERVICE=%%B
        IF "%%A"=="SUPABASE_ANON_KEY" SET SUPA_ANON=%%B
        IF "%%A"=="SENTRY_DSN" SET SENTRY_DSN_VAL=%%B
    )
)

REM Fall back to system env vars if not in .env.deploy
IF NOT DEFINED STRIPE_KEY IF DEFINED STRIPE_SECRET_KEY SET STRIPE_KEY=%STRIPE_SECRET_KEY%
IF NOT DEFINED STRIPE_WH IF DEFINED STRIPE_WEBHOOK_SECRET SET STRIPE_WH=%STRIPE_WEBHOOK_SECRET%
IF NOT DEFINED MAX_M IF DEFINED STRIPE_PRICE_MAX_MONTHLY SET MAX_M=%STRIPE_PRICE_MAX_MONTHLY%
IF NOT DEFINED MAX_Y IF DEFINED STRIPE_PRICE_MAX_YEARLY SET MAX_Y=%STRIPE_PRICE_MAX_YEARLY%
IF NOT DEFINED PRO_M IF DEFINED STRIPE_PRICE_PRO_MONTHLY SET PRO_M=%STRIPE_PRICE_PRO_MONTHLY%
IF NOT DEFINED PRO_Y IF DEFINED STRIPE_PRICE_PRO_YEARLY SET PRO_Y=%STRIPE_PRICE_PRO_YEARLY%
IF NOT DEFINED GROQ_KEY IF DEFINED GROQ_API_KEY SET GROQ_KEY=%GROQ_API_KEY%
IF NOT DEFINED SUPA_JWT IF DEFINED SUPABASE_JWT_SECRET SET SUPA_JWT=%SUPABASE_JWT_SECRET%
IF NOT DEFINED WHISPER_URL IF DEFINED WHISPER_SERVICE_URL SET WHISPER_URL=%WHISPER_SERVICE_URL%
IF NOT DEFINED SUPA_SERVICE IF DEFINED SUPABASE_SERVICE_KEY SET SUPA_SERVICE=%SUPABASE_SERVICE_KEY%
IF NOT DEFINED SUPA_ANON IF DEFINED SUPABASE_ANON_KEY SET SUPA_ANON=%SUPABASE_ANON_KEY%
IF NOT DEFINED SENTRY_DSN_VAL IF DEFINED SENTRY_DSN SET SENTRY_DSN_VAL=%SENTRY_DSN%

REM SUPABASE_ANON_KEY is mandatory — backend boots on os.environ["SUPABASE_ANON_KEY"].
IF NOT DEFINED SUPA_ANON (
    echo ERROR: SUPABASE_ANON_KEY not set. Add it to .env.deploy or export it before running deploy.bat.
    pause
    exit /b 1
)

REM Default to the deployed Whisper service if nothing is set
IF NOT DEFINED WHISPER_URL SET WHISPER_URL=https://fxck-lectures-whisper-2elcrqz4oa-as.a.run.app

SET ENV_VARS=GCP_PROJECT_ID=%PROJECT_ID%
SET ENV_VARS=%ENV_VARS%,GCS_SCREENSHOTS_BUCKET=fxck-lectures-screenshots
SET ENV_VARS=%ENV_VARS%,USE_SINGLE_WRITER=1
SET ENV_VARS=%ENV_VARS%,FRONTEND_URL=https://klareai.com
IF DEFINED STRIPE_KEY SET ENV_VARS=%ENV_VARS%,STRIPE_SECRET_KEY=%STRIPE_KEY%
IF DEFINED STRIPE_WH SET ENV_VARS=%ENV_VARS%,STRIPE_WEBHOOK_SECRET=%STRIPE_WH%
IF DEFINED MAX_M SET ENV_VARS=%ENV_VARS%,STRIPE_PRICE_MAX_MONTHLY=%MAX_M%
IF DEFINED MAX_Y SET ENV_VARS=%ENV_VARS%,STRIPE_PRICE_MAX_YEARLY=%MAX_Y%
IF DEFINED PRO_M SET ENV_VARS=%ENV_VARS%,STRIPE_PRICE_PRO_MONTHLY=%PRO_M%
IF DEFINED PRO_Y SET ENV_VARS=%ENV_VARS%,STRIPE_PRICE_PRO_YEARLY=%PRO_Y%
IF DEFINED SUPA_JWT SET ENV_VARS=%ENV_VARS%,SUPABASE_JWT_SECRET=%SUPA_JWT%
IF DEFINED GROQ_KEY SET ENV_VARS=%ENV_VARS%,GROQ_API_KEY=%GROQ_KEY%
IF DEFINED WHISPER_URL SET ENV_VARS=%ENV_VARS%,WHISPER_SERVICE_URL=%WHISPER_URL%
IF DEFINED SUPA_SERVICE SET ENV_VARS=%ENV_VARS%,SUPABASE_SERVICE_KEY=%SUPA_SERVICE%
SET ENV_VARS=%ENV_VARS%,SUPABASE_ANON_KEY=%SUPA_ANON%
IF DEFINED SENTRY_DSN_VAL SET ENV_VARS=%ENV_VARS%,SENTRY_DSN=%SENTRY_DSN_VAL%

REM concurrency=1 → each pipeline gets its own instance (no Vertex retry storms inside one process)
REM max-instances=50 → supports 50 concurrent users. Bumped from 20 on 2026-04-16.
REM   Idle instances cost $0 thanks to cpu-throttling, so raising the ceiling is
REM   pure headroom — Vertex quota becomes the real ceiling before Cloud Run does.
REM timeout=1800 → 30 min ceiling, well above the ~10 min worst-case pipeline run
REM cpu-throttling → CPU only billed during requests, idle instances cost $0. Warm-ping keeps instance alive for free.
call gcloud run deploy %SERVICE_NAME% --project=%PROJECT_ID% --image=%IMAGE% --region=%REGION% --platform=managed --allow-unauthenticated --use-http2 --memory=2Gi --cpu=4 --timeout=1800 --concurrency=1 --min-instances=0 --max-instances=50 --cpu-throttling --set-env-vars="%ENV_VARS%"

echo.
echo Done! Backend: https://%SERVICE_NAME%-211270844056.%REGION%.run.app
pause
