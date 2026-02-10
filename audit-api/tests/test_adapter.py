from __future__ import annotations

from app.adapters.audit_v1 import adapt_contract_event
from app.schemas import ContractEventIn


def test_adapter_maps_contract_payload_to_internal_event() -> None:
    payload = ContractEventIn.model_validate(
        {
            "conversation_id": "session-123",
            "profile": "pixie-questioner",
            "messages": [
                {"role": "user", "content": "Ik zoek een jeans."},
                {"role": "assistant", "content": "Welke fit zoek je?"},
            ],
            "metadata": {"location": "Antwerpen"},
        }
    )

    adapted = adapt_contract_event(payload)

    assert adapted.conversation_id == "session-123"
    assert adapted.profile == "pixie-questioner"
    assert adapted.metadata == {"location": "Antwerpen"}
    assert [msg.role for msg in adapted.messages] == ["user", "assistant"]
    assert all(msg.metadata == {"location": "Antwerpen"} for msg in adapted.messages)


def test_adapter_uses_empty_metadata_when_absent() -> None:
    payload = ContractEventIn.model_validate(
        {
            "conversation_id": "session-123",
            "profile": "pixie-questioner",
            "messages": [{"role": "user", "content": "Hallo"}],
        }
    )

    adapted = adapt_contract_event(payload)

    assert adapted.metadata == {}
    assert adapted.messages[0].metadata == {}
