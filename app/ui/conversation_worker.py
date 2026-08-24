"""Managed Qt worker flow for non-blocking AURA conversation requests."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.core.conversation import ConversationResult


ConversationHandler = Callable[[str], ConversationResult]


class ConversationWorker(QObject):
    """Execute one existing core conversation request outside the UI thread."""

    completed = Signal(object)

    def __init__(self, handler: ConversationHandler, text: str) -> None:
        super().__init__()
        self.handler = handler
        self.text = text

    @Slot()
    def run(self) -> None:
        """Invoke the injected core handler and emit a safe result object."""

        try:
            result = self.handler(self.text)
            if not isinstance(result, ConversationResult):
                result = ConversationResult(
                    error_message="The conversation handler returned an invalid result."
                )
        except Exception:
            result = ConversationResult(
                error_message=(
                    "I couldn't complete that request because an unexpected error occurred."
                )
            )
        self.completed.emit(result)


class ConversationRunner(QObject):
    """Own one QThread per active request and clean it up after completion."""

    result_ready = Signal(object)

    def __init__(self, handler: ConversationHandler, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.handler = handler
        self._thread: QThread | None = None
        self._worker: ConversationWorker | None = None

    @property
    def busy(self) -> bool:
        """Return whether a background request is currently active."""

        return self._thread is not None

    def submit(self, text: str) -> bool:
        """Start one request, returning false when another request is active."""

        if self.busy:
            return False

        thread = QThread(self)
        worker = ConversationWorker(self.handler, text)
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
        """Forward the result on the main thread, then stop the worker thread."""

        self.result_ready.emit(result)
        if self._thread is not None:
            self._thread.quit()

    @Slot()
    def _clear_thread(self) -> None:
        """Release references after the QThread event loop has stopped."""

        thread = self._thread
        self._thread = None
        self._worker = None
        if thread is not None:
            thread.deleteLater()

    def shutdown(self) -> None:
        """Request thread shutdown and wait briefly for completed worker cleanup."""

        thread = self._thread
        if thread is None:
            return
        thread.requestInterruption()
        thread.quit()
        thread.wait(1000)
        self._thread = None
        self._worker = None


__all__ = ["ConversationRunner", "ConversationWorker"]
