from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from .models import Character


class VoicePipeline:
    """Connect recording, offline STT, conversation, local TTS and playback."""

    def __init__(self, recorder, stt, conversation, tts, player, data_dir: str | Path):
        self.recorder = recorder
        self.stt = stt
        self.conversation = conversation
        self.tts = tts
        self.player = player
        self.temp_root = Path(data_dir).resolve() / "audio-tmp"

    def run_once(self, character: Character, child: dict, record_seconds: int = 6):
        self.temp_root.mkdir(parents=True, exist_ok=True)
        directory = self.temp_root / str(uuid.uuid4())
        directory.mkdir()
        try:
            input_path = directory / "input.wav"
            output_path = directory / "output.wav"
            self.recorder.record(input_path, record_seconds)
            transcript = self.stt.transcribe(input_path)
            if not transcript:
                raise RuntimeError("No speech was recognized")
            answer = self.conversation.answer(transcript, character, child)
            self.tts.synthesize(answer.text, output_path)
            self.player.play(output_path)
            return {"transcript": transcript, "answer": answer.text, "mode": answer.mode}
        finally:
            shutil.rmtree(directory, ignore_errors=True)

