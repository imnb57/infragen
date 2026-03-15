# InfraGen — Engineering Execution Plan

## 1. Repository Structure (Monorepo)

```
infragen/
├── README.md
├── docker-compose.yml          # Local dev environment
├── docker-compose.prod.yml     # Production-like environment
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint, test, type-check
│       ├── deploy-staging.yml
│       └── deploy-prod.yml
│
├── frontend/                   # React SPA
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── public/
│   │   └── cloud-icons/        # AWS/Azure/GCP SVG icons
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   ├── features/
│   │   │   ├── auth/           # Login, signup, OAuth callback
│   │   │   ├── dashboard/      # Project list, recent activity
│   │   │   ├── workspace/      # Main workspace (chat + diagram + code)
│   │   │   │   ├── WorkspaceLayout.tsx
│   │   │   │   ├── ChatPanel.tsx
│   │   │   │   ├── DiagramPanel.tsx
│   │   │   │   ├── CodePanel.tsx
│   │   │   │   ├── CostPanel.tsx
│   │   │   │   └── ValidationPanel.tsx
│   │   │   ├── templates/      # Template gallery
│   │   │   └── settings/       # Account, billing
│   │   ├── shared/
│   │   │   ├── components/     # Button, Input, Modal, etc.
│   │   │   ├── hooks/
│   │   │   ├── api/            # API client, React Query hooks
│   │   │   └── stores/         # Zustand state stores
│   │   └── types/
│   └── tests/
│
├── backend/                    # FastAPI application
│   ├── pyproject.toml          # Dependencies (uv/poetry)
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── generations.py
│   │   │   │   ├── diagrams.py
│   │   │   │   ├── costs.py
│   │   │   │   └── templates.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── auth/
│   │   │   ├── security.py
│   │   │   └── exceptions.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── db/
│   │       ├── session.py
│   │       └── migrations/
│   └── tests/
│
├── ai/                         # AI orchestration (Python package)
│   ├── pyproject.toml
│   ├── infragen_ai/
│   │   ├── orchestrator.py     # Main pipeline
│   │   ├── llm/
│   │   │   ├── client.py       # LLM client wrapper
│   │   │   ├── prompts/        # Prompt templates
│   │   │   └── providers/      # OpenAI, Anthropic, local
│   │   ├── generators/
│   │   │   ├── terraform.py
│   │   │   └── base.py
│   │   ├── validators/
│   │   │   ├── terraform_validator.py
│   │   │   └── security_scanner.py
│   │   ├── diagram/
│   │   │   ├── engine.py
│   │   │   ├── icons.py
│   │   │   └── layout.py
│   │   ├── cost/
│   │   │   ├── engine.py
│   │   │   └── aws_pricing.py
│   │   └── knowledge/          # Cloud service knowledge base
│   │       ├── aws_services.json
│   │       └── patterns.json
│   └── tests/
│
├── shared/                     # Shared types/schemas
│   └── schemas/
│       ├── architecture.json   # Architecture component schema
│       └── generation.json     # Generation request/response schema
│
└── infra/                      # InfraGen's own infrastructure
    ├── docker/
    │   ├── Dockerfile.frontend
    │   ├── Dockerfile.backend
    │   └── Dockerfile.worker
    ├── terraform/              # InfraGen's own Terraform (dogfooding!)
    │   ├── main.tf
    │   ├── variables.tf
    │   └── modules/
    └── k8s/                    # Kubernetes manifests (later)
```

---

## 2. API Design (Key Endpoints)

### Authentication
```
POST   /api/v1/auth/signup          # Email/password signup
POST   /api/v1/auth/login           # Login → JWT
POST   /api/v1/auth/oauth/github    # GitHub OAuth callback
POST   /api/v1/auth/refresh         # Refresh token
GET    /api/v1/auth/me              # Current user
```

### Projects
```
GET    /api/v1/projects             # List user's projects
POST   /api/v1/projects             # Create project
GET    /api/v1/projects/:id         # Get project details
PUT    /api/v1/projects/:id         # Update project
DELETE /api/v1/projects/:id         # Delete project
GET    /api/v1/projects/:id/versions  # List versions
```

