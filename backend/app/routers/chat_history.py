"""
Chat History router — list, view, and delete a user's past chat sessions.

GET    /api/chat-history               → paginated list with preview + metadata
GET    /api/chat-history/{session_id}  → full message transcript
DELETE /api/chat-history/{session_id}  → delete session (cascades to messages)
"""
from __future__ import annotations

import uuid
from typing import Annotated, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.message import ChatSession, Message
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["chat-history"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatHistoryItem(BaseModel):
    id:         str
    session_id: str
    title:      str
    intent:     Optional[str]
    category:   Optional[str]
    created_at: str
    updated_at: str
    preview:    Optional[str]


class ChatHistoryMessage(BaseModel):
    role:       str
    content:    str
    created_at: str


class ChatSessionDetail(BaseModel):
    session_id: str
    title:      str
    messages:   List[ChatHistoryMessage]


class PaginatedHistory(BaseModel):
    items:    List[ChatHistoryItem]
    page:     int
    limit:    int
    total:    int
    has_more: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_user_id(email: str, db: AsyncSession) -> uuid.UUID:
    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ব্যবহারকারী পাওয়া যায়নি।")
    return user.id


async def _get_owned_session(
    session_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> ChatSession:
    result  = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="কথোপকথন পাওয়া যায়নি।")
    return session


# ─── GET /api/chat-history ────────────────────────────────────────────────────

@router.get("/chat-history", response_model=PaginatedHistory)
async def list_chat_history(
    page:         int = Query(1, ge=1),
    limit:        int = Query(20, ge=1, le=100),
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    db:           Annotated[AsyncSession, Depends(get_db)] = ...,
) -> PaginatedHistory:
    """Paginated list of the caller's chat sessions, newest first."""
    user_id = await _get_user_id(current_user.email, db)
    offset  = (page - 1) * limit

    # Subquery: max message created_at per session → used as updated_at
    max_msg_subq = (
        select(
            Message.session_id,
            func.max(Message.created_at).label("updated_at"),
        )
        .group_by(Message.session_id)
        .subquery("max_msg")
    )

    effective_updated = func.coalesce(
        max_msg_subq.c.updated_at, ChatSession.created_at
    )

    # Total count
    count_result = await db.execute(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == user_id)
    )
    total = count_result.scalar_one() or 0

    # Paginated sessions
    rows_result = await db.execute(
        select(
            ChatSession,
            effective_updated.label("updated_at"),
        )
        .outerjoin(max_msg_subq, max_msg_subq.c.session_id == ChatSession.id)
        .where(ChatSession.user_id == user_id)
        .order_by(effective_updated.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = rows_result.fetchall()

    session_ids = [row.ChatSession.id for row in rows]

    # Batch-fetch first assistant message per session (for preview + intent)
    asst_by_session: Dict[uuid.UUID, Message] = {}
    if session_ids:
        first_asst_subq = (
            select(
                Message.session_id,
                func.min(Message.created_at).label("min_at"),
            )
            .where(
                Message.session_id.in_(session_ids),
                Message.role == "assistant",
            )
            .group_by(Message.session_id)
            .subquery("first_asst")
        )

        asst_result = await db.execute(
            select(Message)
            .join(
                first_asst_subq,
                (Message.session_id == first_asst_subq.c.session_id)
                & (Message.created_at == first_asst_subq.c.min_at),
            )
            .where(Message.role == "assistant")
        )
        asst_by_session = {m.session_id: m for m in asst_result.scalars().all()}

    items: List[ChatHistoryItem] = []
    for row in rows:
        s    = row.ChatSession
        asst = asst_by_session.get(s.id)
        items.append(
            ChatHistoryItem(
                id         = str(s.id),
                session_id = str(s.id),
                title      = (s.title or "অশিরোনাম কথোপকথন")[:50],
                intent     = asst.intent   if asst else None,
                category   = asst.category if asst else None,
                created_at = s.created_at.isoformat(),
                updated_at = row.updated_at.isoformat() if row.updated_at else s.created_at.isoformat(),
                preview    = asst.content[:100] if asst else None,
            )
        )

    logger.info("chat_history_listed", email=current_user.email, page=page, total=total)
    return PaginatedHistory(
        items    = items,
        page     = page,
        limit    = limit,
        total    = total,
        has_more = (offset + limit) < total,
    )


# ─── GET /api/chat-history/{session_id} ───────────────────────────────────────

@router.get("/chat-history/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id:   uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    db:           Annotated[AsyncSession, Depends(get_db)] = ...,
) -> ChatSessionDetail:
    """Return the full message transcript for one session."""
    user_id = await _get_user_id(current_user.email, db)
    session = await _get_owned_session(session_id, user_id, db)

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(200)
    )
    messages = msg_result.scalars().all()

    logger.info("chat_session_fetched", session_id=str(session_id), email=current_user.email)
    return ChatSessionDetail(
        session_id = str(session.id),
        title      = session.title or "অশিরোনাম কথোপকথন",
        messages   = [
            ChatHistoryMessage(
                role       = m.role,
                content    = m.content,
                created_at = m.created_at.isoformat(),
            )
            for m in messages
        ],
    )


# ─── DELETE /api/chat-history/{session_id} ────────────────────────────────────

@router.delete("/chat-history/{session_id}")
async def delete_chat_session(
    session_id:   uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    db:           Annotated[AsyncSession, Depends(get_db)] = ...,
) -> Response:
    """Delete a session and all its messages (CASCADE)."""
    user_id = await _get_user_id(current_user.email, db)
    session = await _get_owned_session(session_id, user_id, db)
    await db.delete(session)
    logger.info("chat_session_deleted", session_id=str(session_id), email=current_user.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
