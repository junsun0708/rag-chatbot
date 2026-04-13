"""질의응답 API"""

from fastapi import APIRouter
from pydantic import BaseModel
from ..chain import ask

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


@router.post("")
def chat(req: ChatRequest):
    if not req.question.strip():
        return {"answer": "질문�� 입력해주세요.", "sources": []}
    return ask(req.question)
