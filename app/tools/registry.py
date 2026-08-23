"""Central registry for explicit AURA tools."""

from __future__ import annotations

from collections.abc import Iterable

from .contracts import Tool, ToolDefinition


class ToolRegistry:
    """Store and discover tools independently from AI providers."""

    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        if tools is not None:
            for tool in tools:
                self.register(tool)

    def register(self, tool: Tool) -> None:
        """Register a tool using its normalized unique definition name."""

        name = tool.definition.name.strip().lower()
        if not name:
            raise ValueError("Tool name must not be empty")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        """Return a registered tool or raise a clear lookup error."""

        normalized_name = name.strip().lower()
        try:
            return self._tools[normalized_name]
        except KeyError as error:
            available = ", ".join(self.names) or "none"
            raise LookupError(
                f"Unknown tool '{name}'. Available tools: {available}"
            ) from error

    def definitions(self) -> tuple[ToolDefinition, ...]:
        """Return public tool definitions in deterministic name order."""

        return tuple(self._tools[name].definition for name in self.names)

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered tool names in deterministic order."""

        return tuple(sorted(self._tools))
