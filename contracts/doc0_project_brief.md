# Project brief
<!-- Doc 0 — written by the USER before the CTO orchestrator session begins.
     The CTO reads this file, asks clarifying questions, and appends to
     clarification_log until shared_plan_approved is set to true.
     Do not edit clarification_log or shared_plan_approved manually. -->

---

## Identity

| Field | Value |
|---|---|
| project_id | protego-life-sim-v1 |
| project_name | Protego Life Simulator |
| created_at | 2026-06-22 |
| author | vcucinel (vitocucinelli05@gmail.com) |

---

## What we are building

A **behavioral finance simulator** designed to test and train financial self-control and risk-management discipline in users — without involving real money, real investments, or real gambling.

The platform operates entirely on a virtual currency called **P-Coin**. Users receive a weekly allocation of P-Coins, set monthly virtual spending limits, allocate a portion to a protected "Future Vault," and then interact with an abstract "Risk Arena" — a probabilistic mini-game environment that applies behavioral pressure without mimicking real-world gambling or betting.

The core product innovation is the **Protection Score**: a composite metric that rewards disciplined financial behavior (respecting limits, accepting pauses, maintaining the vault, managing daily expenses) rather than rewarding risk-taking success. This makes the app a tool for **behavioral awareness and self-regulation training**, not a reward-for-profit mechanic.

The MVP is designed from the ground up as a **quantitative beta experiment**: every user interaction is instrumented for KPI tracking, behavioral correlation analysis, and an internal analytics dashboard. Post-session qualitative surveys and user interviews complement the automated tracking.

The target user is someone who wants to understand and improve their own financial impulse-control behavior in a safe, virtual, game-like environment — with no financial risk and no real-money stakes.

---

## Domain

**Financial wellness × behavioral psychology × gamification.**

The application sits at the intersection of:

- **Responsible gambling awareness** — simulating the cognitive and emotional patterns of gambling-adjacent behavior (impulsive deposits, chasing losses, limit overrides) so users can observe and reflect on their own patterns without real-world consequences.
- **Financial literacy and discipline training** — through the Life Layer (career progression, virtual rent/bills/groceries/emergencies) and the Future Vault, users practice balancing risk appetite with real-life financial stability in a simulated economy.
- **Behavioral science research** — the beta is explicitly designed as a quantitative experiment with a full KPI taxonomy (acquisition, activation, behavioral, retention, investor), tracking user responses to alerts, pauses, wins, losses, and limit boundaries.

The application must **never** be positioned as, or confused with, a real casino, sportsbook, investment platform, or prediction market. All UI, marketing copy, and game mechanics must remain fully abstract.

---

## Tech stack

<!-- List what you already know you want to use. Leave blank if undecided. -->

| Layer | Choice | Reason / constraint |
|---|---|---|
| Language | Undecided | |
| Framework | Undecided | |
| Database | Undecided | Must support behavioral event logging and KPI aggregation |
| Auth | Undecided | Must support user registration and profile; no advanced KYC required for MVP |
| Hosting / infra | Undecided | |
| CI/CD | Undecided | |
| Other | Analytics dashboard | Internal dashboard required in MVP to monitor KPIs in real time |

---

## Hard constraints

1. **No real money of any kind.** The platform must never involve real investments, real financial yields, real currency, or any mechanism that converts P-Coins into cash or real-world financial instruments.
2. **No real financial integrations.** No bank account linking, no real PIPs, no actual ETFs, no PSP/PISP (Payment Service Provider / Payment Initiation Service Provider) integrations in the MVP.
3. **No real gambling integrations.** No connections to real betting operators, sportsbooks, real-sports odds feeds, or prediction markets.
4. **No advanced KYC.** Know-Your-Customer protocols are explicitly out of scope for the MVP.
5. **No automatic voucher payouts.** Any future reward program must require manual, non-transferable voucher issuance. No automated conversion of P-Coins to real goods.
6. **No real-world game references.** UI, game mechanics, and marketing copy must use abstract representations (binary choices, symbolic cards, random wheels). No references to real casinos, roulette, blackjack, specific sports, or prediction markets.
7. **Privacy by design (non-negotiable architectural constraint).** Data collection must be minimized to only what is strictly necessary for behavioral analysis. Users must be fully informed during onboarding that behavioral data is being collected.
8. **Transparency with users.** The app must explicitly state during onboarding that it is a behavioral simulator, that P-Coins have no monetary value, and that behavioral data is actively collected for research purposes.
9. **P-Coins have zero monetary value.** This must be contractually and technically enforced — no path to redemption, exchange, or transfer to real financial value.

