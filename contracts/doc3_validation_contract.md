# Validation contract
<!-- Doc 3 — produced by the CTO orchestrator alongside doc2.
     The validator agent reads THIS file plus the worker's milestone report.
     The validator NEVER reads the implementation code — only test definitions.
     This prevents training-data bias: the validator judges against spec, not impl.
     Each test_suite maps 1-to-1 with a feature block in doc2. -->

---

## Meta

| Field | Value |
|---|---|
| project_id | protego-beta |
| contract_version | 1.0 |
| created_at | 2025-01-01T00:00:00Z |
| validator_provider | Google |
| validator_model_version | gemini-2.5-pro-001 |

---

## Validation principles

1. The validator reads test definitions and the milestone report — never the source code.
2. A test passes when the milestone report's `implemented` list and command outputs
   satisfy the test case's `expected` condition.
3. `blocking: true` tests must all pass before a PR can merge.
4. `human_gate_required: true` means a human must review even if all tests pass.
5. Security test failures are always escalated regardless of blocking flag.

---

## Test suites

---

### Suite F-01-001 — Project Scaffolding & Infrastructure

```yaml
suite_id:               F-01-001
feature_id:             F-01-001
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-01-001-T01
  type:         integration
  blocking:     true
  description:  >
    Next.js app starts on port 3000 with no TypeScript errors and home page returns HTTP 200.
  given:        "the repository is cloned, .env.local is populated, and npm run dev has been executed"
  when:         "user navigates to http://localhost:3000 in the browser"
  expected:     "the home page loads with HTTP 200, no TypeScript compilation error overlay is visible, and the page content is rendered"
  verified_via: executable_test

- test_id:      F-01-001-T02
  type:         integration
  blocking:     true
  description:  >
    FastAPI health endpoint returns ok status.
  given:        "the FastAPI service is started with uvicorn main:app"
  when:         "GET /health"
  expected:     "HTTP 200, body is {\"status\": \"ok\"}"
  verified_via: executable_test_api

- test_id:      F-01-001-T03
  type:         integration
  blocking:     true
  description:  >
    GitHub Actions CI pipeline passes all steps without leaking environment variable values.
  given:        "a GitHub Actions workflow is triggered by a PR"
  when:         "ESLint, TypeScript type-check, Prisma schema validation, and Jest steps run"
  expected:     "all steps exit with code 0 and no step's log output contains any environment variable value"
  verified_via: executable_test_api

- test_id:      F-01-001-T04
  type:         integration
  blocking:     true
  description:  >
    All Railway services are reachable on the shared internal network and health checks pass.
  given:        "the Railway EU West Frankfurt environment is configured with Next.js, FastAPI, PostgreSQL, Redis, and Metabase services"
  when:         "each service starts"
  expected:     "each service is reachable from the others on the shared internal network and all health checks return success"
  verified_via: executable_test_api

- test_id:      F-01-001-T05
  type:         integration
  blocking:     true
  description:  >
    All visible strings are served from the Italian i18n namespace with no untranslated key placeholders.
  given:        "the Next.js app is loaded in a browser"
  when:         "user navigates to http://localhost:3000 and the default locale is resolved"
  expected:     "all visible text on the page is in Italian and no untranslated key placeholders such as 'common.button.confirm' are visible anywhere on the page"
  verified_via: executable_test

- test_id:      F-01-001-T06
  type:         integration
  blocking:     true
  description:  >
    PWA manifest triggers Add to Home Screen prompt and icon matches Protego brand asset.
  given:        "the PWA manifest is served by the Next.js app"
  when:         "user visits the app on a mobile device (simulated via Playwright mobile viewport) and the browser evaluates the manifest"
  expected:     "the browser presents an Add to Home Screen prompt and the installed icon URL matches the Protego brand asset path"
  verified_via: executable_test

- test_id:      F-01-001-T07
  type:         security
  blocking:     true
  description:  >
    npm audit reports zero high or critical vulnerabilities in the Node.js dependency tree.
  given:        "the Node.js dependency tree is installed"
  when:         "npm audit --audit-level=high is run"
  expected:     "exit code 0 and zero high or critical vulnerabilities are reported"
  verified_via: executable_test_api

- test_id:      F-01-001-T08
  type:         security
  blocking:     true
  description:  >
    pip-audit reports zero high or critical vulnerabilities in the Python dependency tree.
  given:        "the Python dependency tree is installed"
  when:         "pip-audit is run against the FastAPI service requirements"
  expected:     "exit code 0 and zero high or critical vulnerabilities are reported"
  verified_via: executable_test_api

- test_id:      F-01-001-T09
  type:         security
  blocking:     true
  description:  >
    Railway service environment variable values are never echoed in application startup logs or HTTP response bodies.
  given:        "any Railway service environment variable is set"
  when:         "the application starts and any HTTP endpoint is called"
  expected:     "the environment variable value does not appear in any application startup log line or in any HTTP response body"
  verified_via: executable_test_api
```

---

### Suite F-01-002 — Database Schema & TimescaleDB Setup

```yaml
suite_id:               F-01-002
feature_id:             F-01-002
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-01-002-T01
  type:         integration
  blocking:     true
  description:  >
    Prisma migrations create all relational tables with correct columns, foreign keys, and indexes.
  given:        "a fresh PostgreSQL 16 + TimescaleDB database is available"
  when:         "prisma migrate deploy is executed"
  expected:     "the command exits with code 0 and all relational tables exist with correct columns, foreign keys, and indexes"
  verified_via: executable_test_api

- test_id:      F-01-002-T02
  type:         integration
  blocking:     true
  description:  >
    TimescaleDB hypertable is created successfully for behavioral_events.
  given:        "the TimescaleDB extension is enabled on the database"
  when:         "the raw SQL migration runs SELECT create_hypertable('behavioral_events', 'occurred_at') and then SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'behavioral_events' is queried"
  expected:     "create_hypertable returns success and the hypertables query returns exactly one row"
  verified_via: executable_test_api

- test_id:      F-01-002-T03
  type:         integration
  blocking:     true
  description:  >
    Application role can INSERT into behavioral_events and the row is persisted.
  given:        "the application database role protego_app is active"
  when:         "an INSERT is executed on behavioral_events"
  expected:     "the row is persisted and the INSERT returns the new row id"
  verified_via: executable_test_api

- test_id:      F-01-002-T04
  type:         integration
  blocking:     true
  description:  >
    Application role cannot UPDATE or DELETE rows in behavioral_events.
  given:        "the application database role protego_app is active and a row exists in behavioral_events"
  when:         "an UPDATE or DELETE is attempted on behavioral_events"
  expected:     "the database returns a permission-denied error and no row is modified"
  verified_via: executable_test_api

- test_id:      F-01-002-T05
  type:         integration
  blocking:     true
  description:  >
    behavioral_events table contains only pseudonymous columns with no PII fields.
  given:        "a behavioral_events row is inserted"
  when:         "the row schema is inspected"
  expected:     "the table definition contains only user_id (UUID), event_type, payload (JSONB), and occurred_at columns — no email, IP address, or name fields exist"
  verified_via: executable_test_api

- test_id:      F-01-002-T06
  type:         integration
  blocking:     true
  description:  >
    TimescaleDB compression policy is applied to behavioral_events.
  given:        "the TimescaleDB compression policy migration has run"
  when:         "SELECT * FROM timescaledb_information.compression_settings WHERE hypertable_name = 'behavioral_events' is queried"
  expected:     "a compression policy row is returned"
  verified_via: executable_test_api

- test_id:      F-01-002-T07
  type:         security
  blocking:     true
  description:  >
    Application role has only INSERT and SELECT privileges on behavioral_events — no UPDATE, DELETE, TRUNCATE, or REFERENCES.
  given:        "a direct psql connection is made using the application role credentials"
  when:         "\\dp behavioral_events is run"
  expected:     "the privileges column shows INSERT and SELECT only — no UPDATE, DELETE, TRUNCATE, or REFERENCES privileges are present"
  verified_via: executable_test_api

- test_id:      F-01-002-T08
  type:         security
  blocking:     true
  description:  >
    Application role does not have default SELECT on user_profiles, preventing unauthorized JOIN with behavioral_events.
  given:        "the user_profiles table contains a row with a real email address"
  when:         "a JOIN between behavioral_events and user_profiles is attempted using the application role without an explicit grant"
  expected:     "the query fails with a permission-denied error because the application role has not been explicitly granted SELECT on user_profiles"
  verified_via: executable_test_api
```

---

### Suite F-01-003 — Authentication & Session Management

```yaml
suite_id:               F-01-003
feature_id:             F-01-003
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-01-003-T01
  type:         integration
  blocking:     true
  description:  >
    Unauthenticated user visiting a protected route is redirected to /login.
  given:        "user is not logged in and has no session cookie"
  when:         "user navigates to http://localhost:3000/app/dashboard in the browser"
  expected:     "the browser is redirected to /login with HTTP 302 and no protected dashboard content is visible on the page"
  verified_via: executable_test

- test_id:      F-01-003-T02
  type:         integration
  blocking:     true
  description:  >
    Clicking Accedi con Google initiates OAuth and redirects to DOB collection screen without setting a session cookie.
  given:        "user is on the /login page"
  when:         "user clicks the 'Accedi con Google' button and Google OAuth completes successfully (mocked)"
  expected:     "the browser is redirected to the date-of-birth collection screen and no session cookie is present in the browser"
  verified_via: executable_test

- test_id:      F-01-003-T03
  type:         integration
  blocking:     true
  description:  >
    Submitting a DOB indicating age 17 shows Italian rejection message and creates no session or user row.
  given:        "user is on the date-of-birth collection screen after Google OAuth"
  when:         "user enters a date of birth that makes them 17 years old and submits the form"
  expected:     "no session cookie is set, the page displays the Italian message 'Devi avere almeno 18 anni per partecipare alla beta.' and no redirect to onboarding occurs"
  verified_via: executable_test

- test_id:      F-01-003-T04
  type:         integration
  blocking:     true
  description:  >
    Submitting a DOB indicating age 18 or older creates user row, session in Redis, and redirects to onboarding.
  given:        "user is on the date-of-birth collection screen after Google OAuth"
  when:         "user enters a date of birth that makes them exactly 18 years old and submits the form"
  expected:     "a session cookie is set, the browser is redirected to the onboarding flow, and the page renders the first onboarding step"
  verified_via: executable_test

- test_id:      F-01-003-T05
  type:         integration
  blocking:     true
  description:  >
    Session contains only pseudonymous user_id UUID and no raw Google access token or email is exposed to client-side JavaScript.
  given:        "user is authenticated and has a valid session cookie"
  when:         "user navigates to any /app/* page and the browser's JavaScript console is inspected for session data"
  expected:     "the session object accessible to client-side JavaScript contains only the pseudonymous user_id UUID — no raw Google access token or email address is present"
  verified_via: executable_test

- test_id:      F-01-003-T06
  type:         integration
  blocking:     true
  description:  >
    Session expired after 24 hours redirects user to /login and deletes Redis key.
  given:        "user has a session that has been active for more than 24 hours (simulated by expiring the Redis key)"
  when:         "user navigates to http://localhost:3000/app/dashboard"
  expected:     "the browser is redirected to /login and the Redis session key no longer exists"
  verified_via: executable_test_api

- test_id:      F-01-003-T07
  type:         integration
  blocking:     true
  description:  >
    auth_success behavioral event is recorded after successful authentication.
  given:        "user has just completed authentication successfully"
  when:         "the behavioral_events table is queried for that user_id"
  expected:     "an auth_success event row exists with the correct user_id UUID and a recent occurred_at timestamp"
  verified_via: executable_test_api

- test_id:      F-01-003-T08
  type:         security
  blocking:     true
  description:  >
    Forged JWT cookie with valid-looking user_id is rejected with HTTP 401 and auth_failure event is logged.
  given:        "no valid session exists"
  when:         "GET /app/dashboard with a forged JWT cookie containing a valid-looking user_id but invalid signature"
  expected:     "HTTP 401 is returned, no dashboard content is rendered, and an auth_failure event exists in behavioral_events"
  verified_via: executable_test_api

- test_id:      F-01-003-T09
  type:         security
  blocking:     true
  description:  >
    Login endpoint rate-limits after 20 rapid requests from the same IP within 60 seconds.
  given:        "no session exists"
  when:         "21 POST requests are sent to /api/auth/signin from the same IP within 60 seconds"
  expected:     "the 21st request receives HTTP 429 and no additional OAuth redirects are initiated"
  verified_via: executable_test_api

- test_id:      F-01-003-T10
  type:         security
  blocking:     true
  description:  >
    Session cookie has HttpOnly, Secure, and SameSite=Strict flags set.
  given:        "user has just completed authentication and a session cookie has been set"
  when:         "the browser's cookie attributes for the session cookie are inspected via Playwright"
  expected:     "the session cookie has HttpOnly=true, Secure=true, and SameSite=Strict attributes"
  verified_via: executable_test
```

