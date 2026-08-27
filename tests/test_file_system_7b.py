from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core import ToolExecutionService
from app.core.conversation import ConversationService
from app.ai.provider import ChatMessage, MessageRole, ProviderResponse, ToolCallRequest
from app.tools import (
    CreateDirectoryTool,
    FileSystemPolicy,
    ToolRegistry,
    WriteTextFileTool,
)
from app.tools.file_system import MAX_WRITE_CONTENT_CHARACTERS


@pytest.fixture
def policy(tmp_path: Path) -> FileSystemPolicy:
    roots = {
        name: tmp_path / name
        for name in ("desktop", "documents", "downloads", "pictures", "music", "videos")
    }
    for root in roots.values():
        root.mkdir()
    return FileSystemPolicy(roots=roots)


def execute(
    tool: object,
    name: str,
    arguments: dict[str, Any],
    *,
    policy: FileSystemPolicy,
    confirmed: bool = True,
):
    return ToolExecutionService(ToolRegistry([tool])).execute(
        name, arguments, confirmed=confirmed
    )


def test_create_directory_success_and_nested(policy: FileSystemPolicy) -> None:
    tool = CreateDirectoryTool(policy)
    result = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "Projects"},
        policy=policy,
    )
    assert result.success is True
    assert result.data["relative_path"] == "Projects"
    assert (policy.roots["documents"] / "Projects").is_dir()

    nested = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "Projects/Nested"},
        policy=policy,
    )
    assert nested.success is True
    assert (policy.roots["documents"] / "Projects" / "Nested").is_dir()


def test_create_directory_rejects_existing_and_missing_parent(
    policy: FileSystemPolicy,
) -> None:
    tool = CreateDirectoryTool(policy)
    execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "Existing"},
        policy=policy,
    )
    exists = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "Existing"},
        policy=policy,
    )
    assert exists.success is False
    assert exists.error_code == "target_exists"

    missing_parent = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "NoParent/Child"},
        policy=policy,
    )
    assert missing_parent.success is False
    assert missing_parent.error_code == "parent_not_found"

    (policy.roots["documents"] / "file.txt").write_text("x", encoding="utf-8")
    parent_is_file = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "file.txt/Child"},
        policy=policy,
    )
    assert parent_is_file.success is False
    assert parent_is_file.error_code in {"parent_not_found", "path_not_allowed"}


def test_create_directory_rejects_traversal_absolute_and_network(
    policy: FileSystemPolicy,
) -> None:
    tool = CreateDirectoryTool(policy)
    for path in [
        "../outside",
        "nested/../../outside",
        "C:\\Windows\\Temp\\evil",
        "\\\\server\\share\\evil",
        "//server/share/evil",
        "/etc/passwd",
    ]:
        result = execute(
            tool,
            "create_directory",
            {"location": "documents", "path": path},
            policy=policy,
        )
        assert result.success is False
        assert result.error_code in {
            "invalid_arguments",
            "path_not_allowed",
            "path_validation_error",
        }


def test_create_directory_rejects_sibling_prefix_and_symlink_escape(
    policy: FileSystemPolicy, tmp_path: Path
) -> None:
    sibling = tmp_path / "documents_backup"
    sibling.mkdir(exist_ok=True)
    tool = CreateDirectoryTool(policy)
    result = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "../documents_backup/Evil"},
        policy=policy,
    )
    assert result.success is False

    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    link = policy.roots["documents"] / "link-outside"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this Windows test environment")
    escaped = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "link-outside/EvilDir"},
        policy=policy,
    )
    assert escaped.success is False
    assert escaped.error_code == "path_not_allowed"


def test_create_directory_rejects_invalid_filenames(policy: FileSystemPolicy) -> None:
    tool = CreateDirectoryTool(policy)
    invalid_names = [
        "CON",
        "NUL",
        "COM1",
        "file<name",
        "file|name",
        "file?",
        "file*",
        'file"name',
        "a/b/CON",
        "test/aux.txt",
    ]
    for name in invalid_names:
        result = execute(
            tool,
            "create_directory",
            {"location": "documents", "path": name},
            policy=policy,
        )
        assert result.success is False
        assert result.error_code in {
            "invalid_arguments",
            "invalid_path",
            "path_not_allowed",
        }


