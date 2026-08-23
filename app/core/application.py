"""Provider-agnostic AURA application lifecycle and service boundaries."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from app.ai.provider import AIProvider, ChatMessage, MessageRole
from app.config.settings import Settings
from app.tools.contracts import ToolResult

from .conversation import ConversationResult, ConversationService
from .tool_execution import ToolExecutionService

logger = logging.getLogger(__name__)


class Application:
    """Compose AURA core services without depending on a vendor SDK or UI toolkit."""

    def __init__(
        self,
        settings: Settings,
        provider: AIProvider | None = None,
        provider_error: str | None = None,
        tool_service: ToolExecutionService | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.provider_error = provider_error
        self.tool_service = tool_service
        self.conversation = (
            ConversationService(
                provider,
                system_message=ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "You are AURA, a capable, composed, natural, and helpful "
                        "personal desktop assistant. Keep responses concise and clear."
                    ),
                ),
            )
            if provider is not None
            else None
        )

    @property
    def status_message(self) -> str:
        """Return a safe startup status for the desktop UI."""

        if self.conversation is not None:
            return (
                f"AURA is ready to chat using {self.settings.ai_provider} "
                f"({self.settings.ai_model})."
            )
        if self.provider_error:
            return f"AURA is not ready: {self.provider_error}"
        return "AURA is ready, but no AI provider is configured."

    def send_message(self, text: str) -> ConversationResult:
        """Process one text message through the configured conversation service."""

        if self.conversation is None:
            return ConversationResult(
                error_message=self.provider_error
                or "No AI provider is configured for conversation.",
            )
        return self.conversation.send(text)

    def execute_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        confirmed: bool = False,
    ) -> ToolResult:
        """Execute a registered tool through the controlled tool boundary."""

        if self.tool_service is None:
            return ToolResult.failure(
                "No tool execution service is configured.",
                error_code="tools_unavailable",
            )
        return self.tool_service.execute(name, arguments, confirmed=confirmed)

    def run(self, ui_runner: Callable[[], int] | None = None) -> int:
        """Start AURA and optionally hand off to the desktop UI event loop."""

        logger.info(
            "%s initialized (AI provider: %s)",
            self.settings.application_name,
            self.settings.ai_provider,
        )
        if ui_runner is None:
            return 0
        return ui_runner()

    def close(self) -> None:
        """Release provider resources when the application shuts down."""

        close = getattr(self.provider, "close", None)
        if callable(close):
            close()