---

## Non-goals

- Real-money transactions or wallets of any kind.
- Integration with real bank accounts, brokerage accounts, or payment processors.
- Real sports data, real odds feeds, or any connection to regulated gambling operators.
- Advanced Know-Your-Customer (KYC) flows or identity verification.
- Automatic voucher payouts or automatic conversion of in-app rewards to real goods.
- A public-facing leaderboard or social comparison mechanic based on Risk Arena outcomes (rewards discipline, not risk wins).
- Multi-player or social risk-taking mechanics.
- A real-money version of the app (this is explicitly a beta experiment to validate demand, not the live product).
- Any AI-powered personalized financial advice — the app simulates behavior, it does not give regulated financial guidance.

---

## Team

| Field | Value |
|---|---|
| team_size | Undecided / TBD |
| experience_level | Undecided / TBD |
| working_style | Undecided / TBD |

---

## Known risks

1. **Regulatory ambiguity.** Even without real money, a behavioral simulator that mimics gambling mechanics may attract scrutiny from gambling regulators in certain jurisdictions. The "no real money" guardrail must be airtight both technically and legally.
2. **User data sensitivity.** Behavioral data around financial impulsivity is deeply personal. A data breach or misuse allegation could be reputationally catastrophic. Privacy-by-design architecture must be a first-class concern, not a post-launch addition.
3. **Behavioral KPI instrumentation complexity.** The full KPI taxonomy (5 categories, 40+ individual KPIs) requires a robust event-tracking architecture from day one. Retrofitting analytics onto a live app is expensive and unreliable.
4. **Engagement without real-money stakes.** Keeping users engaged in a game with no real financial upside is a retention risk. The Life Layer progression, Protection Score visibility, and mission system must provide sufficient intrinsic motivation.
5. **Scope creep from the Risk Arena.** Without strict design guardrails, the Risk Arena could evolve toward realistic gambling mechanics. The abstract-only constraint must be enforced at design review, not just in code.
6. **Qualitative data collection operationalization.** Post-session surveys and user interviews are listed as requirements but require operational infrastructure (survey tooling, interview scheduling, incentive structure) beyond the core app — this is a non-trivial project dependency.
7. **Beta countdown mechanic (365-day timer).** If the beta expires before sufficient behavioral data is collected, the experiment may be inconclusive for investor pitch purposes. The analytics dashboard must give early warning of data quality issues.
8. **Unclear tech stack.** No technical choices have been locked in yet. Early architectural decisions (event-sourcing vs. traditional CRUD for behavioral logging, mobile vs. web-first, etc.) will have large downstream consequences.

---

## Reference material

- [protego_life_simulator.md](../protego_life_simulator.md) — full product specification including MVP features, user journey, core mechanics, KPI taxonomy, legal guardrails, and system design requirements. This is the primary source document.

---

## MVP Features summary (from reference spec)

The following features are in scope for Phase 1 (MVP):

