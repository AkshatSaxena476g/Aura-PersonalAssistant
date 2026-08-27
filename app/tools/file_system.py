"""Bounded filesystem tools for AURA Phase 7A + 7B."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any, Iterator

from .contracts import (
    Tool,
    ToolDefinition,
    ToolPermission,
    ToolResult,
    ToolValidationError,
)

logger = logging.getLogger(__name__)

LOCATION_NAMES = (
    "desktop",
    "documents",
    "downloads",
    "pictures",
    "music",
    "videos",
)
_LOCATION_DIRECTORIES = {
    "desktop": "Desktop",
    "documents": "Documents",
    "downloads": "Downloads",
    "pictures": "Pictures",
    "music": "Music",
    "videos": "Videos",
}

MAX_SEARCH_QUERY_LENGTH = 200
MAX_SEARCH_RESULTS = 100
MAX_SEARCH_ENTRIES_SCANNED = 5_000
MAX_SEARCH_DEPTH = 4
MAX_TEXT_FILE_BYTES = 1_048_576
MAX_RETURNED_TEXT_CHARACTERS = 50_000
SUPPORTED_TEXT_EXTENSIONS = frozenset({".txt", ".md", ".py", ".json", ".csv", ".log"})

MAX_WRITE_CONTENT_CHARACTERS = 50_000
MAX_DIRECTORY_NAME_LENGTH = 255
MAX_FILE_NAME_LENGTH = 255
_RESERVED_WINDOWS_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(1, 10)]
    + [f"LPT{i}" for i in range(1, 10)]
)
_INVALID_FILENAME_CHARS = frozenset('<>:"/\\|?*')


class FileSystemPolicyError(ValueError):
    """Base exception for safe path-policy failures."""


class FileSystemLocationError(FileSystemPolicyError):
    """Raised when an approved location cannot be used."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class FileSystemPolicy:
    """Map approved location identifiers to resolved user directories."""

    roots: Mapping[str, Path] = field(default_factory=dict)
    max_search_results: int = MAX_SEARCH_RESULTS
    max_search_entries_scanned: int = MAX_SEARCH_ENTRIES_SCANNED
    max_search_depth: int = MAX_SEARCH_DEPTH
    max_text_file_bytes: int = MAX_TEXT_FILE_BYTES
    max_returned_text_characters: int = MAX_RETURNED_TEXT_CHARACTERS

    def __post_init__(self) -> None:
        normalized_roots = {
            str(location).strip().lower(): Path(root).expanduser().resolve(strict=False)
            for location, root in self.roots.items()
        }
        invalid_locations = set(normalized_roots) - set(LOCATION_NAMES)
        if invalid_locations:
            raise ValueError("Filesystem policy contains an unknown location")
        if any(
            value <= 0
            for value in (
                self.max_search_results,
                self.max_search_entries_scanned,
                self.max_search_depth,
                self.max_text_file_bytes,
                self.max_returned_text_characters,
            )
        ):
            raise ValueError("Filesystem policy limits must be positive")
        object.__setattr__(self, "roots", normalized_roots)

    @classmethod
    def from_user_home(cls, home: Path | None = None) -> "FileSystemPolicy":
        """Build approved roots from the current user's home directory."""

        base = (home or Path.home()).expanduser().resolve(strict=False)
        return cls(
            roots={
                location: base / directory
                for location, directory in _LOCATION_DIRECTORIES.items()
            }
        )

    def root_for(self, location: str) -> Path:
        """Return an available approved root or a safe structured-policy error."""

        normalized_location = location.strip().lower()
        if normalized_location not in LOCATION_NAMES:
            raise FileSystemLocationError(
                "The requested filesystem location is not approved.",
                error_code="unknown_location",
            )
        root = self.roots.get(normalized_location)
        if root is None or not root.exists():
            raise FileSystemLocationError(
                "The requested approved filesystem location is unavailable.",
                error_code="location_unavailable",
            )
        if not root.is_dir():
            raise FileSystemLocationError(
                "The requested approved filesystem location is not a directory.",
                error_code="location_unavailable",
            )
        return root

    def resolve_path(
        self,
        location: str,
        relative_path: str = "",
        *,
        allow_root: bool = True,
    ) -> Path:
        """Resolve a relative target and prove it remains inside its approved root."""

        root = self.root_for(location)
        if not isinstance(relative_path, str):
            raise FileSystemLocationError(
                "The filesystem path must be text.",
                error_code="invalid_path",
            )
        if "\x00" in relative_path:
            raise FileSystemLocationError(
                "The filesystem path is invalid.",
                error_code="path_not_allowed",
            )

        normalized_path = relative_path.strip()
        if not normalized_path and not allow_root:
            raise FileSystemLocationError(
                "A filesystem path is required.",
                error_code="path_required",
            )
        if self._is_absolute_or_network_path(normalized_path):
            raise FileSystemLocationError(
                "Only relative paths inside approved locations are allowed.",
                error_code="path_not_allowed",
            )
        if self._contains_parent_component(normalized_path):
            raise FileSystemLocationError(
                "Parent traversal is not allowed for filesystem paths.",
                error_code="path_not_allowed",
            )

        try:
            candidate = (root / normalized_path).resolve(strict=False)
        except (OSError, RuntimeError):
            raise FileSystemLocationError(
                "The filesystem path could not be resolved safely.",
                error_code="path_not_allowed",
            ) from None

        try:
            candidate.relative_to(root)
        except ValueError:
            raise FileSystemLocationError(
                "The requested path is outside AURA's approved locations.",
                error_code="path_not_allowed",
            ) from None
        return candidate

    @staticmethod
    def _is_absolute_or_network_path(value: str) -> bool:
        windows_path = PureWindowsPath(value)
        return (
            Path(value).is_absolute()
            or windows_path.is_absolute()
            or bool(windows_path.drive)
            or value.startswith(("\\\\", "//"))
        )

    @staticmethod
    def _contains_parent_component(value: str) -> bool:
        return ".." in Path(value).parts or ".." in PureWindowsPath(value).parts


