"""Controlled, provider-independent execution of registered AURA tools."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from app.tools.contracts import ToolPermission, ToolResult, ToolValidationError
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)
ConfirmationHandler = Callable[[str, Mapping[str, Any]], bool]


class ToolExecutionService:
    """Validate and execute only explicitly registered and permitted tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        confirmation_handler: ConfirmationHandler | None = None,
    ) -> None:
        self.registry = registry
        self.confirmation_handler = confirmation_handler

    def execute(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        confirmed: bool = False,
    ) -> ToolResult:
        """Execute a named tool after lookup, validation, and policy checks."""

        if not isinstance(name, str) or not name.strip():
            return ToolResult.failure(
                "A tool name is required.",
                error_code="invalid_tool_name",
            )

        try:
            tool = self.registry.get(name)
        except LookupError:
            return ToolResult.failure(
                f"The requested tool '{name.strip()}' is not available.",
                error_code="unknown_tool",
            )

        tool_arguments: Mapping[str, Any] = {} if arguments is None else arguments
        try:
            validated_arguments = tool.validate(tool_arguments)
        except (ToolValidationError, ValueError) as error:
            return ToolResult.failure(
                str(error),
                error_code="invalid_arguments",
            )
        except Exception:
            logger.error("Unexpected tool validation error")
            return ToolResult.failure(
                "The tool arguments could not be validated.",
                error_code="validation_error",
            )

        permission = tool.definition.permission
        if permission is ToolPermission.RESTRICTED:
            return ToolResult.failure(
                "This tool is restricted and cannot be executed.",
                error_code="restricted_tool",
            )

        if permission is ToolPermission.CONFIRMATION_REQUIRED:
            approved = confirmed
            if not approved and self.confirmation_handler is not None:
                try:
                    approved = self.confirmation_handler(
                        tool.definition.name,
                        validated_arguments,
                    )
                except Exception:
                    logger.error("Tool confirmation handler failed")
                    approved = False
            if not approved:
                return ToolResult.failure(
                    "User confirmation is required before this tool can run.",
                    error_code="confirmation_required",
                )

        try:
            result = tool.execute(validated_arguments)
        except Exception:
            logger.error("Tool execution failed for a registered tool")
            return ToolResult.failure(
                "The tool could not complete successfully.",
                error_code="execution_error",
            )

        if not isinstance(result, ToolResult):
            logger.error("Registered tool returned an invalid result type")
            return ToolResult.failure(
                "The tool returned an invalid result.",
                error_code="invalid_result",
            )
        return result
