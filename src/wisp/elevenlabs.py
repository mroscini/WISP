from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Any


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsClient:
    base_url = "https://api.elevenlabs.io"

    def __init__(self, api_key: str, timeout: float = 20):
        self.api_key = api_key.strip()
        self.timeout = timeout
        if not self.api_key:
            raise ElevenLabsError("Inserisci una API key ElevenLabs")

    def _request(self, path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> bytes:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise ElevenLabsError("API key ElevenLabs non valida o senza permessi") from error
            if error.code == 429:
                raise ElevenLabsError("Limite o crediti ElevenLabs esauriti") from error
            raise ElevenLabsError(f"ElevenLabs ha risposto con errore {error.code}") from error
        except urllib.error.URLError as error:
            raise ElevenLabsError("ElevenLabs non è raggiungibile: controlla Internet") from error

    def account(self) -> dict[str, Any]:
        return json.loads(self._request("/v1/user"))

    def list_voices(self) -> list[dict[str, Any]]:
        data = json.loads(self._request("/v2/voices?page_size=100&voice_type=non-community"))
        return [
            {
                "id": f"elevenlabs:{item['voice_id']}",
                "provider_id": item["voice_id"],
                "name": item.get("name") or "Voce ElevenLabs",
                "kind": "elevenlabs",
                "description": item.get("description") or "Voce online dal tuo account ElevenLabs",
                "available": True,
            }
            for item in data.get("voices", [])
            if item.get("voice_id")
        ]

    def get_voice(self, voice_id: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(voice_id, safe="")
        item = json.loads(self._request(f"/v1/voices/{encoded}"))
        return {
            "id": f"elevenlabs:{item['voice_id']}",
            "provider_id": item["voice_id"],
            "name": item.get("name") or "Voce ElevenLabs",
            "kind": "elevenlabs",
            "description": item.get("description") or "Voce online dal tuo account ElevenLabs",
            "available": True,
        }

    def synthesize(self, voice_id: str, text: str, output_path: str | Path) -> None:
        encoded = urllib.parse.quote(voice_id, safe="")
        pcm = self._request(
            f"/v1/text-to-speech/{encoded}?output_format=pcm_22050",
            method="POST",
            body={"text": text, "model_id": "eleven_multilingual_v2"},
        )
        with wave.open(str(output_path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(22_050)
            audio.writeframes(pcm)


class ElevenLabsTextToSpeech:
    name = "elevenlabs"

    def __init__(self, client: ElevenLabsClient, voice_id: str):
        self.client = client
        self.voice_id = voice_id

    def synthesize(self, text: str, output_path: str | Path) -> None:
        self.client.synthesize(self.voice_id, text, output_path)
