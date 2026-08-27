# Architectural Decisions

## D001: Use Python as the Core Language

**Decision:** Use Python as the primary implementation language.

**Reason:** Python provides strong support for AI integrations, automation, speech processing, file operations, desktop development, testing, and system integration.

## D002: Use a Swappable AI Provider Layer

**Decision:** Do not couple AURA to a single AI provider.

**Reason:** The project will be developed using different AI models and should be able to use providers such as OpenAI, Gemini, Claude, Ollama, or future alternatives without rewriting the assistant core.

## D003: Start as a Desktop Application

**Decision:** Begin with a desktop application and add continuous background and wake-word behavior later.

**Reason:** This allows the core assistant, tool system, and voice pipeline to be developed and tested before adding always-listening complexity.

## D004: Use a Tool-Based Action System

**Decision:** AI models request predefined tools rather than directly executing unrestricted operating-system commands.

**Reason:** This improves safety, validation, maintainability, and control over computer actions.

## D005: Require Confirmation for Sensitive Actions

**Decision:** Potentially destructive or irreversible actions must require appropriate confirmation.

**Reason:** AURA may have access to local files and system functions.

## D006: Initial Platform is Windows

**Decision:** Optimize the first version for Windows.

**Reason:** The initial development and usage target is Windows. Cross-platform support can be evaluated later.

## D007: Personality is Context-Adaptive

**Decision:** AURA is composed and capable by default, natural and conversational when appropriate, and occasionally playful.

**Reason:** The assistant should feel personal without allowing personality to reduce reliability during important tasks.

## D008: Use a Provider-Neutral Tool-Call Boundary

**Decision:** AI providers translate vendor-specific function-call responses into provider-neutral `ToolCallRequest` values. The assistant core derives exposed definitions from the active `ToolRegistry`, validates and prepares requests through `ToolExecutionService`, and owns confirmation state through `PendingToolRequest` values.

**Reason:** This allows Gemini tool calling to be added without coupling the core or UI to Gemini SDK objects. It also ensures every AI-requested action follows the same registry, validation, permission, confirmation, and structured-result path as direct application requests. Confirmation is handled through `Application` boundaries rather than direct widget-to-tool calls, and request identifiers prevent stale or duplicate approval from executing an action twice.

## D009: Commit Local Tool Outcomes as Completed Conversation Turns

**Decision:** A provider-requested tool turn retains its originating user message while awaiting confirmation. Once approved, cancelled, or completed with a structured failure, the conversation service commits that user message together with the local tool outcome represented as an assistant message. Safe tool calls and validation failures follow the same completed-turn rule.

**Reason:** A tool result is part of the conversation state transition even when no second provider request is made. Recording the completed local outcome prevents the next user message from being sent with a history that silently omits the preceding tool turn. Pending state is cleared before decision handling, so stale or duplicate approvals cannot create another completed turn or execute the action twice.

## D010: Use a Managed Qt Worker for Provider-Latency Requests

**Decision:** The desktop composition layer owns a `ConversationRunner` that creates one `QThread` and worker object per active conversation request. The worker calls the existing application handler and emits a structured result through a Qt signal. The MainWindow remains responsible only for rendering and user controls; it never owns conversation logic or directly manipulates core state.

**Reason:** Provider/network latency must not block the Qt event loop. A managed QObject/QThread boundary preserves the existing core and provider architecture, allows the window to remain responsive, prevents duplicate submissions, and provides deterministic cleanup after each request.

## D011: Centralize the Initial Dark Theme

**Decision:** The initial dark palette is defined in `app/ui/theme.py` and applied at the application/window boundary rather than scattered across individual event handlers or feature modules.

**Reason:** A centralized stylesheet keeps the minimal UI coherent, makes contrast and disabled-state behavior easy to review, and avoids introducing an unrelated visual redesign while preserving the existing layout and confirmation controls.

