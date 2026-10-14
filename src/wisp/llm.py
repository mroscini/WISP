from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any


class LlmError(RuntimeError):
    pass


class LlamaCppClient:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        payload = {
            "model": self.settings.get("model", "qwen"),
            "messages": messages,
            "temperature": float(self.settings.get("temperature", 0.2)),
            "max_tokens": int(self.settings.get("max_tokens", 96)),
            "stream": True,
        }
        request = urllib.request.Request(
            self.settings["url"],
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=float(self.settings.get("timeout_seconds", 120))
            ) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    value = line[5:].strip()
                    if value == "[DONE]":
                        break
                    try:
                        event = json.loads(value)
                    except json.JSONDecodeError:
                        continue
                    choices = event.get("choices", [])
                    if choices:
                        piece = choices[0].get("delta", {}).get("content", "")
                        if piece:
                            yield piece
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LlmError(f"llama.cpp is unavailable: {exc}") from exc

    def complete(self, messages: list[dict[str, str]]) -> str:
        return "".join(self.stream(messages)).strip()

    def health(self) -> bool:
        base_url = self.settings.get("url", "")
        models_url = base_url.split("/v1/", 1)[0] + "/v1/models"
        try:
            with urllib.request.urlopen(models_url, timeout=1.5) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False

