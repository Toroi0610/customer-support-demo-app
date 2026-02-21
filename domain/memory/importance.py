"""Importance value object - emotional significance rating from 0.0 to 1.0."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Importance:
    """Immutable value object for memory importance (0.0 = routine, 1.0 = very significant)."""
    value: float

    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(
                f"Importance must be between 0.0 and 1.0, got {self.value}"
            )

    def __float__(self) -> float:
        return self.value

    @classmethod
    def default(cls) -> "Importance":
        return cls(value=0.5)

    @classmethod
    def high(cls) -> "Importance":
        return cls(value=1.0)

    @classmethod
    def low(cls) -> "Importance":
        return cls(value=0.0)
