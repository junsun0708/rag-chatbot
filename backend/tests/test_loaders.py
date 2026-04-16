"""Tests for document loaders."""

from unittest.mock import patch, MagicMock

from app.loaders import (
    load_text,
    load_csv,
    load_html,
    load_pdf,
    load_document,
    LOADER_MAP,
    SUPPORTED_EXTENSIONS,
)


class TestLoadText:
    def test_returns_documents(self, sample_txt_file):
        docs = load_text(sample_txt_file)
        assert len(docs) == 1
        assert "sample text document" in docs[0].page_content

    def test_metadata_has_page(self, sample_txt_file):
        docs = load_text(sample_txt_file)
        assert docs[0].metadata["page"] == 0


class TestLoadCsv:
    def test_returns_documents(self, sample_csv_file):
        docs = load_csv(sample_csv_file)
        assert len(docs) == 1
        assert "Alice" in docs[0].page_content
        assert "Bob" in docs[0].page_content

    def test_tab_separated_output(self, sample_csv_file):
        docs = load_csv(sample_csv_file)
        assert "\t" in docs[0].page_content


class TestLoadHtml:
    def test_returns_documents(self, sample_html_file):
        docs = load_html(sample_html_file)
        assert len(docs) == 1
        assert "Title" in docs[0].page_content
        assert "Hello world paragraph" in docs[0].page_content

    def test_strips_html_tags(self, sample_html_file):
        docs = load_html(sample_html_file)
        assert "<html>" not in docs[0].page_content
        assert "<p>" not in docs[0].page_content


class TestLoadPdf:
    @patch("app.loaders.PyPDFLoader")
    def test_calls_pypdf_loader(self, mock_loader_cls):
        from langchain_core.documents import Document

        mock_instance = MagicMock()
        mock_instance.load.return_value = [
            Document(page_content="PDF content", metadata={"page": 0})
        ]
        mock_loader_cls.return_value = mock_instance

        docs = load_pdf("/fake/path.pdf")
        mock_loader_cls.assert_called_once_with("/fake/path.pdf")
        assert len(docs) == 1
        assert docs[0].page_content == "PDF content"


class TestLoadDocument:
    def test_txt_extension(self, sample_txt_file):
        docs = load_document(sample_txt_file)
        assert len(docs) >= 1

    def test_csv_extension(self, sample_csv_file):
        docs = load_document(sample_csv_file)
        assert len(docs) >= 1

    def test_html_extension(self, sample_html_file):
        docs = load_document(sample_html_file)
        assert len(docs) >= 1

    def test_md_extension(self, sample_md_file):
        docs = load_document(sample_md_file)
        assert len(docs) >= 1

    def test_unsupported_extension(self, tmp_path):
        p = tmp_path / "file.xyz"
        p.write_text("data")
        import pytest

        with pytest.raises(ValueError, match="지원하지 않는"):
            load_document(str(p))

    def test_loader_map_keys_match_supported(self):
        assert set(LOADER_MAP.keys()) == SUPPORTED_EXTENSIONS
