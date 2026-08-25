from collections.abc import Mapping
from datetime import datetime
from typing import Any

import pytest

from app.config import Settings
from app.core import Application, ToolExecutionService
from app.tools import (
    Tool,
    ToolDefinition,
    ToolPermission,
    ToolRegistry,
    ToolResult,
    ToolValidationError,
    create_default_tool_registry,
)
from app.tools.demo import GetLocalDateTimeTool


class EchoTool(Tool):
    def __init__(self, name: str = "echo", permission: ToolPermission = ToolPermission.SAFE) -> None:
        self.calls = 0
        self._definition = ToolDefinition(
            name=name,
            description="Echo a validated text value.",
            permission=permission,
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        return ToolResult.ok(arguments["text"], data={"text": arguments["text"]})


class ExplodingTool(EchoTool):
    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        raise RuntimeError("private execution details")


class InvalidResultTool(EchoTool):
    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        return "not a ToolResult"  # type: ignore[return-value]


def test_tool_registry_registers_discovers_and_prevents_duplicates() -> None:
    first = EchoTool(name="First")
    second = EchoTool(name="second")
    registry = ToolRegistry([first, second])

    assert registry.names == ("first", "second")
    assert [definition.name for definition in registry.definitions()] == [
        "First",
        "second",
    ]
    assert registry.get(" FIRST ") is first

    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool(name="FIRST"))


def test_tool_validation_rejects_missing_unexpected_and_wrong_types() -> None:
    tool = EchoTool()

    with pytest.raises(ToolValidationError, match="Missing required"):
        tool.validate({})
    with pytest.raises(ToolValidationError, match="Unexpected"):
        tool.validate({"text": "ok", "extra": True})
    with pytest.raises(ToolValidationError, match="must be of type string"):
        tool.validate({"text": 123})


def test_safe_tool_executes_with_structured_success_result() -> None:
    tool = EchoTool()
    service = ToolExecutionService(ToolRegistry([tool]))

    result = service.execute("echo", {"text": "hello"})

    assert result.success is True
    assert result.message == "hello"
    assert result.data == {"text": "hello"}
    assert result.error_code is None
    assert tool.calls == 1


def test_invalid_input_is_rejected_before_execution() -> None:
    tool = EchoTool()
    service = ToolExecutionService(ToolRegistry([tool]))

    result = service.execute("echo", {"text": 42})

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert tool.calls == 0


def test_unknown_tool_is_returned_as_structured_failure() -> None:
    service = ToolExecutionService(ToolRegistry())

    result = service.execute("missing")

    assert result.success is False
    assert result.error_code == "unknown_tool"
    assert "not available" in result.message


def test_confirmation_required_tool_does_not_execute_without_approval() -> None:
    tool = EchoTool(permission=ToolPermission.CONFIRMATION_REQUIRED)
    service = ToolExecutionService(ToolRegistry([tool]))

    result = service.execute("echo", {"text": "sensitive"})

    assert result.success is False
    assert result.error_code == "confirmation_required"
    assert tool.calls == 0


def test_confirmation_handler_can_approve_a_tool() -> None:
    tool = EchoTool(permission=ToolPermission.CONFIRMATION_REQUIRED)
    confirmations: list[tuple[str, Mapping[str, Any]]] = []

    def approve(name: str, arguments: Mapping[str, Any]) -> bool:
        confirmations.append((name, arguments))
        return True

    service = ToolExecutionService(
        ToolRegistry([tool]),
        confirmation_handler=approve,
    )
    result = service.execute("echo", {"text": "approved"})

    assert result.success is True
    assert tool.calls == 1
    assert confirmations == [("echo", {"text": "approved"})]


def test_restricted_tool_never_executes() -> None:
    tool = EchoTool(permission=ToolPermission.RESTRICTED)
    service = ToolExecutionService(ToolRegistry([tool]))

    result = service.execute("echo", {"text": "blocked"}, confirmed=True)

    assert result.success is False
    assert result.error_code == "restricted_tool"
    assert tool.calls == 0


def test_tool_execution_errors_are_safely_converted() -> None:
    tool = ExplodingTool()
    service = ToolExecutionService(ToolRegistry([tool]))

    result = service.execute("echo", {"text": "hello"})

    assert result.success is False
    assert result.error_code == "execution_error"
    assert "private execution details" not in result.message


def test_invalid_tool_result_is_safely_converted() -> None:
    tool = InvalidResultTool()
    service = ToolExecutionService(ToolRegistry([tool]))

    result = service.execute("echo", {"text": "hello"})

    assert result.success is False
    assert result.error_code == "invalid_result"


def test_default_registry_contains_safe_demos_and_controlled_launcher() -> None:
    registry = create_default_tool_registry(application_name="AURA")

    assert registry.names == (
        "get_application_status",
        "get_local_datetime",
        "launch_application",
        "open_youtube",
        "search_web",
        "search_youtube",
    )
    definitions = {
        definition.name: definition for definition in registry.definitions()
    }
    assert definitions["get_application_status"].permission is ToolPermission.SAFE
    assert definitions["get_local_datetime"].permission is ToolPermission.SAFE
    assert (
        definitions["launch_application"].permission
        is ToolPermission.CONFIRMATION_REQUIRED
    )
    assert definitions["open_youtube"].permission is ToolPermission.CONFIRMATION_REQUIRED
    assert definitions["search_web"].permission is ToolPermission.CONFIRMATION_REQUIRED
    assert definitions["search_youtube"].permission is ToolPermission.CONFIRMATION_REQUIRED


def test_local_datetime_demo_is_deterministic_when_clock_is_injected() -> None:
    fixed_time = datetime(2026, 8, 24, 12, 30, 45)
    tool = GetLocalDateTimeTool(clock=lambda: fixed_time)

    result = tool.execute({})

    assert result.success is True
    assert result.data["iso_datetime"] == "2026-08-24T12:30:45"


def test_application_exposes_the_controlled_tool_boundary() -> None:
    service = ToolExecutionService(
        create_default_tool_registry(application_name="AURA")
    )
    application = Application(
        settings=Settings.from_environment({}),
        tool_service=service,
    )

    result = application.execute_tool("get_application_status")

    assert result.success is True
    assert result.data == {"application_name": "AURA", "status": "running"}