## D012: Preserve Provider Composition While Diagnosing Async Failures

**Decision:** The configured `GeminiProvider`, `Application`, and `ConversationService` remain composed once at startup and are invoked through the existing managed Qt worker. Provider failures are diagnosed with redacted exception-type/detail logging and cross-thread tests before introducing provider-per-thread reconstruction or moving core state across threads.

**Reason:** The direct and worker-backed requests reproduced the same HTTP 429 quota failure, so recreating the provider or moving conversation state would not address the actual cause and could introduce new history or confirmation races. The UI remains responsive without weakening the provider-neutral architecture.

## D013: Restrict Phase 6A Browser Destinations

**Decision:** Implement web and YouTube browser actions as three explicit tools—`search_web`, `open_youtube`, and `search_youtube`—with internally generated fixed destinations. Search tools accept only bounded validated queries; YouTube homepage opening accepts no arguments. Every browser-opening tool requires confirmation and uses the default browser without shell execution.

**Reason:** This provides useful web discovery while keeping the execution boundary narrow. It prevents Gemini or user input from supplying arbitrary URLs, executable paths, browser arguments, or shell commands, and reuses the established registry, validation, structured-result, and Allow/Cancel architecture instead of introducing generic browser automation.

## D014: Use Explicit Windows Media and Audio Adapters

**Decision:** Implement `media_play_pause`, `media_next`, and `media_previous` with fixed Windows media virtual keys sent through a correctly sized `ctypes` User32 `SendInput` structure. Implement volume and mute controls through a pinned pycaw adapter over the default Windows Core Audio endpoint. Keep platform imports and native calls isolated in `app/tools/media.py` and `app/tools/audio.py`.

**Reason:** The standard library is sufficient for fixed media-key injection, while system endpoint volume and mute require a maintained Core Audio wrapper. The explicit adapters avoid unrestricted keyboard, shell, subprocess, or player-specific commands. The pycaw backend is lazy and balances COM initialization per operation because SAFE tools execute in the managed conversation worker thread. Unsupported platforms, unavailable audio interfaces, partial native input, and API failures are converted into structured safe tool results.

## D015: Centralize Phase 7A Filesystem Path Policy

**Decision:** Implement Phase 7A filesystem discovery through a shared `FileSystemPolicy` that maps approved location identifiers to the current user's standard directories and resolves only relative paths inside those roots. Use the same policy for `list_directory`, `search_files`, `get_file_info`, and `read_text_file`.

**Reason:** AURA must provide useful local discovery without giving Gemini or the user an unrestricted filesystem path capability. Resolved-path containment, rejection of traversal/absolute/network paths, symlink escape protection, bounded search, allow-listed text extensions, and read-size/content limits are security invariants that must not be duplicated across tools. All four tools remain read-only SAFE operations routed through the existing registry and execution service; Phase 7B write and destructive operations are intentionally deferred.

## D016: Extend FileSystemPolicy for Bounded Confirmation-Aware Writes

**Decision:** Implement Phase 7B file creation through `create_directory` and `write_text_file` as `CONFIRMATION_REQUIRED` tools that extend the same `FileSystemPolicy`, location-identifier + relative-path contract, `relative_to()` containment, and symlink-escape checks used in Phase 7A, with additional per-part filename validation (invalid characters, trailing space/period, Windows reserved names) and bounded allow-listed text writes (six extensions, 50,000 characters, 1 MiB UTF-8, parent-must-exist).

**Reason:** AURA needs controlled creation without opening unrestricted filesystem writes. Reusing the centralized policy keeps security invariants consistent and avoids duplicated path logic. Confirmation-gating ensures every state-changing filesystem operation follows the existing `PendingToolRequest` Allow/Cancel flow, while parent-must-exist and single-directory creation prevent implicit recursive writes. Move, copy, delete, recursive delete, and binary writes are postponed to preserve a narrow, testable boundary before later automation.
