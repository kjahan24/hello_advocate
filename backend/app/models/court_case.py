from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from .user import User


class CourtCase(Base, TimestampMixin):
    __tablename__ = "court_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_title:  Mapped[str]           = mapped_column(Text,        nullable=False)
    case_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    court_name:  Mapped[str]           = mapped_column(Text,        nullable=False)
    case_type:   Mapped[str]           = mapped_column(String(50),  nullable=False, default="other")
    next_date:   Mapped[date]          = mapped_column(Date,        nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text,        nullable=True)
    status:      Mapped[str]           = mapped_column(String(20),  nullable=False, default="active")
    updated_at:  Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", lazy="raise")

    def __repr__(self) -> str:
        return f"<CourtCase title={self.case_title!r} next_date={self.next_date}>"
