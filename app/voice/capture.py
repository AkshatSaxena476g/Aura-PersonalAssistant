from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_CHANNELS = 1
_MAX_SECONDS = 30
_MAX_BYTES = _MAX_SECONDS * _SAMPLE_RATE * 2


class AudioCaptureService:
    def __init__(
        self, *, sample_rate: int = _SAMPLE_RATE, max_seconds: int = _MAX_SECONDS
    ) -> None:
        self.sample_rate = sample_rate
        self.max_seconds = max_seconds
        self._stream = None
        self._frames: list[bytes] = []
        self._recording = False
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        with self._lock:
            return self._recording

    def start(self) -> bool:
        with self._lock:
            if self._recording:
                return False
            try:
                import sounddevice as sd

                self._frames = []
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=_CHANNELS,
                    dtype="int16",
                    callback=self._callback,
                )
                self._stream.start()
                self._recording = True
                return True
            except Exception:
                logger.error("Audio capture start failed")
                self._stream = None
                return False

    def stop(self) -> bytes | None:
        with self._lock:
            if not self._recording:
                return None
            try:
                if self._stream is not None:
                    try:
                        self._stream.stop()
                        self._stream.close()
                    except Exception:
                        pass
                data = b"".join(self._frames)
                if len(data) > _MAX_BYTES:
                    data = data[:_MAX_BYTES]
                return data
            finally:
                self._stream = None
                self._frames = []
                self._recording = False

    def cancel(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
            self._stream = None
            self._frames = []
            self._recording = False

    def _callback(self, indata, frames, time, status) -> None:
        try:
            data = bytes(indata)
            with self._lock:
                if self._recording:
                    self._frames.append(data)
                    total = sum(len(f) for f in self._frames)
                    if total > _MAX_BYTES:
                        excess = total - _MAX_BYTES
                        flat = b"".join(self._frames)
                        self._frames = [flat[:_MAX_BYTES]]
        except Exception:
            pass

    def close(self) -> None:
        self.cancel()
