import os
import sys
from collections.abc import Mapping
from typing import Any

import pytest

from app.core import ToolExecutionService
from app.tools import (
    LaunchApplicationTool,
    ToolPermission,
    ToolRegistry,
)


def _service(tool: LaunchApplicationTool | None = None) -> ToolExecutionService:
    return ToolExecutionService(ToolRegistry([tool or LaunchApplicationTool()]))


def test_each_supported_application_resolves_to_a_fixed_internal_target(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    popen_calls: list[tuple[list[str], dict[str, Any]]] = []
    startfile_calls: list[str] = []

    def fake_popen(command: list[str], **kwargs: Any) -> object:
        popen_calls.append((command, kwargs))
        return object()

    def fake_startfile(target: str) -> None:
        startfile_calls.append(target)

    monkeypatch.setattr(
        "app.tools.windows_applications.subprocess.Popen",
        fake_popen,
    )
    monkeypatch.setattr(os, "startfile", fake_startfile, raising=False)
    service = _service()

    results = {
        identifier: service.execute(
            "launch_application",
            {"application": identifier},
            confirmed=True,
        )
        for identifier in ("notepad", "calculator", "settings", "file_explorer")
    }

    assert all(result.success for result in results.values())
    assert [call[0] for call in popen_calls] == [
        ["notepad.exe"],
        ["calc.exe"],
        ["explorer.exe"],
    ]
    assert all(call[1]["shell"] is False for call in popen_calls)
    assert startfile_calls == ["ms-settings:"]
    assert results["calculator"].data == {
        "application": "calculator",
        "display_name": "Calculator",
    }


def test_launcher_normalizes_controlled_identifier(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "app.tools.windows_applications.subprocess.Popen",
        lambda command, **kwargs: object(),
    )
    service = _service()

    result = service.execute(
        "launch_application",
        {"application": "  Notepad  "},
        confirmed=True,
    )

    assert result.success is True
    assert result.data["application"] == "notepad"


def test_unsupported_application_is_rejected_by_the_allow_list() -> None:
    service = _service()

    result = service.execute(
        "launch_application",
        {"application": "powershell"},
        confirmed=True,
    )

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "must be one of" in result.message


def test_arbitrary_path_and_arguments_are_rejected() -> None:
    service = _service()

    path_result = service.execute(
        "launch_application",
        {"application": "C:\\Windows\\System32\\notepad.exe"},
        confirmed=True,
    )
    arguments_result = service.execute(
        "launch_application",
        {"application": "notepad", "arguments": ["secret.txt"]},
        confirmed=True,
    )

    assert path_result.success is False
    assert path_result.error_code == "invalid_arguments"
    assert arguments_result.success is False
    assert arguments_result.error_code == "invalid_arguments"


def test_launcher_requires_confirmation_before_any_external_launch(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "app.tools.windows_applications.subprocess.Popen",
        lambda command, **kwargs: calls.append(command),
    )
    service = _service()

    result = service.execute("launch_application", {"application": "notepad"})

    assert result.success is False
    assert result.error_code == "confirmation_required"
    assert calls == []


def test_launcher_confirmation_handler_can_approve(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "app.tools.windows_applications.subprocess.Popen",
        lambda command, **kwargs: calls.append(command),
    )
    service = ToolExecutionService(
        ToolRegistry([LaunchApplicationTool()]),
        confirmation_handler=lambda name, arguments: name == "launch_application",
    )

    result = service.execute("launch_application", {"application": "notepad"})

    assert result.success is True
    assert calls == [["notepad.exe"]]


def test_popen_launch_failure_becomes_safe_structured_failure(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "app.tools.windows_applications.subprocess.Popen",
        lambda command, **kwargs: (_ for _ in ()).throw(OSError("private details")),
    )
    service = _service()

    result = service.execute(
        "launch_application",
        {"application": "notepad"},
        confirmed=True,
    )

    assert result.success is False
    assert result.error_code == "launch_failed"
    assert result.message == "Notepad could not be launched."
    assert "private details" not in result.message


def test_settings_launch_failure_becomes_safe_structured_failure(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        os,
        "startfile",
        lambda target: (_ for _ in ()).throw(OSError("private details")),
        raising=False,
    )
    service = _service()

    result = service.execute(
        "launch_application",
        {"application": "settings"},
        confirmed=True,
    )

    assert result.success is False
    assert result.error_code == "launch_failed"
    assert result.message == "Windows Settings could not be launched."


def test_launcher_reports_non_windows_platform_without_launching(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    service = _service()

    result = service.execute(
        "launch_application",
        {"application": "notepad"},
        confirmed=True,
    )

    assert result.success is False
    assert result.error_code == "unsupported_platform"


def test_launcher_is_registered_in_the_default_registry() -> None:
    from app.tools import create_default_tool_registry

    registry = create_default_tool_registry()
    definition = registry.get("launch_application").definition

    assert definition.permission is ToolPermission.CONFIRMATION_REQUIRED
    assert definition.input_schema["properties"]["application"]["enum"] == (
        "notepad",
        "calculator",
        "settings",
        "file_explorer",
    )