def test_create_directory_rejects_extra_arguments_and_empty(
    policy: FileSystemPolicy,
) -> None:
    tool = CreateDirectoryTool(policy)
    empty = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "   "},
        policy=policy,
    )
    assert empty.success is False
    assert empty.error_code == "invalid_arguments"

    extra = execute(
        tool,
        "create_directory",
        {"location": "documents", "path": "Valid", "extra": True},
        policy=policy,
    )
    assert extra.success is False
    assert extra.error_code == "invalid_arguments"


def test_write_text_file_creates_and_overwrites(policy: FileSystemPolicy) -> None:
    tool = WriteTextFileTool(policy)
    created = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "notes.txt", "content": "hello"},
        policy=policy,
    )
    assert created.success is True
    assert created.data["relative_path"] == "notes.txt"
    assert (policy.roots["documents"] / "notes.txt").read_text(
        encoding="utf-8"
    ) == "hello"

    overwritten = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "notes.txt", "content": "world"},
        policy=policy,
    )
    assert overwritten.success is True
    assert (policy.roots["documents"] / "notes.txt").read_text(
        encoding="utf-8"
    ) == "world"

    nested_parent = policy.roots["documents"] / "Sub"
    nested_parent.mkdir()
    nested = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "Sub/nested.md", "content": "# hi"},
        policy=policy,
    )
    assert nested.success is True
    assert nested.data["relative_path"] == "Sub/nested.md"


def test_write_text_file_supports_all_allowlisted_extensions(
    policy: FileSystemPolicy,
) -> None:
    tool = WriteTextFileTool(policy)
    for ext in (".txt", ".md", ".py", ".json", ".csv", ".log"):
        result = execute(
            tool,
            "write_text_file",
            {"location": "documents", "path": f"sample{ext}", "content": "data"},
            policy=policy,
        )
        assert result.success is True
        assert (policy.roots["documents"] / f"sample{ext}").exists()


def test_write_text_file_rejects_unsupported_extension(
    policy: FileSystemPolicy,
) -> None:
    tool = WriteTextFileTool(policy)
    for path in ["evil.exe", "image.png", "archive.zip", "notes.pdf", "file"]:
        result = execute(
            tool,
            "write_text_file",
            {"location": "documents", "path": path, "content": "x"},
            policy=policy,
        )
        assert result.success is False
        assert result.error_code in {"invalid_arguments", "unsupported_extension"}


def test_write_text_file_rejects_parent_missing_and_target_is_directory(
    policy: FileSystemPolicy,
) -> None:
    tool = WriteTextFileTool(policy)
    missing = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "NoParent/file.txt", "content": "x"},
        policy=policy,
    )
    assert missing.success is False
    assert missing.error_code == "parent_not_found"

    (policy.roots["documents"] / "adir").mkdir()
    is_dir = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "adir", "content": "x"},
        policy=policy,
    )
    assert is_dir.success is False
    assert is_dir.error_code in {
        "invalid_arguments",
        "unsupported_extension",
        "target_is_directory",
    }

    (policy.roots["documents"] / "adir2").mkdir()
    nested_is_dir = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "adir2/nested.txt", "content": "x"},
        policy=policy,
    )
    assert nested_is_dir.success is True
    # now try to write where target is directory
    (policy.roots["documents"] / "adir2" / "subdir").mkdir()
    target_dir = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "adir2/subdir", "content": "x"},
        policy=policy,
    )
    assert target_dir.success is False


def test_write_text_file_rejects_traversal_and_network_paths(
    policy: FileSystemPolicy,
) -> None:
    tool = WriteTextFileTool(policy)
    for path in [
        "../outside.txt",
        "C:\\Windows\\evil.txt",
        "\\\\server\\share\\evil.txt",
        "//server/share/evil.txt",
    ]:
        result = execute(
            tool,
            "write_text_file",
            {"location": "documents", "path": path, "content": "x"},
            policy=policy,
        )
        assert result.success is False


def test_write_text_file_rejects_oversized_content(policy: FileSystemPolicy) -> None:
    tool = WriteTextFileTool(policy)
    large_chars = "a" * (MAX_WRITE_CONTENT_CHARACTERS + 1)
    result = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "big.txt", "content": large_chars},
        policy=policy,
    )
    assert result.success is False
    assert result.error_code == "invalid_arguments"

    small_policy = FileSystemPolicy(roots=policy.roots, max_text_file_bytes=5)
    small_tool = WriteTextFileTool(small_policy)
    # 6 bytes when encoded
    oversized_bytes = execute(
        small_tool,
        "write_text_file",
        {"location": "documents", "path": "small.txt", "content": "123456"},
        policy=small_policy,
    )
    assert oversized_bytes.success is False
    assert oversized_bytes.error_code == "content_too_large"


