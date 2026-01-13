from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request

from app.schemas import EventIn, EventOut
from app.settings import AUDIT_API_KEY

router = APIRouter()


def _check_api_key(x_api_key: str | None) -> None:
    if AUDIT_API_KEY and x_api_key != AUDIT_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


@router.post("/events", response_model=EventOut)
async def post_event(
    event: EventIn,
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> EventOut:
    _check_api_key(x_api_key)
    if not event.messages and not event.summary:
        raise HTTPException(status_code=400, detail="no messages or summary")

    pool = request.app.state.db
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "insert into audit.conversations (id, profile, metadata) "
                "values ($1, $2, $3) on conflict (id) do nothing",
                event.conversation_id,
                event.profile,
                event.metadata or {},
            )

            for msg in event.messages:
                await conn.execute(
                    "insert into audit.messages (id, conversation_id, role, content, metadata) "
                    "values ($1, $2, $3, $4, $5)",
                    str(uuid4()),
                    event.conversation_id,
                    msg.role,
                    msg.content,
                    msg.metadata or event.metadata or {},
                )

            if event.summary:
                await conn.execute(
                    "insert into audit.summaries (id, conversation_id, content, metadata) "
                    "values ($1, $2, $3, $4)",
                    str(uuid4()),
                    event.conversation_id,
                    event.summary,
                    event.metadata or {},
                )

    return EventOut()
