---
name: cva-domain-rules
description: Capital One product catalog taxonomy, review platforms, team routing rules, and strict compliance boundaries (Evidence vs. Hypothesis separation, personal project independence).
---

# Customer Voice AI — Domain Taxonomy & Compliance Rules

This skill governs all domain classifications, product taxonomies, team routing rules, and compliance boundaries. Activate this skill whenever classifying reviews, writing LLM prompts, generating synthetic data, or designing routing logic.

## 1. Non-Negotiable Compliance Boundaries

### Personal Project Independence Rule
* **100% Independent:** This platform is an educational and portfolio project developed strictly outside any employment context.
* **No Internal Systems:** Never connect to, query, or reference internal enterprise networks, corporate VPNs, private repositories, internal Slack workspaces, Jira instances, or proprietary databases.
* **No Confidential Data:** Never introduce non-public data, employee names, internal architecture terms, proprietary schemas, or customer Personally Identifiable Information (PII).
* **Public & Synthetic Only:** Data sources are strictly limited to publicly available review pages (Apple App Store, Google Play Store, Google Places, Yelp) and calibrated synthetic data.

### Responsible AI Guardrail: Evidence vs. Hypothesis Separation
When generating AI analyses, summaries, recommendations, and executive reports:
* **Observed Evidence ("What customers report"):** Must be grounded directly in explicit customer quotes, ratings, and observed frequency metrics.
  * *Example:* "42 customers reported the mobile app crashed immediately following the v6.14 Face ID login prompt."
* **Investigation Hypothesis ("What may explain the issue"):** Plausible technical, architectural, or operational reasons that engineering teams should investigate.
  * *Example:* "Hypothesis: Possible nil unwrapping or unhandled exception in biometric authentication callback on iOS 18.1."
* **Rule:** Hypotheses must **NEVER** be asserted as confirmed facts or proven root causes. They must always be framed as suggested areas of investigation.

## 2. Capital One Product Catalog (19 Canonical Products)

### Credit Cards
* `venture_x`: Venture X Premium Travel Rewards Card
* `venture`: Venture Rewards Card
* `savor_one`: SavorOne Dining & Entertainment Rewards
* `quicksilver`: Quicksilver Cash Rewards Card
* `platinum`: Platinum Credit Card (Building Credit)
* `spark_cash_plus`: Spark Cash Plus Business Card

### 360 Consumer Banking
* `banking_360_checking`: 360 Checking (Fee-free checking)
* `banking_360_savings`: 360 Performance Savings (High-yield savings)
* `banking_360_cd`: 360 Certificate of Deposit
* `money_teen_checking`: MONEY Teen Checking Account

### Auto Financing
* `auto_navigator`: Auto Navigator Pre-qualification & Car Search
* `auto_refinance`: Auto Loan Refinancing

### Digital, Shopping & AI Platforms
* `c1_mobile_ios`: Capital One Mobile Banking App (Apple iOS)
* `c1_mobile_android`: Capital One Mobile Banking App (Google Android)
* `c1_shopping_extension`: Capital One Shopping Browser Extension
* `eno_virtual_assistant`: Eno Intelligent Virtual Assistant & Virtual Card Numbers
* `creditwise`: CreditWise Free Credit Monitoring

### Cafés & Physical Channels
* `c1_cafe`: Capital One Café Locations (Coffee, workspaces, ambassadors)
* `c1_branch_network`: Capital One Retail Branch & ATM Network

## 3. Review Source Platforms (5 Channels)

* `apple_app_store`: Apple App Store (iOS Mobile reviews)
* `google_play_store`: Google Play Store (Android Mobile reviews)
* `chrome_web_store`: Chrome Web Store (Shopping Extension reviews)
* `google_places`: Google Maps / Places (Café & Branch reviews)
* `trustpilot`: Trustpilot Consumer Reviews (Credit Card & Banking services)

## 4. Generic Enterprise Teams & Routing Rules

Issues and recommendations must be routed to one of seven generic business teams:

1. **Digital Engineering — Mobile (`digital_eng_mobile`):**
   * *Categories:* Mobile App, Authentication, Biometrics, UI/UX, Performance
2. **Payments & Core Banking Operations (`payments_ops`):**
   * *Categories:* Overdraft Fees, Wire Transfers, Direct Deposit, Account Funding
3. **Travel & Lounges Product (`travel_lounges_prod`):**
   * *Categories:* Venture X Perks, Lounge Access, Travel Portal Booking, Partner Miles Transfer
4. **Café Operations & Retail Experience (`cafe_ops`):**
   * *Categories:* Café Facilities, Ambassador Service, Coffee Discount, Wi-Fi Connectivity
5. **Digital AI & Security Engineering (`digital_ai_security`):**
   * *Categories:* Eno Virtual Cards, Fraud Alerts, Identity Verification, CreditWise
6. **Shopping Engineering (`shopping_eng`):**
   * *Categories:* Browser Extension, Coupon Codes, Extension Performance, Cashback Tracking
7. **Customer Experience & Loyalty (`customer_exp`):**
   * *Categories:* Customer Support Wait Times, General Policy, Escalations

### 4.1 Automated Routing & Governance Protocol

1. **Autonomous Routing by Default**:
   - Every cluster formed by the streaming pipeline is automatically evaluated by the `RoutingService`.
   - The engine scores keyword/regex matches across cluster titles, affected products, and customer quotes against priority-ranked database rules (`TeamRoutingRule`).
   - Velocity anomaly z-scores and week-over-week spike percentages automatically determine the Priority level (`P1_CRITICAL` through `P4_LOW`) and resolution SLA (24h to 168h).
   - The engine automatically attaches team-specific remediation playbooks (5 diagnostic steps) and public review response templates.
   - Any cluster without a specific pattern match defaults to `customer_exp` (Customer Experience & Loyalty).

2. **Manual Intervention (HITL Governance Only)**:
   - Operators and engineers do **NOT** need to manually route clusters or reviews.
   - Manual interaction is reserved exclusively for the **Human-in-the-Loop (HITL) Review Stage**: a Product Manager or Team Lead reviews proposed recommendations in `pending_review` status and can:
     - **Approve**: Confirms the automated routing and proposed action.
     - **Re-route / Override**: Changes the assigned team if cross-functional nuance requires a different owner.
     - **Reject / Clarify**: Returns the recommendation with reviewer notes.
