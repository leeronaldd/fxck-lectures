@echo off
REM Deploy backend to GCP Cloud Run
cd /d "%~dp0\.."
SET PROJECT_ID=project-bc1fc31b-94c5-44b0-904
SET SERVICE_NAME=fxck-lectures-api
SET REGION=australia-southeast1
SET IMAGE=%REGION%-docker.pkg.dev/%PROJECT_ID%/fxck-lectures-api/backend

echo Building and pushing image...
call gcloud builds submit --project %PROJECT_ID% --tag %IMAGE% --timeout=600s
if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED
    pause
    exit /b 1
)

echo Deploying to Cloud Run...
REM Read secrets from .env.deploy (not committed to git)
IF EXIST "%~dp0..\.env.deploy" (
    FOR /F "tokens=1,* delims==" %%A IN (%~dp0..\.env.deploy) DO (
        IF "%%A"=="STRIPE_SECRET_KEY" SET STRIPE_KEY=%%B
        IF "%%A"=="SUPABASE_JWT_SECRET" SET SUPA_JWT=%%B
        IF "%%A"=="GROQ_API_KEY" SET GROQ_KEY=%%B
    )
)

REM Fall back to system env vars if not in .env.deploy
IF NOT DEFINED STRIPE_KEY IF DEFINED STRIPE_SECRET_KEY SET STRIPE_KEY=%STRIPE_SECRET_KEY%
IF NOT DEFINED GROQ_KEY IF DEFINED GROQ_API_KEY SET GROQ_KEY=%GROQ_API_KEY%
IF NOT DEFINED SUPA_JWT IF DEFINED SUPABASE_JWT_SECRET SET SUPA_JWT=%SUPABASE_JWT_SECRET%

SET ENV_VARS=GCP_PROJECT_ID=%PROJECT_ID%
IF DEFINED STRIPE_KEY SET ENV_VARS=%ENV_VARS%,STRIPE_SECRET_KEY=%STRIPE_KEY%
IF DEFINED SUPA_JWT SET ENV_VARS=%ENV_VARS%,SUPABASE_JWT_SECRET=%SUPA_JWT%
IF DEFINED GROQ_KEY SET ENV_VARS=%ENV_VARS%,GROQ_API_KEY=%GROQ_KEY%

call gcloud run deploy %SERVICE_NAME% --project %PROJECT_ID% --image %IMAGE% --region %REGION% --platform managed --allow-unauthenticated --use-http2 --memory 2Gi --timeout 900 --concurrency 1 --min-instances 0 --max-instances 3 --set-env-vars "%ENV_VARS%"

echo.
echo Done! Backend: https://%SERVICE_NAME%-211270844056.%REGION%.run.app
pause
