"""
Configuration panel component for NiceGUI frontend.
Presentation layer — settings UI for persona, model, voice, etc.
"""

import json
from nicegui import ui
from ..personas import PERSONA_PROMPTS, VOICE_OPTIONS, MODEL_OPTIONS


def build_config_panel(state: dict, on_change=None) -> None:
    """
    Build the settings panel. Mutates `state` dict on change.

    state keys:
        persona, model, voice, temperature, proactive_audio, grounding,
        affective_dialog, input_transcription, output_transcription,
        disable_activity_detection, silence_duration, prefix_padding,
        project_id, proxy_url
    """

    def _notify():
        if on_change:
            on_change(state)

    with ui.expansion("接続設定", icon="cable").style("width:100%; color:#e0e0e0"):
        ui.input(
            label="バックエンド WebSocket URL",
            value=state.get("proxy_url", "ws://localhost:8080/ws"),
            on_change=lambda e: state.update({"proxy_url": e.value}) or _notify(),
        ).style("width:100%").bind_enabled_from(state, "connected", lambda v: not v)

        ui.input(
            label="Google Cloud プロジェクト ID",
            value=state.get("project_id", ""),
            on_change=lambda e: state.update({"project_id": e.value}) or _notify(),
        ).style("width:100%").bind_enabled_from(state, "connected", lambda v: not v)

        ui.select(
            label="モデル",
            options=MODEL_OPTIONS,
            value=state.get("model", MODEL_OPTIONS[0]),
            on_change=lambda e: state.update({"model": e.value}) or _notify(),
        ).style("width:100%").bind_enabled_from(state, "connected", lambda v: not v)

    with ui.expansion("ペルソナ & 音声", icon="person").style("width:100%; color:#e0e0e0").props("default-opened"):
        persona_options = {k: v["label"] for k, v in PERSONA_PROMPTS.items()}

        persona_select = ui.select(
            label="ペルソナ",
            options=persona_options,
            value=state.get("persona", "bright_friend"),
        ).style("width:100%")

        def _on_persona_change(e):
            state["persona"] = e.value
            # Auto-set recommended voice
            persona_voice = PERSONA_PROMPTS[e.value]["voice"]
            voice_select.value = persona_voice
            state["voice"] = persona_voice
            _notify()

        persona_select.on("update:model-value", _on_persona_change)
        persona_select.bind_enabled_from(state, "connected", lambda v: not v)

        voice_select = ui.select(
            label="音声",
            options=VOICE_OPTIONS,
            value=state.get("voice", "Puck"),
            on_change=lambda e: state.update({"voice": e.value}) or _notify(),
        ).style("width:100%")
        voice_select.bind_enabled_from(state, "connected", lambda v: not v)

        ui.label(f"温度: {state.get('temperature', 1.0):.1f}").bind_text_from(
            state, "temperature", lambda v: f"温度: {v:.1f}"
        ).style("color:#aaa; font-size:13px; margin-top:8px")

        ui.slider(
            min=0.1, max=2.0, step=0.1,
            value=state.get("temperature", 1.0),
            on_change=lambda e: state.update({"temperature": round(e.value, 1)}) or _notify(),
        ).style("width:100%").bind_enabled_from(state, "connected", lambda v: not v)

    with ui.expansion("AIの動作", icon="tune").style("width:100%; color:#e0e0e0"):
        ui.checkbox(
            "プロアクティブ音声を有効化",
            value=state.get("proactive_audio", False),
            on_change=lambda e: state.update({"proactive_audio": e.value}) or _notify(),
        ).bind_enabled_from(state, "connected", lambda v: not v)

        ui.checkbox(
            "Google グラウンディング",
            value=state.get("grounding", False),
            on_change=lambda e: state.update({"grounding": e.value}) or _notify(),
        ).bind_enabled_from(state, "connected", lambda v: not v)

        ui.checkbox(
            "感情対話を有効化",
            value=state.get("affective_dialog", False),
            on_change=lambda e: state.update({"affective_dialog": e.value}) or _notify(),
        ).bind_enabled_from(state, "connected", lambda v: not v)

        ui.checkbox(
            "入力音声の文字起こし",
            value=state.get("input_transcription", True),
            on_change=lambda e: state.update({"input_transcription": e.value}) or _notify(),
        ).bind_enabled_from(state, "connected", lambda v: not v)

        ui.checkbox(
            "出力音声の文字起こし",
            value=state.get("output_transcription", True),
            on_change=lambda e: state.update({"output_transcription": e.value}) or _notify(),
        ).bind_enabled_from(state, "connected", lambda v: not v)

    with ui.expansion("音声アクティビティ検出", icon="graphic_eq").style("width:100%; color:#e0e0e0"):
        ui.checkbox(
            "自動検出を無効化",
            value=state.get("disable_activity_detection", False),
            on_change=lambda e: state.update({"disable_activity_detection": e.value}) or _notify(),
        ).bind_enabled_from(state, "connected", lambda v: not v)

        ui.label("無音判定時間 (ms)").style("color:#aaa; font-size:13px; margin-top:8px")
        ui.number(
            value=state.get("silence_duration", 2000),
            min=500, max=10000, step=100,
            on_change=lambda e: state.update({"silence_duration": int(e.value)}) or _notify(),
        ).style("width:100%").bind_enabled_from(state, "connected", lambda v: not v)

        ui.label("前置きパディング (ms)").style("color:#aaa; font-size:13px; margin-top:8px")
        ui.number(
            value=state.get("prefix_padding", 500),
            min=0, max=5000, step=100,
            on_change=lambda e: state.update({"prefix_padding": int(e.value)}) or _notify(),
        ).style("width:100%").bind_enabled_from(state, "connected", lambda v: not v)
