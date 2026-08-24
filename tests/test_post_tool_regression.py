from collections.abc import Mapping, Sequence
from typing import Any

from app.ai import ChatMessage, MessageRole, ProviderResponse, ToolCallRequest
from app.config import Settings
from app.core import ConversationService, ToolExecutionService
from app.tools import Tool, ToolDefinition, ToolPermission, ToolRegistry, ToolResult


class SequencedProvider:
    name = "fake-sequence"

    def __init__(self, responses: Sequence[ProviderResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[ChatMessage, ...]] = []

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tool_definitions=(),
    ) -> ProviderResponse:
        self.calls.append(tuple(messages))
        return self.responses.pop(0)


class CountingStatusTool(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_application_status",
            description="Report whether AURA is running.",
            permission=ToolPermission.SAFE,
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        return ToolResult.ok("AURA is running.")


class CountingLaunchTool(Tool):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="launch_application",
            description="Launch the approved Calculator application.",
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema={
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "enum": ["calculator"],
                    }
                },
                "required": ["application"],
                "additionalProperties": False,
            },
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls += 1
        return ToolResult.ok("Calculator was opened successfully.")


def _conversation(
    provider: SequencedProvider,
    status_tool: CountingStatusTool,
    launch_tool: CountingLaunchTool,
) -> ConversationService:
    return ConversationService(
        provider,
        system_message=ChatMessage(MessageRole.SYSTEM, "You are AURA."),
        tool_service=ToolExecutionService(
            ToolRegistry([status_tool, launch_tool])
        ),
    )


def test_next_unrelated_message_is_a_new_turn_after_approval() -> None:
    status_tool = CountingStatusTool()
    launch_tool = CountingLaunchTool()
    provider = SequencedProvider(
        [
            ProviderResponse(
                message=ChatMessage(MessageRole.ASSISTANT, "Hello from AURA.")
            ),
            ProviderResponse(
                tool_call=ToolCallRequest(
                    name="launch_application",
                    arguments={"application": "calculator"},
                    call_id="launch-1",
                )
            ),
            ProviderResponse(
                message=ChatMessage(
                    MessageRole.ASSISTANT,
                    "I do not have your name stored.",
                )
            ),
        ]
    )
    conversation = _conversation(provider, status_tool, launch_tool)

    assert conversation.send("Hello").succeeded is True
    pending = conversation.send("Open Calculator").pending_tool
    approved = conversation.approve_pending(pending.request_id)
    follow_up = conversation.send("What is my name?")

    assert approved.tool_result.success is True
    assert follow_up.succeeded is True
    assert follow_up.assistant_message.content == "I do not have your name stored."
    assert launch_tool.calls == 1
    assert status_tool.calls == 0
    assert conversation.pending_tool is None
    assert [message.content for message in provider.calls[-1]] == [
        "You are AURA.",
        "Hello",
        "Hello from AURA.",
        "Open Calculator",
        "Calculator was opened successfully.",
        "What is my name?",
    ]


def test_cancelled_request_cannot_leave_stale_state_for_next_message() -> None:
    status_tool = CountingStatusTool()
    launch_tool = CountingLaunchTool()
    provider = SequencedProvider(
        [
            ProviderResponse(
                tool_call=ToolCallRequest(
                    name="launch_application",
                    arguments={"application": "calculator"},
                    call_id="launch-2",
                )
            ),
            ProviderResponse(
                tool_call=ToolCallRequest(
                    name="launch_application",
                    arguments={"application": "calculator"},
                    call_id="launch-3",
                )
            ),
            ProviderResponse(
                message=ChatMessage(MessageRole.ASSISTANT, "I am doing well.")
            ),
        ]
    )
    conversation = _conversation(provider, status_tool, launch_tool)

    first_pending = conversation.send("Open Calculator").pending_tool
    conversation.approve_pending(first_pending.request_id)
    second_pending = conversation.send("Open Calculator again").pending_tool
    cancelled = conversation.cancel_pending(second_pending.request_id)
    follow_up = conversation.send("How are you?")

    assert cancelled.tool_result.error_code == "cancelled"
    assert follow_up.succeeded is True
    assert follow_up.assistant_message.content == "I am doing well."
    assert launch_tool.calls == 1
    assert status_tool.calls == 0
    assert conversation.pending_tool is None
    assert provider.calls[-1][-2].content == "Tool action cancelled."


def test_unrelated_close_request_does_not_select_status_tool() -> None:
    status_tool = CountingStatusTool()
    launch_tool = CountingLaunchTool()
    provider = SequencedProvider(
        [
            ProviderResponse(
                message=ChatMessage(
                    MessageRole.ASSISTANT,
                    "Closing applications is not currently supported.",
                )
            )
        ]
    )
    conversation = _conversation(provider, status_tool, launch_tool)

    result = conversation.send("Close it")

    assert result.succeeded is True
    assert result.assistant_message.content == (
        "Closing applications is not currently supported."
    )
    assert status_tool.calls == 0
    assert launch_tool.calls == 0
