#!/bin/bash
set -e

# ── Configuration ──────────────────────────────────────────────────────────────
# Get Cloud Run service URL (used as the WebSocket backend)
REGION="asia-northeast1"
SERVICE_NAME="gemini-proxy"
PROJECT_ID=$(gcloud config get-value project)

echo "🔍 Fetching Cloud Run service URL..."
CLOUD_RUN_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format "value(status.url)" 2>/dev/null || echo "")

if [ -z "${CLOUD_RUN_URL}" ]; then
  echo "❌ Could not find Cloud Run service '${SERVICE_NAME}'."
  echo "   Deploy the backend first: ./deploy-backend.sh"
  exit 1
fi

WS_URL=$(echo "${CLOUD_RUN_URL}" | sed 's|https://|wss://|')/ws
echo "   WebSocket URL: ${WS_URL}"

# ── Build ──────────────────────────────────────────────────────────────────────
echo ""
echo "🏗️  Building frontend..."
VITE_WEBSOCKET_URL="${WS_URL}" npm run build

# ── Deploy ────────────────────────────────────────────────────────────────────
echo ""
echo "🚀 Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo ""
echo "✅ Frontend deployed!"
