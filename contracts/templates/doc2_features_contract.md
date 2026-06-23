# Features contract
<!-- Doc 2 — produced by the CTO orchestrator after shared_plan_approved = true.
     Each feature block is a unit of work for one worker agent.
     Workers read their assigned feature block plus doc1_security_contract.md.
     The depends_on field defines the execution DAG — a feature may only start
     when all its dependencies have milestone_status: passed. -->

---

## Meta

| Field | Value |
|---|---|
| project_id | protego-life-sim-v1 |
| contract_version | 1.0 |
| created_at | 2026-06-22 |
| total_features | 28 |
| total_milestones | 4 |

---

## Milestone map

| Milestone ID | Name | Features | Goal |
|---|---|---|---|
| M-01 | Foundation: Auth, Wallet, Event Pipeline | F-01-001, F-01-002, F-01-003, F-01-004, F-01-005, F-01-006, F-01-007 | Establish the authenticated session, P-Coin wallet, GDPR onboarding, and behavioral event ingestion pipeline so all subsequent features have a secure, instrumented base |
| M-02 | Core Game Mechanics: Risk Arena, Vault, Protection Score | F-02-001, F-02-002, F-02-003, F-02-004, F-02-005, F-02-006 | Deliver the three abstract Risk Arena mini-games, Deposit Simulation flow with behavioral alerts, Future Vault visualization, and the Protection Score engine |
| M-03 | Life Layer, Configuration, Beta Mechanics | F-03-001, F-03-002, F-03-003, F-03-004, F-03-005, F-03-006 | Implement career progression, mandatory virtual expenses, spending-limit and vault-quota configuration screens, the 365-day beta countdown, and the post-session survey modal |
| M-04 | Analytics Dashboard, Admin Tools, GDPR Compliance Endpoints | F-04-001, F-04-002, F-04-003, F-04-004, F-04-005, F-04-006, F-04-007, F-04-008, F-04-009 | Wire Metabase OSS to pre-built KPI dashboards, expose admin CSV export, implement GDPR data-export and deletion endpoints, cookie-consent banner, and complete the privacy-by-design audit |

---

## Feature blocks

---

### F-01-001 — Project Scaffold and Infrastructure Bootstrap

```yaml
feature_id:         F-01-001
title:              "Project Scaffold and Infrastructure Bootstrap"
milestone_id:       M-01
priority:           critical
complexity:         L
depends_on:         []
parallel_safe:      false
```

**Description**

Initialise the Next.js 14 App Router project with TypeScript 5, Chakra UI v2, next-i18next with Italian locale, next-pwa, Prisma ORM 5, and all required environment variable scaffolding. Simultaneously bootstrap the FastAPI 0.111 Python 3.12 event-ingestion microservice with its own pyproject.toml, Pydantic v2 models, and a GET /health endpoint. Configure all five Railway EU West Frankfurt services (Next.js, FastAPI, PostgreSQL + TimescaleDB, Redis, Metabase) with correct environment variables and confirm inter-service connectivity. Set up GitHub Actions CI with ESLint, TypeScript type-check, Prisma schema validation, and Jest unit-test steps triggered on every PR.

**Security constraints**

- Secrets: `doc1 § Secrets management — no secrets in source code; all credentials injected via Railway environment variables and GitHub Secrets`
- CI/CD: `doc1 § CI/CD pipeline security — GitHub Actions workflow must not print secrets to logs; Railway deploy token stored as GitHub Secret`
- Data residency: `doc1 § Data residency — all Railway services provisioned in EU West Frankfurt region`
- Dependency hygiene: `doc1 § Dependency management — npm audit and pip-audit must pass with zero high/critical CVEs before first deploy`

**Acceptance criteria**

- [ ] Given the repository is cloned and `.env.local` is populated, when `npm run dev` is executed, then the Next.js app starts on port 3000 with no TypeScript compilation errors and the home page returns HTTP 200.
- [ ] Given the FastAPI service is started with `uvicorn main:app`, when `GET /health` is called, then the response is `{"status": "ok"}` with HTTP 200.
- [ ] Given the GitHub Actions workflow is triggered by a PR, when ESLint, TypeScript type-check, Prisma schema validation, and Jest run, then all steps pass and no step prints any environment variable value to the workflow log.
- [ ] Given the Railway EU West Frankfurt environment is configured, when each service (Next.js, FastAPI, PostgreSQL, Redis, Metabase) starts, then each service is reachable from the others on the shared internal network and all health checks pass.
- [ ] Given the Next.js app loads in a browser, when the default locale is resolved, then all visible strings are served from the Italian (`it`) i18n namespace and no untranslated key placeholders are visible.
- [ ] Given the PWA manifest is served, when a user visits the app on an iOS or Android device, then the browser presents an "Add to Home Screen" prompt and the installed icon matches the Protego brand asset.
- [ ] Security: Given `npm audit --audit-level=high` is run against the Node.js dependency tree, then zero high or critical vulnerabilities are reported.
- [ ] Security: Given `pip-audit` is run against the Python dependency tree, then zero high or critical vulnerabilities are reported.
- [ ] Security: Given any Railway service environment variable is set, then the variable value is never echoed in application startup logs or HTTP response bodies.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-001-scaffold-infrastructure
3. Initialise Next.js 14 with `npx create-next-app@latest --typescript --app`.
4. Install and configure Chakra UI v2, next-i18next (it locale), next-pwa, Prisma 5, Zod.
5. Create FastAPI service in /services/events with pyproject.toml, main.py, GET /health.
6. Write docker-compose.dev.yml mapping all five services for local development.
7. Configure .env.example with all required keys — never commit real values.
8. Set up .github/workflows/ci.yml with ESLint, tsc --noEmit, prisma validate, jest steps.
9. Verify npm audit and pip-audit pass before opening PR.
10. Fill in doc4_milestone_report.md for this feature_id.
11. Open a PR against main. Title: "[F-01-001] Project Scaffold and Infrastructure Bootstrap".
12. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-001-scaffold-infrastructure
github_issue_id:    ""
pr_id:              ""
```

---

### F-01-002 — PostgreSQL Schema and TimescaleDB Hypertable

```yaml
feature_id:         F-01-002
title:              "PostgreSQL Schema and TimescaleDB Hypertable"
milestone_id:       M-01
priority:           critical
complexity:         M
depends_on:         [F-01-001]
parallel_safe:      false
```

**Description**

Define and apply the complete Prisma schema for all relational tables: `users`, `user_profiles`, `wallets`, `wallet_transactions`, `sessions`, `career_tiers`, `vault_allocations`, `protection_score_snapshots`, `spending_limits`, `risk_profiles`, and `consent_records`. Additionally, create the `behavioral_events` TimescaleDB hypertable via a raw SQL migration (outside Prisma's DDL) with columns `id BIGSERIAL`, `user_id UUID`, `event_type VARCHAR(64)`, `payload JSONB`, `occurred_at TIMESTAMPTZ NOT NULL` as an append-only table with no UPDATE or DELETE permissions granted to the application role. Enable TimescaleDB compression and a 90-day retention policy on `behavioral_events`.

**Security constraints**

- Database access control: `doc1 § Database security — application role granted SELECT/INSERT only on behavioral_events; no UPDATE or DELETE; separate admin role for migrations`
- PII separation: `doc1 § Privacy by design — behavioral_events stores only pseudonymous user_id UUID; no name, email, or IP address columns`
- Encryption at rest: `doc1 § Data at rest — Railway PostgreSQL volume encryption enabled`
- Input validation: `doc1 § Input validation — all schema fields have NOT NULL constraints and check constraints where applicable`

**Acceptance criteria**

- [ ] Given Prisma migrations are run against a fresh PostgreSQL 16 + TimescaleDB database, when `prisma migrate deploy` completes, then all relational tables exist with correct columns, foreign keys, and indexes and the command exits with code 0.
- [ ] Given the TimescaleDB extension is enabled, when the raw SQL migration runs `SELECT create_hypertable('behavioral_events', 'occurred_at')`, then the function returns success and `SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'behavioral_events'` returns one row.
- [ ] Given the application database role `protego_app`, when an INSERT is executed on `behavioral_events`, then the row is persisted and the INSERT returns the new row id.
- [ ] Given the application database role `protego_app`, when an UPDATE or DELETE is attempted on `behavioral_events`, then the database returns a permission-denied error and no row is modified.
- [ ] Given a `behavioral_events` row is inserted, when the row is inspected, then the columns contain only `user_id` (UUID), `event_type`, `payload` (JSONB), and `occurred_at` — no email, IP address, or name fields exist in the table definition.
- [ ] Given TimescaleDB compression policy is applied, when `SELECT * FROM timescaledb_information.compression_settings WHERE hypertable_name = 'behavioral_events'` is queried, then a compression policy row is returned.
- [ ] Security: Given a direct psql connection using the application role credentials, when `\dp behavioral_events` is run, then the privileges column shows INSERT and SELECT only — no UPDATE, DELETE, TRUNCATE, or REFERENCES.
- [ ] Security: Given the `user_profiles` table contains a row with a real email address, when a JOIN between `behavioral_events` and `user_profiles` is attempted using the application role, then the query succeeds only if the application role has been explicitly granted SELECT on `user_profiles` — by default the role must not have this grant.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-002-database-schema
3. Write the full Prisma schema in prisma/schema.prisma.
4. Create a custom SQL migration file for TimescaleDB hypertable creation and role grants.
5. Write a seed script for career_tier reference data (Intern through Partner/CEO).
6. Test migrations against the local docker-compose TimescaleDB container.
7. Verify application role permissions with psql \dp commands.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-01-002] PostgreSQL Schema and TimescaleDB Hypertable".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-002-database-schema
github_issue_id:    ""
pr_id:              ""
```

---

### F-01-003 — Google OAuth Authentication and Age Gate

```yaml
feature_id:         F-01-003
title:              "Google OAuth Authentication and Age Gate"
milestone_id:       M-01
priority:           critical
complexity:         M
depends_on:         [F-01-001, F-01-002]
parallel_safe:      false
```

**Description**

Implement NextAuth.js v4 with the Google OAuth 2.0 provider. After Google identity is confirmed, the user is redirected to a date-of-birth collection screen. The server-side NextAuth callback calculates age from the submitted DOB; if the user is under 18, the session is not created, the DOB is not persisted, and the user receives a clear rejection message in Italian. If the user is 18 or older, a pseudonymous `user_id` UUID is generated, the `users` and `user_profiles` rows are created, and a JWT session is stored in Redis via the `@next-auth/upstash-redis-adapter`. All protected Next.js App Router routes use a middleware guard that validates the session token before rendering.

**Security constraints**

- Authentication mechanism: `doc1 § Authentication — mechanism: NextAuth.js v4 Google OAuth; token_expiry: 24 hours; session stored in Redis`
- Age gate: `doc1 § Authentication — age_gate: DOB verified server-side; under-18 sessions never created`
- Session security: `doc1 § Session management — JWT signed with NEXTAUTH_SECRET; HttpOnly Secure SameSite=Strict cookies; Redis session TTL 24 hours`
- PII handling: `doc1 § Privacy by design — email stored only in user_profiles with restricted role; never in behavioral_events`
- Audit logging: `doc1 § Audit logging — log_events: [auth_success, auth_failure, age_gate_rejection]`
- Route protection: `doc1 § Authorization — all /app/* routes require valid session; middleware rejects unauthenticated requests with HTTP 401`

**Acceptance criteria**

