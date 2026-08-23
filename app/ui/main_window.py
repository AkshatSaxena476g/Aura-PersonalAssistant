"""Main desktop window and text conversation controls for AURA."""

from __future__ import annotations

from collections.abc import Callable
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from app.core.conversation import ConversationResult


MessageHandler = Callable[[str], ConversationResult]


class MainWindow(QMainWindow):
    """Simple AURA window for text-only conversation."""

    def __init__(
        self,
        application_name: str = "AURA",
        *,
        message_handler: MessageHandler | None = None,
        startup_message: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.message_handler = message_handler
        self.setObjectName("auraMainWindow")
        self.setWindowTitle(f"{application_name} | Personal Desktop Assistant")
        self.setMinimumSize(560, 420)
        self.resize(720, 520)

        self._build_content(
            application_name,
            startup_message or "AURA is ready. Send a message to begin.",
        )

    def _build_content(self, application_name: str, startup_message: str) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("auraCentralWidget")

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(12)

        title = QLabel(application_name, central_widget)
        title.setObjectName("auraTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Personal Desktop Assistant", central_widget)
        subtitle.setObjectName("auraSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.conversation_display = QTextBrowser(central_widget)
        self.conversation_display.setObjectName("conversationDisplay")
        self.conversation_display.setReadOnly(True)
        self.conversation_display.setOpenExternalLinks(False)

        self.message_input = QLineEdit(central_widget)
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("Type a message to AURA...")
        self.message_input.returnPressed.connect(self._send_message)

        self.send_button = QPushButton("Send", central_widget)
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self._send_message)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        input_layout.addWidget(self.message_input, 1)
        input_layout.addWidget(self.send_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.conversation_display, 1)
        layout.addLayout(input_layout)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("Ready")
        self._append_message("AURA", startup_message)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f7fa;
            }
            QLabel#auraTitle {
                color: #243447;
                font-size: 30px;
                font-weight: 600;
            }
            QLabel#auraSubtitle {
                color: #526477;
                font-size: 15px;
            }
            QTextBrowser#conversationDisplay {
                background: #ffffff;
                border: 1px solid #d8e0e8;
                border-radius: 6px;
                color: #243447;
                font-size: 14px;
                padding: 8px;
            }
            QLineEdit#messageInput {
                background: #ffffff;
                border: 1px solid #c5d0dc;
                border-radius: 5px;
                color: #243447;
                padding: 9px;
            }
            QPushButton#sendButton {
                background: #3d6f9f;
                border: none;
                border-radius: 5px;
                color: #ffffff;
                font-weight: 600;
                padding: 9px 18px;
            }
            QPushButton#sendButton:hover {
                background: #315d87;
            }
            """
        )

    def _append_message(self, speaker: str, content: str) -> None:
        safe_speaker = escape(speaker)
        safe_content = escape(content).replace("\n", "<br>")
        self.conversation_display.append(
            f'<p><b style="color:#3d6f9f;">{safe_speaker}</b><br>{safe_content}</p>'
        )

    def _send_message(self) -> None:
        text = self.message_input.text()
        if not text.strip():
            self._append_message("AURA", "Please enter a message.")
            self.statusBar().showMessage("A message is required")
            return

        self.message_input.clear()
        self._append_message("You", text.strip())
        self.send_button.setEnabled(False)
        self.statusBar().showMessage("Thinking...")

        try:
            result = (
                self.message_handler(text)
                if self.message_handler is not None
                else ConversationResult(
                    error_message="No AI provider is configured for conversation."
                )
            )
        except Exception:
            result = ConversationResult(
                error_message=(
                    "I couldn't complete that request because an unexpected error occurred."
                )
            )
        finally:
            self.send_button.setEnabled(True)

        if result.assistant_message is not None:
            self._append_message("AURA", result.assistant_message.content)
            self.statusBar().showMessage("Ready")
        elif result.error_message:
            self._append_message("AURA", result.error_message)
            self.statusBar().showMessage("Request could not be completed")
