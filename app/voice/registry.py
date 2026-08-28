from __future__ import annotations

from collections.abc import Callable
from typing import Any


class VoiceRegistry:
    def __init__(self) -> None:
        self._stt: dict[str, Callable[[], Any]] = {}
        self._tts: dict[str, Callable[[], Any]] = {}

    def register_stt(self, name: str, factory: Callable[[], Any]) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("STT provider name must not be empty")
        if key in self._stt:
            raise ValueError(f"STT provider already registered: {key}")
        self._stt[key] = factory

    def register_tts(self, name: str, factory: Callable[[], Any]) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("TTS provider name must not be empty")
        if key in self._tts:
            raise ValueError(f"TTS provider already registered: {key}")
        self._tts[key] = factory

    def create_stt(self, name: str) -> Any:
        key = name.strip().lower()
        try:
            return self._stt[key]()
        except KeyError as error:
            available = ", ".join(sorted(self._stt)) or "none"
            raise LookupError(
                f"Unknown STT provider '{name}'. Available: {available}"
            ) from error

    def create_tts(self, name: str) -> Any:
        key = name.strip().lower()
        try:
            return self._tts[key]()
        except KeyError as error:
            available = ", ".join(sorted(self._tts)) or "none"
            raise LookupError(
                f"Unknown TTS provider '{name}'. Available: {available}"
            ) from error

    @property
    def stt_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._stt))

    @property
    def tts_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tts))
