## Task

Begin Phase 6: Web, YouTube, and Media.

## Objectives

- Add only explicitly scoped web and media capabilities through the existing provider-independent tool system.
- Derive any provider-facing declarations from the active `ToolRegistry` rather than maintaining provider-specific tool lists.
- Preserve validation, permission, confirmation, structured results, and safe failure handling.
- Keep Gemini tool calling, normal text conversation, and the Phase 4 allow-listed application launcher functional.

## Current Progress

Phase 5 is complete. AURA now translates Gemini function calls into provider-neutral `ToolCallRequest` values, derives Gemini declarations from the active registry, routes requests through `ToolExecutionService`, and manages confirmation-required actions through `Application` and the simple PySide6 Allow/Cancel panel. Sixty-one automated tests pass, the package builds successfully, and the Windows desktop entry point launches successfully.

## Next Action

Design and implement the smallest safe Phase 6 web/media capability on top of the existing tool and provider-neutral boundaries. Keep browser or media operations explicitly scoped and confirmation-aware where appropriate. Do not add unrestricted browser automation, arbitrary URLs, voice features, memory, or autonomous actions.

## Completion Criteria

The next task is complete when the selected web/media capability is represented as an explicit registered tool with validated inputs, correct permission behavior, safe structured results, focused mocked tests, and no regression in normal conversation, Gemini tool calling, confirmation flow, or Windows application launching.