1. **User registration and profile onboarding** — including initial P-Coin balance, monthly spending limit configuration, Future Vault protection quota selection, risk profile selection (Prudent / Balanced / Growth), and explicit terms acceptance (no real money).
2. **P-Coin wallet system** — tracks balance; handles weekly allocations; supports deposits to Risk Arena and deductions for Life Layer expenses.
3. **Configuration screens** — monthly spending limit and protection quota settings, editable post-onboarding.
4. **Simulated risk profile selection** — Prudent, Balanced, or Growth; determines Future Vault scenario variance (e.g., ±2%, ±5%, ±10%).
5. **Deposit Simulation (core interaction)** — intercepts every Risk Arena transfer, displays risk/protection split, triggers behavioral alerts for approaching limits or rapid consecutive deposits, presents actionable options (confirm / reduce / pause / review budget / go to vault).
6. **Risk Arena** — abstract probabilistic games (binary choices, symbolic cards, random wheels) applying behavioral pressure. No real-world gambling mechanics.
7. **Future Vault** — visualizes protected funds; displays simulated annual scenarios per risk profile; translates virtual capital into tangible goal proxies (bills covered, emergency fund progress).
8. **Protection Score algorithm** — transparent composite score: 30% limit respect, 20% vault maintenance, 15% pause/alert acceptance, 15% daily expense management, 10% anti-impulsive behavior, 10% continuity and mission completion.
9. **Life Layer** — career progression (Intern 1,000 P-Coins/week → Partner/CEO 4,000 P-Coins/week); mandatory virtual expenses (rent, bills, groceries, emergencies); progression tied to disciplined financial behavior, not Risk Arena success.
10. **Beta countdown timer** — 365-day countdown; post-session qualitative survey prompts.
11. **Internal analytics dashboard** — real-time aggregation and visualization of the full KPI taxonomy (acquisition, activation, behavioral, retention, investor KPIs).
12. **Behavioral tracking system** — event-level instrumentation for all 40+ KPIs; privacy-by-design data minimization; full transparency with users.

---

## Clarification log
<!-- MANAGED BY CTO ORCHESTRATOR — do not edit manually.
     Each entry is appended after a round-trip clarification exchange. -->

<!-- format per entry:
round: 1
question: "..."
answer: "..."
resolved: true
-->

---


---
round: 1
question: "What is the primary delivery target for the MVP — web application (desktop/mobile browser), native mobile app (iOS/Android), or a hybrid/PWA — and what is the approximate team size and technical experience level (e.g., 1-2 solo developers, small startup team with full-stack experience, outsourced agency)?"
answer: "I'm only developer,me. I'm not a full stack developer but i'm pretty good in programming. I'm asking help to you to choose the type of application, the application needs to work on ios and android. Maybe for now a PWA is the best but i also would be able to have a real application after without rewriting all the code"
resolved: true
---


---
round: 2
question: "What is your primary programming background — for example, are you most comfortable with JavaScript/TypeScript, Python, Dart, or another language — and do you have any prior experience with frontend frameworks like React, Vue, or Flutter?"
answer: "I had some minimal experience with flutter but i feel better using js/typescript and python. As frontend framework i used react and vue more time"
resolved: true
---


---
round: 3
question: "Do you have any experience with or preference for a backend framework (e.g., Node.js/Express, FastAPI, Django), and do you have access to any cloud provider account (AWS, GCP, Firebase, Supabase, etc.) or are you starting from scratch on infrastructure?"
answer: "I don't have any access and i'm starting from scratch. as backend i know node.js/Express and FastAPI"
resolved: true
---


---
round: 4
question: "What is your approximate monthly budget for infrastructure and services (e.g., hosting, database, analytics tools) — for example, are you targeting near-zero/free-tier only, under $50/month, or are you comfortable spending $100-200/month for a more robust setup during the beta?"
answer: "the budget can also be high. The important thing is that i will be able to harvest all the KPI that i mentioned. Give me some possible solution, even based on the countermeasrues on numbe r of active users ecc."
resolved: true
---


---
round: 5
question: "What is your expected beta user volume and timeline — specifically, how many concurrent users do you anticipate during the 365-day beta (e.g., tens of users for a closed private beta, hundreds for a semi-public beta, or thousands for an open beta) — and do you have a target launch date or deadline driving the MVP delivery?"
answer: "the MVP delivery is in 2 months and i'm palanning to use this system to help me in the creation. The beta coudl last also 365 and we expect that quite some users start to use it()[Dwe dont have estimated the number"
resolved: true
---


---
round: 6
question: "Do you have any legal or compliance review already in place (e.g., a lawyer familiar with gambling/fintech regulation in your target jurisdiction), and which countries or regions are you planning to launch the beta in — this is critical because even a no-real-money simulator may face regulatory scrutiny in certain jurisdictions (e.g., UK, EU, US states) and will directly affect architecture decisions around data residency, GDPR compliance, and terms of service?"
answer: "for now only in Italy and we dont have any compliance review about that"
resolved: true
---


