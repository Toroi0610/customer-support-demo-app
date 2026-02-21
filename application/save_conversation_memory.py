"""SaveConversationMemoryUseCase - persists a conversation as a memory record."""
import json
import ssl
from typing import List, Protocol, runtime_checkable

import aiohttp
import certifi

from domain.memory.memory_record import MemoryRecord
from domain.memory.memory_repository import MemoryRepository
from .dto import SaveMemoryRequest, SaveMemoryResponse


SUMMARY_SYSTEM_INSTRUCTION = """You are a memory summarizer for an AI companion app.
Given a conversation transcript between a user and an AI companion, generate a concise summary in Japanese.
Respond with ONLY a valid JSON object (no markdown, no code blocks).

Provide:
1. "summary": 100-200 character summary of the key moments in the conversation in Japanese
2. "emotion": The user's dominant emotion during this conversation in Japanese (e.g., "楽しそう", "疲れている", "嬉しそう", "落ち込んでいた", "穏やか")
3. "importance": A float 0.0-1.0 rating how emotionally significant this conversation was (0.0 = routine, 1.0 = very significant)
4. "keywords": Array of 2-5 key topics or themes from the conversation in Japanese"""


@runtime_checkable
class AuthService(Protocol):
    def get_access_token(self) -> str: ...


@runtime_checkable
class EmbeddingService(Protocol):
    async def generate(self, text: str, project_id: str) -> List[float]: ...


class SaveConversationMemoryUseCase:
    """Orchestrates:
      1. Summarising the transcript via Gemini (infrastructure via HTTP)
      2. Generating a semantic embedding (infrastructure via Vertex AI)
      3. Persisting the MemoryRecord (infrastructure via repository)

    Dependencies are injected so each can be swapped in tests or extended.
    """

    def __init__(
        self,
        memory_repository: MemoryRepository,
        auth_service: AuthService,
        embedding_service: EmbeddingService,
    ) -> None:
        self._repo = memory_repository
        self._auth = auth_service
        self._embedding = embedding_service

    async def execute(self, request: SaveMemoryRequest) -> SaveMemoryResponse:
        """Generate a summary and save as a MemoryRecord."""
        summary_data = await self._generate_summary(
            request.transcript,
            request.emotions,
            request.persona,
            request.project_id,
        )
        if not summary_data:
            return SaveMemoryResponse(
                memory_id="",
                summary="",
                success=False,
                error="Failed to generate summary",
            )

        embedding = await self._embedding.generate(
            summary_data.get("summary", ""), request.project_id
        )

        record = MemoryRecord(
            user_id=request.user_id,
            persona=request.persona,
            summary=summary_data.get("summary", ""),
            emotion=summary_data.get("emotion", ""),
            importance=float(summary_data.get("importance", 0.5)),
            keywords=summary_data.get("keywords", []),
        )

        memory_id = await self._repo.save(record, embedding=embedding)
        return SaveMemoryResponse(
            memory_id=memory_id,
            summary=record.summary,
            success=True,
        )

    async def _generate_summary(
        self,
        transcript: list,
        emotions: list,
        persona: str,
        project_id: str,
    ) -> dict:
        """Call Gemini to summarise the transcript into a memory record."""
        token = self._auth.get_access_token()
        if not token:
            return None

        transcript_text = "\n".join(
            f"{t.get('role', 'unknown')}: {t.get('text', '')}"
            for t in transcript
            if t.get("text", "").strip()
        )
        if not transcript_text.strip():
            return None

        emotion_note = (
            f"\n観察された感情イベント: {', '.join(emotions)}" if emotions else ""
        )
        user_prompt = f"以下の会話を要約してください。\n\n{transcript_text}{emotion_note}"

        url = (
            f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/us-central1/publishers/google/models/gemini-2.0-flash:generateContent"
        )
        body = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": SUMMARY_SYSTEM_INSTRUCTION}]},
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    ssl=ssl_context,
                ) as resp:
                    if resp.status != 200:
                        print(f"Summary Gemini API error: {resp.status}")
                        return None
                    result = await resp.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text)
                    if not isinstance(parsed, dict) or "summary" not in parsed:
                        return None
                    return parsed
        except Exception as exc:
            print(f"Error generating summary: {exc}")
            return None
