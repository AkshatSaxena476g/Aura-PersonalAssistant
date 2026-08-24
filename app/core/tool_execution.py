"""Controlled, provider-independent execution of registered AURA tools."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.tools.contracts import (
    Tool,
    ToolPermission,
    ToolResult,
    ToolValidationError,
)
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)
ConfirmationHandler = Callable[[str, Mapping[str, Any]], bool]


@dataclass(frozen=True, slots=True)
class PreparedToolCall:
    """Validated tool request ready for policy-approved execution."""

    name: str
    tool: Tool
    arguments: Mapping[str, Any]
    requires_confirmation: bool


@dataclass(frozen=True, slots=True)
class ToolPreparation:
    """Result of validation and permission inspection without execution."""

    prepared: PreparedToolCall | None = None
    failure: ToolResult | None = None

    @property
    def ready(self) -> bool:
        """Return whether the request passed validation and policy inspection."""

        return self.prepared is not None and self.failure is None


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

    def prepare(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> ToolPreparation:
        """Validate a request and inspect its permission without running it."""

        if not isinstance(name, str) or not name.strip():
            return ToolPreparation(
                failure=ToolResult.failure(
                    "A tool name is required.",
                    error_code="invalid_tool_name",
                )
            )

        try:
            tool = self.registry.get(name)
        except LookupError:
            return ToolPreparation(
                failure=ToolResult.failure(
                    f"The requested tool '{name.strip()}' is not available.",
                    error_code="unknown_tool",
                )
            )

        tool_arguments: Mapping[str, Any] = {} if arguments is None else arguments
        try:
            validated_arguments = tool.validate(tool_arguments)
        except (ToolValidationError, ValueError) as error:
            return ToolPreparation(
                failure=ToolResult.failure(
                    str(error),
                    error_code="invalid_arguments",
                )
            )
        except Exception:
            logger.error("Unexpected tool validation error")
            return ToolPreparation(
                failure=ToolResult.failure(
                    "The tool arguments could not be validated.",
                    error_code="validation_error",
                )
            )

        permission = tool.definition.permission
        if permission is ToolPermission.RESTRICTED:
            return ToolPreparation(
                failure=ToolResult.failure(
                    "This tool is restricted and cannot be executed.",
                    error_code="restricted_tool",
                )
            )

        return ToolPreparation(
            prepared=PreparedToolCall(
                name=tool.definition.name,
                tool=tool,
                arguments=validated_arguments,
                requires_confirmation=(
                    permission is ToolPermission.CONFIRMATION_REQUIRED
                ),
            )
        )

    def execute_prepared(
        self,
        prepared: PreparedToolCall,
        *,
        confirmed: bool = False,
    ) -> ToolResult:
        """Execute a previously validated request only after policy approval."""

        if prepared.requires_confirmation and not confirmed:
            return ToolResult.failure(
                "User confirmation is required before this tool can run.",
                error_code="confirmation_required",
            )
        return self._execute_validated(prepared)

    def execute(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        confirmed: bool = False,
    ) -> ToolResult:
        """Execute a named tool after lookup, validation, and policy checks."""

        preparation = self.prepare(name, arguments)
        if not preparation.ready:
            assert preparation.failure is not None
            return preparation.failure

        assert preparation.prepared is not None
        if preparation.prepared.requires_confirmation and not confirmed:
            approved = False
            if self.confirmation_handler is not None:
                try:
                    approved = self.confirmation_handler(
                        preparation.prepared.name,
                        preparation.prepared.arguments,
                    )
                except Exception:
                    logger.error("Tool confirmation handler failed")
            if not approved:
                return ToolResult.failure(
                    "User confirmation is required before this tool can run.",
                    error_code="confirmation_required",
                )
        return self.execute_prepared(preparation.prepared, confirmed=True)

    @staticmethod
    def _execute_validated(prepared: PreparedToolCall) -> ToolResult:
        """Run one validated registered tool and normalize unexpected failures."""

        try:
            result = prepared.tool.execute(prepared.arguments)
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
