from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np

from ..models import RetrievedPassage
from .index import IndexStore


STOPWORDS = {
    "a", "ad", "al", "alla", "allo", "ai", "agli", "alle", "con", "da",
    "dal", "dalla", "dei", "del", "della", "di", "e", "ed", "gli", "ha",
    "hai", "ho", "i", "il", "in", "io", "la", "le", "lo", "mi", "mio",
    "mia", "ne", "nel", "nella", "o", "per", "piu", "se", "si", "sono",
    "su", "te", "ti", "tu", "un", "una", "che", "chi", "come", "cosa",
}


def words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", str(text).lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", normalized)


def lexical_score(query: str, passage: str) -> float:
    query_words = [word for word in words(query) if word not in STOPWORDS]
    if not query_words:
        return 0.0
    passage_words = words(passage)
    passage_set = set(passage_words)
    matched = sum(word in passage_set for word in query_words)
    score = matched / len(query_words)
    if matched == len(query_words):
        score += 1.0
    if " ".join(query_words) in " ".join(passage_words):
        score += 0.5
    return score


class OnnxEmbeddingBackend:
    def __init__(self, model_path: str | Path, tokenizer_path: str | Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_names = {item.name for item in self.session.get_inputs()}

    def embed(self, text: str) -> np.ndarray:
        encoding = self.tokenizer.encode(text)
        input_ids = np.array([encoding.ids[:128]], dtype=np.int64)
        attention_mask = np.array([encoding.attention_mask[:128]], dtype=np.int64)
        feeds: dict[str, Any] = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)
        output = self.session.run(None, feeds)[0]
        mask = attention_mask[..., None].astype(np.float32)
        pooled = np.sum(output * mask, axis=1) / np.clip(mask.sum(axis=1), 1e-9, None)
        pooled /= np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
        return pooled[0].astype(np.float32)


class OnnxReranker:
    def __init__(self, model_path: str | Path, tokenizer_path: str | Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_names = {item.name for item in self.session.get_inputs()}

    def score(self, query: str, passage: str) -> float:
        encoding = self.tokenizer.encode(query, passage)
        ids = np.array([encoding.ids[:256]], dtype=np.int64)
        mask = np.array([encoding.attention_mask[:256]], dtype=np.int64)
        feeds: dict[str, Any] = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.input_names:
            type_ids = getattr(encoding, "type_ids", None)
            feeds["token_type_ids"] = np.array([type_ids[:256]], dtype=np.int64) if type_ids else np.zeros_like(ids)
        return float(np.asarray(self.session.run(None, feeds)[0]).reshape(-1)[0])


class HybridRetriever:
    def __init__(self, index: IndexStore, embedder, reranker=None, top_k: int = 10, lexical_k: int = 10):
        self.index = index
        self.embedder = embedder
        self.reranker = reranker
        self.top_k = top_k
        self.lexical_k = lexical_k

    def retrieve(self, query: str, character_id: str | None = None, limit: int = 3) -> list[RetrievedPassage]:
        data = self.index.load()
        texts = data["texts"]
        embeddings = data["embeddings"]
        if not len(texts) or not embeddings.size:
            return []
        query_embedding = self.embedder.embed(query)
        semantic_scores = embeddings @ query_embedding
        allowed = []
        scopes = data.get("character_ids", np.array([""] * len(texts)))
        for idx, scope in enumerate(scopes):
            members = {item for item in str(scope).split(",") if item}
            if not members or not character_id or character_id in members:
                allowed.append(idx)
        semantic_ids = sorted(allowed, key=lambda idx: float(semantic_scores[idx]), reverse=True)[: self.top_k]
        lexical_ids = sorted(allowed, key=lambda idx: lexical_score(query, str(texts[idx])), reverse=True)[: self.lexical_k]
        candidate_ids = list(dict.fromkeys(semantic_ids + lexical_ids))
        passages = []
        for idx in candidate_ids:
            passage = RetrievedPassage(
                text=str(texts[idx]),
                source_id=str(data["sources"][idx]),
                semantic_score=float(semantic_scores[idx]),
                lexical_score=lexical_score(query, str(texts[idx])),
            )
            if self.reranker:
                passage.rerank_score = self.reranker.score(query, passage.text)
            passages.append(passage)
        passages.sort(
            key=lambda item: item.rerank_score if item.rerank_score is not None else item.semantic_score,
            reverse=True,
        )
        return passages[:limit]

