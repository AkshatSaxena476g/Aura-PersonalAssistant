"""Validated, centrally registered computer-action tools for AURA."""

from .contracts import (
    Tool,
    ToolDefinition,
    ToolPermission,
    ToolResult,
    ToolValidationError,
)
from .defaults import create_default_tool_registry
from .registry import ToolRegistry
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
    FileSystemPolicy,
    GetFileInfoTool,
    ListDirectoryTool,
    ReadTextFileTool,
    SearchFilesTool,
    WriteTextFileTool,
)

__all__ = [
    "Tool",
    "ToolDefinition",
    "ToolPermission",
    "ToolRegistry",
    "ToolResult",
    "ToolValidationError",
    "LaunchApplicationTool",
    "OpenYoutubeTool",
    "SearchWebTool",
    "SearchYoutubeTool",
    "MediaNextTool",
    "MediaPlayPauseTool",
    "MediaPreviousTool",
    "GetVolumeTool",
    "SetVolumeTool",
    "VolumeUpTool",
    "VolumeDownTool",
    "MuteTool",
    "UnmuteTool",
    "FileSystemPolicy",
    "ListDirectoryTool",
    "SearchFilesTool",
    "GetFileInfoTool",
    "ReadTextFileTool",
    "CreateDirectoryTool",
    "WriteTextFileTool",
    "create_default_tool_registry",
]
