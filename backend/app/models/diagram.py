"""Diagram model."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Diagram(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "diagrams"

    generation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("generations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nodes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    edges: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    groups: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    layout_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    svg_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    png_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    generation = relationship("Generation", back_populates="diagram")