---

### Suite F-01-004 — GDPR Consent Flow

```yaml
suite_id:               F-01-004
feature_id:             F-01-004
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-01-004-T01
  type:         integration
  blocking:     true
  description:  >
    Authenticated user without consent record is redirected to /onboarding/consent and cannot bypass it.
  given:        "user is authenticated but has no consent_records row in the database"
  when:         "user navigates to http://localhost:3000/app/dashboard"
  expected:     "the browser is redirected to /onboarding/consent and the consent screen is displayed — the dashboard is not accessible"
  verified_via: executable_test

- test_id:      F-01-004-T02
  type:         integration
  blocking:     true
  description:  >
    Continua button remains disabled and Italian validation messages appear when not all checkboxes are ticked.
  given:        "user is on the /onboarding/consent page"
  when:         "user does not tick all required checkboxes and attempts to click the 'Continua' button"
  expected:     "the 'Continua' button remains disabled and an Italian validation message is shown for each unticked checkbox item"
  verified_via: executable_test

- test_id:      F-01-004-T03
  type:         integration
  blocking:     true
  description:  >
    Ticking all checkboxes and clicking Continua inserts a consent_records row with correct data.
  given:        "user is on the /onboarding/consent page"
  when:         "user ticks all required checkboxes and clicks the 'Continua' button"
  expected:     "the browser navigates to the next onboarding step and a consent_records row exists in the database with user_id, consent_version '1.0', consented_at UTC timestamp, and JSONB payload {\"no_real_money\": true, \"data_collection\": true, \"p_coin_no_value\": true, \"terms_accepted\": true}"
  verified_via: executable_test

- test_id:      F-01-004-T04
  type:         integration
  blocking:     true
  description:  >
    Application role cannot UPDATE an existing consent_records row.
  given:        "a consent_records row exists in the database"
  when:         "an UPDATE is attempted on that row using the application database role"
  expected:     "the database returns a permission-denied error and no row is modified"
  verified_via: executable_test_api

- test_id:      F-01-004-T05
  type:         integration
  blocking:     true
  description:  >
    gdpr_consent_given behavioral event is emitted within 5 seconds of consent submission.
  given:        "user has just submitted the consent form"
  when:         "the behavioral_events hypertable is queried for that user_id"
  expected:     "a gdpr_consent_given event row exists with occurred_at within 5 seconds of the consent submission time"
  verified_via: executable_test_api

- test_id:      F-01-004-T06
  type:         integration
  blocking:     true
  description:  >
    Privacy notice page displays full Italian-language GDPR Article 13 content.
  given:        "user is on the /onboarding/consent page"
  when:         "user clicks the privacy notice link"
  expected:     "the page renders the full Italian-language privacy notice including data controller identity, data categories collected, retention periods, and user rights under GDPR Article 13"
  verified_via: executable_test

- test_id:      F-01-004-T07
  type:         integration
  blocking:     true
  description:  >
    User with valid consent record is not redirected to consent screen when accessing /app/* routes.
  given:        "user is authenticated and has a valid consent_records row"
  when:         "user navigates to http://localhost:3000/app/dashboard"
  expected:     "the dashboard page renders without any redirect to the consent screen"
  verified_via: executable_test

- test_id:      F-01-004-T08
  type:         security
  blocking:     true
  description:  >
    POST to consent submission endpoint without valid session returns HTTP 401 and inserts no consent_records row.
  given:        "no valid session cookie exists"
  when:         "POST /api/onboarding/consent with a valid consent payload body"
  expected:     "HTTP 401 is returned and no consent_records row is inserted in the database"
  verified_via: executable_test_api

- test_id:      F-01-004-T09
  type:         security
  blocking:     true
  description:  >
    POST to consent submission endpoint with SQL injection in consent_version field is rejected with HTTP 400.
  given:        "a valid session cookie exists"
  when:         "POST /api/onboarding/consent with body containing consent_version set to a SQL injection payload such as '; DROP TABLE consent_records; --'"
  expected:     "HTTP 400 is returned with a Zod validation error body and no database write occurs"
  verified_via: executable_test_api
```

---

### Suite F-01-005 — P-Coin Wallet Initialisation & Weekly Allocation

```yaml
suite_id:               F-01-005
feature_id:             F-01-005
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-01-005-T01
  type:         integration
  blocking:     true
  description:  >
    Completing GDPR onboarding creates a wallet with 1000 balance and an initial_allocation transaction atomically.
  given:        "user has just completed GDPR onboarding"
  when:         "the server action finalises onboarding"
  expected:     "a wallets row exists with balance = 1000 and a wallet_transactions row of type initial_allocation with amount = 1000 exists — both created in the same atomic transaction"
  verified_via: executable_test_api

- test_id:      F-01-005-T02
  type:         integration
  blocking:     true
  description:  >
    Rolling back the wallet creation transaction leaves no wallets or wallet_transactions rows.
  given:        "the wallet creation transaction is simulated to fail midway and roll back"
  when:         "the transaction is rolled back"
  expected:     "neither the wallets row nor the wallet_transactions row exists in the database"
  verified_via: executable_test_api

- test_id:      F-01-005-T03
  type:         integration
  blocking:     true
  description:  >
    Weekly allocation cron on Monday inserts a weekly_allocation transaction and increments wallet balance by 1000.
  given:        "an active Intern-tier user exists and the cron job runs on Monday at 00:00 UTC"
  when:         "the weekly allocation cron executes"
  expected:     "a wallet_transactions row of type weekly_allocation with amount = 1000 is inserted and the wallet balance is incremented by 1000"
  verified_via: executable_test_api

- test_id:      F-01-005-T04
  type:         integration
  blocking:     true
  description:  >
    Duplicate cron run in the same week does not insert a second allocation row due to unique constraint.
  given:        "the weekly allocation cron has already run once for a user in the current week"
  when:         "the cron runs a second time for the same user in the same week"
  expected:     "the unique constraint on (user_id, week_start_date, transaction_type) raises a conflict and no duplicate allocation row is inserted"
  verified_via: executable_test_api

- test_id:      F-01-005-T05
  type:         integration
  blocking:     true
  description:  >
    Deduction exceeding wallet balance is rolled back and returns insufficient_balance error.
  given:        "a wallet has a balance of 50 P-Coins"
  when:         "a deduction of 100 P-Coins is attempted"
  expected:     "the transaction is rolled back, the balance remains 50, and an insufficient_balance error is returned"
  verified_via: executable_test_api

- test_id:      F-01-005-T06
  type:         integration
  blocking:     true
  description:  >
    User A cannot access User B's wallet balance — returns HTTP 403.
  given:        "User A is authenticated and User B exists with a different user_id"
  when:         "User A's session calls the wallet balance API endpoint with User B's user_id as a parameter"
  expected:     "HTTP 403 is returned and User B's balance is not disclosed in the response body"
  verified_via: executable_test_api

- test_id:      F-01-005-T07
  type:         integration
  blocking:     true
  description:  >
    allocation_cron_run behavioral event is emitted after cron completes with correct payload.
  given:        "the weekly allocation cron has just completed"
  when:         "the behavioral_events table is queried"
  expected:     "an allocation_cron_run event exists with a payload containing {\"users_processed\": N, \"week_start_date\": \"YYYY-MM-DD\"}"
  verified_via: executable_test_api

- test_id:      F-01-005-T08
  type:         security
  blocking:     true
  description:  >
    POST to wallet mutation API without valid session returns HTTP 401 and no wallet row is modified.
  given:        "no valid session cookie exists"
  when:         "POST /api/wallet/mutate with a wallet mutation payload"
  expected:     "HTTP 401 is returned and no wallet row is modified"
  verified_via: executable_test_api

- test_id:      F-01-005-T09
  type:         security
  blocking:     true
  description:  >
    POST to wallet mutation endpoint with negative amount field is rejected with HTTP 400.
  given:        "a valid session cookie exists"
  when:         "POST /api/wallet/mutate with body containing amount: -500"
  expected:     "HTTP 400 is returned by Zod validation and no database write occurs"
  verified_via: executable_test_api
```

---

### Suite F-01-006 — FastAPI Behavioral Event Ingestion Endpoint

```yaml
suite_id:               F-01-006
feature_id:             F-01-006
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-01-006-T01
  type:         integration
  blocking:     true
  description:  >
    Valid POST to /events with correct API key and 3 valid event objects inserts all 3 rows and returns HTTP 201.
  given:        "the FastAPI service is running"
  when:         "POST /events with Authorization: Bearer {INTERNAL_API_KEY} and a JSON array of 3 valid event objects"
  expected:     "HTTP 201 is returned with body {\"inserted\": 3} and all 3 rows are present in behavioral_events"
  verified_via: executable_test_api

- test_id:      F-01-006-T02
  type:         integration
  blocking:     true
  description:  >
    POST to /events without Authorization header returns HTTP 401 and inserts no rows.
  given:        "the FastAPI service is running"
  when:         "POST /events with no Authorization header and a valid event payload"
  expected:     "HTTP 401 is returned and no rows are inserted into behavioral_events"
  verified_via: executable_test_api

- test_id:      F-01-006-T03
  type:         integration
  blocking:     true
  description:  >
    POST to /events with event_type not in allowlist returns HTTP 422 and inserts no rows.
  given:        "the FastAPI service is running"
  when:         "POST /events with Authorization: Bearer {INTERNAL_API_KEY} and event_type set to 'arbitrary_event'"
  expected:     "HTTP 422 is returned with a Pydantic validation error body and no rows are inserted"
  verified_via: executable_test_api

- test_id:      F-01-006-T04
  type:         integration
  blocking:     true
  description:  >
    POST to /events with invalid UUID4 user_id returns HTTP 422 and inserts no rows.
  given:        "the FastAPI service is running"
  when:         "POST /events with Authorization: Bearer {INTERNAL_API_KEY} and user_id set to 'not-a-uuid'"
  expected:     "HTTP 422 is returned and no rows are inserted"
  verified_via: executable_test_api

- test_id:      F-01-006-T05
  type:         integration
  blocking:     true
  description:  >
    POST to /events with payload field exceeding 4 KB returns HTTP 422 and inserts no rows.
  given:        "the FastAPI service is running"
  when:         "POST /events with Authorization: Bearer {INTERNAL_API_KEY} and a payload field containing more than 4096 bytes of data"
  expected:     "HTTP 422 is returned and no rows are inserted"
  verified_via: executable_test_api

- test_id:      F-01-006-T06
  type:         integration
  blocking:     true
  description:  >
    Batch of 50 valid events is inserted in a single database round-trip within 500 ms.
  given:        "the FastAPI service is running"
  when:         "POST /events with Authorization: Bearer {INTERNAL_API_KEY} and a JSON array of 50 valid event objects"
  expected:     "all 50 rows are inserted, HTTP 201 is returned with {\"inserted\": 50}, and the response time is under 500 ms"
  verified_via: executable_test_api

- test_id:      F-01-006-T07
  type:         integration
  blocking:     true
  description:  >
    GET /health returns HTTP 200 with ok status and db connected when service and database are healthy.
  given:        "the FastAPI service is running and the database connection pool is healthy"
  when:         "GET /health"
  expected:     "HTTP 200 is returned with body {\"status\": \"ok\", \"db\": \"connected\"}"
  verified_via: executable_test_api

- test_id:      F-01-006-T08
  type:         integration
  blocking:     true
  description:  >
    Rate limiter returns HTTP 429 on the 201st POST request from the same IP within 60 seconds.
  given:        "the FastAPI service is running"
  when:         "201 POST requests are sent to /events from the same IP within 60 seconds"
  expected:     "the 201st request receives HTTP 429"
  verified_via: executable_test_api

- test_id:      F-01-006-T09
  type:         security
  blocking:     true
  description:  >
    POST to /events with SQL injection payload as Bearer token returns HTTP 401 and executes no database query.
  given:        "the FastAPI service is running"
  when:         "POST /events with Authorization header containing a SQL injection payload as the Bearer token value"
  expected:     "HTTP 401 is returned and no database query is executed"
  verified_via: executable_test_api

- test_id:      F-01-006-T10
  type:         security
  blocking:     true
  description:  >
    INTERNAL_API_KEY value does not appear in FastAPI service log output after a successful request.
  given:        "the FastAPI service is running"
  when:         "a valid POST to /events is processed and the service logs are inspected"
  expected:     "the INTERNAL_API_KEY value does not appear anywhere in the log output"
  verified_via: executable_test_api
```

