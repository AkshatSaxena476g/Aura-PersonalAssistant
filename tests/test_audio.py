from collections.abc import Mapping
from typing import Any

import pytest

from app.core import ToolExecutionService
from app.tools import (
    GetVolumeTool,
    MuteTool,
    SetVolumeTool,
    ToolRegistry,
    UnmuteTool,
    VolumeDownTool,
    VolumeUpTool,
)


class FakeEndpoint:
    def __init__(self, volume: float = 50.0) -> None:
        self.volume_percent = volume
        self.mute_calls: list[int] = []

    def GetMute(self) -> int:
        return self.mute_calls[-1] if self.mute_calls else 0

    def SetMute(self, mute: int, event_context: object | None) -> None:
        self.mute_calls.append(mute)


class FakeBackend:
    def __init__(self, endpoint: FakeEndpoint | None = None, error: Exception | None = None) -> None:
        self.endpoint = endpoint or FakeEndpoint()
        self.error = error

    def endpoint_volume(self) -> FakeEndpoint:
        if self.error is not None:
            raise self.error
        return self.endpoint


def _service(tool: object) -> ToolExecutionService:
    return ToolExecutionService(ToolRegistry([tool]))  # type: ignore[arg-type]


def _win(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.audio.sys.platform", "win32")


def test_get_volume_returns_normalized_percentage_and_data(monkeypatch) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint(63.6)

    result = _service(GetVolumeTool(FakeBackend(endpoint))).execute(
        "get_volume", {}, confirmed=True
    )

    assert result.success is True
    assert result.message == "System volume is 64%."
    assert result.data == {"volume": 64}


@pytest.mark.parametrize("volume", [0, 50, 100])
def test_set_volume_accepts_whole_percentages(monkeypatch, volume: int) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint()

    result = _service(SetVolumeTool(FakeBackend(endpoint))).execute(
        "set_volume", {"volume": volume}, confirmed=True
    )

    assert result.success is True
    assert endpoint.volume_percent == float(volume)
    assert result.data == {"volume": volume}


@pytest.mark.parametrize(
    ("arguments", "expected_fragment"),
    [
        ({"volume": -1}, "between 0 and 100"),
        ({"volume": 101}, "between 0 and 100"),
        ({"volume": 50.5}, "whole-number"),
        ({"volume": "50"}, "must be of type number"),
        ({"volume": 50, "extra": True}, "Unexpected argument"),
    ],
)
def test_set_volume_rejects_invalid_values(
    monkeypatch,
    arguments: Mapping[str, Any],
    expected_fragment: str,
) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint(25)

    result = _service(SetVolumeTool(FakeBackend(endpoint))).execute(
        "set_volume", arguments, confirmed=True
    )

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert expected_fragment in result.message
    assert endpoint.volume_percent == 25


def test_volume_up_uses_default_and_clamps_to_100(monkeypatch) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint(95)

    result = _service(VolumeUpTool(FakeBackend(endpoint))).execute(
        "volume_up", {}, confirmed=True
    )

    assert result.success is True
    assert endpoint.volume_percent == 100.0
    assert result.data == {"volume": 100}


def test_volume_down_uses_explicit_amount_and_clamps_to_zero(monkeypatch) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint(5)

    result = _service(VolumeDownTool(FakeBackend(endpoint))).execute(
        "volume_down", {"amount": 20}, confirmed=True
    )

    assert result.success is True
    assert endpoint.volume_percent == 0.0
    assert result.data == {"volume": 0}


@pytest.mark.parametrize("tool_class", [VolumeUpTool, VolumeDownTool])
def test_relative_volume_rejects_invalid_amounts(monkeypatch, tool_class) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint(50)
    service = _service(tool_class(FakeBackend(endpoint)))

    negative = service.execute(tool_class.action, {"amount": -1}, confirmed=True)
    too_large = service.execute(tool_class.action, {"amount": 51}, confirmed=True)
    fractional = service.execute(tool_class.action, {"amount": 1.5}, confirmed=True)
    wrong_type = service.execute(tool_class.action, {"amount": "10"}, confirmed=True)

    for result, fragment in (
        (negative, "between 1 and 50"),
        (too_large, "between 1 and 50"),
        (fractional, "whole number"),
        (wrong_type, "must be of type number"),
    ):
        assert result.success is False
        assert result.error_code == "invalid_arguments"
        assert fragment in result.message
    assert endpoint.volume_percent == 50


def test_mute_and_unmute_set_explicit_states(monkeypatch) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint()
    service = ToolExecutionService(
        ToolRegistry([MuteTool(FakeBackend(endpoint)), UnmuteTool(FakeBackend(endpoint))])
    )

    muted = service.execute("mute", {}, confirmed=True)
    unmuted = service.execute("unmute", {}, confirmed=True)

    assert muted.success is True
    assert muted.data == {"muted": True}
    assert unmuted.success is True
    assert unmuted.data == {"muted": False}
    assert endpoint.mute_calls == [1, 0]


def test_audio_tools_are_safe_and_no_argument_tools_reject_extras(monkeypatch) -> None:
    _win(monkeypatch)
    endpoint = FakeEndpoint()
    service = _service(GetVolumeTool(FakeBackend(endpoint)))

    result = service.execute("get_volume", {"volume": 50}, confirmed=True)

    assert result.success is False
    assert result.error_code == "invalid_arguments"


def test_audio_tools_report_unsupported_platform(monkeypatch) -> None:
    monkeypatch.setattr("app.tools.audio.sys.platform", "linux")
    endpoint = FakeEndpoint(50)

    result = _service(GetVolumeTool(FakeBackend(endpoint))).execute(
        "get_volume", {}, confirmed=True
    )

    assert result.success is False
    assert result.error_code == "unsupported_platform"
    assert endpoint.volume_percent == 50


def test_audio_backend_failure_is_safe_and_structured(monkeypatch) -> None:
    _win(monkeypatch)
    service = _service(GetVolumeTool(FakeBackend(error=OSError("private audio details"))))

    result = service.execute("get_volume", {}, confirmed=True)

    assert result.success is False
    assert result.error_code == "audio_control_failed"
    assert "private audio details" not in result.message


class FakePycawEndpoint:
    def __init__(self) -> None:
        self.volume_scalar = 0.42
        self.set_volume_calls: list[tuple[float, object | None]] = []
        self.mute = 0
        self.set_mute_calls: list[tuple[int, object | None]] = []

    def GetMasterVolumeLevelScalar(self) -> float:
        return self.volume_scalar

    def SetMasterVolumeLevelScalar(self, scalar: float, event_context: object | None) -> None:
        self.set_volume_calls.append((scalar, event_context))
        self.volume_scalar = scalar

    def GetMute(self) -> int:
        return self.mute

    def SetMute(self, mute: int, event_context: object | None) -> None:
        self.set_mute_calls.append((mute, event_context))
        self.mute = mute


def test_pycaw_endpoint_adapter_normalizes_com_pointer_interface() -> None:
    from app.tools.audio import _EndpointVolumeAdapter

    interface = FakePycawEndpoint()
    endpoint = _EndpointVolumeAdapter(interface)

    assert endpoint.volume_percent == 42.0
    endpoint.volume_percent = 75.0
    endpoint.SetMute(1, None)

    assert interface.set_volume_calls == [(0.75, None)]
    assert endpoint.volume_percent == 75.0
    assert endpoint.GetMute() == 1
    assert interface.set_mute_calls == [(1, None)]
