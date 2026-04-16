"""외부 서비스 연동 API — Confluence, Notion"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..vectorstore import ingest_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ── Confluence ──────────────────────────────────────────


class ConfluenceRequest(BaseModel):
    url: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    api_token: str = Field(..., min_length=1)
    space_key: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_~-]+$")
    limit: int = Field(default=50, ge=1, le=100)


@router.post("/confluence/sync", dependencies=[Depends(verify_api_key)])
def sync_confluence(req: ConfluenceRequest):
    try:
        from atlassian import Confluence
    except ImportError:
        raise HTTPException(500, "atlassian-python-api 패키지가 설치되지 않았습니다.")

    try:
        confluence = Confluence(url=req.url, username=req.username, password=req.api_token)
        pages = confluence.get_all_pages_from_space(
            req.space_key, start=0, limit=req.limit, expand="body.storage"
        )
    except Exception as e:
        logger.error("Confluence 연결 실패: space_key=%s, error=%s", req.space_key, e)
        raise HTTPException(400, "Confluence 연결에 실패했습니다. URL과 인증 정보를 확인해주세요.")

    total_chunks = 0
    synced_pages = []

    for page in pages:
        title = page.get("title", "Untitled")
        html_body = page.get("body", {}).get("storage", {}).get("value", "")
        if not html_body:
            continue

        # HTML → 텍스트 변환
        try:
            from bs4 import BeautifulSoup
            text = BeautifulSoup(html_body, "html.parser").get_text(separator="\n", strip=True)
        except ImportError:
            # bs4 없으면 HTML 태그 간단 제거
            import re
            text = re.sub(r"<[^>]+>", " ", html_body)
            text = re.sub(r"\s+", " ", text).strip()

        if not text:
            continue

        source = f"[Confluence] {title}"
        chunks = ingest_text(text, source, metadata={"type": "confluence", "space": req.space_key})
        total_chunks += chunks
        synced_pages.append(title)

    logger.info("Confluence 동기화 완료: space=%s, pages=%d, chunks=%d", req.space_key, len(synced_pages), total_chunks)

    return {
        "pages_synced": len(synced_pages),
        "total_chunks": total_chunks,
        "pages": synced_pages,
        "message": f"Confluence '{req.space_key}' 스페이스에서 {len(synced_pages)}개 페이지, {total_chunks}개 청크를 동기화했습니다.",
    }


# ── Notion ──────────────────────────────────────────


class NotionRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    database_id: str = ""
    page_ids: list[str] = []
    limit: int = Field(default=50, ge=1, le=100)


@router.post("/notion/sync", dependencies=[Depends(verify_api_key)])
def sync_notion(req: NotionRequest):
    try:
        from notion_client import Client as NotionClient
    except ImportError:
        raise HTTPException(500, "notion-client 패키지가 설치되지 않았습니다.")

    try:
        notion = NotionClient(auth=req.api_key)
    except Exception as e:
        logger.error("Notion 연결 실패: %s", e)
        raise HTTPException(400, "Notion 연결에 실패했습니다. API 키를 확인해주세요.")

    pages_to_process = []

    # 데이터베이스에서 페이지 가져오기
    if req.database_id:
        try:
            results = notion.databases.query(database_id=req.database_id, page_size=req.limit)
            pages_to_process.extend(results.get("results", []))
        except Exception as e:
            logger.error("Notion 데이터베이스 조회 실패: db_id=%s, error=%s", req.database_id, e)
            raise HTTPException(400, "Notion 데이터베이스 조회에 실패했습니다. 데이터베이스 ID를 확인해주세요.")

    # 개별 페이지 ID로 가져오기
    for page_id in req.page_ids:
        try:
            page = notion.pages.retrieve(page_id=page_id)
            pages_to_process.append(page)
        except Exception as e:
            logger.warning("Notion 페이지 조회 실패: page_id=%s, error=%s", page_id, e)
            continue

    total_chunks = 0
    synced_pages = []

    for page in pages_to_process:
        page_id = page["id"]
        # 페이지 제목 추출
        title = _extract_notion_title(page)

        # 페이지 블록 내용 가져오기
        try:
            blocks = notion.blocks.children.list(block_id=page_id)
            text = _extract_notion_blocks_text(blocks.get("results", []))
        except Exception:
            continue

        if not text:
            continue

        source = f"[Notion] {title}"
        chunks = ingest_text(text, source, metadata={"type": "notion", "page_id": page_id})
        total_chunks += chunks
        synced_pages.append(title)

    logger.info("Notion 동기화 완료: pages=%d, chunks=%d", len(synced_pages), total_chunks)

    return {
        "pages_synced": len(synced_pages),
        "total_chunks": total_chunks,
        "pages": synced_pages,
        "message": f"Notion에서 {len(synced_pages)}개 페이지, {total_chunks}개 청크를 동기화했습니다.",
    }


def _extract_notion_title(page: dict) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_parts) or "Untitled"
    return "Untitled"


def _extract_notion_blocks_text(blocks: list) -> str:
    texts = []
    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})

        # rich_text가 있는 블록 처리
        rich_text = block_data.get("rich_text", [])
        if rich_text:
            line = "".join(rt.get("plain_text", "") for rt in rich_text)
            if line:
                texts.append(line)

        # 테이블 행 등 다른 형태
        cells = block_data.get("cells", [])
        for cell in cells:
            cell_text = "".join(rt.get("plain_text", "") for rt in cell)
            if cell_text:
                texts.append(cell_text)

    return "\n".join(texts)
