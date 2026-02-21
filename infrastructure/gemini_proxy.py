"""GeminiProxy - bidirectional WebSocket proxy between browser and Gemini API."""
import asyncio
import ssl

import certifi
import websockets
from websockets.exceptions import ConnectionClosed

from .google_auth import GoogleAuthService

DEBUG = False


async def _proxy_task(source, destination, label: str) -> None:
    """Forward every message from *source* to *destination*."""
    import json
    try:
        async for message in source:
            try:
                data = json.loads(message)
                if DEBUG:
                    print(f"[proxy] {label}: {data}")
                await destination.send(json.dumps(data))
            except Exception as exc:
                print(f"[proxy] Error processing {label} message: {exc}")
    except ConnectionClosed as exc:
        print(f"[proxy] {label} connection closed: {exc.code} - {exc.reason}")
    except Exception as exc:
        print(f"[proxy] Unexpected error in {label}: {exc}")
    finally:
        await destination.close()


class GeminiProxy:
    """Opens a WebSocket connection to the Gemini Live API and creates a
    bidirectional proxy with the browser client.

    Responsibilities:
      - Authenticate with Google Cloud (via GoogleAuthService)
      - Optionally send a pre-built session setup message as the first server frame
      - Relay all subsequent messages in both directions
    """

    def __init__(self, auth_service: GoogleAuthService = None) -> None:
        self._auth = auth_service or GoogleAuthService()

    async def proxy(
        self,
        client_websocket,
        service_url: str,
        bearer_token: str = "",
        initial_server_message: dict = None,
    ) -> None:
        """Connect to Gemini and proxy until one side disconnects."""
        token = bearer_token or self._auth.get_access_token()
        if not token:
            print("❌ GeminiProxy: could not obtain bearer token")
            await client_websocket.close(code=1008, reason="Authentication failed")
            return

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        print("Connecting to Gemini API…")
        try:
            async with websockets.connect(
                service_url,
                additional_headers=headers,
                ssl=ssl_context,
            ) as server_ws:
                print("✅ Connected to Gemini API")

                if initial_server_message is not None:
                    import json
                    await server_ws.send(json.dumps(initial_server_message))

                c2s = asyncio.create_task(
                    _proxy_task(client_websocket, server_ws, "client→server")
                )
                s2c = asyncio.create_task(
                    _proxy_task(server_ws, client_websocket, "server→client")
                )

                done, pending = await asyncio.wait(
                    [c2s, s2c], return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                for ws in (server_ws, client_websocket):
                    try:
                        await ws.close()
                    except Exception:
                        pass

        except ConnectionClosed as exc:
            print(f"Server connection closed: {exc.code} - {exc.reason}")
            if not client_websocket.closed:
                await client_websocket.close(code=exc.code, reason=exc.reason)
        except Exception as exc:
            print(f"Failed to connect to Gemini API: {exc}")
            if not client_websocket.closed:
                await client_websocket.close(
                    code=1008, reason="Upstream connection failed"
                )
