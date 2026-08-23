"""Provider-agnostic AURA application lifecycle."""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.ai.provider import AIProvider
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class Application:
    """Compose the initial AURA foundation without starting future features."""

    def __init__(
        self,
        settings: Settings,
        provider: AIProvider | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider

    def run(self, ui_runner: Callable[[], int] | None = None) -> int:
        """Start AURA and optionally hand off to the desktop UI event loop.

        The core owns application startup and configuration, while the UI is
        supplied as a callable by the composition root. This keeps the core
        independent from PySide6 and preserves a headless path for tests and
        future non-desktop entry points.
        """

        logger.info(
            "%s initialized (AI provider: %s)",
            self.settings.application_name,
            self.settings.ai_provider,
        )
        if ui_runner is None:
            return 0
        return ui_runner()
