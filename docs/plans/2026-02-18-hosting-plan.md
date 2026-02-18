# Hosting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy the app publicly using Firebase Hosting (frontend) + Cloud Run (backend).

**Architecture:** The Python backend is refactored from 2-port to single-port aiohttp so Cloud Run can expose it. The frontend reads the backend URL from a Vite environment variable. Two shell scripts handle manual deployment.

**Tech Stack:** aiohttp (WebSocket + HTTP unified), Docker, Cloud Run, Firebase Hosting, Vite env vars

---

## Prerequisites (manual, before starting)

Run these once before starting the tasks:

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Log into Firebase
firebase login

# Log into gcloud (if not already)
gcloud auth login
gcloud auth application-default login

# Set your GCP project
gcloud config set project YOUR_PROJECT_ID
```

---

### Task 1: Refactor server.py to single-port aiohttp

Cloud Run exposes only one port. Currently server.py uses port 8080 (WebSocket via `websockets` library) and port 8081 (HTTP via aiohttp). We unify both under aiohttp using its built-in WebSocket support.

**Files:**
- Modify: `server.py`

**Step 1: Add `AiohttpWSAdapter` class and `ws_handler` after the imports block (after line 24)**

Replace the entire `server.py` with the following. The key changes are:
- Add `import aiohttp` at top (already partially imported inline)
- Add `AiohttpWSAdapter` class (adapts aiohttp WS to websockets-compatible interface)
- Add `ws_handler(request)` aiohttp route handler
- Replace `start_websocket_server()` + `start_http_server()` with single `start_server()`
- Read port from `PORT` env var (Cloud Run requirement)

```python
#!/usr/bin/env python3
"""
WebSocket Proxy Server for Gemini Live API
Handles authentication and proxies WebSocket connections.

This server acts as a bridge between the browser client and Gemini API,
handling Google Cloud authentication automatically using default credentials.
"""

import asyncio
import websockets
import aiohttp
import json
import ssl
import certifi
import os
import base64
from aiohttp import web
from websockets.legacy.protocol import WebSocketCommonProtocol
from websockets.exceptions import ConnectionClosed

# Google auth imports
import google.auth
from google.auth.transport.requests import Request

DEBUG = False  # Set to True for verbose logging
PORT = int(os.environ.get("PORT", 8080))


def generate_access_token():
    """Retrieves an access token using Google Cloud default credentials."""
    try:
        creds, _ = google.auth.default()
        if not creds.valid:
            creds.refresh(Request())
        return creds.token
    except Exception as e:
        print(f"Error generating access token: {e}")
        print("Make sure you're logged in with: gcloud auth application-default login")
        return None


class AiohttpWSAdapter:
    """Adapts aiohttp WebSocketResponse to mimic the websockets library interface."""

    def __init__(self, ws: web.WebSocketResponse):
        self._ws = ws

    @property
    def closed(self):
        return self._ws.closed

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._ws.receive()
        if msg.type in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
            return msg.data
        raise StopAsyncIteration

    async def recv(self):
        msg = await self._ws.receive()
        if msg.type in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
            return msg.data
        raise ConnectionClosed(None, None)

    async def send(self, data):
        if isinstance(data, (bytes, bytearray)):
            await self._ws.send_bytes(data)
        else:
            await self._ws.send_str(data)

    async def close(self, code=1000, reason=""):
        if not self._ws.closed:
            await self._ws.close(
                code=code, message=reason.encode() if reason else b""
            )


async def proxy_task(
    source_websocket,
    destination_websocket,
    is_server: bool,
) -> None:
    """Forwards messages from source_websocket to destination_websocket."""
    try:
        async for message in source_websocket:
            try:
                data = json.loads(message)
                if DEBUG:
                    print(f"Proxying from {'server' if is_server else 'client'}: {data}")
                await destination_websocket.send(json.dumps(data))
            except Exception as e:
                print(f"Error processing message: {e}")
    except ConnectionClosed as e:
        print(
            f"{'Server' if is_server else 'Client'} connection closed: {e.code} - {e.reason}"
        )
    except Exception as e:
        print(f"Unexpected error in proxy_task: {e}")
    finally:
        await destination_websocket.close()


