from __future__ import annotations

import io
import logging
import threading

from .provider import TranscriptionResult

logger = logging.getLogger(__name__)

_MAX_AUDIO_BYTES = 10 * 1024 * 1024
_MAX_AUDIO_SECONDS = 30
_SAMPLE_RATE = 16000


class WhisperSTTProvider:
    name = "whisper"

    def __init__(
        self,
        model_name: str = "base",
        *,
        model_factory=None,
    ) -> None:
        self._model_name = model_name
        self._model_factory = model_factory
        self._model = None
        self._lock = threading.Lock()
        self._closed = False

    def _get_model(self):
        if self._model is not None:
            return self._model
        if self._model_factory is not None:
            self._model = self._model_factory()
            return self._model
        try:
            import whisper

            self._model = whisper.load_model(self._model_name)
            return self._model
        except Exception as error:
            raise OSError("Whisper model unavailable") from error

    def transcribe(
        self, audio_bytes: bytes, *, sample_rate: int = 16000
    ) -> TranscriptionResult:
        if self._closed:
            return TranscriptionResult(error_message="Speech recognition is closed.")
        if not audio_bytes:
            return TranscriptionResult(
                error_message="No audio captured. Hold the talk button and speak."
            )
        if len(audio_bytes) > _MAX_AUDIO_BYTES:
            return TranscriptionResult(
                error_message="Audio is too long. Keep it under 30 seconds."
            )
        if sample_rate <= 0 or sample_rate > 48000:
            return TranscriptionResult(error_message="Unsupported audio sample rate.")
        max_samples = _MAX_AUDIO_SECONDS * sample_rate * 2
        if len(audio_bytes) > max_samples:
            return TranscriptionResult(
                error_message="Audio is too long. Keep it under 30 seconds."
            )
        try:
            with self._lock:
                model = self._get_model()
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    tmp.write(_pcm_to_wav(audio_bytes, sample_rate))
                try:
                    result = model.transcribe(tmp_path, language=None)
                    text = (
                        result.get("text", "")
                        if isinstance(result, dict)
                        else str(result)
                    )
                    text = text.strip()
                    if not text:
                        return TranscriptionResult(
                            error_message="Could not understand audio. Please try again."
                        )
                    if len(text) > 5000:
                        text = text[:5000]
                    return TranscriptionResult(text=text)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
        except OSError:
            logger.error("Whisper model load failed")
            return TranscriptionResult(
                error_message="Speech recognition is unavailable. The Whisper model could not be loaded."
            )
        except Exception:
            logger.error("Whisper transcribe failed")
            return TranscriptionResult(
                error_message="Speech recognition failed. Please try again."
            )

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._model = None


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()
