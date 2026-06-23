# Protego Life Simulator

## 22 June 2026

### Core App Concept & Guardrails

- The application is a behavioral simulator designed to test financial self-control and the management of risk, rather than a real gambling or betting platform.
- The platform operates exclusively on a virtual currency ("P-Coin").
- The application must not involve real money, real investments, real financial yields, or automatic conversions to cash.
- The system must incorporate privacy by design, minimizing data collection while tracking behavioral patterns.
- The UI and marketing must avoid any references to real casinos, bookmakers, real sports odds, or prediction markets.

### MVP Features to Develop (Phase 1)

- User registration and profile onboarding.
- A wallet system to track the P-Coin balance and handle weekly allocations.
- Configuration screens for setting monthly spending limits and protection quotas.
- Selection interfaces for simulated risk profiles.
- An abstract "Risk Arena" for risk simulation.
- A deposit simulation mechanic that includes behavioral pauses and alerts.
- The "Future Vault" interface to visualize protected funds.
- An algorithm to calculate and display the user's "Protection Score".
- A "Life Layer" featuring career progression and mandatory daily expenses like bills.
- A beta countdown timer (e.g., 365 days) and post-session qualitative survey prompts.
- An internal analytics dashboard to measure KPIs.

### User Journey & Modules

- **Onboarding:** Users must receive an initial balance of P-Coins. During onboarding, users are required to set a monthly virtual spending limit and choose a percentage of their budget to allocate to the Future Vault. They must select a simulated risk level (Prudent, Balanced, or Growth) and explicitly accept terms stating the app uses no real money.
- **Deposit Simulation (The Core Interaction):** Whenever a user attempts to transfer P-Coins into the Risk Arena, the app must intercept the transaction. The interface must display the split between the amount being risked and the amount being protected. If the user is approaching their monthly limit or making rapid consecutive deposits, the app must trigger an alert. This alert must present actionable options: confirm the deposit, reduce the amount, take a timed pause (e.g., 10 minutes), review the budget, or navigate to the Future Vault.
- **Future Vault:** This module visualizes the protected portion of the user's budget. It must display simulated annual scenarios tied to the chosen risk profile, showing both positive and negative simulated variations (e.g., a "Prudent" profile shows a +2% or -2% simulated scenario). It must translate virtual capital into tangible goals, such as the number of bills covered or progress toward building an emergency fund.
- **Risk Arena:** This section applies behavioral pressure using abstract probabilistic games. These games should include binary choices, symbolic cards, or random wheels, without mimicking real-world roulette or sports betting.

### Core Mechanics & Systems

- **P-Coin Economy:** P-Coins act as the user's available budget for deposits, daily expenses, and Life Layer purchases. They serve only to create engagement and possess no monetary value.
- **Protection Score Algorithm:** This is the primary success metric of the app, measuring discipline rather than accumulated wealth. The calculation must be transparent and weighted as follows:
    - 30% for respecting set limits.
    - 20% for maintaining the protected quota in the Future Vault.
    - 15% for accepting pauses and alerts.
    - 15% for successfully managing daily expenses.
    - 10% for reducing impulsive behaviors (like chasing losses).
    - 10% for app continuity and completing educational missions.
- **Life Layer Progression:** Users begin at a base career level (e.g., "Intern" earning 1,000 P-Coins/week) and can progress to higher tiers (e.g., "Partner/CEO" earning 4,000 P-Coins/week). Progression is dictated by diligent financial behavior rather than success in the Risk Arena. This layer requires users to spend P-Coins on virtual rent, bills, groceries, and emergencies, forcing them to balance risk with real-life simulated stability.
- **Reward Program:** High Protection Scores grant users priority access to a future Reward Program. Rewards must take the form of limited, non-transferable vouchers for essential goods (e.g., groceries, mobility), strictly excluding gambling, trading, alcohol, or tobacco.

### Features to Strictly Exclude from the MVP

- Integrations with real financial products, bank accounts, real PIPs, or actual ETFs.
- Any mechanisms allowing the conversion of P-Coins into real money or automatic voucher payouts.
- Integrations with real betting operators, sports games, or prediction markets.
- Advanced KYC (Know Your Customer) protocols or real PSP/PISP (Payment Service Provider) integrations.

### System Design and Architecture

- **Quantitative Experiment Foundation:** The beta must be designed from the very beginning as a quantitative experiment.
- **Tracking System:** A dedicated data tracking system must be implemented to allow for subsequent correlation analysis of user behavior.
- **Analytics Dashboard:** The MVP must include the development of an internal analytics dashboard to aggregate, monitor, and visualize these KPIs.

### Qualitative Data Collection

- **In-App Surveys:** Alongside automated quantitative tracking, the app must implement brief post-session surveys to capture the user's psychological state and feedback.
- **User Interviews:** The implementation strategy should also include conducting interviews to gather deeper qualitative evidence for pitch decks and partner discussions.

### Legal and Privacy Guardrails

- **Privacy by Design:** The data collection architecture must be built strictly following "privacy by design" principles.
- **Data Minimization:** The system must practice data minimization, collecting only what is strictly necessary for the behavioral analysis.
- **Total Transparency:** The app must be completely transparent with users during onboarding, clearly stating that the simulator is actively collecting behavioral data.

### 1. Acquisition KPIs

- Total impressions of marketing campaigns.
- The ratio of users who click, view, and exit (click-to-view drop-off rate).
- Click-through rate (CTR).
- Cost per click (CPC).
- Conversion rate from landing page to app download.
- Cost per installation (CPI).
- Conversion rate from installation to user registration.
- Onboarding completion rate.

### 2. Activation KPIs

- Percentage of users who set monthly limits.
- Percentage of users who choose a protection quota.
- The average quota amount that users choose to protect.
- The specific simulated risk profiles chosen by users.
- Completion of the user's first deposit simulation.
- The user's first interaction with the Future Vault.
- The user's first interaction with the Risk Arena.

### 3. Behavioral KPIs

- The average size of a virtual deposit.
- The number of virtual deposits made per session.
- The frequency of rapid, closely spaced deposits.
- User reactions following a simulated loss.
- User reactions following a simulated win.
- Percentage of users who voluntarily reduce their deposit after receiving an alert.
- Percentage of users who accept a behavioral pause.
- Percentage of users who exceed their set limits.
- Percentage of users who actively modify their limits.
- Percentage of users who maintain an active Future Vault.

### 4. Retention KPIs

- Retention rates for Day 1 (D1), Day 7 (D7), Day 14 (D14), and Day 30 (D30).
- Average number of sessions per week.
- Average duration of a session.
- The rate of mission completion.
- Career progression within the Life Layer.
- The stability of the user's Protection Score over time.

### 5. Investor KPIs

- Total number of registered users.
- Weekly active users.
- The number of users maintaining a high Protection Score.
- The percentage of users who explicitly declare interest in a real-money version of the app.
- The percentage of users who would accept an integration with their real bank account.
- The percentage of users who would use ProtegoPay with a real, regulated operator.
- The size of the waitlist for the real application.
- The Customer Acquisition Cost (CAC) for beta users.
- Average user engagement levels.
- Qualitative evidence gathered from brief in-app surveys and user interviews.