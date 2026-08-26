from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core import ToolExecutionService
from app.tools import (
    FileSystemPolicy,
    GetFileInfoTool,
    ListDirectoryTool,
    ReadTextFileTool,
    SearchFilesTool,
    ToolRegistry,
)
from app.tools.file_system import (
    MAX_RETURNED_TEXT_CHARACTERS,
    FileSystemLocationError,
)


@pytest.fixture
def policy(tmp_path: Path) -> FileSystemPolicy:
    roots = {
        name: tmp_path / name
        for name in ("desktop", "documents", "downloads", "pictures", "music", "videos")
    }
    for root in roots.values():
        root.mkdir()
    return FileSystemPolicy(roots=roots)


def execute(tool: object, name: str, arguments: dict[str, Any], *, policy: FileSystemPolicy):
    return ToolExecutionService(ToolRegistry([tool])).execute(
        name,
        arguments,
        confirmed=True,
    )


def test_policy_resolves_only_relative_paths_inside_selected_root(policy: FileSystemPolicy) -> None:
    documents = policy.roots["documents"]
    nested = documents / "Projects"
    nested.mkdir()

    assert policy.resolve_path("documents", "Projects") == nested.resolve()
    assert policy.resolve_path("DOCUMENTS", " Projects ") == nested.resolve()


@pytest.mark.parametrize(
    "value",
    [
        "../outside.txt",
        "nested/../../outside.txt",
        "..\\outside.txt",
        "C:\\Windows\\System32",
        "\\\\server\\share\\secret.txt",
        "//server/share/secret.txt",
        "/etc/passwd",
    ],
)
def test_policy_rejects_traversal_absolute_and_network_paths(
    policy: FileSystemPolicy,
    value: str,
) -> None:
    with pytest.raises(FileSystemLocationError) as error:
        policy.resolve_path("documents", value)

    assert error.value.error_code == "path_not_allowed"


def test_policy_rejects_sibling_prefix_escape(policy: FileSystemPolicy, tmp_path: Path) -> None:
    sibling = tmp_path / "documents_backup"
    sibling.mkdir()
    with pytest.raises(FileSystemLocationError) as error:
        policy.resolve_path("documents", "../documents_backup")
    assert error.value.error_code == "path_not_allowed"


def test_policy_rejects_symlink_escape_when_supported(
    policy: FileSystemPolicy,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = policy.roots["documents"] / "outside-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this Windows test environment")

    with pytest.raises(FileSystemLocationError) as error:
        policy.resolve_path("documents", "outside-link/secret.txt")
    assert error.value.error_code == "path_not_allowed"


def test_policy_reports_unknown_and_unavailable_locations(tmp_path: Path) -> None:
    policy = FileSystemPolicy(
        roots={"documents": tmp_path / "documents"},
    )
    policy.roots["documents"].mkdir()

    with pytest.raises(FileSystemLocationError) as unknown:
        policy.root_for("other")
    assert unknown.value.error_code == "unknown_location"

    missing_policy = FileSystemPolicy(roots={"documents": tmp_path / "missing"})
    with pytest.raises(FileSystemLocationError) as unavailable:
        missing_policy.root_for("documents")
    assert unavailable.value.error_code == "location_unavailable"


def test_list_directory_returns_deterministic_safe_entries(policy: FileSystemPolicy) -> None:
    root = policy.roots["documents"]
    (root / "zeta.txt").write_text("z", encoding="utf-8")
    (root / "Alpha").mkdir()
    (root / "Alpha" / "nested.md").write_text("nested", encoding="utf-8")

    result = execute(ListDirectoryTool(policy), "list_directory", {"location": "documents"}, policy=policy)

    assert result.success is True
    assert result.data is not None
    assert result.data["relative_path"] == "."
    assert result.data["entries"] == [
        {"name": "Alpha", "relative_path": "Alpha", "type": "directory"},
        {"name": "zeta.txt", "relative_path": "zeta.txt", "type": "file"},
    ]
    assert all("/" not in entry["relative_path"] or not entry["relative_path"].startswith("/") for entry in result.data["entries"])


