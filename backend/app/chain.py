"""RAG 체인 — 검색 + LLM 답변 생성"""

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from .config import OPENAI_API_KEY
from .vectorstore import search

_llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 업로드된 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
아래 문서 내용을 참고하여 정확하게 답변하세요.
문서에 없는 내용은 "해당 내용은 업로드된 문서에서 찾을 수 없습니다."라고 답하세요.

참고 문서:
{context}"""),
    ("human", "{question}"),
])


def ask(question: str) -> dict:
    """질문 → 유사 문서 검색 → LLM 답변 생성."""
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

    chain = _PROMPT | _llm
    result = chain.invoke({"context": context, "question": question})

    sources = list(set(doc.metadata.get("source", "") for doc in docs))

    return {
        "answer": result.content,
        "sources": sources,
    }
