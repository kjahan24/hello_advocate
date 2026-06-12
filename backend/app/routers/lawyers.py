"""
Lawyers router — Lawyer Referral Marketplace.

GET  /api/lawyers           → list verified lawyers (filter: specialization, location)
GET  /api/lawyers/{id}      → single lawyer profile
POST /api/lawyers/{id}/contact → return contact info (requires auth)
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.lawyer import Lawyer

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["lawyers"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LawyerCard(BaseModel):
    id:                   str
    name:                 str
    specializations:      List[str]
    experience_years:     int
    fee_per_consultation: Optional[float]
    fee_per_hour:         Optional[float]
    location:             Optional[str]
    rating:               float
    total_reviews:        int
    is_verified:          bool
    is_available:         bool
    bio:                  Optional[str]
    bar_number:           Optional[str]


class LawyerDetail(LawyerCard):
    email: Optional[str]
    phone: Optional[str]


class ContactResponse(BaseModel):
    phone:   Optional[str]
    email:   Optional[str]
    message: str


# ─── Helper ───────────────────────────────────────────────────────────────────

def _to_card(l: Lawyer) -> LawyerCard:
    return LawyerCard(
        id=str(l.id),
        name=l.name,
        specializations=list(l.specializations) if l.specializations else [],
        experience_years=l.experience_years,
        fee_per_consultation=float(l.fee_per_consultation) if l.fee_per_consultation else None,
        fee_per_hour=float(l.fee_per_hour) if l.fee_per_hour else None,
        location=l.location,
        rating=float(l.rating),
        total_reviews=l.total_reviews,
        is_verified=l.is_verified,
        is_available=l.is_available,
        bio=l.bio,
        bar_number=l.bar_number,
    )


def _to_detail(l: Lawyer) -> LawyerDetail:
    card = _to_card(l)
    return LawyerDetail(**card.model_dump(), email=l.email, phone=l.phone)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/lawyers", response_model=List[LawyerCard])
async def list_lawyers(
    specialization: Optional[str] = Query(None, description="Filter by specialization slug"),
    location:       Optional[str] = Query(None, description="Filter by district name"),
    db:             AsyncSession  = Depends(get_db),
) -> List[LawyerCard]:
    stmt = (
        select(Lawyer)
        .where(Lawyer.is_verified == True)  # noqa: E712
        .order_by(Lawyer.rating.desc(), Lawyer.experience_years.desc())
    )
    if location:
        stmt = stmt.where(Lawyer.location.ilike(f"%{location}%"))

    result = await db.execute(stmt)
    lawyers = result.scalars().all()

    if specialization:
        lawyers = [l for l in lawyers if specialization in (l.specializations or [])]

    return [_to_card(l) for l in lawyers]


@router.get("/lawyers/{lawyer_id}", response_model=LawyerDetail)
async def get_lawyer(
    lawyer_id: uuid.UUID,
    db:        AsyncSession = Depends(get_db),
) -> LawyerDetail:
    result = await db.execute(select(Lawyer).where(Lawyer.id == lawyer_id))
    lawyer = result.scalar_one_or_none()
    if lawyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="আইনজীবী পাওয়া যায়নি।")
    return _to_detail(lawyer)


@router.post("/lawyers/{lawyer_id}/contact", response_model=ContactResponse)
async def contact_lawyer(
    lawyer_id:    uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
) -> ContactResponse:
    result = await db.execute(select(Lawyer).where(Lawyer.id == lawyer_id))
    lawyer = result.scalar_one_or_none()
    if lawyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="আইনজীবী পাওয়া যায়নি।")

    logger.info("lawyer_contact_requested", lawyer=lawyer.name, user=current_user.email)
    return ContactResponse(
        phone=lawyer.phone,
        email=lawyer.email,
        message=f"{lawyer.name}-এর সাথে যোগাযোগ করুন। ফোন বা ইমেইলে সরাসরি কথা বলতে পারেন।",
    )
