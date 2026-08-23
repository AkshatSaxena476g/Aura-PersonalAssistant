"""Provider-independent contracts for AURA tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolPermission(StrEnum):
    """Execution policy declared by a tool."""

    SAFE = "safe"
    CONFIRMATION_REQUIRED = "confirmation_required"
    RESTRICTED = "restricted"


class ToolValidationError(ValueError):
    """Raised when a tool receives arguments outside its declared schema."""


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Metadata and input schema exposed for a registered tool."""

    name: str
    description: str
    permission: ToolPermission
    input_schema: Mapping[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool name must not be empty")
        if not self.description.strip():
            raise ValueError("Tool description must not be empty")
        if self.input_schema.get("type") != "object":
            raise ValueError("Tool input schema must describe an object")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Structured outcome returned by controlled tool execution."""

    success: bool
    message: str
    data: Mapping[str, Any] | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Tool result message must not be empty")
        if self.success and self.error_code is not None:
            raise ValueError("Successful tool results cannot contain an error code")
        if not self.success and not self.error_code:
            raise ValueError("Failed tool results must contain an error code")

    @classmethod
    def ok(
        cls,
        message: str,
        *,
        data: Mapping[str, Any] | None = None,
    ) -> "ToolResult":
        """Construct a successful tool result."""

        return cls(success=True, message=message, data=data)

    @classmethod
    def failure(
        cls,
        message: str,
        *,
        error_code: str,
        data: Mapping[str, Any] | None = None,
    ) -> "ToolResult":
        """Construct a failed tool result."""

        return cls(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
        )


class Tool(ABC):
    """Base contract for explicit, validated, controlled AURA tools."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool metadata and structured input schema."""
        raise NotImplementedError

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Validate and copy arguments according to the declared schema."""

        if not isinstance(arguments, Mapping):
            raise ToolValidationError("Tool arguments must be an object")

        schema = self.definition.input_schema
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional_properties = schema.get("additionalProperties", False)

        missing = [name for name in required if name not in arguments]
        if missing:
            raise ToolValidationError(
                f"Missing required argument(s): {', '.join(sorted(missing))}"
            )

        if not additional_properties:
            unexpected = sorted(set(arguments) - set(properties))
            if unexpected:
                raise ToolValidationError(
                    f"Unexpected argument(s): {', '.join(unexpected)}"
                )

        for name, value in arguments.items():
            if name in properties:
                self._validate_value(name, value, properties[name])

        return dict(arguments)

    @staticmethod
    def _validate_value(name: str, value: Any, schema: Mapping[str, Any]) -> None:
        expected_type = schema.get("type")
        type_matches = {
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "object": isinstance(value, Mapping),
            "array": isinstance(value, list),
            "null": value is None,
        }
        if expected_type in type_matches and not type_matches[expected_type]:
            raise ToolValidationError(
                f"Argument '{name}' must be of type {expected_type}"
            )

    @abstractmethod
    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        """Execute validated arguments and return a structured result."""
        raise NotImplementedError
