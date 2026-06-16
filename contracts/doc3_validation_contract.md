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
| project_id | |
| contract_version | 1.0 |
| created_at | |
| validator_provider | <!-- e.g. different from worker provider, e.g. GPT-4o, Gemini --> |
| validator_model_version | <!-- pin exact version to prevent drift --> |

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

<!-- One suite per feature. suite_id matches feature_id from doc2. -->

---

### Suite F-01-001 — [Feature name]

```yaml
suite_id:               F-01-001
feature_id:             F-01-001      # ref to doc2
pass_threshold:         100%          # % of blocking tests that must pass to merge
human_gate_required:    false         # true for high-risk or architectural features
```

**Test cases**

For `app_type: api` — write given/when/expected at the HTTP interface level
(method, path, body, expected status and response shape).

For `app_type: frontend` or `fullstack` — write given/when/expected at the
browser interaction level (what a user navigates to, clicks, types, and sees).
For API-level security checks in a frontend/fullstack app, mark
`verified_via: executable_test_api` so the generator uses `requests` instead.

```yaml
# ── API example ──────────────────────────────────────────────────────────
- test_id:      F-01-001-T01
  type:         unit
  blocking:     true
  description:  >
    User can register with a valid email and password.
  given:        "no user exists with email a@b.com"
  when:         "POST /api/users with body {email: a@b.com, password: secret123}"
  expected:     "201 Created, body contains id and email, no password field"
  verified_via: executable_test

# ── Frontend / fullstack example ─────────────────────────────────────────
- test_id:      F-01-001-T02
  type:         integration
  blocking:     true
  description:  >
    User can complete the registration form and reach the dashboard.
  given:        "user is on the /register page"
  when:         "user fills email 'a@b.com' and password 'secret123', clicks the Register button"
  expected:     "page navigates to /dashboard, heading 'Welcome' is visible"
  verified_via: executable_test

# ── Security (HTTP-level, even in frontend/fullstack apps) ───────────────
- test_id:      F-01-001-T03
  type:         security
  blocking:     true
  description:  >
    Protected API route returns 401 without authentication.
  given:        "no Authorization header is provided"
  when:         "GET /api/profile"
  expected:     "401 Unauthorized, no internal error details in body"
  verified_via: executable_test_api   # always requests-based, even in frontend apps

- test_id:      F-01-001-T04
  type:         regression
  blocking:     false
  description:  >
    [Check that this feature does not break previously passing features.
     Write at the same interface level as the other tests in this suite.]
  given:        ""
  when:         ""
  expected:     ""
  verified_via: executable_test
```

---

### Suite F-01-002 — [Feature name]

<!-- Copy suite block above and fill in -->

---

## Cross-feature security tests
<!-- These run after every milestone, regardless of which feature was implemented.
     These three are checked by deterministic Python code reading the milestone
     report — NOT compiled into executable tests like the feature suites above. -->

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
<!-- The validator must produce a result in this exact format after each run.
     This output is read by the system to update doc4 and shared memory. -->

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
| 1.0 | | CTO orchestrator | Initial |
