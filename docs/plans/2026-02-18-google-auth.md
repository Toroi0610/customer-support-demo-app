# Google Authentication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restrict app access to specific approved Google accounts using Google Identity Services (frontend) and google-auth token verification (backend).

**Architecture:** Frontend shows Google Sign-In overlay when not logged in. Google ID token is included in the WebSocket setup message and HTTP Authorization header. Backend verifies the token with `google.oauth2.id_token` and checks the email against an `ALLOWED_EMAILS` environment variable.

**Tech Stack:** Google Identity Services (JS), google-auth (Python, already installed), aiohttp, React

---

## Prerequisites (manual, before starting)

1. **Create OAuth 2.0 Client ID** in Google Cloud Console:
   - Go to: APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web application**
   - Authorized JavaScript origins:
     - `https://anima-mvp-feac4.web.app`
     - `http://localhost:5173` (for local dev)
   - Copy the generated Client ID (format: `xxx.apps.googleusercontent.com`)

2. **Note your Client ID** — you'll need it for Tasks 4 and 5.

---

### Task 1: Add token verification to server.py

**Files:**
- Modify: `server.py`

**Step 1: Add imports and env vars at the top (after existing imports)**

Find:
```python
DEBUG = False  # Set to True for verbose logging
PORT = int(os.environ.get("PORT", 8080))
```

Replace with:
```python
DEBUG = False  # Set to True for verbose logging
PORT = int(os.environ.get("PORT", 8080))

# Authentication
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
ALLOWED_EMAILS_RAW = os.environ.get("ALLOWED_EMAILS", "")
ALLOWED_EMAILS = set(e.strip() for e in ALLOWED_EMAILS_RAW.split(",") if e.strip())
```

**Step 2: Add `verify_google_token` helper after `generate_access_token`**

After the `generate_access_token` function, add:
```python
def verify_google_token(token_string: str) -> bool:
    """Verifies a Google ID token and checks the email against the allowlist."""
    if not GOOGLE_CLIENT_ID:
        print("⚠️  GOOGLE_CLIENT_ID not set — skipping auth (dev mode)")
        return True
    if not ALLOWED_EMAILS:
        print("⚠️  ALLOWED_EMAILS not set — skipping auth (dev mode)")
        return True
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as grequests
        idinfo = google_id_token.verify_oauth2_token(
            token_string,
            grequests.Request(),
            GOOGLE_CLIENT_ID,
        )
        email = idinfo.get("email", "")
        if email not in ALLOWED_EMAILS:
            print(f"🚫 Access denied for email: {email}")
            return False
        print(f"✅ Access granted for email: {email}")
        return True
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        return False
```

**Step 3: Update `handle_websocket_client` to accept prefetched setup data**

Find:
```python
async def handle_websocket_client(client_websocket) -> None:
    """Handles a new WebSocket client connection."""
    print("🔌 New WebSocket client connection...")
    try:
        service_setup_message = await asyncio.wait_for(
            client_websocket.recv(), timeout=10.0
        )
        service_setup_message_data = json.loads(service_setup_message)
```

Replace with:
```python
async def handle_websocket_client(client_websocket, prefetched_setup: dict = None) -> None:
    """Handles a new WebSocket client connection."""
    print("🔌 New WebSocket client connection...")
    try:
        if prefetched_setup is not None:
            service_setup_message_data = prefetched_setup
        else:
            service_setup_message = await asyncio.wait_for(
                client_websocket.recv(), timeout=10.0
            )
            service_setup_message_data = json.loads(service_setup_message)
```

**Step 4: Update `ws_handler` to verify token before proxying**

Find:
```python
async def ws_handler(request):
    """aiohttp WebSocket upgrade handler — replaces websockets.serve()."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    adapter = AiohttpWSAdapter(ws)
    await handle_websocket_client(adapter)
    return ws
```

Replace with:
```python
async def ws_handler(request):
    """aiohttp WebSocket upgrade handler — replaces websockets.serve()."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Read first message to verify auth before proxying
    try:
        msg = await asyncio.wait_for(ws.receive(), timeout=10.0)
    except asyncio.TimeoutError:
        await ws.close(code=1008, message=b"Timeout waiting for setup message")
        return ws

    if msg.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
        await ws.close(code=1008, message=b"Expected text message")
        return ws

    try:
        setup_data = json.loads(msg.data)
    except json.JSONDecodeError:
        await ws.close(code=1008, message=b"Invalid JSON")
        return ws

    id_token = setup_data.get("id_token", "")
    if not verify_google_token(id_token):
        await ws.close(code=4001, message=b"Unauthorized")
        return ws

    adapter = AiohttpWSAdapter(ws)
    await handle_websocket_client(adapter, prefetched_setup=setup_data)
    return ws
```

**Step 5: Add auth check to `handle_analyze_frame`**

Find:
```python
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
```

