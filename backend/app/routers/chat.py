"""
Chat router — SSE streaming endpoint + session CRUD.

Endpoints
---------
POST /api/chat                     → SSE stream (main feature)
POST /api/chat/sessions            → create session
GET  /api/chat/sessions            → list user's sessions (paginated)
GET  /api/chat/sessions/{id}       → session detail + messages

Design note — greenlet safety
------------------------------
FastAPI's StreamingResponse runs the async generator in the same event loop
but SQLAlchemy's asyncpg driver uses Python greenlets internally.  Any
AsyncSession that stays open ACROSS a generator yield point loses its greenlet
context and raises "greenlet_spawn has not been called".

Fix: ALL database work happens BEFORE the generator is defined:
  1. User lookup / auto-create
  2. Rate-limit check
  3. Session lookup / create
  4. History load
  5. User message insert + commit
The generator itself receives only plain Python values (uuid, list, str) and
never touches an AsyncSession directly.  Post-stream persistence (_persist_chat_result)
opens its own fresh connection after all tokens are yielded.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_db_user, get_optional_user
from app.db.database import AsyncSessionLocal, get_db
from app.models.message import ChatSession, Message
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    CreateSessionRequest,
    MessageResponse,
    SessionDetailResponse,
    SessionResponse,
)
from app.services.rag_pipeline import RAGPipeline
import app.services.document_service as doc_svc

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

_MAX_HISTORY_TURNS  = 10   # user+assistant pairs injected as conversation context
_SESSION_PAGE_SIZE  = 20   # default for GET /sessions
_MESSAGE_HARD_LIMIT = 200  # cap messages returned per session

_SSE_HEADERS = {
    "Cache-Control":     "no-cache",
    "Connection":        "keep-alive",
    "X-Accel-Buffering": "no",    # prevent nginx from buffering SSE
}

# ──────────────────────────────────────────────────────────────────────────────
# Pipeline singleton (HTTP clients are expensive to create per-request)
# ──────────────────────────────────────────────────────────────────────────────

_pipeline: Optional[RAGPipeline] = None


def _get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline.create()
    return _pipeline


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _sse(event: Dict[str, Any]) -> str:
    """Serialise one event to the SSE wire format."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _get_or_create_user(caller: CurrentUser, db: AsyncSession) -> User:
    """Load the User row by email, auto-creating it on first login."""
    result = await db.execute(select(User).where(User.email == caller.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=caller.email, name=caller.name)
        db.add(user)
        await db.flush()
        logger.info("user_auto_created", email=caller.email)
    return user


async def _load_history(
    session_id: uuid.UUID, db: AsyncSession
) -> List[Dict[str, str]]:
    """
    Return the last _MAX_HISTORY_TURNS * 2 messages in chronological order,
    formatted as Claude API `messages` dicts.
    """
    result = await db.execute(
        select(Message.role, Message.content)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(_MAX_HISTORY_TURNS * 2)
    )
    return [{"role": r.role, "content": r.content} for r in reversed(result.fetchall())]


async def _persist_chat_result(
    *,
    session_id:    uuid.UUID,
    user_id:       uuid.UUID,
    full_response: str,
    intent_data:   Optional[Dict[str, Any]],
    sources_data:  List[Any],
    is_new_session: bool,
    session_title:  str,
) -> None:
    """
    Save the assistant message and auto-title the session (if new) in one
    fresh connection, then increment the query counter in a second isolated
    connection so a poisoned transaction never silently skips the counter tick.

    Called AFTER all SSE tokens are yielded — the generator has no open session
    at this point, so there is no greenlet conflict.
    """
    async with AsyncSessionLocal() as db:
        try:
            asst_msg = Message(
                session_id = session_id,
                role       = "assistant",
                content    = full_response,
                intent     = intent_data.get("intent")   if intent_data else None,
                category   = intent_data.get("category") if intent_data else None,
                sources    = sources_data or None,
            )
            db.add(asst_msg)

            if is_new_session:
                await db.execute(
                    text(
                        "UPDATE chat_sessions SET title = :title "
                        "WHERE id = :id AND title IS NULL"
                    ),
                    {"title": session_title, "id": session_id},
                )

            await db.commit()
        except Exception as exc:
            logger.warning("persist_assistant_message_failed", error=str(exc))
            await db.rollback()

    async with AsyncSessionLocal() as db:
        try:
            await db.execute(
                text(
                    "UPDATE users "
                    "SET query_count_today = query_count_today + 1 "
                    "WHERE id = :uid"
                ),
                {"uid": str(user_id)},
            )
            await db.commit()
        except Exception as exc:
            logger.warning("query_counter_update_failed", error=str(exc))
            await db.rollback()


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/chat — SSE streaming endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("", summary="Stream a legal chat response (SSE)")
async def chat_stream(
    body:         ChatRequest,
    current_user: CurrentUser = Depends(get_optional_user),
) -> StreamingResponse:
    """
    Main chat endpoint.  Returns a `text/event-stream` response.

    Event sequence per request:
        intent  → sources  → token (×N)  → done
                                         ↳ error (on any failure)

    The caller should provide `session_id` to continue an existing conversation.
    Omit it to start a new session (the session id is embedded in the `done`
    event under `data.session_id`).
    """

    # ── All DB work happens HERE, before the generator is defined ─────────────
    user_id:         uuid.UUID
    session_id:      uuid.UUID
    is_new_session:  bool
    history:         List[Dict[str, str]]

    async with AsyncSessionLocal() as db:
        user             = await _get_or_create_user(current_user, db)
        user_id          = user.id
        user_query_count = user.query_count_today
        user_query_limit = user.query_limit

        # Rate limit — return early with a single SSE error event
        if user_query_count >= user_query_limit:
            async def _rate_limit_stream() -> AsyncIterator[str]:
                yield _sse({
                    "type": "error",
                    "data": {
                        "message": (
                            "আপনার আজকের প্রশ্নের সীমা শেষ হয়ে গেছে। "
                            "আরও প্রশ্নের জন্য প্ল্যান আপগ্রেড করুন। / "
                            "Daily query limit reached. Upgrade your plan for more queries."
                        ),
                        "code":  "RATE_LIMIT",
                        "limit": user_query_limit,
                        "used":  user_query_count,
                    },
                })
            return StreamingResponse(
                _rate_limit_stream(), media_type="text/event-stream", headers=_SSE_HEADERS
            )

        is_new_session = body.session_id is None

        if body.session_id:
            session = await db.get(ChatSession, body.session_id)
            if session is None or session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found",
                )
        else:
            session = ChatSession(user_id=user_id)
            db.add(session)
            await db.flush()

        # Extract scalar — ORM object must not be referenced after this block
        session_id = session.id

        history = await _load_history(session_id, db)

        # Persist the user message and commit before streaming begins
        db.add(Message(session_id=session_id, role="user", content=body.query))
        await db.commit()
    # ── AsyncSession is fully closed here ─────────────────────────────────────

    log      = logger.bind(user_id=str(user_id), session_id=str(session_id), query=body.query[:60])
    pipeline = _get_pipeline()
    log.info("chat_stream_started")

    async def event_generator() -> AsyncIterator[str]:
        # Only plain values here — no AsyncSession, no ORM objects
        intent_data:   Optional[Dict[str, Any]] = None
        sources_data:  List[Any]                = []
        full_response: str                      = ""

        try:
            async for event in pipeline.stream(body.query, history, language=body.language):
                yield _sse(event)

                match event["type"]:
                    case "intent":
                        intent_data = event["data"]
                    case "sources":
                        sources_data = event["data"]
                    case "done":
                        full_response = event["data"].get("full_response", "")
                        log.info(
                            "chat_stream_done",
                            elapsed_ms = event["data"].get("response_time_ms"),
                            strategy   = event["data"].get("strategy"),
                        )
                    case "error":
                        log.error("pipeline_error", message=event["data"].get("message"))

        except Exception as exc:
            logger.error("sse_generator_unhandled_error", error=str(exc))
            yield _sse({"type": "error", "data": {"message": "Internal server error"}})
            return

        # Persist after all tokens are sent — fresh connections, no greenlet risk
        if full_response:
            await _persist_chat_result(
                session_id    = session_id,
                user_id       = user_id,
                full_response = full_response,
                intent_data   = intent_data,
                sources_data  = sources_data,
                is_new_session = is_new_session,
                session_title  = body.query[:60],
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/chat/sessions — create session
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    body: CreateSessionRequest,
    user: User            = Depends(get_db_user),
    db:   AsyncSession    = Depends(get_db),
) -> SessionResponse:
    session = ChatSession(user_id=user.id, title=body.title)
    db.add(session)
    await db.flush()
    return SessionResponse(
        id            = session.id,
        title         = session.title,
        created_at    = session.created_at,
        message_count = 0,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/chat/sessions — list sessions
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    summary="List the current user's chat sessions",
)
async def list_sessions(
    limit:  int           = Query(_SESSION_PAGE_SIZE, ge=1, le=100),
    offset: int           = Query(0, ge=0),
    user:   User          = Depends(get_db_user),
    db:     AsyncSession  = Depends(get_db),
) -> List[SessionResponse]:
    result = await db.execute(
        select(
            ChatSession,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.session_id == ChatSession.id)
        .where(ChatSession.user_id == user.id)
        .group_by(ChatSession.id)
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        SessionResponse(
            id            = row.ChatSession.id,
            title         = row.ChatSession.title,
            created_at    = row.ChatSession.created_at,
            message_count = row.message_count,
        )
        for row in result.fetchall()
    ]


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/chat/sessions/{session_id} — session detail + messages
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get a session with its full message history",
)
async def get_session(
    session_id: uuid.UUID,
    user:       User         = Depends(get_db_user),
    db:         AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(_MESSAGE_HARD_LIMIT)
    )
    messages = msg_result.scalars().all()

    return SessionDetailResponse(
        id         = session.id,
        title      = session.title,
        created_at = session.created_at,
        messages   = [
            MessageResponse(
                id         = m.id,
                role       = m.role,
                content    = m.content,
                intent     = m.intent,
                category   = m.category,
                sources    = m.sources,
                created_at = m.created_at,
            )
            for m in messages
        ],
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/chat/analyze-document — vision document analysis (SSE)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/analyze-document", summary="Analyze a legal document via Claude vision (SSE)")
async def analyze_document(
    file:         UploadFile        = File(..., description="Image (JPEG/PNG/GIF/WEBP) or PDF"),
    query:        str               = Form("", description="Optional user question about the document"),
    session_id:   Optional[str]     = Form(None, description="Existing session UUID to continue"),
    current_user: CurrentUser       = Depends(get_optional_user),
) -> StreamingResponse:
    """
    Accepts a multipart/form-data upload, runs Claude vision to extract a
    text description, then feeds that description through the full RAG pipeline
    (intent detection → vector search → streamed legal answer).

    The response is an SSE stream with the same event format as POST /api/chat.
    """
    # ── File validation (before opening the generator — raises HTTP errors) ──
    file_bytes   = await file.read()
    filename     = file.filename or "document"
    content_type = file.content_type or ""
    media_type   = doc_svc.validate_upload(filename, content_type, len(file_bytes))
    doc_block    = doc_svc.build_content_block(file_bytes, media_type)
    is_pdf       = media_type == doc_svc.PDF_MEDIA_TYPE

    # Resolve session_id string → UUID (Form fields are always strings)
    parsed_session_id: Optional[uuid.UUID] = None
    if session_id:
        try:
            parsed_session_id = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id UUID")

    # Human-readable label stored as the user message in the DB
    display_query = query.strip() or f"[দলিল বিশ্লেষণ / Document: {filename}]"

    # ── All DB work happens HERE, before the generator is defined ─────────────
    user_id:        uuid.UUID
    doc_session_id: uuid.UUID
    is_new_session: bool
    history:        List[Dict[str, str]]

    async with AsyncSessionLocal() as db:
        user             = await _get_or_create_user(current_user, db)
        user_id          = user.id
        user_query_count = user.query_count_today
        user_query_limit = user.query_limit

        if user_query_count >= user_query_limit:
            async def _rate_limit_stream() -> AsyncIterator[str]:
                yield _sse({
                    "type": "error",
                    "data": {
                        "message": (
                            "আপনার আজকের প্রশ্নের সীমা শেষ। আরও প্রশ্নের জন্য প্ল্যান আপগ্রেড করুন। / "
                            "Daily query limit reached. Upgrade your plan for more queries."
                        ),
                        "code":  "RATE_LIMIT",
                        "limit": user_query_limit,
                        "used":  user_query_count,
                    },
                })
            return StreamingResponse(
                _rate_limit_stream(), media_type="text/event-stream", headers=_SSE_HEADERS
            )

        is_new_session = parsed_session_id is None

        if parsed_session_id:
            session = await db.get(ChatSession, parsed_session_id)
            if session is None or session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found",
                )
        else:
            session = ChatSession(user_id=user_id)
            db.add(session)
            await db.flush()

        # Extract scalar — ORM object must not be referenced after this block
        doc_session_id = session.id

        history = await _load_history(doc_session_id, db)

        db.add(Message(session_id=doc_session_id, role="user", content=display_query))
        await db.commit()
    # ── AsyncSession is fully closed here ─────────────────────────────────────

    log      = logger.bind(user_id=str(user_id), session_id=str(doc_session_id), filename=filename)
    pipeline = _get_pipeline()
    log.info("document_analysis_started", media_type=media_type)

    async def event_generator() -> AsyncIterator[str]:
        # Only plain values here — no AsyncSession, no ORM objects
        intent_data:   Optional[Dict[str, Any]] = None
        sources_data:  List[Any]                = []
        full_response: str                      = ""

        # Extract text description from the document (non-streaming Claude call)
        try:
            extracted_query = await pipeline.extract_document_query(
                file_bytes, media_type, query
            )
        except Exception as exc:
            log.error("document_extraction_failed", error=str(exc))
            yield _sse({"type": "error", "data": {"message": f"Could not read document: {exc}"}})
            return

        try:
            async for event in pipeline.stream_with_document(
                extracted_query      = extracted_query,
                document_block       = doc_block,
                user_hint            = query,
                is_pdf               = is_pdf,
                conversation_history = history,
            ):
                yield _sse(event)

                match event["type"]:
                    case "intent":
                        intent_data = event["data"]
                    case "sources":
                        sources_data = event["data"]
                    case "done":
                        full_response = event["data"].get("full_response", "")
                        log.info(
                            "document_analysis_done",
                            elapsed_ms=event["data"].get("response_time_ms"),
                        )
                    case "error":
                        log.error("pipeline_error", message=event["data"].get("message"))

        except Exception as exc:
            logger.error("sse_analyze_unhandled_error", error=str(exc))
            yield _sse({"type": "error", "data": {"message": "Internal server error"}})
            return

        # Persist after all tokens are sent — fresh connections, no greenlet risk
        if full_response:
            await _persist_chat_result(
                session_id    = doc_session_id,
                user_id       = user_id,
                full_response = full_response,
                intent_data   = intent_data,
                sources_data  = sources_data,
                is_new_session = is_new_session,
                session_title  = f"📄 {filename[:55]}",
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
