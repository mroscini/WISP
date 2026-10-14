from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol

import numpy as np

from ..storage import DocumentStore


class Embedder(Protocol):
    def embed(self, text: str) -> np.ndarray: ...


def chunk_text(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        remaining = paragraph
        while remaining:
            cut = min(max_chars, len(remaining))
            if cut < len(remaining):
                boundary = max(remaining.rfind(". ", 0, cut), remaining.rfind(" ", 0, cut))
                if boundary >= max_chars // 2:
                    cut = boundary + 1
            chunks.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()
    return chunks


class IndexStore:
    def __init__(self, data_dir: str | Path):
        self.path = Path(data_dir).resolve() / "index" / "knowledge_embeddings.npz"

    def load(self) -> dict[str, np.ndarray]:
        if not self.path.exists():
            return {
                "embeddings": np.empty((0, 0), dtype=np.float32),
                "texts": np.array([], dtype=str),
                "sources": np.array([], dtype=str),
                "character_ids": np.array([], dtype=str),
            }
        data = np.load(self.path, allow_pickle=False)
        return {key: data[key] for key in data.files}

    def save(self, embeddings: np.ndarray, texts: list[str], sources: list[str], character_ids: list[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(dir=self.path.parent, prefix=".index.", suffix=".npz")
        os.close(handle)
        try:
            np.savez_compressed(
                temp_name,
                embeddings=np.asarray(embeddings, dtype=np.float32),
                texts=np.asarray(texts, dtype=str),
                sources=np.asarray(sources, dtype=str),
                character_ids=np.asarray(character_ids, dtype=str),
            )
            generated = temp_name if temp_name.endswith(".npz") else f"{temp_name}.npz"
            os.replace(generated, self.path)
        finally:
            for candidate in (temp_name, f"{temp_name}.npz"):
                if os.path.exists(candidate):
                    os.unlink(candidate)


class IndexBuilder:
    def __init__(self, documents: DocumentStore, index: IndexStore, embedder: Embedder, max_chunk_chars: int = 900):
        self.documents = documents
        self.index = index
        self.embedder = embedder
        self.max_chunk_chars = max_chunk_chars

    def rebuild(self) -> dict[str, int]:
        texts: list[str] = []
        sources: list[str] = []
        character_ids: list[str] = []
        vectors: list[np.ndarray] = []
        document_count = 0
        for document in self.documents.iter_for_character():
            document_count += 1
            assigned = document.get("character_ids", [])
            scope = ",".join(assigned)
            for chunk in chunk_text(document["text"], self.max_chunk_chars):
                texts.append(chunk)
                sources.append(document["id"])
                character_ids.append(scope)
                vectors.append(self.embedder.embed(chunk))
        matrix = np.stack(vectors).astype(np.float32) if vectors else np.empty((0, 0), dtype=np.float32)
        self.index.save(matrix, texts, sources, character_ids)
        return {"documents": document_count, "chunks": len(texts)}

