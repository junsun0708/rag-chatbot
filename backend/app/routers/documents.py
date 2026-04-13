"""문서 업로드/관리 API"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..config import UPLOAD_DIR
from ..vectorstore import ingest_pdf, list_sources

os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다. 허용: {ALLOWED_EXTENSIONS}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"파일 크기��� {MAX_FILE_SIZE // 1024 // 1024}MB를 초과합니다.")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        chunk_count = ingest_pdf(file_path, file.filename)
    except Exception as e:
        os.unlink(file_path)
        raise HTTPException(500, f"문서 처리 실패: {str(e)}")

    return {
        "filename": file.filename,
        "chunks": chunk_count,
        "message": f"{file.filename}에서 {chunk_count}개 청크를 추출하여 저장했습니다.",
    }


@router.get("/sources")
def get_sources():
    return {"sources": list_sources()}
