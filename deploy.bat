@echo off
REM ============================================
REM  Deploy everything: Whisper STT + Backend
REM  Run from project root (double-click)
REM ============================================
cd /d "%~dp0"

SET PROJECT_ID=project-bc1fc31b-94c5-44b0-904
SET WHISPER_REGION=asia-southeast1
SET BACKEND_REGION=australia-southeast1

REM ── Read secrets from .env.deploy ──
IF EXIST ".env.deploy" (
    FOR /F "tokens=1,* delims==" %%A IN (.env.deploy) DO (
        IF "%%A"=="STRIPE_SECRET_KEY" SET STRIPE_KEY=%%B
        IF "%%A"=="SUPABASE_JWT_SECRET" SET SUPA_JWT=%%B
        IF "%%A"=="GROQ_API_KEY" SET GROQ_KEY=%%B
    )
)
IF NOT DEFINED STRIPE_KEY IF DEFINED STRIPE_SECRET_KEY SET STRIPE_KEY=%STRIPE_SECRET_KEY%
IF NOT DEFINED GROQ_KEY IF DEFINED GROQ_API_KEY SET GROQ_KEY=%GROQ_API_KEY%
IF NOT DEFINED SUPA_JWT IF DEFINED SUPABASE_JWT_SECRET SET SUPA_JWT=%SUPABASE_JWT_SECRET%

REM ── Push frontend to Vercel ──
echo.
echo === FRONTEND (Vercel) ===
call git push origin master
echo Frontend pushed. Remember to promote to production on Vercel.
echo.

REM ============================================
REM  Step 1: Deploy Whisper STT service (GPU)
REM ============================================
echo.
echo ========================================
echo  Step 1/2: Deploying Whisper STT (GPU)
echo ========================================
echo.

SET WHISPER_IMAGE=%WHISPER_REGION%-docker.pkg.dev/%PROJECT_ID%/fxck-lectures-api/whisper

REM Create Artifact Registry in asia-southeast1 if needed
call gcloud artifacts repositories describe fxck-lectures-api --project %PROJECT_ID% --location %WHISPER_REGION% >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Creating Artifact Registry in %WHISPER_REGION%...
    call gcloud artifacts repositories create fxck-lectures-api --project %PROJECT_ID% --location %WHISPER_REGION% --repository-format docker
)

echo Building Whisper image (first time is slow ~5 min)...
call gcloud builds submit --project %PROJECT_ID% --tag %WHISPER_IMAGE% --timeout=1200s --region %WHISPER_REGION% whisper-service/
IF %ERRORLEVEL% NEQ 0 (
    echo WHISPER BUILD FAILED
    pause
    exit /b 1
)

echo Deploying Whisper to Cloud Run with GPU...
call gcloud run deploy fxck-lectures-whisper --project %PROJECT_ID% --image %WHISPER_IMAGE% --region %WHISPER_REGION% --platform managed --no-allow-unauthenticated --gpu 1 --gpu-type nvidia-l4 --cpu 4 --memory 16Gi --timeout 900 --concurrency 1 --min-instances 0 --max-instances 10 --execution-environment gen2
IF %ERRORLEVEL% NEQ 0 (
    echo WHISPER DEPLOY FAILED - You may need to request GPU quota first.
    pause
    exit /b 1
)

REM Get the Whisper service URL
FOR /F "tokens=*" %%U IN ('gcloud run services describe fxck-lectures-whisper --project %PROJECT_ID% --region %WHISPER_REGION% --format "value(status.url)"') DO SET WHISPER_URL=%%U
echo Whisper deployed at: %WHISPER_URL%

REM ============================================
REM  Step 2: Deploy Backend API
REM ============================================
echo.
echo ========================================
echo  Step 2/2: Deploying Backend API
echo ========================================
echo.

SET BACKEND_IMAGE=%BACKEND_REGION%-docker.pkg.dev/%PROJECT_ID%/fxck-lectures-api/backend

echo Building backend image...
call gcloud builds submit --project %PROJECT_ID% --tag %BACKEND_IMAGE% --timeout=600s
IF %ERRORLEVEL% NEQ 0 (
    echo BACKEND BUILD FAILED
    pause
    exit /b 1
)

SET ENV_VARS=GCP_PROJECT_ID=%PROJECT_ID%,WHISPER_SERVICE_URL=%WHISPER_URL%
IF DEFINED STRIPE_KEY SET ENV_VARS=%ENV_VARS%,STRIPE_SECRET_KEY=%STRIPE_KEY%
IF DEFINED SUPA_JWT SET ENV_VARS=%ENV_VARS%,SUPABASE_JWT_SECRET=%SUPA_JWT%
IF DEFINED GROQ_KEY SET ENV_VARS=%ENV_VARS%,GROQ_API_KEY=%GROQ_KEY%

echo Deploying backend to Cloud Run...
call gcloud run deploy fxck-lectures-api --project %PROJECT_ID% --image %BACKEND_IMAGE% --region %BACKEND_REGION% --platform managed --allow-unauthenticated --use-http2 --memory 2Gi --cpu 4 --timeout 900 --concurrency 1 --min-instances 0 --max-instances 100 --set-env-vars "%ENV_VARS%"
IF %ERRORLEVEL% NEQ 0 (
    echo BACKEND DEPLOY FAILED
    pause
    exit /b 1
)

echo.
echo ========================================
echo  All deployed!
echo ========================================
echo  Whisper: %WHISPER_URL%
echo  Backend: https://fxck-lectures-api-211270844056.%BACKEND_REGION%.run.app
echo  Frontend: https://fxck-lectures.vercel.app (promote to production)
echo ========================================
pause
