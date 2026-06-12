"""
Auth router — register, login, current-user info, logout.

Endpoints
---------
POST /api/auth/register  → create user + return JWT
POST /api/auth/login     → verify credentials + return JWT
GET  /api/auth/me        → return profile for the bearer token holder
POST /api/auth/logout    → stateless JWT: just acknowledge (client clears session)
"""
from __future__ import annotations

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, create_access_token, get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id                = str(user.id),
        email             = user.email,
        name              = user.name,
        phone             = user.phone,
        role              = user.role,
        plan              = user.plan,
        query_count_today = user.query_count_today,
        query_limit       = user.query_limit,
        is_admin          = user.is_admin,
        created_at        = user.created_at.isoformat() if user.created_at else None,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/register
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and return a JWT",
)
async def register(
    body: RegisterRequest,
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Uniqueness check
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="এই ইমেইল দিয়ে ইতিমধ্যে একটি অ্যাকাউন্ট আছে।",
        )

    password_bytes = body.password.encode('utf-8')[:72].decode('utf-8', errors='ignore').encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
    user = User(
        email           = body.email,
        name            = body.name,
        phone           = body.phone,
        hashed_password = hashed,
    )
    db.add(user)
    await db.flush()   # assigns user.id before we need it for the token

    token = create_access_token(
        email   = user.email,
        name    = user.name,
        user_id = str(user.id),
    )
    logger.info("user_registered", email=user.email)
    return TokenResponse(access_token=token, user=_to_response(user))


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email + password and return a JWT",
)
async def login(
    body: LoginRequest,
    db:   AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    password_bytes = body.password.encode('utf-8')[:72].decode('utf-8', errors='ignore').encode('utf-8')
    if (
        user is None
        or user.hashed_password is None
        or not bcrypt.checkpw(password_bytes, user.hashed_password.encode('utf-8'))
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ইমেইল বা পাসওয়ার্ড সঠিক নয়।",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        email   = user.email,
        name    = user.name,
        user_id = str(user.id),
    )
    logger.info("user_logged_in", email=user.email)
    return TokenResponse(access_token=token, user=_to_response(user))


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
async def get_me(
    current_user: CurrentUser  = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(select(User).where(User.email == current_user.email))
    user   = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_response(user)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/auth/profile
# ──────────────────────────────────────────────────────────────────────────────

@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update user name and phone",
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: CurrentUser  = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(select(User).where(User.email == current_user.email))
    user   = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.name is not None and body.name.strip():
        user.name = body.name.strip()
    if body.phone is not None:
        user.phone = body.phone.strip() or None

    await db.commit()
    await db.refresh(user)
    logger.info("profile_updated", email=user.email)
    return _to_response(user)


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/auth/password
# ──────────────────────────────────────────────────────────────────────────────

@router.put(
    "/password",
    status_code=status.HTTP_200_OK,
    summary="Change the authenticated user's password",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser  = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(select(User).where(User.email == current_user.email))
    user   = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="এই অ্যাকাউন্টে পাসওয়ার্ড সেট করা নেই।",
        )

    current_bytes = body.current_password.encode("utf-8")[:72]
    if not bcrypt.checkpw(current_bytes, user.hashed_password.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="বর্তমান পাসওয়ার্ড সঠিক নয়।",
        )

    new_bytes = body.new_password.encode("utf-8")[:72]
    user.hashed_password = bcrypt.hashpw(new_bytes, bcrypt.gensalt()).decode("utf-8")
    await db.commit()
    logger.info("password_changed", email=user.email)
    return {"message": "পাসওয়ার্ড সফলভাবে পরিবর্তিত হয়েছে।"}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (client must clear the session — JWTs are stateless)",
)
async def logout() -> dict[str, str]:
    return {"message": "লগআউট সফল হয়েছে।"}
