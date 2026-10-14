from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path


class DisabledSpeechToText:
    name = "disabled"

    def transcribe(self, _path: str | Path) -> str:
        raise RuntimeError("Speech-to-text is not configured")


class AlsaRecorder:
    def __init__(self, device: str = "", sample_rate: int = 16_000, channels: int = 1):
        executable = shutil.which("arecord")
        if not executable:
            raise RuntimeError("arecord is not installed")
        self.executable = executable
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels

    def record(self, output_path: str | Path, seconds: int = 6) -> None:
        command = [
            self.executable, "-q", "-f", "S16_LE", "-r", str(self.sample_rate),
            "-c", str(self.channels), "-d", str(seconds), "-t", "wav",
        ]
        if self.device:
            command.extend(["-D", self.device])
        command.append(str(output_path))
        subprocess.run(command, check=True, timeout=seconds + 10, shell=False)


class AlsaPlayer:
    def __init__(self, device: str = ""):
        executable = shutil.which("aplay")
        if not executable:
            raise RuntimeError("aplay is not installed")
        self.executable = executable
        self.device = device

    def play(self, path: str | Path) -> None:
        command = [self.executable, "-q"]
        if self.device:
            command.extend(["-D", self.device])
        command.append(str(path))
        subprocess.run(command, check=True, timeout=180, shell=False)


class VoskFileSpeechToText:
    """File-based Vosk adapter derived from the device's working experiment."""

    name = "vosk-file"

    def __init__(self, model_path: str | Path):
        from vosk import Model

        self.model = Model(str(model_path))

    def transcribe(self, path: str | Path) -> str:
        import json
        from vosk import KaldiRecognizer

        with wave.open(str(path), "rb") as audio:
            recognizer = KaldiRecognizer(self.model, audio.getframerate())
            while data := audio.readframes(4000):
                recognizer.AcceptWaveform(data)
        return str(json.loads(recognizer.FinalResult()).get("text", "")).strip()


class DisabledTextToSpeech:
    name = "disabled"

    def synthesize(self, _text: str, _output_path: str | Path) -> None:
        raise RuntimeError("Text-to-speech is not configured")


class CommandTextToSpeech:
    """Runs an explicitly configured local TTS command; no cloning is provided."""

    name = "command"

    def __init__(self, executable: str, arguments: list[str]):
        resolved = shutil.which(executable)
        if not resolved:
            raise RuntimeError(f"TTS executable not found: {executable}")
        self.executable = resolved
        self.arguments = arguments

    def synthesize(self, text: str, output_path: str | Path) -> None:
        args = [item.replace("{output}", str(output_path)) for item in self.arguments]
        subprocess.run(
            [self.executable, *args],
            input=text,
            text=True,
            check=True,
            timeout=120,
            shell=False,
        )

