"""
Court Cases router — track case hearing dates.

GET    /api/court-cases           → list user's cases
POST   /api/court-cases           → create a new case
GET    /api/court-cases/upcoming  → cases with next_date within 7 days
GET    /api/court-cases/{id}      → single case
PUT    /api/court-cases/{id}      → update case
DELETE /api/court-cases/{id}      → delete case
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.database import get_db
from app.models.court_case import CourtCase
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["court-cases"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CourtCaseCreate(BaseModel):
    case_title:  str
    case_number: Optional[str] = None
    court_name:  str
    case_type:   str = "other"
    next_date:   date
    description: Optional[str] = None
    status:      str = "active"


class CourtCaseUpdate(BaseModel):
    case_title:  Optional[str]  = None
    case_number: Optional[str]  = None
    court_name:  Optional[str]  = None
    case_type:   Optional[str]  = None
    next_date:   Optional[date] = None
    description: Optional[str]  = None
    status:      Optional[str]  = None


class CourtCaseResponse(BaseModel):
    id:          str
    case_title:  str
    case_number: Optional[str]
    court_name:  str
    case_type:   str
    next_date:   str
    description: Optional[str]
    status:      str
    created_at:  str
    updated_at:  str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_response(c: CourtCase) -> CourtCaseResponse:
    return CourtCaseResponse(
        id=str(c.id),
        case_title=c.case_title,
        case_number=c.case_number,
        court_name=c.court_name,
        case_type=c.case_type,
        next_date=c.next_date.isoformat(),
        description=c.description,
        status=c.status,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


async def _get_user_id(email: str, db: AsyncSession) -> uuid.UUID:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ব্যবহারকারী পাওয়া যায়নি।")
    return user.id


async def _get_owned_case(
    case_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> CourtCase:
    result = await db.execute(
        select(CourtCase).where(CourtCase.id == case_id, CourtCase.user_id == user_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="মামলা পাওয়া যায়নি।")
    return case


# ─── Endpoints — specific routes BEFORE parameterised ─────────────────────────

@router.get("/court-cases/upcoming", response_model=List[CourtCaseResponse])
async def get_upcoming_cases(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> List[CourtCaseResponse]:
    """Return cases with next_date within the next 7 days."""
    user_id = await _get_user_id(current_user.email, db)
    today   = date.today()
    cutoff  = today + timedelta(days=7)

    result = await db.execute(
        select(CourtCase)
        .where(
            CourtCase.user_id == user_id,
            CourtCase.status == "active",
            CourtCase.next_date >= today,
            CourtCase.next_date <= cutoff,
        )
        .order_by(CourtCase.next_date)
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.get("/court-cases", response_model=List[CourtCaseResponse])
async def list_cases(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> List[CourtCaseResponse]:
    user_id = await _get_user_id(current_user.email, db)
    result  = await db.execute(
        select(CourtCase)
        .where(CourtCase.user_id == user_id)
        .order_by(CourtCase.next_date)
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.post("/court-cases", response_model=CourtCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body:         CourtCaseCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> CourtCaseResponse:
    user_id = await _get_user_id(current_user.email, db)
    now     = datetime.now(timezone.utc)
    case    = CourtCase(
        user_id=user_id,
        case_title=body.case_title,
        case_number=body.case_number,
        court_name=body.court_name,
        case_type=body.case_type,
        next_date=body.next_date,
        description=body.description,
        status=body.status,
        updated_at=now,
    )
    db.add(case)
    await db.flush()
    logger.info("court_case_created", user=current_user.email, title=case.case_title)
    return _to_response(case)


@router.get("/court-cases/{case_id}", response_model=CourtCaseResponse)
async def get_case(
    case_id:      uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> CourtCaseResponse:
    user_id = await _get_user_id(current_user.email, db)
    return _to_response(await _get_owned_case(case_id, user_id, db))


@router.put("/court-cases/{case_id}", response_model=CourtCaseResponse)
async def update_case(
    case_id:      uuid.UUID,
    body:         CourtCaseUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> CourtCaseResponse:
    user_id = await _get_user_id(current_user.email, db)
    case    = await _get_owned_case(case_id, user_id, db)

    if body.case_title  is not None: case.case_title  = body.case_title
    if body.case_number is not None: case.case_number = body.case_number
    if body.court_name  is not None: case.court_name  = body.court_name
    if body.case_type   is not None: case.case_type   = body.case_type
    if body.next_date   is not None: case.next_date   = body.next_date
    if body.description is not None: case.description = body.description
    if body.status      is not None: case.status      = body.status
    case.updated_at = datetime.now(timezone.utc)

    logger.info("court_case_updated", case_id=str(case_id), user=current_user.email)
    return _to_response(case)


@router.delete("/court-cases/{case_id}")
async def delete_case(
    case_id:      uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db:           Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    user_id = await _get_user_id(current_user.email, db)
    case    = await _get_owned_case(case_id, user_id, db)
    await db.delete(case)
    logger.info("court_case_deleted", case_id=str(case_id), user=current_user.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
