"""MemoryRepository - abstract repository interface (port) for memory persistence."""
from abc import ABC, abstractmethod
from typing import List

from .memory_record import MemoryRecord


class MemoryRepository(ABC):
    """Defines the contract for memory storage.

    Concrete implementations live in the infrastructure layer.
    This interface keeps the domain decoupled from persistence technology.
    """

    @abstractmethod
    async def save(self, record: MemoryRecord, embedding: List[float] = None) -> str:
        """Persist a memory record. Returns the memory_id."""
        ...

    @abstractmethod
    async def recall(
        self,
        user_id: str,
        persona: str,
        context: str = "",
        project_id: str = "",
        limit: int = 3,
    ) -> List[MemoryRecord]:
        """Retrieve semantically relevant memories. Falls back to recency."""
        ...

    @abstractmethod
    async def list_recent(
        self,
        user_id: str,
        persona: str,
        limit: int = 10,
    ) -> List[MemoryRecord]:
        """List memories sorted by timestamp descending (newest first)."""
        ...

    @abstractmethod
    async def search(
        self,
        user_id: str,
        persona: str,
        query: str,
        project_id: str = "",
        limit: int = 5,
    ) -> List[MemoryRecord]:
        """Search memories semantically, returning relevance scores."""
        ...

    @abstractmethod
    async def get_stats(self, user_id: str, persona: str) -> dict:
        """Return aggregate statistics: total, emotion breakdown, avg importance."""
        ...
