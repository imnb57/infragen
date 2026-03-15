"""Initial schema — all core tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("generation_count_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generation_limit_month", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("github_id", sa.String(100), nullable=True, unique=True),
        sa.Column("google_id", sa.String(100), nullable=True, unique=True),
        sa.Column("default_cloud", sa.String(20), nullable=False, server_default="aws"),
        sa.Column("default_iac", sa.String(20), nullable=False, server_default="terraform"),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_users_tenant", "users", ["tenant_id"])

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cloud_provider", sa.String(20), nullable=False, server_default="aws"),
        sa.Column("iac_tool", sa.String(30), nullable=False, server_default="terraform"),
        sa.Column("region", sa.String(50), nullable=False, server_default="us-east-1"),
        sa.Column("tags", postgresql.ARRAY(sa.String(100)), server_default="{}"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_projects_tenant", "projects", ["tenant_id"])
    op.create_index("idx_projects_user", "projects", ["user_id"])

    # Conversations
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_conversations_project", "conversations", ["project_id"])

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generation_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_messages_conversation", "messages", ["conversation_id"])

    # Generations
    op.create_table(
        "generations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("architecture", postgresql.JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("generations.id"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("validation", postgresql.JSONB(), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("llm_tokens_in", sa.Integer(), nullable=True),
        sa.Column("llm_tokens_out", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_generations_project", "generations", ["project_id"])
    op.create_index("idx_generations_user", "generations", ["user_id"])
    op.create_index("idx_generations_status", "generations", ["status"])
    op.create_index("idx_generations_parent", "generations", ["parent_id"])

    # Generated Files
    op.create_table(
        "generated_files",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("generation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(30), nullable=False),
        sa.Column("language", sa.String(30), nullable=False, server_default="hcl"),
        sa.Column("storage_url", sa.String(500), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_generated_files_generation", "generated_files", ["generation_id"])

    # Diagrams
    op.create_table(
        "diagrams",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("generation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nodes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("edges", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("groups", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("layout_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("svg_url", sa.String(500), nullable=True),
        sa.Column("png_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_diagrams_generation", "diagrams", ["generation_id"])

    # Cost Estimates
    op.create_table(
        "cost_estimates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("generation_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("generations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_monthly", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("confidence", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("breakdown", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("optimization_hints", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pricing_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_cost_estimates_generation", "cost_estimates", ["generation_id"])

    # Templates
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("cloud_provider", sa.String(20), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("architecture", postgresql.JSONB(), nullable=False),
        sa.Column("complexity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("popularity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_templates_category", "templates", ["category"])
    op.create_index("idx_templates_cloud", "templates", ["cloud_provider"])

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_audit_tenant", "audit_logs", ["tenant_id"])
    op.create_index("idx_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("templates")
    op.drop_table("cost_estimates")
    op.drop_table("diagrams")
    op.drop_table("generated_files")
    op.drop_table("generations")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("tenants")
