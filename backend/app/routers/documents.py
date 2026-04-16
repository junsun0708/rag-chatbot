"""문서 업로드/관리 API"""

import logging
import mimetypes
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from ..auth import verify_api_key
from ..config import UPLOAD_DIR, MAX_FILE_SIZE_MB
from ..exceptions import DocumentError
from ..vectorstore import ingest_document, list_sources, get_stats
from ..loaders import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# 확장자별 한글 이름 (에러 메시지용)
EXT_LABELS = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".doc": "Word",
    ".xlsx": "Excel",
    ".xls": "Excel",
    ".hwp": "한/글(HWP)",
    ".hwpx": "한/글(HWPX)",
    ".txt": "텍스트",
    ".md": "마크다운",
    ".html": "HTML",
    ".htm": "HTML",
    ".csv": "CSV",
}

# 확장자별 허용 MIME 타입
ALLOWED_MIME_TYPES = {
    ".pdf": ["application/pdf"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ".doc": ["application/msword"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".xls": ["application/vnd.ms-excel"],
    ".hwp": ["application/x-hwp", "application/haansofthwp", "application/octet-stream"],
    ".hwpx": ["application/hwp+zip", "application/octet-stream"],
    ".txt": ["text/plain"],
    ".md": ["text/plain", "text/markdown"],
    ".html": ["text/html"],
    ".htm": ["text/html"],
    ".csv": ["text/csv", "text/plain"],
}


@router.post("/upload", dependencies=[Depends(verify_api_key)])
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다. 허용: {supported}")

    # MIME 타입 검증
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    allowed_mimes = ALLOWED_MIME_TYPES.get(ext, [])
    if allowed_mimes and mime_type and mime_type not in allowed_mimes:
        logger.warning("MIME 타입 불일치: filename=%s, ext=%s, mime=%s", file.filename, ext, mime_type)
        raise HTTPException(400, f"파일의 MIME 타입({mime_type})이 확장자({ext})와 일치하지 않습니다.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"파일 크기가 {MAX_FILE_SIZE_MB}MB를 초과합니다.")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        chunk_count = ingest_document(file_path, file.filename)
    except DocumentError:
        os.unlink(file_path)
        raise
    except Exception as e:
        os.unlink(file_path)
        logger.error("문서 처리 실패: filename=%s, error=%s", file.filename, e)
        raise HTTPException(500, "문서 처리 중 오류가 발생했습니다.")

    file_type = EXT_LABELS.get(ext, ext.upper())
    logger.info("문서 업로드 완료: filename=%s, type=%s, chunks=%s", file.filename, file_type, chunk_count)

    if chunk_count == -1:
        return {
            "filename": file.filename,
            "type": file_type,
            "chunks": 0,
            "duplicate": True,
            "message": f"{file.filename}은 이미 동일한 내용으로 인덱싱되어 있어 건너뛰었습니다.",
        }

    return {
        "filename": file.filename,
        "type": file_type,
        "chunks": chunk_count,
        "duplicate": False,
        "message": f"{file.filename} ({file_type})에서 {chunk_count}개 청크를 추출하여 저장했습니다.",
    }


@router.get("/sources")
def get_sources():
    return {"sources": list_sources()}


@router.get("/supported-formats")
def get_supported_formats():
    """지원하는 파일 형식 목록 반환."""
    formats = []
    seen = set()
    for ext, label in sorted(EXT_LABELS.items()):
        if label not in seen:
            seen.add(label)
            exts = [e for e, l in EXT_LABELS.items() if l == label]
            formats.append({"label": label, "extensions": exts})
    return {"formats": formats}


@router.get("/stats")
def get_document_stats():
    """벡터DB 통계 및 최적화 설정 반환."""
    return get_stats()
