"""벡터DB 관리 — ChromaDB + HuggingFace Embedding"""

import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import CHROMA_DIR
from .loaders import load_document

os.makedirs(CHROMA_DIR, exist_ok=True)

_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def get_vectorstore() -> Chroma:
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=_embeddings)


def ingest_document(file_path: str, filename: str) -> int:
    """문서를 로드 → 청킹 → 임베딩 → ChromaDB에 저장. 저장된 청크 수 반환."""
    pages = load_document(file_path)

    for page in pages:
        page.metadata["source"] = filename

    chunks = _splitter.split_documents(pages)
    if not chunks:
        return 0

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)

    return len(chunks)


# 하위 호환
ingest_pdf = ingest_document


def ingest_text(text: str, source: str, metadata: dict | None = None) -> int:
    """텍스트 직접 입력 → 청킹 → 임베딩 → ChromaDB에 저장. (Confluence/Notion용)"""
    from langchain_core.documents import Document

    doc_metadata = {"source": source, "page": 0}
    if metadata:
        doc_metadata.update(metadata)

    doc = Document(page_content=text, metadata=doc_metadata)
    chunks = _splitter.split_documents([doc])
    if not chunks:
        return 0

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)

    return len(chunks)


def delete_source(source_name: str) -> int:
    """특정 소스의 모든 청크를 벡터DB에서 삭제. 삭제된 수 반환."""
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    results = collection.get(where={"source": source_name}, include=[])
    ids = results.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    return len(ids)


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
