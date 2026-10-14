from __future__ import annotations

import pytest

from wisp.storage import DocumentError, DocumentStore


def test_document_crud_and_path_validation(tmp_path):
    store = DocumentStore(tmp_path)
    document = store.create("Una storia", "C'era una volta.", ["spider-man"])
    assert store.get(document["id"])["text"] == "C'era una volta."
    assert store.list()[0]["character_count"] == 16
    updated = store.update(document["id"], {"title": "Nuovo titolo"})
    assert updated["title"] == "Nuovo titolo"
    with pytest.raises(DocumentError):
        store.get("../../etc/passwd")
    store.delete(document["id"])
    assert store.list() == []


def test_upload_rejects_extension_size_and_encoding(tmp_path):
    store = DocumentStore(tmp_path, max_upload_bytes=8)
    with pytest.raises(DocumentError, match="Only"):
        store.import_upload("story.pdf", b"hello")
    with pytest.raises(DocumentError, match="large"):
        store.import_upload("story.txt", b"012345678")
    with pytest.raises(DocumentError, match="UTF-8"):
        store.import_upload("story.txt", b"\xff")

