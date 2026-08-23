import os

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.config import Settings
from app.core import Application
from app.ui import MainWindow


@pytest.fixture(scope="session")
def qapplication() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication([])
    yield application
    application.quit()


def test_main_window_has_aura_branding(qapplication: QApplication) -> None:
    window = MainWindow(application_name="AURA")

    assert window.objectName() == "auraMainWindow"
    assert window.windowTitle() == "AURA | Personal Desktop Assistant"
    assert window.findChild(QLabel, "auraTitle").text() == "AURA"
    assert window.findChild(QLabel, "auraSubtitle").text() == "Personal Desktop Assistant"

    window.close()


def test_core_lifecycle_delegates_to_supplied_ui_runner() -> None:
    calls: list[str] = []

    def run_ui() -> int:
        calls.append("ui")
        return 7

    result = Application(Settings.from_environment({})).run(ui_runner=run_ui)

    assert result == 7
    assert calls == ["ui"]
