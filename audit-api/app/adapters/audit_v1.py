"""Adapter from pixie-contracts audit/v1 payloads to internal event models."""

from app.schemas import ContractEventIn, EventIn, MessageIn


def adapt_contract_event(event: ContractEventIn) -> EventIn:
    event_metadata = (
        event.metadata.model_dump() if event.metadata is not None else {}
    )
    messages = [
        MessageIn(
            role=message.role,
            content=message.content,
            metadata=dict(event_metadata),
        )
        for message in event.messages
    ]
    return EventIn(
        conversation_id=event.conversation_id,
        profile=event.profile,
        messages=messages,
        metadata=event_metadata,
    )

