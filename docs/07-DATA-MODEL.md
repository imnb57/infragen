# InfraGen — Data Model & Database Schema

## 1. Entity Relationship Overview

```
┌────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Tenant   │ 1─N │    User      │ 1─N │    Project       │
│            │     │              │     │                  │
│ id         │     │ id           │     │ id               │
│ name       │     │ tenant_id    │     │ user_id          │
│ plan       │     │ email        │     │ tenant_id        │
│ settings   │     │ role         │     │ name             │
└────────────┘     └──────────────┘     │ cloud_provider   │
                                        │ iac_tool         │
                                        └────────┬─────────┘
                                                 │ 1
                                                 │
                                                 │ N
                                        ┌────────┴─────────┐
                                        │   Generation     │
                                        │                  │
                                        │ id               │
                                        │ project_id       │
                                        │ conversation_id  │
                                        │ prompt           │
                                        │ status           │
                                        │ architecture     │
                                        │ version          │
                                        └────────┬─────────┘
                                                 │ 1
                                                 │
                           ┌─────────────────────┼────────────────────┐
                           │                     │                    │
                           │ N                   │ N                  │ 1
                  ┌────────┴───────┐   ┌─────────┴──────┐   ┌───────┴──────┐
                  │  GeneratedFile │   │   DiagramData  │   │ CostEstimate │
                  │                │   │                │   │              │
                  │ id             │   │ id             │   │ id           │
                  │ generation_id  │   │ generation_id  │   │ generation_id│
                  │ file_path      │   │ nodes_json     │   │ total_monthly│
                  │ content        │   │ edges_json     │   │ breakdown    │
                  │ file_type      │   │ groups_json    │   │ currency     │
                  └────────────────┘   │ svg_url        │   └──────────────┘
                                       └────────────────┘
```

---

## 2. SQL Schema (PostgreSQL)

### Core Tables