---

### Suite F-01-007 — Onboarding: Risk Profile, Spending Limit & Vault Quota

```yaml
suite_id:               F-01-007
feature_id:             F-01-007
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-01-007-T01
  type:         integration
  blocking:     true
  description:  >
    Selecting Prudente and clicking Continua persists PRUDENT risk profile to user_profiles.
  given:        "user is on the risk profile selection screen during onboarding"
  when:         "user selects 'Prudente' and clicks the 'Continua' button"
  expected:     "the browser navigates to the next onboarding step and the user_profiles.risk_profile field is updated to PRUDENT in the database"
  verified_via: executable_test

- test_id:      F-01-007-T02
  type:         integration
  blocking:     true
  description:  >
    Entering a spending limit below the minimum of 100 shows an Italian validation error and prevents submission.
  given:        "user is on the spending limit screen during onboarding"
  when:         "user enters the value 50 in the spending limit field and attempts to submit the form"
  expected:     "an Italian validation error message is displayed on the page and the form cannot be submitted"
  verified_via: executable_test

- test_id:      F-01-007-T03
  type:         integration
  blocking:     true
  description:  >
    Entering a spending limit greater than the weekly allocation shows an Italian validation error and prevents submission.
  given:        "user is on the spending limit screen during onboarding and their weekly allocation is 1000"
  when:         "user enters a value greater than 1000 in the spending limit field and attempts to submit the form"
  expected:     "an Italian validation error message is displayed on the page and the form cannot be submitted"
  verified_via: executable_test

- test_id:      F-01-007-T04
  type:         integration
  blocking:     true
  description:  >
    Submitting valid risk profile, spending limit, and vault quota creates all rows atomically.
  given:        "user is on the final onboarding configuration step with valid risk profile, spending limit, and vault quota values"
  when:         "user submits the form with all valid values"
  expected:     "a spending_limits row, a vault_allocations row, and an updated user_profiles row all exist in the database — created in a single atomic transaction"
  verified_via: executable_test_api

- test_id:      F-01-007-T05
  type:         integration
  blocking:     true
  description:  >
    Completing onboarding emits all required behavioral events for that user_id.
  given:        "user has just completed onboarding"
  when:         "the behavioral_events table is queried for that user_id"
  expected:     "risk_profile_selected, spending_limit_set, vault_quota_set, and onboarding_completed event rows all exist for that user_id"
  verified_via: executable_test_api

- test_id:      F-01-007-T06
  type:         integration
  blocking:     true
  description:  >
    Dashboard after onboarding displays risk profile badge, spending limit, and vault quota percentage.
  given:        "user has just completed onboarding and is redirected to /app/dashboard"
  when:         "the dashboard page renders"
  expected:     "the page displays the selected risk profile badge, the current spending limit value, and the vault quota percentage — all visible in the browser"
  verified_via: executable_test

- test_id:      F-01-007-T07
  type:         security
  blocking:     true
  description:  >
    POST to profile update endpoint with mismatched user_id in body returns HTTP 403 and modifies no profile row.
  given:        "a valid session exists for User A"
  when:         "POST /api/profile/update with a user_id in the body that belongs to User B"
  expected:     "HTTP 403 is returned and no user_profiles row is modified"
  verified_via: executable_test_api

- test_id:      F-01-007-T08
  type:         security
  blocking:     true
  description:  >
    POST to profile update endpoint with invalid risk_profile value is rejected with HTTP 400.
  given:        "a valid session exists"
  when:         "POST /api/profile/update with body containing risk_profile: 'ADMIN_OVERRIDE'"
  expected:     "HTTP 400 is returned by Zod validation and no database write occurs"
  verified_via: executable_test_api
```

---

### Suite F-02-001 — Risk Arena Deposit Simulation

```yaml
suite_id:               F-02-001
feature_id:             F-02-001
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-02-001-T01
  type:         integration
  blocking:     true
  description:  >
    Deposit Simulation screen displays deposit amount, monthly spending total, limit, and remaining allowance.
  given:        "user is authenticated and navigates to initiate a Risk Arena deposit of 200 P-Coins"
  when:         "the Deposit Simulation screen renders"
  expected:     "the page displays the deposit amount (200), the current monthly spending total, the monthly spending limit, and the remaining allowance — all visible in the browser"
  verified_via: executable_test

- test_id:      F-02-001-T02
  type:         integration
  blocking:     true
  description:  >
    Yellow alert banner is shown when monthly spending is within 20% of the spending limit.
  given:        "user's monthly spending total is within 20% of their spending limit"
  when:         "the Deposit Simulation screen renders"
  expected:     "a yellow alert banner is visible on the page with an Italian warning message about approaching the spending limit"
  verified_via: executable_test

- test_id:      F-02-001-T03
  type:         integration
  blocking:     true
  description:  >
    Red alert banner is shown when user has made 3 or more deposits in the last 10 minutes.
  given:        "user has made 3 deposits in the last 10 minutes"
  when:         "the Deposit Simulation screen renders"
  expected:     "a red alert banner is visible on the page with an Italian warning message about rapid consecutive deposits"
  verified_via: executable_test

- test_id:      F-02-001-T04
  type:         integration
  blocking:     true
  description:  >
    Clicking Conferma atomically deducts deposit, inserts wallet transaction, and emits deposit_confirmed event.
  given:        "user is on the Deposit Simulation screen with a valid deposit amount"
  when:         "user clicks the 'Conferma' button"
  expected:     "the wallet balance is reduced by the deposit amount, a wallet_transactions row of type risk_arena_deposit is inserted, and a deposit_confirmed behavioral event exists in the database"
  verified_via: executable_test_api

- test_id:      F-02-001-T05
  type:         integration
  blocking:     true
  description:  >
    Clicking Prendi una Pausa sets a 30-minute Redis pause key, deducts no P-Coins, and emits deposit_paused event.
  given:        "user is on the Deposit Simulation screen"
  when:         "user clicks the 'Prendi una Pausa' button"
  expected:     "a Redis key pause:{user_id} is set with a 30-minute TTL, no P-Coins are deducted from the wallet, and a deposit_paused behavioral event exists in the database"
  verified_via: executable_test_api

- test_id:      F-02-001-T06
  type:         integration
  blocking:     true
  description:  >
    Active pause key blocks new deposit and shows countdown timer.
  given:        "a pause:{user_id} Redis key exists for the authenticated user"
  when:         "user navigates to initiate another deposit in the Risk Arena"
  expected:     "the Deposit Simulation screen is blocked and a countdown timer showing the remaining pause time is visible on the page"
  verified_via: executable_test

- test_id:      F-02-001-T07
  type:         integration
  blocking:     true
  description:  >
    Clicking Riduci Importo re-renders the Deposit Simulation screen with the new amount and updated split.
  given:        "user is on the Deposit Simulation screen"
  when:         "user clicks 'Riduci Importo', enters a reduced amount, and submits the form"
  expected:     "the Deposit Simulation screen re-renders showing the new reduced amount and the updated risk/protection split values"
  verified_via: executable_test

- test_id:      F-02-001-T08
  type:         integration
  blocking:     true
  description:  >
    Deposit amount exceeding wallet balance is rejected with HTTP 400 and no deduction occurs.
  given:        "user's wallet balance is 100 P-Coins"
  when:         "POST /api/risk-arena/deposit with amount: 500"
  expected:     "HTTP 400 is returned by Zod validation and no wallet deduction occurs"
  verified_via: executable_test_api

- test_id:      F-02-001-T09
  type:         security
  blocking:     true
  description:  >
    POST to deposit confirm endpoint with another user's wallet_id returns HTTP 403 and no deduction occurs.
  given:        "a valid session exists for User A"
  when:         "POST /api/risk-arena/deposit/confirm with a wallet_id belonging to User B"
  expected:     "HTTP 403 is returned and no wallet deduction occurs"
  verified_via: executable_test_api

- test_id:      F-02-001-T10
  type:         security
  blocking:     true
  description:  >
    POST to deposit confirm endpoint is rate-limited after 10 requests within 60 seconds.
  given:        "a valid session exists"
  when:         "11 POST requests are sent to /api/risk-arena/deposit/confirm within 60 seconds by the same user"
  expected:     "the 11th request receives HTTP 429"
  verified_via: executable_test_api

- test_id:      F-02-001-T11
  type:         security
  blocking:     true
  description:  >
    POST to deposit confirm endpoint with negative amount is rejected with HTTP 400.
  given:        "a valid session exists"
  when:         "POST /api/risk-arena/deposit/confirm with body containing amount: -500"
  expected:     "HTTP 400 is returned by Zod validation and no database write occurs"
  verified_via: executable_test_api
```

---

### Suite F-02-002 — Risk Arena Games (Binary Choice & Random Wheel)

```yaml
suite_id:               F-02-002
feature_id:             F-02-002
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-02-002-T01
  type:         integration
  blocking:     true
  description:  >
    Binary Choice game screen displays two abstract symbols with no real-world gambling references.
  given:        "user has confirmed a deposit and enters the Risk Arena"
  when:         "user selects Binary Choice and the game screen renders"
  expected:     "the page displays two abstract symbols and no card suits, casino imagery, or real-world gambling references are visible anywhere on the page"
  verified_via: executable_test

- test_id:      F-02-002-T02
  type:         integration
  blocking:     true
  description:  >
    Binary Choice game outcome is generated server-side, committed to database before response, and returned in response body.
  given:        "user is on the Binary Choice game screen and has made a selection"
  when:         "the server processes the game"
  expected:     "the outcome is committed to the database before the HTTP response is sent and the client receives the outcome in the response body"
  verified_via: executable_test_api

- test_id:      F-02-002-T03
  type:         unit
  blocking:     true
  description:  >
    Binary Choice win rate is between 45% and 55% across 10,000 simulated outcomes.
  given:        "the Binary Choice outcome generation function uses crypto.randomInt(0, 2)"
  when:         "10,000 Binary Choice game outcomes are simulated in a unit test"
  expected:     "the win rate is between 45% and 55%"
  verified_via: executable_test_api

- test_id:      F-02-002-T04
  type:         integration
  blocking:     true
  description:  >
    Winning a Binary Choice game with 200 P-Coin deposit increases wallet balance by 200 and inserts risk_arena_win transaction.
  given:        "user has deposited 200 P-Coins and plays Binary Choice"
  when:         "the server generates a win outcome and applies the wallet transaction"
  expected:     "the wallet balance increases by 200 P-Coins (net +200 from the win) and a wallet_transactions row of type risk_arena_win with amount = 200 is inserted atomically"
  verified_via: executable_test_api

- test_id:      F-02-002-T05
  type:         integration
  blocking:     true
  description:  >
    Losing a Binary Choice game with 200 P-Coin deposit inserts risk_arena_loss transaction.
  given:        "user has deposited 200 P-Coins and plays Binary Choice"
  when:         "the server generates a loss outcome and applies the wallet transaction"
  expected:     "the wallet balance reflects the loss (deposit was already deducted) and a wallet_transactions row of type risk_arena_loss is inserted"
  verified_via: executable_test_api

- test_id:      F-02-002-T06
  type:         integration
  blocking:     true
  description:  >
    Random Wheel game applies segment multiplier to deposit amount and updates wallet atomically.
  given:        "user has deposited P-Coins and plays the Random Wheel game"
  when:         "the server generates the outcome with a specific segment multiplier"
  expected:     "the resulting P-Coin delta (deposit amount multiplied by the segment multiplier) is applied atomically to the wallet balance"
  verified_via: executable_test_api

- test_id:      F-02-002-T07
  type:         integration
  blocking:     true
  description:  >
    Client-supplied outcome field in game play request body is ignored and server-generated outcome is used.
  given:        "a valid session exists and user has an active deposit"
  when:         "POST /api/risk-arena/play with a body containing outcome: 'win'"
  expected:     "the server ignores the client-supplied outcome field and uses the server-generated outcome exclusively — the response reflects the server-determined result"
  verified_via: executable_test_api

- test_id:      F-02-002-T08
  type:         integration
  blocking:     true
  description:  >
    Risk Arena UI contains no references to real casinos, gambling games, sports teams, or real odds.
  given:        "user is on the Risk Arena page"
  when:         "all text, images, and component names on the page are reviewed"
  expected:     "no references to real casinos, roulette, blackjack, poker, sports teams, real odds, or prediction markets are found anywhere on the page"
  verified_via: executable_test

- test_id:      F-02-002-T09
  type:         security
  blocking:     true
  description:  >
    POST to game play endpoint without valid session returns HTTP 401 and no game outcome is generated.
  given:        "no valid session cookie exists"
  when:         "POST /api/risk-arena/play with a valid game payload"
  expected:     "HTTP 401 is returned and no game outcome is generated or wallet modified"
  verified_via: executable_test_api

- test_id:      F-02-002-T10
  type:         security
  blocking:     true
  description:  >
    POST to game play endpoint with game_type not in allowlist is rejected with HTTP 400.
  given:        "a valid session exists"
  when:         "POST /api/risk-arena/play with body containing game_type: 'SLOT_MACHINE'"
  expected:     "HTTP 400 is returned by Zod validation and no game is played"
  verified_via: executable_test_api

- test_id:      F-02-002-T11
  type:         security
  blocking:     true
  description:  >
    POST to game play endpoint is rate-limited after 14 requests within 60 seconds.
  given:        "a valid session exists"
  when:         "15 POST requests are sent to /api/risk-arena/play within 60 seconds by the same user"
  expected:     "the 15th request receives HTTP 429"
  verified_via: executable_test_api
```

