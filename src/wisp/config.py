from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from .models import Character


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.example.json"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ConfigError(ValueError):
    pass


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    characters = [Character.from_dict(item) for item in config.get("characters", [])]
    if not characters:
        raise ConfigError("At least one character is required")
    ids = [character.id for character in characters]
    if any(not SLUG_RE.fullmatch(item) for item in ids):
        raise ConfigError("Character ids must be lowercase slugs")
    if len(ids) != len(set(ids)):
        raise ConfigError("Character ids must be unique")
    if any(not character.name or len(character.name) > 80 for character in characters):
        raise ConfigError("Character names must contain 1-80 characters")
    if config.get("active_character_id") not in ids:
        raise ConfigError("active_character_id must reference a character")

    server = config.get("server", {})
    port = int(server.get("port", 8787))
    max_upload = int(server.get("max_upload_bytes", 1_048_576))
    if not 1 <= port <= 65535:
        raise ConfigError("Server port is invalid")
    if not 1_024 <= max_upload <= 10 * 1_048_576:
        raise ConfigError("Upload limit must be between 1 KiB and 10 MiB")

    rag = config.get("rag", {})
    if int(rag.get("top_k", 10)) < 1 or int(rag.get("lexical_k", 10)) < 1:
        raise ConfigError("RAG candidate counts must be positive")

    button = config.get("button", {})
    if button.get("line") is not None and int(button["line"]) < 0:
        raise ConfigError("button.line must be a non-negative GPIO offset")
    if button.get("edge", "falling") not in {"falling", "rising"}:
        raise ConfigError("button.edge must be falling or rising")
    if not 0 <= int(button.get("debounce_ms", 80)) <= 5_000:
        raise ConfigError("button.debounce_ms must be between 0 and 5000")
    return config


class ConfigStore:
    def __init__(self, path: str | Path | None = None):
        env_path = os.environ.get("WISP_CONFIG")
        self.path = Path(path or env_path or PROJECT_ROOT / "data" / "config.json").resolve()

    def defaults(self) -> dict[str, Any]:
        return json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))

    def load(self) -> dict[str, Any]:
        config = self.defaults()
        if self.path.exists():
            override = json.loads(self.path.read_text(encoding="utf-8"))
            config = _deep_merge(config, override)
        return validate_config(config)

    def save(self, config: dict[str, Any]) -> dict[str, Any]:
        validated = validate_config(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(validated, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return validated

    def ensure(self) -> dict[str, Any]:
        config = self.load()
        if not self.path.exists():
            self.save(config)
        return config

