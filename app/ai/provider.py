"""Provider-neutral interfaces for AURA's AI layer.

No concrete model or vendor SDK is imported here. Implementations can be
added later without changing the assistant core.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, Sequence

if TYPE_CHECKING:
    from app.tools.contracts import ToolDefinition


class ProviderError(Exception):
    """Base class for expected provider failures safe to show to users."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is not configured for use."""


class ProviderRequestError(ProviderError):
    """Raised when a provider request or response cannot be completed."""


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
class ToolCallRequest:
    """Provider-neutral request for one registered AURA tool."""

    name: str
    arguments: Mapping[str, object]
    call_id: str | None = None

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if not normalized_name:
            raise ValueError("Tool call name must not be empty")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("Tool call arguments must be an object")
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "arguments", dict(self.arguments))
        if self.call_id is not None:
            normalized_call_id = self.call_id.strip()
            object.__setattr__(
                self,
                "call_id",
                normalized_call_id or None,
            )


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Provider-neutral response containing text or one requested tool call."""

    message: ChatMessage | None = None
    tool_call: ToolCallRequest | None = None
    finish_reason: str | None = None

    def __post_init__(self) -> None:
        if (self.message is None) == (self.tool_call is None):
            raise ValueError(
                "ProviderResponse must contain exactly one message or tool_call"
            )


class AIProvider(Protocol):
    """Minimal contract that every AURA AI provider must implement."""

    @property
    def name(self) -> str:
        """Return a stable, human-readable provider identifier."""
        ...

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tool_definitions: Sequence[ToolDefinition] = (),
    ) -> ProviderResponse:
        """Generate a response for a conversation and optional registered tools."""
        ...
