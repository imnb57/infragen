# InfraGen — DevOps & CI/CD Pipeline

## 1. Pipeline Overview

```
Developer ──► GitHub PR ──► CI Pipeline ──► Staging ──► Production
                 │                │
                 │                ├── Lint & Type Check
                 │                ├── Unit Tests
                 │                ├── Integration Tests
                 │                ├── Security Scans
                 │                ├── AI Quality Tests (sampled)
                 │                ├── Build Docker Images
                 │                └── Preview Deployment (PR)
                 │
                 ├── On merge to main ──► Deploy Staging (auto)
                 │                              │
                 │                         Smoke Tests
                 │                              │
                 └── Release tag ──────► Deploy Production (manual approve)
```

---

## 2. GitHub Actions Workflows

### CI Pipeline (Every PR)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"

jobs:
  # ─────────────────────────────────
  # Backend
  # ─────────────────────────────────
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd backend && uv sync
      - run: cd backend && uv run ruff check .
      - run: cd backend && uv run ruff format --check .
      - run: cd backend && uv run mypy app/

  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: infragen_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd backend && uv sync
      - run: cd backend && uv run pytest --cov=app --cov-report=xml -v
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/infragen_test
          REDIS_URL: redis://localhost:6379/0
      - uses: codecov/codecov-action@v4

  # ─────────────────────────────────
  # AI Module
  # ─────────────────────────────────
  ai-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd ai && uv sync
      - run: cd ai && uv run ruff check .
      - run: cd ai && uv run mypy infragen_ai/

  ai-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: cd ai && uv sync
      - run: cd ai && uv run pytest --cov -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY_TEST }}

  # ─────────────────────────────────
  # Frontend
  # ─────────────────────────────────
  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "pnpm", cache-dependency-path: frontend/pnpm-lock.yaml }
      - run: cd frontend && pnpm install --frozen-lockfile
      - run: cd frontend && pnpm lint
      - run: cd frontend && pnpm typecheck

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "pnpm", cache-dependency-path: frontend/pnpm-lock.yaml }
      - run: cd frontend && pnpm install --frozen-lockfile
      - run: cd frontend && pnpm test -- --coverage

  frontend-build:
    runs-on: ubuntu-latest
    needs: [frontend-lint, frontend-test]
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "pnpm", cache-dependency-path: frontend/pnpm-lock.yaml }
      - run: cd frontend && pnpm install --frozen-lockfile
      - run: cd frontend && pnpm build
      - uses: actions/upload-artifact@v4
        with: { name: frontend-dist, path: frontend/dist }

  # ─────────────────────────────────
  # Security
  # ─────────────────────────────────
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit bandit
      - run: cd backend && pip-audit -r requirements.txt || true
      - run: cd backend && bandit -r app/ -ll
      - run: cd frontend && pnpm audit --audit-level=high || true

  # ─────────────────────────────────
  # Docker Build (only on main)
  # ─────────────────────────────────
  docker-build:
    if: github.ref == 'refs/heads/main'
    needs: [backend-test, ai-test, frontend-build, security-scan]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [backend, frontend, worker]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: infra/docker/Dockerfile.${{ matrix.service }}
          push: true
          tags: ghcr.io/${{ github.repository }}/${{ matrix.service }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Deploy Staging (On Merge to Main)

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy Staging

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      # Run database migrations
      - name: Run migrations
        run: |
          # Connect to staging DB and run alembic
          cd backend && alembic upgrade head
        env:
          DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}

      # Deploy backend to Fly.io (MVP) or ECS (scale)
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --config fly.staging.toml --image ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

      # Deploy frontend to Cloudflare Pages
      - run: cd frontend && pnpm install && pnpm build
        env:
          VITE_API_URL: https://api-staging.infragen.io
      - uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          projectName: infragen-staging
          directory: frontend/dist

      # Smoke test
      - name: Smoke Test
        run: |
          sleep 10
          curl -sf https://api-staging.infragen.io/health || exit 1
          curl -sf https://staging.infragen.io || exit 1
```

### Deploy Production (Manual)

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy Production

on:
  workflow_dispatch:
    inputs:
      tag:
        description: 'Release tag to deploy'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.inputs.tag }}
      
      # Same pattern as staging but with production configs
      - name: Deploy Backend
        run: flyctl deploy --config fly.production.toml --image ghcr.io/${{ github.repository }}/backend:${{ github.event.inputs.tag }}
      
      - name: Deploy Frontend
        run: |
          cd frontend && pnpm install && pnpm build
          # Deploy to Cloudflare Pages production
        env:
          VITE_API_URL: https://api.infragen.io
```

---

## 3. Docker Images

