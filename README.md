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

AURA is a Windows-first Python desktop application. The planned technology direction includes PySide6 for the desktop UI, a swappable AI provider layer, SQLite for persistence, replaceable speech and wake-word providers, Playwright for supported web interaction, pytest for testing, Python logging, and PyInstaller for later packaging.

## Repository layout

```text
AURA/
├── app/
│   ├── ai/       # Provider-neutral AI contracts and provider registry
│   ├── config/   # Environment-driven application settings
│   ├── core/     # Provider-agnostic application lifecycle and orchestration
│   ├── data/     # Future persistence and data-access boundary
│   ├── tools/    # Future validated, centrally registered action tools
│   ├── ui/       # Future desktop UI boundary
│   └── voice/    # Future replaceable voice boundary
├── docs/         # Project guidance and architecture records
├── tests/        # Automated tests
├── logs/         # Runtime logs; ignored by git
├── main.py       # Basic application entry point
├── pyproject.toml
└── .env.example
```

The initial foundation deliberately contains no concrete AI provider, desktop UI, voice control, unrestricted command execution, file management, web/media control, wake-word behavior, or advanced automation.

## Local setup

From a Windows PowerShell prompt in the repository root, create and activate a virtual environment, then install the project with its development tools:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` when environment-based settings are needed. The Phase 0 application uses standard-library configuration loading; provider credentials remain reserved for later provider implementations.

Run the foundation application with:

```powershell
py main.py
```

Run the automated tests with:

```powershell
py -m pytest
```
