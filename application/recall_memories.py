"""RecallMemoriesUseCase - retrieves past memories for session context injection."""
from typing import List

from domain.memory.memory_repository import MemoryRepository
from domain.memory.memory_format_service import MemoryFormatService
from .dto import RecallMemoriesRequest, MemoryDTO


class RecallMemoriesUseCase:
    """Orchestrates fetching and formatting relevant memories before a session.

    Dependencies:
        memory_repository  - data access (infrastructure)
        format_service     - prompt formatting (domain service)
    """

    def __init__(
        self,
        memory_repository: MemoryRepository,
        format_service: MemoryFormatService = None,
    ) -> None:
        self._repo = memory_repository
        self._fmt = format_service or MemoryFormatService()

    async def execute(self, request: RecallMemoriesRequest) -> List[MemoryDTO]:
        """Return a list of relevant MemoryDTOs for the given user+persona."""
        records = await self._repo.recall(
            user_id=request.user_id,
            persona=request.persona,
            context=request.context,
            project_id=request.project_id,
            limit=request.limit,
        )
        return [
            MemoryDTO(
                summary=r.summary,
                emotion=r.emotion,
                importance=r.importance,
                days_ago=r.days_ago,
                timestamp=r.timestamp,
            )
            for r in records
        ]

    async def inject_into_session(
        self,
        request: RecallMemoriesRequest,
        session_data: dict,
    ) -> int:
        """Fetch memories and inject them into the session setup message in-place.

        Returns the number of memories injected.
        """
        records = await self._repo.recall(
            user_id=request.user_id,
            persona=request.persona,
            context=request.context,
            project_id=request.project_id,
            limit=request.limit,
        )
        if records:
            self._fmt.inject_into_session(session_data, records)
        return len(records)
