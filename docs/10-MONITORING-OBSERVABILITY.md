# 10. Monitoring, Observability & Operational Excellence

## Overview

InfraGen's observability strategy ensures we can detect, diagnose, and resolve issues before users notice them. This document covers the full observability stack — metrics, logging, tracing, alerting, SLOs, error tracking, and tenant usage analytics.

---

## 1. Observability Pillars

```
┌─────────────────────────────────────────────────────────┐
│                   OBSERVABILITY STACK                     │
│                                                           │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐            │
│  │  METRICS   │  │   LOGS    │  │  TRACES   │            │
│  │ Prometheus │  │ Structured│  │ OpenTele-  │            │
│  │  + Grafana │  │  JSON     │  │  metry     │            │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘            │
│        │              │              │                    │
│        └──────────────┼──────────────┘                    │
│                       ▼                                   │
│              ┌─────────────────┐                          │
│              │   CORRELATION   │                          │
│              │  request_id +   │                          │
│              │  tenant_id      │                          │
│              └────────┬────────┘                          │
│                       ▼                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐            │
│  │  ALERTS   │  │ DASHBOARDS│  │   ERROR    │            │
│  │ PagerDuty │  │  Grafana  │  │  TRACKING  │            │
│  │ + Slack   │  │           │  │   Sentry   │            │
│  └───────────┘  └───────────┘  └───────────┘            │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack by Phase

### MVP (Phase 1 — $0-20/month)

| Component | Tool | Rationale |
|---|---|---|
| **Metrics** | Fly.io built-in metrics + Prometheus client | Free with hosting |
| **Logging** | Structured JSON → stdout → Fly.io log drain | Zero config |
| **Error Tracking** | Sentry (free tier: 5K events/mo) | Industry standard, source maps |
| **Uptime** | BetterStack (free tier) or UptimeRobot | External HTTP checks |
| **Dashboards** | Grafana Cloud (free: 10K metrics) | Generous free tier |
| **Alerting** | Sentry + Grafana alerts → Slack | Slack webhook integration |

### Scale (Phase 2 — $100-500/month)

| Component | Tool | Rationale |
|---|---|---|
| **Metrics** | Prometheus + Grafana Cloud (Pro) | Full custom metrics |
| **Logging** | Loki (via Grafana Cloud) or Datadog | Log aggregation + search |
| **Tracing** | OpenTelemetry → Tempo (Grafana) | Distributed tracing |
| **Error Tracking** | Sentry (Team plan) | Higher volume, performance monitoring |
| **APM** | Sentry Performance or Datadog APM | Latency profiling |
| **Alerting** | PagerDuty + Slack + Email | On-call rotation |
| **Status Page** | Statuspage.io or Instatus | Public incident communication |

---

## 3. Structured Logging

### Log Format (JSON)

Every log line is a structured JSON object for machine parseability:

```python
# backend/app/core/logging.py
import structlog
import logging
import sys
from contextvars import ContextVar

# Context variables for request-scoped data
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")

def setup_logging(log_level: str = "INFO", json_output: bool = True):
    """Configure structured logging for the application."""
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

def _add_request_context(logger, method_name, event_dict):
    """Inject request-scoped context into every log entry."""
    event_dict["request_id"] = request_id_ctx.get("")
    event_dict["tenant_id"] = tenant_id_ctx.get("")
    event_dict["user_id"] = user_id_ctx.get("")
    event_dict["service"] = "infragen-api"
    return event_dict
