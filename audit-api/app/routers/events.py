import logging
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request

from app.schemas import EventIn, EventOut
from app.settings import AUDIT_API_KEY

router = APIRouter()
logger = logging.getLogger(__name__)


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
        logger.warning(
            "event rejected: no messages or summary (conversation_id=%s, profile=%s)",
            event.conversation_id,
            event.profile,
        )
        raise HTTPException(status_code=400, detail="no messages or summary")

    event_metadata = event.metadata or {}
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
                merged_metadata = {**event_metadata, **(msg.metadata or {})}
                await conn.execute(
                    "insert into audit.messages (id, conversation_id, role, content, metadata) "
                    "values ($1, $2, $3, $4, $5)",
                    str(uuid4()),
                    event.conversation_id,
                    msg.role,
                    msg.content,
                    merged_metadata,
                )

            if event.summary:
                await conn.execute(
                    "insert into audit.messages (id, conversation_id, role, content, metadata) "
                    "values ($1, $2, $3, $4, $5)",
                    str(uuid4()),
                    event.conversation_id,
                    "summary",
                    event.summary,
                    event_metadata,
                )

    return EventOut()
