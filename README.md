# RAG Chatbot

PDF 문서를 업로드하면 내용을 기반으로 AI가 질의응답하는 챗봇.

## 아키텍처

```
PDF 업로드 → 청킹(1000자) → HuggingFace 임베딩 → ChromaDB 저장
                                                    ↓
사용자 질문 → 유사 문서 검색(top 4) → Claude CLI(구독) → 답변 생성
```

## 기술 스택

- **Backend**: FastAPI, LangChain, ChromaDB
- **Frontend**: React, Vite, Tailwind CSS
- **임베딩**: HuggingFace all-MiniLM-L6-v2 (로컬, 무료)
- **벡터DB**: ChromaDB (로컬 파일 기반)
- **LLM**: Claude CLI (로그인된 구독 사용, API 키 불필요)

## 사전 조건

- `claude` CLI가 설치되어 있고 로그인된 상태여야 합니다.

## 실행

### 1. 백엔드

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:5173 접속

## 사용법

1. 좌측 사이드바에서 **PDF 업로드**
2. 하단 입력창에 질문 입력
3. AI가 문서 내용을 기반으로 답변 (출처 표시)
