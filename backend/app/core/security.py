"""
Security utilities: JWT verification, password hashing, token creation.

Bearer token flow
-----------------
1. Client POSTs /api/auth/login → backend issues JWT signed with JWT_SECRET.
2. NextAuth CredentialsProvider stores it as session.accessToken.
3. Frontend sends "Authorization: Bearer <jwt>" on every API request.
4. get_current_user / get_optional_user decode with JWT_SECRET here.

Token payload shape
-------------------
  {"sub": "<user_uuid>", "email": "...", "name": "...", "exp": <unix_ts>}
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.models.user import User

logger = structlog.get_logger(__name__)

_bearer          = HTTPBearer(auto_error=True)   # strict — 401 if header absent
_bearer_optional = HTTPBearer(auto_error=False)  # lenient — None if header absent

# Email used for unauthenticated requests in development
GUEST_EMAIL = "guest@dev.local"

_TOKEN_EXPIRE_DAYS = 7

# ──────────────────────────────────────────────────────────────────────────────
# Token payload model
# ──────────────────────────────────────────────────────────────────────────────

class CurrentUser(BaseModel):
    """
    Identity decoded directly from the JWT — no DB call required.
    Use `get_db_user` when you need the full User row (plan, quotas, etc.).
    """
    email: str
    name:  Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────────────────────────────────────

def _password_bytes(plain: str) -> bytes:
    return plain.encode('utf-8')[:72].decode('utf-8', errors='ignore').encode('utf-8')


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_password_bytes(plain), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_password_bytes(plain), hashed.encode('utf-8'))


# ──────────────────────────────────────────────────────────────────────────────
# Token creation
# ──────────────────────────────────────────────────────────────────────────────

def create_access_token(email: str, name: Optional[str], user_id: str) -> str:
    """Issue a signed JWT valid for _TOKEN_EXPIRE_DAYS days."""
    settings = get_settings()
    now      = datetime.now(timezone.utc)
    payload  = {
        "sub":   user_id,
        "email": email,
        "name":  name,
        "iat":   now,
        "exp":   now + timedelta(days=_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _decode_bearer(token: str) -> CurrentUser:
    """Decode and validate a raw bearer token string. Raises 401 on any failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        logger.warning("jwt_verification_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(email=email, name=payload.get("name"))


# ──────────────────────────────────────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """
    Require a valid Authorization: Bearer <token> header.
    Raises 401 if the header is absent or the token is invalid/expired.
    """
    return _decode_bearer(credentials.credentials)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
) -> CurrentUser:
    """
    Like get_current_user but falls back to a guest identity when no token is
    provided, instead of raising 401.

    Used by the chat endpoint so the frontend works without login during
    development.  When a token IS provided it is validated normally — an
    invalid/expired token still returns 401.
    """
    if credentials is None:
        return CurrentUser(email=GUEST_EMAIL, name="Dev Guest")
    return _decode_bearer(credentials.credentials)


async def get_db_user(
    current_user: CurrentUser = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
) -> User:
    """
    Load the full User row for the authenticated caller.
    Creates the user row on first login if it doesn't exist.
    Safe to use on all non-SSE endpoints.
    """
    result = await db.execute(select(User).where(User.email == current_user.email))
    user   = result.scalar_one_or_none()

    if user is None:
        user = User(email=current_user.email, name=current_user.name)
        db.add(user)
        await db.flush()
        logger.info("user_auto_created", email=current_user.email)

    return user


async def get_admin_user(
    user: User = Depends(get_db_user),
) -> User:
    """
    Require the authenticated user to have is_admin = True.
    Raises 403 otherwise.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
