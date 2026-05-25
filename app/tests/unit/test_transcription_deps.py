from __future__ import annotations

from app.api import deps


class DummySettings:
    use_mock_adapters = True
    use_real_whisper_streaming = True
    whisper_model_name = "base"


class DummyStreamingService:
    def __init__(self, model_size: str, device: str, chunk_duration: float):
        self.model_size = model_size
        self.device = device
        self.chunk_duration = chunk_duration


def test_get_transcription_service_can_use_real_whisper_with_mock_data(
    monkeypatch,
):
    deps.get_settings.cache_clear()

    monkeypatch.setattr(deps, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(deps, "_use_mock", lambda: True)

    import app.infrastructure.ai.transcription.faster_whisper_adapter as adapter

    monkeypatch.setattr(
        adapter,
        "StreamingFasterWhisperService",
        DummyStreamingService,
    )

    service = deps.get_transcription_service()

    assert isinstance(service.streaming_service, DummyStreamingService)
    assert service.streaming_service.model_size == "base"
