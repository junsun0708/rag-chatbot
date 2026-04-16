"""폴더 감시 — watchdog 기반 자동 문서 인덱싱"""

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
            logger.info("Deleted from index: %s", filename)

    def _ingest(self, path: str):
        filename = os.path.basename(path)
        time.sleep(0.5)
        try:
            chunks = ingest_document(path, filename)
            if chunks == -1:
                self._watcher._add_log("중복건너뜀", filename, 0)
                logger.info("Skipped duplicate: %s", filename)
                return
            self._watcher._add_log("인덱싱", filename, chunks)
            logger.info("Indexed: %s (%d chunks)", filename, chunks)
        except Exception as e:
            self._watcher._add_log("실패", filename, 0, str(e))
            logger.error("Failed to index %s: %s", filename, e)


class FolderWatcher:
    """폴더 감시 매니저 — 시작/중지, 상태 조회, 로그 관리."""

    def __init__(self):
        self._observer: Observer | None = None
        self._watch_path: str = ""
        self._running = False
        self._scanning = False
        self._scan_thread: threading.Thread | None = None
        self._logs: list[dict] = []
        self._max_logs = 100
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def watch_path(self) -> str:
        return self._watch_path

    def start(self, path: str, scan_existing: bool = True) -> dict:
        """감시 시작. 기존 파일 스캔은 백그라운드에서 비동기 실행."""
        path = os.path.expanduser(path)
        if not os.path.isdir(path):
            raise ValueError(f"디렉토리가 존재하지 않습니다: {path}")

        if self._running:
            self.stop()

        self._watch_path = path
        self._observer = Observer()
        handler = _DocHandler(self)
        self._observer.schedule(handler, path, recursive=True)
        self._observer.start()
        self._running = True

        self._add_log("시작", path, 0)
        logger.info("Watcher started: %s", path)

        # 기존 파일 스캔을 백그라운드 스레드에서 실행 (API 블로킹 방지)
        if scan_existing:
            self._scanning = True
            self._scan_thread = threading.Thread(
                target=self._scan_existing_bg, args=(path,), daemon=True
            )
            self._scan_thread.start()

        return {
            "status": "started",
            "path": path,
        }

    def stop(self) -> dict:
        """감시 중지."""
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._running = False
            self._scanning = False
            self._add_log("중지", self._watch_path, 0)
            logger.info("Watcher stopped")
        return {"status": "stopped"}

    def status(self) -> dict:
        return {
            "running": self._running,
            "scanning": self._scanning,
            "path": self._watch_path,
            "recent_logs": self._logs[-20:],
        }

    def get_logs(self, limit: int = 50) -> list[dict]:
        return self._logs[-limit:]

    def _scan_existing_bg(self, path: str):
        """백그라운드에서 기존 파일 스캔."""
        count = 0
        try:
            for root, _, files in os.walk(path):
                if not self._running:
                    break
                for fname in files:
                    if not self._running:
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
                        logger.error("Scan failed: %s — %s", fname, e)
        finally:
            self._scanning = False
            if self._running:
                self._add_log("스캔완료", f"{count}개 파일 처리", 0)
            logger.info("Background scan done: %d files", count)

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


# 싱글턴 인스턴스
folder_watcher = FolderWatcher()
