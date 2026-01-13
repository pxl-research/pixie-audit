from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.schemas import ConversationOut, MessageOut, SummaryOut

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    request: Request,
    profile: str | None = None,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    limit: int = 50,
    offset: int = 0,
) -> list[ConversationOut]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    clauses: list[str] = []
    params: list[object] = []
    if profile:
        params.append(profile)
        clauses.append(f"profile = ${len(params)}")
    if from_ts:
        params.append(from_ts)
        clauses.append(f"started_at >= ${len(params)}")
    if to_ts:
        params.append(to_ts)
        clauses.append(f"started_at <= ${len(params)}")

    sql = "select id, profile, started_at, ended_at, metadata from audit.conversations"
    if clauses:
        sql += " where " + " and ".join(clauses)

    params.append(limit)
    sql += f" order by started_at desc limit ${len(params)}"
    params.append(offset)
    sql += f" offset ${len(params)}"

    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [ConversationOut(**dict(row)) for row in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: UUID, request: Request
) -> list[MessageOut]:
    sql = (
        "select id, conversation_id, role, content, created_at, metadata "
        "from audit.messages where conversation_id = $1 order by created_at asc"
    )
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, conversation_id)
    return [MessageOut(**dict(row)) for row in rows]


@router.get("/conversations/{conversation_id}/summaries", response_model=list[SummaryOut])
async def list_summaries(
    conversation_id: UUID, request: Request
) -> list[SummaryOut]:
    sql = (
        "select id, conversation_id, content, created_at, metadata "
        "from audit.messages where conversation_id = $1 and role = 'summary' "
        "order by created_at asc"
    )
    pool = request.app.state.db
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, conversation_id)
    return [SummaryOut(**dict(row)) for row in rows]
