"""Executable composition root for the AURA desktop application."""

from __future__ import annotations

import logging

from app.ai import create_configured_provider
from app.config import Settings
from app.core import Application, ToolExecutionService
from app.tools import create_default_tool_registry
from app.ui import DesktopApplication


def main() -> int:
    """Load settings, initialize AURA, and run the desktop application."""

    settings = Settings.from_environment()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    provider, provider_error = create_configured_provider(settings)
    tool_service = ToolExecutionService(
        create_default_tool_registry(application_name=settings.application_name)
    )
    application = Application(
        settings=settings,
        provider=provider,
        provider_error=provider_error,
        tool_service=tool_service,
    )
    desktop_application = DesktopApplication(
        settings=settings,
        message_handler=application.send_message,
        approval_handler=application.approve_tool_call,
        cancellation_handler=application.cancel_tool_call,
        startup_message=application.status_message,
    )

    try:
        return application.run(ui_runner=desktop_application.run)
    finally:
        desktop_application.close()
        application.close()


if __name__ == "__main__":
    raise SystemExit(main())
