"""MemoryFormatService - domain service for rendering memories into prompt text."""
from typing import List

from .memory_record import MemoryRecord


class MemoryFormatService:
    """Converts memory records into a structured Japanese prompt block.

    This is a pure domain service: it has no external dependencies
    and contains only business formatting rules.
    """

    def format_for_prompt(self, memories: List[MemoryRecord]) -> str:
        """Build a [過去の記憶] block from a list of memory records.

        Returns an empty string when memories is empty.
        """
        if not memories:
            return ""

        lines = ["[過去の記憶]"]
        for m in memories:
            when = self._days_label(m.days_ago)
            line = (
                f"- {when}: {m.summary}"
                f"（感情: {m.emotion}、重要度: {m.importance:.1f}）"
            )
            lines.append(line)
        return "\n".join(lines)

    def inject_into_session(
        self, session_data: dict, memories: List[MemoryRecord]
    ) -> None:
        """Append the formatted memory block to the session system_instruction in-place.

        No-op when memories is empty or session_data lacks the expected structure.
        """
        if not memories:
            return
        try:
            parts = session_data["setup"]["system_instruction"]["parts"]
            memory_block = self.format_for_prompt(memories)
            if memory_block:
                parts[0]["text"] = parts[0]["text"] + "\n\n" + memory_block
        except (KeyError, IndexError, TypeError):
            return

    @staticmethod
    def _days_label(days: int) -> str:
        if days == 0:
            return "今日"
        if days == 1:
            return "昨日"
        return f"{days}日前"
