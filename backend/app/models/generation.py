"""Generation model — core AI output."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Generation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "generations"

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )

    # Input
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Parsed Architecture
    architecture: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("generations.id"), nullable=True, index=True
    )

    # Status: pending → parsing → generating → validating → estimating → completed / failed
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)

    # Validation
    validation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # LLM Metadata
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="generations")
    files = relationship("GeneratedFile", back_populates="generation", cascade="all, delete-orphan")
    diagram = relationship("Diagram", back_populates="generation", uselist=False, cascade="all, delete-orphan")
    cost_estimate = relationship("CostEstimate", back_populates="generation", uselist=False, cascade="all, delete-orphan")
