## Task

Begin Phase 2: AI Core.

## Objectives

- Add conversation handling behind the existing provider-neutral AI abstraction.
- Integrate a concrete AI provider without coupling the assistant core to vendor-specific code.
- Define structured assistant responses suitable for future tool requests and UI presentation.
- Preserve the settings-aware desktop lifecycle and minimal UI shell established in Phase 1.

## Current Progress

Phase 1 is complete. The repository now includes a PySide6 dependency, a minimal branded `MainWindow`, a `DesktopApplication` Qt wrapper in `app/ui/`, and an optional UI runner integrated into the existing provider-agnostic `Application` lifecycle. Ten automated tests pass, and the Windows entry point launches the AURA desktop window successfully.

## Next Action

Design and implement the Phase 2 AI core using the existing contracts in `app/ai/` and `app/core/`. Keep concrete provider adapters isolated and do not add tool execution, voice features, file management, system control, wake-word behavior, media features, memory, or advanced automation yet.

## Completion Criteria

The next task is complete when AURA can process a conversation through a selected provider using structured, testable responses, while the core remains provider-agnostic and the Phase 1 desktop startup path remains functional.
