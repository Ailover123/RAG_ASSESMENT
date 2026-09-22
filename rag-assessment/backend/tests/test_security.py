from pathlib import Path
import sys
import types

sys.modules.setdefault("chromadb", types.SimpleNamespace(PersistentClient=object))
sys.modules.setdefault("sentence_transformers", types.SimpleNamespace(SentenceTransformer=object))
sys.modules.setdefault("groq", types.SimpleNamespace(Groq=object))
from types import SimpleNamespace
from unittest.mock import Mock
import zipfile

import pytest
from fastapi import HTTPException

from app.routers.upload import validate_signature
from app.security import sanitize_filename
from app.vectorstore.chroma_client import VectorStore


def test_sanitize_filename_removes_traversal_and_unsafe_characters():
    assert sanitize_filename("../../quarterly report<script>.PDF") == "quarterly report_script_.pdf"
    assert sanitize_filename(r"..\\..\\deck.pptx") == "deck.pptx"


def test_invalid_filename_is_rejected():
    with pytest.raises(HTTPException) as error:
        sanitize_filename("../..")
    assert error.value.status_code == 400


def test_pdf_signature_must_match_extension(tmp_path: Path):
    valid = tmp_path / "valid.pdf"
    valid.write_bytes(b"%PDF-1.7\n")
    validate_signature(valid, ".pdf")

    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"not a pdf")
    with pytest.raises(HTTPException) as error:
        validate_signature(fake, ".pdf")
    assert error.value.detail == "File content does not match its extension."


def test_office_signature_requires_expected_package(tmp_path: Path):
    fake = tmp_path / "fake.docx"
    with zipfile.ZipFile(fake, "w") as archive:
        archive.writestr("[Content_Types].xml", "types")
        archive.writestr("ppt/presentation.xml", "wrong app")
    with pytest.raises(HTTPException):
        validate_signature(fake, ".docx")


def make_store(collection):
    store = VectorStore.__new__(VectorStore)
    store.collection = collection
    return store


def test_query_is_scoped_to_session():
    collection = Mock()
    collection.get.return_value = {"ids": ["1"]}
    collection.query.return_value = {
        "documents": [["private chunk"]],
        "metadatas": [[{"source": "a.pdf", "session_id": "session_a_123456"}]],
        "distances": [[0.1]],
    }
    store = make_store(collection)
    results = store.query([0.1], top_k=4, session_id="session_a_123456")
    assert results[0]["text"] == "private chunk"
    collection.get.assert_called_once_with(where={"session_id": "session_a_123456"}, include=[])
    collection.query.assert_called_once_with(
        query_embeddings=[[0.1]],
        n_results=1,
        where={"session_id": "session_a_123456"},
        include=["documents", "metadatas", "distances"],
    )


def test_document_list_is_scoped_to_session():
    collection = Mock()
    collection.get.return_value = {"metadatas": [{"source": "a.pdf"}, {"source": "a.pdf"}]}
    store = make_store(collection)
    assert store.list_documents("session_a_123456") == ["a.pdf"]
    collection.get.assert_called_once_with(
        where={"session_id": "session_a_123456"}, include=["metadatas"]
    )
