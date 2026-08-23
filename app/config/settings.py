"""Application settings loaded from environment variables.

The foundation intentionally uses only the Python standard library. Provider-
specific credentials and options remain the responsibility of provider
implementations rather than the assistant core.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_VALID_LOG_LEVELS = frozenset({"CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING"})


def _parse_log_level(value: str) -> str:
    """Normalize and validate the standard library logging level."""

    normalized = value.strip().upper()
    if normalized not in _VALID_LOG_LEVELS:
        raise ValueError(
            f"AURA_LOG_LEVEL must be one of: {', '.join(sorted(_VALID_LOG_LEVELS))}"
        )
    return normalized


def _parse_bool(value: str, *, variable_name: str) -> bool:
    """Parse a human-friendly boolean environment variable."""

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(
        f"{variable_name} must be one of: "
        f"{', '.join(sorted(_TRUE_VALUES | _FALSE_VALUES))}"
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings shared across AURA subsystems."""

    application_name: str = "AURA"
    ai_provider: str = "none"
    log_level: str = "INFO"
    debug: bool = False
    data_directory: Path = Path("data")

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "Settings":
        """Build settings from environment variables.

        The optional mapping makes configuration deterministic and easy to test
        without changing the process environment.
        """

        source = os.environ if environment is None else environment
        ai_provider = source.get("AURA_AI_PROVIDER", "none").strip() or "none"
        log_level = _parse_log_level(source.get("AURA_LOG_LEVEL", "INFO") or "INFO")
        debug_value = source.get("AURA_DEBUG", "false")
        data_directory = source.get("AURA_DATA_DIRECTORY", "data").strip() or "data"

        return cls(
            application_name=source.get("AURA_APPLICATION_NAME", "AURA").strip()
            or "AURA",
            ai_provider=ai_provider,
            log_level=log_level,
            debug=_parse_bool(debug_value, variable_name="AURA_DEBUG"),
            data_directory=Path(data_directory).expanduser(),
        )
