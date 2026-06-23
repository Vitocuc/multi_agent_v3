# Security contract
<!-- Doc 1 — produced by the CTO orchestrator after shared_plan_approved = true.
     Workers MUST read this file before implementing any feature.
     Validators check each feature against the fields marked [ENFORCED].
     Do not edit after approval without bumping contract_version. -->

---

## Meta

| Field | Value |
|---|---|
| project_id | protego-life-sim-v1 |
| contract_version | 1.0 |
| created_at | 2026-06-22 |
| approved_by | CTO orchestrator |
| status | approved |

---

## Threat model

### Actors

| Actor | Trust level | Description |
|---|---|---|
| Anonymous user | none | Unauthenticated public internet visitor attempting to access protected routes, probe APIs, or enumerate user data |
| Authenticated user | low | Google-OAuth-verified beta participant with a valid session; may attempt to access other users' wallets, manipulate P-Coin balances, or bypass behavioral limits |
| Admin / developer | high | The sole developer accessing the Railway dashboard, Metabase OSS, PostgreSQL, and the admin CSV export route; must be protected from credential theft |
| Google OAuth provider | medium | External identity provider; trusted for identity assertion only; no financial data is shared with it |
| FastAPI event ingestion service | medium | Internal microservice receiving POST /events from the Next.js frontend; must reject unauthenticated or malformed payloads |
| CI/CD pipeline (GitHub Actions) | medium | Automated system with Railway deploy rights and access to GitHub Secrets; a compromised workflow could inject malicious code or exfiltrate secrets |
| Metabase OSS instance | medium | Self-hosted analytics service with read access to PostgreSQL aggregate views; must never expose raw PII rows |

### Attack vectors

| Vector | Risk level | Mitigation |
|---|---|---|
| SQL / NoSQL injection | high | Prisma ORM parameterized queries for all Next.js DB access; Pydantic-validated asyncpg parameterized queries in FastAPI; no raw string interpolation in SQL ever |
| XSS | high | Next.js React DOM escaping by default; Chakra UI renders no dangerouslySetInnerHTML; Content-Security-Policy header set to disallow inline scripts and restrict script-src to self; all user-supplied strings sanitized server-side before storage |
| CSRF | medium | NextAuth.js CSRF token enforced on all POST/mutation API routes; SameSite=Strict on session cookie; state parameter validated in Google OAuth callback |
| Broken auth / session hijack | high | HttpOnly + Secure + SameSite=Strict session cookie; JWT signed with 256-bit NEXTAUTH_SECRET stored in Railway environment variable; Redis session store with server-side invalidation on logout; short access token expiry (15 minutes) with silent refresh |
| Secrets in source code | critical | All secrets stored exclusively in Railway environment variables and GitHub Actions Secrets; .env files listed in .gitignore; pre-commit hook and GitHub Actions secret-scanning step reject commits containing credential patterns |
| Dependency vulnerabilities | medium | npm audit --audit-level=high and pip-audit run in GitHub Actions CI on every PR; PRs blocked if high or critical CVEs are unresolved; Dependabot enabled on the repository |
| Rate limit abuse on deposit simulation and Risk Arena | high | Redis sliding-window rate limiter on /api/deposit-simulation and /api/risk-arena endpoints (10 requests per minute per authenticated user); behavioral pause enforced server-side after 5 consecutive deposits within 10 minutes |
| Insecure direct object reference (IDOR) on wallet and event endpoints | high | Every API route resolves the resource owner from the verified session JWT (session.user.id) and performs a database ownership check before returning or mutating any wallet, transaction, or event record; user_id from request body is never trusted |
| P-Coin balance manipulation via replay or race condition | high | All wallet mutations executed inside atomic PostgreSQL transactions with SELECT FOR UPDATE row-level locking; idempotency key required on deposit simulation POST to prevent replay |
| Age gate bypass | medium | Date-of-birth verified server-side in NextAuth signIn callback; users born fewer than 18 years before the current UTC date receive a 403 and no session is created; DOB is re-validated on every session refresh |
| Behavioral data re-identification | high | behavioral_events hypertable stores only pseudonymous user_id UUID; no name, email, IP address, or device fingerprint stored in event rows; Metabase queries only pre-defined aggregate views with no join path to user_profiles PII table |
| Admin CSV export data exfiltration | high | /api/admin/export route protected by admin role check; exports contain only pseudonymous user_id UUIDs and event payloads; audit log event emitted on every export; route is not exposed in the public PWA navigation |
| Metabase unauthorized dashboard access | medium | Metabase OSS instance not publicly indexed; protected by Metabase account credentials stored in Railway environment variables; Metabase connects to PostgreSQL via a read-only analytics_reader role that has SELECT only on aggregate views, not on user_profiles or raw behavioral_events |

---

