# AURA Architecture

## High-Level Architecture

User interaction flows through the UI and voice layers into the assistant core.

The assistant core communicates with an AI provider through a provider abstraction layer. The AI may request approved tools. Tools are validated and executed by the application, and results can be returned to the AI or directly to the user interface.

Conceptually:

User Input
    ↓
UI / Voice Layer
    ↓
Assistant Core / Orchestrator
    ├── AI Provider Layer
    │   ├── OpenAI provider
    │   ├── Gemini provider
    │   ├── Claude provider
    │   └── Local/Ollama provider
    │
    └── Tool System
        ├── Application tools
        ├── File tools
        ├── System tools
        ├── Web tools
        └── Media tools
    ↓
Response
    ↓
UI / Text-to-Speech

## Architectural Rules

- The assistant core must not depend directly on one AI provider.
- Providers should implement a common interface.
- Tools should be registered centrally.
- AI-generated requests must be validated before execution.
- Sensitive actions should use confirmation or permission checks.
- UI logic should remain separate from assistant and tool logic.
- Voice providers should also be replaceable where practical.

## Provider-Neutral Tool-Calling Flow

Provider-specific function-calling responses are translated inside the AI provider layer into the neutral `ToolCallRequest` type. The assistant core never receives Gemini SDK objects. Registered `ToolDefinition` values are derived from the active `ToolRegistry` and passed to the provider for declaration; Gemini-specific declarations are not maintained separately.

The execution path is:

```text
User / UI
    ↓
ConversationService
    ↓
AIProvider.complete(messages, tool_definitions)
    ↓
Provider-neutral ToolCallRequest
    ↓
ToolExecutionService.prepare()
    ↓
Validation and permission inspection
    ├── safe tool → controlled local execution
    └── confirmation-required tool → PendingToolRequest
                                      ↓
                                UI Allow / Cancel
                                      ↓
                            ToolExecutionService.execute_prepared()
                                      ↓
                                Structured ToolResult
                                      ↓
                                      UI
```

The `ConversationService` owns pending confirmation state and request identifiers. Approval and cancellation are exposed through `Application` methods so UI widgets never invoke tools directly. Pending requests are cleared before execution or cancellation, making stale and duplicate approval attempts non-executable.

Conversation requests that may involve network/provider latency are submitted by the desktop composition layer to a managed `QThread` worker. The worker invokes the existing application callback and emits a structured result through a Qt signal. Only the main Qt thread updates widgets, confirmation controls, status text, or conversation display state. The worker owns one request at a time and releases its thread after completion.

## Controlled Phase 6A Browser Boundary

Phase 6A browser capabilities are explicit tools rather than generic browser automation. `search_web` and `search_youtube` accept only a bounded validated query and construct their fixed search endpoints internally. `open_youtube` accepts no arguments and uses only the fixed official YouTube homepage. All three tools use the default browser through Python's browser-opening mechanism, require `ToolPermission.CONFIRMATION_REQUIRED`, and return through the existing structured tool-result path.

Raw URLs, arbitrary browser arguments, executable destinations, shell commands, and a generic `open_url` tool are intentionally outside the architecture. The tool layer owns URL construction and the core owns validation, pending confirmation, approval, cancellation, and stale-request protection.

## Controlled Phase 6B Media and Audio Boundary

Phase 6B exposes explicit SAFE tools for three global media actions and six default-output volume actions. Media actions use fixed Windows virtual-key constants through a `ctypes` User32 `SendInput` adapter; no generic key or command input is accepted. Volume and mute actions use a lazy pycaw adapter over the Windows Core Audio endpoint interface and return normalized volume data from 0 to 100.

The platform adapters live in `app/tools/media.py` and `app/tools/audio.py`. They remain behind the existing `Tool` contract and `ToolExecutionService`; the UI, `Application`, `ConversationService`, and `GeminiProvider` do not contain media/audio logic. SAFE actions are still registry-discovered and validated before execution. Unsupported platforms and native API failures become structured tool failures without raw system details.

Because provider requests and SAFE tool calls run through the managed worker, the default pycaw backend balances COM initialization and uninitialization around each audio operation. This keeps COM state local to the thread performing the Core Audio call while leaving the UI event loop responsive.

## Controlled Phase 7A Filesystem Boundary

Phase 7A provides four explicit SAFE, read-only tools: `list_directory`, `search_files`, `get_file_info`, and `read_text_file`. They use the existing registry, schema validation, `ToolExecutionService`, and structured `ToolResult` path; the UI and provider layers never access the filesystem directly.

A centralized `FileSystemPolicy` maps the controlled location identifiers `desktop`, `documents`, `downloads`, `pictures`, `music`, and `videos` to directories under the current user's home directory. Tools accept only a location identifier plus an optional relative path. They do not accept arbitrary absolute, drive-qualified, UNC, network, or user-supplied root paths.

The policy resolves candidates with `pathlib`, rejects NUL characters and parent traversal, verifies resolved containment with `Path.relative_to()`, and resolves symlinks before allowing a target. Bounded recursive search does not follow directory symlinks and is limited by depth, scanned entries, and result count. Text reads are limited to an allow-list of text extensions, a maximum file size, and a maximum returned character count. Successful results expose approved location identifiers and relative paths only; policy, filesystem, encoding, and size failures become structured safe results without raw absolute paths or tracebacks.

## Proposed Application Layout

```text
AURA/
├── app/
│   ├── core/
│   ├── ai/
│   ├── tools/
│   ├── voice/
│   ├── ui/
│   ├── data/
│   └── config/
├── tests/
├── docs/
└── main.py
```

The exact implementation structure may evolve, but changes affecting major module boundaries should be recorded in `DECISIONS.md`.
