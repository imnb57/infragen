"""Generated file model — IaC code output."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class GeneratedFile(Base, UUIDMixin):
    __tablename__ = "generated_files"

    generation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("generations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(30), nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False, default="hcl")
    storage_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(
        nullable=False,
        default="now()",
        server_default="now()",
    )

    # Relationships
    generation = relationship("Generation", back_populates="files")
