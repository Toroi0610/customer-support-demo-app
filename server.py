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

# Authentication
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
ALLOWED_EMAILS_RAW = os.environ.get("ALLOWED_EMAILS", "")
ALLOWED_EMAILS = set(e.strip() for e in ALLOWED_EMAILS_RAW.split(",") if e.strip())


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
