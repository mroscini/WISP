from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .elevenlabs import ElevenLabsClient, ElevenLabsError, ElevenLabsTextToSpeech


PIPER_VOICES = {
    "piper-paola": {
        "name": "Paola",
        "kind": "piper",
        "description": "Voce italiana chiara e naturale",
        "model": "it_IT-paola-medium",
    },
    "piper-riccardo": {
        "name": "Riccardo",
        "kind": "piper",
        "description": "Voce italiana leggera e veloce",
        "model": "it_IT-riccardo-x_low",
    },
}


class VoiceError(ValueError):
    pass


class VoiceStore:
    def __init__(self, root: str | Path, elevenlabs: ElevenLabsClient | None = None):
        self.root = Path(root).resolve()
        self.piper_dir = self.root / "piper"
        self.elevenlabs = elevenlabs

    def list(self) -> list[dict[str, Any]]:
        voices = []
        for voice_id, item in PIPER_VOICES.items():
            model_path = self.piper_dir / f"{item['model']}.onnx"
            voices.append({"id": voice_id, **item, "available": model_path.exists()})
        return voices

    def list_elevenlabs(self) -> list[dict[str, Any]]:
        return self.elevenlabs.list_voices() if self.elevenlabs else []

    def get(self, voice_id: str) -> dict[str, Any]:
        if voice_id.startswith("elevenlabs:"):
            if not self.elevenlabs:
                raise ElevenLabsError("Configura prima la API key ElevenLabs")
            return self.elevenlabs.get_voice(voice_id.split(":", 1)[1])
        for item in self.list():
            if item["id"] == voice_id:
                return item
        raise FileNotFoundError(voice_id)

    def install_piper(self, voice_id: str) -> dict[str, Any]:
        item = PIPER_VOICES.get(voice_id)
        if not item:
            raise FileNotFoundError(voice_id)
        try:
            import piper  # noqa: F401
        except ImportError as error:
            raise VoiceError("Installa prima piper-tts sul dispositivo") from error
        self.piper_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [sys.executable, "-m", "piper.download_voices", item["model"], "--data-dir", str(self.piper_dir)],
                check=True,
                timeout=600,
                shell=False,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise VoiceError("Non sono riuscito a installare la voce Piper") from error
        return self.get(voice_id)

    def synthesizer(self, voice_id: str):
        from .audio import PiperTextToSpeech

        if voice_id.startswith("elevenlabs:"):
            if not self.elevenlabs:
                raise ElevenLabsError("Configura prima la API key ElevenLabs")
            return ElevenLabsTextToSpeech(self.elevenlabs, voice_id.split(":", 1)[1])
        item = PIPER_VOICES.get(voice_id)
        if not item:
            raise FileNotFoundError(voice_id)
        model_path = self.piper_dir / f"{item['model']}.onnx"
        if not model_path.exists():
            raise VoiceError("Questa voce Piper non è ancora installata")
        return PiperTextToSpeech(model_path)
