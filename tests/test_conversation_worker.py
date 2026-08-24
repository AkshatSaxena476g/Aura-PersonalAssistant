import os
import threading
import time
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.ai import ChatMessage, GeminiProvider, MessageRole
from app.config import Settings
from app.core import Application, ConversationResult, ToolExecutionService
from app.tools import create_default_tool_registry
from app.ui import ConversationRunner, MainWindow


@pytest.fixture(scope="session")
def qapplication() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    yield application
    application.quit()


def _process_until(
    application: QApplication,
    predicate,
    timeout: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    application.processEvents()


def test_conversation_runner_executes_off_ui_path_and_cleans_up(
    qapplication: QApplication,
) -> None:
    started = threading.Event()
    release = threading.Event()
    results: list[ConversationResult] = []

    def handler(text: str) -> ConversationResult:
        started.set()
        release.wait(1.0)
        return ConversationResult(
            assistant_message=ChatMessage(
                MessageRole.ASSISTANT,
                f"Handled: {text}",
            )
        )

    runner = ConversationRunner(handler)
    runner.result_ready.connect(results.append)
    try:
        assert runner.submit("first") is True
        assert started.wait(1.0) is True
        assert runner.busy is True
        assert runner.submit("second") is False

        release.set()
        _process_until(
            qapplication,
            lambda: bool(results) and not runner.busy,
        )

        assert len(results) == 1
        assert results[0].assistant_message.content == "Handled: first"
        assert runner.busy is False
    finally:
        release.set()
        runner.shutdown()


def test_gemini_provider_path_runs_from_the_background_worker(
    qapplication: QApplication,
) -> None:
    main_thread_id = threading.get_ident()
    provider_thread_ids: list[int] = []

    class FakeModels:
        def generate_content(self, **kwargs: object) -> object:
            provider_thread_ids.append(threading.get_ident())
            return SimpleNamespace(
                text="Response from the provider worker.",
                function_calls=[],
            )

    class FakeClient:
        models = FakeModels()

    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-test",
        client=FakeClient(),
    )
    application = Application(
        Settings.from_environment({"AURA_AI_PROVIDER": "gemini"}),
        provider=provider,
        tool_service=ToolExecutionService(create_default_tool_registry()),
    )
    results: list[ConversationResult] = []
    runner = ConversationRunner(application.send_message)
    runner.result_ready.connect(results.append)
    try:
        assert runner.submit("Hello from the worker") is True
        _process_until(
            qapplication,
            lambda: bool(results) and not runner.busy,
        )

        assert results[0].assistant_message.content == "Response from the provider worker."
        assert provider_thread_ids
        assert provider_thread_ids[0] != main_thread_id
    finally:
        runner.shutdown()
        application.close()


def test_conversation_runner_converts_worker_exception_to_safe_result(
    qapplication: QApplication,
) -> None:
    results: list[ConversationResult] = []

    def handler(text: str) -> ConversationResult:
        raise RuntimeError("private network details")

    runner = ConversationRunner(handler)
    runner.result_ready.connect(results.append)
    try:
        assert runner.submit("fail") is True
        _process_until(
            qapplication,
            lambda: bool(results) and not runner.busy,
        )

        assert results[0].error_message == (
            "I couldn't complete that request because an unexpected error occurred."
        )
        assert "private network details" not in results[0].error_message
    finally:
        runner.shutdown()


def test_main_window_stays_busy_until_async_result_and_uses_dark_theme(
    qapplication: QApplication,
) -> None:
    submissions: list[str] = []

    def submit(text: str) -> bool:
        submissions.append(text)
        return True

    window = MainWindow(async_message_handler=submit)
    window.message_input.setText("Hello")
    window.send_button.click()

    assert submissions == ["Hello"]
    assert window.message_input.isEnabled() is False
    assert window.send_button.isEnabled() is False
    assert "thinking" in window.statusBar().currentMessage().lower()
    assert "#18212b" in window.styleSheet()
    assert "#222e3a" in window.styleSheet()

    window.send_button.click()
    assert submissions == ["Hello"]

    window.handle_async_result(
        ConversationResult(
            assistant_message=ChatMessage(
                MessageRole.ASSISTANT,
                "Hello from the worker.",
            )
        )
    )

    assert window.message_input.isEnabled() is True
    assert window.send_button.isEnabled() is True
    assert "Hello from the worker." in window.conversation_display.toPlainText()
    window.close()


def test_main_window_restores_controls_after_async_error(qapplication: QApplication) -> None:
    window = MainWindow(async_message_handler=lambda text: True)
    window.message_input.setText("Network request")
    window.send_button.click()

    window.handle_async_result(
        ConversationResult(error_message="Gemini could not complete the request.")
    )

    assert window.message_input.isEnabled() is True
    assert window.send_button.isEnabled() is True
    assert "Gemini could not complete the request." in (
        window.conversation_display.toPlainText()
    )
    window.close()