---

### Suite F-02-003 — Future Vault

```yaml
suite_id:               F-02-003
feature_id:             F-02-003
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-02-003-T01
  type:         integration
  blocking:     true
  description:  >
    Weekly allocation cron transfers vault quota percentage to vault_balance and emits vault_funded event.
  given:        "a user has a vault quota of 20% and the weekly allocation cron runs"
  when:         "the cron executes the vault funding step"
  expected:     "20% of the weekly allocation is transferred to vault_balance and a vault_funded behavioral event is emitted"
  verified_via: executable_test_api

- test_id:      F-02-003-T02
  type:         integration
  blocking:     true
  description:  >
    Vault screen for Balanced risk profile shows three scenario projections with Italian labels and disclaimer.
  given:        "user has the Balanced risk profile and navigates to the vault screen at /app/vault"
  when:         "the scenario projections section renders"
  expected:     "three projections are visible: pessimistic at -5%, neutral at 0%, and optimistic at +5% — all with Italian labels — and a disclaimer in Italian stating these are virtual simulations with no real financial value is visible on the page"
  verified_via: executable_test

- test_id:      F-02-003-T03
  type:         integration
  blocking:     true
  description:  >
    Vault screen displays at least two tangible goal proxy strings calculated from vault balance.
  given:        "user has a non-zero vault balance and navigates to the vault screen"
  when:         "the goal proxy section renders"
  expected:     "at least two goal proxy strings are visible on the page (e.g., weeks of virtual rent covered, months of virtual emergency fund) calculated from the current vault balance"
  verified_via: executable_test

- test_id:      F-02-003-T04
  type:         integration
  blocking:     true
  description:  >
    Vault balance is excluded from available deposit amount in Risk Arena deposit flow with Italian explanation.
  given:        "user has a vault balance and initiates a Risk Arena deposit"
  when:         "the Deposit Simulation screen renders"
  expected:     "the vault balance is not included in the available deposit amount and an Italian message explaining that vault funds are protected is visible on the page"
  verified_via: executable_test

- test_id:      F-02-003-T05
  type:         integration
  blocking:     true
  description:  >
    Vault withdrawal of 500 P-Coins atomically moves funds to free wallet balance and inserts vault_withdrawal transaction.
  given:        "user has at least 500 P-Coins in vault_balance and initiates a vault withdrawal"
  when:         "user submits a withdrawal of 500 P-Coins on the vault screen"
  expected:     "500 P-Coins are moved from vault_balance to the free wallet balance and a wallet_transactions row of type vault_withdrawal is inserted atomically"
  verified_via: executable_test_api

- test_id:      F-02-003-T06
  type:         integration
  blocking:     true
  description:  >
    Vault withdrawal exceeding vault_balance is rejected with HTTP 400 and no balance change occurs.
  given:        "user has 100 P-Coins in vault_balance"
  when:         "POST /api/vault/withdraw with amount: 500"
  expected:     "HTTP 400 is returned by Zod validation and no balance change occurs"
  verified_via: executable_test_api

- test_id:      F-02-003-T07
  type:         security
  blocking:     true
  description:  >
    POST to vault withdrawal endpoint with another user's wallet_id returns HTTP 403 and no vault balance is modified.
  given:        "a valid session exists for User A"
  when:         "POST /api/vault/withdraw with a wallet_id belonging to User B"
  expected:     "HTTP 403 is returned and no vault balance is modified"
  verified_via: executable_test_api

- test_id:      F-02-003-T08
  type:         security
  blocking:     true
  description:  >
    Vault scenario projection API response contains no real financial instrument names, real interest rates, or real investment products.
  given:        "a valid session exists"
  when:         "GET /api/vault/projections"
  expected:     "the response body contains no real financial instrument names, real interest rates, or real investment product names"
  verified_via: executable_test_api
```

---

### Suite F-02-004 — Protection Score Calculation

```yaml
suite_id:               F-02-004
feature_id:             F-02-004
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-02-004-T01
  type:         unit
  blocking:     true
  description:  >
    Limit Respect component contributes full 30 points when user has respected spending limit for all months.
  given:        "a user has respected their spending limit for all months since registration"
  when:         "the Protection Score is calculated"
  expected:     "the Limit Respect component contributes exactly 30 points to the total score"
  verified_via: executable_test_api

- test_id:      F-02-004-T02
  type:         unit
  blocking:     true
  description:  >
    Vault Maintenance component contributes full 20 points when user has never withdrawn from vault.
  given:        "a user has never withdrawn from their vault"
  when:         "the Protection Score is calculated"
  expected:     "the Vault Maintenance component contributes exactly 20 points to the total score"
  verified_via: executable_test_api

- test_id:      F-02-004-T03
  type:         unit
  blocking:     true
  description:  >
    Pause/Alert Acceptance component contributes 12 points when user accepted 8 out of 10 behavioral alerts.
  given:        "a user has accepted 8 out of 10 behavioral alerts (chose Pause or Review Budget)"
  when:         "the Protection Score is calculated"
  expected:     "the Pause/Alert Acceptance component contributes 12 points (80% of 15) to the total score"
  verified_via: executable_test_api

- test_id:      F-02-004-T04
  type:         integration
  blocking:     true
  description:  >
    Protection Score calculation inserts a protection_score_snapshots row with all required fields.
  given:        "the Protection Score calculation runs for a user"
  when:         "the result is stored"
  expected:     "a protection_score_snapshots row is inserted with user_id, score (0-100 integer), component_breakdown (JSONB with all six component scores), and calculated_at timestamp"
  verified_via: executable_test_api

- test_id:      F-02-004-T05
  type:         integration
  blocking:     true
  description:  >
    Dashboard Protection Score section displays total score and all six component scores in Italian.
  given:        "user is authenticated and navigates to /app/dashboard"
  when:         "the Protection Score section renders"
  expected:     "the total score (0-100) and all six component scores with their weights are visible on the page in Italian"
  verified_via: executable_test

- test_id:      F-02-004-T06
  type:         integration
  blocking:     true
  description:  >
    Second Protection Score calculation on the same day upserts the existing snapshot rather than creating a duplicate.
  given:        "a protection_score_snapshots row already exists for the current day for a user"
  when:         "the Protection Score calculation runs again for the same user on the same day"
  expected:     "the existing snapshot row is updated (upserted) and no duplicate row is created for that day"
  verified_via: executable_test_api

- test_id:      F-02-004-T07
  type:         integration
  blocking:     true
  description:  >
    Hypothetical score override endpoint returns HTTP 404 and no score row is modified.
  given:        "a valid session exists"
  when:         "POST /api/protection-score/override with a score override payload"
  expected:     "HTTP 404 is returned and no protection_score_snapshots row is modified"
  verified_via: executable_test_api

- test_id:      F-02-004-T08
  type:         security
  blocking:     true
  description:  >
    GET to Protection Score API with another user's user_id returns HTTP 403 and no score data is disclosed.
  given:        "a valid session exists for User A"
  when:         "GET /api/protection-score?user_id={User_B_UUID}"
  expected:     "HTTP 403 is returned and no score data for User B is disclosed in the response body"
  verified_via: executable_test_api

- test_id:      F-02-004-T09
  type:         security
  blocking:     true
  description:  >
    Protection Score calculation uses only parameterized queries with no raw string interpolation in SQL.
  given:        "the Protection Score calculation function is invoked"
  when:         "it reads from behavioral_events and wallet_transactions"
  expected:     "all SQL queries use parameterized queries — no raw string interpolation is present in any SQL statement executed during the calculation"
  verified_via: executable_test_api
```

---

### Suite F-02-005 — Dashboard

```yaml
suite_id:               F-02-005
feature_id:             F-02-005
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-02-005-T01
  type:         integration
  blocking:     true
  description:  >
    Dashboard displays wallet balance, Protection Score, career tier, monthly spending progress, and beta countdown timer.
  given:        "user has completed onboarding and is redirected to /app/dashboard"
  when:         "the dashboard page renders"
  expected:     "the wallet balance, Protection Score, career tier, monthly spending progress bar, and beta countdown timer are all visible on the page"
  verified_via: executable_test

- test_id:      F-02-005-T02
  type:         integration
  blocking:     true
  description:  >
    Dashboard displays free balance and vault balance separately with Italian labels.
  given:        "user is on /app/dashboard"
  when:         "the wallet balance section renders"
  expected:     "both the free balance and the vault balance are displayed separately with Italian labels visible on the page"
  verified_via: executable_test

- test_id:      F-02-005-T03
  type:         integration
  blocking:     true
  description:  >
    Monthly spending progress bar changes colour to yellow at 80% and red at 100% of spending limit.
  given:        "user is on /app/dashboard and their monthly spending is at 80% of their spending limit"
  when:         "the monthly spending progress bar renders"
  expected:     "the progress bar is yellow in colour and shows the current spending as a percentage of the spending limit"
  verified_via: executable_test

- test_id:      F-02-005-T04
  type:         integration
  blocking:     true
  description:  >
    Beta countdown timer displays correct number of days remaining calculated from first user registration date.
  given:        "user is on /app/dashboard and the first user registration date is stored in the database"
  when:         "the beta countdown timer renders"
  expected:     "the timer displays the correct number of days remaining calculated as 365 minus the number of days elapsed since the first user registration date"
  verified_via: executable_test

- test_id:      F-02-005-T05
  type:         integration
  blocking:     true
  description:  >
    Dashboard server component ignores user_id query parameter and fetches data for session user only.
  given:        "user is authenticated as User A"
  when:         "user navigates to /app/dashboard?user_id={User_B_UUID}"
  expected:     "the dashboard renders data exclusively for User A — User B's data is not displayed anywhere on the page"
  verified_via: executable_test

- test_id:      F-02-005-T06
  type:         integration
  blocking:     true
  description:  >
    Dashboard HTML source contains no raw behavioral event rows, email addresses, or internal database IDs other than the pseudonymous UUID.
  given:        "user is authenticated and on /app/dashboard"
  when:         "the page HTML source is inspected"
  expected:     "no raw behavioral event rows, email addresses, or internal database IDs other than the pseudonymous UUID are present in the rendered HTML"
  verified_via: executable_test

- test_id:      F-02-005-T07
  type:         security
  blocking:     true
  description:  >
    Unauthenticated GET to /app/dashboard returns HTTP 302 redirect to /login with no dashboard content rendered.
  given:        "no session cookie exists"
  when:         "GET /app/dashboard"
  expected:     "HTTP 302 redirect to /login is returned and no dashboard content is present in the response body"
  verified_via: executable_test_api
```

---

