#!/bin/bash
# Deploy backend to GCP Cloud Run
# Run from project root: bash backend/deploy.sh

PROJECT_ID="project-bc1fc31b-94c5-44b0-904"
SERVICE_NAME="fxck-lectures-api"
REGION="australia-southeast1"  # closest to Griffith Uni
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/fxck-lectures-api/backend"

# Build and push to Artifact Registry
gcloud builds submit \
  --project "$PROJECT_ID" \
  --tag "$IMAGE" \
  --timeout=600s

# Deploy to Cloud Run
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --use-http2 \
  --memory 2Gi \
  --cpu 4 \
  --timeout 900 \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET,GCP_PROJECT_ID=$PROJECT_ID,GROQ_API_KEY=$GROQ_API_KEY,WHISPER_SERVICE_URL=$WHISPER_SERVICE_URL"

echo ""
echo "Deployed! URL should be: https://$SERVICE_NAME-211270844056.$REGION.run.app"
