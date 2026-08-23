"""Provider-neutral interfaces for AURA's AI layer.

No concrete model or vendor SDK is imported here. Implementations can be
added later without changing the assistant core.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, Sequence


class MessageRole(StrEnum):
    """Roles supported by the provider-neutral conversation format."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A single message exchanged with an AI provider."""

    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("ChatMessage content must not be empty")


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Provider-neutral response returned to the assistant core."""

    message: ChatMessage
    finish_reason: str | None = None


class AIProvider(Protocol):
    """Minimal contract that every AURA AI provider must implement."""

    @property
    def name(self) -> str:
        """Return a stable, human-readable provider identifier."""
        ...

    def complete(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
        """Generate a response for a conversation."""
        ...
