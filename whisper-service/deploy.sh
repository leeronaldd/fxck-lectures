#!/bin/bash
# Deploy Whisper STT service to Cloud Run with GPU
# Run from project root: bash whisper-service/deploy.sh

PROJECT_ID="project-bc1fc31b-94c5-44b0-904"
SERVICE_NAME="fxck-lectures-whisper"
REGION="asia-southeast1"  # Closest GPU region to Australia
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/fxck-lectures-api/whisper"

# Create Artifact Registry repo in asia-southeast1 if it doesn't exist
gcloud artifacts repositories describe fxck-lectures-api \
  --project "$PROJECT_ID" \
  --location "$REGION" 2>/dev/null || \
gcloud artifacts repositories create fxck-lectures-api \
  --project "$PROJECT_ID" \
  --location "$REGION" \
  --repository-format docker

# Build and push (longer timeout — image is ~5GB with model weights)
gcloud builds submit \
  --project "$PROJECT_ID" \
  --tag "$IMAGE" \
  --timeout=1200s \
  --region "$REGION" \
  whisper-service/

# Deploy to Cloud Run with GPU
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --no-allow-unauthenticated \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --cpu 4 \
  --memory 16Gi \
  --timeout 900 \
  --concurrency 1 \
  --min-instances 0 \
  --max-instances 2 \
  --execution-environment gen2 \
  --service-account "$(gcloud iam service-accounts list --project $PROJECT_ID --format='value(email)' --filter='displayName:Default compute service account' | head -1)"

WHISPER_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format 'value(status.url)')

echo ""
echo "Whisper service deployed at: $WHISPER_URL"
echo ""
echo "Set this in backend deploy:"
echo "  WHISPER_SERVICE_URL=$WHISPER_URL"
