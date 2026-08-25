from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai import ChatMessage, GeminiProvider, MessageRole, ProviderResponse, ToolCallRequest
from app.core import ConversationService, ToolExecutionService
from app.tools import (
    OpenYoutubeTool,
    SearchWebTool,
    SearchYoutubeTool,
    ToolPermission,
    ToolRegistry,
    create_default_tool_registry,
)


def _service(tool: object) -> ToolExecutionService:
    return ToolExecutionService(ToolRegistry([tool]))  # type: ignore[arg-type]


def test_search_web_trims_and_url_encodes_query(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)

    result = _service(SearchWebTool()).execute(
        "search_web",
        {"query": "  Python PySide6 tutorials & examples  "},
        confirmed=True,
    )

    assert result.success is True
    assert opened == [
        "https://www.google.com/search?q=Python+PySide6+tutorials+%26+examples"
    ]
    assert result.data == {"url": opened[0]}


def test_search_youtube_trims_and_url_encodes_query(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)

    result = _service(SearchYoutubeTool()).execute(
        "search_youtube",
        {"query": "  lofi / study music  "},
        confirmed=True,
    )

    assert result.success is True
    assert opened == [
        "https://www.youtube.com/results?search_query=lofi+%2F+study+music"
    ]


@pytest.mark.parametrize(
    ("tool", "arguments", "expected_fragment"),
    [
        (SearchWebTool(), {"query": "   "}, "must not be empty"),
        (SearchWebTool(), {"query": 42}, "must be of type string"),
        (SearchWebTool(), {"query": "AURA", "url": "https://evil.example"}, "Unexpected argument"),
        (SearchWebTool(), {"query": "x" * 201}, "200 characters or fewer"),
        (SearchYoutubeTool(), {"query": 42}, "must be of type string"),
        (SearchYoutubeTool(), {"query": "music", "url": "https://evil.example"}, "Unexpected argument"),
    ],
)
def test_search_tools_reject_invalid_queries_and_extra_arguments(
    tool: object,
    arguments: Mapping[str, Any],
    expected_fragment: str,
) -> None:
    result = _service(tool).execute(tool.definition.name, arguments, confirmed=True)  # type: ignore[attr-defined]

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert expected_fragment in result.message


def test_open_youtube_uses_only_fixed_homepage_and_rejects_arguments(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)
    service = _service(OpenYoutubeTool())

    result = service.execute("open_youtube", {}, confirmed=True)
    extra = service.execute(
        "open_youtube",
        {"url": "https://attacker.example"},
        confirmed=True,
    )

    assert result.success is True
    assert opened == ["https://www.youtube.com/"]
    assert extra.success is False
    assert extra.error_code == "invalid_arguments"
    assert "attacker.example" not in opened


def test_browser_tools_require_confirmation_before_opening(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)

    for tool_name, arguments in (
        ("search_web", {"query": "AURA"}),
        ("open_youtube", {}),
        ("search_youtube", {"query": "AURA"}),
    ):
        tool = {
            "search_web": SearchWebTool,
            "open_youtube": OpenYoutubeTool,
            "search_youtube": SearchYoutubeTool,
        }[tool_name]()
        result = _service(tool).execute(tool_name, arguments)
        assert result.error_code == "confirmation_required"

    assert opened == []


def test_browser_open_failure_is_safe_and_structured(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: False)

    result = _service(OpenYoutubeTool()).execute("open_youtube", {}, confirmed=True)

    assert result.success is False
    assert result.error_code == "browser_open_failed"
    assert result.message == "YouTube could not be opened in the default browser."