```sql
-- ============================================
-- TENANTS & USERS
-- ============================================

CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    plan            VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, pro, team, enterprise
    settings        JSONB NOT NULL DEFAULT '{}',
    
    -- Usage tracking
    generation_count_month  INTEGER NOT NULL DEFAULT 0,
    generation_limit_month  INTEGER NOT NULL DEFAULT 50,  -- based on plan
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    email           VARCHAR(320) NOT NULL UNIQUE,
    password_hash   VARCHAR(255),          -- NULL for OAuth-only users
    name            VARCHAR(255) NOT NULL,
    avatar_url      VARCHAR(500),
    role            VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member
    
    -- OAuth
    github_id       VARCHAR(100),
    google_id       VARCHAR(100),
    
    -- Preferences
    default_cloud   VARCHAR(20) DEFAULT 'aws',
    default_iac     VARCHAR(20) DEFAULT 'terraform',
    
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_github ON users(github_id) WHERE github_id IS NOT NULL;


-- ============================================
-- PROJECTS
-- ============================================

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    cloud_provider  VARCHAR(20) NOT NULL DEFAULT 'aws',     -- aws, azure, gcp
    iac_tool        VARCHAR(30) NOT NULL DEFAULT 'terraform', -- terraform, pulumi, cdk
    region          VARCHAR(50) DEFAULT 'us-east-1',
    tags            VARCHAR(100)[] DEFAULT '{}',
    settings        JSONB NOT NULL DEFAULT '{}',
    
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_tenant ON projects(tenant_id);
CREATE INDEX idx_projects_user ON projects(user_id);


-- ============================================
-- CONVERSATIONS (Chat Threads)
-- ============================================

CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           VARCHAR(500),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_project ON conversations(project_id);


CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content         TEXT NOT NULL,
    generation_id   UUID,                   -- Links to the generation this message triggered
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);


-- ============================================
-- GENERATIONS (Core Output)
-- ============================================

CREATE TABLE generations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    user_id         UUID NOT NULL REFERENCES users(id),
    
    -- Input
    prompt          TEXT NOT NULL,
    options         JSONB NOT NULL DEFAULT '{}',
    
    -- Parsed Architecture
    architecture    JSONB,  -- Structured architecture spec
    
    -- Versioning
    version         INTEGER NOT NULL DEFAULT 1,
    parent_id       UUID REFERENCES generations(id),  -- Previous version
    
    -- Status
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending → parsing → generating → validating → estimating → completed / failed
    
    -- Validation Results
    validation      JSONB,  -- { errors: [], warnings: [], passed: true/false }
    
    -- Metadata
    llm_model       VARCHAR(100),
    llm_tokens_in   INTEGER,
    llm_tokens_out  INTEGER,
    duration_ms     INTEGER,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_generations_project ON generations(project_id);
CREATE INDEX idx_generations_user ON generations(user_id);
CREATE INDEX idx_generations_status ON generations(status);
CREATE INDEX idx_generations_parent ON generations(parent_id);


-- ============================================
-- GENERATED FILES (IaC Code Output)
-- ============================================

CREATE TABLE generated_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id   UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    
    file_path       VARCHAR(500) NOT NULL,        -- e.g., "main.tf", "modules/vpc/main.tf"
    content         TEXT NOT NULL,
    file_type       VARCHAR(30) NOT NULL,          -- terraform, pulumi_python, cdk_typescript
    language        VARCHAR(30) NOT NULL DEFAULT 'hcl',  -- hcl, python, typescript, yaml
    
    -- S3 storage for large files
    storage_url     VARCHAR(500),
    size_bytes      INTEGER,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_generated_files_generation ON generated_files(generation_id);


-- ============================================
-- DIAGRAMS
-- ============================================

CREATE TABLE diagrams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id   UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    
    -- Structured diagram data
    nodes           JSONB NOT NULL DEFAULT '[]',
    edges           JSONB NOT NULL DEFAULT '[]',
    groups          JSONB NOT NULL DEFAULT '[]',
    layout_config   JSONB NOT NULL DEFAULT '{}',
    
    -- Rendered output
    svg_url         VARCHAR(500),
    png_url         VARCHAR(500),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_diagrams_generation ON diagrams(generation_id);


-- ============================================
-- COST ESTIMATES
-- ============================================

CREATE TABLE cost_estimates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id   UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    
    total_monthly   DECIMAL(12, 2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    confidence      VARCHAR(10) NOT NULL DEFAULT 'medium',
    
    breakdown       JSONB NOT NULL DEFAULT '[]',
    -- [{ service, label, monthly, note, category }]
    
    optimization_hints JSONB NOT NULL DEFAULT '[]',
    -- [{ text, potential_savings }]
    
    assumptions     JSONB NOT NULL DEFAULT '[]',
    
    pricing_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    region          VARCHAR(50) NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cost_estimates_generation ON cost_estimates(generation_id);


-- ============================================
-- TEMPLATES (Starter Templates)
-- ============================================

CREATE TABLE templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name            VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL,
    category        VARCHAR(100) NOT NULL,  -- 'web-app', 'data-pipeline', 'serverless'
    cloud_provider  VARCHAR(20) NOT NULL,
    icon            VARCHAR(100),
    
    -- Template definition
    prompt_template TEXT NOT NULL,           -- Pre-filled prompt
    architecture    JSONB NOT NULL,          -- Default architecture spec
    
    -- Metadata
    complexity      VARCHAR(20) NOT NULL DEFAULT 'medium',  -- simple, medium, complex
    estimated_cost  DECIMAL(12, 2),
    popularity      INTEGER NOT NULL DEFAULT 0,
    
    is_public       BOOLEAN NOT NULL DEFAULT TRUE,
    tenant_id       UUID REFERENCES tenants(id),  -- NULL = global template
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_cloud ON templates(cloud_provider);


-- ============================================
-- AUDIT LOG
-- ============================================

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID REFERENCES users(id),
    
    action          VARCHAR(100) NOT NULL,    -- 'project.created', 'generation.completed'
    resource_type   VARCHAR(50) NOT NULL,     -- 'project', 'generation'
    resource_id     UUID,
    
    details         JSONB NOT NULL DEFAULT '{}',
    ip_address      INET,
    user_agent      VARCHAR(500),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
-- Partition by month for large tenants (later optimization)


-- ============================================
-- API KEYS (for CLI / CI integration)
-- ============================================

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    
    name            VARCHAR(255) NOT NULL,
    key_hash        VARCHAR(255) NOT NULL,  -- Store hashed, never plaintext
    key_prefix      VARCHAR(10) NOT NULL,   -- First 8 chars for identification "ig_abc12..."
    
    scopes          VARCHAR(100)[] DEFAULT '{generate,read}',
    
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

---

## 3. SQLAlchemy Models (Python)

```python
# backend/app/models/base.py
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# backend/app/models/project.py
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    cloud_provider = Column(String(20), nullable=False, default="aws")
    iac_tool = Column(String(30), nullable=False, default="terraform")
    region = Column(String(50), default="us-east-1")
    tags = Column(ARRAY(String(100)), default=[])
    settings = Column(JSONB, nullable=False, default={})
    is_archived = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    user = relationship("User", back_populates="projects")
    generations = relationship("Generation", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
```

---

## 4. Pydantic Schemas (API Request/Response)

```python
# backend/app/schemas/generation.py

from pydantic import BaseModel, Field
from enum import Enum

class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"

class IaCTool(str, Enum):
    TERRAFORM = "terraform"
    PULUMI = "pulumi"
    CDK = "cdk"
    CLOUDFORMATION = "cloudformation"

class GenerateRequest(BaseModel):
    project_id: UUID
    message: str = Field(..., min_length=10, max_length=5000)
    conversation_id: UUID | None = None
    options: GenerateOptions

class GenerateOptions(BaseModel):
    cloud: CloudProvider = CloudProvider.AWS
    iac_tool: IaCTool = IaCTool.TERRAFORM
    region: str = "us-east-1"
    include_cost: bool = True
    include_diagram: bool = True

class GenerationResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    version: int
    architecture: dict | None
    files: list[GeneratedFileResponse]
    diagram: DiagramResponse | None
    cost_estimate: CostEstimateResponse | None
    validation: ValidationResponse | None
    created_at: datetime

class CostEstimateResponse(BaseModel):
    total_monthly: float
    currency: str
    breakdown: list[CostLineItem]
    optimization_hints: list[str]

class CostLineItem(BaseModel):
    service: str
    label: str
    monthly: float
    note: str
    category: str  # compute, storage, network, database, other
```

---

## 5. Multi-Tenant Data Isolation

### Row-Level Security (RLS)
```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their tenant's data
CREATE POLICY tenant_isolation ON projects
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON generations
    USING (project_id IN (
        SELECT id FROM projects 
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));
```

### Application-Level Enforcement
```python
# backend/app/api/deps.py

async def get_tenant_db(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AsyncSession:
    """Set the tenant context for RLS policies."""
    await db.execute(
        text("SET app.current_tenant_id = :tid"),
        {"tid": str(current_user.tenant_id)}
    )
    return db
```

---

## 6. Redis Usage Plan

| Use Case | Key Pattern | TTL |
|---|---|---|
| Session/JWT blocklist | `blocklist:{jti}` | Token expiry |
| Rate limiting | `ratelimit:{tenant_id}:{endpoint}` | 1 minute |
| Generation queue status | `gen:{generation_id}:status` | 1 hour |
| SSE channel | `sse:{generation_id}` (Pub/Sub) | — |
| Pricing cache | `pricing:{cloud}:{service}:{region}` | 24 hours |
| Template cache | `template:{id}` | 1 hour |

---

## 7. Migration Strategy

```bash
# Using Alembic
cd backend
alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head

# Naming convention for migrations:
# 001_initial_schema.py
# 002_add_api_keys.py
# 003_add_governance_tables.py
```

### Migration Rules
1. All migrations must be **forward-compatible** (can run while old code is still serving)
2. Never rename columns in production — add new, migrate data, drop old
3. Add indexes concurrently: `CREATE INDEX CONCURRENTLY`
4. Test migrations on a copy of production data before deploying
