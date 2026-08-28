from __future__ import annotations

from .provider import SynthesisResult, TranscriptionResult


class MockSTTProvider:
    name = "mock"

    def __init__(self, text: str = "hello aura") -> None:
        self._text = text
        self.closed = False

    def transcribe(
        self, audio_bytes: bytes, *, sample_rate: int = 16000
    ) -> TranscriptionResult:
        if not audio_bytes:
            return TranscriptionResult(
                error_message="No audio captured. Hold the talk button and speak."
            )
        return TranscriptionResult(text=self._text)

    def close(self) -> None:
        self.closed = True


class MockTTSProvider:
    name = "mock"

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.stopped = False
        self.closed = False

    def speak(self, text: str) -> SynthesisResult:
        if not text.strip():
            return SynthesisResult.failure("No text to speak.", error_code="empty_text")
        self.spoken.append(text)
        return SynthesisResult.ok("Spoken.")

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True
