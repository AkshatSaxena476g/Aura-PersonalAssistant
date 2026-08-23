from app.ai import ChatMessage, MessageRole, ProviderResponse
from app.config import Settings
from app.core import Application


class FakeProvider:
    name = "fake"

    def complete(self, messages: tuple[ChatMessage, ...]) -> ProviderResponse:
        return ProviderResponse(
            message=ChatMessage(MessageRole.ASSISTANT, "Hello from AURA."),
        )


def test_application_starts_without_concrete_ai_provider() -> None:
    application = Application(settings=Settings.from_environment({}))

    assert application.provider is None
    assert application.send_message("Hello").error_message == (
        "No AI provider is configured for conversation."
    )
    assert application.run() == 0


def test_application_routes_messages_through_conversation_service() -> None:
    application = Application(
        settings=Settings.from_environment(
            {"AURA_AI_PROVIDER": "fake", "AURA_AI_MODEL": "fake-model"}
        ),
        provider=FakeProvider(),
    )

    result = application.send_message("Hello")

    assert result.succeeded is True
    assert result.assistant_message.content == "Hello from AURA."
    assert "gemini" not in application.status_message.lower()