Replace with:
```python
async def handle_analyze_frame(request):
    """HTTP endpoint for analyzing a single video frame."""
    cors_origin = os.environ.get("CORS_ORIGIN", "*")
    headers = {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

    if request.method == "OPTIONS":
        return web.Response(headers=headers)

    # Verify Google ID token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        id_token = auth_header[7:]
        if not verify_google_token(id_token):
            return web.json_response({"error": "Unauthorized"}, status=401, headers=headers)
    elif GOOGLE_CLIENT_ID and ALLOWED_EMAILS:
        # Auth is configured but no token provided
        return web.json_response({"error": "Unauthorized"}, status=401, headers=headers)

    try:
        data = await request.json()
```

**Step 6: Start server locally and verify OPTIONS still returns 200**

```bash
source env/bin/activate && python server.py &
sleep 2
curl -s http://localhost:8080/analyze-frame -X OPTIONS -o /dev/null -w "%{http_code}"
kill %1 2>/dev/null; wait %1 2>/dev/null
# Expected: 200
```

**Step 7: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 8: Commit**

```bash
git add server.py
git commit -m "feat: add Google ID token verification to server.py"
```

---

### Task 2: Pass ID token through GeminiLiveAPI

**Files:**
- Modify: `src/utils/gemini-api.js`

**Step 1: Add `idToken` property to GeminiLiveAPI constructor**

Find (in constructor):
```js
    this.previousImage = null;
    this.totalBytesSent = 0;
```

Replace with:
```js
    this.idToken = null;
    this.previousImage = null;
    this.totalBytesSent = 0;
```

**Step 2: Include `id_token` in `sendInitialSetupMessages`**

Find:
```js
  sendInitialSetupMessages() {
    const serviceSetupMessage = {
      service_url: this.serviceUrl,
    };
    this.sendMessage(serviceSetupMessage);
```

Replace with:
```js
  sendInitialSetupMessages() {
    const serviceSetupMessage = {
      service_url: this.serviceUrl,
      ...(this.idToken && { id_token: this.idToken }),
    };
    this.sendMessage(serviceSetupMessage);
```

**Step 3: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 4: Commit**

```bash
git add src/utils/gemini-api.js
git commit -m "feat: include id_token in WebSocket setup message"
```

---

### Task 3: Pass ID token through UserStateMonitor

**Files:**
- Modify: `src/utils/user-monitor.js`

**Step 1: Add `idToken` option to constructor**

Find:
```js
    this.analysisUrl = options.analysisUrl || "http://localhost:8080/analyze-frame";
    this.projectId = options.projectId || "";
```

Replace with:
```js
    this.analysisUrl = options.analysisUrl || "http://localhost:8080/analyze-frame";
    this.idToken = options.idToken || null;
    this.projectId = options.projectId || "";
```

**Step 2: Add Authorization header to fetch call**

Find:
```js
      // Send to analysis endpoint
      const response = await fetch(this.analysisUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
```

Replace with:
```js
      // Send to analysis endpoint
      const authHeaders = { "Content-Type": "application/json" };
      if (this.idToken) {
        authHeaders["Authorization"] = `Bearer ${this.idToken}`;
      }
      const response = await fetch(this.analysisUrl, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
```

**Step 3: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 4: Commit**

```bash
git add src/utils/user-monitor.js
git commit -m "feat: pass Authorization header in UserStateMonitor fetch"
```

---

### Task 4: Add Google Sign-In to frontend

**Files:**
- Modify: `index.html`
- Modify: `src/components/LiveAPIDemo.jsx`
- Modify: `.env.example`
- Modify: `.env.local`

**Step 1: Update `index.html` — add Google Identity Services script and update title**

Find:
```html
    <title>カスタマーサポート デモアプリ</title>
  </head>
```

Replace with:
```html
    <title>AI パートナー</title>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
  </head>
```

**Step 2: Add `idToken` and `authError` state to LiveAPIDemo.jsx**

After:
```js
    // Connection State
    const [connected, setConnected] = useState(false);
    const [setupJson, setSetupJson] = useState(null);
```

Add:
```js
    // Auth State
    const [idToken, setIdToken] = useState(null);
    const [authError, setAuthError] = useState(null);
```

**Step 3: Add Google Sign-In initialization useEffect**

After the model `useEffect` (around line 54), add:
```js
    // Initialize Google Sign-In
    useEffect(() => {
      const initGoogleSignIn = () => {
        if (!window.google) return;
        window.google.accounts.id.initialize({
          client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
          callback: (response) => {
            setIdToken(response.credential);
            setAuthError(null);
          },
        });
        if (!idToken) {
          window.google.accounts.id.renderButton(
            document.getElementById("google-signin-button"),
            { theme: "outline", size: "large", locale: "ja" }
          );
        }
      };

      // Google script may not be loaded yet — poll until ready
      if (window.google) {
        initGoogleSignIn();
      } else {
        const interval = setInterval(() => {
          if (window.google) {
            clearInterval(interval);
            initGoogleSignIn();
          }
        }, 100);
        return () => clearInterval(interval);
      }
    }, [idToken]);
```

**Step 4: Add Sign-In overlay — render it when not logged in**

