"""Persona entity - AI personality configuration."""
from dataclasses import dataclass

from .persona_type import PersonaType


@dataclass
class Persona:
    """Represents the configuration for a specific AI personality.

    Encapsulates the persona type, system instruction, and voice settings
    so the presentation and application layers don't need to know the details.
    """
    persona_type: PersonaType
    system_instruction: str
    voice_name: str = "Zephyr"

    @classmethod
    def create(
        cls,
        persona_type_str: str,
        system_instruction: str,
        voice_name: str = "Zephyr",
    ) -> "Persona":
        return cls(
            persona_type=PersonaType.from_string(persona_type_str),
            system_instruction=system_instruction,
            voice_name=voice_name,
        )

    @property
    def name(self) -> str:
        """Return the persona identifier string."""
        return self.persona_type.value
