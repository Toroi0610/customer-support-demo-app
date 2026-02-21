"""AnalyzeUserStateUseCase - processes a video frame and returns an observation."""
import json
import ssl
from typing import Protocol, runtime_checkable

import aiohttp
import certifi

from domain.user_observation.user_observation import UserObservation
from .dto import AnalyzeFrameRequest, AnalyzeFrameResponse


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


@runtime_checkable
class AuthService(Protocol):
    def get_access_token(self) -> str: ...


class AnalyzeUserStateUseCase:
    """Sends a base64-encoded JPEG frame to Gemini Vision and returns an observation.

    Dependencies:
        auth_service - provides Google Cloud access tokens (infrastructure)
    """

    def __init__(self, auth_service: AuthService) -> None:
        self._auth = auth_service

    async def execute(self, request: AnalyzeFrameRequest) -> AnalyzeFrameResponse:
        """Analyse a single video frame and return the structured observation."""
        token = self._auth.get_access_token()
        if not token:
            return AnalyzeFrameResponse(
                observation="",
                status_key="",
                emotion="",
                details="",
                significant_change=False,
                success=False,
                error="Authentication failed",
            )

        user_prompt = (
            f"Analyze this image. Previous status_key was: '{request.previous_status}'. "
            "Compare with current state."
            if request.previous_status
            else "Analyze this image. This is the first frame being analyzed."
        )

        api_url = (
            f"https://us-central1-aiplatform.googleapis.com/v1/projects/{request.project_id}"
            f"/locations/us-central1/publishers/google/models/{request.model}:generateContent"
        )
        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": request.image_base64,
                            }
                        },
                        {"text": user_prompt},
                    ],
                }
            ],
            "systemInstruction": {"parts": [{"text": ANALYSIS_SYSTEM_INSTRUCTION}]},
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
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
                        return AnalyzeFrameResponse(
                            observation="",
                            status_key="",
                            emotion="",
                            details="",
                            significant_change=False,
                            success=False,
                            error=f"Gemini API error: {resp.status}",
                        )
                    result = await resp.json()

            text = result["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            obs = UserObservation.from_api_response(data)
            return AnalyzeFrameResponse(
                observation=obs.observation,
                status_key=str(obs.status_key),
                emotion=obs.emotion,
                details=obs.details,
                significant_change=obs.significant_change,
            )
        except Exception as exc:
            print(f"Error analyzing frame: {exc}")
            return AnalyzeFrameResponse(
                observation="",
                status_key="",
                emotion="",
                details="",
                significant_change=False,
                success=False,
                error=str(exc),
            )
