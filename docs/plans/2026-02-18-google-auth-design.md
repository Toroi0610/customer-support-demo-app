# Google Authentication Design

**Date:** 2026-02-18
**Status:** Approved

## Goal

Restrict access to the app to specific approved Google accounts using Google Identity Services (frontend) and google-auth token verification (backend).

## Authentication Flow

```
User opens app
    ↓
Logged in? → No → Show Google Sign-In overlay
    ↓ Yes              ↓
    ↓          Click "Googleでログイン"
    ↓                  ↓
    ↓          Receive Google ID token (JWT)
    ↓                  ↓
    ↓          Store in React state (NOT localStorage)
    ↓
On WebSocket connect:
  → Include id_token in first setup message
  → Backend: verify token + check ALLOWED_EMAILS
  → Fail → reject connection with error
  → Pass → proceed with proxy

On /analyze-frame HTTP call:
  → Authorization: Bearer <id_token> header
  → Backend: same verification
```

## Components

### Frontend

| File | Change |
|---|---|
| `index.html` | Add Google Identity Services `<script>` tag |
| `LiveAPIDemo.jsx` | `idToken` state, Sign-In overlay when not logged in, include `id_token` in WebSocket setup message |
| `src/utils/user-monitor.js` | Add `Authorization: Bearer <idToken>` header to `/analyze-frame` requests |
| `.env.example` | Add `VITE_GOOGLE_CLIENT_ID` |
| `.env.local` | Add `VITE_GOOGLE_CLIENT_ID=<dev client id>` |

### Backend

| File | Change |
|---|---|
| `server.py` | Verify Google ID token in `ws_handler` before proxying |
| `server.py` | Verify Google ID token in `handle_analyze_frame` before processing |
| `server.py` | Read `ALLOWED_EMAILS` and `GOOGLE_CLIENT_ID` env vars |

### GCP Setup (manual, one-time)

1. Create OAuth 2.0 Client ID in Google Cloud Console
   - Application type: Web application
   - Authorized JavaScript origins: `https://anima-mvp-feac4.web.app`
2. Set Cloud Run environment variables:
   - `ALLOWED_EMAILS=approved@gmail.com,other@gmail.com`
   - `GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com`
3. Set Vite build variable: `VITE_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com`

## User Experience

| State | UI |
|---|---|
| Not logged in | Full-screen overlay with Google Sign-In button |
| Logged in, not in allowlist | Error message: 「アクセスが許可されていません」 |
| Logged in, in allowlist | Normal app |
| Token expired (1h) | Re-connect fails → page reload triggers re-login |

## Constraints

- No auto token refresh (1 hour sessions, re-login on expiry)
- ID token stored in React state only (not localStorage)
- Allowlist managed via Cloud Run env var; requires redeploy to update
