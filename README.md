# RAG Chatbot

다양한 문서를 업로드하면 내용을 기반으로 AI가 질의응답하는 사내 문서 검색 챗봇.

## 아키텍처

```
문서 업로드/폴더 감시/외부 연동
        ↓
  문서 로드 (PDF, Word, Excel, 한/글, TXT, MD, HTML, CSV)
        ↓
  중복 확인 (SHA-256 해시)
        ↓
  청킹 (2000자, 400자 오버랩)
        ↓
  HuggingFace 임베딩 (384차원, 정규화)
        ↓
  ChromaDB 저장
        ↓
사용자 질문 → 유사 문서 검색 (top 4) → Claude CLI → 답변 생성 (출처 표시)
```

## 기술 스택

- **Backend**: FastAPI, LangChain, ChromaDB
- **Frontend**: React, Vite, Tailwind CSS
- **임베딩**: HuggingFace all-MiniLM-L6-v2 (384차원, 로컬, 무료)
- **벡터DB**: ChromaDB (로컬 파일 기반)
- **LLM**: Claude CLI (로그인된 구독 사용, API 키 불필요)

## 지원 문서 형식

### 파일 업로드
| 형식 | 확장자 |
|------|--------|
| PDF | .pdf |
| Word | .docx, .doc |
| Excel | .xlsx, .xls |
| 한/글 | .hwp, .hwpx |
| 텍스트 | .txt, .md |
| HTML | .html, .htm |
| CSV | .csv |

### 외부 연동
| 서비스 | 연동 방식 |
|--------|----------|
| Confluence | API Token + Space Key로 페이지 동기화 |
| Notion | Integration Token + Database ID로 페이지 동기화 |

### 폴더 감시
지정 폴더를 실시간 감시하여 파일 추가/수정/삭제 시 벡터DB에 자동 반영.

## 사전 조건

- Python 3.10+
- Node.js 18+
- `claude` CLI가 설치되어 있고 로그인된 상태

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

1. 좌측 사이드바에서 **문서 업로드** (12개 형식 지원)
2. 또는 **폴더 감시** 설정으로 자동 인덱싱
3. 또는 **Confluence/Notion** 연동으로 외부 문서 동기화
4. 하단 입력창에 질문 입력
5. AI가 문서 내용을 기반으로 답변 (출처 표시)

## 벡터 최적화

| 항목 | 설정 |
|------|------|
| 청크 크기 | 2000자 (오버랩 400자) |
| 임베딩 차원 | 384차원 (all-MiniLM-L6-v2) |
| 임베딩 정규화 | 활성화 |
| 중복 제거 | SHA-256 해시 기반 자동 감지 |
| 양자화 | ONNX 백엔드 지원 (`optimum` 설치 시 활성화) |

환경변수로 오버라이드 가능:

```bash
CHUNK_SIZE=2000
CHUNK_OVERLAP=400
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_QUANTIZE=true
DEDUP_ENABLED=true
```

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/documents/upload` | 문서 업로드 |
| GET | `/api/documents/sources` | 인덱싱된 문서 목록 |
| GET | `/api/documents/stats` | 벡터DB 통계/최적화 설정 |
| GET | `/api/documents/supported-formats` | 지원 형식 목록 |
| POST | `/api/chat` | 질의응답 |
| POST | `/api/integrations/confluence/sync` | Confluence 동기화 |
| POST | `/api/integrations/notion/sync` | Notion 동기화 |
| POST | `/api/watcher/start` | 폴더 감시 시작 |
| POST | `/api/watcher/stop` | 폴더 감시 중지 |
| GET | `/api/watcher/status` | 감시 상태/로그 |
| GET | `/api/health` | 헬스체크 |

## 프로젝트 구조

```
rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 앱
│   │   ├── config.py            # 설정 (청크, 임베딩, 최적화)
│   │   ├── chain.py             # RAG 체인 (Claude CLI)
│   │   ├── vectorstore.py       # ChromaDB + 임베딩 + 최적화
│   │   ├── loaders.py           # 12개 형식 문서 로더
│   │   ├── watcher.py           # 폴더 감시 (watchdog)
│   │   └── routers/
│   │       ├── documents.py     # 문서 업로드/관리 API
│   │       ├── chat.py          # 질의응답 API
│   │       ├── integrations.py  # Confluence/Notion 연동
│   │       └── watcher.py       # 폴더 감시 API
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   └── components/
│   │       ├── FileUpload.jsx       # 문서 업로드
│   │       ├── WatcherPanel.jsx     # 폴더 감시 설정
│   │       ├── IntegrationPanel.jsx # Confluence/Notion 연동
│   │       ├── ChatMessage.jsx      # 채팅 메시지
│   │       └── SourceList.jsx       # 문서 목록
│   └── package.json
└── uploads/                         # 업로드 파일 저장
```
