from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from .user import User


class Lawyer(Base, TimestampMixin):
    __tablename__ = "lawyers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    name:                 Mapped[str]            = mapped_column(Text, nullable=False)
    email:                Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    phone:                Mapped[Optional[str]]  = mapped_column(String(20), nullable=True)
    bar_number:           Mapped[Optional[str]]  = mapped_column(String(50), nullable=True, unique=True)
    specializations:      Mapped[List[Any]]      = mapped_column(JSONB, nullable=False, default=list)
    experience_years:     Mapped[int]            = mapped_column(Integer, nullable=False, default=0)
    fee_per_hour:         Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    fee_per_consultation: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    location:             Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    bio:                  Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    profile_image_url:    Mapped[Optional[str]]  = mapped_column(Text, nullable=True)
    is_verified:          Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    is_available:         Mapped[bool]           = mapped_column(Boolean, nullable=False, default=True)
    rating:               Mapped[Decimal]        = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("0.00"))
    total_reviews:        Mapped[int]            = mapped_column(Integer, nullable=False, default=0)

    reviews: Mapped[List["LawyerReview"]] = relationship(
        "LawyerReview", back_populates="lawyer", cascade="all, delete-orphan", lazy="raise"
    )

    def __repr__(self) -> str:
        return f"<Lawyer name={self.name!r} location={self.location!r}>"


class LawyerReview(Base, TimestampMixin):
    __tablename__ = "lawyer_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    lawyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating:  Mapped[int]           = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    lawyer: Mapped["Lawyer"] = relationship("Lawyer", back_populates="reviews", lazy="raise")

    def __repr__(self) -> str:
        return f"<LawyerReview lawyer_id={self.lawyer_id} rating={self.rating}>"
