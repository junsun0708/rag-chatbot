# RAG Chatbot

PDF 문서를 업로드하면 내용을 기반으로 AI가 질의응답하는 챗봇.

## 아키텍처

```
PDF 업로드 → 청킹(1000자) → OpenAI 임베딩 → ChromaDB 저장
                                                    ↓
사용자 질문 → 유사 문서 검색(top 4) → LLM(GPT-4o-mini) → 답변 생성
```

## 기술 스택

- **Backend**: FastAPI, LangChain, ChromaDB, OpenAI API
- **Frontend**: React, Vite, Tailwind CSS
- **임베딩**: OpenAI text-embedding-ada-002
- **벡터DB**: ChromaDB (로컬 파일 기반)
- **LLM**: GPT-4o-mini

## 실행

### 1. 환경변수

```bash
cp .env.example .env
# .env에 OPENAI_API_KEY 입력
```

### 2. 백엔드

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. 프론트엔드

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
