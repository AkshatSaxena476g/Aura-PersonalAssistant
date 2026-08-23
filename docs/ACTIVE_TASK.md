## Task

Begin Phase 4: Basic Computer Control.

## Objectives

- Add only narrowly scoped, explicitly approved Windows computer actions on top of the Phase 3 tool boundary.
- Preserve centralized registration, schema validation, permission levels, confirmation gating, and structured results.
- Keep all actions provider-independent and unavailable to Gemini until a later explicit integration decision.
- Add Windows-focused tests for safe and confirmation-required behavior.

## Current Progress

Phase 3 is complete. AURA now has provider-independent tool contracts, structured results, centralized registration and discovery, schema validation, permission and confirmation boundaries, controlled execution, and two safe read-only demonstration tools. The application exposes the execution service as a future integration seam, but Gemini is not connected directly to tool execution.

## Next Action

Design the smallest safe Phase 4 computer-control capability in `app/tools/` using the existing execution service. Any action that changes system state must be narrowly allow-listed, validated, and confirmation-aware. Do not add unrestricted shell execution, arbitrary Python execution, file modification, browser automation, or autonomous actions.

## Completion Criteria

The next task is complete when the selected Windows computer action is implemented as an explicit tool with validated inputs, correct permission behavior, safe failure handling, and focused tests, while all prior conversation and tool-system tests remain functional.