### Suite F-02-006 — Settings: Spending Limit & Vault Quota Updates

```yaml
suite_id:               F-02-006
feature_id:             F-02-006
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-02-006-T01
  type:         integration
  blocking:     true
  description:  >
    Saving a new valid spending limit inserts a spending_limits row with effective_from set to the first day of next month.
  given:        "user is on /app/settings/spending-limit"
  when:         "user enters a new valid spending limit value and clicks the save button"
  expected:     "the page shows a success confirmation and a new spending_limits row is inserted in the database with effective_from set to the first day of the next calendar month"
  verified_via: executable_test

- test_id:      F-02-006-T02
  type:         integration
  blocking:     true
  description:  >
    Saving a new vault quota percentage inserts a vault_allocations row with effective_from set to next Monday.
  given:        "user is on /app/settings/vault-quota"
  when:         "user selects a new vault quota percentage and clicks the save button"
  expected:     "the page shows a success confirmation and a new vault_allocations row is inserted in the database with effective_from set to the next Monday"
  verified_via: executable_test

- test_id:      F-02-006-T03
  type:         integration
  blocking:     true
  description:  >
    Submitting a spending limit below the minimum of 100 returns HTTP 400 and inserts no new row.
  given:        "a valid session exists"
  when:         "POST /api/settings/spending-limit with body containing value: 50"
  expected:     "HTTP 400 is returned by Zod validation and no new spending_limits row is inserted"
  verified_via: executable_test_api

- test_id:      F-02-006-T04
  type:         integration
  blocking:     true
  description:  >
    Saving a configuration change emits the corresponding behavioral event with old and new values in payload.
  given:        "user has just saved a new spending limit"
  when:         "the behavioral_events table is queried for that user_id"
  expected:     "a spending_limit_updated event exists with the old and new values in the payload JSONB"
  verified_via: executable_test_api

- test_id:      F-02-006-T05
  type:         integration
  blocking:     true
  description:  >
    Settings screen displays the most recently effective spending limit and vault quota values, not future-dated pending changes.
  given:        "user has a pending future-dated spending limit change and navigates to /app/settings/spending-limit"
  when:         "the settings screen renders"
  expected:     "the currently displayed spending limit reflects the most recently effective value, not the future-dated pending change"
  verified_via: executable_test

- test_id:      F-02-006-T06
  type:         security
  blocking:     true
  description:  >
    POST to spending limit update endpoint with another user's user_id in body returns HTTP 403 and inserts no row.
  given:        "a valid session exists for User A"
  when:         "POST /api/settings/spending-limit with a user_id in the body belonging to User B"
  expected:     "HTTP 403 is returned and no spending_limits row is inserted"
  verified_via: executable_test_api
```

---

### Suite F-03-001 — Career Progression & Life Layer Expenses

```yaml
suite_id:               F-03-001
feature_id:             F-03-001
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-03-001-T01
  type:         integration
  blocking:     true
  description:  >
    Protection Score reaching 30 advances career tier from INTERN to JUNIOR and updates weekly allocation to 1500.
  given:        "a user's Protection Score snapshot is saved with a score of 30"
  when:         "career tier eligibility is evaluated"
  expected:     "the user's career_tier is updated from INTERN to JUNIOR and the weekly allocation is updated to 1500 P-Coins"
  verified_via: executable_test_api

- test_id:      F-03-001-T02
  type:         integration
  blocking:     true
  description:  >
    Career tier does not advance based on Risk Arena wins alone — only Protection Score thresholds trigger advancement.
  given:        "a user wins a large amount in the Risk Arena but their Protection Score is below the JUNIOR threshold"
  when:         "career tier eligibility is evaluated"
  expected:     "the career tier remains unchanged and no tier advancement occurs"
  verified_via: executable_test_api

- test_id:      F-03-001-T03
  type:         integration
  blocking:     true
  description:  >
    Weekly expense deduction cron atomically deducts virtual expenses and emits life_layer_expense_deducted events.
  given:        "a user has sufficient free balance and the weekly expense deduction cron runs"
  when:         "the cron executes the expense deduction step"
  expected:     "virtual rent, bills, and groceries are deducted atomically from the wallet and a life_layer_expense_deducted behavioral event is emitted for each expense category"
  verified_via: executable_test_api

- test_id:      F-03-001-T04
  type:         integration
  blocking:     true
  description:  >
    Random emergency deduction emits virtual_emergency_triggered event with emergency amount in payload.
  given:        "the weekly expense deduction cron runs and the random emergency probability triggers (simulated by seeding the RNG)"
  when:         "the emergency deduction is applied"
  expected:     "a virtual_emergency_triggered behavioral event is emitted with the emergency amount in the payload JSONB"
  verified_via: executable_test_api

- test_id:      F-03-001-T05
  type:         integration
  blocking:     true
  description:  >
    Insufficient free balance causes expense deduction to be skipped and emits life_layer_expense_missed event.
  given:        "a user's free balance is insufficient to cover mandatory expenses and the expense deduction cron runs"
  when:         "the expense deduction step executes"
  expected:     "the deduction is skipped, a life_layer_expense_missed behavioral event is emitted, and the Protection Score Daily Expense Management component will be penalised in the next calculation"
  verified_via: executable_test_api

- test_id:      F-03-001-T06
  type:         integration
  blocking:     true
  description:  >
    Life Layer screen displays current tier, weekly income, and Protection Score threshold for next tier in Italian.
  given:        "user is authenticated and navigates to the Life Layer screen"
  when:         "the career progression section renders"
  expected:     "the current tier, current weekly income, and the Protection Score threshold required for the next tier are all visible on the page in Italian"
  verified_via: executable_test

- test_id:      F-03-001-T07
  type:         security
  blocking:     true
  description:  >
    POST to hypothetical career tier override endpoint returns HTTP 404.
  given:        "a valid session exists"
  when:         "POST /api/career/tier-override with a tier override payload"
  expected:     "HTTP 404 is returned and no career tier is modified"
  verified_via: executable_test_api

- test_id:      F-03-001-T08
  type:         security
  blocking:     true
  description:  >
    Expense deduction cron sources deduction amounts exclusively from career_tiers reference table and accepts no client-supplied amounts.
  given:        "the expense deduction cron runs"
  when:         "the deduction amounts are calculated"
  expected:     "all deduction amounts are sourced from the career_tiers reference table — no client-supplied amounts are accepted or used in the calculation"
  verified_via: executable_test_api
```

---

### Suite F-03-002 — Missions & Rewards

```yaml
suite_id:               F-03-002
feature_id:             F-03-002
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-03-002-T01
  type:         integration
  blocking:     true
  description:  >
    Mission evaluation cron marks mission as COMPLETED and credits P-Coin bonus when conditions are met.
  given:        "a mission 'Rispetta il limite per 4 settimane' is active for a user and the user has respected their limit for 4 consecutive weeks"
  when:         "the daily mission evaluation cron runs"
  expected:     "the user_missions row is updated to status: COMPLETED and a P-Coin bonus is atomically credited to the wallet"
  verified_via: executable_test_api

- test_id:      F-03-002-T02
  type:         integration
  blocking:     true
  description:  >
    mission_completed and mission_reward_issued behavioral events exist after mission completion.
  given:        "a mission has just been completed for a user"
  when:         "the behavioral_events table is queried for that user_id"
  expected:     "both mission_completed and mission_reward_issued events exist with the mission ID and reward amount in the payload JSONB"
  verified_via: executable_test_api

- test_id:      F-03-002-T03
  type:         integration
  blocking:     true
  description:  >
    Active mission page displays Italian progress indicator showing current progress.
  given:        "user is authenticated and navigates to the missions page"
  when:         "an active mission with 3 out of 4 weeks completed is displayed"
  expected:     "a progress indicator is visible on the page showing '3 di 4 settimane completate' in Italian"
  verified_via: executable_test

- test_id:      F-03-002-T04
  type:         integration
  blocking:     true
  description:  >
    POST to hypothetical mission completion endpoint returns HTTP 404 — mission completion is cron-only.
  given:        "a valid session exists"
  when:         "POST /api/missions/complete with mission_id and completed: true in the body"
  expected:     "HTTP 404 is returned and no mission completion is processed"
  verified_via: executable_test_api

- test_id:      F-03-002-T05
  type:         integration
  blocking:     true
  description:  >
    Wallet balance increases by mission reward amount and mission_reward wallet transaction exists after reward issuance.
  given:        "a mission reward has just been issued for a user"
  when:         "the wallet balance and wallet_transactions table are inspected"
  expected:     "the wallet balance has increased by the mission reward amount and a wallet_transactions row of type mission_reward is present"
  verified_via: executable_test_api

- test_id:      F-03-002-T06
  type:         security
  blocking:     true
  description:  >
    GET to user missions API with another user's user_id returns HTTP 403 and no mission data is disclosed.
  given:        "a valid session exists for User A"
  when:         "GET /api/missions?user_id={User_B_UUID}"
  expected:     "HTTP 403 is returned and no mission data for User B is disclosed in the response body"
  verified_via: executable_test_api
```

---

### Suite F-03-003 — Beta Countdown & Expiry

```yaml
suite_id:               F-03-003
feature_id:             F-03-003
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-03-003-T01
  type:         integration
  blocking:     true
  description:  >
    Dashboard countdown displays correct number of days remaining based on first user registration date.
  given:        "the first user registration date is stored in the database and user is on /app/dashboard"
  when:         "the beta countdown timer renders"
  expected:     "the countdown displays the correct number of days remaining calculated as 365 minus the number of days elapsed since the first user registration date"
  verified_via: executable_test

- test_id:      F-03-003-T02
  type:         integration
  blocking:     true
  description:  >
    Yellow warning banner is displayed when fewer than 30 days remain in the beta.
  given:        "335 days have elapsed since the first user registration (simulated)"
  when:         "user navigates to /app/dashboard"
  expected:     "a yellow warning banner is visible on the page with an Italian message stating 'Mancano meno di 30 giorni alla fine della beta.'"
  verified_via: executable_test

- test_id:      F-03-003-T03
  type:         integration
  blocking:     true
  description:  >
    Full-screen modal is displayed and all game interaction buttons are disabled when beta has expired.
  given:        "365 or more days have elapsed since the first user registration (simulated)"
  when:         "authenticated user navigates to any /app/* route"
  expected:     "a full-screen modal is displayed in Italian stating the beta has ended and all Risk Arena and deposit buttons are disabled and not clickable"
  verified_via: executable_test

- test_id:      F-03-003-T04
  type:         integration
  blocking:     true
  description:  >
    No game interaction buttons are clickable when the beta expiry modal is displayed.
  given:        "the beta expiry modal is displayed (365+ days elapsed)"
  when:         "user inspects the page and attempts to interact with game buttons"
  expected:     "no game interaction buttons are clickable and no deposit simulation can be initiated"
  verified_via: executable_test

- test_id:      F-03-003-T05
  type:         security
  blocking:     true
  description:  >
    POST to hypothetical beta reset endpoint returns HTTP 404 and first registration date is not modified.
  given:        "a valid session exists"
  when:         "POST /api/beta/reset with a reset payload"
  expected:     "HTTP 404 is returned and the first registration date in the database is not modified"
  verified_via: executable_test_api
```

---

### Suite F-03-004 — Post-Session Survey Prompt

