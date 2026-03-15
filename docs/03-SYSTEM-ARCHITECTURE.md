# InfraGen — System Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Web App  │  │   CLI    │  │ VS Code  │  │  API Clients │    │
│  │ (React)  │  │  (Node)  │  │ Extension│  │  (REST/gRPC) │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
└───────┼──────────────┼──────────────┼───────────────┼───────────┘
        │              │              │               │
        └──────────────┴──────┬───────┴───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   API Gateway      │
                    │   (Kong / AWS ALB) │
                    │   Rate Limiting    │
                    │   Auth (JWT/OIDC)  │
                    └─────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐   ┌────────▼────────┐   ┌───────▼────────┐
│  Core API     │   │  AI Orchestrator│   │  Async Workers │
│  (FastAPI)    │   │  (FastAPI)      │   │  (Celery)      │
│               │   │                 │   │                │
│  • Projects   │   │  • NL Parser    │   │  • IaC Gen     │
│  • Templates  │   │  • LLM Router   │   │  • Cost Calc   │
│  • Versions   │   │  • Prompt Mgmt  │   │  • Diagram Gen │
│  • Teams/Orgs │   │  • Validation   │   │  • Doc Gen     │
│  • RBAC       │   │  • Context Mgmt │   │  • Policy Scan │
└───────┬───────┘   └────────┬────────┘   └───────┬────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
   │ PostgreSQL  │    │   Redis     │    │  S3 / Blob  │
   │             │    │             │    │  Storage    │
   │ • Projects  │    │ • Cache     │    │ • IaC files │
   │ • Users     │    │ • Sessions  │    │ • Diagrams  │
   │ • Versions  │    │ • Queue     │    │ • Templates │
   │ • Audit Log │    │ • Rate Lim  │    │ • Exports   │
   └─────────────┘    └─────────────┘    └─────────────┘
```

---

## 2. Component Deep Dive

### 2.1 Frontend (Web Application)

**Tech Stack**: React 18 + TypeScript + Vite + TailwindCSS

```
frontend/
├── src/
│   ├── app/                    # App shell, routing, providers
│   ├── features/
│   │   ├── chat/               # NL conversation interface
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── useChatStream.ts  # SSE streaming hook
│   │   ├── diagram/            # Architecture diagram viewer/editor
│   │   │   ├── DiagramCanvas.tsx  # React Flow / D3 canvas
│   │   │   ├── CloudIcons.tsx     # AWS/Azure/GCP icon registry
│   │   │   ├── NodeEditor.tsx     # Edit component properties
│   │   │   └── DiagramDiff.tsx    # Visual version diff
│   │   ├── code/               # IaC code viewer/editor
│   │   │   ├── CodeEditor.tsx     # Monaco editor
│   │   │   ├── FileTree.tsx
│   │   │   └── ValidationPanel.tsx
│   │   ├── cost/               # Cost estimation dashboard
│   │   │   ├── CostBreakdown.tsx
│   │   │   ├── CostComparison.tsx # Multi-cloud comparison
│   │   │   └── BudgetAlert.tsx
│   │   ├── governance/         # Policy & approval workflows
│   │   ├── docs/               # Generated documentation viewer
│   │   └── settings/           # Org, team, project settings
│   ├── shared/
│   │   ├── components/         # Design system
│   │   ├── hooks/
│   │   ├── api/                # API client (React Query)
│   │   └── stores/             # Zustand stores
│   └── types/
```

**Key UI Pattern**: Split-pane layout
```
┌──────────────────────────────────────────────────┐
│  Org > Project > Version v2.3                    │
├──────────┬───────────────────┬───────────────────┤
│          │                   │                   │
│  Chat    │   Diagram View    │   Code / Cost /   │
│  Panel   │   (Interactive)   │   Docs Panel      │
│          │                   │   (Tabbed)         │
│  ┌────┐  │   ┌───┐   ┌───┐  │                   │
│  │User│  │   │ALB│──▶│ECS│  │   main.tf         │
│  │ hi │  │   └───┘   └─┬─┘  │   variables.tf    │
│  │    │  │          ┌───▼──┐ │   outputs.tf      │
│  │ AI │  │          │ RDS  │ │                   │
│  │resp│  │          └──────┘ │   Cost: $487/mo   │
│  └────┘  │                   │                   │
├──────────┴───────────────────┴───────────────────┤
│  Validation: ✅ 0 errors  ⚠️ 2 warnings          │
└──────────────────────────────────────────────────┘
```

### 2.2 Backend — Core API (FastAPI + Python)

**Why Python/FastAPI**:
- Best LLM ecosystem (LangChain, LlamaIndex, OpenAI SDK)
- Async-native for streaming responses
- Fast development, great for AI-heavy workloads

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings (Pydantic BaseSettings)
│   ├── api/
│   │   ├── v1/
│   │   │   ├── projects.py     # Project CRUD
│   │   │   ├── generations.py  # Trigger AI generation
│   │   │   ├── diagrams.py     # Diagram endpoints
│   │   │   ├── costs.py        # Cost estimation
│   │   │   ├── governance.py   # Policies, approvals
│   │   │   ├── versions.py     # Version management
│   │   │   ├── templates.py    # Template library
│   │   │   ├── orgs.py         # Multi-tenant: orgs/teams
│   │   │   └── auth.py         # Authentication
│   │   └── deps.py             # Dependency injection
│   ├── core/
│   │   ├── auth/
│   │   │   ├── jwt.py          # JWT token handling
│   │   │   ├── rbac.py         # Role-based access control
│   │   │   └── oauth.py        # Google/GitHub SSO
│   │   ├── multi_tenant.py     # Tenant context, isolation
│   │   └── security.py         # Rate limiting, input sanitization
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── org.py
│   │   ├── project.py
│   │   ├── version.py
│   │   ├── generation.py
│   │   └── audit_log.py
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/
│   │   ├── generation_service.py
│   │   ├── version_service.py
│   │   ├── cost_service.py
│   │   ├── diagram_service.py
│   │   └── governance_service.py
│   └── db/
│       ├── session.py          # DB session management
│       └── migrations/         # Alembic migrations
```