## Authentication  [ENFORCED]

```yaml
mechanism: OAuth2 via Google Identity Platform with NextAuth.js v4; server-side JWT session token issued after successful OAuth callback and age-gate validation
token_location: httpOnly Secure SameSite=Strict cookie named __Secure-next-auth.session-token; never exposed to JavaScript; never sent in Authorization header
token_expiry:
  access_session: 15 minutes (maxAge on NextAuth session)
  session_refresh: silent re-issue on each authenticated request within 7 days of last activity
  absolute_expiry: 7 days from last login; user must re-authenticate after 7 days regardless of activity
session_strategy: server-side session store in Redis 7 via @next-auth/upstash-redis-adapter; session ID in cookie maps to session record in Redis; invalidation is immediate on logout
mfa_required: false (MVP scope; Google account MFA is the user's own responsibility)
logout_strategy: DELETE session record from Redis on NextAuth signOut; cookie cleared with Max-Age=0; user redirected to /login
password_policy: not applicable — authentication is delegated entirely to Google OAuth; no local passwords are stored or managed by Protego
age_gate: date_of_birth collected on first onboarding step after OAuth callback; server-side check in NextAuth signIn callback rejects users under 18 years old with HTTP 403 and no session creation; DOB stored in user_profiles table (PII, access-controlled)
```

---

## Authorization  [ENFORCED]

```yaml
model: RBAC with two roles (user, admin); ownership check enforced on all resource-level operations
roles:
  user:
    - read own profile, wallet balance, wallet transactions, protection score, life layer state
    - write own deposit simulation, risk arena session, vault allocation, spending limit configuration
    - write behavioral events via FastAPI POST /events (authenticated with internal service token)
    - read own beta countdown and survey modal state
  admin:
    - all user permissions
    - read aggregate Metabase dashboards (via Metabase account, not app session)
    - trigger admin CSV export via GET /api/admin/export
    - read audit log summary via GET /api/admin/audit
    - no ability to read raw PII of other users via app routes
ownership_check: true — every API route in Next.js resolves session.user.id from the verified JWT and queries the database with WHERE user_id = session.user.id; no route accepts a user_id parameter from the request body or query string as authoritative
admin_separation: true — all /api/admin/* routes are protected by a separate adminGuard middleware that checks session.user.role === 'admin' before the route handler executes; admin routes are never reachable from the public PWA navigation
fastapi_service_auth: FastAPI POST /events requires an internal service token passed as Authorization: Bearer <INTERNAL_SERVICE_TOKEN> header; token is a 256-bit random secret stored in Railway environment variables; Next.js frontend sends this token server-side only (never exposed to the browser)
```

---

## Data security  [ENFORCED]

```yaml
at_rest:
  encryption: Railway-managed PostgreSQL volume encryption at rest using AES-256 (provider-managed disk encryption on Railway EU West Frankfurt infrastructure); Redis persistence encrypted at rest via Railway volume encryption
  pii_fields:
    - user_profiles.email
    - user_profiles.full_name
    - user_profiles.date_of_birth
    - user_profiles.google_sub (Google subject identifier)
    - user_profiles.created_at (indirectly identifying when combined with other fields)
    - sessions.session_token (stored in Redis, not PostgreSQL)
  pii_strategy: PII fields are stored exclusively in the user_profiles table; behavioral_events hypertable stores only the pseudonymous user_id UUID (a randomly generated UUID assigned at registration, not the Google sub); no PII is stored in event payloads; Metabase analytics_reader role has no SELECT permission on user_profiles; admin CSV export strips all PII columns before serialization

in_transit:
  tls_minimum: TLS 1.2 (Railway enforces TLS 1.2 minimum on all public-facing services; TLS 1.3 preferred)
  hsts: true — Strict-Transport-Security: max-age=31536000; includeSubDomains set in Next.js custom headers configuration
  certificate: Railway-managed Let's Encrypt certificate with automatic renewal on the custom domain
  internal_service_communication: FastAPI and PostgreSQL communicate over Railway's private internal network (not public internet); DATABASE_URL uses the internal Railway hostname; FastAPI to PostgreSQL connection uses SSL mode=require

secrets_management:
  tool: Railway environment variables for production secrets; GitHub Actions Secrets for CI/CD pipeline secrets; .env.local for local development only (never committed)
  never_in_code: true — no secrets, API keys, database passwords, or NEXTAUTH_SECRET appear anywhere in the source code repository; pre-commit hook using detect-secrets scans staged files and blocks commits containing credential patterns; GitHub secret scanning is enabled on the repository
  rotation_policy: NEXTAUTH_SECRET and INTERNAL_SERVICE_TOKEN rotated every 90 days or immediately upon any suspected breach; Google OAuth client secret rotated every 180 days; Railway database password rotated every 90 days; rotation procedure documented in the project README under Security Operations
```

