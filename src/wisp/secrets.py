from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class SecretStore:
    """Small local secret store. Values are never exposed by the configuration API."""

    def __init__(self, data_dir: str | Path):
        self.path = Path(data_dir).resolve() / ".secrets.json"

    def load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("Il file locale dei segreti non è leggibile") from error
        return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}

    def get(self, name: str) -> str | None:
        value = self.load().get(name, "").strip()
        return value or None

    def set(self, name: str, value: str) -> None:
        secrets = self.load()
        secrets[name] = value
        self._save(secrets)

    def delete(self, name: str) -> None:
        secrets = self.load()
        secrets.pop(name, None)
        self._save(secrets)

    def _save(self, secrets: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".secrets-", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(secrets, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

