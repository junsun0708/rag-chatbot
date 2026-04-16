"""Tests for the chat API router with Claude CLI mocked."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_chroma_dir, monkeypatch):
    """Create a test client with patched vectorstore."""
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


class TestChatEndpoint:
    @patch("app.chain.subprocess.run")
    def test_chat_returns_answer(self, mock_run, client):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="This is a test answer from Claude.",
            stderr="",
        )
        response = client.post("/api/chat", json={"question": "What is AI?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "This is a test answer from Claude."

    def test_empty_question(self, client):
        response = client.post("/api/chat", json={"question": "  "})
        # Backend returns 400 for empty/whitespace-only questions
        assert response.status_code == 400

    @patch("app.chain.subprocess.run")
    def test_chat_with_documents(self, mock_run, client, sample_txt_file, tmp_upload_dir):
        """Test chat when documents exist in the vector store."""
        import app.vectorstore as vs

        vs.ingest_document(sample_txt_file, "sample.txt")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Answer based on documents.",
            stderr="",
        )
        response = client.post(
            "/api/chat", json={"question": "sample text document"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data

    @patch("app.chain.subprocess.run")
    def test_chat_claude_cli_error(self, mock_run, client):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="CLI error",
        )
        response = client.post("/api/chat", json={"question": "test"})
        # Backend returns 503 when Claude CLI fails
        assert response.status_code == 503

    def test_missing_question_field(self, client):
        response = client.post("/api/chat", json={})
        assert response.status_code == 422