### Generation (Core)
```
POST   /api/v1/generate             # Start generation (SSE stream)
  Request: {
    project_id: string,
    message: string,           # "3-tier web app on AWS..."
    conversation_id?: string,  # For follow-up messages
    options: {
      cloud: "aws",
      iac_tool: "terraform",
      include_cost: true,
      include_diagram: true
    }
  }
  Response: SSE stream of events:
    - { type: "thinking", content: "Analyzing requirements..." }
    - { type: "architecture", data: { components: [...], connections: [...] } }
    - { type: "diagram", data: { svg: "...", metadata: {...} } }
    - { type: "code", data: { files: [{ path: "main.tf", content: "..." }] } }
    - { type: "validation", data: { errors: [], warnings: [...] } }
    - { type: "cost", data: { total: 487, currency: "USD", breakdown: [...] } }
    - { type: "done", data: { generation_id: "..." } }

POST   /api/v1/generate/:id/refine  # Refine existing generation
  Request: {
    message: "Add Redis cache and make it highly available"
  }
```

### Diagrams
```
GET    /api/v1/diagrams/:id         # Get diagram data
GET    /api/v1/diagrams/:id/svg     # Export as SVG
GET    /api/v1/diagrams/:id/png     # Export as PNG
```

### Cost
```
GET    /api/v1/costs/:generation_id         # Get cost estimate
POST   /api/v1/costs/:generation_id/what-if # What-if scenario
```

### Templates
```
GET    /api/v1/templates            # List templates
GET    /api/v1/templates/:id        # Get template details
POST   /api/v1/templates/:id/use    # Generate from template
```

### Export
```
GET    /api/v1/export/:generation_id/zip  # Download all files as ZIP
```

---

## 3. Core AI Prompt Strategy

### Intent Parsing Prompt (LLM Call #1)
```
System: You are an infrastructure architect. Parse the user's request into a 
structured architecture specification.

User: "I need a 3-tier web app on AWS with React, Node.js, PostgreSQL, 
       auto-scaling, and a CDN. Budget around $500/month."

Expected Output (JSON):
{
  "cloud": "aws",
  "pattern": "three_tier_web",
  "components": [
    {"type": "cdn", "service": "cloudfront", "config": {"origins": ["alb"]}},
    {"type": "load_balancer", "service": "alb", "config": {"scheme": "internet-facing"}},
    {"type": "compute", "service": "ecs_fargate", "config": {"cpu": 256, "memory": 512, "min": 2, "max": 8}},
    {"type": "database", "service": "rds_postgresql", "config": {"instance": "db.t3.micro", "multi_az": false}},
    {"type": "storage", "service": "s3", "config": {"purpose": "static_assets"}}
  ],
  "requirements": {
    "high_availability": false,
    "auto_scaling": true,
    "budget_monthly_usd": 500
  },
  "networking": {
    "vpc": true,
    "public_subnets": 2,
    "private_subnets": 2
  }
}
```

### Terraform Generation Prompt (LLM Call #2)
```
System: You are a senior Terraform engineer. Generate production-quality 
Terraform code for the given architecture specification.

Rules:
- Use Terraform 1.5+ syntax with required_providers block
- Follow HashiCorp best practices
- Use variables for all configurable values
- Include outputs for important values (endpoints, ARNs)
- Add meaningful resource names and tags
- Use data sources where appropriate
- Include security groups with least-privilege rules
- NEVER hardcode secrets, credentials, or account IDs
- Structure into logical files: main.tf, variables.tf, outputs.tf, 
  and optionally separate files per major component

Architecture Spec: {architecture_json}

Generate the complete Terraform configuration.
```

### Validation Pipeline
```
1. terraform fmt -check          # Format check
2. terraform init (with plugin cache)
3. terraform validate            # Syntax + semantic validation
4. tflint                        # Linting rules
5. checkov -f main.tf            # Security scanning
6. Custom rules (e.g., no public S3 buckets, encryption required)
```

