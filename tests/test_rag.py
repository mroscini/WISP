from __future__ import annotations

import numpy as np

from wisp.rag.engine import HybridRetriever, lexical_score
from wisp.rag.index import IndexBuilder, IndexStore, chunk_text
from wisp.storage import DocumentStore


class FakeEmbedder:
    def embed(self, text):
        lowered = text.lower()
        vector = np.array(["ragno" in lowered, "luna" in lowered, 1.0], dtype=np.float32)
        return vector / np.linalg.norm(vector)


class FakeReranker:
    def score(self, query, passage):
        return lexical_score(query, passage)


def test_chunking_preserves_content_without_oversized_chunks():
    text = "Prima frase molto breve. " * 20
    chunks = chunk_text(text, max_chars=80)
    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_index_and_retrieve_by_character(tmp_path):
    documents = DocumentStore(tmp_path)
    documents.create("Ragni", "Il ragno costruisce una ragnatela.", ["spider-man"])
    documents.create("Luna", "La luna illumina la notte.", ["moon"])
    index = IndexStore(tmp_path)
    result = IndexBuilder(documents, index, FakeEmbedder()).rebuild()
    assert result == {"documents": 2, "chunks": 2}
    retriever = HybridRetriever(index, FakeEmbedder(), FakeReranker())
    passages = retriever.retrieve("Come funziona la ragnatela?", "spider-man")
    assert passages[0].source_id
    assert "ragno" in passages[0].text.lower()
    assert all("luna" not in item.text.lower() for item in passages)

