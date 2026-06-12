"""Admin router — platform management endpoints.

All routes require is_admin = True on the authenticated user.

Endpoints
---------
GET    /api/admin/stats
GET    /api/admin/users          (paginated)
PATCH  /api/admin/users/{id}
DELETE /api/admin/users/{id}     (soft delete: is_active = False)
GET    /api/admin/revenue
GET    /api/admin/activity
GET    /api/admin/lawyers
POST   /api/admin/lawyers
PATCH  /api/admin/lawyers/{id}
DELETE /api/admin/lawyers/{id}
GET    /api/admin/subscriptions
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_admin_user
from app.db.database import get_db
from app.models.court_case import CourtCase
from app.models.lawyer import Lawyer
from app.models.message import ChatSession
from app.models.subscription import Subscription
from app.models.template import GeneratedDocument
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    total_users: int
    new_users_today: int
    new_users_week: int
    total_chats: int
    chats_today: int
    pro_users: int
    free_users: int
    student_users: int
    total_revenue: float
    monthly_revenue: float
    total_documents: int
    total_cases: int
    active_users_today: int
    total_lawyers: int
    verified_lawyers: int
    total_subscriptions: int
    active_subscriptions: int


class AdminUserItem(BaseModel):
    id: str
    email: str
    name: Optional[str]
    plan: str
    is_admin: bool
    is_active: bool
    query_count_today: int
    query_limit: int
    total_chats: int
    created_at: Optional[str]


class UserListResponse(BaseModel):
    users: List[AdminUserItem]
    total: int
    page: int
    pages: int


class PatchUserRequest(BaseModel):
    plan: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    query_limit: Optional[int] = None


class MonthlyRevenue(BaseModel):
    month: str
    revenue: float
    new_pro: int


class RevenueData(BaseModel):
    monthly: List[MonthlyRevenue]
    total_revenue: float
    mrr: float


class ActivityItem(BaseModel):
    type: str
    description: str
    time: str
    detail: Optional[str] = None


class ActivityData(BaseModel):
    activities: List[ActivityItem]


class AdminLawyerItem(BaseModel):
    id: str
    name: str
    email: Optional[str]
    bar_number: Optional[str]
    specializations: List[str]
    experience_years: int
    location: Optional[str]
    is_verified: bool
    is_available: bool
    rating: float
    total_reviews: int
    fee_per_consultation: Optional[float]


class CreateLawyerRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bar_number: Optional[str] = None
    specializations: List[str] = []
    experience_years: int = 0
    fee_per_hour: Optional[float] = None
    fee_per_consultation: Optional[float] = None
    location: Optional[str] = None
    bio: Optional[str] = None


class PatchLawyerRequest(BaseModel):
    is_verified: Optional[bool] = None
    is_available: Optional[bool] = None
    name: Optional[str] = None
    location: Optional[str] = None
    fee_per_consultation: Optional[float] = None


class AdminSubscriptionItem(BaseModel):
    id: str
    user_email: str
    plan: str
    status: str
    amount: float
    currency: str
    transaction_id: str
    activated_at: Optional[str]
    expires_at: Optional[str]
    created_at: Optional[str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _user_item(u: User, total_chats: int = 0) -> AdminUserItem:
    return AdminUserItem(
        id=str(u.id),
        email=u.email,
        name=u.name,
        plan=u.plan,
        is_admin=u.is_admin,
        is_active=u.is_active,
        query_count_today=u.query_count_today,
        query_limit=u.query_limit,
        total_chats=total_chats,
        created_at=u.created_at.isoformat() if u.created_at else None,
    )


def _lawyer_item(lawyer: Lawyer) -> AdminLawyerItem:
    return AdminLawyerItem(
        id=str(lawyer.id),
        name=lawyer.name,
        email=lawyer.email,
        bar_number=lawyer.bar_number,
        specializations=list(lawyer.specializations or []),
        experience_years=lawyer.experience_years or 0,
        location=lawyer.location,
        is_verified=lawyer.is_verified,
        is_available=lawyer.is_available,
        rating=float(lawyer.rating or 0),
        total_reviews=lawyer.total_reviews or 0,
        fee_per_consultation=float(lawyer.fee_per_consultation) if lawyer.fee_per_consultation else None,
    )


def _last_n_months(n: int) -> List[str]:
    """Return YYYY-MM strings for the last n months, oldest first."""
    today = date.today()
    months: List[str] = []
    for i in range(n - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year}-{month:02d}")
    return months


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStats)
async def get_stats(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminStats:
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_start = date(today.year, today.month, 1)

    async def _count(stmt: Any) -> int:
        return (await db.execute(stmt)).scalar_one()

    total_users        = await _count(select(func.count()).select_from(User))
    new_users_today    = await _count(
        select(func.count()).select_from(User)
        .where(func.date(User.created_at) == today)
    )
    new_users_week     = await _count(
        select(func.count()).select_from(User)
        .where(func.date(User.created_at) >= week_ago)
    )
    pro_users          = await _count(
        select(func.count()).select_from(User).where(User.plan == "pro")
    )
    free_users         = await _count(
        select(func.count()).select_from(User).where(User.plan == "free")
    )
    student_users      = await _count(
        select(func.count()).select_from(User).where(User.plan == "student")
    )
    active_users_today = await _count(
        select(func.count()).select_from(User).where(User.query_count_today > 0)
    )
    total_chats        = await _count(select(func.count()).select_from(ChatSession))
    chats_today        = await _count(
        select(func.count()).select_from(ChatSession)
        .where(func.date(ChatSession.created_at) == today)
    )
    total_documents    = await _count(select(func.count()).select_from(GeneratedDocument))
    total_cases        = await _count(select(func.count()).select_from(CourtCase))
    total_lawyers      = await _count(select(func.count()).select_from(Lawyer))
    verified_lawyers   = await _count(
        select(func.count()).select_from(Lawyer).where(Lawyer.is_verified == True)  # noqa: E712
    )
    total_subscriptions  = await _count(select(func.count()).select_from(Subscription))
    active_subscriptions = await _count(
        select(func.count()).select_from(Subscription).where(Subscription.status == "active")
    )

    total_rev_result = (await db.execute(
        select(func.sum(Subscription.amount)).where(Subscription.status == "active")
    )).scalar_one()
    total_revenue = float(total_rev_result or 0)

    monthly_rev_result = (await db.execute(
        select(func.sum(Subscription.amount))
        .where(Subscription.status == "active")
        .where(func.date(Subscription.activated_at) >= month_start)
    )).scalar_one()
    monthly_revenue = float(monthly_rev_result or 0)

    return AdminStats(
        total_users=total_users,
        new_users_today=new_users_today,
        new_users_week=new_users_week,
        total_chats=total_chats,
        chats_today=chats_today,
        pro_users=pro_users,
        free_users=free_users,
        student_users=student_users,
        total_revenue=total_revenue,
        monthly_revenue=monthly_revenue,
        total_documents=total_documents,
        total_cases=total_cases,
        active_users_today=active_users_today,
        total_lawyers=total_lawyers,
        verified_lawyers=verified_lawyers,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions,
    )


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    plan: Optional[str] = Query(None),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    # Correlated subquery: count chat sessions per user
    chat_count_sq = (
        select(func.count(ChatSession.id))
        .where(ChatSession.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )

    base_filter = [User.is_active == True]  # noqa: E712
    if search:
        term = f"%{search}%"
        base_filter.append(or_(User.email.ilike(term), User.name.ilike(term)))
    if plan and plan != "all":
        base_filter.append(User.plan == plan)

    total = (await db.execute(
        select(func.count()).select_from(User).where(*base_filter)
    )).scalar_one()

    rows = (await db.execute(
        select(User, chat_count_sq.label("total_chats"))
        .where(*base_filter)
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )).all()

    users_data = [_user_item(row[0], int(row[1] or 0)) for row in rows]
    pages = max(1, (total + limit - 1) // limit)

    return UserListResponse(users=users_data, total=total, page=page, pages=pages)


@router.patch("/users/{user_id}", response_model=AdminUserItem)
async def patch_user(
    user_id: str,
    body: PatchUserRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserItem:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if body.plan is not None:
        user.plan = body.plan
        if body.query_limit is None:
            user.query_limit = 200 if body.plan in ("pro", "student", "lawyer") else 10
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.query_limit is not None:
        user.query_limit = body.query_limit

    await db.flush()
    logger.info("admin_user_patched", user_id=user_id, changes=body.model_dump(exclude_none=True))
    return _user_item(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot deactivate an admin user")

    user.is_active = False
    await db.flush()
    logger.info("admin_user_deactivated", user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Revenue ──────────────────────────────────────────────────────────────────

@router.get("/revenue", response_model=RevenueData)
async def get_revenue(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> RevenueData:
    # Fetch all activated subscriptions
    subs = (await db.execute(
        select(Subscription)
        .where(Subscription.status == "active")
        .order_by(Subscription.activated_at.desc())
    )).scalars().all()

    # Build per-month aggregates
    month_data: Dict[str, Dict[str, Any]] = {}
    for s in subs:
        if not s.activated_at:
            continue
        key = s.activated_at.strftime("%Y-%m")
        if key not in month_data:
            month_data[key] = {"revenue": 0.0, "new_pro": 0}
        month_data[key]["revenue"] += float(s.amount)
        month_data[key]["new_pro"] += 1

    # Fill last 12 months (including zeros)
    monthly: List[MonthlyRevenue] = []
    for m in _last_n_months(12):
        d = month_data.get(m, {"revenue": 0.0, "new_pro": 0})
        monthly.append(MonthlyRevenue(month=m, revenue=d["revenue"], new_pro=d["new_pro"]))

    total_revenue = sum(m.revenue for m in monthly)
    mrr = monthly[-1].revenue if monthly else 0.0

    return RevenueData(monthly=monthly, total_revenue=total_revenue, mrr=mrr)


# ─── Activity ─────────────────────────────────────────────────────────────────

@router.get("/activity", response_model=ActivityData)
async def get_activity(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ActivityData:
    recent_users = (await db.execute(
        select(User).order_by(User.created_at.desc()).limit(20)
    )).scalars().all()

    recent_subs = (await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.user))
        .order_by(Subscription.created_at.desc())
        .limit(20)
    )).scalars().all()

    recent_chats = (await db.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc()).limit(20)
    )).scalars().all()

    activities: List[Dict[str, Any]] = []

    for u in recent_users:
        if u.created_at:
            activities.append({
                "type": "new_user",
                "description": f"নতুন নিবন্ধন: {u.email}",
                "time": u.created_at.isoformat(),
                "detail": u.name or None,
            })

    for s in recent_subs:
        if s.created_at:
            email = s.user.email if s.user else "unknown"
            activities.append({
                "type": "new_payment",
                "description": f"পেমেন্ট: {email}",
                "time": s.created_at.isoformat(),
                "detail": f"৳{float(s.amount):.0f} — {s.plan} — {s.status}",
            })

    for sess in recent_chats:
        if sess.created_at:
            activities.append({
                "type": "new_chat",
                "description": "নতুন চ্যাট সেশন",
                "time": sess.created_at.isoformat(),
                "detail": sess.title or None,
            })

    activities.sort(key=lambda x: x["time"], reverse=True)

    return ActivityData(
        activities=[ActivityItem(**a) for a in activities[:50]]
    )


# ─── Lawyers ──────────────────────────────────────────────────────────────────

@router.get("/lawyers", response_model=List[AdminLawyerItem])
async def list_lawyers_admin(
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> List[AdminLawyerItem]:
    lawyers = (
        await db.execute(select(Lawyer).order_by(Lawyer.rating.desc()))
    ).scalars().all()
    return [_lawyer_item(l) for l in lawyers]


@router.post("/lawyers", response_model=AdminLawyerItem, status_code=status.HTTP_201_CREATED)
async def create_lawyer(
    body: CreateLawyerRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminLawyerItem:
    lawyer = Lawyer(
        name=body.name,
        email=body.email,
        phone=body.phone,
        bar_number=body.bar_number,
        specializations=body.specializations,
        experience_years=body.experience_years,
        fee_per_hour=Decimal(str(body.fee_per_hour)) if body.fee_per_hour else None,
        fee_per_consultation=Decimal(str(body.fee_per_consultation)) if body.fee_per_consultation else None,
        location=body.location,
        bio=body.bio,
    )
    db.add(lawyer)
    await db.flush()
    logger.info("admin_lawyer_created", name=body.name)
    return _lawyer_item(lawyer)


@router.patch("/lawyers/{lawyer_id}", response_model=AdminLawyerItem)
async def patch_lawyer(
    lawyer_id: str,
    body: PatchLawyerRequest,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminLawyerItem:
    try:
        lid = uuid.UUID(lawyer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lawyer ID")

    lawyer = (await db.execute(select(Lawyer).where(Lawyer.id == lid))).scalar_one_or_none()
    if lawyer is None:
        raise HTTPException(status_code=404, detail="Lawyer not found")

    if body.is_verified is not None:
        lawyer.is_verified = body.is_verified
    if body.is_available is not None:
        lawyer.is_available = body.is_available
    if body.name is not None:
        lawyer.name = body.name
    if body.location is not None:
        lawyer.location = body.location
    if body.fee_per_consultation is not None:
        lawyer.fee_per_consultation = Decimal(str(body.fee_per_consultation))

    await db.flush()
    logger.info("admin_lawyer_patched", lawyer_id=lawyer_id)
    return _lawyer_item(lawyer)


@router.delete("/lawyers/{lawyer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lawyer(
    lawyer_id: str,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        lid = uuid.UUID(lawyer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lawyer ID")

    lawyer = (await db.execute(select(Lawyer).where(Lawyer.id == lid))).scalar_one_or_none()
    if lawyer is None:
        raise HTTPException(status_code=404, detail="Lawyer not found")

    await db.delete(lawyer)
    logger.info("admin_lawyer_deleted", lawyer_id=lawyer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Subscriptions ────────────────────────────────────────────────────────────

@router.get("/subscriptions", response_model=List[AdminSubscriptionItem])
async def list_subscriptions(
    skip: int = 0,
    limit: int = 50,
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> List[AdminSubscriptionItem]:
    subs = (await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.user))
        .order_by(Subscription.created_at.desc())
        .offset(skip)
        .limit(min(limit, 200))
    )).scalars().all()
    return [
        AdminSubscriptionItem(
            id=str(s.id),
            user_email=s.user.email if s.user else "unknown",
            plan=s.plan,
            status=s.status,
            amount=float(s.amount),
            currency=s.currency,
            transaction_id=s.transaction_id,
            activated_at=s.activated_at.isoformat() if s.activated_at else None,
            expires_at=s.expires_at.isoformat() if s.expires_at else None,
            created_at=s.created_at.isoformat() if s.created_at else None,
        )
        for s in subs
    ]