---

## 4. Diagram Generation Approach

### Option A: LLM → Structured Data → Render (Recommended for MVP)

```
Architecture Spec (JSON)
        │
        ▼
┌─────────────────┐
│  Layout Engine   │  Assigns x,y coordinates using Dagre/ELK algorithm
│  (Dagre.js)     │  Groups by subnet/VPC/region
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SVG Renderer   │  Places official cloud icons at coordinates
│  (D3.js)        │  Draws connections with arrows
│                 │  Adds labels, legends
└────────┬────────┘
         │
         ▼
    SVG / React Flow nodes
```

### Icon Sources (All Free/Official)
- **AWS**: https://aws.amazon.com/architecture/icons/ (SVG)
- **Azure**: https://learn.microsoft.com/en-us/azure/architecture/icons/
- **GCP**: https://cloud.google.com/icons

### Diagram Data Structure
```json
{
  "nodes": [
    {
      "id": "cloudfront-1",
      "type": "aws:cloudfront",
      "label": "CDN",
      "position": {"x": 400, "y": 50},
      "group": "public",
      "properties": {"distribution_id": "..."}
    }
  ],
  "edges": [
    {
      "source": "cloudfront-1",
      "target": "alb-1",
      "label": "HTTPS",
      "style": "solid"
    }
  ],
  "groups": [
    {
      "id": "vpc-1",
      "type": "aws:vpc",
      "label": "VPC (10.0.0.0/16)",
      "children": ["public-subnet-1", "private-subnet-1"]
    }
  ]
}
```

---

## 5. Cost Estimation Engine

### Data Sources
| Cloud | API | Update Frequency |
|---|---|---|
| AWS | AWS Pricing API + Bulk pricing JSON | Daily cache |
| Azure | Azure Retail Prices API | Daily cache |
| GCP | Cloud Billing Catalog API | Daily cache |

### Cost Calculation Flow
```python
def estimate_cost(architecture: Architecture, region: str) -> CostEstimate:
    breakdown = []
    for component in architecture.components:
        service_pricing = get_pricing(component.service, region)
        monthly_cost = calculate_monthly(component, service_pricing)
        breakdown.append({
            "service": component.service,
            "description": component.label,
            "monthly_cost": monthly_cost,
            "assumptions": get_assumptions(component)
        })
    
    return CostEstimate(
        total_monthly=sum(item["monthly_cost"] for item in breakdown),
        breakdown=breakdown,
        region=region,
        currency="USD",
        confidence="medium",  # low/medium/high
        disclaimer="Estimates based on on-demand pricing. Actual costs may vary."
    )
```

### Example Output
```json
{
  "total_monthly": 487.20,
  "currency": "USD",
  "breakdown": [
    {"service": "CloudFront", "monthly": 25.00, "note": "1TB transfer/month assumed"},
    {"service": "ALB", "monthly": 22.50, "note": "Base + 1M requests"},
    {"service": "ECS Fargate", "monthly": 145.70, "note": "2 tasks × 0.25 vCPU, 0.5GB"},
    {"service": "RDS PostgreSQL", "monthly": 185.00, "note": "db.t3.medium, single-AZ, 20GB"},
    {"service": "S3", "monthly": 2.30, "note": "10GB storage, 100K requests"},
    {"service": "VPC/NAT Gateway", "monthly": 95.00, "note": "NAT Gateway + data transfer"},
    {"service": "Other", "monthly": 11.70, "note": "CloudWatch, Route53, Secrets Manager"}
  ],
  "optimization_hints": [
    "Use Reserved Instances for RDS to save ~40% ($74/month)",
    "Consider removing NAT Gateway and using VPC endpoints to save $95/month",
    "Enable S3 Intelligent-Tiering for automatic storage optimization"
  ]
}
```

---

## 6. Development Environment Setup

### Prerequisites
```bash
# Install
- Node.js 20+ (via nvm)
- Python 3.12+ (via pyenv)  
- Docker & Docker Compose
- Terraform CLI (for validation)
- tflint
- uv (Python package manager, fast)
```

