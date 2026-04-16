"""Tests for the watcher API router."""

import os
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


@pytest.fixture()
def watch_dir(tmp_path):
    """Create a temporary directory to watch."""
    d = tmp_path / "watch_target"
    d.mkdir()
    return str(d)


class TestWatcherStatus:
    def test_status_returns_ok(self, client):
        response = client.get("/api/watcher/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "paths" in data


class TestWatcherLogs:
    def test_logs_returns_list(self, client):
        response = client.get("/api/watcher/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)


class TestWatcherAdd:
    @patch("app.watcher.FolderWatcher._scan_bg")
    def test_add_valid_path(self, mock_scan, client, watch_dir):
        response = client.post(
            "/api/watcher/add",
            json={"path": watch_dir, "scan_existing": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "added"

        # Cleanup: stop watcher
        client.post("/api/watcher/stop")

    def test_add_nonexistent_path(self, client):
        response = client.post(
            "/api/watcher/add",
            json={"path": "/nonexistent/path/xyz"},
        )
        assert response.status_code == 400


class TestWatcherRemove:
    def test_remove_not_watched(self, client):
        response = client.post(
            "/api/watcher/remove",
            json={"path": "/some/unwatched/path"},
        )
        assert response.status_code == 400


class TestWatcherStop:
    def test_stop_all(self, client):
        response = client.post("/api/watcher/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