def test_browser_open_exception_is_safe_and_structured(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")

    def fail_open(url: str) -> bool:
        raise OSError("private browser details")

    monkeypatch.setattr("app.tools.web.webbrowser.open", fail_open)

    result = _service(SearchWebTool()).execute(
        "search_web", {"query": "AURA"}, confirmed=True
    )

    assert result.success is False
    assert result.error_code == "browser_open_failed"
    assert "private browser details" not in result.message


def test_browser_tools_report_unsupported_platform_without_opening(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "linux")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)

    result = _service(SearchWebTool()).execute(
        "search_web", {"query": "AURA"}, confirmed=True
    )

    assert result.success is False
    assert result.error_code == "unsupported_platform"
    assert opened == []


def test_phase_6a_tools_are_registered_and_confirmation_required() -> None:
    registry = create_default_tool_registry()

    assert {"search_web", "open_youtube", "search_youtube"}.issubset(registry.names)
    for name in ("search_web", "open_youtube", "search_youtube"):
        assert registry.get(name).definition.permission is ToolPermission.CONFIRMATION_REQUIRED

    assert registry.get("open_youtube").definition.input_schema["additionalProperties"] is False


def test_gemini_declarations_are_derived_from_registry_and_translate_calls() -> None:
    registry = create_default_tool_registry()
    calls: list[dict[str, Any]] = []

    def generate_content(**kwargs: Any) -> object:
        calls.append(kwargs)
        return SimpleNamespace(
            text="",
            function_calls=[
                SimpleNamespace(
                    name="search_youtube",
                    args={"query": "lofi music"},
                    id="search-1",
                )
            ],
        )

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    provider = GeminiProvider(api_key="test-key", model="gemini-test", client=fake_client)

    result = provider.complete(
        [ChatMessage(MessageRole.USER, "Search YouTube")],
        tool_definitions=registry.definitions(),
    )

    assert result.tool_call == ToolCallRequest(
        name="search_youtube",
        arguments={"query": "lofi music"},
        call_id="search-1",
    )
    declarations = calls[0]["config"].tools[0].function_declarations
    assert [declaration.name for declaration in declarations] == list(registry.names)


def test_conversation_confirmation_cancel_and_stale_approval_do_not_open_browser(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)

    class Provider:
        name = "fake"

        def complete(
            self,
            messages: Sequence[ChatMessage],
            *,
            tool_definitions=(),
        ) -> ProviderResponse:
            return ProviderResponse(
                tool_call=ToolCallRequest(
                    name="search_web",
                    arguments={"query": "AURA docs"},
                    call_id="web-1",
                )
            )

    conversation = ConversationService(
        Provider(),
        tool_service=ToolExecutionService(
            ToolRegistry([SearchWebTool()])
        ),
    )
    pending = conversation.send("Search for AURA docs").pending_tool

    assert pending is not None
    assert pending.confirmation_message.startswith("AURA is ready to run search_web")
    cancelled = conversation.cancel_pending(pending.request_id)
    late_approval = conversation.approve_pending(pending.request_id)

    assert cancelled.tool_result.error_code == "cancelled"
    assert late_approval.tool_result.error_code == "stale_confirmation"
    assert opened == []


def test_conversation_approval_opens_browser_exactly_once(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.web.sys.platform", "win32")
    opened: list[str] = []
    monkeypatch.setattr("app.tools.web.webbrowser.open", lambda url: opened.append(url) or True)

    class Provider:
        name = "fake"

        def complete(self, messages, *, tool_definitions=()):
            return ProviderResponse(
                tool_call=ToolCallRequest(
                    name="open_youtube",
                    arguments={},
                    call_id="youtube-1",
                )
            )

    conversation = ConversationService(
        Provider(),
        tool_service=ToolExecutionService(ToolRegistry([OpenYoutubeTool()])),
    )
    pending = conversation.send("Open YouTube").pending_tool

    assert pending is not None
    approved = conversation.approve_pending(pending.request_id)
    duplicate = conversation.approve_pending(pending.request_id)

    assert approved.tool_result.success is True
    assert duplicate.tool_result.error_code == "stale_confirmation"
    assert opened == ["https://www.youtube.com/"]