### Backend Dockerfile
```dockerfile
# infra/docker/Dockerfile.backend
FROM python:3.12-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend/app ./app
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY ai/ /ai

# Non-root user
RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile
```dockerfile
# infra/docker/Dockerfile.frontend
FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm build

# Serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### Worker Dockerfile
```dockerfile
# infra/docker/Dockerfile.worker
FROM python:3.12-slim

# Install uv + terraform CLI (for validation)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=hashicorp/terraform:1.6 /bin/terraform /usr/local/bin/terraform

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY ai/ /ai

RUN useradd -r -s /bin/false appuser
USER appuser

CMD ["uv", "run", "celery", "-A", "app.worker", "worker", "--loglevel=info", "--concurrency=4"]
```

---

## 4. Environment Configuration

### Environment Matrix
| Setting | Development | Staging | Production |
|---|---|---|---|
| `DATABASE_URL` | localhost:5432 | Neon staging | Neon/RDS prod |
| `REDIS_URL` | localhost:6379 | Upstash staging | Upstash/ElastiCache |
| `OPENAI_API_KEY` | Personal key | Org test key | Org production key |
| `JWT_SECRET` | dev-secret | AWS Secrets | AWS Secrets |
| `CORS_ORIGINS` | localhost:5173 | staging.infragen.io | app.infragen.io |
| `LOG_LEVEL` | DEBUG | INFO | WARNING |
| `SENTRY_DSN` | — | Staging DSN | Production DSN |

### .env.example
```bash
# Database
DATABASE_URL=postgresql://infragen:localdev@localhost:5432/infragen
REDIS_URL=redis://localhost:6379/0

# AI
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o

# Auth
JWT_SECRET=change-me-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth (optional for local dev)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Storage
S3_BUCKET=infragen-artifacts
S3_ENDPOINT=http://localhost:9000  # MinIO for local dev
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# App
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=DEBUG
```

---

## 5. Branching Strategy

```
main (protected) ──────────────────────────────────────► production
  │         │         │
  │ feature/ │ feature/ │ feature/
  │ diagram  │ cost-eng │ auth-oauth
  │         │         │
  └─► PR ──►┘─► PR ──►┘─► PR ──► merge to main
```

### Rules
1. `main` is always deployable
2. Feature branches: `feature/<short-description>`
3. Bug fixes: `fix/<issue-number>-<description>`
4. All PRs require:
   - CI passing (all checks green)
   - At least 1 approval (when team > 1)
   - No merge conflicts
5. Squash merge to keep history clean
6. Production deploys via tagged releases: `v0.1.0`, `v0.2.0`

---

## 6. Database Migration Pipeline

```
Developer creates migration
        │
        ▼
alembic revision --autogenerate -m "add api_keys table"
        │
        ▼
Review generated migration file
        │
        ▼
Test locally: alembic upgrade head
        │
        ▼
Push PR → CI runs migration on test DB
        │
        ▼
Merge → Staging auto-deploys, migration runs first
        │
        ▼
Production deploy → Migration runs before new code (via deploy script)
```

### Migration Safety
```yaml
# In deploy script:
- name: Run migrations
  run: |
    # Check for destructive operations
    alembic upgrade --sql head | grep -i "DROP" && echo "WARNING: Destructive migration!" && exit 1
    
    # Run migration
    alembic upgrade head
    
    # Verify
    alembic current
```

---

## 7. Local Development Workflow

```bash
# Daily workflow
git checkout main && git pull
git checkout -b feature/my-feature

# Start services
docker compose up -d  # postgres, redis, minio

# Backend (terminal 1)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
pnpm install
pnpm dev  # Vite on port 5173

# Run tests before pushing
cd backend && uv run pytest -v
cd frontend && pnpm test
cd ai && uv run pytest -v

# Push and create PR
git add . && git commit -m "feat: add diagram export"
git push -u origin feature/my-feature
# → GitHub creates PR → CI runs
```

---

## 8. Release Process

### Versioning: Semantic Versioning
- `v0.x.y` — Pre-1.0 (MVP phase, breaking changes expected)
- `v1.x.y` — Post-1.0 (stable API contract)

### Release Checklist
```markdown
## Release v0.2.0

- [ ] All CI green on main
- [ ] Staging smoke tests pass
- [ ] Run full AI eval suite on staging
- [ ] Update CHANGELOG.md
- [ ] Create git tag: `git tag v0.2.0`
- [ ] Push tag: `git push origin v0.2.0`
- [ ] Trigger production deploy workflow
- [ ] Verify production health checks
- [ ] Monitor error rates for 30 minutes
- [ ] Announce in Discord / changelog page
```