### 2.3 AI Orchestrator

This is the brain of InfraGen — the most critical component.

```
ai/
├── orchestrator.py             # Main orchestration pipeline
├── llm/
│   ├── router.py               # Route to best model per task
│   ├── providers/
│   │   ├── openai_provider.py  # GPT-4o, GPT-4o-mini
│   │   ├── anthropic_provider.py # Claude 3.5 Sonnet
│   │   └── local_provider.py   # Ollama / vLLM for self-hosted
│   ├── prompts/
│   │   ├── system_prompts/
│   │   │   ├── iac_generator.py    # Terraform/Pulumi/CDK generation
│   │   │   ├── diagram_generator.py # Architecture diagram
│   │   │   ├── cost_analyzer.py     # Cost estimation
│   │   │   ├── doc_generator.py     # Documentation
│   │   │   └── refiner.py          # Iterative refinement
│   │   └── templates/              # Prompt templates (Jinja2)
│   └── context/
│       ├── cloud_knowledge.py      # Cloud service knowledge base
│       ├── pricing_data.py         # Pricing embeddings
│       └── best_practices.py       # Well-Architected Framework
├── generators/
│   ├── terraform_gen.py        # Terraform HCL generation
│   ├── pulumi_gen.py           # Pulumi (Python/TypeScript)
│   ├── cdk_gen.py              # AWS CDK generation
│   ├── bicep_gen.py            # Azure Bicep generation
│   └── base_gen.py             # Abstract base generator
├── validators/
│   ├── terraform_validator.py  # terraform validate + tflint
│   ├── security_scanner.py     # Checkov / tfsec / Trivy
│   ├── policy_checker.py       # OPA/Rego policy evaluation
│   └── cost_validator.py       # Budget constraint checking
├── diagram/
│   ├── diagram_engine.py       # Diagram generation engine
│   ├── layout_solver.py        # Auto-layout algorithm
│   ├── icon_registry.py        # Cloud provider icon sets
│   └── exporters/
│       ├── svg_exporter.py
│       ├── mermaid_exporter.py
│       └── drawio_exporter.py
└── cost/
    ├── pricing_engine.py       # Cost calculation engine
    ├── providers/
    │   ├── aws_pricing.py      # AWS Pricing API
    │   ├── azure_pricing.py    # Azure Retail Pricing API
    │   └── gcp_pricing.py      # GCP Cloud Billing API
    └── optimizer.py            # Cost optimization suggestions
```

### AI Pipeline Flow

```
User Input (Natural Language)
        │
        ▼
┌─────────────────┐
│  Intent Parser   │  "I need a 3-tier app on AWS"
│  (LLM Call #1)   │  → {type: "3-tier", cloud: "aws", components: [...]}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Architecture    │  Resolves components to specific cloud services
│  Resolver        │  → {services: ["ALB", "ECS", "RDS", "ElastiCache"]}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  IaC Generator   │  Generates Terraform/Pulumi/CDK
│  (LLM Call #2)   │  Uses cloud-specific prompts + best practices
│  + Validator     │  → Runs tflint, checkov, terraform validate
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Diagram Engine  │  Generates architecture diagram
│                  │  → SVG with official cloud icons
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cost Engine     │  Calculates cost from cloud pricing APIs
│                  │  → Per-service breakdown, total monthly
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Doc Generator   │  Generates ADR, README, runbook
│  (LLM Call #3)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Response        │  Streams back: diagram + code + cost + docs
│  Assembler       │  via SSE to frontend
└─────────────────┘
```

---

## 3. Data Model (Core Entities)

