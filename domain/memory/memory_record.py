"""MemoryRecord entity - a stored conversation summary."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
import uuid


@dataclass
class MemoryRecord:
    """Entity representing a summarized conversation memory.

    Stored per user+persona pair. Importance ranges 0.0 (routine) to 1.0 (very significant).
    """
    user_id: str
    persona: str
    summary: str
    emotion: str
    importance: float
    keywords: List[str]
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    days_ago: int = 0
    relevance: float = None  # Populated only during semantic search

    def __post_init__(self):
        if not self.user_id:
            raise ValueError("user_id is required")
        if not self.persona:
            raise ValueError("persona is required")
        if not self.summary:
            raise ValueError("summary is required")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(
                f"importance must be between 0.0 and 1.0, got {self.importance}"
            )

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "emotion": self.emotion,
            "importance": self.importance,
            "days_ago": self.days_ago,
            "timestamp": self.timestamp,
        }