```yaml
suite_id:               F-03-004
feature_id:             F-03-004
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-03-004-T01
  type:         integration
  blocking:     true
  description:  >
    Survey modal is displayed after Risk Arena session if user has not seen it in the last 7 days.
  given:        "user has completed at least one Risk Arena game and has not seen the survey modal in the last 7 days"
  when:         "user exits the Risk Arena"
  expected:     "the survey modal is displayed on the page"
  verified_via: executable_test

- test_id:      F-03-004-T02
  type:         integration
  blocking:     true
  description:  >
    Survey modal is not displayed if user saw it 3 days ago.
  given:        "user saw the survey modal 3 days ago and completes another Risk Arena session"
  when:         "user exits the Risk Arena"
  expected:     "the survey modal is not displayed on the page"
  verified_via: executable_test

- test_id:      F-03-004-T03
  type:         integration
  blocking:     true
  description:  >
    Clicking the survey link opens the Google Form URL in a new tab and emits survey_link_clicked event.
  given:        "the survey modal is displayed"
  when:         "user clicks the survey link in the modal"
  expected:     "a new browser tab opens with the hardcoded Google Form URL and a survey_link_clicked behavioral event exists in the database"
  verified_via: executable_test

- test_id:      F-03-004-T04
  type:         integration
  blocking:     true
  description:  >
    Dismissing the survey modal emits survey_prompt_dismissed event and updates last_survey_prompt_at field.
  given:        "the survey modal is displayed"
  when:         "user dismisses the modal"
  expected:     "a survey_prompt_dismissed behavioral event exists in the database and the user_profiles.last_survey_prompt_at field is updated to the current timestamp"
  verified_via: executable_test_api

- test_id:      F-03-004-T05
  type:         integration
  blocking:     true
  description:  >
    Survey modal link href matches exactly the NEXT_PUBLIC_SURVEY_URL environment variable value.
  given:        "the survey modal is displayed"
  when:         "the link href attribute is inspected via Playwright"
  expected:     "the href matches exactly the NEXT_PUBLIC_SURVEY_URL environment variable value and no user-supplied URL is used"
  verified_via: executable_test

- test_id:      F-03-004-T06
  type:         security
  blocking:     true
  description:  >
    POST to survey state update endpoint with another user's user_id returns HTTP 403 and no user_profiles row is modified.
  given:        "a valid session exists for User A"
  when:         "POST /api/survey/state with a user_id belonging to User B"
  expected:     "HTTP 403 is returned and no user_profiles row is modified"
  verified_via: executable_test_api
```

---

### Suite F-03-005 — Cookie Consent Banner

```yaml
suite_id:               F-03-005
feature_id:             F-03-005
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-03-005-T01
  type:         integration
  blocking:     true
  description:  >
    Cookie consent banner is displayed before any analytics scripts are initialised on first visit.
  given:        "a first-time visitor loads any page"
  when:         "the page renders"
  expected:     "the cookie consent banner is visible on the page before any analytics scripts or behavioral event tracking is initialised"
  verified_via: executable_test

- test_id:      F-03-005-T02
  type:         integration
  blocking:     true
  description:  >
    Rifiuta tutto button is as visually prominent as Accetta tutto button and no checkbox is pre-ticked.
  given:        "the cookie consent banner is displayed"
  when:         "user inspects the banner UI"
  expected:     "the 'Rifiuta tutto' button is as visually prominent as the 'Accetta tutto' button and no checkbox is pre-ticked"
  verified_via: executable_test

- test_id:      F-03-005-T03
  type:         integration
  blocking:     true
  description:  >
    Clicking Rifiuta tutto sets only strictly necessary cookies and loads no analytics scripts.
  given:        "the cookie consent banner is displayed"
  when:         "user clicks the 'Rifiuta tutto' button"
  expected:     "only strictly necessary cookies are set in the browser, no analytics scripts are loaded, and no cookie_consent_rejected behavioral event is emitted"
  verified_via: executable_test

- test_id:      F-03-005-T04
  type:         integration
  blocking:     true
  description:  >
    Clicking Accetta tutto sets the cookie_consent cookie with correct security flags and initialises behavioral event tracking.
  given:        "the cookie consent banner is displayed"
  when:         "user clicks the 'Accetta tutto' button"
  expected:     "the cookie_consent cookie is set with HttpOnly=true, Secure=true, and SameSite=Strict attributes, and behavioral event tracking is initialised"
  verified_via: executable_test

- test_id:      F-03-005-T05
  type:         integration
  blocking:     true
  description:  >
    Accepting analytics cookies inserts a consent_records row with cookie_analytics consent type.
  given:        "an authenticated user accepts analytics cookies"
  when:         "the consent is recorded"
  expected:     "a consent_records row is inserted in the database with consent_type: 'cookie_analytics' and a consented_at timestamp"
  verified_via: executable_test_api

- test_id:      F-03-005-T06
  type:         integration
  blocking:     true
  description:  >
    Cookie consent banner is not shown again on revisit and previously chosen consent state is respected.
  given:        "user has previously accepted the cookie consent banner"
  when:         "user revisits the site"
  expected:     "the cookie consent banner is not displayed and the previously chosen consent state is respected"
  verified_via: executable_test

- test_id:      F-03-005-T07
  type:         security
  blocking:     true
  description:  >
    No analytics tracking pixel, third-party script, or behavioral event call is present in the DOM before user interacts with the banner.
  given:        "a first-time visitor loads any page and has not yet interacted with the cookie consent banner"
  when:         "the page HTML DOM is inspected via Playwright"
  expected:     "no analytics tracking pixel, third-party script tag, or behavioral event call is present in the DOM"
  verified_via: executable_test
```

---

### Suite F-03-006 — Internationalisation & Italian Locale

```yaml
suite_id:               F-03-006
feature_id:             F-03-006
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-03-006-T01
  type:         integration
  blocking:     true
  description:  >
    No untranslated key placeholders are visible when visiting all implemented screens in sequence.
  given:        "the Italian locale is active"
  when:         "user navigates through every implemented screen in sequence"
  expected:     "no untranslated key placeholder (e.g., 'common.button.confirm') is visible anywhere in the UI on any screen"
  verified_via: executable_test

- test_id:      F-03-006-T02
  type:         integration
  blocking:     true
  description:  >
    Zod validation error messages are displayed in Italian sourced from the it i18n namespace.
  given:        "user is on any form page"
  when:         "user triggers a Zod validation error by submitting an invalid form"
  expected:     "the error message is displayed in Italian and is sourced from the 'it' i18n namespace"
  verified_via: executable_test

- test_id:      F-03-006-T03
  type:         integration
  blocking:     true
  description:  >
    Privacy notice page contains all GDPR Article 13 required fields in Italian.
  given:        "user navigates to the privacy notice page"
  when:         "the page content is reviewed"
  expected:     "all GDPR Article 13 required fields are present in Italian: data controller identity, purposes, legal basis, retention periods, user rights, and DPA contact information"
  verified_via: executable_test

- test_id:      F-03-006-T04
  type:         integration
  blocking:     true
  description:  >
    Translation JSON files contain no secrets, API keys, or environment variable values.
  given:        "the translation JSON files are inspected"
  when:         "the files are scanned for secrets"
  expected:     "no API keys, internal service URLs, database connection strings, or environment variable values are present in any translation file"
  verified_via: executable_test_api

- test_id:      F-03-006-T05
  type:         integration
  blocking:     true
  description:  >
    No translated string is rendered using dangerouslySetInnerHTML in any React component.
  given:        "any translated string is rendered in a React component"
  when:         "the component source is inspected"
  expected:     "dangerouslySetInnerHTML is not used for any translated content in any React component"
  verified_via: executable_test_api

- test_id:      F-03-006-T06
  type:         security
  blocking:     true
  description:  >
    i18n translation files served as static assets contain no sensitive configuration data or internal system information.
  given:        "the i18n translation files are served as static assets"
  when:         "the translation files are fetched directly via HTTP GET requests"
  expected:     "the response bodies contain no sensitive configuration data, API keys, internal service URLs, or internal system information"
  verified_via: executable_test_api
```

---

### Suite F-04-001 — Metabase Analytics Dashboard

```yaml
suite_id:               F-04-001
feature_id:             F-04-001
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-04-001-T01
  type:         integration
  blocking:     true
  description:  >
    Metabase database connection to PostgreSQL is active and connection test returns success.
  given:        "the Metabase instance is running on Railway EU West"
  when:         "admin navigates to the database connection settings in Metabase"
  expected:     "the connection to the PostgreSQL instance is shown as active and the connection test returns success"
  verified_via: executable_test

- test_id:      F-04-001-T02
  type:         integration
  blocking:     true
  description:  >
    Metabase acquisition dashboard displays registration count, age-gate rejection count, and onboarding completion rate as daily time-series charts.
  given:        "admin is authenticated in Metabase and opens the acquisition dashboard"
  when:         "the charts render"
  expected:     "registration count, age-gate rejection count, and onboarding completion rate are all displayed as time-series charts with daily granularity"
  verified_via: executable_test

- test_id:      F-04-001-T03
  type:         integration
  blocking:     true
  description:  >
    Metabase behavioral dashboard deposit confirmation rate chart shows ratio of deposit_confirmed to deposit_initiated events over time.
  given:        "admin is authenticated in Metabase and opens the behavioral dashboard"
  when:         "the deposit confirmation rate chart renders"
  expected:     "the chart shows the ratio of deposit_confirmed events to deposit_initiated events over time"
  verified_via: executable_test

- test_id:      F-04-001-T04
  type:         integration
  blocking:     true
  description:  >
    No Metabase question selects email, date_of_birth, or full_name columns from any table.
  given:        "all Metabase questions are inspected"
  when:         "the underlying SQL query of each question is reviewed"
  expected:     "no query selects the email, date_of_birth, or full_name columns from any table"
  verified_via: executable_test_api

- test_id:      F-04-001-T05
  type:         integration
  blocking:     true
  description:  >
    Metabase instance URL shows login form and no dashboard data when accessed without authentication.
  given:        "no Metabase session exists"
  when:         "user navigates to the Metabase instance URL"
  expected:     "a login form is presented and no dashboard data is visible on the page"
  verified_via: executable_test

- test_id:      F-04-001-T06
  type:         integration
  blocking:     true
  description:  >
    Metabase admin password meets complexity requirements.
  given:        "the Metabase admin password is set in Railway environment variables"
  when:         "the password value is evaluated"
  expected:     "the password is at least 16 characters and contains uppercase letters, lowercase letters, digits, and special characters"
  verified_via: executable_test_api

- test_id:      F-04-001-T07
  type:         security
  blocking:     true
  description:  >
    Metabase database role returns permission-denied when querying user_profiles table directly for email addresses.
  given:        "a Metabase question attempts to query the user_profiles table directly for email addresses"
  when:         "the query is executed using the Metabase database role"
  expected:     "the query returns a permission-denied error because the Metabase role has SELECT only on aggregate views"
  verified_via: executable_test_api

- test_id:      F-04-001-T08
  type:         security
  blocking:     true
  description:  >
    Only the Metabase port is reachable from outside the Railway private network — PostgreSQL and Redis ports are not publicly exposed.
  given:        "the Metabase instance is deployed on Railway"
  when:         "a port scan is performed from outside the Railway private network"
  expected:     "only the configured Metabase port is reachable and PostgreSQL port 5432 and Redis port 6379 are not directly accessible"
  verified_via: executable_test_api
```

---

### Suite F-04-002 — Admin CSV Export Endpoint

```yaml
suite_id:               F-04-002
feature_id:             F-04-002
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-04-002-T01
  type:         integration
  blocking:     true
  description:  >
    Valid GET to admin export endpoint with correct API key and date range streams a CSV with correct headers and matching rows.
  given:        "the Next.js application is running"
  when:         "GET /api/admin/export/events with Authorization: Bearer {ADMIN_API_KEY} and query params from=2026-01-01&to=2026-12-31"
  expected:     "a CSV file is streamed with headers user_id,event_type,payload,occurred_at and rows matching the specified date range"
  verified_via: executable_test_api

- test_id:      F-04-002-T02
  type:         integration
  blocking:     true
  description:  >
    GET to admin export endpoint without Authorization header returns HTTP 401 and no CSV data is streamed.
  given:        "the Next.js application is running"
  when:         "GET /api/admin/export/events with no Authorization header"
  expected:     "HTTP 401 is returned and no CSV data is streamed"
  verified_via: executable_test_api

- test_id:      F-04-002-T03
  type:         integration
  blocking:     true
  description:  >
    GET to admin export endpoint with SQL injection in from parameter returns HTTP 400 and executes no database query.
  given:        "the Next.js application is running"
  when:         "GET /api/admin/export/events with Authorization: Bearer {ADMIN_API_KEY} and from parameter set to '; DROP TABLE behavioral_events; --'"
  expected:     "HTTP 400 is returned by Zod validation and no database query is executed"
  verified_via: executable_test_api

- test_id:      F-04-002-T04
  type:         integration
  blocking:     true
  description:  >
    CSV export content contains no email addresses, full names, dates of birth, or IP addresses.
  given:        "a valid admin export request is processed"
  when:         "the CSV content is inspected"
  expected:     "no column in the CSV contains email addresses, full names, dates of birth, or IP addresses"
  verified_via: executable_test_api

- test_id:      F-04-002-T05
  type:         integration
  blocking:     true
  description:  >
    Admin export endpoint is rate-limited after 5 requests within 60 minutes from the same IP.
  given:        "the Next.js application is running"
  when:         "6 GET requests are sent to /api/admin/export/events from the same IP within 60 minutes"
  expected:     "the 6th request receives HTTP 429"
  verified_via: executable_test_api

- test_id:      F-04-002-T06
  type:         integration
  blocking:     true
  description:  >
    Valid export request emits admin_export_requested and admin_export_completed behavioral events with export parameters.
  given:        "a valid admin export request has been processed"
  when:         "the behavioral_events table is queried"
  expected:     "both admin_export_requested and admin_export_completed events exist with the export parameters (date range) in the payload JSONB"
  verified_via: executable_test_api

- test_id:      F-04-002-T07
  type:         security
  blocking:     true
  description:  >
    Application refuses to start if ADMIN_API_KEY environment variable is shorter than 32 characters.
  given:        "the ADMIN_API_KEY environment variable is set to a value shorter than 32 characters"
  when:         "the application starts"
  expected:     "a startup validation error is thrown and the application refuses to start"
  verified_via: executable_test_api

- test_id:      F-04-002-T08
  type:         security
  blocking:     true
  description:  >
    Admin export CSV user_id column contains only UUID4 format values and no PII.
  given:        "a valid admin export CSV has been downloaded"
  when:         "all columns are inspected"
  expected:     "the user_id column contains only UUID4 format values and no personally identifiable information is present in any column"
  verified_via: executable_test_api
```

