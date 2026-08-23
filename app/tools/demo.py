"""Safe read-only demonstration tools for validating the Phase 3 architecture."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from .contracts import Tool, ToolDefinition, ToolPermission, ToolResult


class GetApplicationStatusTool(Tool):
    """Return static application status without changing the computer."""

    def __init__(self, application_name: str = "AURA") -> None:
        self.application_name = application_name

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_application_status",
            description="Return the current status of the AURA application.",
            permission=ToolPermission.SAFE,
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        return ToolResult.ok(
            f"{self.application_name} is running.",
            data={"application_name": self.application_name, "status": "running"},
        )


class GetLocalDateTimeTool(Tool):
    """Return the current local date and time without changing the computer."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now().astimezone())

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_local_datetime",
            description="Return the current local date and time.",
            permission=ToolPermission.SAFE,
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        current_time = self._clock()
        formatted_time = current_time.isoformat(timespec="seconds")
        return ToolResult.ok(
            f"The current local date and time is {formatted_time}.",
            data={
                "iso_datetime": formatted_time,
                "timezone": current_time.tzname(),
            },
        )
