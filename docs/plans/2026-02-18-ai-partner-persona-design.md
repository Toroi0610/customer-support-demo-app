# AI Partner Persona Design

**Date:** 2026-02-18
**Status:** Approved

## Goal

Transform the app from a customer support demo into an AI partner experience with:
1. AI-partner-appropriate UI text
2. Three selectable personas with distinct system prompts
3. New emotion-reaction tools replacing customer support tools
4. Mobile-responsive layout

---

## Architecture

**Changed files:**
- `src/components/LiveAPIDemo.jsx` — UI text, persona selection state, tool wiring
- `src/utils/tools.js` — new tool definitions
- `src/components/LiveAPIDemo.css` — mobile responsive CSS

---

## Persona System

### Selection UI
- Location: inside 設定 ▾ dropdown, before connecting
- Control: radio buttons or select (disabled while connected)
- Default: 明るい友達

### Personas

| Persona | Key | Personality | Tools |
|---|---|---|---|
| 😊 明るい友達 | `bright_friend` | Energetic, casual, high-energy | `report_visual_state`, `celebrate_moment`, `offer_support` |
| 📖 優しい先生 | `gentle_teacher` | Warm, patient, educational | `report_visual_state`, `offer_support` |
| 😠 意地悪な隣人 | `mean_neighbor` | Sarcastic, grumpy, reluctantly caring | `report_visual_state`, `celebrate_moment` |

### System Prompt Structure
- All personas share the camera-monitoring behavior (`report_visual_state`)
- Unused tools are omitted from each persona's system prompt
- Tone and wording are clearly distinct per persona
- Language: Japanese default, matches user if they switch

---

## New Tools

### `celebrate_moment`
- **Trigger:** AI judges user is happy, excited, or achieved something
- **Parameter:** `message` (string) — a celebratory phrase
- **UI:** 🎉 animated card in chat area

### `offer_support`
- **Trigger:** AI judges user is sad, tired, or stressed
- **Parameter:** `message` (string) — a supportive phrase
- **UI:** 💙 support card in chat area

### Removed Tools
- `process_refund` — customer support specific, removed
- `connect_to_human` — customer support specific, removed

---

## UI Text Changes

| Location | Before | After |
|---|---|---|
| Toolbar h1 | カスタマーサポート | AIパートナー |
| Info panel intro | 次世代カスタマーサポート... | AI パートナーと一緒に... |
| Info panel items | 返金・担当者接続 | 感情認識・寄り添い・祝福 |
| Empty state | 接続してサポートとチャットを開始 | 接続してAIパートナーと話しかけてみましょう |

---

## Mobile Responsive

**Breakpoint:** 768px

| Element | Desktop | Mobile |
|---|---|---|
| Toolbar | horizontal flex | vertical stack |
| Info panel | visible, side-by-side with chat | hidden (collapsed) |
| Chat section | partial width | full width |
| Dropdown | fixed width | screen-width constrained |
