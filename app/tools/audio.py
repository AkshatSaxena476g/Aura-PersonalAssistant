"""Controlled Windows system-volume tools for AURA Phase 6B."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from typing import Any, Protocol

from .contracts import Tool, ToolDefinition, ToolPermission, ToolResult, ToolValidationError

logger = logging.getLogger(__name__)

_DEFAULT_ADJUSTMENT = 10
_MAX_ADJUSTMENT = 50


class _EndpointVolume(Protocol):
    @property
    def volume_percent(self) -> float: ...

    @volume_percent.setter
    def volume_percent(self, value: float) -> None: ...

    def GetMute(self) -> int: ...

    def SetMute(self, mute: int, event_context: object | None) -> None: ...


class _EndpointVolumeAdapter:
    """Expose pycaw's COM pointer through AURA's normalized volume contract."""

    def __init__(self, interface: Any) -> None:
        self._interface = interface

    @property
    def volume_percent(self) -> float:
        return float(self._interface.GetMasterVolumeLevelScalar()) * 100

    @volume_percent.setter
    def volume_percent(self, value: float) -> None:
        self._interface.SetMasterVolumeLevelScalar(value / 100, None)

    def GetMute(self) -> int:
        return int(self._interface.GetMute())

    def SetMute(self, mute: int, event_context: object | None) -> None:
        self._interface.SetMute(mute, event_context)


class _AudioBackend(Protocol):
    def endpoint_volume(self) -> _EndpointVolume: ...


class _PycawBackend:
    """Lazy pycaw adapter so unsupported platforms do not import COM modules."""

    def endpoint_volume(self) -> _EndpointVolume:
        if sys.platform != "win32":
            raise OSError("Windows Core Audio is unavailable on this platform")
        try:
            import comtypes
            from pycaw.api.endpointvolume import IAudioEndpointVolume
            from pycaw.pycaw import AudioUtilities

            speakers = AudioUtilities.GetSpeakers()
            if speakers is None:
                raise OSError("The default audio endpoint is unavailable")

            endpoint_volume = getattr(speakers, "EndpointVolume", None)
            if endpoint_volume is None and callable(
                getattr(speakers, "GetMasterVolumeLevelScalar", None)
            ):
                endpoint_volume = speakers
            if endpoint_volume is not None:
                return _EndpointVolumeAdapter(endpoint_volume)

            device = getattr(speakers, "_dev", speakers)
            activate = getattr(device, "Activate", None)
            if not callable(activate):
                raise OSError("The default audio endpoint cannot be activated")
            interface = activate(
                IAudioEndpointVolume._iid_,
                comtypes.CLSCTX_ALL,
                None,
            )
            endpoint_volume = interface.QueryInterface(IAudioEndpointVolume)
            if endpoint_volume is None:
                raise OSError("The endpoint volume interface is unavailable")
            return _EndpointVolumeAdapter(endpoint_volume)
        except (ImportError, AttributeError, OSError) as error:
            raise OSError("The Windows audio interface is unavailable") from error


class _AudioTool(Tool):
    """Base class for SAFE system-volume tools."""

    def __init__(self, backend: _AudioBackend | None = None) -> None:
        self._backend = backend or _PycawBackend()

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.SAFE

    def _get_endpoint(self) -> _EndpointVolume:
        return self._backend.endpoint_volume()

    @staticmethod
    def _volume_result(volume: int, message: str) -> ToolResult:
        return ToolResult.ok(message, data={"volume": volume})

    @staticmethod
    def _normalized_volume(endpoint: _EndpointVolume) -> int:
        value = float(endpoint.volume_percent)
        return max(0, min(100, round(value)))

    @staticmethod
    def _no_argument_definition(name: str, description: str) -> ToolDefinition:
        return ToolDefinition(
            name=name,
            description=description,
            permission=ToolPermission.SAFE,
        )

    def _execute_audio(self, operation) -> ToolResult:
        if sys.platform != "win32":
            return ToolResult.failure(
                "System audio controls are available only on Windows.",
                error_code="unsupported_platform",
            )
        try:
            if isinstance(self._backend, _PycawBackend):
                import comtypes

                comtypes.CoInitialize()
                try:
                    return operation(self._get_endpoint())
                finally:
                    comtypes.CoUninitialize()
            return operation(self._get_endpoint())
        except Exception:
            logger.error("Audio operation failed for tool=%s", self.definition.name)
            return ToolResult.failure(
                "The Windows audio operation could not be completed.",
                error_code="audio_control_failed",
            )


class GetVolumeTool(_AudioTool):
    """Read the current default output endpoint volume as a percentage."""

    @property
    def definition(self) -> ToolDefinition:
        return self._no_argument_definition(
            "get_volume",
            "Read the current Windows system output volume as a percentage.",
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        def read(endpoint: _EndpointVolume) -> ToolResult:
            volume = self._normalized_volume(endpoint)
            return self._volume_result(volume, f"System volume is {volume}%.")

        return self._execute_audio(read)


class SetVolumeTool(_AudioTool):
    """Set the default output endpoint volume to a whole percentage."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="set_volume",
            description="Set the Windows system output volume to a whole percentage from 0 to 100.",
            permission=ToolPermission.SAFE,
            input_schema={
                "type": "object",
                "properties": {
                    "volume": {
                        "type": "number",
                        "description": "Whole-number volume percentage from 0 through 100.",
                    }
                },
                "required": ["volume"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        volume = validated["volume"]
        if isinstance(volume, float) and not volume.is_integer():
            raise ToolValidationError("Volume must be a whole-number percentage")
        if not 0 <= volume <= 100:
            raise ToolValidationError("Volume must be between 0 and 100")
        validated["volume"] = int(volume)
        return validated

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        volume = int(arguments["volume"])

        def write(endpoint: _EndpointVolume) -> ToolResult:
            endpoint.volume_percent = float(volume)
            return self._volume_result(volume, f"System volume set to {volume}%.")

        return self._execute_audio(write)


class _RelativeVolumeTool(_AudioTool):
    """Base class for bounded volume adjustments."""

    direction: int
    action: str
    verb: str

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.action,
            description=(
                f"Adjust the Windows system output volume {self.verb} by an optional "
                f"amount from 1 to {_MAX_ADJUSTMENT} percentage points; defaults to {_DEFAULT_ADJUSTMENT}."
            ),
            permission=ToolPermission.SAFE,
            input_schema={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": f"Whole-number adjustment from 1 to {_MAX_ADJUSTMENT}; defaults to {_DEFAULT_ADJUSTMENT}.",
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        amount = validated.get("amount", _DEFAULT_ADJUSTMENT)
        if isinstance(amount, float) and not amount.is_integer():
            raise ToolValidationError("Volume adjustment must be a whole number")
        if not 1 <= amount <= _MAX_ADJUSTMENT:
            raise ToolValidationError(
                f"Volume adjustment must be between 1 and {_MAX_ADJUSTMENT}"
            )
        validated["amount"] = int(amount)
        return validated

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        amount = int(arguments.get("amount", _DEFAULT_ADJUSTMENT))

        def adjust(endpoint: _EndpointVolume) -> ToolResult:
            current = self._normalized_volume(endpoint)
            resulting = max(0, min(100, current + self.direction * amount))
            endpoint.volume_percent = float(resulting)
            return self._volume_result(
                resulting,
                f"System volume adjusted {self.verb} to {resulting}%.",
            )

        return self._execute_audio(adjust)


class VolumeUpTool(_RelativeVolumeTool):
    """Increase system volume by a bounded amount."""

    direction = 1
    action = "volume_up"
    verb = "up"


class VolumeDownTool(_RelativeVolumeTool):
    """Decrease system volume by a bounded amount."""

    direction = -1
    action = "volume_down"
    verb = "down"


class MuteTool(_AudioTool):
    """Explicitly mute the default output endpoint."""

    @property
    def definition(self) -> ToolDefinition:
        return self._no_argument_definition(
            "mute", "Mute the Windows system output audio explicitly."
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        def mute(endpoint: _EndpointVolume) -> ToolResult:
            endpoint.SetMute(1, None)
            return ToolResult.ok("System audio muted.", data={"muted": True})

        return self._execute_audio(mute)


class UnmuteTool(_AudioTool):
    """Explicitly unmute the default output endpoint."""

    @property
    def definition(self) -> ToolDefinition:
        return self._no_argument_definition(
            "unmute", "Unmute the Windows system output audio explicitly."
        )

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        def unmute(endpoint: _EndpointVolume) -> ToolResult:
            endpoint.SetMute(0, None)
            return ToolResult.ok("System audio unmuted.", data={"muted": False})

        return self._execute_audio(unmute)


__all__ = [
    "GetVolumeTool",
    "MuteTool",
    "SetVolumeTool",
    "UnmuteTool",
    "VolumeDownTool",
    "VolumeUpTool",
]
