"""Provider-agnostic AURA application lifecycle."""

from __future__ import annotations

import logging

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

    def run(self) -> int:
        """Start the foundation lifecycle and return a process exit code.

        UI, voice, tool execution, persistence, and concrete AI integrations
        are intentionally not started until their planned phases.
        """

        logger.info(
            "%s foundation initialized (AI provider: %s)",
            self.settings.application_name,
            self.settings.ai_provider,
        )
        return 0