---

### Suite F-04-003 — User Data Export (GDPR Article 15)

```yaml
suite_id:               F-04-003
feature_id:             F-04-003
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-04-003-T01
  type:         integration
  blocking:     true
  description:  >
    POST to data export endpoint queues a background job, emits data_export_requested event, and returns HTTP 202 with Italian message.
  given:        "user is authenticated and navigates to the data export section"
  when:         "user clicks the request data export button"
  expected:     "the page shows a confirmation message in Italian 'La tua esportazione dati è in elaborazione.' and HTTP 202 is returned"
  verified_via: executable_test

- test_id:      F-04-003-T02
  type:         integration
  blocking:     true
  description:  >
    Completed export JSON contains required GDPR data categories and behavioral_events_summary with event counts only.
  given:        "the export job has completed for a user"
  when:         "the export JSON is generated and inspected"
  expected:     "the JSON contains user_profiles data, consent_records, wallet_transactions, protection_score_snapshots, and a behavioral_events_summary object with event counts by type — not raw event payloads"
  verified_via: executable_test_api

- test_id:      F-04-003-T03
  type:         integration
  blocking:     true
  description:  >
    Export ready notification displays a download link that expires after 24 hours.
  given:        "the export job has completed and user navigates to the in-app notification"
  when:         "the notification renders"
  expected:     "a download link is displayed on the page and the link expires after 24 hours"
  verified_via: executable_test

- test_id:      F-04-003-T04
  type:         integration
  blocking:     true
  description:  >
    Second data export request within 30 days returns HTTP 429 with Italian message about next available export.
  given:        "user has already requested a data export within the last 30 days"
  when:         "POST /api/user/data-export"
  expected:     "HTTP 429 is returned with an Italian message stating when the next export will be available"
  verified_via: executable_test_api

- test_id:      F-04-003-T05
  type:         integration
  blocking:     true
  description:  >
    user_id field in POST body is ignored and export is generated exclusively for the session user.
  given:        "a valid session exists for User A"
  when:         "POST /api/user/data-export with a user_id field in the body belonging to User B"
  expected:     "the export is generated exclusively for User A's data — User B's data is not included in the export"
  verified_via: executable_test_api

- test_id:      F-04-003-T06
  type:         integration
  blocking:     true
  description:  >
    behavioral_events_summary section contains only event_type and count objects with no raw JSONB payload data.
  given:        "the export JSON has been downloaded"
  when:         "the behavioral_events_summary section is reviewed"
  expected:     "the section contains only {\"event_type\": \"...\", \"count\": N} objects and no raw JSONB payload data"
  verified_via: executable_test_api

- test_id:      F-04-003-T07
  type:         security
  blocking:     true
  description:  >
    POST to data export endpoint without valid session returns HTTP 401 and no export job is queued.
  given:        "no valid session cookie exists"
  when:         "POST /api/user/data-export"
  expected:     "HTTP 401 is returned and no export job is queued"
  verified_via: executable_test_api

- test_id:      F-04-003-T08
  type:         security
  blocking:     true
  description:  >
    Signed export URL accessed after 24 hours returns HTTP 403 or HTTP 410 and the export file is no longer accessible.
  given:        "a signed export URL has been generated and 24 hours have elapsed"
  when:         "the signed URL is accessed via HTTP GET"
  expected:     "HTTP 403 or HTTP 410 is returned and the export file is no longer accessible"
  verified_via: executable_test_api
```

---

### Suite F-04-004 — Account Deletion (GDPR Article 17)

```yaml
suite_id:               F-04-004
feature_id:             F-04-004
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-04-004-T01
  type:         integration
  blocking:     true
  description:  >
    Account deletion confirmation modal displays Italian warning and requires typing ELIMINA to confirm.
  given:        "authenticated user navigates to the account deletion section"
  when:         "the confirmation modal renders"
  expected:     "an Italian warning message stating all data will be deleted is visible and a text input requiring the user to type 'ELIMINA' is present before the delete button becomes active"
  verified_via: executable_test

- test_id:      F-04-004-T02
  type:         integration
  blocking:     true
  description:  >
    Typing ELIMINA and submitting deletion invalidates session, deletes all PII rows atomically, and redirects to home page.
  given:        "user is on the account deletion confirmation modal"
  when:         "user types 'ELIMINA' in the confirmation field and clicks the delete button"
  expected:     "the session is invalidated, the browser is redirected to the home page, and all PII rows for that user are deleted in a single atomic transaction"
  verified_via: executable_test

- test_id:      F-04-004-T03
  type:         integration
  blocking:     true
  description:  >
    behavioral_events table returns zero rows for the original user_id after deletion completes.
  given:        "the deletion transaction has completed for a user"
  when:         "the behavioral_events table is queried for the original user_id"
  expected:     "zero rows are returned for the original user_id"
  verified_via: executable_test_api

- test_id:      F-04-004-T04
  type:         integration
  blocking:     true
  description:  >
    Previously linked behavioral event rows exist with tombstone UUID after deletion and original user_id is not recoverable.
  given:        "the deletion transaction has completed"
  when:         "the behavioral_events table is queried for the tombstone UUID 00000000-0000-0000-0000-000000000000"
  expected:     "the previously linked event rows exist with the tombstone UUID and the original user_id is not present or recoverable from any row"
  verified_via: executable_test_api

- test_id:      F-04-004-T05
  type:         integration
  blocking:     true
  description:  >
    Rolling back the deletion transaction leaves all PII rows intact with no partial deletion.
  given:        "the deletion transaction is simulated to fail midway and roll back"
  when:         "the transaction is rolled back"
  expected:     "all PII rows remain intact in the database and no partial deletion has occurred"
  verified_via: executable_test_api

- test_id:      F-04-004-T06
  type:         integration
  blocking:     true
  description:  >
    Logging in again with the same Google account after deletion creates a new account with no residual data.
  given:        "a user's account has been deleted"
  when:         "user attempts to log in again with the same Google account"
  expected:     "a new account is created from scratch and no residual data from the deleted account is present"
  verified_via: executable_test

- test_id:      F-04-004-T07
  type:         security
  blocking:     true
  description:  >
    POST to delete-account endpoint without confirmation_token ELIMINA returns HTTP 400 and no deletion occurs.
  given:        "a valid session exists"
  when:         "POST /api/user/delete-account with a body that does not contain confirmation_token: 'ELIMINA'"
  expected:     "HTTP 400 is returned and no deletion occurs"
  verified_via: executable_test_api

- test_id:      F-04-004-T08
  type:         security
  blocking:     true
  description:  >
    POST to delete-account endpoint without valid session returns HTTP 401 and no deletion occurs.
  given:        "no valid session cookie exists"
  when:         "POST /api/user/delete-account with confirmation_token: 'ELIMINA'"
  expected:     "HTTP 401 is returned and no deletion occurs"
  verified_via: executable_test_api

- test_id:      F-04-004-T09
  type:         security
  blocking:     true
  description:  >
    POST to delete-account endpoint with mismatched user_id in body deletes only the session user's data.
  given:        "a valid session exists for User A"
  when:         "POST /api/user/delete-account with a user_id field in the body belonging to User B and confirmation_token: 'ELIMINA'"
  expected:     "only User A's data is deleted — User B's data remains intact"
  verified_via: executable_test_api
```

---

### Suite F-04-005 — HTTP Security Headers

```yaml
suite_id:               F-04-005
feature_id:             F-04-005
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-04-005-T01
  type:         security
  blocking:     true
  description:  >
    Strict-Transport-Security header is present with correct max-age and includeSubDomains directive.
  given:        "the Next.js application is running"
  when:         "GET / (any page)"
  expected:     "the response includes the Strict-Transport-Security header with value 'max-age=31536000; includeSubDomains'"
  verified_via: executable_test_api

- test_id:      F-04-005-T02
  type:         security
  blocking:     true
  description:  >
    X-Frame-Options: DENY header is present on all HTTP responses.
  given:        "the Next.js application is running"
  when:         "GET / (any page)"
  expected:     "the response includes the X-Frame-Options header with value 'DENY'"
  verified_via: executable_test_api

- test_id:      F-04-005-T03
  type:         security
  blocking:     true
  description:  >
    X-Content-Type-Options: nosniff header is present on all HTTP responses.
  given:        "the Next.js application is running"
  when:         "GET / (any page)"
  expected:     "the response includes the X-Content-Type-Options header with value 'nosniff'"
  verified_via: executable_test_api

- test_id:      F-04-005-T04
  type:         security
  blocking:     true
  description:  >
    Content-Security-Policy script-src does not contain unsafe-inline or unsafe-eval and is restricted to self and Google accounts.
  given:        "the Next.js application is running"
  when:         "GET / (any page)"
  expected:     "the Content-Security-Policy header is present and script-src does not contain 'unsafe-inline' or 'unsafe-eval' — it is restricted to 'self' and 'https://accounts.google.com'"
  verified_via: executable_test_api

- test_id:      F-04-005-T05
  type:         security
  blocking:     true
  description:  >
    Permissions-Policy header restricts camera, microphone, and geolocation.
  given:        "the Next.js application is running"
  when:         "GET / (any page)"
  expected:     "the Permissions-Policy header is present and contains camera=(), microphone=(), and geolocation=()"
  verified_via: executable_test_api

- test_id:      F-04-005-T06
  type:         security
  blocking:     true
  description:  >
    Application achieves security grade A or higher on Mozilla Observatory scan.
  given:        "the application is deployed to the staging environment"
  when:         "a Mozilla Observatory scan (or equivalent) is run against the application URL"
  expected:     "the security grade is A or higher"
  verified_via: executable_test_api

- test_id:      F-04-005-T07
  type:         security
  blocking:     true
  description:  >
    Browser blocks scripts from external domains not in the CSP allowlist.
  given:        "the Next.js application is running"
  when:         "an attempt is made to load a script from an external domain not in the CSP allowlist (simulated via Playwright)"
  expected:     "the script is blocked by the browser's CSP evaluation and a CSP violation is reported"
  verified_via: executable_test
```

---

### Suite F-04-006 — Rate Limiting

