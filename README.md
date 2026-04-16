# RAG Chatbot

다양한 문서를 업로드하면 내용을 기반으로 AI가 질의응답하는 사내 문서 검색 챗봇.

## 아키텍처

```
문서 업로드/폴더 감시/외부 연동
        ↓
  인증 검증 (API Key)
        ↓
  MIME 타입 + 확장자 검증
        ↓
  문서 로드 (PDF, Word, Excel, 한/글, TXT, MD, HTML, CSV)
        ↓
  중복 확인 (SHA-256 해시)
        ↓
  청킹 (2000자, 400자 오버랩)
        ↓
  HuggingFace 임베딩 (384차원, 정규화)
        ↓
  ChromaDB 저장 (Lock 기반 동시성 제어)
        ↓
사용자 질문 → 유사 문서 검색 (top 4) → Claude CLI → 답변 생성 (출처 표시)
```

## 기술 스택

- **Backend**: FastAPI, LangChain, ChromaDB
- **Frontend**: React, Vite, Tailwind CSS
- **임베딩**: HuggingFace all-MiniLM-L6-v2 (384차원, 로컬, 무료)
- **벡터DB**: ChromaDB (로컬 파일 기반)
- **LLM**: Claude CLI (로그인된 구독 사용, API 키 불필요)
- **테스트**: pytest (39개 테스트)
- **배포**: Docker + docker-compose + nginx

## 보안

| 항목 | 내용 |
|------|------|
| 인증 | API Key 기반 (`X-API-Key` 헤더, 환경변수 미설정 시 비활성화) |
| Rate Limiting | 인메모리 슬라이딩 윈도우 (기본 60req/min) |
| 파일 검증 | 확장자 + MIME 타입 이중 검증 |
| 경로 보호 | 시스템 경로(`/etc`, `/sys` 등) 감시 차단 |
| 에러 처리 | 커스텀 예외로 스택트레이스 노출 방지 |
| 요청 추적 | X-Request-ID 자동 생성 |
| 로깅 | 구조화 로깅 (RotatingFileHandler, 10MB/5백업) |

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
- 여러 폴더 동시 감시 가능
- 파일 추가/수정/삭제 시 벡터DB에 자동 반영
- 서버 재시작 시 감시 경로 자동 복원

## 사전 조건

- Python 3.10+
- Node.js 18+
- `claude` CLI가 설치되어 있고 로그인된 상태

## 실행

### 방법 1: 직접 실행

```bash
# 백엔드
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:5173 접속

### 방법 2: Docker

```bash
docker-compose up
```

브라우저에서 http://localhost:3000 접속

## 환경변수

```bash
# 인증 (미설정 시 인증 비활성화)
API_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# 벡터 최적화
CHUNK_SIZE=2000
CHUNK_OVERLAP=400
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_QUANTIZE=true
DEDUP_ENABLED=true

# 제한
MAX_FILE_SIZE_MB=50
MAX_QUESTION_LENGTH=2000
QUERY_TIMEOUT_SECONDS=30
RATE_LIMIT_PER_MINUTE=60

# 로깅
LOG_LEVEL=INFO
LOG_DIR=./logs
```

## 테스트

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

39개 테스트: 로더, 벡터스토어, 문서 API, 채팅 API, 폴더 감시 API

## API 엔드포인트

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|:----:|------|
| POST | `/api/documents/upload` | 🔒 | 문서 업로드 |
| GET | `/api/documents/sources` | | 인덱싱된 문서 목록 |
| GET | `/api/documents/stats` | | 벡터DB 통계/최적화 설정 |
| GET | `/api/documents/supported-formats` | | 지원 형식 목록 |
| POST | `/api/chat` | | 질의응답 |
| POST | `/api/integrations/confluence/sync` | 🔒 | Confluence 동기화 |
| POST | `/api/integrations/notion/sync` | 🔒 | Notion 동기화 |
| POST | `/api/watcher/add` | 🔒 | 폴더 감시 추가 |
| POST | `/api/watcher/remove` | 🔒 | 폴더 감시 제거 |
| POST | `/api/watcher/stop` | 🔒 | 전체 감시 중지 |
| GET | `/api/watcher/status` | | 감시 상태/로그 |
| GET | `/api/health` | | 헬스체크 (ChromaDB, 디스크, Claude CLI) |
| GET | `/api/readiness` | | 준비 상태 체크 |

🔒 = API_KEY 설정 시 `X-API-Key` 헤더 필요

## 프로젝트 구조

```
rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 앱 + 미들웨어 + 헬스체크
│   │   ├── config.py            # 설정 + 로깅 초기화
│   │   ├── auth.py              # API Key 인증
│   │   ├── exceptions.py        # 커스텀 예외 (RAGError, DocumentError, LLMError)
│   │   ├── middleware.py        # 요청 ID, 로깅, Rate Limiter
│   │   ├── chain.py             # RAG 체인 (Claude CLI, 비동기 지원)
│   │   ├── vectorstore.py       # ChromaDB + 임베딩 + 동시성 제어
│   │   ├── loaders.py           # 12개 형식 문서 로더
│   │   ├── watcher.py           # 폴더 감시 (watchdog, 상태 영속)
│   │   └── routers/
│   │       ├── documents.py     # 문서 업로드/관리 (MIME 검증)
│   │       ├── chat.py          # 질의응답 (입력 검증)
│   │       ├── integrations.py  # Confluence/Notion 연동
│   │       └── watcher.py       # 폴더 감시 (경로 보호)
│   ├── tests/                   # pytest 39개 테스트
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   └── components/
│   │       ├── FileUpload.jsx
│   │       ├── WatcherPanel.jsx
│   │       ├── IntegrationPanel.jsx
│   │       ├── ChatMessage.jsx
│   │       └── SourceList.jsx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── uploads/
└── .dockerignore
```
