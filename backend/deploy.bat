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
REM Read Stripe key from .env.deploy (not committed to git)
IF EXIST "%~dp0..\.env.deploy" (
    FOR /F "tokens=1,2 delims==" %%A IN (%~dp0..\.env.deploy) DO (
        IF "%%A"=="STRIPE_SECRET_KEY" SET STRIPE_KEY=%%B
    )
)
IF DEFINED STRIPE_KEY (
    call gcloud run deploy %SERVICE_NAME% --project %PROJECT_ID% --image %IMAGE% --region %REGION% --platform managed --allow-unauthenticated --memory 2Gi --timeout 900 --concurrency 1 --min-instances 0 --max-instances 3 --set-env-vars "STRIPE_SECRET_KEY=%STRIPE_KEY%"
) ELSE (
    call gcloud run deploy %SERVICE_NAME% --project %PROJECT_ID% --image %IMAGE% --region %REGION% --platform managed --allow-unauthenticated --memory 2Gi --timeout 900 --concurrency 1 --min-instances 0 --max-instances 3
)

echo.
echo Done! Backend: https://%SERVICE_NAME%-211270844056.%REGION%.run.app
pause
