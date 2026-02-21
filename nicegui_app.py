#!/usr/bin/env python3
"""
NiceGUI Frontend Entry Point — Presentation Layer

Pythonでフロントエンドを実装したバージョン。
既存の aiohttp バックエンド (server.py) とは別ポートで動作します。

使い方:
    BACKEND_URL=http://localhost:8080 python nicegui_app.py

環境変数:
    FRONTEND_PORT   NiceGUI が使用するポート (デフォルト: 3001)
    BACKEND_URL     バックエンドの HTTP URL (デフォルト: http://localhost:8080)
    BACKEND_WS_URL  バックエンドの WebSocket URL (デフォルト: ws://localhost:8080/ws)
    APP_RELOAD      開発時のホットリロード有効化 (true/false)
"""

import os
from nicegui import app, ui

# Serve the audio worklet files that the browser needs for audio processing.
# These files are already in the React public/ directory.
app.add_static_files("/audio-processors", "public/audio-processors")

# Import and register the page routes
import src.presentation.nicegui.app  # noqa: F401  (registers @ui.page routes)

if __name__ in ("__main__", "__mp_main__"):
    port = int(os.environ.get("FRONTEND_PORT", 3001))
    reload = os.environ.get("APP_RELOAD", "false").lower() == "true"

    print(f"""
╔════════════════════════════════════════════════════════════╗
║     NiceGUI Frontend (Python)                             ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  🌐 Frontend:  http://localhost:{port:<5}                       ║
║  🔌 Backend:   {os.environ.get('BACKEND_URL', 'http://localhost:8080'):<44}  ║
║                                                            ║
║  バックエンド (server.py) を先に起動してください           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")

    ui.run(
        host="0.0.0.0",
        port=port,
        title="AI パートナー",
        favicon="🤖",
        dark=True,
        reload=reload,
        show=False,
    )
