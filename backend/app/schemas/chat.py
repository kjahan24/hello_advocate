import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    query:      str            = Field(..., min_length=1, max_length=1000)
    session_id: Optional[uuid.UUID] = None
    language:   str            = Field('bn', pattern='^(bn|en)$')

    @field_validator("query")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty or whitespace")
        return v


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)


class MessageResponse(BaseModel):
    id:         uuid.UUID
    role:       str
    content:    str
    intent:     Optional[str]
    category:   Optional[str]
    sources:    Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id:            uuid.UUID
    title:         Optional[str]
    created_at:    datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    id:         uuid.UUID
    title:      Optional[str]
    created_at: datetime
    messages:   List[MessageResponse]

    model_config = {"from_attributes": True}
