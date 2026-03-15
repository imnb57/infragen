"""User model."""

from sqlalchemy import Boolean, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")

    # OAuth
    github_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    google_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    # Preferences
    default_cloud: Mapped[str] = mapped_column(String(20), nullable=False, default="aws")
    default_iac: Mapped[str] = mapped_column(String(20), nullable=False, default="terraform")

    # Status
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