Find (in the return statement, the outer wrapper):
```jsx
    return (
      <div className="live-api-demo">
        <div className="toolbar">
```

Replace with:
```jsx
    // Show sign-in overlay if not authenticated
    if (!idToken) {
      return (
        <div className="signin-overlay">
          <div className="signin-card">
            <h1>AI パートナー</h1>
            <p className="signin-subtitle">Gemini Live API 搭載</p>
            <p className="signin-description">Googleアカウントでログインしてご利用ください</p>
            <div id="google-signin-button"></div>
            {authError && <p className="signin-error">{authError}</p>}
          </div>
        </div>
      );
    }

    return (
      <div className="live-api-demo">
        <div className="toolbar">
```

**Step 5: Pass `idToken` to `GeminiLiveAPI` in connect()**

Find:
```js
        clientRef.current = new GeminiLiveAPI(proxyUrl, projectId, model);

        clientRef.current.systemInstructions = systemInstructions;
```

Replace with:
```js
        clientRef.current = new GeminiLiveAPI(proxyUrl, projectId, model);

        clientRef.current.idToken = idToken;
        clientRef.current.systemInstructions = systemInstructions;
```

**Step 6: Pass `idToken` to `UserStateMonitor` in the monitor creation block**

Find:
```js
        const monitor = new UserStateMonitor({
          analysisUrl: (() => {
```

Add `idToken` to the options object. After `analysisUrl`:
```js
        const monitor = new UserStateMonitor({
          analysisUrl: (() => {
            const wsUrl = proxyUrl || import.meta.env.VITE_WEBSOCKET_URL || "ws://localhost:8080";
            const httpBase = wsUrl.replace(/^ws(s?):\/\//, "http$1://").replace(/\/ws$/, "");
            return `${httpBase}/analyze-frame`;
          })(),
          idToken: idToken,
```

Note: Find the exact `new UserStateMonitor({` block and add `idToken: idToken,` after the `analysisUrl` property.

**Step 7: Add Sign-In overlay CSS to LiveAPIDemo.css**

At the end of the file, add:
```css
/* Sign-In Overlay */
.signin-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8f9fa 0%, #e8f0fe 100%);
}

.signin-card {
  background: white;
  border-radius: 16px;
  padding: 48px 40px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  max-width: 400px;
  width: 90%;
}

.signin-card h1 {
  font-size: 1.8rem;
  color: #202124;
  margin: 0 0 4px;
  font-weight: 500;
}

.signin-subtitle {
  font-size: 0.85rem;
  color: #5f6368;
  margin: 0 0 24px;
}

.signin-description {
  color: #3c4043;
  margin-bottom: 28px;
  font-size: 0.95rem;
}

#google-signin-button {
  display: flex;
  justify-content: center;
}

.signin-error {
  color: #d93025;
  font-size: 0.85rem;
  margin-top: 16px;
}
```

**Step 8: Update `.env.example`**

Add to `.env.example`:
```bash
# Google OAuth Client ID — required for authentication
# VITE_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
```

**Step 9: Update `.env.local`**

Add to `.env.local`:
```bash
VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
```
(Replace `YOUR_CLIENT_ID_HERE` with the actual Client ID from Prerequisites)

**Step 10: Run tests**

```bash
npm test
# Expected: 19 passed
```

**Step 11: Commit**

```bash
git add index.html src/components/LiveAPIDemo.jsx src/utils/user-monitor.js src/components/LiveAPIDemo.css .env.example
git commit -m "feat: add Google Sign-In overlay and pass id_token to backend"
```

---

### Task 5: Deploy with auth enabled

**Step 1: Redeploy backend with auth env vars**

```bash
CORS_ORIGIN="https://anima-mvp-feac4.web.app" \
  GOOGLE_CLIENT_ID="YOUR_CLIENT_ID.apps.googleusercontent.com" \
  ALLOWED_EMAILS="your@gmail.com" \
  ./deploy-backend.sh
```

(Replace values with your actual Client ID and allowed email addresses)

**Step 2: Redeploy frontend with VITE_GOOGLE_CLIENT_ID**

```bash
VITE_GOOGLE_CLIENT_ID="YOUR_CLIENT_ID.apps.googleusercontent.com" \
  ./deploy-frontend.sh
```

**Step 3: Update deploy-backend.sh to include the new env vars**

In `deploy-backend.sh`, find:
```bash
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},CORS_ORIGIN=${CORS_ORIGIN}" \
```

Replace with:
```bash
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},CORS_ORIGIN=${CORS_ORIGIN},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-},ALLOWED_EMAILS=${ALLOWED_EMAILS:-}" \
```

**Step 4: Smoke test**

Open `https://anima-mvp-feac4.web.app` and verify:
- [ ] Sign-In overlay is shown before login
- [ ] "Googleでログイン" button appears
- [ ] Logging in with an approved email grants access
- [ ] Logging in with a non-approved email shows connection error
- [ ] Camera, microphone, and AI response work normally after login

**Step 5: Commit**

```bash
git add deploy-backend.sh
git commit -m "feat: add auth env vars to deploy-backend.sh"
```
