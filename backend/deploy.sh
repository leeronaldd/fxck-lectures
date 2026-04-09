#!/bin/bash
# Deploy backend to GCP Cloud Run
# Run from project root: bash backend/deploy.sh


PROJECT_ID="project-bc1fc31b-94c5-44b0-904"
SERVICE_NAME="fxck-lectures-api"
REGION="australia-southeast1"  # closest to Griffith Uni

# Build and push to Artifact Registry
gcloud builds submit \
  --project "$PROJECT_ID" \
  --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --timeout=600s

# Deploy to Cloud Run
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 900 \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET,GCP_PROJECT_ID=$PROJECT_ID,GROQ_API_KEY=$GROQ_API_KEY"

echo ""
echo "Deployed! Update NEXT_PUBLIC_API_URL in Vercel env vars with the URL above."
