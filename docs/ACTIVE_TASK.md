## Task

Diagnose and safely handle the Gemini request failure observed after the managed background-worker and dark-theme update — complete. Do not begin Phase 6.

## Exact Root Cause

The configured provider initialized successfully. A fresh redacted comparison issued one minimal request directly through `GeminiProvider.complete(...)` and one through the exact desktop path `ConversationRunner` → `Application.send_message` → `ConversationService` → `GeminiProvider` → Google GenAI SDK. Both reached `self._client.models.generate_content` and raised `google.genai.errors.ClientError` with HTTP `429 RESOURCE_EXHAUSTED`.

The API detail identified exhausted free-tier `generate_content` request quota for the configured model. This is an external Gemini account/model quota condition. It is not a Qt cross-thread failure, altered worker argument, provider initialization error, malformed AURA request, or conversation-state regression. The worker update only moved the blocking call off the UI thread and delivered its result asynchronously; it did not change the provider request or cause the API rejection.

## Completed Changes

`GeminiProvider` continues to log only the exception type and bounded detail with the configured credential redacted. It now detects an explicit SDK/API HTTP 429 or `RESOURCE_EXHAUSTED` status and returns a safe quota-specific `ProviderRequestError`. Non-quota failures retain the generic network/API configuration message. No API key or `.env` value was printed, changed, regenerated, or committed.

The existing composition remains intact: one configured provider, one `Application`/`ConversationService`, and one managed `ConversationRunner` request thread at a time. Provider calls remain off the Qt UI thread, and only structured results cross back to the main thread. Tool validation, controlled execution, confirmation-required launcher behavior, Allow/Cancel handling, post-tool history commits, dark theme, and UI restoration were not bypassed or rewritten.

## Validation

Focused provider and worker tests pass with **13 tests**. The complete suite passes with **71 tests**. The package wheel builds successfully. A Windows launch using `python.exe main.py` showed `AURA | Personal Desktop Assistant - AURA` and remained running until clean smoke-test shutdown.

The fresh direct live request and the fresh worker-path live request both reached Gemini and returned the same redacted HTTP 429 quota response. Live normal conversation, sequential messages, arithmetic, and live Calculator Allow/Cancel could not be exercised against Gemini because the service rejected the initial request. Mocked automated coverage continues to verify the normal conversation, tool-call, confirmation, cancellation, responsiveness, state-restoration, and mocked external-launch behavior.

## Next Action

Keep Phase 6 deferred. When the external Gemini quota becomes available, manually rerun a normal conversation, sequential messages, arithmetic, and the Calculator Allow and Cancel flows. No code change can restore an exhausted external quota; the current implementation now reports that condition explicitly and safely.
