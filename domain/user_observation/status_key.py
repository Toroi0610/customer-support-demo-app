"""StatusKey value object - short identifier for the user's observed state."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StatusKey:
    """Immutable value object for a camera-detected user status.

    Examples: "smiling", "tired", "away", "working", "eating"
    """
    value: str

    def __str__(self) -> str:
        return self.value

    def changed_from(self, other: "StatusKey") -> bool:
        """Return True if this status differs meaningfully from *other*."""
        return self.value != other.value

    @classmethod
    def unknown(cls) -> "StatusKey":
        return cls(value="unknown")
