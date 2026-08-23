from app.ai import ChatMessage, MessageRole, ProviderRegistry, ProviderResponse


class FakeProvider:
    name = "fake"

    def complete(self, messages: list[ChatMessage]) -> ProviderResponse:
        return ProviderResponse(
            message=ChatMessage(MessageRole.ASSISTANT, f"received {len(messages)}"),
            finish_reason="stop",
        )


def test_provider_registry_constructs_registered_provider() -> None:
    registry = ProviderRegistry()
    registry.register(" Fake ", FakeProvider)

    provider = registry.create("fake")
    response = provider.complete([ChatMessage(MessageRole.USER, "Hello")])

    assert registry.names == ("fake",)
    assert provider.name == "fake"
    assert response.message.content == "received 1"


def test_provider_registry_rejects_duplicate_names() -> None:
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider)

    try:
        registry.register(" FAKE ", FakeProvider)
    except ValueError as error:
        assert "already registered" in str(error)
    else:
        raise AssertionError("duplicate provider registration should fail")


def test_empty_chat_message_is_rejected() -> None:
    try:
        ChatMessage(MessageRole.USER, "   ")
    except ValueError as error:
        assert "must not be empty" in str(error)
    else:
        raise AssertionError("empty chat content should fail")
