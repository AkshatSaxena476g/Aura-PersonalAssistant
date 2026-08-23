## Task

Begin Phase 1: Basic Desktop Application.

## Objectives

- Add the initial PySide6 desktop application lifecycle.
- Create a minimal UI shell suitable for text interaction.
- Keep UI concerns separate from the provider-agnostic assistant core.
- Establish a settings-aware application startup path without integrating a concrete AI model yet.

## Current Progress

Phase 0 is complete. The repository now contains the documented modular Python package layout, environment-driven settings, a provider-neutral AI contract and registry, a basic application entry point, packaging metadata, setup documentation, and focused automated tests.

## Next Action

Implement the smallest usable PySide6 application shell in `app/ui/` and compose it from the existing `Application` lifecycle without adding voice control, tool execution, file management, web/media control, wake-word behavior, or advanced automation.

## Completion Criteria

The next task is complete when AURA launches a minimal desktop window, the UI remains isolated from provider implementations, and the lifecycle is covered by automated tests without changing the established architecture.
