"""Data Transfer Objects for the application layer.

DTOs cross layer boundaries and carry only plain data — no domain logic.
"""
from dataclasses import dataclass, field
from typing import List, Optional


# ── Memory DTOs ────────────────────────────────────────────────────────────────

@dataclass
class MemoryDTO:
    """Serializable representation of a memory record."""
    summary: str
    emotion: str
    importance: float
    days_ago: int
    timestamp: str = ""
    relevance: Optional[float] = None


@dataclass
class SaveMemoryRequest:
    """Input for SaveConversationMemoryUseCase."""
    user_id: str
    persona: str
    transcript: List[dict]   # list of {role, text} dicts
    emotions: List[str]
    project_id: str


@dataclass
class SaveMemoryResponse:
    """Output from SaveConversationMemoryUseCase."""
    memory_id: str
    summary: str
    success: bool = True
    error: str = ""


@dataclass
class RecallMemoriesRequest:
    """Input for RecallMemoriesUseCase."""
    user_id: str
    persona: str
    context: str = ""
    project_id: str = ""
    limit: int = 3


# ── Frame Analysis DTOs ────────────────────────────────────────────────────────

@dataclass
class AnalyzeFrameRequest:
    """Input for AnalyzeUserStateUseCase."""
    image_base64: str
    project_id: str
    previous_status: str = ""
    model: str = "gemini-2.0-flash"


@dataclass
class AnalyzeFrameResponse:
    """Output from AnalyzeUserStateUseCase."""
    observation: str
    status_key: str
    emotion: str
    details: str
    significant_change: bool
    success: bool = True
    error: str = ""
