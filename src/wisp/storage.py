from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[a-f0-9-]{36}$")
ALLOWED_EXTENSIONS = {".txt", ".md"}


class DocumentError(ValueError):
    pass


class DocumentStore:
    def __init__(self, data_dir: str | Path, max_upload_bytes: int = 1_048_576):
        self.root = Path(data_dir).resolve() / "content"
        self.max_upload_bytes = max_upload_bytes

    def _path(self, document_id: str) -> Path:
        if not SAFE_ID.fullmatch(document_id):
            raise DocumentError("Invalid document id")
        candidate = (self.root / f"{document_id}.json").resolve()
        if candidate.parent != self.root:
            raise DocumentError("Invalid document path")
        return candidate

    @staticmethod
    def _validate_text(text: str) -> str:
        text = text.replace("\x00", "").strip()
        if not text:
            raise DocumentError("Document text is empty")
        return text

    def list(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        documents = []
        for path in self.root.glob("*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
                item["character_count"] = len(item.get("text", ""))
                item.pop("text", None)
                documents.append(item)
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(documents, key=lambda item: item.get("updated_at", ""), reverse=True)

    def get(self, document_id: str) -> dict[str, Any]:
        path = self._path(document_id)
        if not path.exists():
            raise FileNotFoundError(document_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def create(self, title: str, text: str, character_ids: list[str] | None = None) -> dict[str, Any]:
        return self._save(
            {
                "id": str(uuid.uuid4()),
                "title": title.strip()[:160] or "Untitled",
                "text": self._validate_text(text),
                "character_ids": sorted(set(character_ids or [])),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def import_upload(self, filename: str, payload: bytes, character_ids: list[str] | None = None) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise DocumentError("Only .txt and .md files are supported")
        if len(payload) > self.max_upload_bytes:
            raise DocumentError("Uploaded file is too large")
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentError("Uploaded files must use UTF-8") from exc
        title = Path(filename).stem.replace("_", " ").replace("-", " ")
        return self.create(title, text, character_ids)

    def update(self, document_id: str, values: dict[str, Any]) -> dict[str, Any]:
        document = self.get(document_id)
        if "title" in values:
            document["title"] = str(values["title"]).strip()[:160] or "Untitled"
        if "text" in values:
            document["text"] = self._validate_text(str(values["text"]))
        if "character_ids" in values:
            document["character_ids"] = sorted(set(map(str, values["character_ids"])))
        return self._save(document)

    def delete(self, document_id: str) -> None:
        path = self._path(document_id)
        if not path.exists():
            raise FileNotFoundError(document_id)
        path.unlink()

    def _save(self, document: dict[str, Any]) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        document["updated_at"] = datetime.now(UTC).isoformat()
        path = self._path(document["id"])
        handle, temp_name = tempfile.mkstemp(dir=self.root, prefix=".document.", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return document

    def iter_for_character(self, character_id: str | None = None):
        for metadata in self.list():
            document = self.get(metadata["id"])
            assigned = document.get("character_ids", [])
            if not assigned or character_id is None or character_id in assigned:
                yield document

