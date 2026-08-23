"""Default Phase 3 tool composition."""

from __future__ import annotations

from .demo import GetApplicationStatusTool, GetLocalDateTimeTool
from .registry import ToolRegistry


def create_default_tool_registry(*, application_name: str = "AURA") -> ToolRegistry:
    """Return a registry containing only safe, read-only demonstration tools."""

    return ToolRegistry(
        tools=(
            GetApplicationStatusTool(application_name=application_name),
            GetLocalDateTimeTool(),
        )
    )
