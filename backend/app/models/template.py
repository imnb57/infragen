"""Template model."""

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Template(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cloud_provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    architecture: Mapped[dict] = mapped_column(JSONB, nullable=False)
    complexity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tenant_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=True
    )
