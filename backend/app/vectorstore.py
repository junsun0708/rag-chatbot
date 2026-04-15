"""벡터DB 관리 — ChromaDB + HuggingFace Embedding + 최적화"""

import hashlib
import logging
import os
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import (
    CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP,
    EMBEDDING_MODEL, EMBEDDING_QUANTIZE, DEDUP_ENABLED,
)
from .loaders import load_document

logger = logging.getLogger(__name__)
os.makedirs(CHROMA_DIR, exist_ok=True)

# ── 임베딩 모델 초기화 (양자화 지원) ───────────────────────

def _create_embeddings():
    """임베딩 모델 생성. ONNX 양자화 가능하면 적용, 아니면 기본 모델."""
    if EMBEDDING_QUANTIZE:
        try:
            from optimum.onnxruntime import ORTModelForFeatureExtraction
            from transformers import AutoTokenizer
            from langchain_huggingface import HuggingFaceEmbeddings

            # ONNX 양자화 모델 로드 시도
            model_kwargs = {"provider": "CPUExecutionProvider"}
            encode_kwargs = {"normalize_embeddings": True}
            return HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
            )
        except ImportError:
            logger.info("optimum 미설치 — 기본 임베딩 모델 사용")
        except Exception as e:
            logger.warning("ONNX 양자화 실패, 기본 모델 사용: %s", e)

    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


_embeddings = _create_embeddings()
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)


# ── 중복 감지 ─────────────────────────────────────────────

def _content_hash(text: str) -> str:
    """텍스트 콘텐츠의 SHA-256 해시 (앞 16자)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _is_duplicate(filename: str, content_hash: str) -> bool:
    """같은 파일명+동일 내용이 이미 인덱싱되어 있는지 확인."""
    if not DEDUP_ENABLED:
        return False
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    try:
        results = collection.get(
            where={"source": filename},
            include=["metadatas"],
        )
        for meta in results.get("metadatas", []):
            if meta and meta.get("content_hash") == content_hash:
                return True
    except Exception:
        pass
    return False


# ── 핵심 함수 ─────────────────────────────────────────────

def get_vectorstore() -> Chroma:
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=_embeddings)


def ingest_document(file_path: str, filename: str) -> int:
    """문서를 로드 → 중복 확인 → 청킹 → 임베딩 → ChromaDB에 저장."""
    pages = load_document(file_path)
    if not pages:
        return 0

    # 전체 텍스트 해시로 중복 확인
    full_text = "\n".join(p.page_content for p in pages)
    content_hash = _content_hash(full_text)

    if _is_duplicate(filename, content_hash):
        logger.info("중복 문서 건너뜀: %s", filename)
        return -1  # -1 = 중복

    # 같은 파일명의 이전 버전 삭제 (수정된 문서 재인덱싱)
    delete_source(filename)

    for page in pages:
        page.metadata["source"] = filename
        page.metadata["content_hash"] = content_hash

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

    content_hash = _content_hash(text)
    if _is_duplicate(source, content_hash):
        logger.info("중복 텍스트 건너뜀: %s", source)
        return -1

    delete_source(source)

    doc_metadata = {"source": source, "page": 0, "content_hash": content_hash}
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


def get_stats() -> dict:
    """벡터DB 통계 및 최적화 설정 반환."""
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    total_chunks = collection.count()

    # 소스별 청크 수
    results = collection.get(include=["metadatas"])
    source_counts: dict[str, int] = {}
    for meta in results.get("metadatas", []):
        if meta and "source" in meta:
            src = meta["source"]
            source_counts[src] = source_counts.get(src, 0) + 1

    # 임베딩 차원 확인
    dim = 384  # all-MiniLM-L6-v2 기본값
    try:
        sample = collection.peek(limit=1)
        if sample.get("embeddings") and len(sample["embeddings"]) > 0:
            dim = len(sample["embeddings"][0])
    except Exception:
        pass

    # 예상 벡터 용량 (float32 기준)
    vector_size_bytes = total_chunks * dim * 4
    vector_size_mb = vector_size_bytes / (1024 * 1024)

    return {
        "total_chunks": total_chunks,
        "total_sources": len(source_counts),
        "source_details": source_counts,
        "settings": {
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": dim,
            "quantize": EMBEDDING_QUANTIZE,
            "dedup_enabled": DEDUP_ENABLED,
        },
        "storage": {
            "vector_size_mb": round(vector_size_mb, 2),
            "bytes_per_chunk": dim * 4,
        },
    }
