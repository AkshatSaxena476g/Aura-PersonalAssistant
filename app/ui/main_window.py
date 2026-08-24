"""Main desktop window and text conversation controls for AURA."""

from __future__ import annotations

from collections.abc import Callable
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.core.conversation import ConversationResult


MessageHandler = Callable[[str], ConversationResult]
ConfirmationHandler = Callable[[str], ConversationResult]


class MainWindow(QMainWindow):
    """Simple AURA window for text conversation and tool confirmation."""

    def __init__(
        self,
        application_name: str = "AURA",
        *,
        message_handler: MessageHandler | None = None,
        approval_handler: ConfirmationHandler | None = None,
        cancellation_handler: ConfirmationHandler | None = None,
        startup_message: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.message_handler = message_handler
        self.approval_handler = approval_handler
        self.cancellation_handler = cancellation_handler
        self._pending_request_id: str | None = None
        self.setObjectName("auraMainWindow")
        self.setWindowTitle(f"{application_name} | Personal Desktop Assistant")
        self.setMinimumSize(560, 420)
        self.resize(720, 560)

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

        self.confirmation_panel = QWidget(central_widget)
        self.confirmation_panel.setObjectName("confirmationPanel")
        confirmation_layout = QHBoxLayout(self.confirmation_panel)
        confirmation_layout.setContentsMargins(12, 8, 12, 8)
        confirmation_layout.setSpacing(8)

        self.confirmation_label = QLabel(self.confirmation_panel)
        self.confirmation_label.setObjectName("confirmationLabel")
        self.confirmation_label.setWordWrap(True)
        confirmation_layout.addWidget(self.confirmation_label, 1)

        self.allow_button = QPushButton("Allow", self.confirmation_panel)
        self.allow_button.setObjectName("allowButton")
        self.allow_button.clicked.connect(self._approve_pending)
        confirmation_layout.addWidget(self.allow_button)

        self.cancel_button = QPushButton("Cancel", self.confirmation_panel)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self._cancel_pending)
        confirmation_layout.addWidget(self.cancel_button)
        self.confirmation_panel.setVisible(False)

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
        layout.addWidget(self.confirmation_panel)
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
            QWidget#confirmationPanel {
                background: #edf4fb;
                border: 1px solid #b9cfe5;
                border-radius: 6px;
            }
            QLabel#confirmationLabel {
                color: #243447;
                font-size: 13px;
            }
            QLineEdit#messageInput {
                background: #ffffff;
                border: 1px solid #c5d0dc;
                border-radius: 5px;
                color: #243447;
                padding: 9px;
            }
            QPushButton#sendButton, QPushButton#allowButton {
                background: #3d6f9f;
                border: none;
                border-radius: 5px;
                color: #ffffff;
                font-weight: 600;
                padding: 9px 18px;
            }
            QPushButton#sendButton:hover, QPushButton#allowButton:hover {
                background: #315d87;
            }
            QPushButton#cancelButton {
                background: #ffffff;
                border: 1px solid #b9c5d1;
                border-radius: 5px;
                color: #33485c;
                padding: 8px 16px;
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
        if self._pending_request_id is not None:
            return
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

        if result.pending_tool is not None:
            self._show_confirmation(result)
            return

        self.send_button.setEnabled(True)
        self._render_result(result)

    def _show_confirmation(self, result: ConversationResult) -> None:
        """Show one pending request and lock out competing user actions."""

        assert result.pending_tool is not None
        self._pending_request_id = result.pending_tool.request_id
        self.confirmation_label.setText(result.pending_tool.confirmation_message)
        self.confirmation_panel.setVisible(True)
        self.message_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.allow_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Waiting for confirmation")

    def _approve_pending(self) -> None:
        request_id = self._pending_request_id
        if request_id is None:
            return
        self._pending_request_id = None
        self.allow_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        try:
            result = (
                self.approval_handler(request_id)
                if self.approval_handler is not None
                else ConversationResult(
                    tool_result=None,
                    error_message="Tool approval is unavailable.",
                )
            )
        except Exception:
            result = ConversationResult(
                error_message="The approved tool action could not be completed."
            )
        self._finish_confirmation()
        self._render_result(result)

    def _cancel_pending(self) -> None:
        request_id = self._pending_request_id
        if request_id is None:
            return
        self._pending_request_id = None
        self.allow_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        try:
            result = (
                self.cancellation_handler(request_id)
                if self.cancellation_handler is not None
                else ConversationResult(
                    error_message="Tool cancellation is unavailable."
                )
            )
        except Exception:
            result = ConversationResult(
                error_message="The pending tool action could not be cancelled."
            )
        self._finish_confirmation()
        self._render_result(result)

    def _finish_confirmation(self) -> None:
        self.confirmation_panel.setVisible(False)
        self.message_input.setEnabled(True)
        self.send_button.setEnabled(True)

    def _render_result(self, result: ConversationResult) -> None:
        if result.assistant_message is not None:
            self._append_message("AURA", result.assistant_message.content)
            self.statusBar().showMessage("Ready")
            return

        if result.tool_result is not None:
            if result.tool_result.success:
                self._append_message("AURA", result.tool_result.message)
                self.statusBar().showMessage("Tool action completed")
            else:
                self._append_message("AURA", result.tool_result.message)
                self.statusBar().showMessage("Tool action cancelled or failed")
            return

        if result.error_message:
            self._append_message("AURA", result.error_message)
            self.statusBar().showMessage("Request could not be completed")
