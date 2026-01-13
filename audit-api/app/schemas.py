from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventIn(BaseModel):
    conversation_id: UUID
    profile: str
    messages: List[MessageIn] = Field(default_factory=list)
    summary: Optional[str] = None
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