---

## Input validation  [ENFORCED]

```yaml
strategy: |
  All Next.js API route inputs validated with Zod schemas before any business logic or database access.
  All FastAPI endpoint inputs validated with Pydantic v2 models before any database write.
  Validation is applied at the API boundary on every request; no trust is placed on client-side validation alone.
  Specific validations enforced:
    - P-Coin deposit amounts: positive integer, minimum 1, maximum equal to current wallet balance (server-side check)
    - Spending limit configuration: positive integer, minimum 100, maximum 100000
    - Protection quota: integer 0–100 representing percentage
    - Risk profile selection: enum of exactly ['prudent', 'balanced', 'growth']
    - Date of birth: ISO 8601 date string, must be a valid past date, user must be >= 18 years old
    - Event type in POST /events: enum of the 40+ defined KPI event types; unknown event types rejected with 422
    - Event payload JSONB: maximum 4096 bytes; no executable content; stripped of any PII fields before storage
    - Career tier: enum of exactly ['intern', 'junior', 'mid', 'senior', 'partner_ceo']
sanitization: |
  All string inputs stripped of leading/trailing whitespace.
  No HTML rendering of user-supplied strings anywhere in the UI; React DOM escaping is the default.
  Parameterized queries used exclusively via Prisma ORM (Next.js) and asyncpg with $1 placeholders (FastAPI); no string concatenation in SQL.
  JSONB event payloads sanitized to remove any keys matching PII field names (email, name, dob, ip) before insertion.
file_uploads:
  allowed_types: none — the MVP has no file upload feature; any POST request with Content-Type multipart/form-data is rejected with 415 Unsupported Media Type
  max_size: not applicable
  scan_for_malware: not applicable
```

---

## Rate limiting  [ENFORCED]

```yaml
global: 200 requests per minute per IP address on all Next.js routes; enforced via next-rate-limit middleware backed by Redis sliding window; exceeding the limit returns HTTP 429 with Retry-After header
auth_endpoints:
  google_oauth_initiation: 10 attempts per 15 minutes per IP; exceeding returns 429 and logs a rate_limit_breach audit event
  nextauth_callback: 10 attempts per 15 minutes per IP; brute-force on OAuth callback is mitigated by Google's own rate limiting plus this layer
  age_gate_submission: 5 attempts per 15 minutes per IP; repeated age-gate failures logged as age_gate_failure audit events
api_endpoints:
  deposit_simulation_post: 10 requests per minute per authenticated user_id; enforces behavioral pause mechanic server-side; 5 consecutive deposits within 10 minutes triggers a mandatory 5-minute cooldown returning HTTP 429 with a behavioral_pause_triggered event emitted
  risk_arena_session_post: 10 requests per minute per authenticated user_id
  wallet_read: 60 requests per minute per authenticated user_id
  event_ingestion_fastapi: 120 requests per minute per authenticated service token (internal only; not user-facing)
  admin_csv_export: 5 requests per hour per admin session; each export emits a data_export audit event
strategy: sliding window counter stored in Redis; window size and limit configurable via environment variables without code changes
store: Redis 7 on Railway EU West internal network; keys namespaced as ratelimit:{type}:{identifier} with TTL equal to the window size
```

---

## Audit logging  [ENFORCED]

```yaml
log_events:
  - auth_success: user successfully authenticated via Google OAuth and passed age gate
  - auth_failure: OAuth callback error or age gate rejection (under 18)
  - logout: user explicitly signed out
  - session_expired: session TTL exceeded and was invalidated
  - rate_limit_breach: any rate limit threshold exceeded (includes endpoint name and identifier type)
  - age_gate_failure: DOB submitted that results in under-18 rejection
  - privilege_escalation: any attempt to access an admin route without admin role
  - idor_attempt: any attempt to access a resource where session.user.id does not match the resource owner
  - data_export: admin CSV export triggered (includes admin user_id and timestamp)
  - admin_action: any write operation performed via an /api/admin/* route
  - config_change: user modifies spending limit, protection quota, or risk profile
  - terms_acceptance: user accepts terms and privacy notice during onboarding (stored as consent event in behavioral_events and in audit log)
  - consent_withdrawal: user requests data deletion (GDPR Article 17)
  - behavioral_pause_triggered: server-side cooldown enforced on deposit simulation
  - wallet_transaction: every P-Coin credit or debit with amount, type, and resulting balance
  - weekly_allocation_job: cron job execution result (success/failure, coins allocated, users affected count)
  - dependency_audit_failure: CI pipeline detected unresolved high/critical CVE (emitted to CI log, not app log)
log_format: structured JSON with fields timestamp (ISO 8601 UTC), event_type, actor_id (pseudonymous user_id UUID or 'system' for cron), ip_address_hash (SHA-256 of IP, not raw IP), resource_type, resource_id, outcome (success|failure), metadata (non-PII context object)
log_destination: stdout on Railway services → Railway's built-in log aggregation (retained 30 days on Railway); critical security events (privilege_escalation, idor_attempt, data_export) additionally written as rows in the audit_log PostgreSQL table for durable retention and Metabase visibility
retention: Railway log aggregation 30 days rolling; audit_log PostgreSQL table retained for the full 365-day beta duration plus 12 months post-beta for GDPR accountability obligations; behavioral_events hypertable retained for the full beta duration plus 12 months
pii_in_logs: false — actor_id is always the pseudonymous UUID, never email or name; IP addresses are stored only as SHA-256 hashes; no PII fields appear in any log line or audit_log row
```

