import ctypes
from collections.abc import Mapping
from typing import Any

import pytest

from app.core import ToolExecutionService
from app.tools import (
    MediaNextTool,
    MediaPlayPauseTool,
    MediaPreviousTool,
    ToolPermission,
    ToolRegistry,
)


@pytest.mark.parametrize(
    ("tool", "expected_key", "expected_action"),
    [
        (MediaPlayPauseTool(), 0xB3, "media_play_pause"),
        (MediaNextTool(), 0xB0, "media_next"),
        (MediaPreviousTool(), 0xB1, "media_previous"),
    ],
)
def test_media_tools_send_only_their_fixed_media_key(
    monkeypatch,
    tool: object,
    expected_key: int,
    expected_action: str,
) -> None:
    monkeypatch.setattr("app.tools.media.sys.platform", "win32")
    sent_keys: list[int] = []
    monkeypatch.setattr(
        "app.tools.media._send_media_virtual_key",
        lambda key: sent_keys.append(key),
    )

    service = ToolExecutionService(ToolRegistry([tool]))  # type: ignore[arg-type]
    result = service.execute(tool.definition.name, {}, confirmed=True)  # type: ignore[attr-defined]

    assert result.success is True
    assert result.data == {"action": expected_action}
    assert sent_keys == [expected_key]
    assert tool.definition.permission is ToolPermission.SAFE  # type: ignore[attr-defined]


def test_media_tools_accept_no_arguments(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.media.sys.platform", "win32")
    sent_keys: list[int] = []
    monkeypatch.setattr(
        "app.tools.media._send_media_virtual_key",
        lambda key: sent_keys.append(key),
    )
    service = ToolExecutionService(ToolRegistry([MediaNextTool()]))

    result = service.execute("media_next", {"key": "VK_MEDIA_NEXT_TRACK"}, confirmed=True)

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert sent_keys == []


def test_media_tool_reports_unsupported_platform_without_sending(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.media.sys.platform", "linux")
    sent_keys: list[int] = []
    monkeypatch.setattr(
        "app.tools.media._send_media_virtual_key",
        lambda key: sent_keys.append(key),
    )
    service = ToolExecutionService(ToolRegistry([MediaPlayPauseTool()]))

    result = service.execute("media_play_pause", {}, confirmed=True)

    assert result.success is False
    assert result.error_code == "unsupported_platform"
    assert sent_keys == []


def test_media_tool_normalizes_platform_failure(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.media.sys.platform", "win32")

    def fail_send(key: int) -> None:
        raise OSError("private platform detail")

    monkeypatch.setattr("app.tools.media._send_media_virtual_key", fail_send)
    service = ToolExecutionService(ToolRegistry([MediaPreviousTool()]))

    result = service.execute("media_previous", {}, confirmed=True)

    assert result.success is False
    assert result.error_code == "media_command_failed"
    assert "private platform detail" not in result.message


def test_send_input_uses_architecture_sized_input_and_press_release_pair(monkeypatch) -> None:
    from app.tools.media import (
        _Input,
        _KEYEVENTF_EXTENDEDKEY,
        _KEYEVENTF_KEYUP,
        _send_media_virtual_key,
    )

    class FakeSendInput:
        def __init__(self) -> None:
            self.calls: list[tuple[int, Any, int]] = []
            self.argtypes = None
            self.restype = None

        def __call__(self, count: int, inputs: Any, size: int) -> int:
            self.calls.append((count, inputs, size))
            return 2

    fake_send_input = FakeSendInput()
    monkeypatch.setattr(
        "app.tools.media.ctypes.WinDLL",
        lambda name, use_last_error: type(
            "FakeUser32", (), {"SendInput": fake_send_input}
        )(),
    )
    monkeypatch.setattr("app.tools.media.sys.platform", "win32")

    _send_media_virtual_key(0xB3)

    count, inputs, size = fake_send_input.calls[0]
    assert count == 2
    assert size == ctypes.sizeof(_Input)
    assert inputs[0].ki.wVk == 0xB3
    assert inputs[0].ki.dwFlags == _KEYEVENTF_EXTENDEDKEY
    assert inputs[1].ki.dwFlags == _KEYEVENTF_EXTENDEDKEY | _KEYEVENTF_KEYUP
