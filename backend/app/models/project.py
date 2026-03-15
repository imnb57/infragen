"""Project model."""

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cloud_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="aws")
    iac_tool: Mapped[str] = mapped_column(String(30), nullable=False, default="terraform")
    region: Mapped[str] = mapped_column(String(50), nullable=False, default="us-east-1")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    user = relationship("User", back_populates="projects")
    generations = relationship("Generation", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
