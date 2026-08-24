import os
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.ai import ChatMessage, MessageRole
from app.config import Settings
from app.core import Application, ConversationResult
from app.tools import ToolResult
from app.ui import MainWindow


@pytest.fixture(scope="session")
def qapplication() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    yield application
    application.quit()


def test_main_window_has_aura_branding_and_chat_controls(qapplication: QApplication) -> None:
    window = MainWindow(application_name="AURA")

    assert window.objectName() == "auraMainWindow"
    assert window.windowTitle() == "AURA | Personal Desktop Assistant"
    assert window.findChild(QLabel, "auraTitle").text() == "AURA"
    assert window.findChild(QLabel, "auraSubtitle").text() == "Personal Desktop Assistant"
    assert window.conversation_display.objectName() == "conversationDisplay"
    assert window.message_input.objectName() == "messageInput"
    assert window.send_button.objectName() == "sendButton"

    window.close()


def test_main_window_delegates_text_to_core_handler(qapplication: QApplication) -> None:
    received: list[str] = []

    def handle_message(text: str) -> ConversationResult:
        received.append(text)
        return ConversationResult(
            user_message=ChatMessage(MessageRole.USER, text),
            assistant_message=ChatMessage(MessageRole.ASSISTANT, "Hello from AURA."),
        )

    window = MainWindow(message_handler=handle_message)
    window.message_input.setText("Hello")
    window.send_button.click()

    assert received == ["Hello"]
    assert "You" in window.conversation_display.toPlainText()
    assert "Hello from AURA." in window.conversation_display.toPlainText()
    assert window.message_input.text() == ""
    assert window.send_button.isEnabled() is True

    window.close()


def test_main_window_handles_empty_text_without_calling_core(qapplication: QApplication) -> None:
    received: list[str] = []

    def handle_message(text: str) -> ConversationResult:
        received.append(text)
        return ConversationResult()

    window = MainWindow(message_handler=handle_message)
    window.message_input.setText("   ")
    window.send_button.click()

    assert received == []
    assert "Please enter a message." in window.conversation_display.toPlainText()

    window.close()


def test_main_window_shows_confirmation_and_approves_once(qapplication: QApplication) -> None:
    approvals: list[str] = []
    sends: list[str] = []
    pending = SimpleNamespace(
        request_id="ui-call-1",
        confirmation_message="I can open Calculator. Do you want me to proceed?",
    )

    def handle_message(text: str) -> ConversationResult:
        sends.append(text)
        return ConversationResult(pending_tool=pending)

    def approve(request_id: str) -> ConversationResult:
        approvals.append(request_id)
        return ConversationResult(
            tool_result=ToolResult.ok("Calculator launch requested.")
        )

    window = MainWindow(
        message_handler=handle_message,
        approval_handler=approve,
    )
    window.message_input.setText("Open Calculator")
    window.send_button.click()

    assert sends == ["Open Calculator"]
    assert window.confirmation_panel.isHidden() is False
    assert "Calculator" in window.confirmation_label.text()
    assert window.message_input.isEnabled() is False
    assert window.send_button.isEnabled() is False

    window.allow_button.click()
    window.allow_button.click()

    assert approvals == ["ui-call-1"]
    assert window.confirmation_panel.isHidden() is True
    assert window.send_button.isEnabled() is True
    assert "Calculator launch requested." in window.conversation_display.toPlainText()

    window.close()


def test_main_window_cancels_pending_action_without_approval(qapplication: QApplication) -> None:
    cancellations: list[str] = []
    pending = SimpleNamespace(
        request_id="ui-call-2",
        confirmation_message="I can open Calculator. Do you want me to proceed?",
    )

    def handle_message(text: str) -> ConversationResult:
        return ConversationResult(pending_tool=pending)

    def cancel(request_id: str) -> ConversationResult:
        cancellations.append(request_id)
        return ConversationResult(
            tool_result=ToolResult.failure(
                "Tool action cancelled.",
                error_code="cancelled",
            )
        )

    window = MainWindow(
        message_handler=handle_message,
        cancellation_handler=cancel,
    )
    window.message_input.setText("Open Calculator")
    window.send_button.click()
    window.cancel_button.click()

    assert cancellations == ["ui-call-2"]
    assert window.confirmation_panel.isHidden() is True
    assert "Tool action cancelled." in window.conversation_display.toPlainText()

    window.close()


def test_core_lifecycle_delegates_to_supplied_ui_runner() -> None:
    calls: list[str] = []

    def run_ui() -> int:
        calls.append("ui")
        return 7

    result = Application(Settings.from_environment({})).run(ui_runner=run_ui)

    assert result == 7
    assert calls == ["ui"]