def test_list_directory_supports_nested_directory_and_rejects_file_target(
    policy: FileSystemPolicy,
) -> None:
    root = policy.roots["documents"]
    nested = root / "Projects"
    nested.mkdir()
    (nested / "notes.txt").write_text("notes", encoding="utf-8")

    nested_result = execute(
        ListDirectoryTool(policy),
        "list_directory",
        {"location": "documents", "path": "Projects"},
        policy=policy,
    )
    assert nested_result.success is True
    assert nested_result.data["entries"][0]["relative_path"] == "Projects/notes.txt"

    file_result = execute(
        ListDirectoryTool(policy),
        "list_directory",
        {"location": "documents", "path": "Projects/notes.txt"},
        policy=policy,
    )
    assert file_result.success is False
    assert file_result.error_code == "not_directory"


def test_list_directory_reports_missing_and_extra_arguments_safely(
    policy: FileSystemPolicy,
) -> None:
    missing = execute(
        ListDirectoryTool(policy),
        "list_directory",
        {"location": "documents", "path": "Missing"},
        policy=policy,
    )
    assert missing.success is False
    assert missing.error_code == "target_not_found"

    extra = execute(
        ListDirectoryTool(policy),
        "list_directory",
        {"location": "documents", "unexpected": True},
        policy=policy,
    )
    assert extra.success is False
    assert extra.error_code == "invalid_arguments"


def test_search_files_matches_files_and_directories_with_bounds(policy: FileSystemPolicy) -> None:
    root = policy.roots["documents"]
    (root / "resume.pdf").write_text("pdf placeholder", encoding="utf-8")
    (root / "Resume Archive").mkdir()
    (root / "Resume Archive" / "resume-notes.txt").write_text("notes", encoding="utf-8")
    (root / "other.txt").write_text("other", encoding="utf-8")

    result = execute(
        SearchFilesTool(policy),
        "search_files",
        {"location": "documents", "query": "  RESUME  "},
        policy=policy,
    )

    assert result.success is True
    assert result.data["query"] == "RESUME"
    assert [item["relative_path"] for item in result.data["results"]] == [
        "Resume Archive",
        "Resume Archive/resume-notes.txt",
        "resume.pdf",
    ]
    assert {item["type"] for item in result.data["results"]} == {"file", "directory"}
    assert all(
        not Path(item["relative_path"]).is_absolute()
        and not item["relative_path"].startswith(("/", "\\\\"))
        for item in result.data["results"]
    )

    no_results = execute(
        SearchFilesTool(policy),
        "search_files",
        {"location": "documents", "query": "does-not-exist"},
        policy=policy,
    )
    assert no_results.success is True
    assert no_results.data["results"] == []

    bounded = FileSystemPolicy(roots=policy.roots, max_search_results=2)
    bounded_result = execute(
        SearchFilesTool(bounded),
        "search_files",
        {"location": "documents", "query": "resume"},
        policy=bounded,
    )
    assert bounded_result.success is True
    assert len(bounded_result.data["results"]) == 2
    assert bounded_result.data["truncated"] is True


def test_search_files_rejects_empty_invalid_and_extra_query_inputs(
    policy: FileSystemPolicy,
) -> None:
    tool = SearchFilesTool(policy)
    for arguments in (
        {"location": "documents", "query": ""},
        {"location": "documents", "query": "   "},
        {"location": "documents", "query": 42},
        {"location": "documents", "query": "x" * 201},
        {"location": "documents", "query": "x", "path": "secret"},
        {"location": "unknown", "query": "x"},
    ):
        result = execute(tool, "search_files", arguments, policy=policy)
        assert result.success is False
        assert result.error_code == "invalid_arguments"


def test_get_file_info_returns_minimal_file_and_directory_metadata(
    policy: FileSystemPolicy,
) -> None:
    root = policy.roots["downloads"]
    file_path = root / "resume.pdf"
    file_path.write_bytes(b"12345")
    directory = root / "Archive"
    directory.mkdir()

    file_result = execute(
        GetFileInfoTool(policy),
        "get_file_info",
        {"location": "downloads", "path": "resume.pdf"},
        policy=policy,
    )
    assert file_result.success is True
    assert file_result.data == {
        "name": "resume.pdf",
        "relative_path": "resume.pdf",
        "location": "downloads",
        "type": "file",
        "extension": ".pdf",
        "size_bytes": 5,
    }

    directory_result = execute(
        GetFileInfoTool(policy),
        "get_file_info",
        {"location": "downloads", "path": "Archive"},
        policy=policy,
    )
    assert directory_result.success is True
    assert directory_result.data == {
        "name": "Archive",
        "relative_path": "Archive",
        "location": "downloads",
        "type": "directory",
    }