---
round: 7
question: "Do you have any preference or constraint on how users will be recruited and authenticated for the beta — for example, will this be invite-only (closed beta with a whitelist), open self-registration, or social login (Google/Apple) — and do you need any age verification or minimum age gate given the behavioral finance and gambling-adjacent nature of the content?"
answer: "The idea is to make the MVP usable by everyone so maybe could integrate a google authentication and of course see the the client is 18 years old"
resolved: true
---


---
round: 8
question: "Do you have any existing design assets, brand guidelines, or UI mockups for the app (e.g., Figma files, color palette, logo), or are you starting from zero on design as well — and do you have a preference for a component library (e.g., Material UI, Chakra UI, Tailwind) to accelerate frontend development given your 2-month deadline?"
answer: "No i don't have an UI mockups but maybe we can provide after the mockup(if you start to build the backend before. As a component library i think chackra ui is fine"
resolved: true
---


---
round: 9
question: "Do you have any preference for how the internal analytics dashboard is delivered — for example, embedded inside the same app (admin-only route), a separate standalone web app, or a third-party BI tool like Metabase or Grafana — and who will be accessing it (just you, or also non-technical stakeholders like investors)?"
answer: "i nede to harvest KPI but also behavioural patterns as you can see from doc0. So a third party is also better. Don'tt fortget all the controls for the privacy"
resolved: true
---


---
round: 10
question: "Do you have any preference for where user data and the database are hosted geographically — specifically, given GDPR and Italian privacy law (Codice Privacy + Garante), all personal and behavioral data must reside on EU-based servers — and are you comfortable using a managed cloud platform like Supabase (EU region) or Railway for the database and backend hosting, or do you have a strong preference for a specific cloud provider like AWS EU or GCP Europe-West?"
answer: "the data should be in europe i could say. I dont have strong preference for the specific cloud provider"
resolved: true
---


---
round: 11
question: "Do you have any existing domain name or brand identity registered for Protego, and do you need the MVP to support Italian-language localization (i18n) from day one, or is English-only acceptable for the initial beta?"
answer: "mvp in italia and no i don't have a domain"
resolved: true
---


---
round: 12
question: "Do you have any preference for how the behavioral event data is stored and queried — specifically, are you comfortable with an event-sourcing or append-only log approach (e.g., every user action is stored as an immutable event row) versus a traditional CRUD database model — and do you have any preference for PostgreSQL versus a dedicated time-series or analytics database like ClickHouse for the KPI aggregation layer?"
answer: "i prefer maybe a dedicated time series analysis. The main idea is to have the data in a table that i can also use to analyze offline using ml algorithms. Maybe postgree is better"
resolved: true
---

## Shared plan

<!-- MANAGED BY CTO ORCHESTRATOR — written once clarification is complete. -->

shared_plan_approved: false

summary: >
  Protego Life Simulator is a behavioral finance PWA built as a fullstack Next.js 14 application with a FastAPI microservice for behavioral event ingestion. The frontend is a React-based PWA using Chakra UI with Italian i18n, installable on iOS and Android. Authentication uses NextAuth.js with Google OAuth plus a DOB age gate (18+). All user state, wallet, and game data lives in PostgreSQL 16 with TimescaleDB extension enabling time-bucketed KPI queries and CSV export for offline ML analysis. Metabase OSS self-hosted on Railway EU West provides the internal analytics dashboard. Redis handles session storage and rate limiting. All services run on Railway EU West (Frankfurt) to satisfy GDPR and Italian Codice Privacy data residency requirements.

