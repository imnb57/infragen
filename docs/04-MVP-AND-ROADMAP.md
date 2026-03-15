# InfraGen — MVP Definition & Product Roadmap

## 1. MVP Philosophy

> **Ship the smallest thing that delivers the "magic moment":**
> User types a description → gets a working architecture diagram + validated Terraform code + cost estimate in under 60 seconds.

### Magic Moment
```
Input:  "3-tier web app on AWS with React, Node.js API, PostgreSQL, 
         auto-scaling, CDN, budget $500/month"

Output: ✅ Architecture diagram (AWS icons, interactive)
        ✅ Terraform code (validated, linted, security-scanned)
        ✅ Cost estimate: $487/month with per-service breakdown
        ✅ One-click download (ZIP with all files)

Time: < 60 seconds
```

If a user experiences this once, they understand the value and come back.

---

## 2. MVP Scope (v0.1 — 8-10 weeks)

### IN Scope

| Feature | Details | Priority |
|---|---|---|
| **NL → Terraform** | Single cloud (AWS), Terraform only | P0 |
| **Architecture Diagram** | Auto-generated, AWS icons, SVG export | P0 |
| **Cost Estimation** | AWS pricing, monthly breakdown | P0 |
| **Chat Interface** | Conversational refinement ("add Redis", "make it HA") | P0 |
| **Code Viewer** | Monaco editor, file tree, syntax highlighting | P0 |
| **Validation** | terraform validate + tflint + basic Checkov | P0 |
| **User Auth** | Email/password + GitHub OAuth | P0 |
| **Project Save** | Save/load projects, basic versioning | P1 |
| **Template Library** | 5-10 starter templates | P1 |
| **Export** | Download as ZIP (Terraform + diagram + README) | P1 |

### OUT of Scope (MVP)

| Feature | Why Deferred |
|---|---|
| Azure / GCP support | Focus on AWS to nail quality |
| Pulumi / CDK / Bicep | Terraform is most popular, start there |
| Multi-tenant org/team | Single user accounts first |
| Approval workflows | No team features in MVP |
| Monitoring config gen | Nice-to-have, not core |
| CI/CD integration | Users download and run locally |
| Self-hosted option | SaaS-only for MVP |
| Diagram-to-code editing | Complex, defer to v0.3 |

---

## 3. MVP Technical Stack

```
Frontend:
  - React 18 + TypeScript + Vite
  - TailwindCSS + shadcn/ui (fast, beautiful)
  - React Flow (diagram canvas)
  - Monaco Editor (code viewer)
  - React Query (data fetching)
  - Zustand (state management)

Backend:
  - Python 3.12 + FastAPI
  - SQLAlchemy 2.0 + Alembic (ORM + migrations)
  - PostgreSQL 16
  - Redis (cache + rate limiting)
  - Celery (async generation tasks)
  - OpenAI GPT-4o (primary LLM)

Infrastructure:
  - Docker Compose (local dev)
  - Fly.io or Railway (MVP deployment — fast, cheap)
  - Neon (managed PostgreSQL, free tier)
  - Upstash (managed Redis, free tier)
  - Cloudflare (CDN, DNS)
  - S3 (artifact storage)

Cost to Run MVP: ~$50-100/month + LLM API costs (~$0.01-0.05 per generation)
```

---

## 4. MVP Milestones (8-10 Week Plan)

### Week 1-2: Foundation
- [ ] Project scaffolding (monorepo: frontend + backend)
- [ ] Auth system (JWT + GitHub OAuth)
- [ ] Database schema + migrations
- [ ] Basic API structure (projects CRUD)
- [ ] Frontend shell (routing, layout, auth pages)
- [ ] Docker Compose dev environment

### Week 3-4: AI Core
- [ ] LLM integration (OpenAI SDK, prompt management)
- [ ] Intent parser (NL → structured architecture spec)
- [ ] Terraform generator (LLM + templates + validation)
- [ ] terraform validate + tflint integration
- [ ] Streaming SSE responses to frontend
- [ ] Chat interface with message history