def _validate_filename_part(name: str) -> str | None:
    if not name or name in (".", ".."):
        return "Filename is invalid."
    if len(name) > MAX_FILE_NAME_LENGTH:
        return "Filename exceeds safe length."
    if any(char in name for char in _INVALID_FILENAME_CHARS):
        return "Filename contains invalid characters."
    if any(ord(c) < 32 for c in name):
        return "Filename contains invalid characters."
    if name[-1] in (" ", "."):
        return "Filename must not end with space or period."
    stem = name.split(".")[0].upper()
    if stem in _RESERVED_WINDOWS_NAMES:
        return "Filename is reserved on Windows."
    return None


def _validate_write_path(path: str) -> str | None:
    for part in PureWindowsPath(path).parts:
        if part in ("/", "\\", ".", ".."):
            continue
        error = _validate_filename_part(part)
        if error is not None:
            return error
    for part in Path(path).parts:
        if part in ("/", "\\", ".", ".."):
            continue
        error = _validate_filename_part(part)
        if error is not None:
            return error
    return None


class _FileSystemTool(Tool):
    """Shared validation, policy access, and safe failure mapping."""

    def __init__(self, policy: FileSystemPolicy | None = None) -> None:
        self._policy = policy or FileSystemPolicy.from_user_home()

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.SAFE

    @staticmethod
    def _location_schema() -> dict[str, Any]:
        return {
            "type": "string",
            "enum": list(LOCATION_NAMES),
            "description": "Approved user location identifier.",
        }

    @staticmethod
    def _path_schema(*, required: bool) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": "string",
            "description": "Relative path inside the selected approved location.",
        }
        if required:
            schema["minLength"] = 1
        return schema

    @staticmethod
    def _normalize_location(arguments: dict[str, Any]) -> dict[str, Any]:
        location = arguments["location"]
        normalized = location.strip().lower()
        if normalized not in LOCATION_NAMES:
            raise ToolValidationError(
                "Argument 'location' must be one of: " + ", ".join(LOCATION_NAMES)
            )
        arguments["location"] = normalized
        return arguments

    @staticmethod
    def _normalize_required_path(arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments["path"]
        if not path.strip():
            raise ToolValidationError("Argument 'path' must not be empty")
        arguments["path"] = path.strip()
        return arguments

    @staticmethod
    def _normalize_optional_path(arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path", "")
        arguments["path"] = path.strip()
        return arguments

    def _resolve(
        self,
        location: str,
        path: str = "",
        *,
        allow_root: bool = True,
    ) -> tuple[Path | None, ToolResult | None]:
        try:
            return (
                self._policy.resolve_path(location, path, allow_root=allow_root),
                None,
            )
        except FileSystemLocationError as error:
            return None, ToolResult.failure(str(error), error_code=error.error_code)
        except Exception:
            logger.error("Unexpected filesystem path-policy failure")
            return None, ToolResult.failure(
                "The filesystem path could not be validated safely.",
                error_code="path_validation_error",
            )

    @staticmethod
    def _safe_failure(message: str, error_code: str) -> ToolResult:
        return ToolResult.failure(message, error_code=error_code)

    def _safe_entry(
        self,
        location: str,
        root: Path,
        entry: Path,
    ) -> dict[str, Any] | None:
        try:
            relative_path = entry.resolve(strict=False).relative_to(root).as_posix()
            resolved = self._policy.resolve_path(
                location, relative_path, allow_root=False
            )
            if resolved.is_dir():
                entry_type = "directory"
            elif resolved.is_file():
                entry_type = "file"
            else:
                return None
            return {
                "name": resolved.name,
                "relative_path": relative_path,
                "type": entry_type,
            }
        except (FileSystemPolicyError, OSError, RuntimeError):
            return None

    def _iter_safe_entries(
        self,
        location: str,
        root: Path,
    ) -> Iterator[tuple[Path, str, str]]:
        """Walk a bounded depth without following directory symlinks."""

        stack: list[tuple[Path, int]] = [(root, 0)]
        scanned = 0
        while stack and scanned < self._policy.max_search_entries_scanned:
            current, depth = stack.pop()
            try:
                children = sorted(
                    current.iterdir(),
                    key=lambda path: path.name.casefold(),
                    reverse=True,
                )
            except OSError:
                continue

            for child in children:
                if scanned >= self._policy.max_search_entries_scanned:
                    return
                scanned += 1
                try:
                    relative_path = (
                        child.resolve(strict=False).relative_to(root).as_posix()
                    )
                    resolved = self._policy.resolve_path(
                        location,
                        relative_path,
                        allow_root=False,
                    )
                except (FileSystemPolicyError, OSError, RuntimeError):
                    continue

                if resolved.is_dir():
                    yield resolved, "directory", relative_path
                    if (
                        not child.is_symlink()
                        and depth + 1 < self._policy.max_search_depth
                    ):
                        stack.append((resolved, depth + 1))
                elif resolved.is_file():
                    yield resolved, "file", relative_path


class ListDirectoryTool(_FileSystemTool):
    """List immediate safe entries in an approved directory."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_directory",
            description=(
                "List the immediate files and directories inside one approved user location. "
                "Use only an approved location identifier and an optional relative path."
            ),
            permission=ToolPermission.SAFE,
            input_schema={
                "type": "object",
                "properties": {
                    "location": self._location_schema(),
                    "path": self._path_schema(required=False),
                },
                "required": ["location"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        return self._normalize_optional_path(self._normalize_location(validated))

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        target, failure = self._resolve(
            arguments["location"],
            arguments.get("path", ""),
        )
        if failure is not None:
            return failure
        assert target is not None
        if not target.exists():
            return self._safe_failure(
                "The requested directory does not exist.",
                "target_not_found",
            )
        if not target.is_dir():
            return self._safe_failure(
                "The requested target is not a directory.",
                "not_directory",
            )

        root = self._policy.root_for(arguments["location"])
        try:
            entries = []
            for entry in sorted(
                target.iterdir(), key=lambda path: path.name.casefold()
            ):
                safe_entry = self._safe_entry(arguments["location"], root, entry)
                if safe_entry is not None:
                    entries.append(safe_entry)
        except OSError:
            return self._safe_failure(
                "The directory could not be read.",
                "filesystem_error",
            )

        relative_path = target.relative_to(root).as_posix() or "."
        return ToolResult.ok(
            f"Found {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.",
            data={
                "location": arguments["location"],
                "relative_path": relative_path,
                "entries": entries,
            },
        )


class SearchFilesTool(_FileSystemTool):
    """Search bounded depth inside one approved location by name."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_files",
            description=(
                "Search for matching file and directory names inside one approved user location. "
                "Search is bounded by depth, scanned entries, and result count."
            ),
            permission=ToolPermission.SAFE,
            input_schema={
                "type": "object",
                "properties": {
                    "location": self._location_schema(),
                    "query": {
                        "type": "string",
                        "description": "Non-empty name fragment to search for.",
                        "minLength": 1,
                    },
                },
                "required": ["location", "query"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        validated = self._normalize_location(validated)
        query = validated["query"].strip()
        if not query:
            raise ToolValidationError("Argument 'query' must not be empty")
        if len(query) > MAX_SEARCH_QUERY_LENGTH:
            raise ToolValidationError(
                f"Argument 'query' must be at most {MAX_SEARCH_QUERY_LENGTH} characters"
            )
        validated["query"] = query
        return validated

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        root, failure = self._resolve(arguments["location"])
        if failure is not None:
            return failure
        assert root is not None
        query = arguments["query"].casefold()
        results: list[dict[str, Any]] = []
        scanned = 0
        truncated = False
        try:
            for path, entry_type, relative_path in self._iter_safe_entries(
                arguments["location"], root
            ):
                scanned += 1
                if query in path.name.casefold():
                    results.append(
                        {
                            "name": path.name,
                            "relative_path": relative_path,
                            "location": arguments["location"],
                            "type": entry_type,
                        }
                    )
                    if len(results) >= self._policy.max_search_results:
                        truncated = True
                        break
        except OSError:
            return self._safe_failure(
                "The approved location could not be searched.",
                "filesystem_error",
            )

        results.sort(key=lambda item: item["relative_path"].casefold())
        message = (
            f"Found {len(results)} matching item{'s' if len(results) != 1 else ''}."
        )
        if truncated:
            message += " The result list was bounded."
        return ToolResult.ok(
            message,
            data={
                "location": arguments["location"],
                "query": arguments["query"],
                "results": results,
                "scanned_entries": scanned,
                "truncated": truncated,
            },
        )


class GetFileInfoTool(_FileSystemTool):
    """Return bounded metadata for an approved file or directory."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_file_info",
            description=(
                "Read safe metadata for one existing file or directory inside an approved user location."
            ),
            permission=ToolPermission.SAFE,
            input_schema={
                "type": "object",
                "properties": {
                    "location": self._location_schema(),
                    "path": self._path_schema(required=True),
                },
                "required": ["location", "path"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        return self._normalize_required_path(self._normalize_location(validated))

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        target, failure = self._resolve(
            arguments["location"],
            arguments["path"],
            allow_root=False,
        )
        if failure is not None:
            return failure
        assert target is not None
        if not target.exists():
            return self._safe_failure(
                "The requested filesystem target does not exist.",
                "target_not_found",
            )

        root = self._policy.root_for(arguments["location"])
        relative_path = target.relative_to(root).as_posix()
        try:
            if target.is_file():
                stat = target.stat()
                data = {
                    "name": target.name,
                    "relative_path": relative_path,
                    "location": arguments["location"],
                    "type": "file",
                    "extension": target.suffix.lower(),
                    "size_bytes": stat.st_size,
                }
                return ToolResult.ok("File metadata read successfully.", data=data)
            if target.is_dir():
                return ToolResult.ok(
                    "Directory metadata read successfully.",
                    data={
                        "name": target.name,
                        "relative_path": relative_path,
                        "location": arguments["location"],
                        "type": "directory",
                    },
                )
        except OSError:
            return self._safe_failure(
                "The filesystem metadata could not be read.",
                "filesystem_error",
            )
        return self._safe_failure(
            "The requested target is not a regular file or directory.",
            "unsupported_target",
        )


class ReadTextFileTool(_FileSystemTool):
    """Read a bounded UTF-8 text file from an approved location."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_text_file",
            description=(
                "Read a bounded UTF-8 text file from an approved user location. "
                "Supported extensions are .txt, .md, .py, .json, .csv, and .log."
            ),
            permission=ToolPermission.SAFE,
            input_schema={
                "type": "object",
                "properties": {
                    "location": self._location_schema(),
                    "path": self._path_schema(required=True),
                },
                "required": ["location", "path"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        return self._normalize_required_path(self._normalize_location(validated))

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        target, failure = self._resolve(
            arguments["location"],
            arguments["path"],
            allow_root=False,
        )
        if failure is not None:
            return failure
        assert target is not None
        if not target.exists():
            return self._safe_failure(
                "The requested text file does not exist.",
                "target_not_found",
            )
        if not target.is_file():
            return self._safe_failure(
                "The requested target is not a regular file.",
                "not_file",
            )
        if target.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
            return self._safe_failure(
                "This file extension is not supported for safe text reading.",
                "unsupported_extension",
            )

        try:
            if target.stat().st_size > self._policy.max_text_file_bytes:
                return self._safe_failure(
                    "The text file exceeds AURA's safe size limit.",
                    "file_too_large",
                )
            with target.open("r", encoding="utf-8", errors="strict") as handle:
                content = handle.read(self._policy.max_returned_text_characters + 1)
        except UnicodeDecodeError:
            return self._safe_failure(
                "The text file is not valid UTF-8.",
                "encoding_error",
            )
        except OSError:
            return self._safe_failure(
                "The text file could not be read.",
                "filesystem_error",
            )

        truncated = len(content) > self._policy.max_returned_text_characters
        if truncated:
            content = content[: self._policy.max_returned_text_characters]
        message = "Text file read successfully."
        if truncated:
            message = "Text file read with bounded content truncation."
        root = self._policy.root_for(arguments["location"])
        relative_path = target.relative_to(root).as_posix()
        return ToolResult.ok(
            message,
            data={
                "location": arguments["location"],
                "relative_path": relative_path,
                "name": target.name,
                "content": content,
                "truncated": truncated,
            },
        )


class CreateDirectoryTool(_FileSystemTool):
    """Create a single bounded directory inside an approved location."""

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION_REQUIRED

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_directory",
            description=(
                "Create a single new directory inside an approved user location. "
                "The parent directory must already exist; intermediate directories are not created automatically. "
                "Use only an approved location identifier and a relative path."
            ),
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema={
                "type": "object",
                "properties": {
                    "location": self._location_schema(),
                    "path": self._path_schema(required=True),
                },
                "required": ["location", "path"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        validated = self._normalize_required_path(self._normalize_location(validated))
        error = _validate_write_path(validated["path"])
        if error is not None:
            raise ToolValidationError(error)
        return validated

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        target, failure = self._resolve(
            arguments["location"],
            arguments["path"],
            allow_root=False,
        )
        if failure is not None:
            return failure
        assert target is not None
        if target.exists():
            return self._safe_failure(
                "The requested directory already exists.",
                "target_exists",
            )
        error = _validate_write_path(arguments["path"])
        if error is not None:
            return self._safe_failure(error, "invalid_path")

        root = self._policy.root_for(arguments["location"])
        parent = target.parent
        try:
            parent.relative_to(root)
        except ValueError:
            return self._safe_failure(
                "The requested path is outside AURA's approved locations.",
                "path_not_allowed",
            )
        if not parent.exists():
            return self._safe_failure(
                "The parent directory does not exist.",
                "parent_not_found",
            )
        if not parent.is_dir():
            return self._safe_failure(
                "The parent target is not a directory.",
                "parent_not_found",
            )
        if parent.is_symlink():
            try:
                resolved_parent = parent.resolve(strict=True)
                resolved_parent.relative_to(root)
            except (OSError, ValueError, RuntimeError):
                return self._safe_failure(
                    "The requested path is outside AURA's approved locations.",
                    "path_not_allowed",
                )

        try:
            target.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            return self._safe_failure(
                "The requested directory already exists.",
                "target_exists",
            )
        except OSError:
            return self._safe_failure(
                "The directory could not be created.",
                "filesystem_error",
            )

        relative_path = target.relative_to(root).as_posix()
        return ToolResult.ok(
            "Directory created successfully.",
            data={
                "location": arguments["location"],
                "relative_path": relative_path,
                "name": target.name,
            },
        )


class WriteTextFileTool(_FileSystemTool):
    """Create or overwrite a bounded UTF-8 text file inside an approved location."""

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.CONFIRMATION_REQUIRED

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_text_file",
            description=(
                "Create or overwrite a bounded UTF-8 text file inside an approved user location. "
                "Supported extensions are .txt, .md, .py, .json, .csv, and .log. "
                "Content is limited to 50,000 characters and 1 MiB when encoded as UTF-8. "
                "The parent directory must already exist."
            ),
            permission=ToolPermission.CONFIRMATION_REQUIRED,
            input_schema={
                "type": "object",
                "properties": {
                    "location": self._location_schema(),
                    "path": self._path_schema(required=True),
                    "content": {
                        "type": "string",
                        "description": "UTF-8 text content to write; at most 50,000 characters.",
                    },
                },
                "required": ["location", "path", "content"],
                "additionalProperties": False,
            },
        )

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        validated = super().validate(arguments)
        validated = self._normalize_required_path(self._normalize_location(validated))
        content = validated.get("content")
        if not isinstance(content, str):
            raise ToolValidationError("Argument 'content' must be a string")
        if len(content) > MAX_WRITE_CONTENT_CHARACTERS:
            raise ToolValidationError(
                f"Argument 'content' must be at most {MAX_WRITE_CONTENT_CHARACTERS} characters"
            )
        error = _validate_write_path(validated["path"])
        if error is not None:
            raise ToolValidationError(error)
        path_obj = Path(validated["path"])
        if path_obj.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
            raise ToolValidationError(
                "File extension is not supported for safe text writing. Use .txt, .md, .py, .json, .csv, or .log"
            )
        return validated

    def execute(self, arguments: Mapping[str, Any]) -> ToolResult:
        target, failure = self._resolve(
            arguments["location"],
            arguments["path"],
            allow_root=False,
        )
        if failure is not None:
            return failure
        assert target is not None

        error = _validate_write_path(arguments["path"])
        if error is not None:
            return self._safe_failure(error, "invalid_path")

        if target.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
            return self._safe_failure(
                "This file extension is not supported for safe text writing.",
                "unsupported_extension",
            )

        content: str = arguments["content"]
        if len(content) > MAX_WRITE_CONTENT_CHARACTERS:
            return self._safe_failure(
                "The text content exceeds AURA's safe character limit.",
                "content_too_large",
            )
        encoded = content.encode("utf-8")
        if len(encoded) > self._policy.max_text_file_bytes:
            return self._safe_failure(
                "The text content exceeds AURA's safe size limit.",
                "content_too_large",
            )

        root = self._policy.root_for(arguments["location"])
        parent = target.parent
        try:
            parent.relative_to(root)
        except ValueError:
            return self._safe_failure(
                "The requested path is outside AURA's approved locations.",
                "path_not_allowed",
            )
        if not parent.exists():
            return self._safe_failure(
                "The parent directory does not exist.",
                "parent_not_found",
            )
        if not parent.is_dir():
            return self._safe_failure(
                "The parent target is not a directory.",
                "parent_not_found",
            )
        if parent.is_symlink():
            try:
                resolved_parent = parent.resolve(strict=True)
                resolved_parent.relative_to(root)
            except (OSError, ValueError, RuntimeError):
                return self._safe_failure(
                    "The requested path is outside AURA's approved locations.",
                    "path_not_allowed",
                )

        if target.exists() and target.is_dir():
            return self._safe_failure(
                "The requested target is a directory.",
                "target_is_directory",
            )
        if target.is_symlink():
            try:
                resolved_target = target.resolve(strict=True)
                resolved_target.relative_to(root)
            except (OSError, ValueError, RuntimeError):
                return self._safe_failure(
                    "The requested path is outside AURA's approved locations.",
                    "path_not_allowed",
                )

        try:
            with target.open("w", encoding="utf-8", newline="") as handle:
                handle.write(content)
        except OSError:
            return self._safe_failure(
                "The text file could not be written.",
                "filesystem_error",
            )

        relative_path = target.relative_to(root).as_posix()
        try:
            size_bytes = target.stat().st_size
        except OSError:
            size_bytes = len(encoded)

        return ToolResult.ok(
            "Text file written successfully.",
            data={
                "location": arguments["location"],
                "relative_path": relative_path,
                "name": target.name,
                "size_bytes": size_bytes,
            },
        )


__all__ = [
    "FileSystemPolicy",
    "GetFileInfoTool",
    "ListDirectoryTool",
    "LOCATION_NAMES",
    "MAX_RETURNED_TEXT_CHARACTERS",
    "MAX_SEARCH_DEPTH",
    "MAX_SEARCH_ENTRIES_SCANNED",
    "MAX_SEARCH_QUERY_LENGTH",
    "MAX_SEARCH_RESULTS",
    "MAX_TEXT_FILE_BYTES",
    "MAX_WRITE_CONTENT_CHARACTERS",
    "ReadTextFileTool",
    "SearchFilesTool",
    "SUPPORTED_TEXT_EXTENSIONS",
    "CreateDirectoryTool",
    "WriteTextFileTool",
]
