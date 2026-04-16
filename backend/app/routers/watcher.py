"""폴더 감시 API — 추가/제거/전체중지/상태/로그"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import verify_api_key
from ..watcher import folder_watcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watcher", tags=["watcher"])

# 감시 금지 시스템 경로
BLOCKED_PATHS = frozenset({"", "/", "/etc", "/sys", "/proc", "/dev", "/boot", "/bin", "/sbin", "/usr"})


def _validate_watch_path(path: str) -> str:
    """경로를 정규화하고 시스템 위험 경로를 차단한다."""
    normalized = os.path.normpath(os.path.abspath(path))
    if normalized in BLOCKED_PATHS:
        raise HTTPException(400, f"시스템 경로는 감시할 수 없습니다: {normalized}")
    # 시스템 경로의 하위 경로도 차단 (/etc/xxx 등, 단 /usr/local 등은 허용하지 않음)
    for blocked in BLOCKED_PATHS:
        if blocked and blocked != "/" and normalized.startswith(blocked + "/"):
            raise HTTPException(400, f"시스템 경로는 감시할 수 없습니다: {normalized}")
    return normalized


class WatcherPathRequest(BaseModel):
    path: str
    scan_existing: bool = True


class WatcherRemoveRequest(BaseModel):
    path: str


@router.post("/add", dependencies=[Depends(verify_api_key)])
def add_watch_path(req: WatcherPathRequest):
    normalized = _validate_watch_path(req.path)
    logger.info("폴더 감시 추가 요청: path=%s", normalized)
    try:
        return folder_watcher.add_path(normalized, req.scan_existing)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("폴더 추가 실패: path=%s, error=%s", normalized, e)
        raise HTTPException(500, "폴더 추가 중 오류가 발생했습니다.")


@router.post("/remove", dependencies=[Depends(verify_api_key)])
def remove_watch_path(req: WatcherRemoveRequest):
    logger.info("폴더 감시 제거 요청: path=%s", req.path)
    try:
        return folder_watcher.remove_path(req.path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/stop", dependencies=[Depends(verify_api_key)])
def stop_all():
    logger.info("전체 폴더 감시 중지 요청")
    return folder_watcher.stop_all()


@router.get("/status")
def watcher_status():
    return folder_watcher.status()


@router.get("/logs")
def watcher_logs(limit: int = 50):
    return {"logs": folder_watcher.get_logs(limit)}
