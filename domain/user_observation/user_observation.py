"""UserObservation entity - the result of a single video frame analysis."""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .emotion_level import EmotionLevel
from .status_key import StatusKey


@dataclass
class UserObservation:
    """Represents what the AI observed from one camera frame.

    Produced by the AnalyzeUserStateUseCase and consumed by the
    speech-decision logic to decide whether the AI should proactively speak.
    """
    observation: str          # Free-text description in Japanese
    status_key: StatusKey     # Short stable key (smiling, tired, away …)
    emotion: str              # Detected emotion label in Japanese
    details: str              # Comma-separated notable items in Japanese
    significant_change: bool  # True if meaningfully different from previous
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def is_significant(self) -> bool:
        return self.significant_change

    @classmethod
    def from_api_response(cls, data: dict) -> "UserObservation":
        """Build from the raw JSON returned by the frame-analysis endpoint."""
        return cls(
            observation=data.get("observation", ""),
            status_key=StatusKey(value=data.get("status_key", "unknown")),
            emotion=data.get("emotion", ""),
            details=data.get("details", ""),
            significant_change=bool(data.get("significant_change", False)),
        )

    def to_dict(self) -> dict:
        return {
            "observation": self.observation,
            "status_key": str(self.status_key),
            "emotion": self.emotion,
            "details": self.details,
            "significant_change": self.significant_change,
        }