```

### Sample Log Output

```json
{
  "timestamp": "2025-03-15T14:22:33.456Z",
  "level": "info",
  "event": "generation_completed",
  "request_id": "req_abc123",
  "tenant_id": "tenant_xyz",
  "user_id": "user_456",
  "service": "infragen-api",
  "generation_id": "gen_789",
  "provider": "aws",
  "duration_ms": 4523,
  "tokens_used": 2150,
  "output_format": "terraform"
}
```

### Log Levels Convention

| Level | Usage | Example |
|---|---|---|
| **DEBUG** | Development-only detail | Prompt templates, raw LLM responses |
| **INFO** | Normal operations | Generation started/completed, user login |
| **WARNING** | Degraded but functioning | LLM fallback triggered, rate limit approaching |
| **ERROR** | Operation failed | Generation failed, DB connection error |
| **CRITICAL** | System-wide failure | All LLM providers down, DB unreachable |

### Logging Middleware

```python
# backend/app/middleware/logging.py
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging import request_id_ctx, tenant_id_ctx, user_id_ctx
import structlog

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx.set(request_id)
        
        # Set tenant/user from auth context if available
        if hasattr(request.state, "tenant_id"):
            tenant_id_ctx.set(str(request.state.tenant_id))
        if hasattr(request.state, "user_id"):
            user_id_ctx.set(str(request.state.user_id))
        
        start_time = time.perf_counter()
        
        await logger.ainfo(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        await logger.ainfo(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        response.headers["X-Request-ID"] = request_id
        return response
```

---

## 4. Application Metrics (Prometheus)

### Custom Metrics Registry

```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info

# --- HTTP Metrics ---
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# --- Generation Metrics ---
generation_requests_total = Counter(
    "generation_requests_total",
    "Total infrastructure generation requests",
    ["provider", "output_format", "status"],  # status: success|failure|timeout
)
generation_duration_seconds = Histogram(
    "generation_duration_seconds",
    "Time to complete infrastructure generation",
    ["provider", "output_format"],
    buckets=[1, 2, 5, 10, 15, 30, 60, 120],
)
generation_in_progress = Gauge(
    "generation_in_progress",
    "Number of generations currently being processed",
    ["provider"],
)

# --- LLM Metrics ---
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API calls",
    ["provider", "model", "status"],  # provider: openai|anthropic
)
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API call latency",
    ["provider", "model"],
    buckets=[0.5, 1, 2, 5, 10, 15, 30, 60],
)
llm_tokens_used_total = Counter(
    "llm_tokens_used_total",
    "Total LLM tokens consumed",
    ["provider", "model", "type"],  # type: prompt|completion
)
llm_fallback_total = Counter(
    "llm_fallback_total",
    "Number of times LLM fallback was triggered",
    ["from_provider", "to_provider"],
)

# --- Tenant Metrics ---
tenant_active_users = Gauge(
    "tenant_active_users",
    "Number of active users per tenant",
    ["tenant_id", "plan"],
)
tenant_generations_total = Counter(
    "tenant_generations_total",
    "Total generations per tenant",
    ["tenant_id", "plan"],
)

# --- Cost Estimation Metrics ---
cost_estimation_requests_total = Counter(
    "cost_estimation_requests_total",
    "Total cost estimation requests",
    ["cloud_provider"],
)
cost_estimation_duration_seconds = Histogram(
    "cost_estimation_duration_seconds",
    "Time to estimate infrastructure costs",
    ["cloud_provider"],
    buckets=[0.1, 0.5, 1, 2, 5],
)

# --- Validation Metrics ---
validation_runs_total = Counter(
    "validation_runs_total",
    "Total IaC validation runs",
    ["tool", "status"],  # tool: terraform|tflint|checkov; status: pass|fail|error
)
validation_duration_seconds = Histogram(
    "validation_duration_seconds",
    "IaC validation run duration",
    ["tool"],
    buckets=[1, 5, 10, 15, 30],
)

# --- System Metrics ---
celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
)
celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
    ["state"],  # state: active|idle|overflow
)
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
)
```

### Metrics Endpoint

```python
# backend/app/api/routes/metrics.py
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint. Restrict access in production."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

> **Security Note:** The `/metrics` endpoint must be restricted to internal traffic only (e.g., via network policy, IP allowlist, or bearer token) to prevent exposing business metrics publicly.

---

## 5. Distributed Tracing (OpenTelemetry)

### Trace Configuration

```python
# backend/app/core/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_tracing(service_name: str, otlp_endpoint: str | None = None):
    """Initialize OpenTelemetry tracing."""
    if not otlp_endpoint:
        return  # Skip tracing in development
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment": "production",
    })
    
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=otlp_endpoint)
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

def instrument_app(app, db_engine):
    """Auto-instrument FastAPI, SQLAlchemy, Redis, and HTTP clients."""
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=db_engine)
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
```

### Custom Spans for Generation Pipeline

