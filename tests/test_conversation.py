from app.ai import ChatMessage, MessageRole, ProviderRequestError, ProviderResponse
from app.core import ConversationService


class FakeProvider:
    name = "fake"

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[ChatMessage, ...]] = []

    def complete(self, messages: tuple[ChatMessage, ...]) -> ProviderResponse:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return ProviderResponse(
            message=ChatMessage(MessageRole.ASSISTANT, "AURA response"),
            finish_reason="stop",
        )


def test_conversation_service_commits_successful_turn() -> None:
    provider = FakeProvider()
    service = ConversationService(provider)

    result = service.send(" Hello AURA ")

    assert result.succeeded is True
    assert result.user_message.content == "Hello AURA"
    assert result.assistant_message.content == "AURA response"
    assert [message.role for message in service.history] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert provider.calls[0][0].content == "Hello AURA"


def test_conversation_service_does_not_call_provider_for_empty_text() -> None:
    provider = FakeProvider()
    service = ConversationService(provider)

    result = service.send("   ")

    assert result.succeeded is False
    assert result.error_message == "Please enter a message."
    assert provider.calls == []


def test_conversation_service_keeps_failed_turn_out_of_history() -> None:
    provider = FakeProvider(error=ProviderRequestError("temporary failure"))
    service = ConversationService(provider)

    result = service.send("Hello")

    assert result.succeeded is False
    assert result.error_message == "temporary failure"
    assert service.history == ()


def test_conversation_service_hides_unexpected_provider_error() -> None:
    provider = FakeProvider(error=RuntimeError("internal details"))
    service = ConversationService(provider)

    result = service.send("Hello")

    assert result.succeeded is False
    assert result.error_message == (
        "I couldn't complete that request because an unexpected provider error occurred."
    )
    assert "internal details" not in result.error_message
