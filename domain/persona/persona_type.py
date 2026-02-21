"""PersonaType enum - supported AI personality modes."""
from enum import Enum


class PersonaType(str, Enum):
    """Available AI persona configurations.

    Each persona has a distinct system instruction, tone, and interaction style.
    """
    BRIGHT_FRIEND = "bright_friend"
    GENTLE_TEACHER = "gentle_teacher"
    MEAN_NEIGHBOR = "mean_neighbor"
    STUPID_DOG = "stupid_dog"
    LOVER_MALE = "lover_male"
    LOVER_FEMALE = "lover_female"

    @classmethod
    def from_string(cls, value: str) -> "PersonaType":
        """Parse a persona string; falls back to BRIGHT_FRIEND on unknown values."""
        try:
            return cls(value)
        except ValueError:
            return cls.BRIGHT_FRIEND
