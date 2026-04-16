import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RAGError(Exception):
    """Base exception for RAG operations."""
    pass


class DocumentError(RAGError):
    """Exception raised during document processing."""
    pass


class LLMError(RAGError):
    """Exception raised during LLM calls."""
    pass


async def rag_error_handler(request: Request, exc: RAGError) -> JSONResponse:
    """Global exception handler for RAGError and its subclasses."""
    logger.error("RAGError occurred: %s (path=%s)", exc, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_type": type(exc).__name__},
    )
