from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    text: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        has_text = self.text is not None and self.text.strip() != ""
        has_error = self.error_message is not None and self.error_message.strip() != ""
        if has_text == has_error:
            raise ValueError(
                "TranscriptionResult must contain exactly one text or error_message"
            )

    @property
    def succeeded(self) -> bool:
        return self.text is not None


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    success: bool
    message: str
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("SynthesisResult message must not be empty")
        if self.success and self.error_code is not None:
            raise ValueError("Successful synthesis cannot contain error_code")
        if not self.success and not self.error_code:
            raise ValueError("Failed synthesis must contain error_code")

    @classmethod
    def ok(cls, message: str) -> "SynthesisResult":
        return cls(success=True, message=message)

    @classmethod
    def failure(cls, message: str, *, error_code: str) -> "SynthesisResult":
        return cls(success=False, message=message, error_code=error_code)


class STTProvider(Protocol):
    @property
    def name(self) -> str: ...

    def transcribe(
        self, audio_bytes: bytes, *, sample_rate: int = 16000
    ) -> TranscriptionResult: ...

    def close(self) -> None: ...


class TTSProvider(Protocol):
    @property
    def name(self) -> str: ...

    def speak(self, text: str) -> SynthesisResult: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...
