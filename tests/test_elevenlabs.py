from __future__ import annotations

import json
import wave

from wisp.elevenlabs import ElevenLabsClient


class Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_elevenlabs_lists_voices_without_exposing_key(monkeypatch):
    seen = {}

    def open_request(request, timeout):
        seen["url"] = request.full_url
        seen["key"] = request.headers["Xi-api-key"]
        seen["timeout"] = timeout
        payload = json.dumps({"voices": [{"voice_id": "abc", "name": "Casa"}]}).encode()
        return Response(payload)

    monkeypatch.setattr("wisp.elevenlabs.urllib.request.urlopen", open_request)
    voices = ElevenLabsClient("secret-test-key", timeout=3).list_voices()
    assert voices[0]["id"] == "elevenlabs:abc"
    assert seen == {
        "url": "https://api.elevenlabs.io/v2/voices?page_size=100&voice_type=non-community",
        "key": "secret-test-key",
        "timeout": 3,
    }


def test_elevenlabs_pcm_is_wrapped_as_wav(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "wisp.elevenlabs.urllib.request.urlopen",
        lambda _request, timeout: Response(b"\x00\x00\x01\x00"),
    )
    output = tmp_path / "voice.wav"
    ElevenLabsClient("secret-test-key").synthesize("voice-id", "Ciao", output)
    with wave.open(str(output), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 22_050
        assert audio.readframes(2) == b"\x00\x00\x01\x00"
