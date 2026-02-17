#!/usr/bin/env python3
"""
WebSocket Proxy Server for Gemini Live API
Handles authentication and proxies WebSocket connections.

This server acts as a bridge between the browser client and Gemini API,
handling Google Cloud authentication automatically using default credentials.
"""

import asyncio
import websockets
import json
import ssl
import certifi
import os
import base64
from aiohttp import web
from websockets.legacy.server import WebSocketServerProtocol
from websockets.legacy.protocol import WebSocketCommonProtocol
from websockets.exceptions import ConnectionClosed

# Google auth imports
import google.auth
from google.auth.transport.requests import Request

DEBUG = False  # Set to True for verbose logging
WS_PORT = 8080    # Port for WebSocket server
HTTP_PORT = 8081   # Port for HTTP analysis endpoint


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


async def proxy_task(
    source_websocket: WebSocketCommonProtocol,
    destination_websocket: WebSocketCommonProtocol,
    is_server: bool,
) -> None:
    """
    Forwards messages from source_websocket to destination_websocket.

    Args:
        source_websocket: The WebSocket connection to receive messages from.
        destination_websocket: The WebSocket connection to send messages to.
        is_server: True if source is server side, False otherwise.
    """
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


async def create_proxy(
    client_websocket: WebSocketCommonProtocol, bearer_token: str, service_url: str
) -> None:
    """
    Establishes a WebSocket connection to the Gemini server and creates bidirectional proxy.

    Args:
        client_websocket: The WebSocket connection of the client.
        bearer_token: The bearer token for authentication with the server.
        service_url: The url of the service to connect to.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
    }

    # Create SSL context with certifi certificates
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

            # Create bidirectional proxy tasks
            client_to_server_task = asyncio.create_task(
                proxy_task(client_websocket, server_websocket, is_server=False)
            )
            server_to_client_task = asyncio.create_task(
                proxy_task(server_websocket, client_websocket, is_server=True)
            )

            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [client_to_server_task, server_to_client_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel the remaining task
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Close connections
            try:
                await server_websocket.close()
            except:
                pass

            try:
                await client_websocket.close()
            except:
                pass

    except ConnectionClosed as e:
        print(f"Server connection closed unexpectedly: {e.code} - {e.reason}")
        if not client_websocket.closed:
            await client_websocket.close(code=e.code, reason=e.reason)
    except Exception as e:
        print(f"Failed to connect to Gemini API: {e}")
        if not client_websocket.closed:
            await client_websocket.close(code=1008, reason="Upstream connection failed")


async def handle_websocket_client(client_websocket: WebSocketServerProtocol) -> None:
    """
    Handles a new WebSocket client connection.

    Expects first message with optional bearer_token and service_url.
    If no bearer_token provided, generates one using Google default credentials.

    Args:
        client_websocket: The WebSocket connection of the client.
    """
    print("🔌 New WebSocket client connection...")
    try:
        # Wait for the first message from the client
        service_setup_message = await asyncio.wait_for(
            client_websocket.recv(), timeout=10.0
        )
        service_setup_message_data = json.loads(service_setup_message)

        bearer_token = service_setup_message_data.get("bearer_token")
        service_url = service_setup_message_data.get("service_url")

        # If no bearer token provided, generate one using default credentials
        if not bearer_token:
            print("🔑 Generating access token using default credentials...")
            bearer_token = generate_access_token()
            if not bearer_token:
                print("❌ Failed to generate access token")
                await client_websocket.close(
                    code=1008, reason="Authentication failed"
                )
                return
            print("✅ Access token generated")

        if not service_url:
            print("❌ Error: Service URL is missing")
            await client_websocket.close(
                code=1008, reason="Service URL is required"
            )
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


async def start_websocket_server():
    """Start the WebSocket proxy server."""
    async with websockets.serve(handle_websocket_client, "0.0.0.0", WS_PORT):
        print(f"🔌 WebSocket proxy running on ws://localhost:{WS_PORT}")
        # Run forever
        await asyncio.Future()


# ─── HTTP Frame Analysis Endpoint ───────────────────────────────────

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
    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
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

        # Get access token
        token = generate_access_token()
        if not token:
            return web.json_response(
                {"error": "Authentication failed"}, status=500, headers=headers
            )

        # Build prompt with previous state context
        if previous_status:
            user_prompt = f"Analyze this image. Previous status_key was: '{previous_status}'. Compare with current state."
        else:
            user_prompt = "Analyze this image. This is the first frame being analyzed."

        # Call Gemini REST API via Vertex AI
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

        import aiohttp

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

        # Extract the text response
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
        return web.json_response(
            {"error": str(e)}, status=500, headers=headers
        )


async def start_http_server():
    """Start the HTTP server for frame analysis."""
    app = web.Application()
    app.router.add_post("/analyze-frame", handle_analyze_frame)
    app.router.add_options("/analyze-frame", handle_analyze_frame)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    print(f"🔍 HTTP analysis endpoint running on http://localhost:{HTTP_PORT}/analyze-frame")


async def main():
    """
    Starts the WebSocket server and HTTP analysis server.
    """
    print(f"""
╔════════════════════════════════════════════════════════════╗
║     Gemini Live API Proxy Server                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  🔌 WebSocket Proxy: ws://localhost:{WS_PORT:<5}                   ║
║  🔍 Frame Analysis:  http://localhost:{HTTP_PORT}/analyze-frame  ║
║                                                            ║
║  Authentication:                                           ║
║  • Uses Google Cloud default credentials                  ║
║  • Run: gcloud auth application-default login             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")

    # Start both servers concurrently
    await asyncio.gather(
        start_websocket_server(),
        start_http_server(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Servers stopped")