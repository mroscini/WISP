from __future__ import annotations

from pathlib import Path

from wisp.models import Answer, Character
from wisp.voice_pipeline import VoicePipeline


class Recorder:
    def record(self, path, _seconds):
        Path(path).write_bytes(b"RIFF")


class Stt:
    def transcribe(self, _path):
        return "Raccontami della luna"


class Conversation:
    def answer(self, text, _character, _child):
        assert text == "Raccontami della luna"
        return Answer("La luna illumina la notte.", "llm-with-rag")


class Tts:
    def synthesize(self, text, path):
        assert "luna" in text
        Path(path).write_bytes(b"RIFF")


class Player:
    def __init__(self):
        self.played = False

    def play(self, path):
        self.played = Path(path).exists()


def test_voice_pipeline_connects_all_stages(tmp_path):
    player = Player()
    pipeline = VoicePipeline(Recorder(), Stt(), Conversation(), Tts(), player, tmp_path)
    result = pipeline.run_once(Character("moon", "Moon"), {}, 1)
    assert result["transcript"] == "Raccontami della luna"
    assert result["mode"] == "llm-with-rag"
    assert player.played

