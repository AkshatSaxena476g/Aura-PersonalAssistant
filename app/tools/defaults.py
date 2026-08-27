"""Default registered tools exposed to the application and AI provider."""

from __future__ import annotations

from .demo import GetApplicationStatusTool, GetLocalDateTimeTool
from .windows_applications import LaunchApplicationTool
from .web import OpenYoutubeTool, SearchWebTool, SearchYoutubeTool
from .media import MediaNextTool, MediaPlayPauseTool, MediaPreviousTool
from .audio import (
    GetVolumeTool,
    MuteTool,
    SetVolumeTool,
    UnmuteTool,
    VolumeDownTool,
    VolumeUpTool,
)
from .file_system import (
    CreateDirectoryTool,
    GetFileInfoTool,
    ListDirectoryTool,
    ReadTextFileTool,
    SearchFilesTool,
    WriteTextFileTool,
)
from .registry import ToolRegistry


def create_default_tool_registry(*, application_name: str = "AURA") -> ToolRegistry:
    """Return the single source-of-truth registry for currently available tools."""

    return ToolRegistry(
        tools=(
            GetApplicationStatusTool(application_name=application_name),
            GetLocalDateTimeTool(),
            LaunchApplicationTool(),
            SearchWebTool(),
            OpenYoutubeTool(),
            SearchYoutubeTool(),
            MediaPlayPauseTool(),
            MediaNextTool(),
            MediaPreviousTool(),
            GetVolumeTool(),
            SetVolumeTool(),
            VolumeUpTool(),
            VolumeDownTool(),
            MuteTool(),
            UnmuteTool(),
            ListDirectoryTool(),
            SearchFilesTool(),
            GetFileInfoTool(),
            ReadTextFileTool(),
            CreateDirectoryTool(),
            WriteTextFileTool(),
        )
    )
