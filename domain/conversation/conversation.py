"""Conversation aggregate - manages the session transcript and emotion events."""
from datetime import datetime, timezone
from typing import List

from .message import Message, MessageRole


class Conversation:
    """Aggregate root for a single conversation session.

    Holds the ordered list of messages and any observed emotion events
    that occurred during the session.
    """

    def __init__(self) -> None:
        self.messages: List[Message] = []
        self.emotion_events: List[str] = []
        self.started_at: datetime = datetime.now(timezone.utc)

    def add_message(self, role: str, text: str) -> Message:
        """Append a message and return the new Message entity."""
        message = Message(role=role, text=text)
        if not message.is_empty():
            self.messages.append(message)
        return message

    def add_emotion_event(self, emotion: str) -> None:
        """Record an observed user emotion during the session."""
        if emotion:
            self.emotion_events.append(emotion)

    def get_transcript(self) -> List[dict]:
        """Return transcript as a list of plain dicts for serialization."""
        return [m.to_dict() for m in self.messages]

    def is_empty(self) -> bool:
        return len(self.messages) == 0

    @property
    def message_count(self) -> int:
        return len(self.messages)
