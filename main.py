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
    stt_provider = None
    tts_provider = None
    capture_service = None
    if settings.voice_enabled:
        try:
            from app.voice.capture import AudioCaptureService
            from app.voice.factory import create_voice_registry

            voice_registry = create_voice_registry(settings)
            try:
                stt_provider = voice_registry.create_stt(settings.stt_provider)
            except Exception:
                stt_provider = None
            try:
                tts_provider = voice_registry.create_tts(settings.tts_provider)
            except Exception:
                tts_provider = None
            capture_service = AudioCaptureService()
        except Exception:
            capture_service = None
    application = Application(
        settings=settings,
        provider=provider,
        provider_error=provider_error,
        tool_service=tool_service,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
    )
    desktop_application = DesktopApplication(
        settings=settings,
        message_handler=application.send_message,
        approval_handler=application.approve_tool_call,
        cancellation_handler=application.cancel_tool_call,
        startup_message=application.status_message,
        voice_transcribe_handler=application.transcribe_and_send
        if capture_service is not None
        else None,
        voice_start_handler=capture_service.start
        if capture_service is not None
        else None,
        voice_stop_handler=capture_service.stop
        if capture_service is not None
        else None,
    )

    try:
        return application.run(ui_runner=desktop_application.run)
    finally:
        desktop_application.close()
        application.close()
        if capture_service is not None:
            try:
                capture_service.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
