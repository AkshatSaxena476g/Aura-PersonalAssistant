from collections.abc import Mapping, Sequence
from typing import Any

from app.ai import ChatMessage, MessageRole, ProviderResponse, ToolCallRequest
from app.config import Settings
from app.core import Application, ConversationService, ToolExecutionService
from app.tools import (
    Tool,
    ToolDefinition,
    ToolPermission,
    ToolRegistry,
    ToolResult,
    create_default_tool_registry,
)


class ConfirmationTool(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="confirmable_action",
            description="A test action requiring confirmation.",
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        return ToolResult.ok(f"Action completed for {arguments['value']}.")


class SafeTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="safe_action",
            description="A test safe action.",
            permission=ToolPermission.SAFE,
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        return ToolResult.ok("Safe action completed.")


class FakeToolCallingProvider:
    name = "fake"

    def __init__(self, response: ProviderResponse) -> None:
        self.response = response
        self.calls: list[tuple[tuple[ChatMessage, ...], tuple[ToolDefinition, ...]]] = []

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tool_definitions: Sequence[ToolDefinition] = (),
    ) -> ProviderResponse:
        self.calls.append((tuple(messages), tuple(tool_definitions)))
        return self.response


def test_tool_call_request_normalizes_name_arguments_and_id() -> None:
    request = ToolCallRequest(
        name=" launch_application ",
        arguments={"application": "calculator"},
        call_id=" call-1 ",
    )

    assert request.name == "launch_application"
    assert request.arguments == {"application": "calculator"}
    assert request.call_id == "call-1"


def test_conversation_derives_tool_definitions_from_registry() -> None:
    registry = ToolRegistry([SafeTool()])
    service = ToolExecutionService(registry)
    provider = FakeToolCallingProvider(
        ProviderResponse(message=ChatMessage(MessageRole.ASSISTANT, "Normal response"))
    )
    conversation = ConversationService(provider, tool_service=service)

    result = conversation.send("What can you do?")

    assert result.succeeded is True
    assert [definition.name for definition in provider.calls[0][1]] == [
        "safe_action"
    ]


def test_confirmation_required_call_creates_pending_state_without_execution() -> None:
    tool = ConfirmationTool()
    service = ToolExecutionService(ToolRegistry([tool]))
    provider = FakeToolCallingProvider(
        ProviderResponse(
            tool_call=ToolCallRequest(
                name="confirmable_action",
                arguments={"value": "calculator"},
                call_id="call-1",
            )
        )
    )
    conversation = ConversationService(provider, tool_service=service)

    result = conversation.send("Open Calculator")

    assert result.requires_confirmation is True
    assert result.pending_tool.request_id == "call-1"
    assert result.pending_tool.confirmation_message == (
        "AURA is ready to run confirmable_action. Do you want me to proceed?"
    )
    assert tool.calls == 0


def test_approval_executes_exact_pending_request_once() -> None:
    tool = ConfirmationTool()
    service = ToolExecutionService(ToolRegistry([tool]))
    provider = FakeToolCallingProvider(
        ProviderResponse(
            tool_call=ToolCallRequest(
                name="confirmable_action",
                arguments={"value": "calculator"},
                call_id="call-2",
            )
        )
    )
    conversation = ConversationService(provider, tool_service=service)
    pending = conversation.send("Open Calculator").pending_tool

    approved = conversation.approve_pending(pending.request_id)
    duplicate = conversation.approve_pending(pending.request_id)

    assert approved.tool_result.success is True
    assert tool.calls == 1
    assert duplicate.tool_result.success is False
    assert duplicate.tool_result.error_code == "stale_confirmation"


def test_cancellation_does_not_execute_and_blocks_later_approval() -> None:
    tool = ConfirmationTool()
    service = ToolExecutionService(ToolRegistry([tool]))
    provider = FakeToolCallingProvider(
        ProviderResponse(
            tool_call=ToolCallRequest(
                name="confirmable_action",
                arguments={"value": "calculator"},
                call_id="call-3",
            )
        )
    )
    conversation = ConversationService(provider, tool_service=service)
    pending = conversation.send("Open Calculator").pending_tool

    cancelled = conversation.cancel_pending(pending.request_id)
    late_approval = conversation.approve_pending(pending.request_id)

    assert cancelled.tool_result.error_code == "cancelled"
    assert tool.calls == 0
    assert late_approval.tool_result.error_code == "stale_confirmation"


def test_safe_tool_call_executes_without_confirmation() -> None:
    tool = SafeTool()
    service = ToolExecutionService(ToolRegistry([tool]))
    provider = FakeToolCallingProvider(
        ProviderResponse(tool_call=ToolCallRequest(name="safe_action", arguments={}))
    )
    conversation = ConversationService(provider, tool_service=service)

    result = conversation.send("Check status")

    assert result.pending_tool is None
    assert result.tool_result.success is True


def test_unknown_provider_tool_call_is_structured_failure() -> None:
    service = ToolExecutionService(ToolRegistry([SafeTool()]))
    provider = FakeToolCallingProvider(
        ProviderResponse(tool_call=ToolCallRequest(name="missing_tool", arguments={}))
    )
    conversation = ConversationService(provider, tool_service=service)

    result = conversation.send("Do something unsupported")

    assert result.tool_result.success is False
    assert result.tool_result.error_code == "unknown_tool"


def test_application_exposes_approval_and_cancellation_boundaries() -> None:
    tool = ConfirmationTool()
    service = ToolExecutionService(ToolRegistry([tool]))
    provider = FakeToolCallingProvider(
        ProviderResponse(
            tool_call=ToolCallRequest(
                name="confirmable_action",
                arguments={"value": "test"},
                call_id="call-4",
            )
        )
    )
    application = Application(
        settings=Settings.from_environment({}),
        provider=provider,
        tool_service=service,
    )

    pending = application.send_message("Do it").pending_tool
    result = application.approve_tool_call(pending.request_id)

    assert result.tool_result.success is True
    assert tool.calls == 1


def test_default_registry_is_the_only_source_of_exposed_tools() -> None:
    registry = create_default_tool_registry()
    service = ToolExecutionService(registry)
    provider = FakeToolCallingProvider(
        ProviderResponse(message=ChatMessage(MessageRole.ASSISTANT, "Ready"))
    )
    conversation = ConversationService(provider, tool_service=service)

    conversation.send("Hello")

    assert [definition.name for definition in provider.calls[0][1]] == list(
        registry.names
    )
