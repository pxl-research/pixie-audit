from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


Role = Literal["user", "assistant", "system", "summary"]


class MessageIn(BaseModel):
    role: Role
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventIn(BaseModel):
    conversation_id: UUID
    profile: str
    messages: List[MessageIn]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    status: str = "ok"


class ConversationOut(BaseModel):
    id: UUID
    profile: str
    started_at: datetime
    ended_at: Optional[datetime]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SummaryOut(BaseModel):
    id: UUID
    conversation_id: UUID
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
