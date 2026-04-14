"""RAG 체인 — 검색 + Claude CLI 답변 생성"""

import subprocess
from .vectorstore import search

_SYSTEM_PROMPT = """당신은 업로드된 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
아래 문서 내용을 참고하여 정확하게 답변하세요.
문서에 없는 내용은 "해당 내용은 업로드된 문서에서 찾을 수 없습니다."라고 답하세요."""


def _call_claude(prompt: str) -> str:
    """로그인된 Claude CLI를 통해 답변 생성."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--no-input"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI 오류: {result.stderr.strip()}")
    return result.stdout.strip()


def ask(question: str) -> dict:
    """질문 → 유사 문서 검색 → Claude CLI 답변 생성."""
    docs = search(question, k=4)

    if not docs:
        return {
            "answer": "업로드된 문서가 없습니다. 먼저 PDF를 업로드해주세요.",
            "sources": [],
        }

    context = "\n\n---\n\n".join([
        f"[{doc.metadata.get('source', '?')} / p.{doc.metadata.get('page', '?')}]\n{doc.page_content}"
        for doc in docs
    ])

    prompt = f"""{_SYSTEM_PROMPT}

참고 문서:
{context}

질문: {question}"""

    answer = _call_claude(prompt)
    sources = list(set(doc.metadata.get("source", "") for doc in docs))

    return {
        "answer": answer,
        "sources": sources,
    }
