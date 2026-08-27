"""Provider-agnostic text conversation and controlled tool-call flow for AURA."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.ai.provider import (
    AIProvider,
    ChatMessage,
    MessageRole,
    ProviderError,
    ToolCallRequest,
)
from app.tools.contracts import ToolResult

from .tool_execution import PreparedToolCall, ToolExecutionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """Structured result for one user turn or one tool action."""

    user_message: ChatMessage | None = None
    assistant_message: ChatMessage | None = None
    tool_result: ToolResult | None = None
    pending_tool: "PendingToolRequest | None" = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether a normal assistant response was produced."""

        return self.assistant_message is not None and self.error_message is None

    @property
    def requires_confirmation(self) -> bool:
        """Return whether the UI must obtain approval before execution."""

        return self.pending_tool is not None


@dataclass(frozen=True, slots=True)
class PendingToolRequest:
    """A specific validated request awaiting one user decision."""

    request_id: str
    user_message: ChatMessage
    call: PreparedToolCall
    confirmation_message: str


class ConversationService:
    """Keep conversation state and route provider tool calls through execution."""

    def __init__(
        self,
        provider: AIProvider,
        *,
        system_message: ChatMessage | None = None,
        tool_service: ToolExecutionService | None = None,
    ) -> None:
        self.provider = provider
        self.tool_service = tool_service
        self._history: list[ChatMessage] = []
        self._pending_tool: PendingToolRequest | None = None
        self._completed_request_ids: set[str] = set()
        if system_message is not None:
            if system_message.role != MessageRole.SYSTEM:
                raise ValueError("system_message must have the system role")
            self._history.append(system_message)

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        """Return an immutable snapshot of committed conversation messages."""

        return tuple(self._history)

    @property
    def pending_tool(self) -> PendingToolRequest | None:
        """Return the current confirmation request, if one is awaiting approval."""

        return self._pending_tool

    def available_tool_definitions(self):
        """Derive provider-facing definitions from the current registry only."""

        if self.tool_service is None:
            return ()
        return self.tool_service.registry.definitions()

    def send(self, text: str) -> ConversationResult:
        """Send one user message and handle one provider text or tool-call response."""

        if self._pending_tool is not None:
            return ConversationResult(
                error_message="Please approve or cancel the pending tool action first."
            )
        if not text.strip():
            return ConversationResult(error_message="Please enter a message.")

        user_message = ChatMessage(MessageRole.USER, text.strip())
        candidate_history = (*self._history, user_message)
        try:
            if self.tool_service is None:
                response = self.provider.complete(candidate_history)
            else:
                response = self.provider.complete(
                    candidate_history,
                    tool_definitions=self.available_tool_definitions(),
                )
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

        if response.tool_call is not None:
            return self._prepare_tool_call(user_message, response.tool_call)

        if response.message is None:
            return ConversationResult(
                user_message=user_message,
                error_message="The provider returned no usable response.",
            )

        self._history.extend((user_message, response.message))
        return ConversationResult(
            user_message=user_message,
            assistant_message=response.message,
        )

    def approve_pending(self, request_id: str) -> ConversationResult:
        """Approve and execute the exact pending request at most once."""

        pending = self._pending_tool
        if pending is None or pending.request_id != request_id:
            return ConversationResult(
                tool_result=ToolResult.failure(
                    "That tool confirmation is no longer available.",
                    error_code="stale_confirmation",
                )
            )

        self._pending_tool = None
        self._completed_request_ids.add(request_id)
        assert self.tool_service is not None
        result = self.tool_service.execute_prepared(pending.call, confirmed=True)
        self._commit_tool_result(pending.user_message, result)
        return ConversationResult(tool_result=result)

    def cancel_pending(self, request_id: str) -> ConversationResult:
        """Cancel the exact pending request and prevent later duplicate approval."""

        pending = self._pending_tool
        if pending is None or pending.request_id != request_id:
            return ConversationResult(
                tool_result=ToolResult.failure(
                    "That tool confirmation is no longer available.",
                    error_code="stale_confirmation",
                )
            )

        self._pending_tool = None
        self._completed_request_ids.add(request_id)
        result = ToolResult.failure(
            "Tool action cancelled.",
            error_code="cancelled",
        )
        self._commit_tool_result(pending.user_message, result)
        return ConversationResult(tool_result=result)

    def _prepare_tool_call(
        self,
        user_message: ChatMessage,
        request: ToolCallRequest,
    ) -> ConversationResult:
        """Validate provider input and create a pending confirmation when needed."""

        if self.tool_service is None:
            return ConversationResult(
                user_message=user_message,
                error_message="Tool requests are unavailable.",
            )

        preparation = self.tool_service.prepare(request.name, request.arguments)
        if not preparation.ready:
            assert preparation.failure is not None
            self._commit_tool_result(user_message, preparation.failure)
            return ConversationResult(
                user_message=user_message,
                tool_result=preparation.failure,
            )

        assert preparation.prepared is not None
        if not preparation.prepared.requires_confirmation:
            result = self.tool_service.execute_prepared(
                preparation.prepared,
                confirmed=True,
            )
            self._commit_tool_result(user_message, result)
            return ConversationResult(
                user_message=user_message,
                tool_result=result,
            )

        request_id = request.call_id or uuid4().hex
        if request_id in self._completed_request_ids:
            return ConversationResult(
                user_message=user_message,
                tool_result=ToolResult.failure(
                    "This tool request has already been handled.",
                    error_code="duplicate_request",
                ),
            )

        pending = PendingToolRequest(
            request_id=request_id,
            user_message=user_message,
            call=preparation.prepared,
            confirmation_message=self._confirmation_message(preparation.prepared),
        )
        self._pending_tool = pending
        return ConversationResult(
            user_message=user_message,
            pending_tool=pending,
        )

    def _commit_tool_result(
        self,
        user_message: ChatMessage,
        result: ToolResult,
    ) -> None:
        """Record a local tool outcome as the assistant side of the completed turn."""

        assistant_message = ChatMessage(MessageRole.ASSISTANT, result.message)
        self._history.extend((user_message, assistant_message))

    @staticmethod
    def _confirmation_message(prepared: PreparedToolCall) -> str:
        """Build a concise approval prompt without exposing raw system details."""

        if prepared.name == "launch_application":
            application = prepared.arguments.get("application", "application")
            labels = {
                "notepad": "Notepad",
                "calculator": "Calculator",
                "settings": "Windows Settings",
                "file_explorer": "File Explorer",
            }
            display_name = labels.get(str(application), "this application")
            return f"I can open {display_name}. Do you want me to proceed?"
        if prepared.name == "create_directory":
            location = prepared.arguments.get("location", "location")
            path = prepared.arguments.get("path", "directory")
            return f"I can create the directory '{path}' in {location}. Do you want me to proceed?"
        if prepared.name == "write_text_file":
            location = prepared.arguments.get("location", "location")
            path = prepared.arguments.get("path", "file")
            return f"I can write to '{path}' in {location}. Do you want me to proceed?"
        return f"AURA is ready to run {prepared.name}. Do you want me to proceed?"