---

## Dependency policy

```yaml
lock_file_required: true — package-lock.json committed for the Next.js project; poetry.lock committed for the FastAPI project; PRs that modify dependencies without updating the lock file are blocked by CI
audit_on_install: true — npm audit --audit-level=high runs in GitHub Actions on every PR for the Next.js project; pip-audit runs in GitHub Actions on every PR for the FastAPI project; Dependabot is enabled with weekly dependency update PRs for both projects; any PR introducing a high or critical CVE is blocked from merging until the vulnerability is resolved or an explicit exception is documented
allowed_licenses:
  - MIT
  - Apache-2.0
  - BSD-2-Clause
  - BSD-3-Clause
  - ISC
  - Python-2.0
  - CC0-1.0
disallowed_licenses:
  - GPL-2.0
  - GPL-3.0
  - LGPL-2.0
  - LGPL-2.1
  - LGPL-3.0
  - AGPL-3.0
  - SSPL-1.0
  - Commons-Clause
license_check_tool: license-checker (npm) and pip-licenses (Python) run in CI; PRs introducing disallowed licenses are blocked
```

---

## Security checklist (worker self-check before milestone report)

Workers MUST confirm each item before marking a feature done:

- [ ] No secrets, API keys, database passwords, or tokens appear in source code, commit history, or application logs; all secrets sourced from environment variables only
- [ ] All API route inputs validated with Zod (Next.js) or Pydantic v2 (FastAPI) schemas before any business logic or database access; validation errors return 422 with a generic message and no internal detail
- [ ] Authentication enforced on every protected Next.js API route via getServerSession; FastAPI POST /events enforces internal service token check; no route is accidentally left unauthenticated
- [ ] Ownership check (WHERE user_id = session.user.id) applied on every database query that reads or mutates user-owned resources; no user_id from request body is trusted as authoritative
- [ ] Rate limiting middleware active on all public-facing endpoints; deposit simulation and Risk Arena endpoints enforce the 10 req/min per user limit and the 5-consecutive-deposit behavioral pause
- [ ] PII fields (email, full_name, date_of_birth, google_sub) stored only in user_profiles table; behavioral_events hypertable contains only pseudonymous user_id UUID; no PII appears in event payloads, logs, or CSV exports
- [ ] All wallet mutations (P-Coin credit, debit, allocation) executed inside atomic PostgreSQL transactions with SELECT FOR UPDATE row-level locking; idempotency key validated on deposit simulation to prevent replay
- [ ] npm audit --audit-level=high and pip-audit pass with zero unresolved high or critical CVEs; all dependencies use allowed licenses only
- [ ] Error responses to clients contain only a generic error message and a request ID; no stack traces, SQL error details, or internal service names are exposed in HTTP responses
- [ ] Audit log events emitted for all actions listed in the audit logging section; audit_log PostgreSQL table rows verified for auth_success, auth_failure, privilege_escalation, idor_attempt, data_export, config_change, and terms_acceptance
- [ ] Content-Security-Policy, Strict-Transport-Security, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, and Referrer-Policy: strict-origin-when-cross-origin headers present on all Next.js responses (verified via curl or browser DevTools)
- [ ] Age gate server-side validation confirmed: test account with DOB resulting in age 17 years 364 days receives HTTP 403 and no session is created; test account with DOB resulting in exactly 18 years receives a valid session
- [ ] GDPR consent event stored in behavioral_events and audit_log on terms acceptance; data deletion endpoint (POST /api/user/delete) tested to remove user_profiles row and pseudonymize behavioral_events rows (replace user_id with a tombstone UUID)
- [ ] Metabase analytics_reader PostgreSQL role confirmed to have SELECT only on aggregate views; direct SELECT on user_profiles and raw behavioral_events returns permission denied for the analytics_reader role

---

## Amendments

| Version | Date | Changed by | Summary |
|---|---|---|---|
| 1.0 | 2026-06-22 | CTO orchestrator | Initial approved security contract for protego-life-sim-v1 MVP |
