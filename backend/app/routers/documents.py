"""문서 업로드/관리 API"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..config import UPLOAD_DIR
from ..vectorstore import ingest_document, list_sources, get_stats
from ..loaders import SUPPORTED_EXTENSIONS

os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Excel/HWP 대용량 대비)

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


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다. 허용: {supported}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"파일 크기가 {MAX_FILE_SIZE // 1024 // 1024}MB를 초과합니다.")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        chunk_count = ingest_document(file_path, file.filename)
    except Exception as e:
        os.unlink(file_path)
        raise HTTPException(500, f"문서 처리 실패: {str(e)}")

    file_type = EXT_LABELS.get(ext, ext.upper())

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
