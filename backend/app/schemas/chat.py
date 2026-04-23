from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.answering import AnswerSource


class ChatCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    role: str
    content: str
    sources: list[AnswerSource] = Field(default_factory=list)
    insufficient_evidence: bool
    retrieval_hits_count: int
    created_at: datetime


class ChatListItem(BaseModel):
    id: int
    project_id: int
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)
