from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import AUDIT_EVENT_CONTRACT_VERSION, ContractEventIn


def test_audit_event_contract_version_is_pinned() -> None:
    assert AUDIT_EVENT_CONTRACT_VERSION == "audit-event-v1.0.0"


def test_contract_schema_matches_expected_shape() -> None:
    schema = ContractEventIn.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema.get("required", [])) == {
        "conversation_id",
        "profile",
        "messages",
    }
    assert schema["properties"]["conversation_id"]["type"] == "string"
    assert schema["properties"]["conversation_id"]["minLength"] == 1
    assert schema["properties"]["profile"]["type"] == "string"
    assert schema["properties"]["profile"]["minLength"] == 1
    assert schema["properties"]["messages"]["type"] == "array"
    assert schema["properties"]["messages"]["minItems"] == 1

    message_schema = schema["$defs"]["ContractMessageIn"]
    assert message_schema["additionalProperties"] is False
    assert set(message_schema.get("required", [])) == {"role", "content"}
    assert message_schema["properties"]["role"]["enum"] == [
        "user",
        "assistant",
        "summary",
    ]
    assert message_schema["properties"]["content"]["type"] == "string"
    assert message_schema["properties"]["content"]["minLength"] == 1

    metadata_schema = schema["$defs"]["ContractMetadataIn"]
    assert metadata_schema["additionalProperties"] is False
    assert set(metadata_schema.get("required", [])) == {"location"}
    assert metadata_schema["properties"]["location"]["type"] == "string"
    assert metadata_schema["properties"]["location"]["minLength"] == 1


def test_contract_validation_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ContractEventIn.model_validate(
            {
                "conversation_id": "session-123",
                "profile": "pixie-questioner",
                "messages": [{"role": "user", "content": "Hallo"}],
                "extra": True,
            }
        )


def test_contract_validation_rejects_extra_metadata_fields() -> None:
    with pytest.raises(ValidationError):
        ContractEventIn.model_validate(
            {
                "conversation_id": "session-123",
                "profile": "pixie-questioner",
                "messages": [{"role": "user", "content": "Hallo"}],
                "metadata": {"location": "Antwerpen", "unknown": "x"},
            }
        )
