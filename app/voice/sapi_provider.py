from __future__ import annotations

import logging
import sys
import threading

from .provider import SynthesisResult

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS = 5000


class SapiTTSProvider:
    name = "sapi"

    def __init__(
        self,
        voice_id: str | None = None,
        rate: int = 180,
        *,
        engine_factory=None,
    ) -> None:
        self._voice_id = voice_id
        self._rate = rate
        self._engine_factory = engine_factory
        self._engine = None
        self._lock = threading.Lock()
        self._closed = False

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        if self._engine_factory is not None:
            self._engine = self._engine_factory()
            return self._engine
        try:
            import pyttsx3

            engine = pyttsx3.init()
        except Exception as error:
            raise OSError("TTS engine unavailable") from error
        try:
            engine.setProperty("rate", int(self._rate))
            if self._voice_id:
                engine.setProperty("voice", self._voice_id)
        except Exception:
            pass
        self._engine = engine
        return engine

    def speak(self, text: str) -> SynthesisResult:
        if self._closed:
            return SynthesisResult.failure(
                "TTS provider is closed.", error_code="tts_closed"
            )
        cleaned = text.strip()
        if not cleaned:
            return SynthesisResult.failure("No text to speak.", error_code="empty_text")
        if len(cleaned) > _MAX_TEXT_CHARS:
            cleaned = cleaned[:_MAX_TEXT_CHARS]
        if sys.platform != "win32" and self._engine_factory is None:
            return SynthesisResult.failure(
                "Text-to-speech is available only on Windows.",
                error_code="unsupported_platform",
            )
        try:
            with self._lock:
                if sys.platform == "win32" and self._engine_factory is None:
                    try:
                        import comtypes

                        comtypes.CoInitialize()
                        try:
                            engine = self._get_engine()
                            engine.say(cleaned)
                            engine.runAndWait()
                        finally:
                            comtypes.CoUninitialize()
                    except ImportError:
                        engine = self._get_engine()
                        engine.say(cleaned)
                        engine.runAndWait()
                else:
                    engine = self._get_engine()
                    engine.say(cleaned)
                    engine.runAndWait()
        except Exception:
            logger.error("TTS speak failed")
            return SynthesisResult.failure(
                "The text-to-speech operation could not be completed.",
                error_code="tts_failed",
            )
        return SynthesisResult.ok("Spoken.")

    def stop(self) -> None:
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass

    def close(self) -> None:
        with self._lock:
            self._closed = True
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._engine = None