### Week 5-6: Diagram + Cost
- [ ] Diagram engine (architecture spec → SVG with AWS icons)
- [ ] React Flow interactive diagram viewer
- [ ] AWS Pricing API integration
- [ ] Cost calculation engine
- [ ] Cost breakdown UI component
- [ ] Split-pane layout (chat | diagram | code+cost)

### Week 7-8: Polish + Templates
- [ ] Conversational refinement ("add Redis", "switch to Fargate")
- [ ] 5-10 starter templates
- [ ] Export as ZIP (Terraform + diagram + README)
- [ ] Validation panel (errors, warnings, security issues)
- [ ] Basic project save/load
- [ ] Checkov security scanning

### Week 9-10: Launch Prep
- [ ] Landing page
- [ ] Onboarding flow
- [ ] Usage limits (free tier: 10 generations/month)
- [ ] Error handling, edge cases, loading states
- [ ] Performance optimization (caching, streaming)
- [ ] Deploy to production
- [ ] Analytics (PostHog / Mixpanel)
- [ ] Documentation (user guide)

---

## 5. Post-MVP Roadmap

### v0.2 — Multi-Cloud + Teams (Weeks 11-16)
- Azure support (Terraform + Azure icons + Azure pricing)
- GCP support
- Multi-cloud comparison ("show me AWS vs Azure")
- Organization + team accounts
- Basic RBAC (admin, member, viewer)
- Project sharing within team

### v0.3 — Governance + Advanced Diagrams (Weeks 17-22)
- Policy engine (OPA/Rego integration)
- Approval workflows (propose → review → approve)
- Audit logging
- Bidirectional diagram editing (drag component → update code)
- Diagram diffing between versions
- Pulumi support

### v0.4 — Documentation + Monitoring (Weeks 23-28)
- Auto-generated ADRs
- Runbook generation
- Compliance documentation (SOC2 mapping)
- Monitoring config generation (CloudWatch, Datadog)
- Alert templates
- CDK support

### v0.5 — Enterprise (Weeks 29-36)
- SSO/SAML
- Advanced RBAC + custom roles
- Self-hosted option
- SOC2 Type II certification
- Enterprise support SLA
- API for programmatic access
- CI/CD integration (GitHub Actions, GitLab CI)

### v1.0 — Platform (Weeks 37+)
- Template marketplace (community-contributed)
- Plugin system (custom generators, validators)
- Drift detection (compare desired vs. actual infra)
- AI-powered migration assistant
- Bicep + CloudFormation support
- IDE extensions (VS Code, JetBrains)

---

## 6. Success Metrics (MVP)

| Metric | Target (90 days post-launch) |
|---|---|
| Signups | 1,000 |
| Weekly Active Users | 200 |
| Generations per user per week | 3+ |
| Generation success rate (valid output) | > 90% |
| Time to first generation | < 3 minutes from signup |
| NPS score | > 40 |
| Paid conversion (free → paid) | 5% |
| Monthly Recurring Revenue | $2,000 |

---

## 7. Technical Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| LLM generates invalid Terraform | Users lose trust | High | Multi-layer validation, template-assisted generation, automated tests |
| Cost estimates inaccurate | Users make bad decisions | Medium | Use official pricing APIs, show confidence level, disclaimer |
| LLM latency too high (>60s) | Bad UX | Medium | Streaming, caching common patterns, smaller model for parsing |
| OpenAI API costs spiral | Burns cash | Medium | Cache aggressively, use GPT-4o-mini for simple tasks, rate limits |
| Prompt injection attacks | Security breach | Low | Input sanitization, output validation, sandboxed execution |
| Scaling AI workers | Bottleneck under load | Low (MVP) | Celery with auto-scale, queue-based backpressure |