def test_write_text_file_rejects_invalid_filenames(policy: FileSystemPolicy) -> None:
    tool = WriteTextFileTool(policy)
    invalid = ["CON.txt", "file<.txt", "file|.txt", "NUL.txt", "a/COM1.txt"]
    for path in invalid:
        result = execute(
            tool,
            "write_text_file",
            {"location": "documents", "path": path, "content": "x"},
            policy=policy,
        )
        assert result.success is False


def test_write_text_file_rejects_extra_args_and_empty_path(
    policy: FileSystemPolicy,
) -> None:
    tool = WriteTextFileTool(policy)
    extra = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "valid.txt", "content": "x", "extra": True},
        policy=policy,
    )
    assert extra.success is False
    assert extra.error_code == "invalid_arguments"

    empty = execute(
        tool,
        "write_text_file",
        {"location": "documents", "path": "   ", "content": "x"},
        policy=policy,
    )
    assert empty.success is False


def test_write_tools_require_confirmation_and_are_registered(
    policy: FileSystemPolicy,
) -> None:
    assert (
        CreateDirectoryTool(policy).definition.permission.value
        == "confirmation_required"
    )
    assert (
        WriteTextFileTool(policy).definition.permission.value == "confirmation_required"
    )

    registry = ToolRegistry([CreateDirectoryTool(policy), WriteTextFileTool(policy)])
    assert registry.get("create_directory") is not None
    assert registry.get("write_text_file") is not None

    service = ToolExecutionService(registry)
    prep_dir = service.prepare(
        "create_directory", {"location": "documents", "path": "NeedConfirm"}
    )
    assert prep_dir.ready is True
    assert prep_dir.prepared.requires_confirmation is True
    # not confirmed should fail
    fail = service.execute_prepared(prep_dir.prepared, confirmed=False)
    assert fail.success is False
    assert fail.error_code == "confirmation_required"

    prep_write = service.prepare(
        "write_text_file", {"location": "documents", "path": "need.txt", "content": "x"}
    )
    assert prep_write.prepared.requires_confirmation is True


def test_write_flow_via_conversation_pending(policy: FileSystemPolicy) -> None:
    class FakeProvider:
        def __init__(self, call):
            self._call = call

        def complete(self, messages, tool_definitions=None):
            return ProviderResponse(message=None, tool_call=self._call)

    tool_registry = ToolRegistry(
        [CreateDirectoryTool(policy), WriteTextFileTool(policy)]
    )
    service = ToolExecutionService(tool_registry)
    call = ToolCallRequest(
        name="create_directory",
        arguments={"location": "documents", "path": "FromAI"},
        call_id="test123",
    )
    provider = FakeProvider(call)
    conv = ConversationService(provider, tool_service=service)
    result = conv.send("create folder FromAI in documents")
    assert result.pending_tool is not None
    assert result.pending_tool.request_id == "test123"
    assert "create_directory" in result.pending_tool.call.name

    approved = conv.approve_pending("test123")
    assert approved.tool_result.success is True
    assert (policy.roots["documents"] / "FromAI").is_dir()

    # duplicate approve should be stale
    stale = conv.approve_pending("test123")
    assert stale.tool_result.success is False
    assert stale.tool_result.error_code == "stale_confirmation"

    # write via conversation
    call2 = ToolCallRequest(
        name="write_text_file",
        arguments={"location": "documents", "path": "ai.txt", "content": "hello ai"},
        call_id="w123",
    )
    provider2 = FakeProvider(call2)
    conv2 = ConversationService(provider2, tool_service=service)
    r2 = conv2.send("write ai.txt")
    assert r2.pending_tool is not None
    c2 = conv2.approve_pending("w123")
    assert c2.tool_result.success is True
    assert (policy.roots["documents"] / "ai.txt").read_text(
        encoding="utf-8"
    ) == "hello ai"


def test_default_registry_contains_new_tools() -> None:
    from app.tools.defaults import create_default_tool_registry

    registry = create_default_tool_registry()
    assert registry.get("create_directory") is not None
    assert registry.get("write_text_file") is not None
    assert registry.get("list_directory") is not None
