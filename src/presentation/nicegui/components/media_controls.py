"""
Media controls component for NiceGUI frontend.
Presentation layer — audio/video toggle buttons that call JavaScript via ui.run_javascript().
"""

from nicegui import ui


def build_media_controls(state: dict) -> None:
    """
    Build audio / video / volume controls.

    state keys used: audio_streaming, video_streaming, volume,
                     selected_mic, selected_camera, connected
    """

    with ui.row().style("align-items:center; gap:12px; flex-wrap:wrap"):

        # Audio toggle
        async def toggle_audio():
            if not state.get("connected"):
                ui.notify("先に Gemini に接続してください", type="warning")
                return
            if state.get("audio_streaming"):
                await ui.run_javascript("window.geminiStopAudio()")
                state["audio_streaming"] = False
                audio_btn.props("color=grey-8 icon=mic_off")
                audio_btn.text = "マイク OFF"
            else:
                device_id = state.get("selected_mic", "")
                js = f"window.geminiStartAudio({repr(device_id) if device_id else 'null'})"
                try:
                    await ui.run_javascript(js)
                    state["audio_streaming"] = True
                    audio_btn.props("color=red icon=mic")
                    audio_btn.text = "マイク ON"
                except Exception as e:
                    ui.notify(f"マイクエラー: {e}", type="negative")

        audio_btn = ui.button(
            "マイク OFF",
            on_click=toggle_audio,
            icon="mic_off",
        ).props("color=grey-8 unelevated").style("font-size:13px")

        # Video toggle
        async def toggle_video():
            if not state.get("connected"):
                ui.notify("先に Gemini に接続してください", type="warning")
                return
            if state.get("video_streaming"):
                await ui.run_javascript("window.geminiStopVideo()")
                state["video_streaming"] = False
                video_btn.props("color=grey-8 icon=videocam_off")
                video_btn.text = "カメラ OFF"
            else:
                device_id = state.get("selected_camera", "")
                js = f"window.geminiStartVideo({repr(device_id) if device_id else 'null'})"
                try:
                    await ui.run_javascript(js)
                    state["video_streaming"] = True
                    video_btn.props("color=green icon=videocam")
                    video_btn.text = "カメラ ON"
                except Exception as e:
                    ui.notify(f"カメラエラー: {e}", type="negative")

        video_btn = ui.button(
            "カメラ OFF",
            on_click=toggle_video,
            icon="videocam_off",
        ).props("color=grey-8 unelevated").style("font-size:13px")

    # Volume slider
    with ui.row().style("align-items:center; gap:8px; margin-top:8px; width:100%"):
        ui.icon("volume_up").style("color:#aaa")
        ui.label("音量").style("color:#aaa; font-size:13px; min-width:30px")

        async def on_volume_change(e):
            state["volume"] = e.value
            await ui.run_javascript(f"window.geminiSetVolume({e.value / 100})")

        ui.slider(
            min=0, max=100, step=1,
            value=state.get("volume", 80),
            on_change=on_volume_change,
        ).style("flex:1")

        ui.label().bind_text_from(state, "volume", lambda v: f"{v}%").style(
            "color:#aaa; font-size:13px; min-width:35px"
        )

    # Video preview (hidden by default, shown by JS when camera starts)
    with ui.element("div").style("margin-top:8px; width:100%"):
        ui.html(
            '<video id="video-preview" hidden muted playsinline '
            'style="width:100%; max-height:180px; border-radius:8px; background:#000;"></video>'
        )