```python
# ai/infragen_ai/tracing.py
from opentelemetry import trace

tracer = trace.get_tracer("infragen.ai")

async def generate_infrastructure(request):
    with tracer.start_as_current_span("generate_infrastructure") as span:
        span.set_attribute("generation.provider", request.provider)
        span.set_attribute("generation.output_format", request.output_format)
        span.set_attribute("tenant.id", request.tenant_id)
        
        # Step 1: Parse intent
        with tracer.start_as_current_span("parse_intent") as intent_span:
            intent = await parse_user_intent(request.prompt)
            intent_span.set_attribute("intent.resource_count", len(intent.resources))
        
        # Step 2: Generate code
        with tracer.start_as_current_span("generate_code") as code_span:
            code = await generate_iac_code(intent, request.output_format)
            code_span.set_attribute("code.lines", code.count("\n"))
            code_span.set_attribute("llm.model", "gpt-4o")
            code_span.set_attribute("llm.tokens_prompt", code_meta.prompt_tokens)
            code_span.set_attribute("llm.tokens_completion", code_meta.completion_tokens)
        
        # Step 3: Validate
        with tracer.start_as_current_span("validate_code") as val_span:
            validation = await validate_generated_code(code)
            val_span.set_attribute("validation.passed", validation.passed)
            val_span.set_attribute("validation.issues", len(validation.issues))
        
        # Step 4: Estimate cost
        with tracer.start_as_current_span("estimate_cost") as cost_span:
            cost = await estimate_cost(intent.resources, request.provider)
            cost_span.set_attribute("cost.monthly_usd", cost.monthly_total)
        
        span.set_attribute("generation.status", "success")
        return GenerationResult(code=code, validation=validation, cost=cost)
```

### Trace Visualization

```
[generate_infrastructure] ─────────────────────────────────── 4.5s
  ├── [parse_intent] ──────── 0.8s
  │     └── [llm_call: gpt-4o] ── 0.7s
  ├── [generate_code] ──────────────── 2.5s
  │     └── [llm_call: gpt-4o] ──────── 2.3s
  ├── [validate_code] ──── 0.6s
  │     ├── [terraform_validate] ── 0.3s
  │     └── [checkov_scan] ──── 0.2s
  └── [estimate_cost] ── 0.4s
        └── [pricing_api_lookup] ── 0.3s
```

---

## 6. Error Tracking (Sentry)

### Sentry Configuration

```python
# backend/app/core/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

def setup_sentry(dsn: str, environment: str, release: str):
    """Initialize Sentry error tracking."""
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.1,  # 10% of transactions for performance
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        before_send=_scrub_sensitive_data,
        # Don't send PII to Sentry
        send_default_pii=False,
    )

def _scrub_sensitive_data(event, hint):
    """Remove sensitive data before sending to Sentry."""
    # Remove authorization headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"
    
    # Remove request body for auth endpoints
    if "request" in event:
        url = event["request"].get("url", "")
        if "/auth/" in url or "/login" in url:
            event["request"]["data"] = "[REDACTED]"
    
    return event
```

### Custom Error Context

```python
# Usage in generation service
import sentry_sdk

async def handle_generation(request):
    sentry_sdk.set_tag("tenant_id", request.tenant_id)
    sentry_sdk.set_tag("cloud_provider", request.provider)
    sentry_sdk.set_tag("output_format", request.output_format)
    sentry_sdk.set_context("generation", {
        "generation_id": request.generation_id,
        "resource_count": len(request.resources),
        "model": "gpt-4o",
    })
    
    try:
        result = await generate(request)
    except LLMProviderError as e:
        sentry_sdk.capture_exception(e)
        # Attempt fallback
        ...
```

### Frontend Error Tracking

```typescript
// frontend/src/lib/sentry.ts
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.VITE_ENVIRONMENT,
  release: import.meta.env.VITE_VERSION,
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration({ maskAllText: false, blockAllMedia: false }),
  ],
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.01,  // 1% of sessions
  replaysOnErrorSampleRate: 1.0,   // 100% of error sessions
  beforeSend(event) {
    // Scrub sensitive route params
    if (event.request?.url) {
      event.request.url = event.request.url.replace(
        /\/api-keys\/[^/]+/,
        "/api-keys/[REDACTED]"
      );
    }
    return event;
  },
});
```

---

## 7. Service Level Objectives (SLOs)

### SLO Definitions