key_decisions:
  - PWA via Next.js 14 App Router: Single codebase deployable to web, installable on iOS/Android as PWA, and upgradeable to React Native Expo later without rewriting business logic or API contracts.
  - NextAuth.js with Google OAuth provider: Handles Google login, JWT session management, and age-gate check. DOB collected at onboarding, verified server-side before session is activated.
  - PostgreSQL 16 with TimescaleDB extension: Relational tables for users/wallets/game state via Prisma ORM plus a hypertable for behavioral_events as append-only immutable rows. Enables time-bucketed KPI queries and CSV/parquet export for offline ML.
  - FastAPI Python 3.12 as dedicated event ingestion microservice: Receives POST /events from Next.js frontend, validates with Pydantic, bulk-inserts into TimescaleDB hypertable. Python is the natural language for the ML export pipeline and keeps event writes decoupled from the Next.js request cycle.
  - Chakra UI v2 with next-i18next for Italian localization: Accelerates UI development, mobile-responsive out of the box, supports future language additions.
  - Metabase OSS self-hosted on Railway EU West: Connects directly to PostgreSQL, provides no-code KPI dashboards for investor and stakeholder access, with row-level security and GDPR-compliant data masking views.
  - Railway EU West Frankfurt for all services: Satisfies GDPR Article 44 and Italian Codice Privacy data residency requirement. No data leaves the EU.
  - Redis 7 for session store and rate limiting: NextAuth.js uses Redis adapter for distributed sessions. Rate limiting on deposit simulation and Risk Arena endpoints enforces behavioral pause mechanics.
  - Atomic PostgreSQL transactions for all P-Coin operations: Row-level locking prevents double-spend and ensures wallet integrity without any real financial rails.
  - Privacy-by-design pseudonymous event storage: behavioral_events table stores only pseudonymous user_id UUID, never PII. Separate user_profiles table holds PII with strict access controls. Metabase queries only aggregate views.

open_assumptions:
  - Google OAuth credentials will be created by the developer in Google Cloud Console before deployment at no cost.
  - Railway Starter plan (~$5/month per service) is used for production beta, estimated $30-60/month total at low-to-medium user volume.
  - TimescaleDB extension is available via the timescale/timescaledb Docker image on Railway.
  - Metabase OSS is self-hosted on Railway as a Docker container with no Metabase Cloud cost.
  - Age verification is a soft DOB gate only. No document-based KYC. Legal review for Italian ADM compliance is the developer's responsibility before public launch.
  - The 365-day beta countdown starts from the first user registration date stored in the database.
  - Post-session qualitative surveys are implemented as an in-app modal linking to an external Google Form, not a custom survey engine.
  - Risk Arena abstract game outcomes are generated server-side using cryptographically secure random functions.
  - No push notifications in MVP PWA due to iOS PWA push limitations. In-app alerts only.
  - Offline ML analysis is done by the developer exporting CSV from TimescaleDB directly. No automated ML pipeline is in scope for MVP.

tech_stack:
  language: TypeScript 5 (Next.js frontend and API routes), Python 3.12 (FastAPI event ingestion service)
  framework: Next.js 14 with App Router (fullstack PWA) and FastAPI 0.111 (event microservice)
  database: PostgreSQL 16 with TimescaleDB 2.15 extension; Prisma ORM 5 for schema and migrations; behavioral_events stored as TimescaleDB hypertable with append-only rows
  auth: NextAuth.js v4 with Google OAuth 2.0 provider; JWT sessions stored in Redis via @next-auth/upstash-redis-adapter; DOB age-gate enforced server-side at session creation
  hosting: Railway EU West Frankfurt: Next.js app service, FastAPI service, PostgreSQL plus TimescaleDB service, Redis service, Metabase OSS service
  ci_cd: GitHub Actions: ESLint plus TypeScript type-check plus Prisma schema validation plus Jest unit tests on every PR; Railway auto-deploy on merge to main via GitHub integration
  other: Chakra UI v2 (component library), next-i18next (Italian i18n), next-pwa (PWA manifest and service worker), Metabase OSS 0.49 (self-hosted analytics dashboard), Zod (runtime validation in Next.js), Pydantic v2 (FastAPI request validation), node-cron (weekly P-Coin allocation job)