async def create_proxy(client_websocket, bearer_token: str, service_url: str) -> None:
    """Establishes a WebSocket connection to Gemini and creates bidirectional proxy."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    print(f"Connecting to Gemini API...")
    if DEBUG:
        print(f"Service URL: {service_url}")

    try:
        async with websockets.connect(
            service_url,
            additional_headers=headers,
            ssl=ssl_context
        ) as server_websocket:
            print(f"✅ Connected to Gemini API")

            client_to_server_task = asyncio.create_task(
                proxy_task(client_websocket, server_websocket, is_server=False)
            )
            server_to_client_task = asyncio.create_task(
                proxy_task(server_websocket, client_websocket, is_server=True)
            )

            done, pending = await asyncio.wait(
                [client_to_server_task, server_to_client_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            try:
                await server_websocket.close()
            except Exception:
                pass

            try:
                await client_websocket.close()
            except Exception:
                pass

    except ConnectionClosed as e:
        print(f"Server connection closed unexpectedly: {e.code} - {e.reason}")
        if not client_websocket.closed:
            await client_websocket.close(code=e.code, reason=e.reason)
    except Exception as e:
        print(f"Failed to connect to Gemini API: {e}")
        if not client_websocket.closed:
            await client_websocket.close(code=1008, reason="Upstream connection failed")


async def handle_websocket_client(client_websocket) -> None:
    """Handles a new WebSocket client connection."""
    print("🔌 New WebSocket client connection...")
    try:
        service_setup_message = await asyncio.wait_for(
            client_websocket.recv(), timeout=10.0
        )
        service_setup_message_data = json.loads(service_setup_message)

        bearer_token = service_setup_message_data.get("bearer_token")
        service_url = service_setup_message_data.get("service_url")

        if not bearer_token:
            print("🔑 Generating access token using default credentials...")
            bearer_token = generate_access_token()
            if not bearer_token:
                print("❌ Failed to generate access token")
                await client_websocket.close(code=1008, reason="Authentication failed")
                return
            print("✅ Access token generated")

        if not service_url:
            print("❌ Error: Service URL is missing")
            await client_websocket.close(code=1008, reason="Service URL is required")
            return

        await create_proxy(client_websocket, bearer_token, service_url)

    except asyncio.TimeoutError:
        print("⏱️ Timeout waiting for the first message from the client")
        await client_websocket.close(code=1008, reason="Timeout")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in first message: {e}")
        await client_websocket.close(code=1008, reason="Invalid JSON")
    except Exception as e:
        print(f"❌ Error handling client: {e}")
        if not client_websocket.closed:
            await client_websocket.close(code=1011, reason="Internal error")


# ─── aiohttp Route Handlers ───────────────────────────────────────────────────

async def ws_handler(request):
    """aiohttp WebSocket upgrade handler — replaces websockets.serve()."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    adapter = AiohttpWSAdapter(ws)
    await handle_websocket_client(adapter)
    return ws


ANALYSIS_SYSTEM_INSTRUCTION = """You are a video analysis assistant monitoring a user through their camera.
Analyze the image and respond with ONLY a valid JSON object (no markdown, no code blocks).

Provide:
1. "observation": A brief description in Japanese of what you see (the user's state, expression, posture, actions, surroundings)
2. "status_key": A short consistent key for the current state (e.g., "smiling", "tired", "away", "working", "eating", "talking", "reading")
3. "significant_change": Compare the current status_key with the previous status_key provided.
   - Set to true ONLY if the status represents a meaningful change worth mentioning
   - Set to false if the status is essentially the same
   - For the first frame (no previous status), set to false
4. "emotion": The user's detected emotion in Japanese (e.g., "笑顔", "真剣", "疲れている", "困っている", "楽しそう", "不在")
5. "details": Comma-separated list of notable items or changes in Japanese

Focus on changes that a caring friend would notice and comment on."""


