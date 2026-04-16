"""Shared pytest fixtures for RAG chatbot tests."""

import os
import tempfile
import shutil

import pytest


@pytest.fixture()
def tmp_chroma_dir(monkeypatch, tmp_path):
    """Provide a temporary ChromaDB directory and patch config to use it."""
    chroma_dir = str(tmp_path / "chroma")
    os.makedirs(chroma_dir, exist_ok=True)
    monkeypatch.setattr("app.config.CHROMA_DIR", chroma_dir)
    return chroma_dir


@pytest.fixture()
def tmp_upload_dir(monkeypatch, tmp_path):
    """Provide a temporary upload directory and patch config to use it."""
    upload_dir = str(tmp_path / "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    monkeypatch.setattr("app.config.UPLOAD_DIR", upload_dir)
    return upload_dir


@pytest.fixture()
def sample_txt_file(tmp_path):
    """Create a sample .txt file and return its path."""
    p = tmp_path / "sample.txt"
    p.write_text("This is a sample text document for testing purposes.", encoding="utf-8")
    return str(p)


@pytest.fixture()
def sample_csv_file(tmp_path):
    """Create a sample .csv file and return its path."""
    p = tmp_path / "sample.csv"
    p.write_text("name,age,city\nAlice,30,Seoul\nBob,25,Busan\n", encoding="utf-8")
    return str(p)


@pytest.fixture()
def sample_html_file(tmp_path):
    """Create a sample .html file and return its path."""
    p = tmp_path / "sample.html"
    p.write_text(
        "<html><body><h1>Title</h1><p>Hello world paragraph.</p></body></html>",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture()
def sample_md_file(tmp_path):
    """Create a sample .md file and return its path."""
    p = tmp_path / "sample.md"
    p.write_text("# Heading\n\nSome markdown content here.", encoding="utf-8")
    return str(p)
