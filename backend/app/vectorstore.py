"""벡터DB 관리 — ChromaDB + HuggingFace Embedding"""

import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from .config import CHROMA_DIR

os.makedirs(CHROMA_DIR, exist_ok=True)

_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def get_vectorstore() -> Chroma:
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=_embeddings)


def ingest_pdf(file_path: str, filename: str) -> int:
    """PDF를 청킹 → 임베딩 → ChromaDB에 저장. 저장된 청크 수 반환."""
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    for page in pages:
        page.metadata["source"] = filename

    chunks = _splitter.split_documents(pages)

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)

    return len(chunks)


def search(query: str, k: int = 4):
    """유사 문서 검색."""
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search(query, k=k)


def list_sources() -> list[str]:
    """저장된 문서 소스 목록."""
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    results = collection.get(include=["metadatas"])
    sources = set()
    for meta in results["metadatas"]:
        if meta and "source" in meta:
            sources.add(meta["source"])
    return sorted(sources)
