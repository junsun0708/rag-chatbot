"""폴더 감시 API — 시작/중지/상태/로그"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..watcher import folder_watcher

router = APIRouter(prefix="/api/watcher", tags=["watcher"])


class WatcherStartRequest(BaseModel):
    path: str
    scan_existing: bool = True


@router.post("/start")
def start_watcher(req: WatcherStartRequest):
    try:
        result = folder_watcher.start(req.path, req.scan_existing)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"감시 시작 실패: {str(e)}")
    return result


@router.post("/stop")
def stop_watcher():
    return folder_watcher.stop()


@router.get("/status")
def watcher_status():
    return folder_watcher.status()


@router.get("/logs")
def watcher_logs(limit: int = 50):
    return {"logs": folder_watcher.get_logs(limit)}