```sql
-- Multi-tenancy
organizations (id, name, slug, plan, settings, created_at)
teams (id, org_id, name, settings)
users (id, email, name, auth_provider, created_at)
org_memberships (user_id, org_id, role) -- owner, admin, member
team_memberships (user_id, team_id, role)

-- Core domain
projects (id, org_id, team_id, name, description, cloud_providers[], default_iac_tool, created_by, created_at)
versions (id, project_id, version_number, status, parent_version_id, created_by, created_at)
  -- status: draft, in_review, approved, deployed, archived

-- Generation artifacts (per version)
architectures (id, version_id, components JSONB, connections JSONB, diagram_svg, diagram_data JSONB)
iac_files (id, version_id, file_path, content, iac_tool, cloud_provider, validated, errors JSONB)
cost_estimates (id, version_id, cloud_provider, region, monthly_total, breakdown JSONB, assumptions JSONB)
documents (id, version_id, doc_type, title, content_md, generated_at)
  -- doc_type: adr, readme, runbook, compliance

-- Conversation
conversations (id, version_id, created_at)
messages (id, conversation_id, role, content, artifacts JSONB, created_at)
  -- role: user, assistant, system

-- Governance
policies (id, org_id, name, policy_type, rules JSONB, enforcement) -- warn, block
  -- policy_type: cost_limit, service_allowlist, region_restriction, security_baseline
approval_requests (id, version_id, requested_by, status, reviewers[], approved_by, created_at)
audit_logs (id, org_id, user_id, action, resource_type, resource_id, details JSONB, created_at)

-- Templates
templates (id, org_id, name, description, category, architecture JSONB, is_public, usage_count)
  -- category: web_app, microservices, data_pipeline, ml_platform, static_site
```

---

## 4. Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Language** | Python (backend), TypeScript (frontend) | Best AI/ML ecosystem, fast dev |
| **API Framework** | FastAPI | Async, streaming (SSE), auto OpenAPI docs |
| **Database** | PostgreSQL + JSONB | Relational + flexible JSON for components |
| **Cache/Queue** | Redis | Session cache, Celery broker, rate limiting |
| **Task Queue** | Celery | Heavy AI tasks async, retry logic |
| **LLM** | OpenAI GPT-4o (primary), Claude (fallback) | Best code generation quality |
| **Diagram Rendering** | Server: Graphviz + custom SVG; Client: React Flow | Standard layouts + interactive editing |
| **IaC Validation** | terraform CLI, tflint, checkov, OPA | Industry standard toolchain |
| **Auth** | JWT + OAuth2 (Google, GitHub SSO) | Standard, supports enterprise SSO later |
| **Storage** | S3-compatible (MinIO for dev) | Files, diagrams, exports |
| **Deployment** | Docker + Kubernetes (EKS/GKE) | Scale AI workers independently |
| **CI/CD** | GitHub Actions | Standard, our users use it too |

---

## 5. Infrastructure (InfraGen's Own Infra)

### Production Environment
```
┌─────────────────────────────────────────────┐
│                  AWS                         │
│                                             │
│  CloudFront CDN ──▶ S3 (React SPA)         │
│                                             │
│  ALB ──▶ ECS Fargate                       │
│          ├── Core API (2-8 tasks)           │
│          ├── AI Orchestrator (2-16 tasks)   │
│          └── Celery Workers (2-32 tasks)    │
│                                             │
│  RDS PostgreSQL (Multi-AZ)                  │
│  ElastiCache Redis (Cluster)                │
│  S3 (artifacts, diagrams, exports)          │
│                                             │
│  Secrets Manager (API keys, LLM keys)       │
│  CloudWatch (logs, metrics, alarms)         │
│  WAF (API protection)                       │
└─────────────────────────────────────────────┘
```

### Development Environment
```
docker-compose.yml:
  - frontend (Vite dev server)
  - backend (FastAPI + uvicorn)
  - postgres
  - redis
  - minio (S3-compatible)
  - celery-worker
  - celery-beat
```

---

## 6. Security Architecture

| Layer | Control |
|---|---|
| **Network** | WAF, VPC isolation, private subnets for DB |
| **Auth** | JWT with short expiry, refresh tokens, OAuth2/OIDC |
| **Authorization** | RBAC (owner/admin/member/viewer per org+team) |
| **Tenant Isolation** | Row-level security in PostgreSQL, org_id on every query |
| **Secrets** | AWS Secrets Manager, never in code or DB |
| **API Security** | Rate limiting (per tenant), input validation (Pydantic), CORS |
| **LLM Security** | Prompt injection defense, output sanitization, no PII to LLM |
| **Data** | Encryption at rest (AES-256), in transit (TLS 1.3) |
| **Audit** | Every mutation logged with user, timestamp, diff |
| **Compliance** | SOC2 Type II readiness from day 1 |

---

## 7. Scaling Strategy

| Component | Scaling Trigger | Strategy |
|---|---|---|
| Core API | CPU > 70% | Horizontal auto-scale (2-8) |
| AI Orchestrator | Request queue depth | Horizontal (2-16), GPU instances optional |
| Celery Workers | Queue length | Horizontal (2-32), spot instances |
| PostgreSQL | Connections > 80% | Read replicas, then vertical scale |
| Redis | Memory > 80% | Cluster mode, add shards |
| LLM Calls | Rate limits | Multi-provider failover, caching |
