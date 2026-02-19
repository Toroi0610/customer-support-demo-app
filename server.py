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

from datetime import datetime, timezone
from memory_mcp import store as memory_store

DEBUG = False  # Set to True for verbose logging
PORT = int(os.environ.get("PORT", 8080))

# Authentication
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

# ─── Memory utilities ─────────────────────────────────────────────────────────


def format_memories_for_prompt(memories: list) -> str:
    """Format a list of memory dicts into a Japanese prompt block.

    Each memory dict must have: summary, emotion, importance, days_ago.
    Returns empty string when memories list is empty.
    """
    if not memories:
        return ""
    lines = ["[過去の記憶]"]
    for m in memories:
        days = m.get("days_ago", 0)
        if days == 0:
            when = "今日"
        elif days == 1:
            when = "昨日"
        else:
            when = f"{days}日前"
        line = f"- {when}: {m.get('summary', '')}（感情: {m.get('emotion', '')}、重要度: {m.get('importance', 0.5):.1f}）"
        lines.append(line)
    return "\n".join(lines)


def inject_memories_into_setup(session_data: dict, memories: list) -> None:
    """Inject formatted memories into session_data system_instruction in-place.

    No-op when memories is empty or session_data has no setup key.
    """
    if not memories:
        return
    try:
        parts = session_data["setup"]["system_instruction"]["parts"]
        memory_block = format_memories_for_prompt(memories)
        if memory_block:
            parts[0]["text"] = parts[0]["text"] + "\n\n" + memory_block
    except (KeyError, IndexError, TypeError):
        return



SUMMARY_SYSTEM_INSTRUCTION = """You are a memory summarizer for an AI companion app.
Given a conversation transcript between a user and an AI companion, generate a concise summary in Japanese.
Respond with ONLY a valid JSON object (no markdown, no code blocks).

Provide:
1. "summary": 100-200 character summary of the key moments in the conversation in Japanese
2. "emotion": The user's dominant emotion during this conversation in Japanese (e.g., "楽しそう", "疲れている", "嬉しそう", "落ち込んでいた", "穏やか")
3. "importance": A float 0.0-1.0 rating how emotionally significant this conversation was (0.0 = routine, 1.0 = very significant)
4. "keywords": Array of 2-5 key topics or themes from the conversation in Japanese"""


