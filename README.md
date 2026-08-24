# AURA

AURA is a personal AI-powered desktop assistant with a female identity. She is designed to understand natural language through text and voice, perform approved actions on the user's computer, manage files, interact with applications and media, and gradually develop into a capable background assistant.

## Core direction

AURA should be intelligent and capable, composed by default, natural and conversational when appropriate, and occasionally playful. She should adapt her tone to the context while remaining reliable and safe for computer actions.

## Project documentation

Before contributing to the project, read the documents in this order:

1. `docs/AI_INSTRUCTIONS.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/PLAN.md`
4. `docs/CURRENT_STATUS.md`
5. `docs/ACTIVE_TASK.md`
6. `docs/ARCHITECTURE.md`
7. `docs/DECISIONS.md`

The current implementation target is recorded in `docs/ACTIVE_TASK.md`.

## Initial technology direction

AURA is a Windows-first Python desktop application. The technology direction includes PySide6 for the desktop UI, the official `google-genai` SDK behind a swappable AI provider layer, SQLite for persistence, replaceable speech and wake-word providers, Playwright for supported web interaction, pytest for testing, Python logging, and PyInstaller for later packaging. The current Phase 2 implementation supports text conversation through Gemini only.

## Repository layout

```text
AURA/
├── app/
│   ├── ai/       # Provider contracts, registry, factory, and Gemini adapter
│   ├── config/   # Environment-driven application settings
│   ├── core/     # Provider-agnostic lifecycle, conversation, and tool execution
│   ├── data/     # Future persistence and data-access boundary
│   ├── tools/    # Validated, centrally registered, permission-aware tools
│   ├── ui/       # Desktop UI boundary and initial Qt shell
│   └── voice/    # Future replaceable voice boundary
├── docs/         # Project guidance and architecture records
├── tests/        # Automated tests
├── logs/         # Runtime logs; ignored by git
├── main.py       # Basic application entry point
├── pyproject.toml
└── .env.example
```

The Phase 5 foundation supports normal text conversation and provider-neutral Gemini tool calling. Gemini receives function declarations derived from the active `ToolRegistry`; every call is validated and routed through `ToolExecutionService`. Confirmation-required actions display Allow/Cancel controls and cannot execute before approval. The current registered capabilities remain limited to safe demonstrations and the controlled four-application Windows launcher. File management, shell execution, web/media control, voice, text-to-speech, wake-word behavior, persistent memory, and autonomous actions remain unavailable.

## Local setup

From a Windows PowerShell prompt in the repository root, create and activate a virtual environment, then install the project with its development tools:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`, `AURA_AI_PROVIDER=gemini`, and `AURA_AI_MODEL` for Gemini conversation and registered tool calling. Application settings use the standard library, and API credentials are never printed or logged.

Run the AURA desktop application with:

```powershell
py main.py
```

Run the automated tests with:

```powershell
py -m pytest
```

For headless test environments, set `QT_QPA_PLATFORM=offscreen` before running pytest.
