"""Command-line entry point for the AURA desktop application foundation."""

from __future__ import annotations

import logging

from app.config import Settings
from app.core import Application
from app.ui import DesktopApplication


def main() -> int:
    """Load settings, initialize AURA, and return an exit status."""

    settings = Settings.from_environment()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    desktop_application = DesktopApplication(settings=settings)
    return Application(settings=settings).run(ui_runner=desktop_application.run)


if __name__ == "__main__":
    raise SystemExit(main())
