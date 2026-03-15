import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis
from core.db import get_db
from core.redis_client import get_redis
from models.conversation import Conversation
from models.message import Message
from schemas.agent import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationRenameRequest,
    ConversationResponse,
    MessageResponse,
)

router = APIRouter(prefix="/agent", tags=["agent"])


def get_redis_dep() -> aioredis.Redis:
    return get_redis()


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    from agent.planner import run_agent_chat

    conversation_id = req.conversation_id or uuid.uuid4()
    reply, job_ids = await run_agent_chat(
        message=req.message,
        conversation_id=conversation_id,
        db=db,
        redis=redis,
    )
    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply,
        job_ids_referenced=job_ids,
    )


# ─── Conversation CRUD ────────────────────────────────────────────────────────

@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List conversations ordered by most recent first."""
    stmt = select(Conversation).order_by(Conversation.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    convs = result.scalars().all()
    return [ConversationResponse(id=c.id, name=c.name, created_at=c.created_at) for c in convs]


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
async def get_conversation(conv_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a conversation with its full message history."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    msg_responses = [
        MessageResponse(
            id=m.id,
            role=m.role,
            text=m.content.get("text", "") if isinstance(m.content, dict) else str(m.content),
            created_at=m.created_at,
        )
        for m in messages
    ]
    return ConversationDetail(
        id=conv.id,
        name=conv.name,
        created_at=conv.created_at,
        messages=msg_responses,
    )


@router.patch("/conversations/{conv_id}", response_model=ConversationResponse)
async def rename_conversation(
    conv_id: uuid.UUID,
    req: ConversationRenameRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rename a conversation."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.name = req.name[:50]
    await db.commit()
    return ConversationResponse(id=conv.id, name=conv.name, created_at=conv.created_at)


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and all its messages (CASCADE)."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return {"deleted": str(conv_id)}
