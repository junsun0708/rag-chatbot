"""폴더 감시 — watchdog 기반 자동 문서 인덱싱 (다중 폴더 지원)"""

import os
import time
import logging
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .loaders import SUPPORTED_EXTENSIONS
from .vectorstore import ingest_document, delete_source

logger = logging.getLogger(__name__)


class _DocHandler(FileSystemEventHandler):
    """파일 생성/수정 시 자동 인덱싱, 삭제 시 벡터DB에서 제거."""

    def __init__(self, watcher: "FolderWatcher"):
        self._watcher = watcher
        self._recent: dict[str, float] = {}

    def _should_process(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return False
        now = time.time()
        if now - self._recent.get(path, 0) < 2.0:
            return False
        self._recent[path] = now
        return True

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            self._ingest(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            filename = os.path.basename(event.src_path)
            delete_source(filename)
            self._ingest(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filename = os.path.basename(event.src_path)
            delete_source(filename)
            self._watcher._add_log("삭제", filename, 0)

    def _ingest(self, path: str):
        filename = os.path.basename(path)
        time.sleep(0.5)
        try:
            chunks = ingest_document(path, filename)
            if chunks == -1:
                self._watcher._add_log("중복건너뜀", filename, 0)
                return
            self._watcher._add_log("인덱싱", filename, chunks)
        except Exception as e:
            self._watcher._add_log("실패", filename, 0, str(e))
            logger.error("Failed to index %s: %s", filename, e)


class FolderWatcher:
    """다중 폴더 감시 매니저."""

    def __init__(self):
        self._observer: Observer | None = None
        self._paths: dict[str, object] = {}  # path → watch handle
        self._scanning_paths: set[str] = set()
        self._logs: list[dict] = []
        self._max_logs = 100
        self._lock = threading.Lock()
        self._handler = _DocHandler(self)

    def _ensure_observer(self):
        """Observer가 없으면 생성 및 시작."""
        if self._observer is None:
            self._observer = Observer()
            self._observer.start()

    def add_path(self, path: str, scan_existing: bool = True) -> dict:
        """감시 폴더 추가."""
        path = os.path.realpath(os.path.expanduser(path))
        if not os.path.isdir(path):
            raise ValueError(f"디렉토리가 존재하지 않습니다: {path}")
        if path in self._paths:
            raise ValueError(f"이미 감시 중인 폴더입니다: {path}")

        self._ensure_observer()
        watch = self._observer.schedule(self._handler, path, recursive=True)
        self._paths[path] = watch

        self._add_log("추가", path, 0)
        logger.info("Watch added: %s", path)

        if scan_existing:
            self._scanning_paths.add(path)
            t = threading.Thread(target=self._scan_bg, args=(path,), daemon=True)
            t.start()

        return {"status": "added", "path": path, "total_paths": len(self._paths)}

    def remove_path(self, path: str) -> dict:
        """감시 폴더 제거."""
        path = os.path.realpath(os.path.expanduser(path))
        watch = self._paths.pop(path, None)
        if watch is None:
            raise ValueError(f"감시 중이 아닌 폴더입니다: {path}")

        self._observer.unschedule(watch)
        self._scanning_paths.discard(path)
        self._add_log("제거", path, 0)
        logger.info("Watch removed: %s", path)

        # 감시 폴더가 없으면 observer도 정리
        if not self._paths:
            self._stop_observer()

        return {"status": "removed", "path": path, "total_paths": len(self._paths)}

    def stop_all(self) -> dict:
        """모든 감시 중지."""
        self._paths.clear()
        self._scanning_paths.clear()
        self._stop_observer()
        self._add_log("전체중지", "", 0)
        logger.info("All watches stopped")
        return {"status": "stopped"}

    def _stop_observer(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

    def status(self) -> dict:
        return {
            "running": len(self._paths) > 0,
            "paths": list(self._paths.keys()),
            "scanning": list(self._scanning_paths),
            "recent_logs": self._logs[-20:],
        }

    def get_logs(self, limit: int = 50) -> list[dict]:
        return self._logs[-limit:]

    def _scan_bg(self, path: str):
        """백그라운드에서 기존 파일 스캔."""
        count = 0
        try:
            for root, _, files in os.walk(path):
                if path not in self._paths:
                    break
                for fname in files:
                    if path not in self._paths:
                        break
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in SUPPORTED_EXTENSIONS:
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        chunks = ingest_document(fpath, fname)
                        if chunks == -1:
                            self._add_log("중복건너뜀", fname, 0)
                        else:
                            self._add_log("초기스캔", fname, chunks)
                            count += 1
                    except Exception as e:
                        self._add_log("실패", fname, 0, str(e))
        finally:
            self._scanning_paths.discard(path)
            if path in self._paths:
                self._add_log("스캔완료", f"{path} ({count}개 파일)", 0)

    def _add_log(self, action: str, target: str, chunks: int, error: str = ""):
        with self._lock:
            self._logs.append({
                "time": datetime.now().isoformat(timespec="seconds"),
                "action": action,
                "target": target,
                "chunks": chunks,
                "error": error,
            })
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]


folder_watcher = FolderWatcher()
