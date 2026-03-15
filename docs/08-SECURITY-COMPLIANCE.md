# InfraGen — Security & Compliance Framework

## 1. Threat Model Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     THREAT LANDSCAPE                        │
├──────────────────┬──────────────────────────────────────────┤
│ Threat           │ Risk & Mitigation                        │
├──────────────────┼──────────────────────────────────────────┤
│ Tenant data leak │ HIGH — RLS + app-level tenant isolation  │
│ Prompt injection │ HIGH — Input sanitization + output guard │
│ Generated IaC    │ HIGH — Security scanning (checkov/tfsec) │
│   insecure code  │       before presenting to user          │
│ LLM API key leak │ MED — Vault/secrets manager, never log   │
│ XSS/CSRF         │ MED — CSP headers, CSRF tokens, SameSite│
│ IDOR             │ MED — Ownership checks on every endpoint │
│ DDoS / abuse     │ MED — Rate limiting + WAF                │
│ Supply chain     │ LOW — Dependabot, lock files, audit      │
└──────────────────┴──────────────────────────────────────────┘
```

---

## 2. Authentication & Authorization

### Auth Stack
```
Frontend ──────► FastAPI Backend
                    │
                    ├── Email/Password  → Argon2id hashing
                    ├── GitHub OAuth    → OAuth 2.0 PKCE
                    ├── Google OAuth    → OAuth 2.0 PKCE
                    │
                    └── JWT Access Token (15 min) + Refresh Token (7 days)
                        stored in httpOnly, Secure, SameSite=Strict cookie
```

### JWT Structure
```json
{
  "sub": "user-uuid",
  "tid": "tenant-uuid",
  "role": "admin",
  "scopes": ["generate", "read", "manage"],
  "exp": 1700000000,
  "iat": 1699999100,
  "jti": "unique-token-id"    // For revocation
}
```

### Role-Based Access Control (RBAC)

| Permission | Owner | Admin | Member | Viewer |
|---|---|---|---|---|
| Create project | ✅ | ✅ | ✅ | ❌ |
| Generate infrastructure | ✅ | ✅ | ✅ | ❌ |
| View projects | ✅ | ✅ | ✅ | ✅ |
| Delete project | ✅ | ✅ | ❌ | ❌ |
| Manage team members | ✅ | ✅ | ❌ | ❌ |
| Billing & plan changes | ✅ | ❌ | ❌ | ❌ |
| Manage API keys | ✅ | ✅ | Own only | ❌ |
| View audit logs | ✅ | ✅ | ❌ | ❌ |

### Implementation
```python
# backend/app/core/auth/permissions.py

from enum import Enum
from functools import wraps

class Permission(str, Enum):
    GENERATE = "generate"
    READ = "read"
    MANAGE_PROJECTS = "manage_projects"
    MANAGE_TEAM = "manage_team"
    BILLING = "billing"
    AUDIT = "audit"

ROLE_PERMISSIONS = {
    "owner":  {Permission.GENERATE, Permission.READ, Permission.MANAGE_PROJECTS, 
               Permission.MANAGE_TEAM, Permission.BILLING, Permission.AUDIT},
    "admin":  {Permission.GENERATE, Permission.READ, Permission.MANAGE_PROJECTS, 
               Permission.MANAGE_TEAM, Permission.AUDIT},
    "member": {Permission.GENERATE, Permission.READ},
    "viewer": {Permission.READ},
}

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            user_permissions = ROLE_PERMISSIONS.get(current_user.role, set())
            if permission not in user_permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

---

## 3. Multi-Tenant Security

### Isolation Layers
```
Layer 1: JWT tenant claim (tid) — set at authentication
Layer 2: Application middleware — extracts tenant, sets context
Layer 3: Service layer — all queries scoped by tenant_id
Layer 4: PostgreSQL RLS — database-level enforcement (defense in depth)
```

### Middleware
```python
# backend/app/core/middleware/tenant.py

class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant from JWT
        token = request.state.user
        if token:
            request.state.tenant_id = token.get("tid")
        
        response = await call_next(request)
        return response
```

### Cross-Tenant Attack Prevention
- Every database query MUST include `tenant_id` filter
- File storage paths include tenant ID: `s3://{bucket}/{tenant_id}/{project_id}/...`
- Redis keys include tenant ID: `gen:{tenant_id}:{generation_id}:status`
- API responses never expose internal IDs from other tenants
- Background workers receive tenant context from the job payload

---

## 4. Input Validation & Injection Prevention

### User Prompt Sanitization
```python
# ai/infragen_ai/validators/input_sanitizer.py

import re

BLOCKED_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all previous",
    r"you are now",
    r"forget your instructions",
    r"system prompt",
    r"<script",
    r"javascript:",
]

def sanitize_user_prompt(prompt: str) -> str:
    """Sanitize user input before sending to LLM."""
    # Length limit
    if len(prompt) > 5000:
        raise ValueError("Prompt too long (max 5000 characters)")
    
    # Check for prompt injection attempts
    prompt_lower = prompt.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, prompt_lower):
            raise ValueError("Input contains disallowed content")
    
    return prompt.strip()
```

