from types import SimpleNamespace

import pytest

from app.ai import (
    ChatMessage,
    GeminiProvider,
    MessageRole,
    ProviderConfigurationError,
    ProviderRequestError,
)


class FakeModels:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.models = FakeModels(response=response, error=error)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_gemini_provider_translates_messages_and_response() -> None:
    client = FakeClient(response=SimpleNamespace(text=" Hello from Gemini "))
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    result = provider.complete(
        [
            ChatMessage(MessageRole.SYSTEM, "Be concise."),
            ChatMessage(MessageRole.USER, "Hello"),
            ChatMessage(MessageRole.ASSISTANT, "Hi there."),
        ]
    )

    call = client.models.calls[0]
    contents = call["contents"]
    assert call["model"] == "gemini-test"
    assert len(contents) == 2
    assert contents[0].role == "user"
    assert contents[1].role == "model"
    assert call["config"].system_instruction == "Be concise."
    assert result.message.role == MessageRole.ASSISTANT
    assert result.message.content == "Hello from Gemini"

    provider.close()
    assert client.closed is True


def test_gemini_provider_rejects_missing_api_key() -> None:
    with pytest.raises(ProviderConfigurationError, match="GEMINI_API_KEY"):
        GeminiProvider(api_key=None, model="gemini-test")


def test_gemini_provider_translates_sdk_failure() -> None:
    client = FakeClient(error=RuntimeError("simulated network failure"))
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    with pytest.raises(ProviderRequestError, match="network and API configuration"):
        provider.complete([ChatMessage(MessageRole.USER, "Hello")])


def test_gemini_provider_rejects_empty_conversation() -> None:
    client = FakeClient(response=SimpleNamespace(text="unused"))
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    with pytest.raises(ProviderRequestError, match="at least one message"):
        provider.complete([])