- [ ] Given an unauthenticated user visits any `/app/*` route, when the middleware evaluates the request, then the user is redirected to `/login` with HTTP 302 and no protected content is returned.
- [ ] Given a user clicks "Accedi con Google" on the login page, when Google OAuth completes successfully, then the user is redirected to the DOB collection screen and no session cookie is set yet.
- [ ] Given a user submits a DOB indicating they are 17 years old, when the server-side age check runs, then no session is created, no user row is inserted in the database, and the response renders the Italian rejection message "Devi avere almeno 18 anni per partecipare alla beta."
- [ ] Given a user submits a DOB indicating they are 18 years or older, when the server-side age check runs, then a `users` row is created with a new UUID, a `user_profiles` row is created with the Google email, a JWT session is stored in Redis with a 24-hour TTL, and the user is redirected to the onboarding flow.
- [ ] Given a valid session cookie exists, when the NextAuth session is inspected server-side, then the session contains only the pseudonymous `user_id` UUID and no raw Google access token or email is exposed to client-side JavaScript.
- [ ] Given a session has been active for more than 24 hours, when any protected route is accessed, then the session is expired, the Redis key is deleted, and the user is redirected to `/login`.
- [ ] Given a user completes authentication, when the `behavioral_events` table is queried for that user, then an `auth_success` event row exists with the correct `user_id` UUID and `occurred_at` timestamp.
- [ ] Security: Given an attacker submits a forged JWT cookie with a valid-looking `user_id`, when the middleware validates the token, then the token signature check fails, the request is rejected with HTTP 401, and an `auth_failure` event is logged.
- [ ] Security: Given the login endpoint receives 20 rapid successive requests from the same IP within 60 seconds, when the rate limiter evaluates the requests, then requests beyond the threshold receive HTTP 429 and no additional OAuth redirects are initiated.
- [ ] Security: Given the session cookie is set, when the browser developer tools inspect the cookie attributes, then the cookie has `HttpOnly`, `Secure`, and `SameSite=Strict` flags set.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-003-google-oauth-age-gate
3. Install next-auth, @next-auth/upstash-redis-adapter, ioredis.
4. Configure NextAuth in app/api/auth/[...nextauth]/route.ts with Google provider.
5. Implement DOB collection page at /onboarding/dob with server action for age check.
6. Write Next.js middleware.ts to guard all /app/* routes.
7. Implement Redis rate limiter on the /api/auth/* routes using ioredis.
8. Write behavioral event emission for auth_success, auth_failure, age_gate_rejection.
9. Write Jest unit tests for the age calculation function covering boundary cases (exactly 18, 17 years 364 days).
10. Fill in doc4_milestone_report.md for this feature_id.
11. Open a PR against main. Title: "[F-01-003] Google OAuth Authentication and Age Gate".
12. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-003-google-oauth-age-gate
github_issue_id:    ""
pr_id:              ""
```

---

### F-01-004 — GDPR Onboarding Screen and Consent Recording

```yaml
feature_id:         F-01-004
title:              "GDPR Onboarding Screen and Consent Recording"
milestone_id:       M-01
priority:           critical
complexity:         M
depends_on:         [F-01-003]
parallel_safe:      false
```

**Description**

Immediately after age-gate approval, present the user with a mandatory multi-step onboarding screen that discloses: (1) the app is a behavioral simulator with no real money; (2) P-Coins have zero monetary value and cannot be redeemed; (3) behavioral data is actively collected for research purposes with a link to the full privacy notice; (4) the user's explicit consent is required before proceeding. Each consent item is a separate checkbox. The user cannot proceed until all checkboxes are ticked. On submission, a `consent_records` row is inserted with the `user_id`, `consent_version`, `consented_at` timestamp, and a JSONB snapshot of which items were accepted. A `gdpr_consent_given` behavioral event is also emitted to the FastAPI event pipeline.

**Security constraints**

- Consent integrity: `doc1 § Privacy by design — consent_records row is immutable after insert; no UPDATE permitted on application role`
- Audit logging: `doc1 § Audit logging — log_events: [gdpr_consent_given, onboarding_completed]`
- Data minimization: `doc1 § Privacy by design — consent snapshot stores only boolean flags per item, not free-text user input`
- Input validation: `doc1 § Input validation — all consent form fields validated server-side with Zod before database write`
- No bypass: `doc1 § Authorization — any authenticated user without a consent_records row must be redirected to onboarding before accessing any /app/* route`

**Acceptance criteria**

- [ ] Given a newly authenticated user has no `consent_records` row, when they attempt to access any `/app/*` route, then they are redirected to `/onboarding/consent` and cannot bypass it.
- [ ] Given the consent screen is displayed, when the user attempts to click "Continua" without ticking all required checkboxes, then the button remains disabled and a validation message in Italian is shown for each unticked item.
- [ ] Given all consent checkboxes are ticked and the user clicks "Continua", when the server action processes the submission, then a `consent_records` row is inserted with `user_id`, `consent_version: "1.0"`, `consented_at` (UTC timestamp), and a JSONB payload containing `{"no_real_money": true, "data_collection": true, "p_coin_no_value": true, "terms_accepted": true}`.
- [ ] Given a `consent_records` row is inserted, when an UPDATE is attempted on that row using the application database role, then the database returns a permission-denied error.
- [ ] Given the consent is submitted, when the `behavioral_events` hypertable is queried for that `user_id`, then a `gdpr_consent_given` event row exists with `occurred_at` within 5 seconds of the consent submission.
- [ ] Given the privacy notice link is clicked, when the page renders, then the full Italian-language privacy notice is displayed including the data controller identity, data categories collected, retention periods, and user rights under GDPR Article 13.
- [ ] Given a user has a valid `consent_records` row, when they access any `/app/*` route, then they are not redirected to the consent screen again.
- [ ] Security: Given a POST request to the consent submission endpoint is made without a valid session cookie, when the server processes the request, then HTTP 401 is returned and no `consent_records` row is inserted.
- [ ] Security: Given a POST request to the consent submission endpoint contains a `consent_version` field with a SQL injection payload, when Zod validation runs server-side, then the request is rejected with HTTP 400 and no database write occurs.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-004-gdpr-onboarding-consent
3. Build multi-step consent screen at /onboarding/consent using Chakra UI.
4. Write Zod schema for consent form payload.
5. Write server action to validate, insert consent_records, and emit behavioral event.
6. Update Next.js middleware to check for consent_records row after session check.
7. Write Italian privacy notice page at /privacy with all GDPR Article 13 fields.
8. Write Jest tests for consent validation logic and middleware redirect logic.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-01-004] GDPR Onboarding Screen and Consent Recording".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-004-gdpr-onboarding-consent
github_issue_id:    ""
pr_id:              ""
```

---

### F-01-005 — P-Coin Wallet Creation and Weekly Allocation Cron

```yaml
feature_id:         F-01-005
title:              "P-Coin Wallet Creation and Weekly Allocation Cron"
milestone_id:       M-01
priority:           critical
complexity:         M
depends_on:         [F-01-004]
parallel_safe:      false
```

**Description**

On completion of the GDPR onboarding screen, automatically create a `wallets` row for the user with an initial balance of 1,000 P-Coins (Intern tier). A `wallet_transactions` row of type `initial_allocation` is inserted atomically in the same PostgreSQL transaction. A `node-cron` job runs every Monday at 00:00 UTC and issues weekly P-Coin allocations to all active users based on their current `career_tier` (Intern: 1,000; Junior: 1,500; Senior: 2,000; Manager: 3,000; Partner/CEO: 4,000). Each allocation is a separate `wallet_transactions` row of type `weekly_allocation`. All wallet balance mutations use row-level locking (`SELECT ... FOR UPDATE`) to prevent race conditions. The wallet balance is never allowed to go below zero.

**Security constraints**

- Atomic transactions: `doc1 § Financial integrity — all P-Coin balance mutations wrapped in PostgreSQL transactions with row-level locking; no balance can go negative`
- Idempotency: `doc1 § Financial integrity — weekly allocation cron uses a unique constraint on (user_id, week_start_date, transaction_type) to prevent duplicate allocations`
- Authorization: `doc1 § Authorization — wallet balance and transactions readable only by the owning user_id; no cross-user wallet access`
- Audit logging: `doc1 § Audit logging — log_events: [wallet_created, weekly_allocation_issued, allocation_cron_run]`
- Input validation: `doc1 § Input validation — career_tier values validated against the career_tiers reference table; no arbitrary amounts accepted`

**Acceptance criteria**

- [ ] Given a user completes GDPR onboarding, when the server action finalises onboarding, then a `wallets` row is created with `balance = 1000` and a `wallet_transactions` row of type `initial_allocation` with `amount = 1000` is inserted in the same atomic transaction.
- [ ] Given the wallet creation transaction fails midway (simulated by rolling back), when the transaction is rolled back, then neither the `wallets` row nor the `wallet_transactions` row exists in the database.
- [ ] Given the cron job runs on Monday at 00:00 UTC, when an active Intern-tier user exists, then a `wallet_transactions` row of type `weekly_allocation` with `amount = 1000` is inserted and the wallet `balance` is incremented by 1,000.
- [ ] Given the cron job runs twice in the same week for the same user (simulated duplicate run), when the second insert is attempted, then the unique constraint on `(user_id, week_start_date, transaction_type)` raises a conflict and no duplicate allocation row is inserted.
- [ ] Given a wallet balance is 50 P-Coins and a deduction of 100 P-Coins is attempted, when the transaction runs, then the transaction is rolled back, the balance remains 50, and an `insufficient_balance` error is returned.
- [ ] Given User A is authenticated, when User A's session calls the wallet balance API endpoint with User B's `user_id`, then HTTP 403 is returned and User B's balance is not disclosed.
- [ ] Given the cron job completes, when the `behavioral_events` table is queried, then an `allocation_cron_run` event exists with a payload containing `{"users_processed": N, "week_start_date": "YYYY-MM-DD"}`.
- [ ] Security: Given a direct POST to the wallet mutation API endpoint without a valid session, when the server processes the request, then HTTP 401 is returned and no wallet row is modified.
- [ ] Security: Given a POST to the wallet mutation endpoint with a crafted `amount` field containing a negative number, when Zod validation runs, then HTTP 400 is returned and no database write occurs.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-005-wallet-weekly-allocation
3. Write Prisma wallet and wallet_transactions models with unique constraint.
4. Write wallet creation server action called from onboarding completion.
5. Implement node-cron job in a dedicated /jobs/weeklyAllocation.ts module.
6. Write wallet balance query API route with user_id ownership check.
7. Write Jest unit tests for allocation logic, negative balance guard, and idempotency.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-01-005] P-Coin Wallet Creation and Weekly Allocation Cron".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-005-wallet-weekly-allocation
github_issue_id:    ""
pr_id:              ""
```

---

### F-01-006 — FastAPI Behavioral Event Ingestion Service

```yaml
feature_id:         F-01-006
title:              "FastAPI Behavioral Event Ingestion Service"
milestone_id:       M-01
priority:           critical
complexity:         M
depends_on:         [F-01-002]
parallel_safe:      true
```

**Description**

Implement the FastAPI 0.111 Python 3.12 event-ingestion microservice that receives behavioral events from the Next.js frontend and bulk-inserts them into the `behavioral_events` TimescaleDB hypertable. The service exposes `POST /events` accepting a JSON array of event objects validated by Pydantic v2 models. Each event must contain `user_id` (UUID), `event_type` (string from an allowlist of 40+ KPI event types), `payload` (arbitrary JSONB), and `occurred_at` (ISO 8601 UTC timestamp). The service authenticates incoming requests using a shared internal API key passed as a Bearer token in the `Authorization` header. The service must handle bulk inserts of up to 50 events per request using asyncpg connection pooling.

**Security constraints**

- Internal service authentication: `doc1 § Service-to-service authentication — FastAPI POST /events requires Authorization: Bearer {INTERNAL_API_KEY}; key stored as Railway environment variable; never hardcoded`
- Input validation: `doc1 § Input validation — event_type validated against a Pydantic Literal allowlist; user_id validated as UUID4; payload size capped at 4 KB per event`
- Append-only enforcement: `doc1 § Database security — service uses INSERT only; no UPDATE or DELETE statements exist in the codebase`
- Rate limiting: `doc1 § Rate limiting — POST /events rate-limited to 200 requests per minute per calling service IP`
- Audit logging: `doc1 § Audit logging — log_events: [event_batch_received, event_batch_inserted, event_validation_failed]`

**Acceptance criteria**

- [ ] Given a valid POST request to `/events` with `Authorization: Bearer {INTERNAL_API_KEY}` and a JSON array of 3 valid event objects, when the endpoint processes the request, then all 3 rows are inserted into `behavioral_events` and HTTP 201 is returned with `{"inserted": 3}`.
- [ ] Given a POST request to `/events` without an `Authorization` header, when the endpoint processes the request, then HTTP 401 is returned and no rows are inserted.
- [ ] Given a POST request to `/events` with an `event_type` value not in the allowlist (e.g., `"arbitrary_event"`), when Pydantic validation runs, then HTTP 422 is returned with a validation error body and no rows are inserted.
- [ ] Given a POST request to `/events` with a `user_id` that is not a valid UUID4 format, when Pydantic validation runs, then HTTP 422 is returned and no rows are inserted.
- [ ] Given a POST request to `/events` with a `payload` field exceeding 4 KB, when Pydantic validation runs, then HTTP 422 is returned and no rows are inserted.
- [ ] Given a valid batch of 50 events is posted, when the bulk insert runs using asyncpg, then all 50 rows are inserted in a single database round-trip and the response time is under 500 ms.
- [ ] Given `GET /health` is called, when the service is running and the database connection pool is healthy, then HTTP 200 is returned with `{"status": "ok", "db": "connected"}`.
- [ ] Given 201 rapid POST requests arrive from the same IP within 60 seconds, when the rate limiter evaluates the 201st request, then HTTP 429 is returned.
- [ ] Security: Given a POST request to `/events` with an `Authorization` header containing a SQL injection payload as the Bearer token, when the token validation runs, then HTTP 401 is returned and no database query is executed.
- [ ] Security: Given the FastAPI service logs are inspected after a successful request, then the `INTERNAL_API_KEY` value does not appear anywhere in the log output.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-006-fastapi-event-ingestion
3. Create /services/events/main.py with FastAPI app, Pydantic models, asyncpg pool.
4. Define the full 40+ event_type allowlist as a Pydantic Literal type in models.py.
5. Implement Bearer token middleware for internal API key validation.
6. Implement slowapi rate limiter on POST /events.
7. Write pytest tests for all validation cases, auth rejection, and bulk insert.
8. Write Dockerfile for the events service.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-01-006] FastAPI Behavioral Event Ingestion Service".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-006-fastapi-event-ingestion
github_issue_id:    ""
pr_id:              ""
```

---

### F-01-007 — Risk Profile and Onboarding Profile Completion

```yaml
feature_id:         F-01-007
title:              "Risk Profile and Onboarding Profile Completion"
milestone_id:       M-01
priority:           high
complexity:         S
depends_on:         [F-01-005, F-01-006]
parallel_safe:      false
```

**Description**

After wallet creation, present the final onboarding steps: (1) risk profile selection (Prudent / Balanced / Growth) with clear Italian-language descriptions of what each means in terms of Future Vault scenario variance (±2%, ±5%, ±10%); (2) initial monthly spending limit configuration (user sets a P-Coin amount between 100 and their full weekly allocation); (3) initial Future Vault protection quota selection (user selects a percentage of weekly allocation to auto-protect: 10%, 20%, 30%, 40%, 50%). On submission, the `user_profiles` row is updated with the selected `risk_profile`, a `spending_limits` row is created, and a `vault_allocations` row is created. A `onboarding_completed` behavioral event is emitted.

**Security constraints**

- Input validation: `doc1 § Input validation — risk_profile validated as enum (PRUDENT, BALANCED, GROWTH); spending_limit validated as integer between 100 and user's weekly allocation amount; vault_quota validated as enum (10, 20, 30, 40, 50)`
- Authorization: `doc1 § Authorization — profile update endpoint verifies session user_id matches the profile being updated; no cross-user profile modification`
- Audit logging: `doc1 § Audit logging — log_events: [risk_profile_selected, spending_limit_set, vault_quota_set, onboarding_completed]`

**Acceptance criteria**

- [ ] Given the risk profile selection screen is displayed, when the user selects "Prudente" and clicks "Continua", then the `user_profiles.risk_profile` field is updated to `PRUDENT` and the selection is persisted.
- [ ] Given the spending limit screen is displayed, when the user enters a value of 50 (below the minimum of 100), then a validation error in Italian is shown and the form cannot be submitted.
- [ ] Given the spending limit screen is displayed, when the user enters a value greater than their weekly allocation, then a validation error in Italian is shown and the form cannot be submitted.
- [ ] Given valid risk profile, spending limit, and vault quota are submitted, when the server action runs, then a `spending_limits` row and a `vault_allocations` row are created and the `user_profiles` row is updated in a single atomic transaction.
- [ ] Given onboarding is completed, when the `behavioral_events` table is queried, then `risk_profile_selected`, `spending_limit_set`, `vault_quota_set`, and `onboarding_completed` event rows exist for that `user_id`.
- [ ] Given onboarding is completed, when the user is redirected to `/app/dashboard`, then the dashboard displays the selected risk profile badge, the current spending limit, and the vault quota percentage.
- [ ] Security: Given a POST to the profile update endpoint with a `user_id` in the body that differs from the session `user_id`, when the server processes the request, then HTTP 403 is returned and no profile row is modified.
- [ ] Security: Given a POST to the profile update endpoint with `risk_profile: "ADMIN_OVERRIDE"`, when Zod validation runs, then HTTP 400 is returned and no database write occurs.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-01-007-risk-profile-onboarding
3. Build three-step onboarding wizard pages at /onboarding/risk-profile, /onboarding/spending-limit, /onboarding/vault-quota.
4. Write Zod schemas for each step's form payload.
5. Write server action for atomic profile completion transaction.
6. Emit behavioral events via FastAPI event service client.
7. Write Jest tests for validation boundary cases.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-01-007] Risk Profile and Onboarding Profile Completion".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-01-007-risk-profile-onboarding
github_issue_id:    ""
pr_id:              ""
```

---

### F-02-001 — Deposit Simulation Flow and Behavioral Alerts

```yaml
feature_id:         F-02-001
title:              "Deposit Simulation Flow and Behavioral Alerts"
milestone_id:       M-02
priority:           critical
complexity:         L
depends_on:         [F-01-007]
parallel_safe:      false
```

**Description**

Implement the Deposit Simulation intercept screen that appears every time a user attempts to transfer P-Coins into the Risk Arena. The screen displays: the requested deposit amount, the risk/protection split (how much of the deposit would come from the protected vault vs. free balance), the current monthly spending total vs. the spending limit, and a behavioral alert if the user is within 20% of their monthly limit or has made 3 or more deposits in the last 10 minutes. The user is presented with five action options: Confirm, Reduce Amount, Take a Pause (30-minute cooldown), Review Budget, or Go to Vault. Each action emits a distinct behavioral event. The Confirm action proceeds to the Risk Arena. The Pause action sets a Redis key with a 30-minute TTL that blocks further deposits.

**Security constraints**

- Atomic transactions: `doc1 § Financial integrity — deposit amount deducted from wallet atomically only after Confirm action; no partial deductions`
- Rate limiting: `doc1 § Rate limiting — deposit simulation endpoint rate-limited to 10 requests per minute per user_id to enforce behavioral pause mechanics`
- Input validation: `doc1 § Input validation — deposit amount validated as positive integer not exceeding current wallet balance; Zod schema enforced server-side`
- Authorization: `doc1 § Authorization — deposit endpoint verifies session user_id owns the wallet being debited`
- Audit logging: `doc1 § Audit logging — log_events: [deposit_initiated, deposit_confirmed, deposit_reduced, deposit_paused, deposit_cancelled, spending_limit_alert_shown, rapid_deposit_alert_shown]`

**Acceptance criteria**

- [ ] Given a user initiates a Risk Arena deposit of 200 P-Coins, when the Deposit Simulation screen renders, then it displays the deposit amount (200), the current monthly spending total, the monthly spending limit, and the remaining allowance.
- [ ] Given the user's monthly spending total is within 20% of their spending limit, when the Deposit Simulation screen renders, then a yellow alert banner in Italian is displayed warning the user they are approaching their limit.
- [ ] Given the user has made 3 or more deposits in the last 10 minutes, when the Deposit Simulation screen renders, then a red alert banner in Italian is displayed warning of rapid consecutive deposits.
- [ ] Given the user clicks "Conferma", when the server action runs, then the deposit amount is atomically deducted from the wallet balance, a `wallet_transactions` row of type `risk_arena_deposit` is inserted, and a `deposit_confirmed` behavioral event is emitted.
- [ ] Given the user clicks "Prendi una Pausa", when the server action runs, then a Redis key `pause:{user_id}` is set with a 30-minute TTL, no P-Coins are deducted, and a `deposit_paused` behavioral event is emitted.
- [ ] Given a `pause:{user_id}` Redis key exists, when the user attempts to initiate another deposit, then the Deposit Simulation screen is blocked and a countdown timer showing remaining pause time is displayed.
- [ ] Given the user clicks "Riduci Importo", when the reduced amount form is submitted, then the Deposit Simulation screen re-renders with the new amount and updated risk/protection split.
- [ ] Given a deposit amount exceeding the current wallet balance is submitted, when Zod validation runs server-side, then HTTP 400 is returned and no wallet deduction occurs.
- [ ] Security: Given a POST to the deposit confirm endpoint with a `wallet_id` belonging to another user, when the server processes the request, then HTTP 403 is returned and no deduction occurs.
- [ ] Security: Given a POST to the deposit confirm endpoint is made 11 times within 60 seconds by the same user, when the rate limiter evaluates the 11th request, then HTTP 429 is returned.
- [ ] Security: Given a POST to the deposit confirm endpoint with `amount: -500`, when Zod validation runs, then HTTP 400 is returned and no database write occurs.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-02-001-deposit-simulation-alerts
3. Build /app/deposit/simulate page with Chakra UI components.
4. Write server action for deposit confirmation with atomic wallet deduction.
5. Implement Redis pause key logic with TTL and countdown display.
6. Implement rapid-deposit detection query (3+ deposits in last 10 minutes).
7. Implement spending-limit proximity alert (within 20% of limit).
8. Emit all 7 behavioral event types via FastAPI event client.
9. Write Jest tests for alert trigger logic and pause enforcement.
10. Fill in doc4_milestone_report.md for this feature_id.
11. Open a PR against main. Title: "[F-02-001] Deposit Simulation Flow and Behavioral Alerts".
12. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-02-001-deposit-simulation-alerts
github_issue_id:    ""
pr_id:              ""
```

---

### F-02-002 — Risk Arena: Three Abstract Mini-Games

```yaml
feature_id:         F-02-002
title:              "Risk Arena: Three Abstract Mini-Games"
milestone_id:       M-02
priority:           critical
complexity:         XL
depends_on:         [F-02-001]
parallel_safe:      false
```

**Description**

Implement the three abstract Risk Arena mini-games: (1) Binary Choice — the user picks one of two abstract symbols; server generates a cryptographically secure random outcome; 50% win probability; (2) Symbolic Card Flip — the user selects one of five face-down abstract cards; one card is the "win" card; 20% win probability; (3) Random Wheel — a spinning wheel with 8 abstract segments of varying multipliers (0×, 0.5×, 1×, 1.5×, 2×, 2.5×, 3×, 5×) with weighted probabilities summing to 1.0. All outcomes are generated server-side using Node.js `crypto.randomInt`. The UI animates the result client-side after receiving the server response. Win/loss amounts are applied to the wallet atomically. No real-world gambling references, casino names, card suits, or sports references appear anywhere in the UI or code.

**Security constraints**

- Cryptographic randomness: `doc1 § Game integrity — all Risk Arena outcomes generated server-side using Node.js crypto.randomInt or Python secrets module; no client-side random generation`
- Atomic transactions: `doc1 § Financial integrity — win/loss amounts applied to wallet in atomic PostgreSQL transaction; outcome and wallet mutation in same transaction`
- No manipulation: `doc1 § Game integrity — outcome is generated and committed to database before result is returned to client; no client-supplied outcome accepted`
- Input validation: `doc1 § Input validation — game_type validated as enum (BINARY_CHOICE, CARD_FLIP, RANDOM_WHEEL); selected_option validated against valid options for each game type`
- Audit logging: `doc1 § Audit logging — log_events: [game_started, game_outcome_win, game_outcome_loss, game_outcome_multiplier]`
- Abstract content: `doc1 § Regulatory compliance — no real-world gambling mechanics, casino names, card suits, sports references, or real-odds feeds in UI or codebase`

**Acceptance criteria**

- [ ] Given a user has confirmed a deposit via the Deposit Simulation flow, when they enter the Risk Arena and select Binary Choice, then the game screen displays two abstract symbols with no real-world gambling references and no card suits or casino imagery.
- [ ] Given the user makes a selection in Binary Choice, when the server processes the game, then the outcome is generated using `crypto.randomInt(0, 2)` server-side, the result is committed to the database before the response is sent, and the client receives the outcome in the response body.
- [ ] Given 10,000 Binary Choice game outcomes are simulated in a unit test, when the win/loss distribution is calculated, then the win rate is between 45% and 55% (within expected statistical variance of a 50% probability).
- [ ] Given the user wins a Binary Choice game with a 200 P-Coin deposit, when the wallet transaction is applied, then the wallet balance increases by 200 P-Coins (net +200 from the win) and a `wallet_transactions` row of type `risk_arena_win` with `amount = 200` is inserted atomically.
- [ ] Given the user loses a Binary Choice game with a 200 P-Coin deposit, when the wallet transaction is applied, then the wallet balance reflects the loss (deposit was already deducted in F-02-001) and a `wallet_transactions` row of type `risk_arena_loss` is inserted.
- [ ] Given the Random Wheel game is played, when the server generates the outcome, then the selected segment multiplier is applied to the deposit amount and the resulting P-Coin delta is applied atomically to the wallet.
- [ ] Given a POST to the game outcome endpoint with a client-supplied `outcome: "win"` field in the request body, when the server processes the request, then the client-supplied outcome is ignored and the server-generated outcome is used exclusively.
- [ ] Given the Risk Arena UI is inspected, when all text, images, and component names are reviewed, then no references to real casinos, roulette, blackjack, poker, sports teams, real odds, or prediction markets are found.
- [ ] Security: Given a POST to the game play endpoint without a valid session, when the server processes the request, then HTTP 401 is returned and no game outcome is generated or wallet modified.
- [ ] Security: Given a POST to the game play endpoint with `game_type: "SLOT_MACHINE"` (not in the allowlist), when Zod validation runs, then HTTP 400 is returned and no game is played.
- [ ] Security: Given a POST to the game play endpoint is made 15 times within 60 seconds by the same user, when the rate limiter evaluates the 15th request, then HTTP 429 is returned.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-02-002-risk-arena-mini-games
3. Build /app/risk-arena page with game selection and three game sub-pages.
4. Implement server-side outcome generation using crypto.randomInt for all three games.
5. Write atomic wallet mutation transaction for win/loss application.
6. Build client-side animation components (no real gambling imagery).
7. Write Zod schemas for game play request validation.
8. Write Jest unit tests for probability distribution (10,000 simulations per game).
9. Write Jest tests for client-supplied outcome rejection.
10. Fill in doc4_milestone_report.md for this feature_id.
11. Open a PR against main. Title: "[F-02-002] Risk Arena: Three Abstract Mini-Games".
12. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-02-002-risk-arena-mini-games
github_issue_id:    ""
pr_id:              ""
```

---

### F-02-003 — Future Vault

```yaml
feature_id:         F-02-003
title:              "Future Vault"
milestone_id:       M-02
priority:           high
complexity:         M
depends_on:         [F-01-007]
parallel_safe:      true
```

**Description**

Implement the Future Vault feature: a protected P-Coin balance that is automatically funded each week according to the user's selected vault quota percentage. The vault balance is stored in a separate `vault_balance` column on the `wallets` table. The vault screen visualises the protected balance, displays three simulated annual scenario projections (pessimistic, neutral, optimistic) based on the user's risk profile variance (Prudent ±2%, Balanced ±5%, Growth ±10%), and translates the virtual capital into tangible goal proxies (e.g., "Equivale a 3 settimane di affitto virtuale" or "Copre 2 mesi di spese di emergenza virtuali"). The vault balance cannot be used in the Risk Arena directly; a separate explicit withdrawal flow is required.

**Security constraints**

- Atomic transactions: `doc1 § Financial integrity — vault funding deducted from free balance and added to vault_balance in single atomic transaction`
- Authorization: `doc1 § Authorization — vault balance readable and modifiable only by the owning user_id`
- Input validation: `doc1 § Input validation — vault withdrawal amount validated as positive integer not exceeding vault_balance`
- Audit logging: `doc1 § Audit logging — log_events: [vault_funded, vault_withdrawal_initiated, vault_balance_viewed]`
- No real financial instruments: `doc1 § Regulatory compliance — vault scenario projections are clearly labelled as simulated virtual scenarios with no real financial value`

**Acceptance criteria**

- [ ] Given the weekly allocation cron runs, when a user has a vault quota of 20%, then 20% of their weekly allocation is automatically transferred to `vault_balance` and a `vault_funded` behavioral event is emitted.
- [ ] Given a user with the Balanced risk profile views the vault screen, when the scenario projections are displayed, then three projections are shown (pessimistic at −5%, neutral at 0%, optimistic at +5%) with Italian labels and a disclaimer stating these are virtual simulations with no real financial value.
- [ ] Given the vault screen is displayed, when the goal proxy section renders, then at least two tangible goal proxy strings are shown (e.g., weeks of virtual rent covered, months of virtual emergency fund) calculated from the current vault balance.
- [ ] Given a user attempts to use vault balance directly in the Risk Arena deposit flow, when the deposit simulation runs, then the vault balance is excluded from the available deposit amount and a message in Italian explains that vault funds are protected.
- [ ] Given a user initiates a vault withdrawal of 500 P-Coins, when the server action runs, then 500 P-Coins are atomically moved from `vault_balance` to the free wallet balance and a `wallet_transactions` row of type `vault_withdrawal` is inserted.
- [ ] Given a vault withdrawal of an amount exceeding `vault_balance` is attempted, when Zod validation runs server-side, then HTTP 400 is returned and no balance change occurs.
- [ ] Security: Given a POST to the vault withdrawal endpoint with another user's `wallet_id`, when the server processes the request, then HTTP 403 is returned and no vault balance is modified.
- [ ] Security: Given the vault scenario projection API is called, when the response is inspected, then no real financial instrument names, real interest rates, or real investment products are referenced in the response body.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-02-003-future-vault
3. Add vault_balance column to wallets table via Prisma migration.
4. Update weekly allocation cron to split allocation between free balance and vault.
5. Build /app/vault page with balance display, scenario projections, and goal proxies.
6. Write vault withdrawal server action with atomic transaction.
7. Write scenario projection calculation utility for all three risk profiles.
8. Write Jest tests for scenario calculation and vault funding split.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-02-003] Future Vault".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-02-003-future-vault
github_issue_id:    ""
pr_id:              ""
```

---

### F-02-004 — Protection Score Engine

```yaml
feature_id:         F-02-004
title:              "Protection Score Engine"
milestone_id:       M-02
priority:           critical
complexity:         L
depends_on:         [F-02-001, F-02-003]
parallel_safe:      false
```

**Description**

Implement the Protection Score composite metric engine. The score is calculated on demand and stored as a daily snapshot in `protection_score_snapshots`. The six weighted components are: (1) Limit Respect 30% — ratio of months where spending stayed within limit; (2) Vault Maintenance 20% — ratio of weeks where vault quota was not withdrawn; (3) Pause/Alert Acceptance 15% — ratio of behavioral alerts where the user chose Pause or Review Budget over Confirm; (4) Daily Expense Management 15% — ratio of Life Layer expense periods where mandatory expenses were paid on time; (5) Anti-Impulsive Behavior 10% — inverse of rapid-deposit alert frequency; (6) Continuity and Mission Completion 10% — ratio of active days and completed missions. The final score is a 0–100 integer. The score is displayed prominently on the dashboard with a breakdown of each component.

**Security constraints**

- Authorization: `doc1 § Authorization — Protection Score readable only by the owning user_id; no cross-user score access`
- Data integrity: `doc1 § Financial integrity — score calculation reads only from append-only behavioral_events and wallet_transactions; no score can be manually overridden via API`
- Audit logging: `doc1 § Audit logging — log_events: [protection_score_calculated, protection_score_viewed]`
- Input validation: `doc1 § Input validation — no external input accepted for score calculation; all inputs sourced from database records`

**Acceptance criteria**

- [ ] Given a user has respected their spending limit for all months since registration, when the Protection Score is calculated, then the Limit Respect component contributes its full 30 points to the score.
- [ ] Given a user has never withdrawn from their vault, when the Protection Score is calculated, then the Vault Maintenance component contributes its full 20 points.
- [ ] Given a user has accepted 8 out of 10 behavioral alerts (chose Pause or Review Budget), when the Protection Score is calculated, then the Pause/Alert Acceptance component contributes 12 points (80% of 15).
- [ ] Given the Protection Score is calculated, when the result is stored, then a `protection_score_snapshots` row is inserted with `user_id`, `score` (0–100 integer), `component_breakdown` (JSONB with all six component scores), and `calculated_at` timestamp.
- [ ] Given the dashboard renders, when the Protection Score section is displayed, then the total score (0–100) and all six component scores with their weights are visible in Italian.
- [ ] Given a user's score is calculated twice on the same day, when the second calculation runs, then the existing snapshot for that day is updated (upsert) rather than creating a duplicate row.
- [ ] Given a POST request to a hypothetical score override endpoint, when the server processes the request, then HTTP 404 is returned (no such endpoint exists) and no score row is modified.
- [ ] Security: Given a GET request to the Protection Score API with another user's `user_id` as a query parameter, when the server processes the request, then HTTP 403 is returned and no score data is disclosed.
- [ ] Security: Given the Protection Score calculation function is called, when it executes, then it reads exclusively from `behavioral_events` and `wallet_transactions` using parameterized queries and no raw string interpolation is used in any SQL.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-02-004-protection-score-engine
3. Write the ProtectionScoreCalculator class/module with six component functions.
4. Write the daily snapshot upsert logic in a server action.
5. Build the Protection Score dashboard widget at /app/dashboard/protection-score.
6. Write Jest unit tests for each component calculation with known input/output pairs.
7. Write integration test verifying score cannot be externally overridden.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-02-004] Protection Score Engine".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-02-004-protection-score-engine
github_issue_id:    ""
pr_id:              ""
```

---

### F-02-005 — Dashboard Home Screen

```yaml
feature_id:         F-02-005
title:              "Dashboard Home Screen"
milestone_id:       M-02
priority:           high
complexity:         M
depends_on:         [F-02-004, F-02-002]
parallel_safe:      false
```

**Description**

Implement the main `/app/dashboard` home screen that aggregates and displays the user's current state: P-Coin wallet balance (free + vault), current Protection Score with component breakdown, current career tier and weekly allocation, monthly spending progress bar vs. limit, quick-access buttons to Risk Arena, Future Vault, and Life Layer, and the 365-day beta countdown timer. All data is fetched server-side via Next.js App Router server components to avoid exposing raw API endpoints to the client. The dashboard is the first screen shown after onboarding completion and after every subsequent login.

**Security constraints**

- Authorization: `doc1 § Authorization — dashboard server components fetch data using the session user_id only; no user_id accepted from URL parameters or query strings`
- Data minimization: `doc1 § Privacy by design — dashboard renders only aggregated summary data; no raw behavioral event rows are exposed to the client`
- Audit logging: `doc1 § Audit logging — log_events: [dashboard_viewed]`

**Acceptance criteria**

- [ ] Given a user completes onboarding and is redirected to `/app/dashboard`, when the page renders, then the wallet balance, Protection Score, career tier, monthly spending progress, and beta countdown timer are all visible.
- [ ] Given the dashboard renders, when the wallet balance section is inspected, then both the free balance and the vault balance are displayed separately with Italian labels.
- [ ] Given the dashboard renders, when the monthly spending progress bar is inspected, then it shows the current month's total spending as a percentage of the spending limit with a colour change to yellow at 80% and red at 100%.
- [ ] Given the dashboard renders, when the beta countdown timer is inspected, then it displays the number of days remaining in the 365-day beta calculated from the first user registration date stored in the database.
- [ ] Given the dashboard page is requested with a `?user_id=other-uuid` query parameter, when the server component fetches data, then it ignores the query parameter and fetches data exclusively for the session user_id.
- [ ] Given the dashboard renders, when the page HTML source is inspected, then no raw behavioral event rows, email addresses, or internal database IDs other than the pseudonymous UUID are present in the rendered HTML.
- [ ] Security: Given an unauthenticated GET request to `/app/dashboard`, when the middleware evaluates the request, then HTTP 302 redirect to `/login` is returned and no dashboard content is rendered.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-02-005-dashboard-home
3. Build /app/dashboard/page.tsx as a Next.js server component.
4. Implement server-side data fetching for wallet, score, career, spending, countdown.
5. Build Chakra UI dashboard layout with all required sections.
6. Implement beta countdown calculation from first registration date.
7. Write Jest tests for countdown calculation and spending progress percentage.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-02-005] Dashboard Home Screen".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-02-005-dashboard-home
github_issue_id:    ""
pr_id:              ""
```

---

### F-02-006 — Spending Limit and Vault Quota Configuration Screens

```yaml
feature_id:         F-02-006
title:              "Spending Limit and Vault Quota Configuration Screens"
milestone_id:       M-02
priority:           medium
complexity:         S
depends_on:         [F-01-007]
parallel_safe:      true
```

**Description**

Implement the post-onboarding configuration screens accessible from the dashboard settings menu that allow users to update their monthly spending limit and vault protection quota at any time. Changes take effect from the next calendar month for the spending limit and from the next weekly allocation for the vault quota. Each change is recorded as a new row in `spending_limits` and `vault_allocations` respectively (append-only history), and a behavioral event is emitted for each change.

**Security constraints**

- Input validation: `doc1 § Input validation — spending_limit validated as integer between 100 and current weekly allocation; vault_quota validated as enum (10, 20, 30, 40, 50)`
- Authorization: `doc1 § Authorization — configuration update endpoint verifies session user_id owns the configuration being modified`
- Audit logging: `doc1 § Audit logging — log_events: [spending_limit_updated, vault_quota_updated]`

**Acceptance criteria**

- [ ] Given a user navigates to `/app/settings/spending-limit`, when they enter a new valid spending limit and save, then a new `spending_limits` row is inserted with `effective_from` set to the first day of the next calendar month.
- [ ] Given a user navigates to `/app/settings/vault-quota`, when they select a new vault quota percentage and save, then a new `vault_allocations` row is inserted with `effective_from` set to the next Monday.
- [ ] Given a user submits a spending limit of 50 (below minimum), when Zod validation runs, then HTTP 400 is returned and no new row is inserted.
- [ ] Given a configuration change is saved, when the `behavioral_events` table is queried, then the corresponding event (`spending_limit_updated` or `vault_quota_updated`) exists with the old and new values in the payload JSONB.
- [ ] Given the settings screen renders, when the current spending limit and vault quota are displayed, then they reflect the most recently effective values (not future-dated pending changes).
- [ ] Security: Given a POST to the spending limit update endpoint with another user's `user_id` in the body, when the server processes the request, then HTTP 403 is returned and no row is inserted.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-02-006-configuration-screens
3. Build /app/settings/spending-limit and /app/settings/vault-quota pages.
4. Write server actions for each configuration update with effective_from logic.
5. Write Zod schemas for both configuration forms.
6. Emit behavioral events for each change.
7. Write Jest tests for effective_from date calculation logic.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-02-006] Spending Limit and Vault Quota Configuration Screens".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-02-006-configuration-screens
github_issue_id:    ""
pr_id:              ""
```

---

### F-03-001 — Life Layer: Career Progression and Virtual Expenses

```yaml
feature_id:         F-03-001
title:              "Life Layer: Career Progression and Virtual Expenses"
milestone_id:       M-03
priority:           high
complexity:         L
depends_on:         [F-01-005, F-02-004]
parallel_safe:      false
```

**Description**

Implement the Life Layer system with five career tiers (Intern 1,000/week, Junior 1,500/week, Senior 2,000/week, Manager 3,000/week, Partner/CEO 4,000/week). Career progression is triggered when the user's Protection Score reaches defined thresholds (Intern→Junior: 30, Junior→Senior: 50, Senior→Manager: 65, Manager→Partner/CEO: 80) and is never triggered by Risk Arena wins. Each week, mandatory virtual expenses are deducted from the free wallet balance: virtual rent, virtual bills, virtual groceries, and a random virtual emergency (10% probability each week). If the user cannot cover mandatory expenses, a `life_layer_expense_missed` behavioral event is emitted and the Protection Score's Daily Expense Management component is penalised. The Life Layer screen displays the current career tier, weekly income, expense breakdown, and progression requirements.

**Security constraints**

- Atomic transactions: `doc1 § Financial integrity — mandatory expense deductions applied atomically; partial deductions not permitted`
- Authorization: `doc1 § Authorization — career tier and expense data readable only by the owning user_id`
- No real-money references: `doc1 § Regulatory compliance — all expense amounts are P-Coin denominated; no real currency amounts displayed`
- Audit logging: `doc1 § Audit logging — log_events: [career_tier_advanced, life_layer_expense_deducted, life_layer_expense_missed, virtual_emergency_triggered]`

**Acceptance criteria**

- [ ] Given a user's Protection Score reaches 30, when the Protection Score snapshot is saved, then the user's `career_tier` is updated from `INTERN` to `JUNIOR` and the weekly allocation is updated to 1,500 P-Coins.
- [ ] Given a user wins a large amount in the Risk Arena, when career tier eligibility is evaluated, then the career tier does not advance based on Risk Arena wins alone — only Protection Score thresholds trigger advancement.
- [ ] Given the weekly expense deduction cron runs, when a user has sufficient free balance, then virtual rent, bills, and groceries are deducted atomically and a `life_layer_expense_deducted` event is emitted for each expense category.
- [ ] Given the weekly expense deduction cron runs and the random emergency probability triggers (simulated by seeding the RNG), when the emergency deduction is applied, then a `virtual_emergency_triggered` behavioral event is emitted with the emergency amount in the payload.
- [ ] Given a user's free balance is insufficient to cover mandatory expenses, when the expense deduction runs, then the deduction is skipped, a `life_layer_expense_missed` event is emitted, and the Protection Score Daily Expense Management component is penalised in the next calculation.
- [ ] Given the Life Layer screen renders, when the career progression section is displayed, then the current tier, current weekly income, and the Protection Score threshold required for the next tier are shown in Italian.
- [ ] Security: Given a POST to a hypothetical career tier override endpoint, when the server processes the request, then HTTP 404 is returned (no such endpoint exists).
- [ ] Security: Given the expense deduction cron runs, when the deduction amounts are calculated, then they are sourced exclusively from the `career_tiers` reference table and no client-supplied amounts are accepted.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-03-001-life-layer-career-expenses
3. Add career_tier column to users table via Prisma migration.
4. Write career progression trigger logic called from Protection Score snapshot save.
5. Implement weekly expense deduction cron job with atomic transactions.
6. Implement virtual emergency random trigger using crypto.randomInt.
7. Build /app/life-layer page with career tier display and expense breakdown.
8. Write Jest tests for career progression thresholds and expense deduction logic.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-03-001] Life Layer: Career Progression and Virtual Expenses".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-03-001-life-layer-career-expenses
github_issue_id:    ""
pr_id:              ""
```

---

### F-03-002 — Mission System

```yaml
feature_id:         F-03-002
title:              "Mission System"
milestone_id:       M-03
priority:           medium
complexity:         M
depends_on:         [F-03-001]
parallel_safe:      false
```

**Description**

Implement a mission system that provides intrinsic motivation for disciplined behavior. Missions are predefined behavioral objectives (e.g., "Rispetta il tuo limite di spesa per 4 settimane consecutive", "Mantieni il Vault per 30 giorni senza prelievi", "Accetta 5 pause consecutive"). Missions are stored in a `missions` reference table and tracked per user in `user_missions`. Mission completion is evaluated daily by a cron job that queries `behavioral_events`. Completing a mission awards a P-Coin bonus (deposited to free balance) and contributes to the Continuity and Mission Completion component of the Protection Score. Missions are displayed on a dedicated `/app/missions` page with progress indicators.

**Security constraints**

- Authorization: `doc1 § Authorization — user_missions data readable only by the owning user_id`
- No manipulation: `doc1 § Game integrity — mission completion evaluated exclusively from behavioral_events records; no client-supplied completion claims accepted`
- Audit logging: `doc1 § Audit logging — log_events: [mission_started, mission_completed, mission_reward_issued]`
- Atomic transactions: `doc1 § Financial integrity — mission reward P-Coin bonus applied atomically with mission completion status update`

**Acceptance criteria**

- [ ] Given a mission "Rispetta il limite per 4 settimane" is active for a user, when the daily mission evaluation cron runs and the user has respected their limit for 4 consecutive weeks (verified from `behavioral_events`), then the `user_missions` row is updated to `status: COMPLETED` and a P-Coin bonus is atomically credited to the wallet.
- [ ] Given a mission is completed, when the `behavioral_events` table is queried, then `mission_completed` and `mission_reward_issued` events exist with the mission ID and reward amount in the payload.
- [ ] Given the missions page renders, when a user views an active mission, then a progress indicator shows the current progress (e.g., "3 di 4 settimane completate") in Italian.
- [ ] Given a POST request to a hypothetical mission completion endpoint with `mission_id` and `completed: true` in the body, when the server processes the request, then HTTP 404 is returned (no such endpoint exists) and mission completion is evaluated only by the cron job.
- [ ] Given a mission reward is issued, when the wallet balance is inspected, then the balance has increased by the mission reward amount and a `wallet_transactions` row of type `mission_reward` is present.
- [ ] Security: Given a GET request to the user missions API with another user's `user_id`, when the server processes the request, then HTTP 403 is returned and no mission data is disclosed.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-03-002-mission-system
3. Write Prisma models for missions and user_missions tables.
4. Seed missions reference table with at least 10 predefined missions.
5. Write daily mission evaluation cron job querying behavioral_events.
6. Write atomic mission completion and reward transaction.
7. Build /app/missions page with progress indicators.
8. Write Jest tests for mission completion evaluation logic.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-03-002] Mission System".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-03-002-mission-system
github_issue_id:    ""
pr_id:              ""
```

---

### F-03-003 — 365-Day Beta Countdown Timer

```yaml
feature_id:         F-03-003
title:              "365-Day Beta Countdown Timer"
milestone_id:       M-03
priority:           medium
complexity:         S
depends_on:         [F-02-005]
parallel_safe:      true
```

**Description**

Implement the 365-day beta countdown timer displayed on the dashboard. The countdown start date is the `created_at` timestamp of the first user registration in the `users` table. The remaining days are calculated server-side on each dashboard render. When fewer than 30 days remain, a yellow warning banner is displayed. When the beta expires (0 days remaining), a full-screen modal informs users the beta has ended and data collection is complete, and all game interactions are disabled. The countdown is also displayed in the Metabase analytics dashboard for the admin.

**Security constraints**

- Authorization: `doc1 § Authorization — beta start date is read-only; no endpoint exists to modify it`
- Audit logging: `doc1 § Audit logging — log_events: [beta_30_day_warning_shown, beta_expired]`

**Acceptance criteria**

- [ ] Given the first user registered on a known date, when the dashboard renders, then the countdown displays the correct number of days remaining calculated as `365 - (today - first_registration_date)`.
- [ ] Given 335 days have elapsed since the first registration, when the dashboard renders, then a yellow warning banner in Italian is displayed stating "Mancano meno di 30 giorni alla fine della beta."
- [ ] Given 365 or more days have elapsed since the first registration, when any authenticated user accesses any `/app/*` route, then a full-screen modal is displayed in Italian stating the beta has ended and all Risk Arena and deposit buttons are disabled.
- [ ] Given the beta expiry modal is displayed, when the user inspects the page, then no game interaction buttons are clickable and no deposit simulation can be initiated.
- [ ] Security: Given a POST to a hypothetical beta reset endpoint, when the server processes the request, then HTTP 404 is returned (no such endpoint exists) and the first registration date is not modified.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-03-003-beta-countdown-timer
3. Write server-side countdown calculation utility reading first users.created_at.
4. Integrate countdown display into dashboard server component.
5. Implement 30-day warning banner and beta-expired modal.
6. Disable game interaction buttons when beta is expired.
7. Write Jest tests for countdown calculation including boundary cases (day 334, 335, 365, 366).
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-03-003] 365-Day Beta Countdown Timer".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-03-003-beta-countdown-timer
github_issue_id:    ""
pr_id:              ""
```

---

### F-03-004 — Post-Session Survey Modal

```yaml
feature_id:         F-03-004
title:              "Post-Session Survey Modal"
milestone_id:       M-03
priority:           low
complexity:         S
depends_on:         [F-02-002]
parallel_safe:      true
```

**Description**

Implement a post-session survey modal that appears after a user completes a Risk Arena session (defined as exiting the Risk Arena after at least one game play). The modal displays a brief Italian-language prompt and a button linking to an external Google Form survey. The modal appears at most once per 7-day period per user to avoid survey fatigue. The last survey prompt date is stored in `user_profiles`. A `survey_prompt_shown` behavioral event is emitted each time the modal is displayed, and a `survey_link_clicked` event is emitted if the user clicks the link.

**Security constraints**

- Authorization: `doc1 § Authorization — survey prompt state readable and writable only by the owning user_id`
- External link safety: `doc1 § Output encoding — Google Form URL is a hardcoded constant in environment variables; no user-supplied URLs are rendered`
- Audit logging: `doc1 § Audit logging — log_events: [survey_prompt_shown, survey_link_clicked, survey_prompt_dismissed]`

**Acceptance criteria**

- [ ] Given a user completes at least one Risk Arena game and exits the Risk Arena, when the post-session flow runs, then the survey modal is displayed if the user has not seen it in the last 7 days.
- [ ] Given a user saw the survey modal 3 days ago, when they complete another Risk Arena session, then the survey modal is not displayed.
- [ ] Given the survey modal is displayed and the user clicks the survey link, when the link is followed, then it opens the hardcoded Google Form URL in a new tab and a `survey_link_clicked` behavioral event is emitted.
- [ ] Given the survey modal is displayed and the user dismisses it, when the `behavioral_events` table is queried, then a `survey_prompt_dismissed` event exists and the `user_profiles.last_survey_prompt_at` field is updated.
- [ ] Given the survey modal renders, when the link href is inspected, then it matches exactly the `NEXT_PUBLIC_SURVEY_URL` environment variable value and no user-supplied URL is used.
- [ ] Security: Given a POST to the survey state update endpoint with another user's `user_id`, when the server processes the request, then HTTP 403 is returned and no `user_profiles` row is modified.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-03-004-post-session-survey-modal
3. Add last_survey_prompt_at column to user_profiles via Prisma migration.
4. Add NEXT_PUBLIC_SURVEY_URL to environment variable schema.
5. Build survey modal Chakra UI component triggered from Risk Arena exit flow.
6. Write server action to update last_survey_prompt_at and emit events.
7. Write Jest tests for 7-day suppression logic.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-03-004] Post-Session Survey Modal".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-03-004-post-session-survey-modal
github_issue_id:    ""
pr_id:              ""
```

---

### F-03-005 — Cookie Consent Banner

```yaml
feature_id:         F-03-005
title:              "Cookie Consent Banner"
milestone_id:       M-03
priority:           high
complexity:         S
depends_on:         [F-01-001]
parallel_safe:      true
```

**Description**

Implement a GDPR-compliant cookie consent banner displayed to all users on first visit before any non-essential cookies or tracking scripts are loaded. The banner presents three categories: strictly necessary (always on), functional (session management), and analytics (behavioral event tracking). Users must explicitly accept or reject non-essential categories. The consent choice is stored in a `cookie_consent` cookie (HttpOnly, Secure, SameSite=Strict) and in the `consent_records` table linked to the user_id if authenticated. The banner is implemented in Italian and complies with the Italian Garante guidelines on cookie consent.

**Security constraints**

- Cookie security: `doc1 § Session management — cookie_consent cookie set with HttpOnly, Secure, SameSite=Strict flags`
- Consent integrity: `doc1 § Privacy by design — analytics scripts and behavioral event emission are gated behind analytics consent; no tracking before consent`
- Audit logging: `doc1 § Audit logging — log_events: [cookie_consent_accepted, cookie_consent_rejected, cookie_consent_partial]`
- GDPR compliance: `doc1 § Privacy by design — consent granular per category; pre-ticked boxes not permitted; reject-all option must be as prominent as accept-all`

**Acceptance criteria**

- [ ] Given a first-time visitor loads any page, when the page renders, then the cookie consent banner is displayed before any analytics scripts or behavioral event tracking is initialised.
- [ ] Given the cookie consent banner is displayed, when the user inspects the UI, then the "Rifiuta tutto" (reject all) button is as visually prominent as the "Accetta tutto" (accept all) button and no checkbox is pre-ticked.
- [ ] Given the user clicks "Rifiuta tutto", when the consent is processed, then only strictly necessary cookies are set, no analytics scripts are loaded, and a `cookie_consent_rejected` behavioral event is NOT emitted (since analytics consent was rejected).
- [ ] Given the user clicks "Accetta tutto", when the consent is processed, then the `cookie_consent` cookie is set with `HttpOnly`, `Secure`, and `SameSite=Strict` flags and behavioral event tracking is initialised.
- [ ] Given an authenticated user accepts analytics cookies, when the consent is recorded, then a `consent_records` row is inserted with `consent_type: "cookie_analytics"` and `consented_at` timestamp.
- [ ] Given the cookie consent banner has been accepted, when the user revisits the site, then the banner is not shown again and the previously chosen consent state is respected.
- [ ] Security: Given the cookie consent banner renders, when the page HTML is inspected, then no analytics tracking pixel, third-party script, or behavioral event call is present in the DOM before the user has interacted with the banner.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-03-005-cookie-consent-banner
3. Build CookieConsentBanner Chakra UI component loaded in the root layout.
4. Implement consent state management gating analytics initialisation.
5. Write server action to persist consent to consent_records for authenticated users.
6. Write Jest tests for consent gating logic (analytics not loaded before consent).
7. Fill in doc4_milestone_report.md for this feature_id.
8. Open a PR against main. Title: "[F-03-005] Cookie Consent Banner".
9. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-03-005-cookie-consent-banner
github_issue_id:    ""
pr_id:              ""
```

---

### F-03-006 — Italian i18n Completeness Pass

```yaml
feature_id:         F-03-006
title:              "Italian i18n Completeness Pass"
milestone_id:       M-03
priority:           medium
complexity:         S
depends_on:         [F-03-001, F-03-002, F-03-003, F-03-004, F-03-005]
parallel_safe:      false
```

**Description**

Perform a complete Italian localisation audit across all implemented screens. Ensure every user-facing string, error message, validation message, alert, modal, and button label is served from the `it` i18n namespace via next-i18next and no hardcoded English strings remain in any component. Add missing translation keys, review Italian copy for clarity and appropriateness for the behavioral finance context, and ensure all GDPR-related text (privacy notice, consent labels, data rights) is legally accurate in Italian.

**Security constraints**

- No sensitive data in translation files: `doc1 § Secrets management — translation JSON files must not contain API keys, internal URLs, or any configuration values`
- Output encoding: `doc1 § Output encoding — all translated strings rendered via React's JSX escaping; no dangerouslySetInnerHTML used for translated content`

**Acceptance criteria**

- [ ] Given the Italian locale is active, when every implemented screen is visited in sequence, then no untranslated key placeholder (e.g., `common.button.confirm`) is visible in the UI.
- [ ] Given a Zod validation error is triggered on any form, when the error message renders, then it is displayed in Italian and sourced from the `it` i18n namespace.
- [ ] Given the privacy notice page renders, when the content is reviewed, then all GDPR Article 13 required fields (data controller, purposes, legal basis, retention, user rights, DPA contact) are present in Italian.
- [ ] Given the translation JSON files are inspected, when they are scanned for secrets, then no API keys, internal service URLs, database connection strings, or environment variable values are present.
- [ ] Given any translated string is rendered in a React component, when the component source is inspected, then `dangerouslySetInnerHTML` is not used for any translated content.
- [ ] Security: Given the i18n translation files are served as static assets, when the files are fetched directly via HTTP, then they contain no sensitive configuration data or internal system information.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-03-006-i18n-completeness
3. Run a grep for hardcoded Italian or English strings in all .tsx and .ts files.
4. Move all hardcoded strings to /public/locales/it/*.json namespace files.
5. Review all GDPR-related copy with reference to GDPR Article 13 requirements.
6. Scan translation files for accidental secret inclusion.
7. Write Jest snapshot tests for key screens to catch future i18n regressions.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-03-006] Italian i18n Completeness Pass".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-03-006-i18n-completeness
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-001 — Metabase OSS KPI Dashboard Setup

```yaml
feature_id:         F-04-001
title:              "Metabase OSS KPI Dashboard Setup"
milestone_id:       M-04
priority:           high
complexity:         M
depends_on:         [F-01-006, F-01-002]
parallel_safe:      true
```

**Description**

Configure the self-hosted Metabase OSS 0.49 instance on Railway EU West to connect to the PostgreSQL database and build pre-configured dashboards covering all five KPI categories: acquisition (registrations, age-gate rejections, onboarding completion rate), activation (first deposit rate, first game play rate, Protection Score at day 7), behavioral (deposit confirmation rate, pause acceptance rate, alert response distribution, rapid deposit frequency), retention (DAU/WAU/MAU, 7-day and 30-day retention, session length), and investor (total active users, Protection Score distribution, career tier distribution, vault funding rate). All Metabase queries must use aggregate views or materialized views — no raw PII rows are exposed. Metabase admin access is protected by a strong password and is not publicly accessible.

**Security constraints**

- No PII in dashboards: `doc1 § Privacy by design — all Metabase questions query only aggregate views or pseudonymous user_id counts; no email, name, or DOB columns in any dashboard`
- Access control: `doc1 § Authorization — Metabase admin account protected by strong password; Metabase instance not publicly accessible without VPN or Railway private networking`
- Data residency: `doc1 § Data residency — Metabase instance runs on Railway EU West Frankfurt; no data leaves EU`
- Audit logging: `doc1 § Audit logging — Metabase audit log enabled to track dashboard access`

**Acceptance criteria**

- [ ] Given the Metabase instance is running on Railway EU West, when the admin navigates to the database connection settings, then the connection to the PostgreSQL instance is active and the connection test returns success.
- [ ] Given the Metabase acquisition dashboard is opened, when the charts render, then registration count, age-gate rejection count, and onboarding completion rate are displayed as time-series charts with daily granularity.
- [ ] Given the Metabase behavioral dashboard is opened, when the deposit confirmation rate chart renders, then it shows the ratio of `deposit_confirmed` events to `deposit_initiated` events over time.
- [ ] Given any Metabase question is inspected, when the underlying SQL query is reviewed, then no query selects the `email`, `date_of_birth`, or `full_name` columns from any table.
- [ ] Given the Metabase instance URL is accessed without authentication, when the login page renders, then no dashboard data is visible and a login form is presented.
- [ ] Given the Metabase admin password is inspected in the Railway environment variables, when the password is evaluated, then it is at least 16 characters and contains uppercase, lowercase, digits, and special characters.
- [ ] Security: Given a Metabase question attempts to query the `user_profiles` table directly for email addresses, when the query is executed using the Metabase database role, then the query returns a permission-denied error because the Metabase role has SELECT only on aggregate views.
- [ ] Security: Given the Metabase instance is deployed, when a port scan is performed from outside the Railway private network, then only the configured Metabase port is reachable and no PostgreSQL or Redis ports are directly exposed.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-001-metabase-kpi-dashboards
3. Create PostgreSQL aggregate views for each KPI category (no PII columns).
4. Create a metabase_reader database role with SELECT only on aggregate views.
5. Configure Metabase Railway service with MB_DB_* environment variables.
6. Set Metabase admin password via MB_ADMIN_PASSWORD environment variable.
7. Create all five KPI dashboard collections in Metabase with pre-built questions.
8. Document dashboard access instructions in README.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-04-001] Metabase OSS KPI Dashboard Setup".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-001-metabase-kpi-dashboards
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-002 — Admin CSV Export Route

```yaml
feature_id:         F-04-002
title:              "Admin CSV Export Route"
milestone_id:       M-04
priority:           high
complexity:         M
depends_on:         [F-01-006, F-01-002]
parallel_safe:      true
```

**Description**

Implement a protected admin-only Next.js API route `GET /api/admin/export/events` that streams a CSV export of the `behavioral_events` hypertable filtered by date range query parameters. The route is protected by an `ADMIN_API_KEY` Bearer token (separate from the internal event ingestion key). The CSV contains only pseudonymous columns: `user_id`, `event_type`, `payload`, `occurred_at`. No PII columns are included. The export supports optional `from` and `to` ISO 8601 date parameters and a `event_type` filter parameter. Large exports are streamed using Node.js streams to avoid memory exhaustion. The route is rate-limited to 5 requests per hour.

**Security constraints**

- Admin authentication: `doc1 § Authorization — admin export route requires Authorization: Bearer {ADMIN_API_KEY}; key stored as Railway environment variable; minimum 32 characters`
- No PII in export: `doc1 § Privacy by design — CSV export contains only user_id UUID, event_type, payload JSONB, occurred_at; no email, name, IP, or DOB columns`
- Rate limiting: `doc1 § Rate limiting — admin export endpoint rate-limited to 5 requests per hour per IP`
- Input validation: `doc1 § Input validation — from, to, and event_type query parameters validated with Zod; SQL injection prevented by parameterized queries`
- Audit logging: `doc1 § Audit logging — log_events: [admin_export_requested, admin_export_completed, admin_export_unauthorized]`

**Acceptance criteria**

- [ ] Given a GET request to `/api/admin/export/events` with a valid `Authorization: Bearer {ADMIN_API_KEY}` header and `from=2026-01-01&to=2026-12-31` parameters, when the route processes the request, then a CSV file is streamed with headers `user_id,event_type,payload,occurred_at` and rows matching the date range.
- [ ] Given a GET request to `/api/admin/export/events` without an `Authorization` header, when the route processes the request, then HTTP 401 is returned and no CSV data is streamed.
- [ ] Given a GET request to `/api/admin/export/events` with a `from` parameter containing a SQL injection payload (e.g., `'; DROP TABLE behavioral_events; --`), when Zod validation runs, then HTTP 400 is returned and no database query is executed.
- [ ] Given the CSV export is streamed, when the CSV content is inspected, then no column contains email addresses, full names, dates of birth, or IP addresses.
- [ ] Given 6 GET requests to the admin export endpoint arrive within 60 minutes from the same IP, when the rate limiter evaluates the 6th request, then HTTP 429 is returned.
- [ ] Given a valid export request is processed, when the `behavioral_events` table is queried for admin audit events, then an `admin_export_requested` event and an `admin_export_completed` event exist with the export parameters in the payload.
- [ ] Security: Given the `ADMIN_API_KEY` environment variable is set to a value shorter than 32 characters, when the application starts, then a startup validation error is thrown and the application refuses to start.
- [ ] Security: Given the admin export CSV is downloaded and opened, when all columns are inspected, then the `user_id` column contains only UUID4 format values and no personally identifiable information.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-002-admin-csv-export
3. Create /app/api/admin/export/events/route.ts with streaming CSV response.
4. Implement ADMIN_API_KEY Bearer token middleware.
5. Write Zod schema for from, to, event_type query parameters.
6. Implement Node.js Readable stream for large CSV exports.
7. Add startup validation for ADMIN_API_KEY minimum length.
8. Write Jest tests for auth rejection, parameter validation, and PII absence.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-04-002] Admin CSV Export Route".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-002-admin-csv-export
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-003 — GDPR Data Export Endpoint (Right of Access)

```yaml
feature_id:         F-04-003
title:              "GDPR Data Export Endpoint (Right of Access)"
milestone_id:       M-04
priority:           high
complexity:         M
depends_on:         [F-01-004, F-01-006]
parallel_safe:      true
```

**Description**

Implement a user-facing GDPR Article 15 data export endpoint `POST /api/user/data-export` that allows an authenticated user to request a JSON export of all personal data held about them. The export includes: `user_profiles` row (email, DOB, risk_profile, career_tier), `consent_records` rows, `wallet_transactions` rows, `protection_score_snapshots` rows, and a count of `behavioral_events` rows by event_type (not the raw payload, to minimise data volume). The export is generated asynchronously, stored temporarily in a signed URL for 24 hours, and the user is notified via an in-app notification. A `data_export_requested` behavioral event is emitted. The endpoint is rate-limited to 1 request per 30 days per user.

**Security constraints**

- Authorization: `doc1 § Authorization — data export endpoint verifies session user_id; export contains only the requesting user's own data`
- Rate limiting: `doc1 § Rate limiting — data export endpoint rate-limited to 1 request per 30 days per user_id`
- Secure delivery: `doc1 § Data at rest — export file stored with a time-limited signed URL (24-hour TTL); not stored permanently`
- Audit logging: `doc1 § Audit logging — log_events: [data_export_requested, data_export_ready, data_export_downloaded]`
- No cross-user data: `doc1 § Authorization — export query uses session user_id as the sole filter; no user_id accepted from request body`

**Acceptance criteria**

- [ ] Given an authenticated user submits a POST to `/api/user/data-export`, when the request is processed, then a background job is queued, a `data_export_requested` event is emitted, and HTTP 202 is returned with `{"message": "La tua esportazione dati è in elaborazione."}`.
- [ ] Given the export job completes, when the export JSON is generated, then it contains the user's `user_profiles` data, `consent_records`, `wallet_transactions`, `protection_score_snapshots`, and a `behavioral_events_summary` object with event counts by type — not raw event payloads.
- [ ] Given the export is ready, when the user accesses the in-app notification, then a download link is displayed that expires after 24 hours.
- [ ] Given a user has already requested a data export within the last 30 days, when they submit another POST to `/api/user/data-export`, then HTTP 429 is returned with an Italian message stating when the next export will be available.
- [ ] Given a POST to `/api/user/data-export` with a `user_id` field in the request body that differs from the session user_id, when the server processes the request, then the body field is ignored and the export is generated exclusively for the session user_id.
- [ ] Given the export JSON is downloaded and inspected, when the `behavioral_events_summary` section is reviewed, then it contains only `{"event_type": "...", "count": N}` objects and no raw JSONB payload data.
- [ ] Security: Given a POST to `/api/user/data-export` without a valid session, when the server processes the request, then HTTP 401 is returned and no export job is queued.
- [ ] Security: Given the signed export URL is inspected, when the URL is accessed after 24 hours, then HTTP 403 or HTTP 410 is returned and the export file is no longer accessible.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-003-gdpr-data-export
3. Create /app/api/user/data-export/route.ts with async job queuing.
4. Implement export job using node-cron or a simple async queue.
5. Write export JSON assembly function with all required data categories.
6. Implement signed URL generation with 24-hour TTL (use Railway volume or S3-compatible storage).
7. Implement 30-day rate limit per user_id using Redis.
8. Write Jest tests for cross-user isolation and rate limiting.
9. Fill in doc4_milestone_report.md for this feature_id.
10. Open a PR against main. Title: "[F-04-003] GDPR Data Export Endpoint".
11. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-003-gdpr-data-export
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-004 — GDPR Data Deletion Endpoint (Right to Erasure)

```yaml
feature_id:         F-04-004
title:              "GDPR Data Deletion Endpoint (Right to Erasure)"
milestone_id:       M-04
priority:           high
complexity:         M
depends_on:         [F-04-003]
parallel_safe:      false
```

**Description**

Implement a user-facing GDPR Article 17 data deletion endpoint `POST /api/user/delete-account` that allows an authenticated user to request deletion of their account and all associated personal data. The deletion process: (1) immediately invalidates the user's session in Redis; (2) hard-deletes the `user_profiles` row (PII); (3) hard-deletes the `users` row; (4) hard-deletes `consent_records`, `spending_limits`, `vault_allocations`, `wallet_transactions`, and `wallets` rows; (5) pseudonymises `behavioral_events` rows by replacing the `user_id` with a static tombstone UUID `00000000-0000-0000-0000-000000000000` (preserving aggregate research value while removing linkability); (6) emits a `account_deletion_completed` event using the tombstone UUID before the deletion completes. The user is shown a confirmation modal in Italian before the deletion is executed.

**Security constraints**

- Authorization: `doc1 § Authorization — deletion endpoint verifies session user_id; no user_id accepted from request body`
- Session invalidation: `doc1 § Session management — user's Redis session key deleted immediately on deletion request`
- Audit trail: `doc1 § Audit logging — account_deletion_completed event emitted with tombstone UUID before PII deletion; provides audit trail without PII`
- Confirmation required: `doc1 § Authorization — deletion requires explicit confirmation token submitted in the same request to prevent CSRF-triggered deletion`
- Atomic deletion: `doc1 § Financial integrity — all PII table deletions wrapped in a single PostgreSQL transaction; partial deletion not permitted`

**Acceptance criteria**

- [ ] Given an authenticated user navigates to account deletion, when the confirmation modal renders, then it displays an Italian warning stating all data will be deleted and requires the user to type "ELIMINA" to confirm.
- [ ] Given the user types "ELIMINA" and submits the deletion request, when the server processes the request, then the session is invalidated in Redis, all PII rows are deleted in a single atomic transaction, and the user is redirected to the home page.
- [ ] Given the deletion transaction completes, when the `behavioral_events` table is queried for the original `user_id`, then zero rows are returned.
- [ ] Given the deletion transaction completes, when the `behavioral_events` table is queried for the tombstone UUID `00000000-0000-0000-0000-000000000000`, then the previously linked event rows exist with the tombstone UUID and the original `user_id` is not recoverable.
- [ ] Given the deletion transaction fails midway (simulated rollback), when the transaction is rolled back, then all PII rows remain intact and no partial deletion has occurred.
- [ ] Given the deletion is complete, when the user attempts to log in again with the same Google account, then a new account is created from scratch (no residual data from the deleted account).
- [ ] Security: Given a POST to `/api/user/delete-account` without the `confirmation_token: "ELIMINA"` field, when the server processes the request, then HTTP 400 is returned and no deletion occurs.
- [ ] Security: Given a POST to `/api/user/delete-account` without a valid session, when the server processes the request, then HTTP 401 is returned and no deletion occurs.
- [ ] Security: Given a POST to `/api/user/delete-account` with a `user_id` field in the body that differs from the session user_id, when the server processes the request, then the body field is ignored and only the session user's data is deleted.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-004-gdpr-data-deletion
3. Create /app/api/user/delete-account/route.ts.
4. Implement confirmation token validation (must equal "ELIMINA").
5. Write atomic deletion transaction covering all PII tables.
6. Implement behavioral_events pseudonymisation UPDATE to tombstone UUID.
7. Implement Redis session invalidation on deletion.
8. Build confirmation modal Chakra UI component.
9. Write Jest tests for partial rollback safety, tombstone replacement, and auth rejection.
10. Fill in doc4_milestone_report.md for this feature_id.
11. Open a PR against main. Title: "[F-04-004] GDPR Data Deletion Endpoint".
12. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-004-gdpr-data-deletion
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-005 — Security Headers and CSP Configuration

```yaml
feature_id:         F-04-005
title:              "Security Headers and CSP Configuration"
milestone_id:       M-04
priority:           high
complexity:         S
depends_on:         [F-01-001]
parallel_safe:      true
```

**Description**

Configure all required HTTP security headers on the Next.js application via `next.config.js` headers configuration. Required headers: `Content-Security-Policy` (restricting script sources to self and the Google OAuth domain only), `Strict-Transport-Security` (max-age 31536000, includeSubDomains), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (disabling camera, microphone, geolocation). The CSP must not use `unsafe-inline` or `unsafe-eval` for scripts. Nonce-based CSP is used for any inline scripts required by Next.js.

**Security constraints**

- Security headers: `doc1 § HTTP security headers — all six headers required; CSP must not include unsafe-inline or unsafe-eval for script-src`
- HSTS: `doc1 § HTTP security headers — HSTS max-age minimum 31536000 with includeSubDomains`
- CSP: `doc1 § HTTP security headers — CSP script-src restricted to self and accounts.google.com; nonce-based for Next.js inline scripts`

**Acceptance criteria**

- [ ] Given the Next.js application is running, when an HTTP response is inspected for any page, then the `Strict-Transport-Security` header is present with `max-age=31536000; includeSubDomains`.
- [ ] Given the Next.js application is running, when an HTTP response is inspected, then the `X-Frame-Options: DENY` header is present.
- [ ] Given the Next.js application is running, when an HTTP response is inspected, then the `X-Content-Type-Options: nosniff` header is present.
- [ ] Given the Next.js application is running, when the `Content-Security-Policy` header is inspected, then `script-src` does not contain `unsafe-inline` or `unsafe-eval` and is restricted to `'self'` and `https://accounts.google.com`.
- [ ] Given the Next.js application is running, when the `Permissions-Policy` header is inspected, then `camera=()`, `microphone=()`, and `geolocation=()` are all present.
- [ ] Given the application is scanned with the Mozilla Observatory tool (or equivalent), when the scan completes, then the security grade is A or higher.
- [ ] Security: Given an attempt to load a script from an external domain not in the CSP allowlist, when the browser evaluates the CSP, then the script is blocked and a CSP violation is reported.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-005-security-headers-csp
3. Configure all security headers in next.config.js headers() function.
4. Implement nonce generation middleware for Next.js inline scripts.
5. Test CSP with browser developer tools to confirm no violations on normal page load.
6. Run Mozilla Observatory scan against staging deployment.
7. Write Jest tests asserting header presence in API route responses.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-04-005] Security Headers and CSP Configuration".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-005-security-headers-csp
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-006 — Global Rate Limiting and DDoS Protection

```yaml
feature_id:         F-04-006
title:              "Global Rate Limiting and DDoS Protection"
milestone_id:       M-04
priority:           high
complexity:         S
depends_on:         [F-01-001, F-01-003]
parallel_safe:      true
```

**Description**

Implement global rate limiting across all Next.js API routes using a Redis-backed rate limiter (using the `@upstash/ratelimit` or `ioredis` sliding window algorithm). Define per-route rate limit tiers: authentication endpoints (20 req/min per IP), deposit simulation (10 req/min per user_id), game play (15 req/min per user_id), event ingestion (200 req/min per service IP), admin export (5 req/hour per IP), data export (1 req/30 days per user_id). All rate limit rejections return HTTP 429 with a `Retry-After` header and an Italian error message. Rate limit counters are stored in Redis with appropriate TTLs.

**Security constraints**

- Rate limiting: `doc1 § Rate limiting — all API routes covered; Redis sliding window algorithm; HTTP 429 with Retry-After header on rejection`
- DDoS mitigation: `doc1 § Rate limiting — global 100 req/min per IP ceiling applied before route-specific limits`
- Audit logging: `doc1 § Audit logging — log_events: [rate_limit_exceeded]`

**Acceptance criteria**

- [ ] Given 21 POST requests to `/api/auth/signin` arrive from the same IP within 60 seconds, when the rate limiter evaluates the 21st request, then HTTP 429 is returned with a `Retry-After` header and an Italian error message.
- [ ] Given 101 requests of any type arrive from the same IP within 60 seconds, when the global rate limiter evaluates the 101st request, then HTTP 429 is returned regardless of the specific endpoint.
- [ ] Given a rate limit is exceeded, when the HTTP 429 response is inspected, then the `Retry-After` header is present with the number of seconds until the limit resets.
- [ ] Given a rate limit rejection occurs, when the `behavioral_events` table is queried, then a `rate_limit_exceeded` event exists with the endpoint and IP hash (not raw IP) in the payload.
- [ ] Given the rate limit window expires (simulated by advancing Redis TTL), when the next request arrives, then the counter resets and the request is processed normally.
- [ ] Security: Given the rate limit counter is stored in Redis, when the Redis key is inspected, then it contains only a numeric counter and TTL — no raw IP addresses or user PII are stored as Redis key values (IP is hashed before use as key).

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-006-global-rate-limiting
3. Implement Redis sliding window rate limiter utility in /lib/rateLimit.ts.
4. Apply route-specific rate limits to all API routes via middleware or route handlers.
5. Implement global 100 req/min per IP ceiling in Next.js middleware.ts.
6. Hash IP addresses before using as Redis keys.
7. Write Jest tests for each rate limit tier and the global ceiling.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-04-006] Global Rate Limiting and DDoS Protection".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-006-global-rate-limiting
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-007 — Dependency Audit and Vulnerability Scanning CI Step

```yaml
feature_id:         F-04-007
title:              "Dependency Audit and Vulnerability Scanning CI Step"
milestone_id:       M-04
priority:           medium
complexity:         S
depends_on:         [F-01-001]
parallel_safe:      true
```

**Description**

Add automated dependency vulnerability scanning to the GitHub Actions CI pipeline. For the Node.js project, add `npm audit --audit-level=high` as a required CI step that fails the pipeline on any high or critical CVE. For the Python FastAPI service, add `pip-audit` as a required CI step. Additionally, add a `trivy` container image scan step that scans the Docker images for both services before Railway deployment. Configure Dependabot for both `package.json` and `requirements.txt` to automatically open PRs for dependency updates weekly.

**Security constraints**

- Dependency hygiene: `doc1 § Dependency management — npm audit and pip-audit must pass with zero high/critical CVEs; pipeline fails on violation`
- Container security: `doc1 § Dependency management — trivy image scan must pass with zero critical CVEs before deployment`
- Automated updates: `doc1 § Dependency management — Dependabot configured for weekly dependency update PRs`

**Acceptance criteria**

- [ ] Given a PR is opened against main, when the GitHub Actions CI pipeline runs, then `npm audit --audit-level=high` runs as a required step and the pipeline fails if any high or critical CVE is found.
- [ ] Given a PR is opened against main, when the GitHub Actions CI pipeline runs, then `pip-audit` runs against the FastAPI service requirements and the pipeline fails if any high or critical CVE is found.
- [ ] Given a Docker image is built for either service, when the `trivy image` scan step runs, then the pipeline fails if any critical CVE is found in the image layers.
- [ ] Given Dependabot is configured, when a new version of a dependency with a security fix is released, then Dependabot opens a PR within 7 days with the updated version.
- [ ] Given the CI pipeline runs with zero vulnerabilities, when all audit steps complete, then the pipeline passes and the Railway deployment step proceeds.
- [ ] Security: Given a dependency with a known high CVE is intentionally added to `package.json` in a test branch, when the CI pipeline runs, then the `npm audit` step fails with a non-zero exit code and the deployment step is skipped.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-007-dependency-audit-ci
3. Add npm audit step to .github/workflows/ci.yml.
4. Add pip-audit step to .github/workflows/ci.yml for the events service.
5. Add trivy image scan step to .github/workflows/ci.yml.
6. Create .github/dependabot.yml for npm and pip ecosystems with weekly schedule.
7. Write CI workflow test by temporarily adding a known-vulnerable package and verifying failure.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-04-007] Dependency Audit and Vulnerability Scanning CI Step".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-007-dependency-audit-ci
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-008 — P-Coin Zero Monetary Value Technical Enforcement

```yaml
feature_id:         F-04-008
title:              "P-Coin Zero Monetary Value Technical Enforcement"
milestone_id:       M-04
priority:           critical
complexity:         S
depends_on:         [F-01-005]
parallel_safe:      true
```

**Description**

Implement technical guardrails that make it architecturally impossible for P-Coins to be converted to real monetary value. Specifically: (1) add a database-level CHECK constraint on `wallet_transactions` that rejects any `transaction_type` value containing the strings "withdrawal_real", "payout", "transfer_external", or "redeem"; (2) add a startup assertion in the Next.js application that verifies no payment processor environment variables (STRIPE_KEY, PAYPAL_KEY, etc.) are present; (3) add a CI lint rule that fails the pipeline if any source file imports a payment processing library (stripe, paypal-js, braintree, etc.); (4) display a persistent "P-Coin non hanno valore monetario reale" disclaimer on the wallet screen, the Risk Arena screen, and the Future Vault screen.

**Security constraints**

- No real money: `doc1 § Regulatory compliance — P-Coins must have zero monetary value enforced at database, application, and CI levels`
- Audit logging: `doc1 § Audit logging — log_events: [p_coin_value_disclaimer_shown]`

**Acceptance criteria**

- [ ] Given a direct SQL INSERT on `wallet_transactions` with `transaction_type = 'payout'`, when the database CHECK constraint evaluates the insert, then the insert is rejected with a constraint violation error.
- [ ] Given the Next.js application starts with a `STRIPE_KEY` environment variable set, when the startup assertion runs, then the application throws a fatal error and refuses to start.
- [ ] Given a developer adds `import Stripe from 'stripe'` to any source file and opens a PR, when the CI lint rule runs, then the pipeline fails with an error identifying the prohibited import.
- [ ] Given the wallet screen renders, when the page is inspected, then the Italian disclaimer "P-Coin non hanno valore monetario reale" is visible in the UI.
- [ ] Given the Risk Arena screen renders, when the page is inspected, then the Italian disclaimer "P-Coin non hanno valore monetario reale" is visible in the UI.
- [ ] Given the Future Vault screen renders, when the page is inspected, then the Italian disclaimer "P-Coin non hanno valore monetario reale" is visible in the UI.
- [ ] Security: Given the database CHECK constraint is in place, when `transaction_type = 'redeem'` is attempted via the application API, then the database rejects the insert and HTTP 500 is returned (no silent failure).

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-008-p-coin-zero-value-enforcement
3. Add CHECK constraint to wallet_transactions via Prisma raw migration.
4. Write startup assertion in Next.js instrumentation.ts checking for payment env vars.
5. Write ESLint custom rule prohibiting payment library imports.
6. Add disclaimer Chakra UI component to wallet, Risk Arena, and vault screens.
7. Write Jest tests for startup assertion and CHECK constraint rejection.
8. Fill in doc4_milestone_report.md for this feature_id.
9. Open a PR against main. Title: "[F-04-008] P-Coin Zero Monetary Value Technical Enforcement".
10. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-008-p-coin-zero-value-enforcement
github_issue_id:    ""
pr_id:              ""
```

---

### F-04-009 — End-to-End Privacy Audit and GDPR Compliance Report

```yaml
feature_id:         F-04-009
title:              "End-to-End Privacy Audit and GDPR Compliance Report"
milestone_id:       M-04
priority:           high
complexity:         M
depends_on:         [F-04-003, F-04-004, F-04-005, F-04-006, F-04-008, F-03-005, F-03-006]
parallel_safe:      false
```

**Description**

Perform a complete end-to-end privacy and GDPR compliance audit of the entire application before beta launch. The audit covers: (1) data flow mapping — verify every personal data field collected, its storage location, retention period, and legal basis; (2) data minimization check — verify no unnecessary PII is collected or logged; (3) consent flow completeness — verify GDPR onboarding, cookie consent, and withdrawal flows all function correctly; (4) data subject rights — verify data export (Article 15) and deletion (Article 17) endpoints work end-to-end; (5) security measures documentation — verify all technical measures from doc1 are implemented; (6) produce a written GDPR compliance checklist document committed to the repository as `docs/gdpr_compliance_checklist.md`.

**Security constraints**

- Privacy by design: `doc1 § Privacy by design — all data flows documented; no undocumented PII collection`
- Data minimization: `doc1 § Privacy by design — audit must confirm no PII stored in behavioral_events, logs, or Redis`
- Consent completeness: `doc1 § Privacy by design — all three consent flows (GDPR onboarding, cookie consent, deletion) verified end-to-end`
- Audit logging: `doc1 § Audit logging — log_events: [privacy_audit_completed]`

**Acceptance criteria**

- [ ] Given the audit is run, when all database tables are inspected, then no email address, full name, date of birth, or IP address appears in the `behavioral_events`, `wallet_transactions`, or `protection_score_snapshots` tables.
- [ ] Given the audit is run, when all application log outputs are inspected, then no PII (email, name, DOB, raw IP) appears in any log line from the Next.js application or FastAPI service.
- [ ] Given the audit is run, when all Redis keys are inspected, then no Redis key or value contains raw PII — only UUIDs, hashed IPs, and numeric counters are present.
- [ ] Given the data export endpoint (F-04-003) is tested end-to-end, when the export JSON is downloaded, then it contains all required GDPR Article 15 data categories and no undocumented data fields.
- [ ] Given the data deletion endpoint (F-04-004) is tested end-to-end, when deletion completes, then a database scan confirms zero PII rows remain for the deleted user_id.
- [ ] Given the `docs/gdpr_compliance_checklist.md` document is committed, when it is reviewed, then it contains a completed checklist covering all GDPR Articles 13, 15, 17, 25, and 32 requirements with pass/fail status for each item.
- [ ] Security: Given the complete application is deployed to the Railway EU West staging environment, when a network scan is performed, then no service port other than the Next.js app port (3000) and Metabase port (3001) is reachable from the public internet — PostgreSQL (5432) and Redis (6379) ports must not be publicly accessible.
- [ ] Security: Given the privacy audit is complete, when the `behavioral_events` table is queried for the `privacy_audit_completed` event, then a row exists with `occurred_at` matching the audit completion time.

**Worker instructions**

```
1. Read doc1_security_contract.md in full before writing any code.
2. Create branch: git checkout -b feature/F-04-009-privacy-audit-gdpr-compliance
3. Write a data flow mapping document covering all PII fields and their storage locations.
4. Run automated PII scan across all database tables using SQL queries.
5. Inspect application logs for PII leakage.
6. Inspect Redis keyspace for PII.
7. Run end-to-end tests for data export and deletion flows.
8. Write docs/gdpr_compliance_checklist.md with all GDPR article checks.
9. Emit privacy_audit_completed behavioral event.
10. Fill in doc4_milestone_report.md for this feature_id.
11. Open a PR against main. Title: "[F-04-009] End-to-End Privacy Audit and GDPR Compliance Report".
12. Do not merge — human gate required before validator runs.
```

**Done definition**

- [ ] All acceptance criteria pass in validator run
- [ ] Security checklist in doc1 fully checked
- [ ] Milestone report filed with milestone_status: passed
- [ ] PR approved by human reviewer

**GitHub**

```yaml
branch_name:        feature/F-04-009-privacy-audit-gdpr-compliance
github_issue_id:    ""
pr_id:              ""
```

---

## Feature status tracker

| feature_id | title | milestone | status | branch | validator_result |
|---|---|---|---|---|---|
| F-01-001 | Project Scaffold and Infrastructure Bootstrap | M-01 | in_progress | feature/F-01-001-scaffold-infrastructure | |
| F-01-002 | PostgreSQL Schema and TimescaleDB Hypertable | M-01 | pending | feature/F-01-002-database-schema | |
| F-01-003 | Google OAuth Authentication and Age Gate | M-01 | pending | feature/F-01-003-google-oauth-age-gate | |
| F-01-004 | GDPR Onboarding Screen and Consent Recording | M-01 | pending | feature/F-01-004-gdpr-onboarding-consent | |
| F-01-005 | P-Coin Wallet Creation and Weekly Allocation Cron | M-01 | pending | feature/F-01-005-wallet-weekly-allocation | |
| F-01-006 | FastAPI Behavioral Event Ingestion Service | M-01 | pending | feature/F-01-006-fastapi-event-ingestion | |
| F-01-007 | Risk Profile and Onboarding Profile Completion | M-01 | pending | feature/F-01-007-risk-profile-onboarding | |
| F-02-001 | Deposit Simulation Flow and Behavioral Alerts | M-02 | pending | feature/F-02-001-deposit-simulation-alerts | |
| F-02-002 | Risk Arena: Three Abstract Mini-Games | M-02 | pending | feature/F-02-002-risk-arena-mini-games | |
|
