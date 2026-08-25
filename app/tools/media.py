"""Controlled Windows global media playback tools for AURA Phase 6B."""

from __future__ import annotations

import ctypes
import logging
import sys
from collections.abc import Mapping
from typing import Any
from ctypes import wintypes

from .contracts import Tool, ToolDefinition, ToolPermission, ToolResult

logger = logging.getLogger(__name__)

_INPUT_KEYBOARD = 1
_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP = 0x0002
_VK_MEDIA_NEXT_TRACK = 0xB0
_VK_MEDIA_PREV_TRACK = 0xB1
_VK_MEDIA_PLAY_PAUSE = 0xB3


class _KeyboardInput(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class _MouseInput(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class _HardwareInput(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class _InputUnion(ctypes.Union):
    _fields_ = (
        ("mi", _MouseInput),
        ("ki", _KeyboardInput),
        ("hi", _HardwareInput),
    )


class _Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = (
        ("type", wintypes.DWORD),
        ("data", _InputUnion),
    )


def _send_media_virtual_key(virtual_key: int) -> None:
    """Send one fixed media-key press/release pair through User32.SendInput."""

    if sys.platform != "win32":
        raise OSError("Windows media input is unavailable on this platform")

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        send_input = user32.SendInput
        send_input.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(_Input),
            ctypes.c_int,
        )
        send_input.restype = wintypes.UINT

        flags = _KEYEVENTF_EXTENDEDKEY
        inputs = (_Input * 2)(
            _Input(
                type=_INPUT_KEYBOARD,
                ki=_KeyboardInput(wVk=virtual_key, dwFlags=flags),
            ),
            _Input(
                type=_INPUT_KEYBOARD,
                ki=_KeyboardInput(
                    wVk=virtual_key,
                    dwFlags=flags | _KEYEVENTF_KEYUP,
                ),
            ),
        )
        sent = send_input(2, inputs, ctypes.sizeof(_Input))
    except (AttributeError, OSError, TypeError, ValueError) as error:
        raise OSError("Windows media input could not be sent") from error

    if sent != 2:
        raise OSError("Windows media input was not accepted")


class _MediaTool(Tool):
    """Base class for an explicit fixed media action."""

    virtual_key: int
    action_name: str
    result_label: str

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.action_name,
            description=(
                f"Send the predefined global {self.result_label.lower()} media action. "
                "This tool accepts no arguments."
            ),
            permission=ToolPermission.SAFE,
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        """Send the fixed action and normalize platform/API failures."""

        if sys.platform != "win32":
            return ToolResult.failure(
                "Global media controls are available only on Windows.",
                error_code="unsupported_platform",
            )

        try:
            _send_media_virtual_key(self.virtual_key)
        except Exception:
            logger.error("Media command failed for tool=%s", self.action_name)
            return ToolResult.failure(
                f"The {self.result_label.lower()} media command could not be sent.",
                error_code="media_command_failed",
            )

        return ToolResult.ok(
            f"Global {self.result_label.lower()} command sent.",
            data={"action": self.action_name},
        )


class MediaPlayPauseTool(_MediaTool):
    """Send the fixed global play/pause media action."""

    virtual_key = _VK_MEDIA_PLAY_PAUSE
    action_name = "media_play_pause"
    result_label = "play/pause"


class MediaNextTool(_MediaTool):
    """Send the fixed global next-track media action."""

    virtual_key = _VK_MEDIA_NEXT_TRACK
    action_name = "media_next"
    result_label = "next-track"


class MediaPreviousTool(_MediaTool):
    """Send the fixed global previous-track media action."""

    virtual_key = _VK_MEDIA_PREV_TRACK
    action_name = "media_previous"
    result_label = "previous-track"


__all__ = ["MediaNextTool", "MediaPlayPauseTool", "MediaPreviousTool"]
