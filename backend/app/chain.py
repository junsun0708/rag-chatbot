"""RAG 체인 — 검색 + Claude CLI 답변 생성 (하이브리드)"""

import asyncio
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

from .config import QUERY_TIMEOUT_SECONDS
from .exceptions import LLMError
from .vectorstore import search

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)

_RAG_PROMPT = """당신은 업로드된 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
아래 문서 내용을 우선 참고하여 답변하세요.
문서에 관련 내용이 있으면 문서 기반으로 답변하고, 문서에 없는 내용은 당신의 지식을 활용하여 답변하되
"[참고: 이 내용은 업로드된 문서가 아닌 AI 자체 지식으로 답변한 것입니다]"라고 명시하세요."""

_GENERAL_PROMPT = """당신은 도움이 되는 AI 어시스턴트입니다. 질문에 정확하고 친절하게 답변하세요."""


def _call_claude(prompt: str) -> str:
    """로그인된 Claude CLI를 통해 답변 생성."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.exception("Claude CLI 타임아웃 (%ds)", QUERY_TIMEOUT_SECONDS)
        raise LLMError(f"Claude CLI 응답 시간이 {QUERY_TIMEOUT_SECONDS}초를 초과했습니다.")
    except OSError:
        logger.exception("Claude CLI 실행 실패")
        raise LLMError("Claude CLI를 실행할 수 없습니다.")

    if result.returncode != 0:
        logger.error("Claude CLI 비정상 종료 (code=%d): %s", result.returncode, result.stderr.strip())
        raise LLMError("Claude CLI가 응답을 생성하지 못했습니다.")

    return result.stdout.strip()


def ask(question: str) -> dict:
    """질문 → 유사 문서 검색 → Claude CLI 답변 생성 (하이브리드)."""
    start = time.time()
    docs = search(question, k=4)

    logger.info(
        "질문 수신: '%.100s' | 검색 문서 %d건",
        question, len(docs),
    )

    if not docs:
        prompt = f"""{_GENERAL_PROMPT}

질문: {question}"""
        answer = _call_claude(prompt)
        elapsed = time.time() - start
        logger.info("응답 완료 (일반): %.2f초", elapsed)
        return {
            "answer": answer,
            "sources": [],
        }

    context = "\n\n---\n\n".join([
        f"[{doc.metadata.get('source', '?')} / p.{doc.metadata.get('page', '?')}]\n{doc.page_content}"
        for doc in docs
    ])

    prompt = f"""{_RAG_PROMPT}

참고 문서:
{context}

질문: {question}"""

    answer = _call_claude(prompt)
    sources = list(set(doc.metadata.get("source", "") for doc in docs))

    elapsed = time.time() - start
    logger.info("응답 완료 (RAG): %.2f초 | 소스: %s", elapsed, sources)

    return {
        "answer": answer,
        "sources": sources,
    }


async def ask_async(question: str) -> dict:
    """ask()의 비동기 버전 — ThreadPoolExecutor로 블로킹 호출을 감싼다."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, ask, question)