def test_get_file_info_rejects_missing_invalid_and_extra_paths(policy: FileSystemPolicy) -> None:
    tool = GetFileInfoTool(policy)
    missing = execute(
        tool,
        "get_file_info",
        {"location": "downloads", "path": "missing.txt"},
        policy=policy,
    )
    assert missing.success is False
    assert missing.error_code == "target_not_found"

    for arguments in (
        {"location": "downloads", "path": ""},
        {"location": "downloads", "path": "../secret.txt"},
        {"location": "downloads", "path": 5},
        {"location": "downloads", "path": "x", "extra": True},
    ):
        result = execute(tool, "get_file_info", arguments, policy=policy)
        assert result.success is False
        assert result.error_code in {"invalid_arguments", "path_not_allowed"}


def test_read_text_file_supports_allowlisted_extensions_and_bounded_content(
    policy: FileSystemPolicy,
) -> None:
    root = policy.roots["documents"]
    for extension in (".txt", ".md", ".py", ".json", ".csv", ".log"):
        (root / f"sample{extension}").write_text("hello", encoding="utf-8")

    result = execute(
        ReadTextFileTool(policy),
        "read_text_file",
        {"location": "documents", "path": "sample.md"},
        policy=policy,
    )
    assert result.success is True
    assert result.data["content"] == "hello"
    assert result.data["truncated"] is False

    limited = FileSystemPolicy(roots=policy.roots, max_returned_text_characters=4)
    truncated = execute(
        ReadTextFileTool(limited),
        "read_text_file",
        {"location": "documents", "path": "sample.txt"},
        policy=limited,
    )
    assert truncated.success is True
    assert truncated.data["content"] == "hell"
    assert truncated.data["truncated"] is True
    assert len(truncated.data["content"]) <= MAX_RETURNED_TEXT_CHARACTERS


def test_read_text_file_rejects_unsupported_binary_oversized_and_invalid_encoding(
    policy: FileSystemPolicy,
) -> None:
    root = policy.roots["documents"]
    (root / "program.exe").write_bytes(b"not text")
    (root / "binary.txt").write_bytes(b"\xff\xfe")
    (root / "large.txt").write_text("123456", encoding="utf-8")
    (root / "folder.txt").mkdir()

    unsupported = execute(
        ReadTextFileTool(policy),
        "read_text_file",
        {"location": "documents", "path": "program.exe"},
        policy=policy,
    )
    assert unsupported.success is False
    assert unsupported.error_code == "unsupported_extension"

    binary = execute(
        ReadTextFileTool(policy),
        "read_text_file",
        {"location": "documents", "path": "binary.txt"},
        policy=policy,
    )
    assert binary.success is False
    assert binary.error_code == "encoding_error"

    small_policy = FileSystemPolicy(roots=policy.roots, max_text_file_bytes=5)
    oversized = execute(
        ReadTextFileTool(small_policy),
        "read_text_file",
        {"location": "documents", "path": "large.txt"},
        policy=small_policy,
    )
    assert oversized.success is False
    assert oversized.error_code == "file_too_large"

    directory = execute(
        ReadTextFileTool(policy),
        "read_text_file",
        {"location": "documents", "path": "folder.txt"},
        policy=policy,
    )
    assert directory.success is False
    assert directory.error_code == "not_file"


def test_read_text_file_rejects_missing_traversal_and_extra_arguments(
    policy: FileSystemPolicy,
) -> None:
    tool = ReadTextFileTool(policy)
    for arguments in (
        {"location": "documents", "path": "missing.txt"},
        {"location": "documents", "path": "../secret.txt"},
        {"location": "documents", "path": "notes.txt", "extra": True},
    ):
        result = execute(tool, "read_text_file", arguments, policy=policy)
        assert result.success is False
        assert result.error_code in {
            "target_not_found",
            "invalid_arguments",
            "path_not_allowed",
        }
        assert str(policy.roots["documents"]) not in result.message


def test_filesystem_tools_are_safe_and_require_no_confirmation(policy: FileSystemPolicy) -> None:
    for tool in (
        ListDirectoryTool(policy),
        SearchFilesTool(policy),
        GetFileInfoTool(policy),
        ReadTextFileTool(policy),
    ):
        assert tool.definition.permission.value == "safe"
