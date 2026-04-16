"""폴더 감시 — watchdog 기반 자동 문서 인덱싱 (다중 폴더 지원)"""

import json
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

_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "watcher_state.json")


class _DocHandler(FileSystemEventHandler):
    """파일 생성/수정 시 자동 인덱싱, 삭제 시 벡터DB에서 제거."""

    def __init__(self, watcher: "FolderWatcher"):
        self._watcher = watcher
        self._recent: dict[str, float] = {}
        self._processing: set[str] = set()
        self._lock = threading.RLock()

    def _should_process(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return False
        with self._lock:
            now = time.time()
            if now - self._recent.get(path, 0) < 2.0:
                return False
            if path in self._processing:
                return False
            self._recent[path] = now
            self._processing.add(path)
        return True

    def _done_processing(self, path: str):
        with self._lock:
            self._processing.discard(path)

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            try:
                self._ingest(event.src_path)
            finally:
                self._done_processing(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            try:
                filename = os.path.basename(event.src_path)
                delete_source(filename)
                self._ingest(event.src_path)
            finally:
                self._done_processing(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filename = os.path.basename(event.src_path)
            delete_source(filename)
            logger.info("파일 삭제 감지: %s", filename)
            self._watcher._add_log("삭제", filename, 0)

    def _ingest(self, path: str):
        filename = os.path.basename(path)
        time.sleep(0.5)
        try:
            start = time.time()
            chunks = ingest_document(path, filename)
            elapsed = time.time() - start
            if chunks == -1:
                logger.info("중복 건너뜀: %s", filename)
                self._watcher._add_log("중복건너뜀", filename, 0)
                return
            logger.info("자동 인덱싱: %s | %d 청크 | %.2f초", filename, chunks, elapsed)
            self._watcher._add_log("인덱싱", filename, chunks)
        except Exception as e:
            self._watcher._add_log("실패", filename, 0, str(e))
            logger.exception("자동 인덱싱 실패: %s", filename)


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

    # ── 상태 영속성 ──────────────────────────────────────────

    def _save_state(self):
        """현재 감시 경로를 JSON 파일에 저장."""
        try:
            os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
            data = {"paths": list(self._paths.keys())}
            with open(_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("감시 상태 저장: %d개 경로", len(self._paths))
        except Exception:
            logger.exception("감시 상태 저장 실패")

    def _load_state(self):
        """저장된 감시 경로를 복원 (scan_existing=False)."""
        if not os.path.exists(_STATE_FILE):
            return
        try:
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            paths = data.get("paths", [])
            restored = 0
            for p in paths:
                if os.path.isdir(p) and p not in self._paths:
                    try:
                        self.add_path(p, scan_existing=False)
                        restored += 1
                    except Exception:
                        logger.warning("감시 경로 복원 실패: %s", p)
            if restored:
                logger.info("감시 경로 복원: %d개", restored)
        except Exception:
            logger.exception("감시 상태 파일 로드 실패")

    # ── 폴더 관리 ────────────────────────────────────────────

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
        logger.info("감시 폴더 추가: %s", path)
        self._save_state()

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
        logger.info("감시 폴더 제거: %s", path)
        self._save_state()

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
        logger.info("모든 감시 중지")
        self._save_state()
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
        start = time.time()
        logger.info("초기 스캔 시작: %s", path)
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
                        logger.exception("초기 스캔 실패: %s", fname)
        finally:
            self._scanning_paths.discard(path)
            elapsed = time.time() - start
            if path in self._paths:
                logger.info("초기 스캔 완료: %s | %d개 파일 | %.2f초", path, count, elapsed)
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
