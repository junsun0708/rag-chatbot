"""질의응답 API"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..chain import ask
from ..config import MAX_QUESTION_LENGTH
from ..exceptions import LLMError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


@router.post("")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(400, "질문을 입력해주세요.")

    if len(req.question) > MAX_QUESTION_LENGTH:
        raise HTTPException(400, f"질문은 {MAX_QUESTION_LENGTH}자 이내로 입력해주세요.")

    try:
        logger.info("채팅 질문 수신: length=%d", len(req.question))
        result = ask(req.question)
        return result
    except LLMError as e:
        logger.error("LLM 처리 오류: %s", e)
        raise HTTPException(503, "AI 응답 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
    except Exception as e:
        logger.error("채팅 처리 중 예기치 않은 오류: %s", e)
        raise HTTPException(500, "요청 처리 중 오류가 발생했습니다.")
