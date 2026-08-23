from pathlib import Path

import pytest

from app.config import Settings


def test_settings_use_safe_foundation_defaults() -> None:
    settings = Settings.from_environment({})

    assert settings.application_name == "AURA"
    assert settings.ai_provider == "none"
    assert settings.log_level == "INFO"
    assert settings.debug is False
    assert settings.data_directory == Path("data")


def test_settings_load_environment_values() -> None:
    settings = Settings.from_environment(
        {
            "AURA_APPLICATION_NAME": "AURA Test",
            "AURA_AI_PROVIDER": "local",
            "AURA_LOG_LEVEL": "debug",
            "AURA_DEBUG": "yes",
            "AURA_DATA_DIRECTORY": "~/aura-data",
        }
    )

    assert settings.application_name == "AURA Test"
    assert settings.ai_provider == "local"
    assert settings.ai_model == "gemini-3.7-flash"
    assert settings.log_level == "DEBUG"
    assert settings.debug is True
    assert settings.data_directory == Path("~/aura-data").expanduser()


def test_settings_load_dotenv_without_exposing_values(tmp_path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "AURA_AI_PROVIDER=gemini\nAURA_AI_MODEL=gemini-test\nGEMINI_API_KEY=secret\n",
        encoding="utf-8",
    )

    settings = Settings.from_environment(dotenv_path=dotenv)

    assert settings.ai_provider == "gemini"
    assert settings.ai_model == "gemini-test"
    assert settings.gemini_api_key == "secret"


def test_settings_reject_invalid_boolean() -> None:
    with pytest.raises(ValueError, match="AURA_DEBUG"):
        Settings.from_environment({"AURA_DEBUG": "sometimes"})


def test_settings_reject_invalid_log_level() -> None:
    with pytest.raises(ValueError, match="AURA_LOG_LEVEL"):
        Settings.from_environment({"AURA_LOG_LEVEL": "verbose-ish"})
