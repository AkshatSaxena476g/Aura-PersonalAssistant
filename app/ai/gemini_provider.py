"""Gemini implementation of AURA's provider-neutral AI contract."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from google import genai
from google.genai import types

from app.tools.contracts import ToolDefinition

from .provider import (
    AIProvider,
    ChatMessage,
    MessageRole,
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderResponse,
    ToolCallRequest,
)

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Synchronous text and manual-tool-call provider using Google's GenAI SDK."""

    name = "gemini"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        *,
        client: genai.Client | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ProviderConfigurationError(
                "Gemini is not configured because GEMINI_API_KEY is missing."
            )
        if not model or not model.strip():
            raise ProviderConfigurationError(
                "Gemini is not configured because AURA_AI_MODEL is missing."
            )

        self.model = model.strip()
        self._credential_for_redaction = api_key.strip()
        if client is not None:
            self._client = client
        else:
            try:
                self._client = genai.Client(api_key=api_key.strip())
            except Exception as error:
                del error
                raise ProviderConfigurationError(
                    "Gemini could not be initialized. Check the API configuration."
                ) from None

    @staticmethod
    def _function_tools(
        tool_definitions: Sequence[ToolDefinition],
    ) -> list[types.Tool]:
        """Translate registered AURA definitions into SDK declarations."""

        if not tool_definitions:
            return []
        declarations = [
            types.FunctionDeclaration(
                name=definition.name,
                description=definition.description,
                parameters_json_schema=dict(definition.input_schema),
            )
            for definition in tool_definitions
        ]
        return [types.Tool(function_declarations=declarations)]

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tool_definitions: Sequence[ToolDefinition] = (),
    ) -> ProviderResponse:
        """Send text and registered tool declarations, returning text or one call."""

        if not messages:
            raise ProviderRequestError("Gemini requires at least one message.")

        system_instructions: list[str] = []
        contents: list[types.Content] = []
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                system_instructions.append(message.content)
                continue
            if message.role == MessageRole.TOOL:
                raise ProviderRequestError(
                    "Tool result messages are not supported in this conversation flow."
                )

            sdk_role = "model" if message.role == MessageRole.ASSISTANT else "user"
            contents.append(
                types.Content(
                    role=sdk_role,
                    parts=[types.Part.from_text(text=message.content)],
                )
            )

        if not contents:
            raise ProviderRequestError("Gemini requires user or assistant content.")

        function_tools = self._function_tools(tool_definitions)
        config_kwargs: dict[str, object] = {}
        if system_instructions:
            config_kwargs["system_instruction"] = "\n\n".join(system_instructions)
        if function_tools:
            config_kwargs["tools"] = function_tools
            config_kwargs["automatic_function_calling"] = (
                types.AutomaticFunctionCallingConfig(disable=True)
            )
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except Exception as error:
            logger.error(
                "Gemini request failed (exception_type=%s, detail=%s)",
                type(error).__name__,
                self._safe_error_detail(error),
            )
            if self._is_quota_exhausted(error):
                raise ProviderRequestError(
                    "Gemini request quota is currently exhausted for the configured model. "
                    "Please retry after the quota resets or check the Gemini API usage and billing settings."
                ) from None
            raise ProviderRequestError(
                "Gemini could not complete the request. Check your network and API configuration."
            ) from None

        raw_function_calls = getattr(response, "function_calls", None) or []
        if raw_function_calls:
            return self._translate_function_call(raw_function_calls[0])

        try:
            response_text = (response.text or "").strip()
        except Exception:
            response_text = ""
        if not response_text:
            raise ProviderRequestError("Gemini returned an empty response.")

        return ProviderResponse(
            message=ChatMessage(MessageRole.ASSISTANT, response_text),
            finish_reason=None,
        )

    @staticmethod
    def _is_quota_exhausted(error: Exception) -> bool:
        """Recognize an SDK/API response that explicitly indicates HTTP 429 quota exhaustion."""

        code = getattr(error, "code", None)
        status = getattr(error, "status", None)
        return code == 429 or status == "RESOURCE_EXHAUSTED"

    def _safe_error_detail(self, error: Exception) -> str:
        """Return bounded exception detail with the configured key redacted."""

        detail = str(error).replace(self._credential_for_redaction, "[REDACTED]")
        return detail[:500] or "(no exception detail)"

    @staticmethod
    def _translate_function_call(raw_call: object) -> ProviderResponse:
        """Convert one SDK call object into AURA's neutral call representation."""

        name = getattr(raw_call, "name", None)
        arguments = getattr(raw_call, "args", None)
        call_id = getattr(raw_call, "id", None)
        if not isinstance(name, str) or not name.strip():
            raise ProviderRequestError("Gemini returned a malformed tool call.")
        if not isinstance(arguments, Mapping):
            raise ProviderRequestError("Gemini returned malformed tool arguments.")

        try:
            request = ToolCallRequest(
                name=name,
                arguments=dict(arguments),
                call_id=call_id if isinstance(call_id, str) else None,
            )
        except (TypeError, ValueError):
            raise ProviderRequestError("Gemini returned a malformed tool call.") from None
        return ProviderResponse(tool_call=request)

    def close(self) -> None:
        """Release the SDK client's network resources when supported."""

        close = getattr(self._client, "close", None)
        if callable(close):
            close()


assert isinstance(GeminiProvider.name, str)
