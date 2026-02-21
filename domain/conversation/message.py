"""Message entity - represents a single turn in a conversation."""
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """Participant roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    UNKNOWN = "unknown"


@dataclass
class Message:
    """Represents a single message in a conversation."""
    role: MessageRole
    text: str

    def __post_init__(self):
        if isinstance(self.role, str):
            try:
                self.role = MessageRole(self.role)
            except ValueError:
                self.role = MessageRole.UNKNOWN

    def is_empty(self) -> bool:
        return not self.text.strip()

    def to_dict(self) -> dict:
        return {"role": self.role.value, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(role=data.get("role", "unknown"), text=data.get("text", ""))
