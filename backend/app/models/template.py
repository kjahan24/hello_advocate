from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from .user import User


class DocumentTemplate(Base, TimestampMixin):
    __tablename__ = "document_templates"

    id:          Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    title:       Mapped[str]           = mapped_column(Text, nullable=False)
    title_en:    Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category:    Mapped[str]           = mapped_column(String(50), nullable=False, default="other")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fields:      Mapped[List[Any]]     = mapped_column(JSONB, nullable=False, default=list)
    is_pro:      Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    usage_count: Mapped[int]           = mapped_column(Integer, nullable=False, default=0)

    generated_documents: Mapped[List["GeneratedDocument"]] = relationship(
        "GeneratedDocument",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<DocumentTemplate title={self.title!r} category={self.category!r}>"


class GeneratedDocument(Base, TimestampMixin):
    __tablename__ = "generated_documents"

    id:                Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:           Mapped[uuid.UUID]          = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    field_values:      Mapped[Dict[str, Any]]     = mapped_column(JSONB, nullable=False, default=dict)
    generated_content: Mapped[str]                = mapped_column(Text, nullable=False)

    user:     Mapped["User"]                       = relationship("User", lazy="raise")
    template: Mapped[Optional["DocumentTemplate"]] = relationship("DocumentTemplate", back_populates="generated_documents", lazy="raise")

    def __repr__(self) -> str:
        return f"<GeneratedDocument id={self.id} user_id={self.user_id}>"