async def generate_summary(transcript: list, emotions: list, persona: str, project_id: str) -> dict:
    """Generate a memory summary from a transcript using Gemini.

    transcript: list of {role, text} dicts
    Returns dict with summary, emotion, importance, keywords; or None on failure.
    """
    token = generate_access_token()
    if not token:
        return None

    transcript_text = "\n".join(
        f"{t.get('role', 'unknown')}: {t.get('text', '')}"
        for t in transcript
        if t.get("text", "").strip()
    )
    if not transcript_text.strip():
        return None

    emotion_note = f"\n観察された感情イベント: {', '.join(emotions)}" if emotions else ""
    user_prompt = f"以下の会話を要約してください。\n\n{transcript_text}{emotion_note}"

    url = (
        f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/us-central1/publishers/google/models/gemini-2.0-flash:generateContent"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": SUMMARY_SYSTEM_INSTRUCTION}]},
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                ssl=ssl_context,
            ) as resp:
                if resp.status != 200:
                    print(f"Summary Gemini API error: {resp.status}")
                    return None
                result = await resp.json()
                text_response = result["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_response)
                if not isinstance(parsed, dict) or "summary" not in parsed:
                    print(f"Unexpected summary format from Gemini: {parsed}")
                    return None
                return parsed
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None


async def get_memories(user_id: str, persona: str, limit: int = 3) -> list:
    """Fetch relevant memories for a user+persona from ChromaDB.

    Uses persona as the semantic search context so the most relevant memories
    for this interaction style are retrieved.
    """
    return await memory_store.recall_memories(user_id, persona, context=persona, limit=limit)


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


def verify_app_password(password: str) -> bool:
    """Verifies the app password.
    When APP_PASSWORD is not set, all connections are rejected to prevent
    accidental open access in production.
    """
    if not APP_PASSWORD:
        print("🚫 APP_PASSWORD not set — all connections rejected. Set APP_PASSWORD env var.")
        return False
    if password == APP_PASSWORD:
        print("✅ Access granted")
        return True
    print("🚫 Access denied: wrong password")
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


async def create_proxy(client_websocket, bearer_token: str, service_url: str, initial_server_message: dict = None) -> None:
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

            # Send the (optionally memory-injected) session setup message first
            if initial_server_message is not None:
                await server_websocket.send(json.dumps(initial_server_message))

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


async def handle_websocket_client(client_websocket, prefetched_setup: dict = None, prefetched_session: dict = None) -> None:
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

        await create_proxy(client_websocket, bearer_token, service_url, initial_server_message=prefetched_session)

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
    """aiohttp WebSocket upgrade handler."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # ── Read first message: service setup (auth + metadata) ───────────────────
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

    # Auth check
    app_password = setup_data.get("app_password", "")
    if not verify_app_password(app_password):
        await ws.send_json({"error": "unauthorized"})
        await ws.close(code=4001, message=b"Unauthorized")
        return ws

    user_id = setup_data.get("user_id", "")
    persona = setup_data.get("persona", "")

    # ── Read second message: session setup (system_instruction, tools, etc.) ──
    try:
        msg2 = await asyncio.wait_for(ws.receive(), timeout=10.0)
    except asyncio.TimeoutError:
        await ws.close(code=1008, message=b"Timeout waiting for session setup message")
        return ws

    if msg2.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
        await ws.close(code=1008, message=b"Expected text for session setup")
        return ws

    try:
        session_data = json.loads(msg2.data)
    except json.JSONDecodeError:
        await ws.close(code=1008, message=b"Invalid JSON in session setup")
        return ws

    # ── Fetch memories and inject into system prompt ───────────────────────────
    if user_id and persona:
        memories = await get_memories(user_id, persona, limit=3)
        if memories:
            inject_memories_into_setup(session_data, memories)
            print(f"💭 Injected {len(memories)} memories for {user_id}/{persona}")

    adapter = AiohttpWSAdapter(ws)
    await handle_websocket_client(adapter, prefetched_setup=setup_data, prefetched_session=session_data)
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

    # Verify app password
    auth_header = request.headers.get("Authorization", "")
    password = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not verify_app_password(password):
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


async def handle_memory_list(request):
    """HTTP endpoint to list recent memories for a user+persona."""
    cors_origin = os.environ.get("CORS_ORIGIN", "*")
    headers = {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

    if request.method == "OPTIONS":
        return web.Response(headers=headers)

    auth_header = request.headers.get("Authorization", "")
    password = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not verify_app_password(password):
        return web.json_response({"error": "Unauthorized"}, status=401, headers=headers)

    user_id = request.rel_url.query.get("user_id", "").strip()
    persona = request.rel_url.query.get("persona", "").strip()
    try:
        limit = int(request.rel_url.query.get("limit", "10"))
    except ValueError:
        return web.json_response(
            {"error": "limit must be an integer"}, status=400, headers=headers
        )
    if limit <= 0:
        return web.json_response(
            {"error": "limit must be a positive integer"}, status=400, headers=headers
        )

    if not user_id or not persona:
        return web.json_response(
            {"error": "user_id and persona are required"}, status=400, headers=headers
        )

    try:
        memories = await memory_store.list_recent_memories(user_id, persona, limit)
        return web.json_response({"memories": memories}, headers=headers)
    except Exception as e:
        print(f"Error in handle_memory_list: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=headers)


async def handle_memory_save(request):
    """HTTP endpoint to save a session memory."""
    cors_origin = os.environ.get("CORS_ORIGIN", "*")
    headers = {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

    if request.method == "OPTIONS":
        return web.Response(headers=headers)

    auth_header = request.headers.get("Authorization", "")
    password = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not verify_app_password(password):
        return web.json_response({"error": "Unauthorized"}, status=401, headers=headers)

    try:
        data = await request.json()
        user_id = data.get("user_id", "").strip()
        persona = data.get("persona", "").strip()
        transcript = data.get("transcript", [])
        if not isinstance(transcript, list):
            return web.json_response({"error": "transcript must be a list"}, status=400, headers=headers)
        emotions = data.get("emotions", [])
        project_id = data.get("project_id", os.environ.get("GOOGLE_CLOUD_PROJECT", ""))

        if not user_id or not persona:
            return web.json_response({"error": "user_id and persona are required"}, status=400, headers=headers)
        if not transcript:
            return web.json_response({"error": "transcript is required"}, status=400, headers=headers)
        if not project_id:
            return web.json_response({"error": "project_id is required"}, status=400, headers=headers)

        summary_data = await generate_summary(transcript, emotions, persona, project_id)
        if not summary_data:
            return web.json_response({"error": "Failed to generate summary"}, status=500, headers=headers)

        memory_id = await memory_store.save_memory(
            user_id=user_id,
            persona=persona,
            summary=summary_data.get("summary", ""),
            emotion=summary_data.get("emotion", ""),
            importance=float(summary_data.get("importance", 0.5)),
            keywords=summary_data.get("keywords", []),
            project_id=project_id,
        )

        print(f"✅ Memory saved: {memory_id} for {user_id}/{persona}")
        return web.json_response(
            {"memory_id": memory_id, "summary": summary_data.get("summary", "")},
            headers=headers
        )

    except Exception as e:
        print(f"Error in handle_memory_save: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=headers)


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
    app.router.add_get("/memory/list", handle_memory_list)
    app.router.add_options("/memory/list", handle_memory_list)
    app.router.add_post("/memory/save", handle_memory_save)
    app.router.add_options("/memory/save", handle_memory_save)

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
