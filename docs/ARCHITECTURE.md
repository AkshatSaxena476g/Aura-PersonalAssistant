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
