"""Composition helpers for selecting configured AI providers."""

from __future__ import annotations

import logging

from app.config import Settings

from .gemini_provider import GeminiProvider
from .provider import AIProvider, ProviderError
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


def create_configured_provider(
    settings: Settings,
) -> tuple[AIProvider | None, str | None]:
    """Create the selected provider and return a safe startup error if needed."""

    registry = ProviderRegistry()
    registry.register(
        GeminiProvider.name,
        lambda: GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.ai_model,
        ),
    )

    if settings.ai_provider in {"", "none"}:
        return None, None

    try:
        return registry.create(settings.ai_provider), None
    except ProviderError as error:
        return None, str(error)
    except LookupError:
        return (
            None,
            f"The configured AI provider '{settings.ai_provider}' is not supported.",
        )
    except Exception:
        logger.error("Unexpected AI provider initialization error")
        return None, "The configured AI provider could not be initialized."
