"""Main desktop window for the initial AURA UI shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """Minimal, intentionally non-interactive AURA desktop window."""

    def __init__(
        self,
        application_name: str = "AURA",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("auraMainWindow")
        self.setWindowTitle(f"{application_name} | Personal Desktop Assistant")
        self.setMinimumSize(520, 320)
        self.resize(640, 400)

        self._build_content(application_name)

    def _build_content(self, application_name: str) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("auraCentralWidget")

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(48, 42, 48, 42)
        layout.setSpacing(12)

        title = QLabel(application_name, central_widget)
        title.setObjectName("auraTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Personal Desktop Assistant", central_widget)
        subtitle.setObjectName("auraSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status = QLabel(
            "AURA is ready. Conversation and approved actions will be added in later phases.",
            central_widget,
        )
        status.setObjectName("auraStatus")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setWordWrap(True)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(status)
        layout.addStretch(1)

        self.setCentralWidget(central_widget)
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f7fa;
            }
            QLabel#auraTitle {
                color: #243447;
                font-size: 32px;
                font-weight: 600;
            }
            QLabel#auraSubtitle {
                color: #526477;
                font-size: 16px;
            }
            QLabel#auraStatus {
                color: #667788;
                font-size: 13px;
            }
            """
        )
