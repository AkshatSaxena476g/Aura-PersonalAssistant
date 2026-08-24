## Current Phase

Phase 4: Basic Computer Control — complete.

## Completed

- Phases 0–3 remain intact, including the replaceable Gemini provider layer, provider-agnostic conversation service, PySide6 desktop lifecycle, centralized tool registry, schema validation, structured results, and permission boundary.
- `app/tools/windows_applications.py` adds `LaunchApplicationTool` using the existing `Tool` contract and `ToolExecutionService`.
- The launcher accepts only the normalized internal identifiers `notepad`, `calculator`, `settings`, and `file_explorer`.
- Internal fixed targets resolve those identifiers to `notepad.exe`, `calc.exe`, `ms-settings:`, and `explorer.exe`. User-provided executable paths, commands, URLs, arguments, and shell expressions are not accepted.
- Windows launching uses `subprocess.Popen` with an argument list and `shell=False` for executable targets, and `os.startfile` for the Windows Settings URI. No unrestricted command interpreter is used.
- Application launching is declared `confirmation_required`, so the execution service blocks it unless explicit confirmation or an injected confirmation handler approves the validated request.
- The launcher is registered through `create_default_tool_registry()` and exposed through the existing `Application.execute_tool()` boundary. Gemini function calling is not connected to tools.
- Mocked tests cover every supported application, normalization, unsupported identifiers, arbitrary paths and arguments, confirmation behavior, permission behavior, launch failures, unsupported platforms, registry integration, and structured results.
- README documentation was updated to reflect the controlled application-launching capability.

## Currently Working On

Phase 4 is complete. AURA can now request a narrowly scoped, confirmation-aware launch of one of four internally allow-listed Windows applications through the provider-independent tool system.

## Next Task

Begin Phase 5: File and Folder Management. Extend the existing tool boundary only with explicitly scoped, validated file operations, confirmation for destructive changes, and Windows-focused tests. Do not add arbitrary file paths or deletion behavior without the required safety controls.

## Validation

- `QT_QPA_PLATFORM=offscreen py -3.12 -m pytest -q`: 48 tests passed.
- Package wheel build: completed successfully after adding the Windows launcher.
- `py main.py` on Windows: launched successfully with the local configuration; the validation process reported the window title `AURA | Personal Desktop Assistant - AURA` and was then closed cleanly.
- Automated external launches were mocked; no real application was opened during tests.
- Temporary build and editable-install artifacts were removed after validation.

## Known Issues

No known implementation issues. The launcher is intentionally Windows-only, confirmation-required, and not connected to Gemini or the chat UI. Shell execution, arbitrary executable launching, process termination, file modification, browser automation, voice, media control, memory, and autonomous actions remain unavailable.

## Last Updated

2026-08-23 — Phase 4 controlled Windows application launching implemented and verified.
