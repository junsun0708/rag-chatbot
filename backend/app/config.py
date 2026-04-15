import os
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")

# ── 벡터 최적화 설정 ──────────────────────────────────────
# 환경변수로 오버라이드 가능

# 청크 크기 (기본 2000자, 기존 1000에서 확대 → 벡터 수 절반 감소)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2000"))
# 청크 오버랩 (문맥 유지, 청크 크기의 ~20%)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "400"))
# 임베딩 모델 (384차원, 로컬 무료)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# 임베딩 양자화 — ONNX 백엔드 사용 시 int8 양자화 적용 (용량·속도 개선)
EMBEDDING_QUANTIZE = os.getenv("EMBEDDING_QUANTIZE", "true").lower() == "true"
# 중복 문서 제거 활성화
DEDUP_ENABLED = os.getenv("DEDUP_ENABLED", "true").lower() == "true"
