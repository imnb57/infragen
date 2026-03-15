"""Cost estimate model."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class CostEstimate(Base, UUIDMixin):
    __tablename__ = "cost_estimates"

    generation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("generations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_monthly: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    breakdown: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    optimization_hints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    assumptions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pricing_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[str] = mapped_column(
        nullable=False, default="now()", server_default="now()"
    )

    # Relationships
    generation = relationship("Generation", back_populates="cost_estimate")