| SLO | Target | Measurement | Burn Rate Alert |
|---|---|---|---|
| **API Availability** | 99.9% (43 min downtime/mo) | Successful HTTP responses (non-5xx) / total | 1h: 14.4x, 6h: 6x |
| **Generation Success Rate** | 99.0% | Successful generations / total attempts | 1h: 10x, 6h: 5x |
| **API Latency (p99)** | < 500ms (non-generation) | 99th percentile response time | p99 > 500ms for 5 min |
| **Generation Latency (p95)** | < 30 seconds | 95th percentile generation time | p95 > 30s for 10 min |
| **Time to First Byte (SSE)** | < 3 seconds | Time from request to first SSE event | p95 > 3s for 5 min |
| **Diagram Render Time** | < 2 seconds | Client-side diagram render completion | p95 > 2s for 10 min |

### SLI Recording

```python
# backend/app/core/slo.py
from app.core.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    generation_requests_total,
    generation_duration_seconds,
)

# SLIs are derived from the metrics above:
#
# API Availability SLI:
#   rate(http_requests_total{status_code!~"5.."}[5m]) 
#   / rate(http_requests_total[5m])
#
# Generation Success SLI:
#   rate(generation_requests_total{status="success"}[5m])
#   / rate(generation_requests_total[5m])
#
# API Latency SLI:
#   histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
#
# Generation Latency SLI:
#   histogram_quantile(0.95, rate(generation_duration_seconds_bucket[5m]))
```

### Error Budget Policy

```markdown
## Error Budget Policy

### Budget Calculation
- 99.9% availability = 43.2 minutes of downtime per 30-day window
- 99.0% generation success = 1% failure budget

### Escalation Thresholds
| Budget Consumed | Action |
|---|---|
| < 50% | Normal development velocity |
| 50-75% | Review recent deployments, increase monitoring |
| 75-90% | Freeze non-critical deploys, prioritize reliability |
| > 90% | Halt all feature work, all-hands on reliability |
| Budget exhausted | Roll back recent changes, incident review |
```

---

## 8. Alerting Strategy

### Alert Priority Levels

| Priority | Response Time | Channel | Example |
|---|---|---|---|
| **P1 — Critical** | < 15 min | PagerDuty + Slack #incidents | API down, DB unreachable |
| **P2 — High** | < 1 hour | Slack #alerts + email | Generation failure rate > 5% |
| **P3 — Medium** | < 4 hours | Slack #alerts | LLM latency degraded |
| **P4 — Low** | Next business day | Slack #monitoring | Disk usage > 70% |

### Alert Definitions

```yaml
# infra/monitoring/alerts.yml

groups:
  - name: infragen-critical
    rules:
      # P1: API is down
      - alert: APIDown
        expr: |
          (1 - (
            sum(rate(http_requests_total{status_code!~"5.."}[5m]))
            / sum(rate(http_requests_total[5m]))
          )) > 0.01
        for: 2m
        labels:
          severity: critical
          priority: P1
        annotations:
          summary: "API error rate > 1% for 2 minutes"
          description: "Current error rate: {{ $value | humanizePercentage }}"
          runbook: "https://wiki.infragen.dev/runbooks/api-down"

      # P1: Database unreachable
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
          priority: P1
        annotations:
          summary: "PostgreSQL is unreachable"
          runbook: "https://wiki.infragen.dev/runbooks/db-down"

  - name: infragen-high
    rules:
      # P2: Generation failure spike
      - alert: GenerationFailureRateHigh
        expr: |
          (
            sum(rate(generation_requests_total{status="failure"}[10m]))
            / sum(rate(generation_requests_total[10m]))
          ) > 0.05
        for: 5m
        labels:
          severity: high
          priority: P2
        annotations:
          summary: "Generation failure rate > 5% for 5 minutes"
          description: "Failure rate: {{ $value | humanizePercentage }}"
          runbook: "https://wiki.infragen.dev/runbooks/generation-failures"

      # P2: All LLM providers failing
      - alert: AllLLMProvidersDown
        expr: |
          sum(rate(llm_requests_total{status="error"}[5m]))
          / sum(rate(llm_requests_total[5m]))
          > 0.50
        for: 3m
        labels:
          severity: high
          priority: P2
        annotations:
          summary: "LLM provider error rate > 50%"
          runbook: "https://wiki.infragen.dev/runbooks/llm-providers-down"

  - name: infragen-medium
    rules:
      # P3: LLM latency degraded
      - alert: LLMLatencyHigh
        expr: |
          histogram_quantile(0.95,
            rate(llm_request_duration_seconds_bucket[10m])
          ) > 15
        for: 10m
        labels:
          severity: medium
          priority: P3
        annotations:
          summary: "LLM p95 latency > 15s for 10 minutes"

      # P3: Celery queue backing up
      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 50
        for: 5m
        labels:
          severity: medium
          priority: P3
        annotations:
          summary: "Celery task queue has > 50 pending tasks"

      # P3: Generation latency SLO burning
      - alert: GenerationLatencySLOBurning
        expr: |
          histogram_quantile(0.95,
            rate(generation_duration_seconds_bucket[30m])
          ) > 30
        for: 10m
        labels:
          severity: medium
          priority: P3
        annotations:
          summary: "Generation p95 latency > 30s (SLO breach)"

  - name: infragen-low
    rules:
      # P4: Disk usage warning
      - alert: DiskUsageHigh
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.3
        for: 30m
        labels:
          severity: low
          priority: P4
        annotations:
          summary: "Disk usage > 70%"

      # P4: Redis memory high
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 15m
        labels:
          severity: low
          priority: P4
        annotations:
          summary: "Redis memory usage > 80%"
```

