"""Controlled web and YouTube browser-opening tools for AURA Phase 6A."""

from __future__ import annotations

import logging
import sys
import webbrowser
from abc import abstractmethod
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote_plus

from .contracts import Tool, ToolDefinition, ToolPermission, ToolResult, ToolValidationError

logger = logging.getLogger(__name__)

_SEARCH_QUERY_MAX_LENGTH = 200
_GOOGLE_SEARCH_ENDPOINT = "https://www.google.com/search?q="
_YOUTUBE_HOME_URL = "https://www.youtube.com/"
_YOUTUBE_SEARCH_ENDPOINT = "https://www.youtube.com/results?search_query="


def _query_schema(description: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": description,
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    }


class _BrowserOpeningTool(Tool):
    """Shared safe execution boundary for fixed, internally generated destinations."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return a user-facing action name without exposing implementation details."""
        raise NotImplementedError

    @abstractmethod
    def _build_url(self, arguments: Mapping[str, Any]) -> str:
        """Build a URL exclusively from internal constants and validated arguments."""
        raise NotImplementedError

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        """Open one internally generated URL with the registered default browser."""

        if sys.platform != "win32":
            return ToolResult.failure(
                "Browser actions are available only on Windows.",
                error_code="unsupported_platform",
            )

        try:
            url = self._build_url(arguments)
            if not url.startswith(("https://www.google.com/", "https://www.youtube.com/")):
                raise ValueError("Unsupported internal browser destination")
            opened = webbrowser.open(url)
        except Exception:
            logger.error("Browser opening failed for tool=%s", self.definition.name)
            return ToolResult.failure(
                f"{self.display_name} could not be opened in the default browser.",
                error_code="browser_open_failed",
            )

        if not opened:
            return ToolResult.failure(
                f"{self.display_name} could not be opened in the default browser.",
                error_code="browser_open_failed",
            )

        return ToolResult.ok(
            f"{self.display_name} opened in the default browser.",
            data={"url": url},
        )


class _ValidatedQueryTool(_BrowserOpeningTool):
    """Base implementation for tools that accept only one bounded search query."""

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Normalize and strictly validate the query before URL construction."""

        normalized = dict(arguments) if isinstance(arguments, Mapping) else arguments
        if isinstance(normalized, dict) and isinstance(normalized.get("query"), str):
            normalized["query"] = normalized["query"].strip()

        validated = super().validate(normalized)
        query = validated["query"]
        if not query:
            raise ToolValidationError("Search query must not be empty")
        if len(query) > _SEARCH_QUERY_MAX_LENGTH:
            raise ToolValidationError(
                f"Search query must be { _SEARCH_QUERY_MAX_LENGTH } characters or fewer"
            )
        return validated


class SearchWebTool(_ValidatedQueryTool):
    """Search Google using a validated query and the default Windows browser."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_web",
            description=(
                "Open a Google web search for a validated query. The application "
                "constructs the destination; URLs and browser arguments are not accepted."
            ),
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema=_query_schema("The web search terms to look up."),
        )

    @property
    def display_name(self) -> str:
        return "Web search"

    def _build_url(self, arguments: Mapping[str, Any]) -> str:
        return _GOOGLE_SEARCH_ENDPOINT + quote_plus(arguments["query"], safe="")


class OpenYoutubeTool(_BrowserOpeningTool):
    """Open only the fixed official YouTube homepage."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="open_youtube",
            description=(
                "Open the official YouTube homepage. The destination is fixed by "
                "the application and no URL or arguments are accepted."
            ),
            permission=ToolPermission.CONFIRMATION_REQUIRED,
        )

    @property
    def display_name(self) -> str:
        return "YouTube"

    def _build_url(self, arguments: Mapping[str, Any]) -> str:
        return _YOUTUBE_HOME_URL


class SearchYoutubeTool(_ValidatedQueryTool):
    """Search YouTube using a validated query and the default Windows browser."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_youtube",
            description=(
                "Open a YouTube search for a validated query. The application "
                "constructs the destination; URLs and browser arguments are not accepted."
            ),
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema=_query_schema("The YouTube search terms to look up."),
        )

    @property
    def display_name(self) -> str:
        return "YouTube search"

    def _build_url(self, arguments: Mapping[str, Any]) -> str:
        return _YOUTUBE_SEARCH_ENDPOINT + quote_plus(arguments["query"], safe="")


__all__ = ["OpenYoutubeTool", "SearchWebTool", "SearchYoutubeTool"]
