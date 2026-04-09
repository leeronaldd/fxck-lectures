@echo off
REM Deploy everything — run from project root: deploy.bat
SET PROJECT_ID=project-bc1fc31b-94c5-44b0-904
SET SERVICE_NAME=fxck-lectures-api
SET REGION=australia-southeast1
SET IMAGE=%REGION%-docker.pkg.dev/%PROJECT_ID%/fxck-lectures-api/backend

echo === FRONTEND (Vercel) ===
call git push origin master
if %ERRORLEVEL% NEQ 0 (
    echo Git push failed
    exit /b 1
)
echo Frontend pushed. Remember to promote to production on Vercel.
echo.

echo === BACKEND (Cloud Run) ===
echo Building image...
call gcloud builds submit --project %PROJECT_ID% --tag %IMAGE% --timeout=600s
if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED
    exit /b 1
)

echo Deploying to Cloud Run...
call gcloud run deploy %SERVICE_NAME% --project %PROJECT_ID% --image %IMAGE% --region %REGION% --platform managed --allow-unauthenticated --memory 2Gi --timeout 900 --concurrency 1 --min-instances 0 --max-instances 3

echo.
echo === ALL DONE ===
echo Frontend: https://fxck-lectures.vercel.app (promote to production on Vercel)
echo Backend:  https://%SERVICE_NAME%-211270844056.%REGION%.run.app