### Alert Routing

```
                    ┌─────────────┐
                    │   Alert     │
                    │  Manager    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │P1 + P2 │  │P2 + P3 │  │  All   │
         │        │  │        │  │        │
         │Pager-  │  │ Slack  │  │ Slack  │
         │ Duty   │  │#alerts │  │#monitor│
         └────────┘  └────────┘  └────────┘
```

---

## 9. Grafana Dashboards

### Dashboard Structure

```
InfraGen Dashboards/
├── 01-Platform Overview          # High-level health at a glance
├── 02-API Performance            # Request rates, latencies, error rates
├── 03-Generation Pipeline        # Generation metrics, success/failure, durations
├── 04-LLM Provider Health        # OpenAI/Anthropic latency, errors, token usage
├── 05-Tenant Analytics           # Per-tenant usage, generation counts, costs
├── 06-Infrastructure             # DB connections, Redis, Celery queues, disk
├── 07-SLO Dashboard              # Error budgets, burn rates, compliance
└── 08-Business Metrics           # Signups, conversions, revenue (Phase 2)
```

### Platform Overview Dashboard Panels

```
┌──────────────────────────────────────────────────────────┐
│                  INFRAGEN — PLATFORM OVERVIEW             │
├──────────────┬──────────────┬──────────────┬─────────────┤
│  API Uptime  │  Gen Success │  Active Users│  LLM Cost   │
│   99.97%     │    98.5%     │     142      │  $23.50/day │
│   (30 days)  │   (24 hrs)   │   (24 hrs)   │             │
├──────────────┴──────────────┴──────────────┴─────────────┤
│                                                           │
│  Request Rate (rps)          Generation Latency (p50/p95) │
│  ████████████████████████    ████████████████████████████  │
│  │    ╱╲    ╱╲              │                     ─── p95 │
│  │   ╱  ╲  ╱  ╲             │  ─────────────────  ─── p50 │
│  │  ╱    ╲╱    ╲            │                             │
│  │ ╱            ╲           │                             │
│  └──────────────────────    └─────────────────────────── │
│                                                           │
├──────────────────────────────┬────────────────────────────┤
│  Error Rate by Endpoint      │  Active Generations        │
│  ████████████████████████    │                            │
│  POST /generate ■ 0.8%      │       ┌──┐                 │
│  POST /auth     ■ 0.1%      │    ┌──┤  ├──┐              │
│  GET  /projects ■ 0.0%      │ ┌──┤  │  │  ├──┐           │
│                              │ │  │  │  │  │  │           │
├──────────────────────────────┴────────────────────────────┤
│  Top Errors (last 24h)                                    │
│  1. LLMTimeoutError (openai) — 12 occurrences            │
│  2. ValidationError (terraform) — 8 occurrences           │
│  3. RateLimitExceeded — 3 occurrences                     │
└──────────────────────────────────────────────────────────┘
```