async def handle_analyze_frame(request):
    """HTTP endpoint for analyzing a single video frame."""
    cors_origin = os.environ.get("CORS_ORIGIN", "*")
    headers = {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    if request.method == "OPTIONS":
        return web.Response(headers=headers)

    try:
        data = await request.json()
        image_base64 = data.get("image")
        previous_status = data.get("previous_status", "")
        project_id = data.get("project_id", "")
        model = data.get("model", "gemini-2.0-flash")

        if not image_base64:
            return web.json_response(
                {"error": "No image provided"}, status=400, headers=headers
            )

        if not project_id:
            return web.json_response(
                {"error": "No project_id provided"}, status=400, headers=headers
            )

        token = generate_access_token()
        if not token:
            return web.json_response(
                {"error": "Authentication failed"}, status=500, headers=headers
            )

        if previous_status:
            user_prompt = f"Analyze this image. Previous status_key was: '{previous_status}'. Compare with current state."
        else:
            user_prompt = "Analyze this image. This is the first frame being analyzed."

        api_url = (
            f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/us-central1/publishers/google/models/{model}:generateContent"
        )

        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": image_base64,
                            }
                        },
                        {"text": user_prompt},
                    ],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": ANALYSIS_SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                json=request_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                ssl=ssl_context,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"Gemini API error: {resp.status} - {error_text}")
                    return web.json_response(
                        {"error": f"Gemini API error: {resp.status}"},
                        status=500,
                        headers=headers,
                    )

                result = await resp.json()

        try:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"]
            analysis = json.loads(text_response)
            return web.json_response(analysis, headers=headers)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Raw response: {result}")
            return web.json_response(
                {"error": "Failed to parse analysis response"},
                status=500,
                headers=headers,
            )

    except Exception as e:
        print(f"Error in analyze_frame: {e}")
        return web.json_response({"error": str(e)}, status=500, headers=headers)


