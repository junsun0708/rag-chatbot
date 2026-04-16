import logging
import os
import shutil
import subprocess

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS, CHROMA_DIR, RATE_LIMIT_PER_MINUTE, setup_logging
from .exceptions import RAGError, rag_error_handler
from .middleware import InMemoryRateLimiter, RequestIDMiddleware, RequestLoggingMiddleware
from .routers import chat, documents, integrations, watcher

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Chatbot API")

# -- Exception handlers -------------------------------------------------------
app.add_exception_handler(RAGError, rag_error_handler)

# -- Middleware (order matters: first added = outermost) -----------------------
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(InMemoryRateLimiter, max_requests=RATE_LIMIT_PER_MINUTE, window_seconds=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)

# -- Routers -------------------------------------------------------------------
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(integrations.router)
app.include_router(watcher.router)


def _check_chroma() -> bool:
    """Return True if ChromaDB data directory exists and is accessible."""
    return os.path.isdir(CHROMA_DIR)


def _check_disk(path: str = "/", min_gb: float = 1.0) -> dict:
    """Return disk usage info for the given path."""
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    return {"free_gb": round(free_gb, 2), "ok": free_gb >= min_gb}


def _check_claude_cli() -> bool:
    """Return True if the Claude CLI is available on PATH."""
    try:
        subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@app.get("/api/health")
def health():
    chroma_ok = _check_chroma()
    disk = _check_disk()
    claude_ok = _check_claude_cli()

    status = "ok" if (chroma_ok and disk["ok"]) else "degraded"
    return {
        "status": status,
        "checks": {
            "chromadb": chroma_ok,
            "disk": disk,
            "claude_cli": claude_ok,
        },
    }


@app.get("/api/readiness")
def readiness():
    """Lightweight readiness probe for orchestrators / load balancers."""
    if not _check_chroma():
        return {"ready": False, "reason": "ChromaDB directory not found"}
    return {"ready": True}