### Grafana Dashboard as Code

```json
// infra/monitoring/dashboards/platform-overview.json (excerpt)
{
  "dashboard": {
    "title": "InfraGen — Platform Overview",
    "uid": "infragen-overview",
    "refresh": "30s",
    "time": { "from": "now-24h", "to": "now" },
    "panels": [
      {
        "title": "API Availability (30d)",
        "type": "stat",
        "targets": [{
          "expr": "1 - (sum(increase(http_requests_total{status_code=~\"5..\"}[30d])) / sum(increase(http_requests_total[30d])))",
          "legendFormat": "Availability"
        }],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "thresholds": {
              "steps": [
                { "value": 0, "color": "red" },
                { "value": 0.999, "color": "green" }
              ]
            }
          }
        }
      },
      {
        "title": "Generation Success Rate (24h)",
        "type": "stat",
        "targets": [{
          "expr": "sum(increase(generation_requests_total{status=\"success\"}[24h])) / sum(increase(generation_requests_total[24h]))"
        }]
      },
      {
        "title": "Request Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "sum(rate(http_requests_total[5m]))",
          "legendFormat": "Total rps"
        }]
      },
      {
        "title": "Generation Latency",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, sum(rate(generation_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, sum(rate(generation_duration_seconds_bucket[5m])) by (le))",
            "legendFormat": "p95"
          }
        ]
      }
    ]
  }
}
```

---

## 10. Health Checks

### Application Health Endpoint

```python
# backend/app/api/routes/health.py
from fastapi import APIRouter, Response
from sqlalchemy import text
from redis.asyncio import Redis
import structlog

logger = structlog.get_logger()
router = APIRouter()

@router.get("/health")
async def health_check():
    """Shallow health check for load balancer."""
    return {"status": "healthy"}

@router.get("/health/ready")
async def readiness_check(db=Depends(get_db), redis: Redis = Depends(get_redis)):
    """Deep readiness check — verifies all dependencies."""
    checks = {}
    healthy = True
    
    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        healthy = False
        await logger.aerror("health_check_failed", component="database", error=str(e))
    
    # Redis check
    try:
        await redis.ping()
        checks["redis"] = {"status": "healthy"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        healthy = False
        await logger.aerror("health_check_failed", component="redis", error=str(e))
    
    status_code = 200 if healthy else 503
    return Response(
        content=json.dumps({
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
        }),
        status_code=status_code,
        media_type="application/json",
    )
```

### Health Check Integration

```yaml
# Docker Compose health checks
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s

  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U infragen"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
```

---

## 11. Tenant Usage Analytics & Billing Metrics

### Usage Tracking

```python
# backend/app/services/usage_tracker.py
import structlog
from datetime import datetime, timezone
from app.core.metrics import tenant_generations_total

logger = structlog.get_logger()

class UsageTracker:
    """Track per-tenant resource usage for billing and analytics."""
    
    def __init__(self, redis, db):
        self.redis = redis
        self.db = db
    
    async def record_generation(
        self,
        tenant_id: str,
        generation_id: str,
        tokens_used: int,
        provider: str,
        duration_ms: int,
    ):
        """Record a completed generation for billing."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        pipe = self.redis.pipeline()
        
        # Daily generation count
        daily_key = f"usage:{tenant_id}:generations:{today}"
        pipe.incr(daily_key)
        pipe.expire(daily_key, 90 * 86400)  # 90-day retention
        
        # Monthly generation count (for plan limits)
        monthly_key = f"usage:{tenant_id}:generations:{month}"
        pipe.incr(monthly_key)
        pipe.expire(monthly_key, 365 * 86400)
        
        # Monthly token usage
        token_key = f"usage:{tenant_id}:tokens:{month}"
        pipe.incrby(token_key, tokens_used)
        pipe.expire(token_key, 365 * 86400)
        
        await pipe.execute()
        
        # Prometheus metric
        tenant_generations_total.labels(
            tenant_id=tenant_id,
            plan=await self._get_tenant_plan(tenant_id),
        ).inc()
        
        await logger.ainfo(
            "usage_recorded",
            tenant_id=tenant_id,
            generation_id=generation_id,
            tokens_used=tokens_used,
            provider=provider,
            duration_ms=duration_ms,
        )
    
    async def get_monthly_usage(self, tenant_id: str) -> dict:
        """Get current month's usage for a tenant."""
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        pipe = self.redis.pipeline()
        pipe.get(f"usage:{tenant_id}:generations:{month}")
        pipe.get(f"usage:{tenant_id}:tokens:{month}")
        results = await pipe.execute()
        
        return {
            "generations": int(results[0] or 0),
            "tokens": int(results[1] or 0),
            "month": month,
        }
    
    async def check_plan_limit(self, tenant_id: str) -> bool:
        """Check if tenant has remaining generations in their plan."""
        usage = await self.get_monthly_usage(tenant_id)
        plan = await self._get_tenant_plan(tenant_id)
        
        limits = {
            "free": 10,
            "pro": 200,
            "team": 1000,
            "enterprise": float("inf"),
        }
        
        return usage["generations"] < limits.get(plan, 0)
```

