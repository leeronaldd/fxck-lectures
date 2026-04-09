@echo off
REM Deploy backend to GCP Cloud Run — run from project root: deploy.bat
SET PROJECT_ID=project-bc1fc31b-94c5-44b0-904
SET SERVICE_NAME=fxck-lectures-api
SET REGION=australia-southeast1
SET IMAGE=%REGION%-docker.pkg.dev/%PROJECT_ID%/fxck-lectures-api/backend

echo Building and pushing image...
gcloud builds submit --project %PROJECT_ID% --tag %IMAGE% --timeout=600s
if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED
    exit /b 1
)

echo Deploying to Cloud Run...
gcloud run deploy %SERVICE_NAME% --project %PROJECT_ID% --image %IMAGE% --region %REGION% --platform managed --allow-unauthenticated --memory 2Gi --timeout 900 --concurrency 1 --min-instances 0 --max-instances 3 --set-env-vars "SUPABASE_JWT_SECRET=%SUPABASE_JWT_SECRET%,GCP_PROJECT_ID=%PROJECT_ID%,GROQ_API_KEY=%GROQ_API_KEY%"

echo.
echo Done! Backend: https://%SERVICE_NAME%-211270844056.%REGION%.run.app
