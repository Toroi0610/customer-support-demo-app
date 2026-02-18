# Hosting Design: Firebase Hosting + Cloud Run

Date: 2026-02-18

## Overview

Host the customer support demo app as a publicly accessible web application using:
- **Frontend**: Firebase Hosting (React SPA via CDN)
- **Backend**: Google Cloud Run (Python WebSocket proxy server)

## Architecture

```
[Browser]
  ├─ HTTPS ──→ Firebase Hosting (React SPA: dist/)
  └─ WSS ───→ Cloud Run (server.py)
                  └─ Gemini Live API (proxy)
```

## Backend Changes

The current `server.py` runs two separate ports:
- Port 8080: WebSocket server (websockets library)
- Port 8081: HTTP server for `/analyze-frame` (aiohttp)

Cloud Run exposes a single port, so both must be consolidated into one aiohttp application.

Changes:
- Replace `websockets.serve()` with aiohttp's `web.WebSocketResponse`
- Serve WebSocket and `/analyze-frame` from the same aiohttp app
- Bind to `PORT` environment variable (Cloud Run default: 8080)
- Add CORS headers to allow requests from the Firebase Hosting domain
- Add `Dockerfile` (Python 3.12-slim base image)

## Frontend Changes

Currently, URLs are hardcoded to `localhost`. These must be externalized via environment variables.

Changes:
- Add `VITE_WEBSOCKET_URL` environment variable (e.g., `wss://your-app.run.app`)
- Update `LiveAPIDemo.jsx` default WebSocket URL to use `VITE_WEBSOCKET_URL`
- Derive `analysisUrl` from the WebSocket URL host (`wss://xxx` → `https://xxx/analyze-frame`)
- Create `.env.example` to document required environment variables
- Local development continues to work via `.env.local` override

## Infrastructure

### GCP Resources

1. **Service Account**: For Cloud Run to authenticate to Gemini API
   - Role: `roles/aiplatform.user`
2. **Artifact Registry**: Store Docker images
3. **Cloud Run Service**: Run the containerized `server.py`
   - Environment variable: `GOOGLE_CLOUD_PROJECT`
4. **Firebase Hosting**: Serve the React SPA with SPA routing config

### Deployment

Manual deployment scripts (no CI/CD in scope):
- `deploy-backend.sh`: Build Docker image → push to Artifact Registry → deploy to Cloud Run
- `deploy-frontend.sh`: `npm run build` → `firebase deploy --only hosting`

## Cost Estimate

For demo-level traffic:
- Firebase Hosting: Free tier (10 GB storage, 10 GB/month transfer)
- Cloud Run: Free tier covers most usage; scales to zero when idle
- Estimated total: $0–$5/month

## Out of Scope

- CI/CD pipeline (GitHub Actions etc.)
- Authentication/authorization for demo viewers
- Custom domain setup
