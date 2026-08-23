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
