"""폴더 감시 API — 추가/제거/전체중지/상태/로그"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..watcher import folder_watcher

router = APIRouter(prefix="/api/watcher", tags=["watcher"])


class WatcherPathRequest(BaseModel):
    path: str
    scan_existing: bool = True


class WatcherRemoveRequest(BaseModel):
    path: str


@router.post("/add")
def add_watch_path(req: WatcherPathRequest):
    try:
        return folder_watcher.add_path(req.path, req.scan_existing)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"폴더 추가 실패: {str(e)}")


@router.post("/remove")
def remove_watch_path(req: WatcherRemoveRequest):
    try:
        return folder_watcher.remove_path(req.path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/stop")
def stop_all():
    return folder_watcher.stop_all()


@router.get("/status")
def watcher_status():
    return folder_watcher.status()


@router.get("/logs")
def watcher_logs(limit: int = 50):
    return {"logs": folder_watcher.get_logs(limit)}
