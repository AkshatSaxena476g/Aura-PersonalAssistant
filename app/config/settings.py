"""Application settings loaded from environment variables and .env files.

Provider-specific credentials remain configuration data. They are kept out of
logs and are only passed to the concrete provider that needs them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
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


def _read_dotenv(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE entries without overriding process variables."""

    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings shared across AURA subsystems."""

    application_name: str = "AURA"
    ai_provider: str = "none"
    ai_model: str = "gemini-3.7-flash"
    gemini_api_key: str | None = field(default=None, repr=False)
    log_level: str = "INFO"
    debug: bool = False
    data_directory: Path = Path("data")

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        dotenv_path: Path | None = None,
    ) -> "Settings":
        """Build settings from a mapping, process environment, and optional .env.

        An explicit mapping is used as-is for deterministic tests. When no
        mapping is supplied, values from ``.env`` are loaded first and process
        environment variables take precedence. Secret values are never logged.
        """

        if environment is None:
            source = _read_dotenv(dotenv_path or Path(".env"))
            source.update(os.environ)
        else:
            source = environment

        ai_provider = source.get("AURA_AI_PROVIDER", "none").strip() or "none"
        ai_model = source.get("AURA_AI_MODEL", "gemini-3.7-flash").strip()
        log_level = _parse_log_level(source.get("AURA_LOG_LEVEL", "INFO") or "INFO")
        debug_value = source.get("AURA_DEBUG", "false")
        data_directory = source.get("AURA_DATA_DIRECTORY", "data").strip() or "data"
        api_key = source.get("GEMINI_API_KEY", "").strip() or None

        return cls(
            application_name=source.get("AURA_APPLICATION_NAME", "AURA").strip()
            or "AURA",
            ai_provider=ai_provider,
            ai_model=ai_model or "gemini-3.7-flash",
            gemini_api_key=api_key,
            log_level=log_level,
            debug=_parse_bool(debug_value, variable_name="AURA_DEBUG"),
            data_directory=Path(data_directory).expanduser(),
        )
