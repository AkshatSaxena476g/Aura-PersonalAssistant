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
        stt_provider=None,
        tts_provider=None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.provider_error = provider_error
        self.tool_service = tool_service
        self.stt_provider = stt_provider
        self.tts_provider = tts_provider
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
                tool_service=tool_service,
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
        result = self.conversation.send(text)
        self._maybe_speak(result)
        return result

    def transcribe_and_send(
        self, audio_bytes: bytes, sample_rate: int = 16000
    ) -> ConversationResult:
        if not self.settings.voice_enabled:
            return ConversationResult(
                error_message="Voice input is disabled. Enable AURA_VOICE_ENABLED to use Hold to Talk."
            )
        if self.stt_provider is None:
            return ConversationResult(error_message="Voice input is not configured.")
        if self.conversation is None:
            return ConversationResult(
                error_message=self.provider_error
                or "No AI provider is configured for conversation."
            )
        transcription = self.stt_provider.transcribe(
            audio_bytes, sample_rate=sample_rate
        )
        if not transcription.succeeded:
            return ConversationResult(
                error_message=transcription.error_message
                or "Speech recognition failed."
            )
        assert transcription.text is not None
        result = self.conversation.send(transcription.text)
        self._maybe_speak(result)
        return result

    def speak_text(self, text: str):
        if self.tts_provider is None:
            from app.voice.provider import SynthesisResult

            return SynthesisResult.failure(
                "Text-to-speech is not configured.", error_code="tts_unavailable"
            )
        return self.tts_provider.speak(text)

    def _maybe_speak(self, result: ConversationResult) -> None:
        if not self.settings.voice_auto_speak or self.tts_provider is None:
            return
        text = None
        if result.assistant_message is not None:
            text = result.assistant_message.content
        elif result.tool_result is not None:
            text = result.tool_result.message
        if text and text.strip():
            try:
                self.tts_provider.speak(text.strip()[:5000])
            except Exception:
                pass

    def approve_tool_call(self, request_id: str) -> ConversationResult:
        """Approve the exact pending provider-requested tool call."""

        if self.conversation is None:
            return ConversationResult(error_message="No AI conversation is configured.")
        return self.conversation.approve_pending(request_id)

    def cancel_tool_call(self, request_id: str) -> ConversationResult:
        """Cancel the exact pending provider-requested tool call."""

        if self.conversation is None:
            return ConversationResult(error_message="No AI conversation is configured.")
        return self.conversation.cancel_pending(request_id)

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
        for prov in (self.stt_provider, self.tts_provider):
            c = getattr(prov, "close", None)
            if callable(c):
                try:
                    c()
                except Exception:
                    pass
            s = getattr(prov, "stop", None)
            if callable(s):
                try:
                    s()
                except Exception:
                    pass
