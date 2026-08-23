"""Gemini implementation of AURA's provider-neutral AI contract."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from google import genai
from google.genai import types

from .provider import (
    AIProvider,
    ChatMessage,
    MessageRole,
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderResponse,
)

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Synchronous text provider backed by Google's official GenAI SDK."""

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

    def complete(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
        """Send the conversation to Gemini and return a normalized response."""

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
                    "Tool messages are not supported during text conversation."
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

        config = None
        if system_instructions:
            config = types.GenerateContentConfig(
                system_instruction="\n\n".join(system_instructions),
            )

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            response_text = (response.text or "").strip()
        except Exception:
            logger.error("Gemini request failed")
            raise ProviderRequestError(
                "Gemini could not complete the request. Check your network and API configuration."
            ) from None

        if not response_text:
            raise ProviderRequestError("Gemini returned an empty response.")

        return ProviderResponse(
            message=ChatMessage(MessageRole.ASSISTANT, response_text),
            finish_reason=None,
        )

    def close(self) -> None:
        """Release the SDK client's network resources when supported."""

        close = getattr(self._client, "close", None)
        if callable(close):
            close()


assert isinstance(GeminiProvider.name, str)
