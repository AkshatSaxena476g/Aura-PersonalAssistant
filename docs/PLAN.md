# AURA Development Plan

## Phase 0: Planning and Project Foundation
Project documentation, architecture, repository structure, configuration strategy, coding rules, and AI provider abstraction.

## Phase 1: Basic Desktop Application
PySide6 application, basic interface, application lifecycle, and settings foundation.

## Phase 2: AI Core
Provider abstraction, Gemini model integration, conversation handling, and structured AI responses.

## Phase 3: Tool System
Provider-independent tool definitions, centralized registry, validation, permission policy, controlled execution, and structured tool results.

## Phase 4: Basic Computer Control
The first narrowly scoped Windows action: confirmation-aware launching of an internal allow-list of approved applications.

## Phase 5: AI Tool Calling Integration
Provider-neutral tool-call representation, provider-derived tool declarations, Gemini function-call translation, registry-based discovery, confirmation state, and controlled AI-requested tool execution.

## Phase 6A: Controlled Web and YouTube Capabilities — complete
Restricted `search_web`, `open_youtube`, and `search_youtube` tools using fixed internally generated destinations, strict validation, default-browser opening, and the existing confirmation flow. Arbitrary URLs, browser automation, shell commands, and executable browser arguments are intentionally unsupported.

## Phase 6B: Basic Media Controls — complete
Bounded global media playback and Windows system-volume controls through explicit SAFE tools, with mocked platform tests, lazy platform integration, and no arbitrary audio commands.

## Phase 7A: Safe File and Folder Discovery — complete
Read-only, bounded discovery through `list_directory`, `search_files`, `get_file_info`, and `read_text_file`. All targets use approved user-location identifiers and centralized resolved-path validation; write and destructive operations are not included.

## Phase 7B: Controlled File Creation and Organization — complete
Bounded, confirmation-aware creation through `create_directory` and `write_text_file` inside the same six approved locations and centralized `FileSystemPolicy`. Both tools validate filenames, enforce allow-listed text extensions, and apply size/content limits; destructive operations (delete, move/copy, binary writes) remain out of scope.


## Phase 8: Voice Interaction
Microphone input, speech-to-text, text-to-speech, and push-to-talk.

## Phase 9: Wake Word and Background Mode
Wake-word activation, background operation, and optional startup behavior.

## Phase 10: Memory and Personalization
Persistent settings, relevant long-term memory, preferences, and personalized behavior.

## Phase 11: Advanced Automation
Multi-step tasks, routines, scheduled actions, and controlled autonomous workflows.

## Phase 12: UI, Personality, and Polish
Final visual identity, personality behavior, animations, settings, and usability refinement.

## Phase 13: Testing, Security, and Packaging
Testing, error handling, safety review, packaging, installation, and release preparation.

## Development Rule

Complete and stabilize the current phase before expanding into unrelated future phases unless a dependency requires earlier implementation.
