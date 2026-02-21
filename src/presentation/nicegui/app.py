"""
NiceGUI frontend application — Presentation layer main page.

This module wires together all UI components and handles:
- Authentication (password form)
- Settings panel (config_panel)
- Chat display (direct DOM via JavaScript)
- Media controls (media_controls)
- Memories dialog (memories_dialog)
- Connect / Disconnect logic (calls JS via ui.run_javascript)
"""

import json
import os
import uuid

from nicegui import app, ui

from .js_bridge import GEMINI_BRIDGE_JS
from .personas import PERSONA_PROMPTS
from .components.config_panel import build_config_panel
from .components.media_controls import build_media_controls
from .components.memories_dialog import build_memories_dialog

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8080")
BACKEND_WS_URL = os.environ.get(
    "BACKEND_WS_URL",
    BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws",
)


def _default_state() -> dict:
    return {
        # Connection
        "proxy_url": BACKEND_WS_URL,
        "project_id": "",
        "model": "gemini-2.0-flash-live-001",
        "connected": False,
        # Persona & voice
        "persona": "bright_friend",
        "voice": "Puck",
        "temperature": 1.0,
        # Feature flags
        "proactive_audio": False,
        "grounding": False,
        "affective_dialog": False,
        "input_transcription": True,
        "output_transcription": True,
        # Activity detection
        "disable_activity_detection": False,
        "silence_duration": 2000,
        "prefix_padding": 500,
        # Media
        "audio_streaming": False,
        "video_streaming": False,
        "volume": 80,
        "selected_mic": "",
        "selected_camera": "",
    }


@ui.page("/")
async def index():
    # ── Per-client state ──────────────────────────────────────────────────────
    state = _default_state()

    # Restore persisted settings from browser localStorage via JS
    stored_project_id = await ui.run_javascript(
        "localStorage.getItem('projectId') || ''"
    )
    stored_persona = await ui.run_javascript(
        "localStorage.getItem('persona') || 'bright_friend'"
    )
    stored_model = await ui.run_javascript(
        "localStorage.getItem('model') || 'gemini-2.0-flash-live-001'"
    )
    user_id = await ui.run_javascript(
        "localStorage.getItem('userId') || (function(){ const id = 'user-' + Math.random().toString(36).slice(2); localStorage.setItem('userId', id); return id; })()"
    )

    state["project_id"] = stored_project_id or ""
    state["persona"] = stored_persona or "bright_friend"
    state["model"] = stored_model or "gemini-2.0-flash-live-001"
    state["user_id"] = user_id

    # ── Inject JavaScript bridge ───────────────────────────────────────────────
    ui.add_head_html(GEMINI_BRIDGE_JS)

    # ── Dark theme & global styles ─────────────────────────────────────────────
    ui.add_head_html("""
    <style>
      body { background: #121212 !important; }
      .nicegui-content { background: #121212; }
      .q-expansion-item__header { color: #e0e0e0 !important; }
      .q-expansion-item__container { background: #1e1e1e; }
    </style>
    """)

    # ── Auth check ─────────────────────────────────────────────────────────────
    stored_password = await ui.run_javascript(
        "sessionStorage.getItem('appPassword') || ''"
    )
    if not stored_password:
        _show_auth_page(state)
        return

    state["app_password"] = stored_password
    _show_main_page(state)


def _show_auth_page(state: dict) -> None:
    with ui.column().style(
        "width:100vw; height:100vh; justify-content:center; align-items:center; background:#121212;"
    ):
        with ui.card().style(
            "background:#1e1e1e; padding:40px; border-radius:16px; min-width:320px; "
            "box-shadow:0 8px 32px rgba(0,0,0,0.5); align-items:center; gap:16px;"
        ):
            ui.label("AI パートナー").style(
                "font-size:28px; font-weight:bold; color:#fff; text-align:center"
            )
            ui.label("Gemini Live API 搭載").style(
                "font-size:14px; color:#aaa; margin-top:-8px; text-align:center"
            )

            password_input = ui.input(
                placeholder="パスワードを入力",
                password=True,
                password_toggle_button=True,
            ).style("width:280px; margin-top:16px")

            error_label = ui.label("").style("color:#ef5350; font-size:13px; min-height:20px")

            async def submit():
                pw = password_input.value.strip()
                if not pw:
                    error_label.text = "パスワードを入力してください"
                    return
                await ui.run_javascript(f"sessionStorage.setItem('appPassword', {json.dumps(pw)})")
                ui.navigate.to("/")

            password_input.on("keydown.enter", submit)

            ui.button("入室", on_click=submit).style(
                "width:280px; background:#1976d2; color:#fff; font-size:16px; "
                "border-radius:8px; margin-top:8px;"
            ).props("unelevated")


