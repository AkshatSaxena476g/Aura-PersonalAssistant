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
