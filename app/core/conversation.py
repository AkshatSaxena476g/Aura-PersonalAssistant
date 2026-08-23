"""Provider-agnostic text conversation flow for AURA."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from app.ai.provider import (
    AIProvider,
    ChatMessage,
    MessageRole,
    ProviderError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """Structured result for one user turn."""

    user_message: ChatMessage | None = None
    assistant_message: ChatMessage | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the provider produced an assistant response."""

        return self.assistant_message is not None and self.error_message is None


class ConversationService:
    """Keep conversation state while remaining independent from any provider."""

    def __init__(
        self,
        provider: AIProvider,
        *,
        system_message: ChatMessage | None = None,
    ) -> None:
        self.provider = provider
        self._history: list[ChatMessage] = []
        if system_message is not None:
            if system_message.role != MessageRole.SYSTEM:
                raise ValueError("system_message must have the system role")
            self._history.append(system_message)

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        """Return an immutable snapshot of committed conversation messages."""

        return tuple(self._history)

    def send(self, text: str) -> ConversationResult:
        """Send one user message and commit the turn only on success."""

        if not text.strip():
            return ConversationResult(error_message="Please enter a message.")

        user_message = ChatMessage(MessageRole.USER, text.strip())
        candidate_history = (*self._history, user_message)
        try:
            response = self.provider.complete(candidate_history)
        except ProviderError as error:
            return ConversationResult(
                user_message=user_message,
                error_message=str(error),
            )
        except Exception:
            logger.error("Unexpected conversation provider error")
            return ConversationResult(
                user_message=user_message,
                error_message=(
                    "I couldn't complete that request because an unexpected provider "
                    "error occurred."
                ),
            )

        self._history.extend((user_message, response.message))
        return ConversationResult(
            user_message=user_message,
            assistant_message=response.message,
        )
