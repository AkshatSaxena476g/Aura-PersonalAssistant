import logging
from types import SimpleNamespace

import pytest

from app.ai import (
    ChatMessage,
    GeminiProvider,
    MessageRole,
    ProviderConfigurationError,
    ProviderRequestError,
)
from app.tools import ToolDefinition, ToolPermission


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


def test_gemini_provider_logs_exception_type_and_redacts_api_key(caplog) -> None:
    client = FakeClient(error=RuntimeError("test-key must not be logged"))
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    with caplog.at_level(logging.ERROR, logger="app.ai.gemini_provider"):
        with pytest.raises(ProviderRequestError):
            provider.complete([ChatMessage(MessageRole.USER, "Hello")])

    assert "exception_type=RuntimeError" in caplog.text
    assert "[REDACTED]" in caplog.text
    assert "test-key must not be logged" not in caplog.text


def test_gemini_provider_translates_registered_tool_definition_and_call() -> None:
    client = FakeClient(
        response=SimpleNamespace(
            text="",
            function_calls=[
                SimpleNamespace(
                    name="launch_application",
                    args={"application": "calculator"},
                    id="call-1",
                )
            ],
        )
    )
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)
    definition = ToolDefinition(
        name="launch_application",
        description="Launch an approved application.",
        permission=ToolPermission.CONFIRMATION_REQUIRED,
        input_schema={
            "type": "object",
            "properties": {
                "application": {
                    "type": "string",
                    "enum": ["calculator"],
                }
            },
            "required": ["application"],
            "additionalProperties": False,
        },
    )

    result = provider.complete(
        [ChatMessage(MessageRole.USER, "Open Calculator")],
        tool_definitions=[definition],
    )

    tool_call = result.tool_call
    assert tool_call.name == "launch_application"
    assert tool_call.arguments == {"application": "calculator"}
    assert tool_call.call_id == "call-1"
    config = client.models.calls[0]["config"]
    declaration = config.tools[0].function_declarations[0]
    assert declaration.name == "launch_application"
    assert declaration.parameters_json_schema["required"] == ["application"]
    assert config.automatic_function_calling.disable is True


def test_gemini_provider_rejects_malformed_tool_call() -> None:
    client = FakeClient(
        response=SimpleNamespace(
            text="",
            function_calls=[SimpleNamespace(name="launch_application", args=None)],
        )
    )
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    with pytest.raises(ProviderRequestError, match="malformed tool arguments"):
        provider.complete([ChatMessage(MessageRole.USER, "Open Calculator")])


def test_gemini_provider_rejects_empty_conversation() -> None:
    client = FakeClient(response=SimpleNamespace(text="unused"))
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    with pytest.raises(ProviderRequestError, match="at least one message"):
        provider.complete([])


class FakeQuotaError(Exception):
    code = 429
    status = "RESOURCE_EXHAUSTED"


def test_gemini_provider_classifies_quota_exhaustion() -> None:
    client = FakeClient(error=FakeQuotaError("quota detail must remain internal"))
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=client)

    with pytest.raises(ProviderRequestError, match="request quota is currently exhausted") as caught:
        provider.complete([ChatMessage(MessageRole.USER, "Hello")])

    assert "quota detail must remain internal" not in str(caught.value)
    assert "network and API configuration" not in str(caught.value)
