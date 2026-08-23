## Task

Begin Phase 3: Tool System.

## Objectives

- Define a safe, explicit contract for approved AURA tools.
- Create a centralized tool registry that does not permit unrestricted shell or system commands.
- Add input validation before tool execution.
- Establish execution and result boundaries that can later support AI-requested actions.
- Preserve the current Gemini text conversation and PySide6 startup paths.

## Current Progress

Phase 2 is complete. AURA now loads Gemini configuration from the local `.env` or environment, registers the concrete Gemini provider through the existing provider registry, routes text through the provider-agnostic conversation service, and displays user/AURA messages in the PySide6 UI. Twenty-five automated tests pass, the package builds successfully, and the Windows desktop entry point launches with the configured local settings.

## Next Action

Design and implement the Phase 3 tool system in `app/tools/` and its core boundary. Keep tools explicit, validated, centrally registered, and confirmation-aware. Do not implement computer control, file management, shell execution, web automation, voice features, media control, memory, or advanced automation yet.

## Completion Criteria

The next task is complete when AURA has a testable tool definition and registry/execution foundation that can safely receive future AI tool requests without permitting unrestricted commands, while Phase 2 conversation behavior remains functional.
