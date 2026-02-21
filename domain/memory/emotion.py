"""Emotion value object - represents a user's detected emotion (Japanese string)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Emotion:
    """Immutable value object wrapping a Japanese emotion string."""
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str):
            raise ValueError("Emotion value must be a string")

    def __str__(self) -> str:
        return self.value

    def is_empty(self) -> bool:
        return not self.value.strip()

    @classmethod
    def empty(cls) -> "Emotion":
        return cls(value="")
