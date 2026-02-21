"""
Memories dialog component for NiceGUI frontend.
Presentation layer — fetches memories from the backend REST API via Python.
"""

import aiohttp
from nicegui import ui


def build_memories_dialog(backend_url: str) -> tuple:
    """
    Build the memories dialog.

    Returns (dialog, open_fn) where open_fn(password, user_id, persona) fetches and shows memories.
    """
    with ui.dialog() as dialog, ui.card().style("min-width:600px; max-width:800px; background:#1e1e1e; color:#e0e0e0"):
        ui.label("🧠 過去の記憶").style("font-size:20px; font-weight:bold; color:#fff; margin-bottom:8px")

        memories_column = ui.column().style("width:100%; gap:8px; max-height:500px; overflow-y:auto")
        status_label = ui.label("").style("color:#aaa; font-size:13px")

        with ui.row().style("justify-content:flex-end; width:100%; margin-top:8px"):
            ui.button("閉じる", on_click=dialog.close).style("background:#444; color:#fff")

    async def open_dialog(password: str, user_id: str, persona: str, limit: int = 10) -> None:
        memories_column.clear()
        status_label.text = "読み込み中..."
        dialog.open()

        try:
            url = f"{backend_url}/memory/list"
            params = {"user_id": user_id, "persona": persona, "limit": limit}
            headers = {"Authorization": f"Bearer {password}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 401:
                        status_label.text = "認証エラー: パスワードが正しくありません"
                        return
                    if resp.status != 200:
                        status_label.text = f"エラー: {resp.status}"
                        return
                    data = await resp.json()

            memories = data.get("memories", [])
            if not memories:
                with memories_column:
                    ui.label("まだ記憶がありません").style("color:#888; font-style:italic")
                status_label.text = ""
                return

            with memories_column:
                for mem in memories:
                    days = mem.get("days_ago", 0)
                    if days == 0:
                        when = "今日"
                    elif days == 1:
                        when = "昨日"
                    else:
                        when = f"{days}日前"

                    importance = mem.get("importance", 0.5)
                    importance_stars = "★" * round(importance * 5) + "☆" * (5 - round(importance * 5))
                    emotion = mem.get("emotion", "")

                    with ui.card().style(
                        "background:#2d2d2d; border-left:3px solid #1976d2; "
                        "padding:12px; width:100%; box-sizing:border-box"
                    ):
                        with ui.row().style("justify-content:space-between; align-items:center; margin-bottom:4px"):
                            ui.label(when).style("color:#aaa; font-size:12px")
                            ui.label(importance_stars).style("color:#ffd700; font-size:12px")

                        ui.label(mem.get("summary", "")).style(
                            "color:#e0e0e0; font-size:14px; line-height:1.5"
                        )

                        if emotion:
                            ui.label(f"感情: {emotion}").style(
                                "color:#90caf9; font-size:12px; margin-top:4px"
                            )

            status_label.text = f"{len(memories)} 件の記憶"

        except Exception as e:
            status_label.text = f"エラー: {e}"

    return dialog, open_dialog