async def main():
    print(f"""
╔════════════════════════════════════════════════════════════╗
║     Gemini Live API Proxy Server                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  🔌 WebSocket Proxy: ws://localhost:{PORT:<5}                   ║
║  🔍 Frame Analysis:  http://localhost:{PORT}/analyze-frame  ║
║                                                            ║
║  Authentication:                                           ║
║  • Uses Google Cloud default credentials                  ║
║  • Run: gcloud auth application-default login             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")

    app = web.Application()
    app.router.add_get("/ws", ws_handler)
    app.router.add_post("/analyze-frame", handle_analyze_frame)
    app.router.add_options("/analyze-frame", handle_analyze_frame)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Server running on port {PORT}")

    await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
```

**Step 2: Verify server starts locally**

```bash
source env/bin/activate && python server.py &
sleep 2
curl -s http://localhost:8080/analyze-frame -X OPTIONS -o /dev/null -w "%{http_code}"
# Expected: 200
kill %1
```

**Step 3: Run existing tests to confirm nothing is broken**

```bash
npm test
# Expected: 19 passed
```

**Step 4: Commit**

```bash
git add server.py
git commit -m "refactor: consolidate server.py to single aiohttp port for Cloud Run"
```

---

### Task 2: Create Dockerfile

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "server.py"]
```

**Step 2: Create `.dockerignore`**

```
env/
node_modules/
dist/
__pycache__/
*.pyc
.git/
src/
public/
docs/
*.md
package*.json
vite.config.js
index.html
```

**Step 3: Test Docker build locally**

```bash
docker build -t gemini-proxy .
# Expected: Successfully built ...
```

**Step 4: Test Docker run locally (requires gcloud ADC)**

```bash
docker run --rm -p 8080:8080 \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  gemini-proxy &
sleep 2
curl -s http://localhost:8080/analyze-frame -X OPTIONS -o /dev/null -w "%{http_code}"
# Expected: 200
docker stop $(docker ps -q --filter ancestor=gemini-proxy)
```

**Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Dockerfile for Cloud Run deployment"
```

---

### Task 3: Externalize frontend URLs via environment variables

Currently `ws://localhost:8080` and `http://localhost:8081/analyze-frame` are hardcoded. We move them to Vite env vars.

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx` (lines 34, 549)
- Modify: `src/utils/user-monitor.js` (line 21)
- Create: `.env.example`
- Create: `.env.local` (gitignored, for local dev)

**Step 1: Update `LiveAPIDemo.jsx` line 34 — default proxyUrl**

Find:
```js
localStorage.getItem("proxyUrl") || "ws://localhost:8080"
```
Replace with:
```js
localStorage.getItem("proxyUrl") || import.meta.env.VITE_WEBSOCKET_URL || "ws://localhost:8080"
```

**Step 2: Update `LiveAPIDemo.jsx` line 549 — analysisUrl passed to UserStateMonitor**

Find:
```js
analysisUrl: "http://localhost:8081/analyze-frame",
```

The analysis URL lives on the same host as the WebSocket server. Derive it from `proxyUrl`:

```js
analysisUrl: (() => {
  const wsUrl = proxyUrl || import.meta.env.VITE_WEBSOCKET_URL || "ws://localhost:8080";
  const httpBase = wsUrl.replace(/^ws(s?):\/\//, "http$1://").replace(/\/ws$/, "");
  return `${httpBase}/analyze-frame`;
})(),
```

**Step 3: Update `src/utils/user-monitor.js` line 21 — remove hardcoded fallback**

Find:
```js
this.analysisUrl = options.analysisUrl || "http://localhost:8081/analyze-frame";
```
Replace with:
```js
this.analysisUrl = options.analysisUrl || "http://localhost:8080/analyze-frame";
```
(Fallback now uses port 8080 since server is unified; `analysisUrl` will be passed from LiveAPIDemo.jsx in production.)

**Step 4: Create `.env.example`**

```bash
# Copy to .env.local for local development, or set in CI/CD for production builds
# WebSocket proxy URL — set to your Cloud Run service URL for production
# VITE_WEBSOCKET_URL=wss://your-service-xxxxx-uc.a.run.app/ws
```

**Step 5: Create `.env.local` for local development**

```bash
# Local development — use local server
VITE_WEBSOCKET_URL=ws://localhost:8080/ws
```

**Step 6: Ensure `.env.local` is gitignored**

```bash
grep -q ".env.local" .gitignore || echo ".env.local" >> .gitignore
```

**Step 7: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 8: Commit**

```bash
git add src/components/LiveAPIDemo.jsx src/utils/user-monitor.js .env.example .gitignore
git commit -m "feat: externalize backend URLs via VITE_WEBSOCKET_URL env var"
```

---

### Task 4: Create Firebase Hosting configuration

**Files:**
- Create: `firebase.json`
- Create: `.firebaserc`

**Step 1: Initialize Firebase (interactive)**

```bash
firebase init hosting
```

When prompted:
- "Which Firebase project?" → select your GCP project
- "Public directory?" → `dist`
- "Configure as single-page app?" → `Yes`
- "Set up automatic builds with GitHub?" → `No`

This creates `firebase.json` and `.firebaserc`.

**Step 2: Verify `firebase.json` looks like this**

```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

**Step 3: Commit**

```bash
git add firebase.json .firebaserc
git commit -m "feat: add Firebase Hosting configuration"
```

---

### Task 5: Create Cloud Run deployment script

**Files:**
- Create: `deploy-backend.sh`

**Step 1: Create `deploy-backend.sh`**

```bash
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
docker build -t "${IMAGE}" .

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
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},CORS_ORIGIN=${CORS_ORIGIN}" \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 3600

echo ""
echo "✅ Backend deployed!"
echo "   Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --format "value(status.url)"
```

**Step 2: Make executable**

```bash
chmod +x deploy-backend.sh
```

**Step 3: Commit**

```bash
git add deploy-backend.sh
git commit -m "feat: add Cloud Run deployment script"
```

---

### Task 6: Create Firebase Hosting deployment script

**Files:**
- Create: `deploy-frontend.sh`

**Step 1: Create `deploy-frontend.sh`**

```bash
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
```

**Step 2: Make executable**

```bash
chmod +x deploy-frontend.sh
```

**Step 3: Commit**

```bash
git add deploy-frontend.sh
git commit -m "feat: add Firebase Hosting deployment script"
```

---

### Task 7: First full deployment

**Step 1: Create GCP service account for Cloud Run**

```bash
PROJECT_ID=$(gcloud config get-value project)
gcloud iam service-accounts create gemini-proxy-sa \
  --display-name "Gemini Proxy Service Account"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:gemini-proxy-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role "roles/aiplatform.user"
```

**Step 2: Enable required APIs**

```bash
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  aiplatform.googleapis.com
```

**Step 3: Configure Docker for GCR**

```bash
gcloud auth configure-docker
```

**Step 4: Deploy backend**

```bash
./deploy-backend.sh
```

Note the output Service URL (e.g., `https://gemini-proxy-xxxxx-uc.a.run.app`).

**Step 5: Update CORS_ORIGIN after first deploy**

After the frontend is deployed in Step 7, you'll know the Firebase Hosting URL (e.g., `https://your-project.web.app`). Re-deploy backend with exact origin:

```bash
CORS_ORIGIN="https://your-project.web.app" ./deploy-backend.sh
```

**Step 6: Deploy frontend**

```bash
./deploy-frontend.sh
```

**Step 7: Smoke test**

Open the Firebase Hosting URL in a browser. Verify:
- [ ] App loads without errors
- [ ] Can connect to the WebSocket proxy
- [ ] Camera/audio session starts successfully

**Step 8: Final commit**

```bash
git add -A
git commit -m "chore: verify deployment — app live on Firebase Hosting + Cloud Run"
```
