import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    job_ids_referenced: list[str] = []


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str           # "user" | "assistant"
    text: str           # extracted from content["text"]
    created_at: datetime


class ConversationResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    created_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse]


class ConversationRenameRequest(BaseModel):
    name: str
