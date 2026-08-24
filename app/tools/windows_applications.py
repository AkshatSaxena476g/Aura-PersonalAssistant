"""Controlled Windows application launching for AURA Phase 4."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import Tool, ToolDefinition, ToolPermission, ToolResult, ToolValidationError


@dataclass(frozen=True, slots=True)
class _WindowsApplicationSpec:
    """Internal fixed launch target for one supported Windows application."""

    identifier: str
    display_name: str
    target: str
    launch_with_shell: bool = False


_APPLICATIONS: dict[str, _WindowsApplicationSpec] = {
    "notepad": _WindowsApplicationSpec(
        identifier="notepad",
        display_name="Notepad",
        target="notepad.exe",
    ),
    "calculator": _WindowsApplicationSpec(
        identifier="calculator",
        display_name="Calculator",
        target="calc.exe",
    ),
    "settings": _WindowsApplicationSpec(
        identifier="settings",
        display_name="Windows Settings",
        target="ms-settings:",
        launch_with_shell=True,
    ),
    "file_explorer": _WindowsApplicationSpec(
        identifier="file_explorer",
        display_name="File Explorer",
        target="explorer.exe",
    ),
}


class LaunchApplicationTool(Tool):
    """Launch one of four fixed Windows applications after confirmation."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="launch_application",
            description=(
                "Launch one approved Windows application: Notepad, Calculator, "
                "Windows Settings, or File Explorer."
            ),
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema={
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "enum": tuple(_APPLICATIONS),
                        "description": "A normalized approved application identifier.",
                    }
                },
                "required": ["application"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Normalize the controlled identifier before applying the schema."""

        if isinstance(arguments, Mapping) and isinstance(arguments.get("application"), str):
            normalized = dict(arguments)
            normalized["application"] = normalized["application"].strip().lower()
            return super().validate(normalized)
        return super().validate(arguments)

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        """Launch the internally resolved target without shell command parsing."""

        identifier = arguments["application"]
        spec = _APPLICATIONS[identifier]

        if sys.platform != "win32":
            return ToolResult.failure(
                "Application launching is available only on Windows.",
                error_code="unsupported_platform",
            )

        try:
            if spec.launch_with_shell:
                os.startfile(spec.target)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(
                    [spec.target],
                    shell=False,
                    close_fds=True,
                )
        except (OSError, ValueError):
            return ToolResult.failure(
                f"{spec.display_name} could not be launched.",
                error_code="launch_failed",
            )

        return ToolResult.ok(
            f"{spec.display_name} launch requested.",
            data={
                "application": spec.identifier,
                "display_name": spec.display_name,
            },
        )


__all__ = ["LaunchApplicationTool"]
