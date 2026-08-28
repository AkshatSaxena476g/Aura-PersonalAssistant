import os

import pytest
from PySide6.QtWidgets import QApplication

from app.ai import ChatMessage, MessageRole, ProviderResponse
from app.config import Settings
from app.core import Application, ConversationResult
from app.ui import MainWindow
from app.ui.voice_worker import VoiceRunner
from app.voice import (
    MockSTTProvider,
    MockTTSProvider,
    VoiceRegistry,
    create_voice_registry,
)
from app.voice.capture import AudioCaptureService
from app.voice.provider import SynthesisResult, TranscriptionResult
from app.voice.sapi_provider import SapiTTSProvider
from app.voice.whisper_provider import WhisperSTTProvider


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()


def test_transcription_result_requires_exactly_one():
    with pytest.raises(ValueError):
        TranscriptionResult()
    with pytest.raises(ValueError):
        TranscriptionResult(text="hi", error_message="err")
    assert TranscriptionResult(text="hi").succeeded is True
    assert TranscriptionResult(error_message="fail").succeeded is False


def test_synthesis_result_validation():
    with pytest.raises(ValueError):
        SynthesisResult(success=True, message=" ", error_code=None)
    with pytest.raises(ValueError):
        SynthesisResult(success=True, message="ok", error_code="x")
    with pytest.raises(ValueError):
        SynthesisResult(success=False, message="fail", error_code=None)
    assert SynthesisResult.ok("ok").success is True
    assert SynthesisResult.failure("fail", error_code="x").success is False


def test_voice_registry():
    reg = VoiceRegistry()
    reg.register_stt("whisper", lambda: MockSTTProvider())
    reg.register_tts("sapi", lambda: MockTTSProvider())
    with pytest.raises(ValueError, match="already registered"):
        reg.register_stt("whisper", lambda: MockSTTProvider())
    with pytest.raises(LookupError):
        reg.create_stt("unknown")
    assert reg.create_stt("WHISPER").name == "mock"
    assert "whisper" in reg.stt_names


def test_create_voice_registry_defaults():
    s = Settings.from_environment({})
    reg = create_voice_registry(s)
    assert "whisper" in reg.stt_names
    assert "sapi" in reg.tts_names
    assert "mock" in reg.stt_names


def test_settings_voice_defaults():
    s = Settings.from_environment({})
    assert s.voice_enabled is False
    assert s.stt_provider == "whisper"
    assert s.tts_provider == "sapi"
    assert s.whisper_model == "base"
    assert s.tts_rate == 180
    assert s.voice_auto_speak is False


def test_settings_voice_parsing():
    s = Settings.from_environment(
        {
            "AURA_VOICE_ENABLED": "true",
            "AURA_STT_PROVIDER": "mock",
            "AURA_TTS_PROVIDER": "mock",
            "AURA_WHISPER_MODEL": "tiny",
            "AURA_TTS_RATE": "200",
            "AURA_VOICE_AUTO_SPEAK": "yes",
        }
    )
    assert s.voice_enabled is True
    assert s.stt_provider == "mock"
    assert s.tts_rate == 200
    assert s.voice_auto_speak is True


def test_settings_voice_rejects_bad_rate():
    with pytest.raises(ValueError, match="AURA_TTS_RATE"):
        Settings.from_environment({"AURA_TTS_RATE": "not-int"})
    with pytest.raises(ValueError, match="AURA_TTS_RATE"):
        Settings.from_environment({"AURA_TTS_RATE": "10"})


def test_mock_stt_empty():
    p = MockSTTProvider()
    r = p.transcribe(b"")
    assert r.error_message is not None
    assert p.transcribe(b"\x00\x01").text == "hello aura"


def test_mock_tts():
    p = MockTTSProvider()
    assert p.speak("  ").error_code == "empty_text"
    assert p.speak("hello").success is True
    assert p.spoken == ["hello"]
    p.stop()
    assert p.stopped is True


