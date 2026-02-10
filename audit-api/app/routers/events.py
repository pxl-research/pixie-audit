from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request

from app.adapters.audit_v1 import adapt_contract_event
from app.schemas import ContractEventIn, EventOut
from app.settings import AUDIT_API_KEY

router = APIRouter()


def _check_api_key(x_api_key: str | None) -> None:
    if AUDIT_API_KEY and x_api_key != AUDIT_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


@router.post("/events", response_model=EventOut)
async def post_event(
    event: ContractEventIn,
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> EventOut:
    _check_api_key(x_api_key)
    adapted_event = adapt_contract_event(event)

    event_metadata = adapted_event.metadata or {}
    pool = request.app.state.db
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "insert into audit.conversations (id, profile, metadata) "
                "values ($1, $2, $3) on conflict (id) do nothing",
                adapted_event.conversation_id,
                adapted_event.profile,
                adapted_event.metadata or {},
            )

            for msg in adapted_event.messages:
                await conn.execute(
                    "insert into audit.messages (id, conversation_id, role, content, metadata) "
                    "values ($1, $2, $3, $4, $5)",
                    str(uuid4()),
                    adapted_event.conversation_id,
                    msg.role,
                    msg.content,
                    {**event_metadata, **(msg.metadata or {})},
                )

    return EventOut()