def _show_main_page(state: dict) -> None:
    # ── Register JS callbacks (JS → Python notifications) ─────────────────────
    # These JS functions are called by the bridge when events occur.
    ui.add_head_html("""
    <script>
    window._niceguiOnConnected = function() {
        document.getElementById('conn-status').textContent = '接続中';
        document.getElementById('conn-status').style.color = '#66bb6a';
        document.getElementById('conn-dot').style.background = '#66bb6a';
        document.getElementById('connect-btn').style.display = 'none';
        document.getElementById('disconnect-btn').style.display = '';
    };
    window._niceguiOnDisconnect = function(code, reason) {
        document.getElementById('conn-status').textContent = '未接続';
        document.getElementById('conn-status').style.color = '#aaa';
        document.getElementById('conn-dot').style.background = '#aaa';
        document.getElementById('connect-btn').style.display = '';
        document.getElementById('disconnect-btn').style.display = 'none';
    };
    window._niceguiOnError = function(msg) {
        const area = document.getElementById('chat-messages');
        if (area) {
            const el = document.createElement('div');
            el.style.cssText = 'color:#ef5350; text-align:center; font-size:13px; padding:8px;';
            el.textContent = '[エラー: ' + msg + ']';
            area.appendChild(el);
        }
    };
    window._niceguiOnAuthError = function() {
        sessionStorage.removeItem('appPassword');
        location.reload();
    };
    </script>
    """)

    memories_dialog, open_memories = build_memories_dialog(BACKEND_URL)

    # ── Layout ─────────────────────────────────────────────────────────────────
    with ui.row().style(
        "width:100vw; height:100vh; gap:0; background:#121212; overflow:hidden;"
    ):

        # ── Left sidebar: settings ─────────────────────────────────────────────
        with ui.column().style(
            "width:300px; min-width:280px; height:100vh; background:#1a1a1a; "
            "border-right:1px solid #333; overflow-y:auto; padding:12px; gap:8px;"
        ):
            ui.label("AI パートナー").style(
                "font-size:18px; font-weight:bold; color:#fff; padding:4px 0 8px 0"
            )

            # Memories button
            async def show_memories():
                pw = state.get("app_password", "")
                uid = state.get("user_id", "default-user")
                persona = state.get("persona", "bright_friend")
                await open_memories(pw, uid, persona)

            ui.button("🧠 記憶を見る", on_click=show_memories).style(
                "width:100%; background:#2d2d2d; color:#e0e0e0; font-size:13px"
            ).props("flat unelevated")

            ui.separator().style("margin:4px 0; border-color:#333")

            # Settings panels
            build_config_panel(state)

            ui.separator().style("margin:4px 0; border-color:#333")

            # Save settings to localStorage on change
            async def _persist():
                await ui.run_javascript(f"""
                    localStorage.setItem('projectId', {json.dumps(state.get('project_id', ''))});
                    localStorage.setItem('persona', {json.dumps(state.get('persona', 'bright_friend'))});
                    localStorage.setItem('model', {json.dumps(state.get('model', 'gemini-2.0-flash-live-001'))});
                """)

            # Logout button
            async def logout():
                await ui.run_javascript("sessionStorage.removeItem('appPassword')")
                ui.navigate.to("/")

            ui.button("ログアウト", on_click=logout, icon="logout").style(
                "width:100%; color:#888; font-size:12px"
            ).props("flat")

        # ── Main area: chat + controls ─────────────────────────────────────────
        with ui.column().style(
            "flex:1; height:100vh; overflow:hidden; display:flex; flex-direction:column; "
            "background:#121212;"
        ):

            # Toolbar
            with ui.row().style(
                "align-items:center; gap:12px; padding:10px 16px; "
                "background:#1a1a1a; border-bottom:1px solid #333; flex-shrink:0;"
            ):
                # Connection status indicator
                ui.html(
                    '<span id="conn-dot" style="display:inline-block;width:10px;height:10px;'
                    'border-radius:50%;background:#aaa;"></span>'
                )
                ui.html('<span id="conn-status" style="color:#aaa;font-size:13px;">未接続</span>')

                ui.element("div").style("flex:1")  # spacer

                # Connect button
                async def connect():
                    pw = state.get("app_password", "")
                    persona_key = state.get("persona", "bright_friend")
                    persona_data = PERSONA_PROMPTS.get(persona_key, PERSONA_PROMPTS["bright_friend"])

                    config = {
                        "appPassword": pw,
                        "userId": state.get("user_id", "default-user"),
                        "persona": persona_key,
                        "projectId": state.get("project_id", ""),
                        "model": state.get("model", "gemini-2.0-flash-live-001"),
                        "voice": state.get("voice", persona_data["voice"]),
                        "temperature": state.get("temperature", 1.0),
                        "systemInstruction": persona_data["prompt"],
                        "proactiveAudio": state.get("proactive_audio", False),
                        "grounding": state.get("grounding", False),
                        "affectiveDialog": state.get("affective_dialog", False),
                        "inputTranscription": state.get("input_transcription", True),
                        "outputTranscription": state.get("output_transcription", True),
                        "disableActivityDetection": state.get("disable_activity_detection", False),
                        "silenceDuration": state.get("silence_duration", 2000),
                        "prefixPadding": state.get("prefix_padding", 500),
                    }

                    proxy_url = state.get("proxy_url", BACKEND_WS_URL)
                    await ui.run_javascript(
                        f"window.geminiConnect({json.dumps(proxy_url)}, {json.dumps(config)})"
                    )
                    state["connected"] = True
                    await _persist()

                connect_btn_html = (
                    '<button id="connect-btn" onclick="document.getElementById(\'connect-py-btn\').click()" '
                    'style="background:#1976d2;color:#fff;border:none;padding:8px 18px;'
                    'border-radius:8px;cursor:pointer;font-size:14px;">接続</button>'
                )
                disconnect_btn_html = (
                    '<button id="disconnect-btn" onclick="document.getElementById(\'disconnect-py-btn\').click()" '
                    'style="display:none;background:#d32f2f;color:#fff;border:none;padding:8px 18px;'
                    'border-radius:8px;cursor:pointer;font-size:14px;">切断</button>'
                )
                ui.html(connect_btn_html + disconnect_btn_html)

                # Hidden NiceGUI buttons triggered by the HTML buttons above
                async def disconnect():
                    await ui.run_javascript("window.geminiDisconnect()")
                    state["connected"] = False
                    state["audio_streaming"] = False
                    state["video_streaming"] = False

                ui.button(on_click=connect).props("id=connect-py-btn").style("display:none")
                ui.button(on_click=disconnect).props("id=disconnect-py-btn").style("display:none")

            # Chat area
            ui.html(
                '<div id="chat-messages" style="'
                "flex:1; overflow-y:auto; padding:16px; "
                "display:flex; flex-direction:column; gap:4px; "
                "min-height:0; background:#121212;"
                '"></div>'
            ).style("flex:1; display:flex; flex-direction:column; overflow:hidden; min-height:0")

            # Bottom controls area
            with ui.column().style(
                "flex-shrink:0; padding:12px 16px; background:#1a1a1a; "
                "border-top:1px solid #333; gap:8px;"
            ):
                # Media controls
                build_media_controls(state)

                # Text input row
                with ui.row().style("align-items:center; gap:8px; width:100%; margin-top:4px"):
                    text_input = ui.input(
                        placeholder="テキストメッセージを送信... (Enter で送信)",
                    ).style(
                        "flex:1; background:#2d2d2d; color:#e0e0e0; border-radius:8px"
                    ).props("outlined dense dark")

                    async def send_text():
                        text = text_input.value.strip()
                        if not text:
                            return
                        if not state.get("connected"):
                            ui.notify("先に Gemini に接続してください", type="warning")
                            return
                        await ui.run_javascript(
                            f"window.geminiSendText({json.dumps(text)})"
                        )
                        # Show user message in chat
                        await ui.run_javascript(
                            f"appendChatMessage({json.dumps(text)}, 'user', true)"
                        )
                        text_input.value = ""

                    text_input.on("keydown.enter", send_text)

                    ui.button(icon="send", on_click=send_text).props(
                        "color=primary unelevated round dense"
                    )
