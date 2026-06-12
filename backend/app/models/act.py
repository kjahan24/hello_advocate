import uuid
from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from .section import Section


class Act(Base, TimestampMixin):
    __tablename__ = "acts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    act_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_bn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_repealed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_text_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_text_bn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)

    sections: Mapped[List["Section"]] = relationship(
        "Section", back_populates="act", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Act act_id={self.act_id!r} title={self.title_en[:40]!r}>"
