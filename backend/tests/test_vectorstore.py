"""Tests for vectorstore operations using a temporary ChromaDB directory."""

import pytest
from unittest.mock import patch


# We need to patch the embeddings before importing vectorstore functions,
# so we use a module-level fixture approach.


class FakeEmbeddings:
    """Deterministic fake embeddings for testing."""

    def embed_documents(self, texts):
        return [[float(ord(c) % 10) / 10.0 for c in t[:384].ljust(384)] for t in texts]

    def embed_query(self, text):
        return [float(ord(c) % 10) / 10.0 for c in text[:384].ljust(384)]


@pytest.fixture(autouse=True)
def _patch_vectorstore(tmp_chroma_dir, monkeypatch):
    """Patch vectorstore module to use temp dir and fake embeddings."""
    import app.vectorstore as vs

    monkeypatch.setattr(vs, "_embeddings", FakeEmbeddings())
    monkeypatch.setattr("app.config.CHROMA_DIR", tmp_chroma_dir)
    monkeypatch.setattr(vs, "CHROMA_DIR", tmp_chroma_dir)


class TestIngestDocument:
    def test_ingest_txt_file(self, sample_txt_file):
        from app.vectorstore import ingest_document

        count = ingest_document(sample_txt_file, "sample.txt")
        assert count > 0

    def test_ingest_returns_chunk_count(self, sample_csv_file):
        from app.vectorstore import ingest_document

        count = ingest_document(sample_csv_file, "sample.csv")
        assert isinstance(count, int)
        assert count > 0


class TestSearch:
    def test_search_returns_results(self, sample_txt_file):
        from app.vectorstore import ingest_document, search

        ingest_document(sample_txt_file, "sample.txt")
        results = search("sample text", k=2)
        assert len(results) > 0

    def test_search_empty_db(self):
        from app.vectorstore import search

        results = search("nonexistent query", k=2)
        assert len(results) == 0


class TestDeleteSource:
    def test_delete_removes_chunks(self, sample_txt_file):
        from app.vectorstore import ingest_document, delete_source, search

        ingest_document(sample_txt_file, "sample.txt")
        deleted = delete_source("sample.txt")
        assert deleted > 0

        results = search("sample text", k=2)
        matching = [r for r in results if r.metadata.get("source") == "sample.txt"]
        assert len(matching) == 0

    def test_delete_nonexistent_returns_zero(self):
        from app.vectorstore import delete_source

        deleted = delete_source("nonexistent.txt")
        assert deleted == 0


class TestDuplicateDetection:
    def test_duplicate_returns_negative_one(self, sample_txt_file, monkeypatch):
        monkeypatch.setattr("app.config.DEDUP_ENABLED", True)
        import app.vectorstore as vs

        monkeypatch.setattr(vs, "DEDUP_ENABLED", True)

        from app.vectorstore import ingest_document

        count1 = ingest_document(sample_txt_file, "sample.txt")
        assert count1 > 0

        count2 = ingest_document(sample_txt_file, "sample.txt")
        assert count2 == -1
