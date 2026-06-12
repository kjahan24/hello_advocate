"""
Payments router — SSLCommerz integration.

POST /api/payments/initiate  — authenticated; creates pending subscription, returns GatewayPageURL
POST /api/payments/success   — SSLCommerz browser redirect after payment success
POST /api/payments/fail      — SSLCommerz browser redirect after payment failure
POST /api/payments/cancel    — SSLCommerz browser redirect after payment cancel
POST /api/payments/ipn       — SSLCommerz server-to-server IPN webhook
GET  /api/payments/status    — authenticated; return current user's subscription status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, status as http_status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import GUEST_EMAIL, CurrentUser, get_current_user, get_optional_user
from app.db.database import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.services import sslcommerz

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["payments"])

_PRO_AMOUNT        = 999.00  # BDT
_PRO_DURATION_DAYS = 30


# ─── Schemas ──────────────────────────────────────────────────────────────────

class InitiateResponse(BaseModel):
    gateway_url:    str
    transaction_id: str


class SubscriptionStatus(BaseModel):
    plan:      str
    status:    str
    expires_at: Optional[datetime]
    is_active: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _new_tran_id() -> str:
    return f"HA-{uuid.uuid4().hex[:16].upper()}"


async def _fetch_user(email: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="ব্যবহারকারী পাওয়া যায়নি।",
        )
    return user


async def _activate_subscription(
    sub: Subscription, val_id: str, db: AsyncSession
) -> None:
    """Mark subscription active and upgrade the user's plan."""
    now = datetime.now(timezone.utc)
    sub.status        = "active"
    sub.ssl_session_id = val_id
    sub.activated_at  = now
    sub.expires_at    = now + timedelta(days=_PRO_DURATION_DAYS)

    user_result = await db.execute(select(User).where(User.id == sub.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.plan        = "pro"
        user.query_limit = 200


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/payments/initiate", response_model=InitiateResponse)
async def initiate_payment(
    current_user: Annotated[CurrentUser, Depends(get_optional_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> InitiateResponse:
    if current_user.email == GUEST_EMAIL:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="পেমেন্ট শুরু করতে লগইন করুন।",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user    = await _fetch_user(current_user.email, db)
    tran_id = _new_tran_id()

    sub = Subscription(
        user_id=user.id,
        plan="pro",
        status="pending",
        amount=_PRO_AMOUNT,
        currency="BDT",
        transaction_id=tran_id,
    )
    db.add(sub)
    await db.flush()

    gateway_url = await sslcommerz.init_payment(
        tran_id=tran_id,
        amount=_PRO_AMOUNT,
        plan="pro",
        cus_name=current_user.name or current_user.email,
        cus_email=current_user.email,
        cus_phone=getattr(user, "phone", None) or "01700000000",
    )

    logger.info("payment_initiated", tran_id=tran_id, email=current_user.email)
    return InitiateResponse(gateway_url=gateway_url, transaction_id=tran_id)


@router.post("/payments/success")
async def payment_success(
    tran_id: Annotated[str, Form()],
    val_id:  Annotated[str, Form()],
    db:      AsyncSession = Depends(get_db),
):
    """SSLCommerz redirects the browser here after a successful payment."""
    settings = get_settings()

    try:
        verification = await sslcommerz.verify_payment(val_id)
        verified     = verification.get("status") in ("VALID", "VALIDATED")
    except HTTPException:
        verified = False

    result = await db.execute(
        select(Subscription).where(Subscription.transaction_id == tran_id)
    )
    sub = result.scalar_one_or_none()

    if sub and verified:
        await _activate_subscription(sub, val_id, db)
        logger.info("payment_activated", tran_id=tran_id, val_id=val_id)
    else:
        if sub:
            sub.status = "failed"
        logger.warning("payment_verification_failed", tran_id=tran_id, verified=verified)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/payment/success?tran_id={tran_id}",
        status_code=303,
    )


@router.post("/payments/fail")
async def payment_fail(
    tran_id: Annotated[str, Form()],
    db:      AsyncSession = Depends(get_db),
):
    settings = get_settings()
    result = await db.execute(
        select(Subscription).where(Subscription.transaction_id == tran_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "failed"
    logger.info("payment_failed", tran_id=tran_id)
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/payment/fail?tran_id={tran_id}",
        status_code=303,
    )


@router.post("/payments/cancel")
async def payment_cancel(
    tran_id: Annotated[str, Form()],
    db:      AsyncSession = Depends(get_db),
):
    settings = get_settings()
    result = await db.execute(
        select(Subscription).where(Subscription.transaction_id == tran_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "cancelled"
    logger.info("payment_cancelled", tran_id=tran_id)
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/payment/cancel?tran_id={tran_id}",
        status_code=303,
    )


@router.post("/payments/ipn")
async def payment_ipn(
    tran_id:    Annotated[str, Form()] = "",
    val_id:     Annotated[str, Form()] = "",
    ipn_status: Annotated[str, Form(alias="status")] = "",
    db:         AsyncSession = Depends(get_db),
):
    """
    Server-to-server IPN from SSLCommerz — mirrors success logic without a redirect.
    Always returns 200 so SSLCommerz stops retrying.
    """
    if not tran_id or ipn_status not in ("VALID", "VALIDATED"):
        return {"received": True}

    try:
        verification = await sslcommerz.verify_payment(val_id)
        if verification.get("status") not in ("VALID", "VALIDATED"):
            return {"received": True}
    except HTTPException:
        return {"received": True}

    result = await db.execute(
        select(Subscription).where(Subscription.transaction_id == tran_id)
    )
    sub = result.scalar_one_or_none()
    if sub and sub.status != "active":
        await _activate_subscription(sub, val_id, db)
        logger.info("ipn_activated", tran_id=tran_id)

    return {"received": True}


@router.get("/payments/status", response_model=SubscriptionStatus)
async def get_payment_status(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionStatus:
    user = await _fetch_user(current_user.email, db)

    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if sub:
        is_active = sub.expires_at is None or sub.expires_at > datetime.now(timezone.utc)
        return SubscriptionStatus(
            plan=sub.plan,
            status=sub.status,
            expires_at=sub.expires_at,
            is_active=is_active,
        )

    return SubscriptionStatus(
        plan=user.plan,
        status="active",
        expires_at=None,
        is_active=True,
    )