### Usage Dashboard Data (API)

```python
# backend/app/api/routes/usage.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/usage", tags=["usage"])

@router.get("/current")
async def get_current_usage(
    tenant_id: str = Depends(get_current_tenant),
    tracker: UsageTracker = Depends(get_usage_tracker),
):
    """Get current billing period usage for the authenticated tenant."""
    usage = await tracker.get_monthly_usage(tenant_id)
    plan = await tracker.get_tenant_plan(tenant_id)
    
    return {
        "period": usage["month"],
        "generations": {
            "used": usage["generations"],
            "limit": plan.generation_limit,
            "remaining": max(0, plan.generation_limit - usage["generations"]),
        },
        "tokens": {
            "used": usage["tokens"],
        },
    }
```

---

## 12. Incident Management

### Incident Response Process

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│  DETECT   │───▶│  RESPOND  │───▶│  RESOLVE  │───▶│  REVIEW   │
│           │    │           │    │           │    │           │
│ Alert     │    │ Ack page  │    │ Fix root  │    │ Postmortem│
│ fires     │    │ Triage    │    │ cause     │    │ Action    │
│           │    │ Communicate│   │ Verify    │    │ items     │
└───────────┘    └───────────┘    └───────────┘    └───────────┘
```

### Incident Severity Levels

| Severity | Definition | Response | Communication |
|---|---|---|---|
| **SEV1** | Platform completely down | All hands, 15-min updates | Status page, email blast |
| **SEV2** | Major feature broken (generation) | Primary on-call, 30-min updates | Status page update |
| **SEV3** | Degraded performance | On-call investigates, 1-hr updates | Internal Slack only |
| **SEV4** | Minor issue, no user impact | Tracked in backlog | None |

### Postmortem Template

```markdown
## Incident Postmortem: [TITLE]

**Date:** YYYY-MM-DD
**Duration:** Xh Ym
**Severity:** SEV-X
**Author:** [Name]
**Status:** Draft | Final

### Summary
[1-2 sentence description of what happened]

### Impact
- Users affected: X
- Generations failed: X
- Duration of impact: Xh Ym
- Error budget consumed: X%

### Timeline (all times UTC)
| Time | Event |
|---|---|
| HH:MM | Alert fired |
| HH:MM | Engineer acknowledged |
| HH:MM | Root cause identified |
| HH:MM | Fix deployed |
| HH:MM | Metrics returned to normal |

### Root Cause
[Technical explanation of why this happened]

### Resolution
[What was done to fix the immediate problem]

### Action Items
| Action | Owner | Priority | Due Date |
|---|---|---|---|
| [Specific action] | @name | P1/P2 | YYYY-MM-DD |

### Lessons Learned
- What went well:
- What didn't go well:
- Where we got lucky:
```

---

## 13. Uptime & External Monitoring

### External Health Checks

Configure BetterStack (or UptimeRobot) to monitor from multiple regions:

| Check | URL | Interval | Timeout | Regions |
|---|---|---|---|---|
| API Health | `https://api.infragen.dev/health` | 30s | 10s | US-East, EU-West, AP-South |
| API Readiness | `https://api.infragen.dev/health/ready` | 60s | 15s | US-East |
| Frontend | `https://app.infragen.dev` | 60s | 10s | US-East, EU-West |
| SSE Endpoint | `https://api.infragen.dev/health` | 60s | 10s | US-East |

