"""EmotionLevel enum - urgency classification of detected user emotions."""
from enum import Enum


class EmotionLevel(str, Enum):
    """Classifies how urgently the AI should respond to a detected emotion.

    HIGH   - Speak immediately (sad, angry, distressed).
    MEDIUM - Speak only after consecutive detections.
    LOW    - Speak at periodic intervals (normal, focused, happy).
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_string(cls, value: str) -> "EmotionLevel":
        try:
            return cls(value.upper())
        except (ValueError, AttributeError):
            return cls.LOW
