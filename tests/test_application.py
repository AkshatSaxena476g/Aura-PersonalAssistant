from app.config import Settings
from app.core import Application


def test_application_starts_without_concrete_ai_provider() -> None:
    application = Application(settings=Settings.from_environment({}))

    assert application.provider is None
    assert application.run() == 0