def test_whisper_provider_bounds():
    p = WhisperSTTProvider(model_factory=lambda: None)
    assert p.transcribe(b"").error_message is not None
    assert p.transcribe(b"a" * (11 * 1024 * 1024)).error_message is not None
    assert p.transcribe(b"\x00\x01", sample_rate=0).error_message is not None
    assert p.transcribe(b"\x00\x01", sample_rate=99999).error_message is not None
    p.close()
    assert p.transcribe(b"\x00\x01").error_message is not None


def _fake_whisper_model(text=" hello world "):
    class M:
        def transcribe(self, path, language=None):
            return {"text": text}

    return M()


def test_whisper_provider_success():
    p = WhisperSTTProvider(model_factory=lambda: _fake_whisper_model())
    audio = b"\x00\x01" * 8000
    r = p.transcribe(audio, sample_rate=16000)
    assert r.text == "hello world"


def test_whisper_provider_empty_text():
    p = WhisperSTTProvider(model_factory=lambda: _fake_whisper_model("   "))
    r = p.transcribe(b"\x00\x01" * 100, sample_rate=16000)
    assert r.error_message is not None


def test_whisper_provider_model_load_failure():
    def bad_factory():
        raise OSError("missing")

    p = WhisperSTTProvider(model_factory=bad_factory)
    r = p.transcribe(b"\x00\x01" * 100, sample_rate=16000)
    assert "unavailable" in r.error_message.lower()


class FakeEngine:
    def __init__(self, fail=False):
        self.said = []
        self.fail = fail
        self.stopped = False

    def setProperty(self, *a, **kw):
        pass

    def say(self, text):
        if self.fail:
            raise RuntimeError("fail")
        self.said.append(text)

    def runAndWait(self):
        if self.fail:
            raise RuntimeError("fail")

    def stop(self):
        self.stopped = True


def test_sapi_provider_success():
    eng = FakeEngine()
    p = SapiTTSProvider(engine_factory=lambda: eng)
    r = p.speak(" hello ")
    assert r.success is True
    assert eng.said == ["hello"]
    p.stop()
    assert eng.stopped is True
    p.close()
    assert p.speak("hi").error_code == "tts_closed"


def test_sapi_provider_empty_and_failure():
    eng = FakeEngine()
    p = SapiTTSProvider(engine_factory=lambda: eng)
    assert p.speak("  ").error_code == "empty_text"
    eng2 = FakeEngine(fail=True)
    p2 = SapiTTSProvider(engine_factory=lambda: eng2)
    r = p2.speak("hi")
    assert r.success is False
    assert r.error_code == "tts_failed"


def test_application_transcribe_disabled():
    s = Settings.from_environment({})
    app = Application(settings=s, provider=None)
    r = app.transcribe_and_send(b"\x00\x01")
    assert "disabled" in r.error_message.lower()


def test_application_transcribe_no_stt():
    s = Settings.from_environment({"AURA_VOICE_ENABLED": "true"})
    app = Application(settings=s, provider=None)
    r = app.transcribe_and_send(b"\x00\x01")
    assert "not configured" in r.error_message.lower()


def test_application_transcribe_success():
    class FakeProvider:
        name = "fake"

        def complete(self, messages, tool_definitions=()):
            return ProviderResponse(message=ChatMessage(MessageRole.ASSISTANT, "reply"))

    s = Settings.from_environment({"AURA_VOICE_ENABLED": "true"})

    class FakeSTT:
        def transcribe(self, b, sample_rate=16000):
            return TranscriptionResult(text="hello")

    app = Application(settings=s, provider=FakeProvider(), stt_provider=FakeSTT())
    r = app.transcribe_and_send(b"\x00\x01")
    assert r.succeeded is True
    assert r.assistant_message.content == "reply"


def test_application_transcribe_stt_failure():
    class FakeProvider:
        name = "fake"

        def complete(self, messages, tool_definitions=()):
            return ProviderResponse(message=ChatMessage(MessageRole.ASSISTANT, "ok"))

    s = Settings.from_environment({"AURA_VOICE_ENABLED": "true"})

    class BadSTT:
        def transcribe(self, b, sample_rate=16000):
            return TranscriptionResult(error_message="nope")

    app = Application(settings=s, provider=FakeProvider(), stt_provider=BadSTT())
    r = app.transcribe_and_send(b"\x00\x01")
    assert r.error_message == "nope"


