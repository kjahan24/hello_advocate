"""
Dashboard router.

GET /api/dashboard/stats  — authenticated; returns user info, subscription, and usage stats
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.court_case import CourtCase
from app.models.message import ChatSession
from app.models.subscription import Subscription
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["dashboard"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    name:              Optional[str]
    email:             str
    plan:              str
    query_count_today: int
    query_limit:       int
    joined_at:         Optional[str]


class SubscriptionSummary(BaseModel):
    plan:      str
    status:    str
    expires_at: Optional[str]
    is_active: bool


class StatsSummary(BaseModel):
    today_questions: int
    total_chats:     int
    total_documents: int
    upcoming_cases:  int


class DashboardStats(BaseModel):
    user:         UserSummary
    subscription: SubscriptionSummary
    stats:        StatsSummary


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> DashboardStats:
    # Fetch user row
    user_result = await db.execute(select(User).where(User.email == current_user.email))
    user = user_result.scalar_one_or_none()

    if user is None:
        # Edge case: token valid but user deleted — return minimal response
        return DashboardStats(
            user=UserSummary(
                name=current_user.name, email=current_user.email,
                plan="free", query_count_today=0, query_limit=10, joined_at=None,
            ),
            subscription=SubscriptionSummary(plan="free", status="none", expires_at=None, is_active=False),
            stats=StatsSummary(today_questions=0, total_chats=0, total_documents=0, upcoming_cases=0),
        )

    # Count chat sessions
    chat_count_result = await db.execute(
        select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user.id)
    )
    total_chats = chat_count_result.scalar_one() or 0

    # Count upcoming court cases (next_date within 7 days, status=active)
    today  = date.today()
    cutoff = today + timedelta(days=7)
    upcoming_result = await db.execute(
        select(func.count()).select_from(CourtCase).where(
            CourtCase.user_id == user.id,
            CourtCase.status  == "active",
            CourtCase.next_date >= today,
            CourtCase.next_date <= cutoff,
        )
    )
    upcoming_cases = upcoming_result.scalar_one() or 0

    # Get most recent active subscription
    sub_result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = sub_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if sub and (sub.expires_at is None or sub.expires_at > now):
        subscription = SubscriptionSummary(
            plan=sub.plan,
            status="active",
            expires_at=sub.expires_at.isoformat() if sub.expires_at else None,
            is_active=True,
        )
    else:
        subscription = SubscriptionSummary(
            plan=user.plan,
            status="none",
            expires_at=None,
            is_active=False,
        )

    logger.info("dashboard_stats_fetched", email=user.email, total_chats=total_chats)

    return DashboardStats(
        user=UserSummary(
            name=user.name,
            email=user.email,
            plan=user.plan,
            query_count_today=user.query_count_today,
            query_limit=user.query_limit,
            joined_at=user.created_at.isoformat() if user.created_at else None,
        ),
        subscription=subscription,
        stats=StatsSummary(
            today_questions=user.query_count_today,
            total_chats=total_chats,
            total_documents=0,
            upcoming_cases=upcoming_cases,
        ),
    )
