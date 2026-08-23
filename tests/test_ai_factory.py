from app.ai import GeminiProvider, create_configured_provider
from app.config import Settings


def test_factory_registers_and_selects_gemini(monkeypatch) -> None:
    monkeypatch.setattr(
        GeminiProvider,
        "__init__",
        lambda self, api_key, model: setattr(self, "model", model),
    )

    settings = Settings.from_environment(
        {
            "AURA_AI_PROVIDER": "gemini",
            "AURA_AI_MODEL": "gemini-test",
            "GEMINI_API_KEY": "test-key",
        }
    )

    provider, error = create_configured_provider(settings)

    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-test"
    assert error is None


def test_factory_returns_safe_error_for_missing_gemini_key() -> None:
    settings = Settings.from_environment({"AURA_AI_PROVIDER": "gemini"})

    provider, error = create_configured_provider(settings)

    assert provider is None
    assert error == "Gemini is not configured because GEMINI_API_KEY is missing."


def test_factory_returns_safe_error_for_unsupported_provider() -> None:
    settings = Settings.from_environment({"AURA_AI_PROVIDER": "unsupported"})

    provider, error = create_configured_provider(settings)

    assert provider is None
    assert error == "The configured AI provider 'unsupported' is not supported."
