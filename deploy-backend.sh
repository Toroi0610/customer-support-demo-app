#!/bin/bash
set -e

# ── Configuration ──────────────────────────────────────────────────────────────
PROJECT_ID=$(gcloud config get-value project)
REGION="asia-northeast1"
SERVICE_NAME="gemini-proxy"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
CORS_ORIGIN="${CORS_ORIGIN:-*}"  # Override with your Firebase Hosting URL after first deploy

echo "🚀 Deploying backend to Cloud Run..."
echo "   Project:  ${PROJECT_ID}"
echo "   Region:   ${REGION}"
echo "   Service:  ${SERVICE_NAME}"

# ── Build & Push ───────────────────────────────────────────────────────────────
echo ""
echo "📦 Building Docker image..."
docker build --platform linux/amd64 -t "${IMAGE}" .

echo ""
echo "⬆️  Pushing to Container Registry..."
docker push "${IMAGE}"

# ── Deploy to Cloud Run ────────────────────────────────────────────────────────
echo ""
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},CORS_ORIGIN=${CORS_ORIGIN},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-},ALLOWED_EMAILS=${ALLOWED_EMAILS:-}" \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 3600

echo ""
echo "✅ Backend deployed!"
echo "   Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format "value(status.url)"