def test_application_auto_speak():
    s = Settings.from_environment(
        {"AURA_VOICE_ENABLED": "true", "AURA_VOICE_AUTO_SPEAK": "true"}
    )
    mock_tts = MockTTSProvider()

    class FakeProvider:
        name = "fake"

        def complete(self, messages, tool_definitions=()):
            return ProviderResponse(
                message=ChatMessage(MessageRole.ASSISTANT, "spoken reply")
            )

    app = Application(
        settings=s,
        provider=FakeProvider(),
        stt_provider=MockSTTProvider(),
        tts_provider=mock_tts,
    )
    app.send_message("hi")
    assert mock_tts.spoken == ["spoken reply"]


def test_capture_start_failure_without_sounddevice(monkeypatch):
    svc = AudioCaptureService()
    import sys

    monkeypatch.setitem(sys.modules, "sounddevice", None)
    # force import failure by patching __import__
    assert svc.start() is False
    assert svc.stop() is None


def test_voice_runner_busy(qapp):
    def handler(audio, sr):
        return ConversationResult(error_message="done")

    runner = VoiceRunner(handler)
    assert runner.busy is False
    # mock thread start without actually starting thread
    runner._thread = object()
    assert runner.busy is True
    assert runner.submit(b"\x00", 16000) is False
    runner._thread = None
    runner.shutdown()


def test_main_window_voice_button_visibility(qapp):
    w = MainWindow(voice_enabled=False)
    assert w.voice_button.isHidden() is True
    w.close()
    w2 = MainWindow(voice_enabled=True)
    assert w2.voice_button.isHidden() is False
    assert w2.voice_button.objectName() == "voiceButton"
    w2.close()


def test_main_window_voice_busy_lock(qapp):
    w = MainWindow(
        voice_enabled=True,
        voice_transcribe_handler=lambda a, s: ConversationResult(error_message="done"),
    )
    w._request_active = True
    w._set_request_controls_busy(True)
    assert w.voice_button.isEnabled() is False
    w._request_active = False
    w._set_request_controls_busy(False)
    assert w.voice_button.isEnabled() is True
    w.close()


def test_main_window_hold_to_talk_flow(qapp):
    transcribed = []

    def fake_transcribe(audio, sr):
        transcribed.append(audio)
        return ConversationResult(
            assistant_message=ChatMessage(MessageRole.ASSISTANT, "voice reply")
        )

    started = []
    stopped_audio = b"\x00\x01" * 100

    def fake_start():
        started.append(True)
        return True

    def fake_stop():
        return stopped_audio

    w = MainWindow(
        voice_enabled=True,
        voice_transcribe_handler=fake_transcribe,
        voice_start_handler=fake_start,
        voice_stop_handler=fake_stop,
    )
    w._start_voice_capture()
    assert w._voice_recording is True
    assert w.voice_button.text() == "Listening..."
    w._stop_voice_capture()
    assert w._voice_recording is False
    assert transcribed == [stopped_audio]
    assert "voice reply" in w.conversation_display.toPlainText()
    w.close()


def test_main_window_voice_no_audio(qapp):
    w = MainWindow(
        voice_enabled=True,
        voice_start_handler=lambda: True,
        voice_stop_handler=lambda: b"",
    )
    w._start_voice_capture()
    w._stop_voice_capture()
    assert "No audio" in w.conversation_display.toPlainText()
    w.close()


def test_main_window_voice_respects_pending(qapp):
    from types import SimpleNamespace

    pending = SimpleNamespace(request_id="r1", confirmation_message="confirm?")
    w = MainWindow(
        voice_enabled=True,
        voice_start_handler=lambda: True,
        voice_stop_handler=lambda: b"\x00\x01",
    )
    w._pending_request_id = "r1"
    w._start_voice_capture()
    assert w._voice_recording is False
    w.close()
