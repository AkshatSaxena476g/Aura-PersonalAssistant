"""Qt application composition for the AURA desktop UI."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from app.config import Settings
from app.core.conversation import ConversationResult

from .conversation_worker import ConversationRunner
from .main_window import ConfirmationHandler, MainWindow, MessageHandler
from .theme import AURA_DARK_THEME


class DesktopApplication:
    """Create and run the Qt UI for an already configured AURA application."""

    def __init__(
        self,
        settings: Settings,
        *,
        message_handler: MessageHandler | None = None,
        approval_handler: ConfirmationHandler | None = None,
        cancellation_handler: ConfirmationHandler | None = None,
        startup_message: str | None = None,
        argv: Sequence[str] | None = None,
    ) -> None:
        self.settings = settings
        self.message_handler = message_handler
        self.approval_handler = approval_handler
        self.cancellation_handler = cancellation_handler
        self.startup_message = startup_message
        self.argv = list(sys.argv if argv is None else argv)
        self.window: MainWindow | None = None
        self.qt_application: QApplication | None = None
        self.conversation_runner: ConversationRunner | None = None

    def run(self) -> int:
        """Show the main window and enter the Qt event loop."""

        qt_application = QApplication.instance()
        if qt_application is None:
            qt_application = QApplication(self.argv)

        qt_application.setApplicationName(self.settings.application_name)
        qt_application.setApplicationDisplayName(self.settings.application_name)
        qt_application.setStyleSheet(AURA_DARK_THEME)

        if self.message_handler is not None:
            self.conversation_runner = ConversationRunner(self.message_handler)

        self.window = MainWindow(
            application_name=self.settings.application_name,
            async_message_handler=(
                self.conversation_runner.submit
                if self.conversation_runner is not None
                else None
            ),
            message_handler=(
                None if self.conversation_runner is not None else self.message_handler
            ),
            approval_handler=self.approval_handler,
            cancellation_handler=self.cancellation_handler,
            startup_message=self.startup_message,
        )
        if self.conversation_runner is not None:
            self.conversation_runner.result_ready.connect(
                self.window.handle_async_result
            )
        self.window.show()
        self.qt_application = qt_application

        return qt_application.exec()

    def close(self) -> None:
        """Close the UI, stop active worker cleanup, and exit the Qt event loop."""

        if self.conversation_runner is not None:
            self.conversation_runner.shutdown()
        if self.window is not None:
            self.window.close()
        if self.qt_application is not None:
            self.qt_application.quit()


__all__ = ["ConversationResult", "DesktopApplication"]
