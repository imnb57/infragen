# InfraGen

**AI-powered infrastructure-as-code generation platform.** Describe your infrastructure in natural language — get production-ready Terraform, architecture diagrams, and cost estimates instantly.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

# 2. Start everything
docker compose up --build

# 3. Access
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000/docs
# MinIO:     http://localhost:9001
```

## Architecture

```
infragen/
├── frontend/       # Next.js 15 + shadcn/ui
├── backend/        # FastAPI + SQLAlchemy
├── ai/             # AI orchestration (coming soon)
├── infra/docker/   # Dockerfiles
├── docs/           # Product documentation
└── docker-compose.yml
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Storage | MinIO (S3-compatible) |
| AI | OpenAI GPT-4o |
| Infra | Docker Compose |