### Quick Start
```bash
# Clone
git clone https://github.com/your-org/infragen.git
cd infragen

# Environment variables
cp .env.example .env
# Edit .env: add OPENAI_API_KEY

# Start everything
docker compose up -d

# Frontend (separate terminal for hot reload)
cd frontend && npm install && npm run dev

# Backend (separate terminal)
cd backend && uv sync && uv run uvicorn app.main:app --reload

# Run tests
cd backend && uv run pytest
cd frontend && npm test
```

### Docker Compose (Development)
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: infragen
      POSTGRES_USER: infragen
      POSTGRES_PASSWORD: localdev
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]

  worker:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.backend
    command: celery -A app.worker worker --loglevel=info
    depends_on: [postgres, redis]
    env_file: .env

volumes:
  postgres_data:
```

---

## 7. Testing Strategy

| Level | Tool | What to Test |
|---|---|---|
| **Unit** (Backend) | pytest | Services, validators, cost engine, prompt templates |
| **Unit** (Frontend) | Vitest + Testing Library | Components, hooks, stores |
| **Integration** (API) | pytest + httpx | API endpoints with real DB |
| **AI Quality** | Custom eval suite | Generation accuracy, validation pass rate |
| **E2E** | Playwright | Full user flows (signup → generate → export) |

### AI Evaluation Suite (Critical)
```python
# tests/ai/test_generation_quality.py

TEST_CASES = [
    {
        "input": "Simple S3 bucket with versioning enabled",
        "assertions": [
            "contains aws_s3_bucket resource",
            "versioning is enabled",
            "passes terraform validate",
            "passes checkov",
            "cost estimate > 0"
        ]
    },
    {
        "input": "3-tier web app on AWS with auto-scaling",
        "assertions": [
            "contains VPC, subnets, ALB, ECS/EC2, RDS",
            "auto-scaling group or ECS service auto-scaling present",
            "security groups are least-privilege",
            "passes terraform validate"
        ]
    },
    # ... 20-50 test cases covering common patterns
]
```

---

## 8. Deployment Strategy (MVP)

### Phase 1: Simple (MVP Launch)
```
Fly.io or Railway:
  - Backend (FastAPI) → 1 machine, auto-scale to 3
  - Worker (Celery) → 1 machine, auto-scale to 5
Neon: PostgreSQL (free tier → pro when needed)
Upstash: Redis (free tier → paid when needed)
Cloudflare Pages: Frontend (free, global CDN)
S3: Artifact storage
```
**Monthly cost**: ~$50-100 + LLM API

### Phase 2: Scale (Post-PMF)
```
AWS:
  - ECS Fargate (backend + workers)
  - RDS PostgreSQL (Multi-AZ)
  - ElastiCache Redis
  - CloudFront + S3 (frontend)
  - ALB
```
**Monthly cost**: ~$500-2000

---

## 9. Key Technical Decisions to Make Early

| Decision | Options | Recommendation |
|---|---|---|
| Monorepo vs polyrepo | Monorepo (Turborepo) vs separate repos | **Monorepo** — easier coordination for small team |
| LLM strategy | OpenAI only vs multi-provider | **OpenAI primary** (MVP), add Claude for fallback |
| Streaming | SSE vs WebSocket | **SSE** — simpler, sufficient for one-way streaming |
| Diagram rendering | Server-side (Graphviz) vs client-side (React Flow) | **Both** — server generates layout, client renders interactively |
| IaC validation | Shell out to terraform CLI vs library | **Shell out** — terraform CLI is the standard, run in Docker sandbox |
| State management | Redux vs Zustand vs Jotai | **Zustand** — simple, minimal boilerplate |
| CSS | Tailwind + shadcn/ui vs Material UI | **Tailwind + shadcn/ui** — fast, customizable, modern look |
| Package manager (Python) | pip vs poetry vs uv | **uv** — fastest, modern, resolves deps correctly |
| Package manager (Node) | npm vs pnpm | **pnpm** — fast, disk efficient, good monorepo support |
