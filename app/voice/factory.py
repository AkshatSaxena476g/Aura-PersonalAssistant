from __future__ import annotations

import logging

from app.config import Settings

from .registry import VoiceRegistry

logger = logging.getLogger(__name__)


def create_voice_registry(settings: Settings) -> VoiceRegistry:
    registry = VoiceRegistry()
    registry.register_stt("whisper", lambda: _create_whisper(settings))
    registry.register_stt("mock", lambda: _create_mock_stt())
    registry.register_tts("sapi", lambda: _create_sapi(settings))
    registry.register_tts("mock", lambda: _create_mock_tts())
    return registry


def _create_whisper(settings: Settings):
    from .whisper_provider import WhisperSTTProvider

    return WhisperSTTProvider(model_name=settings.whisper_model)


def _create_sapi(settings: Settings):
    from .sapi_provider import SapiTTSProvider

    return SapiTTSProvider(voice_id=settings.tts_voice, rate=settings.tts_rate)


def _create_mock_stt():
    from .mock_provider import MockSTTProvider

    return MockSTTProvider()


def _create_mock_tts():
    from .mock_provider import MockTTSProvider

    return MockTTSProvider()
