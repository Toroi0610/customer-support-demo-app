"""VertexAIEmbeddingService - generates text embeddings via Vertex AI."""
import ssl
from typing import List

import aiohttp
import certifi

from .google_auth import GoogleAuthService


class VertexAIEmbeddingService:
    """Calls Vertex AI text-embedding-004 to produce 768-dimensional vectors.

    Used by SaveConversationMemoryUseCase to embed memory summaries for
    semantic search in ChromaDB.
    """

    MODEL = "text-embedding-004"

    def __init__(self, auth_service: GoogleAuthService = None) -> None:
        self._auth = auth_service or GoogleAuthService()

    async def generate(self, text: str, project_id: str) -> List[float]:
        """Return a 768-dim embedding vector, or [] on failure."""
        token = self._auth.get_access_token()
        if not token or not project_id:
            return []

        url = (
            f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/us-central1/publishers/google/models/{self.MODEL}:predict"
        )
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"instances": [{"content": text}]},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    ssl=ssl_context,
                ) as resp:
                    if resp.status != 200:
                        print(f"Embedding API error: {resp.status}")
                        return []
                    data = await resp.json()
                    return data["predictions"][0]["embeddings"]["values"]
        except Exception as exc:
            print(f"Error generating embedding: {exc}")
            return []