scope_boundary: "IN SCOPE: User registration with Google OAuth plus DOB age gate and full onboarding flow (P-Coin balance, spending limit, vault quota, risk profile, terms acceptance); P-Coin wallet with weekly allocation cron job and atomic transactions; configuration screens for spending limit and protection quota; Deposit Simulation flow with behavioral alerts and action options; Risk Arena with three abstract mini-games (binary choice, symbolic card flip, random wheel) and server-side cryptographic outcome generation; Future Vault with protected balance visualization and simulated annual scenarios per risk profile; Protection Score engine with six weighted components; Life Layer with five career tiers and mandatory virtual expense deductions; 365-day beta countdown timer; post-session survey modal linking to external Google Form; behavioral event ingestion via FastAPI with 40+ KPI event types into TimescaleDB hypertable; Metabase OSS analytics dashboard with pre-built KPI dashboards; GDPR compliance including privacy notice, pseudonymous event storage, data export and deletion endpoints, and cookie consent banner; Italian i18n via next-i18next; PWA installable on iOS and Android; admin CSV export route. OUT OF SCOPE: Real-money transactions or payment processors; real gambling mechanics or real sports data; advanced KYC or document identity verification; automatic voucher or reward payouts; public leaderboard or social comparison; multiplayer mechanics; AI-powered financial advice; native iOS/Android app (post-MVP React Native migration); automated ML pipeline; custom survey engine; push notifications; multi-language support beyond Italian; legal and compliance review."
first_milestone: "Foundation: Auth plus Wallet plus Event Pipeline (14 days). Deliverables: Next.js 14 project scaffolded with Chakra UI, next-i18next Italian locale, next-pwa, Prisma, and NextAuth Google OAuth; PostgreSQL schema with users, user_profiles, wallets, wallet_transactions, and sessions tables via Prisma migrations; TimescaleDB hypertable behavioral_events with columns user_id UUID, event_type VARCHAR, payload JSONB, occurred_at TIMESTAMPTZ as append-only with no updates or deletes; FastAPI event ingestion service with POST /events endpoint using Pydantic validation and bulk insert to behavioral_events plus GET /health endpoint; Google OAuth login flow with DOB age gate rejecting users under 18 and storing pseudonymous profile; GDPR onboarding screen with privacy notice, data collection disclosure, P-Coin no-monetary-value declaration, and terms acceptance stored as consent events; P-Coin wallet creation on registration with initial 1000 P-Coin Intern tier balance; weekly allocation cron job via node-cron adding P-Coins based on career tier every Monday 00:00 UTC; Redis session store wired to NextAuth adapter; GitHub Actions CI with ESLint plus TypeScript check plus Prisma schema validation on every PR; all five Railway EU West services running with environment variables configured; Metabase connected to PostgreSQL with one starter dashboard showing event count per event_type over time."
app_type: "fullstack"
app_run_command: "npm run dev"
app_port: 3000

# Auxiliary services (databases, caches, queues) and env vars the
# application needs. The validator starts every service on the shared
# Docker network, waits for each to be reachable, then starts the app
# with app_env injected, so the app can reach services by their `name`.
```yaml
app_env:
  DATABASE_URL: postgresql://protego:protego_pass@db:5432/protego
  REDIS_URL: redis://redis:6379
  NEXTAUTH_URL: http://localhost:3000
  NEXTAUTH_SECRET: dev_secret_change_in_production
  GOOGLE_CLIENT_ID: your_google_client_id
  GOOGLE_CLIENT_SECRET: your_google_client_secret
  NEXT_PUBLIC_EVENT_API_URL: http://events:8000
  NODE_ENV: development
services:
- name: db
  image: timescale/timescaledb:latest-pg16
  port: 5432
  env:
    POSTGRES_USER: protego
    POSTGRES_PASSWORD: protego_pass
    POSTGRES_DB: protego
- name: redis
  image: redis:7-alpine
  port: 6379
  env: {}
- name: events
  image: python:3.12-slim
  port: 8000
  env:
    DATABASE_URL: postgresql://protego:protego_pass@db:5432/protego
    PYTHONUNBUFFERED: '1'
- name: metabase
  image: metabase/metabase:v0.49.0
  port: 3001
  env:
    MB_DB_TYPE: postgres
    MB_DB_DBNAME: metabase
    MB_DB_PORT: '5432'
    MB_DB_USER: protego
    MB_DB_PASS: protego_pass
    MB_DB_HOST: db
```