```yaml
suite_id:               F-04-006
feature_id:             F-04-006
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-04-006-T01
  type:         security
  blocking:     true
  description:  >
    Login endpoint rate-limits after 20 requests within 60 seconds and returns HTTP 429 with Retry-After header and Italian error message.
  given:        "the Next.js application is running"
  when:         "21 POST requests are sent to /api/auth/signin from the same IP within 60 seconds"
  expected:     "the 21st request receives HTTP 429 with a Retry-After header and an Italian error message"
  verified_via: executable_test_api

- test_id:      F-04-006-T02
  type:         security
  blocking:     true
  description:  >
    Global rate limiter returns HTTP 429 on the 101st request of any type from the same IP within 60 seconds.
  given:        "the Next.js application is running"
  when:         "101 requests of any type are sent from the same IP within 60 seconds"
  expected:     "the 101st request receives HTTP 429 regardless of the specific endpoint"
  verified_via: executable_test_api

- test_id:      F-04-006-T03
  type:         integration
  blocking:     true
  description:  >
    HTTP 429 response includes Retry-After header with seconds until limit resets.
  given:        "a rate limit has been exceeded"
  when:         "the HTTP 429 response is inspected"
  expected:     "the Retry-After header is present in the response with the number of seconds until the rate limit resets"
  verified_via: executable_test_api

- test_id:      F-04-006-T04
  type:         integration
  blocking:     true
  description:  >
    rate_limit_exceeded behavioral event is emitted with endpoint and IP hash (not raw IP) in payload.
  given:        "a rate limit rejection has just occurred"
  when:         "the behavioral_events table is queried"
  expected:     "a rate_limit_exceeded event exists with the endpoint and a hashed IP (not raw IP address) in the payload JSONB"
  verified_via: executable_test_api

- test_id:      F-04-006-T05
  type:         integration
  blocking:     true
  description:  >
    Rate limit counter resets after the window expires and the next request is processed normally.
  given:        "a rate limit has been exceeded and the Redis TTL for the rate limit key has been advanced to simulate window expiry"
  when:         "the next request arrives after the window expires"
  expected:     "the request is processed normally and HTTP 200 (or appropriate success code) is returned"
  verified_via: executable_test_api

- test_id:      F-04-006-T06
  type:         security
  blocking:     true
  description:  >
    Redis rate limit keys contain only numeric counters and TTL — no raw IP addresses or user PII are stored as key values.
  given:        "rate limiting is active and requests have been made"
  when:         "the Redis keys for rate limiting are inspected"
  expected:     "rate limit Redis keys contain only numeric counters and TTL — IP addresses are hashed before use as key values and no raw PII is stored"
  verified_via: executable_test_api
```

---

### Suite F-04-007 — Dependency Vulnerability Scanning & CI

```yaml
suite_id:               F-04-007
feature_id:             F-04-007
pass_threshold:         100%
human_gate_required:    false
```

**Test cases**

```yaml
- test_id:      F-04-007-T01
  type:         security
  blocking:     true
  description:  >
    CI pipeline fails if npm audit finds any high or critical CVE in Node.js dependencies.
  given:        "a PR is opened against main"
  when:         "the GitHub Actions CI pipeline runs the npm audit --audit-level=high step"
  expected:     "the pipeline step runs as a required step and fails with a non-zero exit code if any high or critical CVE is found"
  verified_via: executable_test_api

- test_id:      F-04-007-T02
  type:         security
  blocking:     true
  description:  >
    CI pipeline fails if pip-audit finds any high or critical CVE in Python dependencies.
  given:        "a PR is opened against main"
  when:         "the GitHub Actions CI pipeline runs the pip-audit step against FastAPI service requirements"
  expected:     "the pipeline step runs as a required step and fails with a non-zero exit code if any high or critical CVE is found"
  verified_via: executable_test_api

- test_id:      F-04-007-T03
  type:         security
  blocking:     true
  description:  >
    CI pipeline fails if trivy image scan finds any critical CVE in Docker image layers.
  given:        "a Docker image is built for either service"
  when:         "the trivy image scan step runs in the CI pipeline"
  expected:     "the pipeline fails with a non-zero exit code if any critical CVE is found in the image layers"
  verified_via: executable_test_api

- test_id:      F-04-007-T04
  type:         integration
  blocking:     true
  description:  >
    Dependabot opens a PR within 7 days when a dependency with a security fix is released.
  given:        "Dependabot is configured for the repository"
  when:         "a new version of a dependency with a security fix is released"
  expected:     "Dependabot opens a PR within 7 days with the updated dependency version"
  verified_via: executable_test_api

- test_id:      F-04-007-T05
  type:         integration
  blocking:     true
  description:  >
    CI pipeline passes all audit steps and proceeds to Railway deployment when zero vulnerabilities are found.
  given:        "the CI pipeline runs with zero vulnerabilities in all dependency trees"
  when:         "all audit steps complete"
  expected:     "the pipeline passes all audit steps and the Railway deployment step proceeds"
  verified_via: executable_test_api

- test_id:      F-04-007-T06
  type:         security
  blocking:     true
  description:  >
    CI pipeline npm audit step fails with non-zero exit code when a dependency with a known high CVE is present and deployment step is skipped.
  given:        "a dependency with a known high CVE has been intentionally added to package.json in a test branch"
  when:         "the CI pipeline runs"
  expected:     "the npm audit step fails with a non-zero exit code and the deployment step is skipped"
  verified_via: executable_test_api
```

---

### Suite F-04-008 — No-Real-Money Guardrails

```yaml
suite_id:               F-04-008
feature_id:             F-04-008
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-04-008-T01
  type:         integration
  blocking:     true
  description:  >
    Database CHECK constraint rejects INSERT on wallet_transactions with transaction_type payout.
  given:        "the database CHECK constraint is in place on wallet_transactions"
  when:         "a direct SQL INSERT on wallet_transactions with transaction_type = 'payout' is attempted"
  expected:     "the insert is rejected with a constraint violation error"
  verified_via: executable_test_api

- test_id:      F-04-008-T02
  type:         integration
  blocking:     true
  description:  >
    Application refuses to start if STRIPE_KEY environment variable is set.
  given:        "the Next.js application is configured with a STRIPE_KEY environment variable set"
  when:         "the application starts"
  expected:     "the application throws a fatal startup error and refuses to start"
  verified_via: executable_test_api

- test_id:      F-04-008-T03
  type:         integration
  blocking:     true
  description:  >
    CI lint rule fails when a Stripe import is added to any source file.
  given:        "a developer adds 'import Stripe from stripe' to any source file and opens a PR"
  when:         "the CI lint step runs"
  expected:     "the pipeline fails with an error identifying the prohibited Stripe import"
  verified_via: executable_test_api

- test_id:      F-04-008-T04
  type:         integration
  blocking:     true
  description:  >
    Wallet screen displays Italian P-Coin disclaimer.
  given:        "user is authenticated and navigates to the wallet screen"
  when:         "the wallet page renders"
  expected:     "the Italian disclaimer 'P-Coin non hanno valore monetario reale' is visible on the page"
  verified_via: executable_test

- test_id:      F-04-008-T05
  type:         integration
  blocking:     true
  description:  >
    Risk Arena screen displays Italian P-Coin disclaimer.
  given:        "user is authenticated and navigates to the Risk Arena screen"
  when:         "the Risk Arena page renders"
  expected:     "the Italian disclaimer 'P-Coin non hanno valore monetario reale' is visible on the page"
  verified_via: executable_test

- test_id:      F-04-008-T06
  type:         integration
  blocking:     true
  description:  >
    Future Vault screen displays Italian P-Coin disclaimer.
  given:        "user is authenticated and navigates to the Future Vault screen"
  when:         "the Future Vault page renders"
  expected:     "the Italian disclaimer 'P-Coin non hanno valore monetario reale' is visible on the page"
  verified_via: executable_test

- test_id:      F-04-008-T07
  type:         security
  blocking:     true
  description:  >
    Database CHECK constraint rejects transaction_type redeem via the application API and returns HTTP 500 with no silent failure.
  given:        "the database CHECK constraint is in place on wallet_transactions"
  when:         "POST /api/wallet/mutate with transaction_type: 'redeem' is attempted via the application API"
  expected:     "the database rejects the insert due to the CHECK constraint and HTTP 500 is returned — no silent failure occurs"
  verified_via: executable_test_api
```

---

### Suite F-04-009 — Privacy Audit & PII Compliance

```yaml
suite_id:               F-04-009
feature_id:             F-04-009
pass_threshold:         100%
human_gate_required:    true
```

**Test cases**

```yaml
- test_id:      F-04-009-T01
  type:         integration
  blocking:     true
  description:  >
    No PII appears in behavioral_events, wallet_transactions, or protection_score_snapshots tables.
  given:        "the privacy audit is run against the deployed database"
  when:         "all rows in behavioral_events, wallet_transactions, and protection_score_snapshots are inspected"
  expected:     "no email address, full name, date of birth, or IP address appears in any column of these tables"
  verified_via: executable_test_api

- test_id:      F-04-009-T02
  type:         integration
  blocking:     true
  description:  >
    No PII appears in any application log output from Next.js or FastAPI.
  given:        "the privacy audit is run against application logs"
  when:         "all log outputs from the Next.js application and FastAPI service are inspected"
  expected:     "no PII (email, name, date of birth, raw IP address) appears in any log line from either service"
  verified_via: executable_test_api

- test_id:      F-04-009-T03
  type:         integration
  blocking:     true
  description:  >
    No Redis key or value contains raw PII — only UUIDs, hashed IPs, and numeric counters are present.
  given:        "the privacy audit is run against Redis"
  when:         "all Redis keys and values are inspected"
  expected:     "no Redis key or value contains raw PII — only UUIDs, hashed IP addresses, and numeric counters are present"
  verified_via: executable_test_api

- test_id:      F-04-009-T04
  type:         integration
  blocking:     true
  description:  >
    Data export endpoint returns all required GDPR Article 15 data categories with no undocumented data fields.
  given:        "the data export endpoint is tested end-to-end"
  when:         "the export JSON is downloaded and inspected"
  expected:     "the export contains all required GDPR Article 15 data categories and no undocumented data fields are present"
  verified_via: executable_test_api

- test_id:      F-04-009-T05
  type:         integration
  blocking:     true
  description:  >
    Data deletion endpoint leaves zero PII rows for the deleted user_id after completion.
  given:        "the data deletion endpoint is tested end-to-end"
  when:         "deletion completes and a database scan is performed"
  expected:     "zero PII rows remain for the deleted user_id in any table"
  verified_via: executable_test_api

- test_id:      F-04-009-T06
  type:         integration
  blocking:     true
  description:  >
    GDPR compliance checklist document covers all required GDPR articles with pass/fail status.
  given:        "the docs/gdpr_compliance_checklist.md document is committed to the repository"
  when:         "the document is reviewed"
  expected:     "the checklist contains completed entries covering all GDPR Articles 13, 15, 17, 25, and 32 requirements with a pass/fail status for each item"
  verified_via: executable_test_api

- test_id:      F-04-009-T07
  type:         security
  blocking:     true
  description:  >
    Only Next.js app port 3000 and Metabase port 3001 are reachable from the public internet — PostgreSQL and Redis ports are not publicly accessible.
  given:        "the complete application is deployed to the Railway EU West staging environment"
  when:         "a network scan is performed from outside the Railway private network"
  expected:     "only port 3000 (Next.js) and port 3001 (Metabase) are reachable — PostgreSQL port 5432 and Redis port 6379 are not accessible from the public internet"
  verified_via: executable_test_api

- test_id:      F-04-009-T08
  type:         security
  blocking:     true
  description:  >
    privacy_audit_completed behavioral event exists in behavioral_events table after audit completion.
  given:        "the privacy audit has been completed"
  when:         "the behavioral_events table is queried for the privacy_audit_completed event"
  expected:     "a privacy_audit_completed event row exists with occurred_at matching the audit completion time"
  verified_via: executable_test_api
```

---

## Cross-feature security tests

```yaml
- test_id:      SEC-GLOBAL-01
  type:         security
  blocking:     true
  description:  No credentials, tokens, or PII appear in any logged command output.
  verified_via: milestone_report.commands_run[*].stdout_summary

- test_id:      SEC-GLOBAL-02
  type:         security
  blocking:     true
  description:  The security checklist in doc1 was followed for this feature.
  verified_via: milestone_report.security_checklist_followed

- test_id:      SEC-GLOBAL-03
  type:         security
  blocking:     true
  description:  No high or critical CVEs introduced by new dependencies.
  verified_via: milestone_report.commands_run — look for audit command and exit code
```

---

## Validator output format

```yaml
validator_run:
  suite_id:         ""
  run_at:           ""           # ISO 8601
  provider:         ""
  model_version:    ""
  overall:          pass | fail
  blocking_passed:  true | false
  human_gate:       pending | approved | rejected

  results:
    - test_id:      ""
      status:       pass | fail | skip
      notes:        ""           # brief reason if fail or skip

  failures:         []           # list of test_ids that failed
  escalations:      []           # security failures always listed here separately
```

---

## Amendments

| Version | Date | Changed by | Summary |
|---|---|---|---|
| 1.0 | 2025-01-01 | CTO orchestrator | Initial — covers all features F-01-001 through F-04-009 |
