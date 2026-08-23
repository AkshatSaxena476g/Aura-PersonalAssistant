# Instructions for AI Models Working on AURA

## Mandatory Reading

Before analyzing, editing, or creating implementation code, read:

1. `README.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/PLAN.md`
4. `docs/CURRENT_STATUS.md`
5. `docs/ACTIVE_TASK.md`
6. `docs/ARCHITECTURE.md`
7. `docs/DECISIONS.md`

Read any additional documentation relevant to the task.

## Required Initial Behavior

Before making significant changes:

- Summarize the current project state internally or to the user when requested.
- Identify the current phase and active task.
- Inspect existing code before creating duplicate modules or functionality.
- Preserve working behavior unless the requested change requires modification.
- Follow the established architecture.

## Implementation Rules

- Keep AI provider integrations independent from the assistant core.
- Do not hard-code a specific AI provider into unrelated application modules.
- Prefer small, modular, testable components.
- Do not introduce unrestricted shell or system command execution.
- Validate tool inputs.
- Require confirmation where the established safety rules require it.
- Keep UI, business logic, provider logic, and tool execution separated.
- Avoid unnecessary rewrites.
- Do not silently replace major dependencies or architecture decisions.

## Documentation Rules

After significant work, update the relevant documentation:

- `CURRENT_STATUS.md` for completed work, current work, and next tasks.
- `ACTIVE_TASK.md` when the active task changes.
- `DECISIONS.md` when a meaningful architectural decision is made or changed.
- `PLAN.md` when the development roadmap changes.
- `ARCHITECTURE.md` when major architecture changes.

Do not mark work as complete until the implementation and relevant validation are complete.

## When Context Is Missing

Do not guess about previous architectural decisions or implementation intent. Inspect the relevant code and documentation first. If the information is still missing and materially affects the implementation, ask the user.

## Goal

Maintain continuity across development sessions and across different AI models so that AURA develops as one coherent project.