### Status Page Configuration

Public status page at `https://status.infragen.dev`:

```
Components:
├── Web Application        [Operational]
├── API                    [Operational]  
├── Generation Engine      [Operational]
├── Cost Estimation        [Operational]
├── Authentication         [Operational]
└── Diagram Rendering      [Operational]
```

---

## 14. Log Retention & Data Lifecycle

| Data Type | Retention (Dev) | Retention (Prod) | Storage |
|---|---|---|---|
| Application logs | 3 days | 30 days | Stdout → log drain |
| Audit logs (DB) | 30 days | 1 year | PostgreSQL |
| Metrics | 7 days | 13 months | Prometheus/Grafana Cloud |
| Traces | 3 days | 7 days | Tempo/Grafana Cloud |
| Error events | 30 days | 90 days | Sentry |
| Usage data | 30 days | 2 years | Redis + PostgreSQL archive |

### Log Drain Configuration (Fly.io)

```toml
# fly.toml
[metrics]
  port = 9091
  path = "/metrics"

# Ship logs to Grafana Cloud Loki
# Configure via: fly logs ship --org infragen --loki-url https://...
```

---

## 15. Local Development Observability

For local development, observability is lightweight:

```yaml
# docker-compose.yml (dev additions)
services:
  # Existing services: api, postgres, redis, worker...

  # Optional: Local Prometheus + Grafana
  prometheus:
    image: prom/prometheus:v2.51.0
    profiles: ["monitoring"]  # Only start with: docker compose --profile monitoring up
    ports:
      - "9090:9090"
    volumes:
      - ./infra/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:10.4.0
    profiles: ["monitoring"]
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AUTH_ANONYMOUS_ENABLED=true
    volumes:
      - ./infra/monitoring/dashboards:/var/lib/grafana/dashboards
      - ./infra/monitoring/provisioning:/etc/grafana/provisioning
```

```ini
# infra/monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "infragen-api"
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics

  - job_name: "infragen-worker"
    static_configs:
      - targets: ["worker:9091"]
```

**Development logging** uses console renderer (colored, human-readable) instead of JSON:

```bash
# .env.development
LOG_FORMAT=console
LOG_LEVEL=DEBUG
SENTRY_DSN=  # Empty = disabled in dev
OTLP_ENDPOINT=  # Empty = tracing disabled in dev
```

---

## 16. Observability Checklist by Phase

### MVP Launch Checklist

- [ ] Structured JSON logging on all services
- [ ] Request ID propagation (X-Request-ID header)
- [ ] `/health` and `/health/ready` endpoints
- [ ] Sentry configured (backend + frontend)
- [ ] External uptime monitoring (BetterStack free)
- [ ] Basic Prometheus metrics (http, generation, LLM)
- [ ] Grafana Cloud dashboard (overview)
- [ ] Slack alerts for P1/P2 conditions
- [ ] Usage tracking for plan limits
- [ ] Audit logging for security events

### Scale Phase Additions

- [ ] OpenTelemetry distributed tracing
- [ ] Full SLO dashboard with error budgets
- [ ] PagerDuty on-call rotation
- [ ] Public status page
- [ ] Per-tenant analytics dashboard
- [ ] Log aggregation with search (Loki)
- [ ] Grafana alerting rules (Prometheus → Alertmanager)
- [ ] Postmortem process documented
- [ ] Incident response runbooks for all P1/P2 alerts
- [ ] Cost attribution per tenant (LLM spend)

---

## Summary

| Aspect | MVP Solution | Scale Solution |
|---|---|---|
| **Logging** | structlog → stdout → Fly.io | structlog → Loki → Grafana |
| **Metrics** | Prometheus client → Grafana Cloud free | Prometheus → Grafana Cloud Pro |
| **Tracing** | None (request_id only) | OpenTelemetry → Tempo |
| **Errors** | Sentry free tier | Sentry Team |
| **Alerting** | Sentry + Slack | Prometheus Alertmanager + PagerDuty |
| **Uptime** | BetterStack free | BetterStack + status page |
| **SLOs** | Manual tracking | Automated error budget dashboards |
| **Incidents** | Slack thread | Structured process + postmortems |
| **Cost** | ~$0-20/month | ~$100-300/month |
