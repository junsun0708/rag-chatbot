"""Tests for the documents API router."""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_upload_dir, tmp_chroma_dir, monkeypatch):
    """Create a test client with patched directories and fake embeddings."""
    import app.vectorstore as vs

    class FakeEmbeddings:
        def embed_documents(self, texts):
            return [[0.1] * 384 for _ in texts]

        def embed_query(self, text):
            return [0.1] * 384

    monkeypatch.setattr(vs, "_embeddings", FakeEmbeddings())
    monkeypatch.setattr(vs, "CHROMA_DIR", tmp_chroma_dir)

    from app.main import app

    return TestClient(app)


class TestUploadDocument:
    def test_upload_txt_file(self, client):
        content = b"Hello, this is a test document with enough content."
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["chunks"] > 0
        assert data["duplicate"] is False

    def test_upload_unsupported_format(self, client):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.xyz", io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_upload_csv_file(self, client):
        content = b"col1,col2\nval1,val2\n"
        response = client.post(
            "/api/documents/upload",
            files={"file": ("data.csv", io.BytesIO(content), "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "data.csv"


class TestGetSources:
    def test_sources_empty(self, client):
        response = client.get("/api/documents/sources")
        assert response.status_code == 200
        assert "sources" in response.json()

    def test_sources_after_upload(self, client):
        client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )
        response = client.get("/api/documents/sources")
        assert response.status_code == 200
        sources = response.json()["sources"]
        assert "test.txt" in sources


class TestSupportedFormats:
    def test_returns_formats(self, client):
        response = client.get("/api/documents/supported-formats")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert len(data["formats"]) > 0


class TestDocumentStats:
    def test_returns_stats(self, client):
        response = client.get("/api/documents/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_chunks" in data


class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
