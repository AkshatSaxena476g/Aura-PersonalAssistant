## Task

Implement Phase 6A controlled Web and YouTube capabilities using AURA's existing provider-neutral tool architecture — complete. Do not start Phase 6B automatically.

## Completed Tools

The default registry now includes three confirmation-required tools:

- `search_web` accepts only a validated, trimmed query of at most 200 characters and internally constructs a URL for Google web search.
- `open_youtube` accepts no arguments and internally opens only the fixed official YouTube homepage.
- `search_youtube` accepts only a validated, trimmed query of at most 200 characters and internally constructs a YouTube search URL.

All query values are URL-encoded. Extra arguments, empty or invalid queries, raw URLs, arbitrary browser arguments, and arbitrary executable destinations are rejected. Browser opening uses Python's default-browser mechanism and never invokes a shell. All three tools report structured safe failures and require the existing confirmation flow.

## Architecture Integration

The implementation is in `app/tools/web.py`. `app/tools/defaults.py` registers the tools, and `app/tools/__init__.py` exports them. Gemini receives their declarations automatically from the active registry through the existing provider-neutral adapter. The UI and core were not given browser-specific logic.

The existing path remains: provider-neutral `ToolCallRequest` → `ToolExecutionService.prepare()` → strict validation and permission inspection → `PendingToolRequest` → existing Allow/Cancel UI → `execute_prepared()` only after approval. Cancellation, stale approval, and duplicate approval cannot open the browser. No parallel confirmation system or generic URL tool was introduced.

## Validation

The focused Phase 6A suite passes with **17 tests**. The complete suite passes with **88 tests**. Tests cover all three tools, URL encoding, validation boundaries, extra-argument rejection, fixed YouTube destination, mocked browser success/failure, unsupported platform behavior, registry membership, Gemini declaration derivation, confirmation-required behavior, Cancel, Allow exactly once, and stale approval. Existing launcher, conversation, provider, worker, dark-theme, and post-tool regression coverage remains passing.

The package wheel built successfully. Windows `python.exe main.py` launched successfully with the title `AURA | Personal Desktop Assistant - AURA` and remained running until clean smoke-test shutdown. Automated tests performed no real browser launches. The static security scan found no shell execution, arbitrary URL tool, or browser-argument path. No API key or `.env` value was exposed, modified, regenerated, or committed.

## Gemini Availability Note

Live Gemini requests remain subject to the previously confirmed external HTTP 429 `RESOURCE_EXHAUSTED` free-tier quota condition. Phase 6A's Gemini declaration and tool-call tests therefore use mocked provider responses and do not alter the provider architecture or API configuration.

## Next Action

Do not begin Phase 6B automatically. The recommended next task is Phase 6B: Basic Media Controls.
