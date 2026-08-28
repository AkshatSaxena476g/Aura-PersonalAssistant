from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.core.conversation import ConversationResult

TranscribeHandler = Callable[[bytes, int], ConversationResult]
SpeakHandler = Callable[[str], object]


class VoiceTranscribeWorker(QObject):
    completed = Signal(object)

    def __init__(
        self, handler: TranscribeHandler, audio: bytes, sample_rate: int
    ) -> None:
        super().__init__()
        self.handler = handler
        self.audio = audio
        self.sample_rate = sample_rate

    @Slot()
    def run(self) -> None:
        try:
            result = self.handler(self.audio, self.sample_rate)
            if not isinstance(result, ConversationResult):
                result = ConversationResult(
                    error_message="Voice handler returned an invalid result."
                )
        except Exception:
            result = ConversationResult(
                error_message="Voice processing failed due to an unexpected error."
            )
        self.completed.emit(result)


class VoiceRunner(QObject):
    result_ready = Signal(object)

    def __init__(
        self, handler: TranscribeHandler, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.handler = handler
        self._thread: QThread | None = None
        self._worker: VoiceTranscribeWorker | None = None

    @property
    def busy(self) -> bool:
        return self._thread is not None

    def submit(self, audio: bytes, sample_rate: int = 16000) -> bool:
        if self.busy:
            return False
        thread = QThread(self)
        worker = VoiceTranscribeWorker(self.handler, audio, sample_rate)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._handle_result)
        worker.completed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_thread)
        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    @Slot(object)
    def _handle_result(self, result: object) -> None:
        self.result_ready.emit(result)
        if self._thread is not None:
            self._thread.quit()

    @Slot()
    def _clear_thread(self) -> None:
        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.deleteLater()

    def shutdown(self) -> None:
        thread = self._thread
        if thread is None:
            return
        thread.requestInterruption()
        thread.quit()
        thread.wait(1000)
        self._thread = None
        self._worker = None
