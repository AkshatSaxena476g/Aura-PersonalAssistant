## Task

Begin Phase 5: File and Folder Management.

## Objectives

- Extend the existing provider-independent tool system with explicitly scoped file and folder operations.
- Validate all paths and arguments before execution.
- Require confirmation for destructive or irreversible changes.
- Preserve centralized registration, permission policy, structured results, and safe error handling.
- Keep Gemini text conversation and the Phase 4 allow-listed application launcher functional.

## Current Progress

Phase 4 is complete. AURA now has a Windows-specific `launch_application` tool that supports only the internal identifiers `notepad`, `calculator`, `settings`, and `file_explorer`. The fixed targets are resolved internally, application launching is confirmation-required, external launches are mocked in tests, and Gemini is not connected directly to tool execution.

## Next Action

Design and implement the smallest safe Phase 5 file/folder capability on top of `ToolExecutionService`. Use explicit path validation, prevent unintended traversal or broad modification, and keep destructive operations confirmation-aware. Do not add unrestricted file or folder mutation.

## Completion Criteria

The next task is complete when the selected file/folder operations are implemented as explicit validated tools with correct permission behavior, safe failures, focused Windows tests, and no regressions in the existing conversation, tool, and application-launch functionality.