### Generated Code Security Scanning
```python
# ai/infragen_ai/validators/security_scanner.py

async def scan_generated_terraform(files: list[GeneratedFile]) -> ValidationResult:
    """Run security checks on generated IaC code."""
    
    results = ValidationResult(errors=[], warnings=[], passed=True)
    
    # 1. Static analysis with checkov
    checkov_results = await run_checkov(files)
    for finding in checkov_results:
        if finding.severity == "CRITICAL":
            results.errors.append(f"Security issue: {finding.message}")
            results.passed = False
        else:
            results.warnings.append(f"{finding.severity}: {finding.message}")
    
    # 2. Custom rules (critical)
    for file in files:
        content = file.content
        
        # No hardcoded secrets
        if re.search(r'(password|secret|key)\s*=\s*"[^"]{8,}"', content, re.I):
            results.errors.append(f"{file.path}: Possible hardcoded secret detected")
            results.passed = False
        
        # No public S3 buckets
        if 'acl' in content and '"public-read"' in content:
            results.errors.append(f"{file.path}: Public S3 bucket detected")
            results.passed = False
        
        # Encryption required for storage
        if 'aws_s3_bucket' in content and 'server_side_encryption' not in content:
            results.warnings.append(f"{file.path}: S3 bucket missing encryption config")
    
    return results
```

---

## 5. API Security

### Rate Limiting
```python
# Per-endpoint rate limits
RATE_LIMITS = {
    "/api/v1/generate":     "10/minute",     # Expensive (LLM calls)
    "/api/v1/auth/login":   "5/minute",      # Prevent brute force
    "/api/v1/auth/signup":  "3/minute",       
    "/api/v1/*":            "100/minute",     # General
}

# Per-tenant limits (based on plan)
TENANT_LIMITS = {
    "free":       {"generations/month": 50,  "projects": 3},
    "pro":        {"generations/month": 500, "projects": 20},
    "team":       {"generations/month": 2000, "projects": 100},
    "enterprise": {"generations/month": None, "projects": None},  # Unlimited
}
```

### Security Headers
```python
# backend/app/core/middleware/security.py

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",  # Deprecated, use CSP instead
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.amazonaws.com",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
```

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # ["https://app.infragen.io"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## 6. Secrets Management

### Local Development
```bash
# .env (NEVER committed — in .gitignore)
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
JWT_SECRET=<random-256-bit>
```

### Production
```
AWS Secrets Manager or HashiCorp Vault
├── infragen/prod/openai-api-key
├── infragen/prod/database-url
├── infragen/prod/jwt-secret
├── infragen/prod/github-oauth-secret
└── infragen/prod/stripe-secret-key
```

### Rules
1. **NEVER** log API keys, tokens, or secrets
2. **NEVER** include secrets in error messages or API responses
3. Rotate JWT secrets every 90 days
4. Rotate API keys on any suspected compromise
5. Use short-lived credentials where possible

---

## 7. Data Protection

### Encryption
| Data State | Method |
|---|---|
| In transit | TLS 1.3 everywhere |
| At rest (DB) | PostgreSQL TDE or AWS RDS encryption |
| At rest (S3) | AES-256 (SSE-S3) |
| Passwords | Argon2id (memory: 64MB, iterations: 3, parallelism: 1) |
| API keys | SHA-256 hash (stored), prefix for lookup |

### PII Handling
- User emails: stored encrypted-at-rest
- Prompts: stored as-is (user's infrastructure descriptions — generally not PII)
- Generated code: stored, user owns it
- Payment data: handled by Stripe, never touches our DB

### Data Retention
| Data | Retention |
|---|---|
| Active projects | Until user deletes |
| Deleted projects | Hard delete after 30-day grace period |
| Audit logs | 1 year (free), 3 years (enterprise) |
| LLM conversation logs | 90 days, then anonymized |
| Account after deletion | 30-day grace period, then purge |

---

## 8. IaC Execution Security (Terraform Validation)

### Sandboxed Execution
```
User's generated Terraform code
        │
        ▼
┌─────────────────────────┐
│  Docker Sandbox          │
│  - Read-only filesystem  │
│  - No network access     │ ← `terraform validate` only, NOT `apply`
│  - CPU/memory limits     │
│  - 30-second timeout     │
│  - Dropped capabilities  │
└─────────────────────────┘
```

```yaml
# Docker container for validation
terraform-sandbox:
  image: hashicorp/terraform:1.6
  read_only: true
  network_mode: none
  mem_limit: 256m
  cpus: 0.5
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
```

### Important: InfraGen NEVER Executes User Infrastructure
- InfraGen generates and validates code — it does NOT run `terraform apply`
- Users download code and deploy through their own pipelines
- This eliminates the risk of InfraGen provisioning unauthorized resources

---

## 9. SOC 2 Readiness Checklist (For Later)

| Control | Status | Notes |
|---|---|---|
| Access control (RBAC) | ✅ Built into MVP | Roles, permissions |
| Audit logging | ✅ Built into MVP | All actions logged |
| Encryption at rest | ✅ Infrastructure-level | RDS encryption, S3 SSE |
| Encryption in transit | ✅ TLS everywhere | Enforced via HSTS |
| Vulnerability scanning | ⬜ Post-MVP | Dependabot + Snyk |
| Penetration testing | ⬜ Post-MVP | Annual pen test |
| Incident response plan | ⬜ Post-MVP | Documented runbook |
| Business continuity | ⬜ Post-MVP | Backup/DR strategy |
| Change management | ✅ Git + PR reviews | CI/CD pipeline |
| Employee security training | ⬜ Post-MVP | Annual training |

---

## 10. Security Development Lifecycle

### Pre-Commit
- `pre-commit` hooks: no secrets (detect-secrets), linting
- Dependabot / Renovate for dependency updates

### CI Pipeline
- SAST: Bandit (Python), ESLint security plugin (TypeScript)
- Dependency audit: `pip-audit`, `npm audit`
- Container scanning: Trivy
- Generated code scanning: checkov on every test case

### Production
- WAF (Cloudflare or AWS WAF)
- DDoS protection (Cloudflare)
- Error tracking without PII (Sentry with scrubbing rules)
- Security alerts → PagerDuty/Slack
