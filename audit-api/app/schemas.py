from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AUDIT_EVENT_CONTRACT_VERSION = "audit-event-v1.0.0"

ContractRole = Literal["user", "assistant", "summary"]
InternalRole = Literal["user", "assistant", "system", "summary"]


class ContractMetadataIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str = Field(..., min_length=1)


class ContractMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ContractRole
    content: str = Field(..., min_length=1)


class ContractEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(..., min_length=1)
    profile: str = Field(..., min_length=1)
    messages: List[ContractMessageIn] = Field(..., min_length=1)
    metadata: Optional[ContractMetadataIn] = None


class MessageIn(BaseModel):
    role: InternalRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventIn(BaseModel):
    conversation_id: str
    profile: str
    messages: List[MessageIn]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


class ConversationOut(BaseModel):
    id: str
    profile: str
    started_at: datetime
    ended_at: Optional[datetime]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SummaryOut(BaseModel):
    id: str
    conversation_id: str
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
