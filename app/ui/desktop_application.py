"""Qt application composition for the AURA desktop UI."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from app.config import Settings

from .main_window import MainWindow, MessageHandler


class DesktopApplication:
    """Create and run the Qt UI for an already configured AURA application."""

    def __init__(
        self,
        settings: Settings,
        *,
        message_handler: MessageHandler | None = None,
        startup_message: str | None = None,
        argv: Sequence[str] | None = None,
    ) -> None:
        self.settings = settings
        self.message_handler = message_handler
        self.startup_message = startup_message
        self.argv = list(sys.argv if argv is None else argv)
        self.window: MainWindow | None = None
        self.qt_application: QApplication | None = None

    def run(self) -> int:
        """Show the main window and enter the Qt event loop."""

        qt_application = QApplication.instance()
        if qt_application is None:
            qt_application = QApplication(self.argv)

        qt_application.setApplicationName(self.settings.application_name)
        qt_application.setApplicationDisplayName(self.settings.application_name)

        self.window = MainWindow(
            application_name=self.settings.application_name,
            message_handler=self.message_handler,
            startup_message=self.startup_message,
        )
        self.window.show()
        self.qt_application = qt_application

        return qt_application.exec()

    def close(self) -> None:
        """Close the UI window and request that the Qt event loop exits."""

        if self.window is not None:
            self.window.close()
        if self.qt_application is not None:
            self.qt_application.quit()


__all__ = ["DesktopApplication"]
