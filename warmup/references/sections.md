# The Warmup — Report Section Structures

Loaded on demand: read this file when building section content for the brief.

## CISO Report — Section Structure

Organize the brief into these five sections, in this order.
Each section has a defined scope. Stay within it.

### Section 1 — THREAT LANDSCAPE

**What belongs here:** Named threat actors currently active; their targeted
sectors; their primary TTPs.

- Use CrowdStrike naming convention for threat groups where possible
  (SCATTERED SPIDER, COZY BEAR, VOLT TYPHOON, etc.). Note aliases when
  relevant (e.g., "APT29 / COZY BEAR").
- Tag each item with the actor name, 1–2 MITRE ATT&CK technique IDs
  (e.g., T1566.001 — Spearphishing Attachment), and source.
- If the user provided a sector, lead with actors known to target that
  sector. If no sector-specific activity exists this week, say so briefly
  rather than forcing items that do not fit.
- If the user provided a company name, note explicitly if the company
  or its sector has appeared in attribution reporting.

**Scope boundary:** Attribution and TTPs only. Do not put CVEs here —
those go in Emerging Threats. Do not put vendor news here — that goes
in Industry Intel.

### Section 2 — EMERGING THREATS

**What belongs here:** New vulnerabilities and attack techniques entering
circulation in the last 7 days.

- CISA KEV additions: any CVE added to the Known Exploited Vulnerabilities
  catalog this week.
- High/critical CVEs with active exploitation evidence or public POC.
- Zero-day disclosures. New malware families or significant variants.
- Each CVE entry: CVE ID, CVSS score, affected product(s), exploitation
  status (exploited in wild / POC available / no exploitation evidence).
- Sort by exploitation urgency, not CVSS score alone. A CVSS 7.5 with
  confirmed in-the-wild exploitation ranks above a CVSS 9.8 with no POC.

**Scope boundary:** Technical vulnerabilities and new attack techniques only.

### Section 3 — RESEARCH DIGEST

**What belongs here:** New publications from Tier 1 and Tier 2 sources
in the last 7 days.

- New threat research reports, technical blog posts, malware analyses.
- One headline + 2–3 sentence summary per item.
- Tag with source name and publication date.
- Exclude vendor marketing content. Only substantive research with
  named threat data, indicators, or detection guidance qualifies.

**Scope boundary:** Research publications only, not breaking news.
If something is both news and research (e.g., a major IR firm publishes
on an ongoing incident), put it here and note the news angle.

### Section 4 — INDUSTRY INTEL

**What belongs here:** Market and vendor movement a CISO cares about for
budget and vendor portfolio decisions.

- M&A activity: acquisitions, mergers, divestitures in the security market.
- Significant product launches from vendors the user tracks.
- Leadership changes at major security vendors.
- Regulatory changes: SEC disclosure rules, GDPR/HIPAA/DORA enforcement
  actions, CMMC updates, state-level privacy laws.
- Tag each item: [M&A], [PRODUCT], [REGULATORY], or [EXEC].
- If any news directly affects a vendor the user listed in their profile,
  note that explicitly.

**Scope boundary:** Market and regulatory movement. Not technical threat data.

### Section 5 — SOCIAL SIGNAL

**What belongs here:** High-signal community discussion from the security
field. This section is optional and should be omitted if nothing substantive
is found.

- High-engagement threads or posts on r/netsec, LinkedIn security community,
  or X/Twitter security accounts that discuss something of professional
  consequence (a significant debate, a disclosed incident, a tool release
  that is getting traction).
- Every item in this section must carry a [COMMUNITY] tag.
- Add this note at the top of the section:
  *"Unverified community signal. Cross-reference Tier 1–2 sources before acting."*
- If nothing of consequence is found: **omit the section entirely.**
  Do not pad with low-signal posts to fill the section. Absence is better
  than noise.

---

---

## Product Leader Report — Section Structure

Eight sections, in this order. Section 7 (Vertical Intel) is dynamic — its
name and scope adapt to the user's declared vertical. Section 8 (Special
Interests) is optional and omitted if not configured.

### Section 1 — COMPANY INTEL

**What belongs here:** Your own company's external signal — what the market,
analysts, customers, and press are saying about you.

- Analyst coverage: Gartner, Forrester, IDC mentions; category placement changes
- Customer review movement: G2, Capterra, Trustpilot score shifts, notable reviews,
  category ranking changes
- Press coverage of the company: product launches, leadership moves, partnerships
- Job posting signals: significant new role categories that suggest strategic direction
  (e.g., suddenly posting 20 ML roles signals an AI pivot)
- Earnings/analyst day commentary for public companies
- Tag each item: [ANALYST], [REVIEW], [PRESS], [HIRING], [EXEC]

**Scope boundary:** Only your own company. Competitor company signal goes in
Section 2. Industry news goes in Section 7.

### Section 2 — COMPETITOR INTEL

**What belongs here:** Strategic moves from the competitor list in WARMUP.md.

- Product launches and feature announcements — what they shipped
- Pricing changes — especially if moving toward or away from your segment
- Funding rounds, M&A activity, acqui-hires
- Executive hires and departures (CTO/CPO/CEO changes are significant)
- Customer wins or losses where named (case studies, press releases, reviews)
- Any public roadmap signals (conference talks, job posts for new product areas)
- Tag each item with the competitor name and: [PRODUCT], [FUNDING], [M&A], [EXEC],
  [PRICING], or [CUSTOMER]
- If a competitor ships something that directly threatens your roadmap, bold the
  item and put it first in the section.

**Scope boundary:** Named competitors only. New entrants or emerging threats
go in Section 7 (Vertical Intel). Do not include your own company here.

### Section 3 — AI IN PRODUCT

**What belongs here:** Two tracks in one section.

**Track A — Frontier model and AI vendor moves:**
- New model releases and benchmark results (GPT, Claude, Gemini, Llama, Mistral, etc.)
- API changes, deprecations, pricing shifts from major AI vendors
- New capabilities that change what products can realistically build
- Acquisitions or partnerships that shift the AI vendor landscape
- Tag: [MODEL RELEASE], [API], [PRICING], [ACQUISITION]

**Track B — AI in product development:**
- New coding tools, agent frameworks, or dev-workflow AI (Cursor, Copilot, Devin, etc.)
- Research pre-prints from arXiv cs.AI with near-term product implications
- Notable real-world deployments of AI in products similar to the user's
- Practitioner write-ups: how teams are actually shipping AI features
- Tag: [TOOLING], [RESEARCH], [DEPLOYMENT], [FRAMEWORK]

**Ordering:** Put Track A items first (they move the floor). Track B items follow.

**Scope boundary:** AI capabilities, vendors, and tooling only. Do not put general
tech news here. Do not duplicate competitor AI launches — those go in Section 2.

### Section 4 — FUNDING & M&A

**What belongs here:** Capital and consolidation moves in the user's market.

- Funding rounds in the user's category or adjacent ones: Series A+, growth rounds,
  late-stage. Note the lead investor — signals where smart money is pointing.
- Acquisitions: who bought whom, implied valuation, strategic rationale
- IPOs and SPACs in the sector
- Notable shutdowns or acqui-hires that signal market consolidation
- If a direct competitor raised or got acquired, this item belongs in Section 2,
  not here — cross-reference rather than duplicate.
- Tag: [FUNDING], [M&A], [IPO], [SHUTDOWN]

**Scope boundary:** Capital events only. Not product launches, not general news.

### Section 5 — PLATFORM & ECOSYSTEM RISK

**What belongs here:** Changes to the platforms, APIs, and infrastructure your
product depends on or competes within.

- App store policy changes (Apple, Google Play) — pricing, review policies, categories
- Major API changes, deprecations, or pricing shifts from platform dependencies
  (Stripe, Twilio, AWS, Salesforce, Shopify, etc.)
- Browser or OS changes with product implications (Safari privacy changes, Chrome
  deprecations, new mobile OS features)
- Cloud provider moves: new services, pricing changes, regional expansions that affect
  build-vs-buy decisions
- Developer platform news: GitHub, npm, open-source ecosystem shifts
- Tag: [APP STORE], [API CHANGE], [DEPRECATION], [PLATFORM], [CLOUD]

**Scope boundary:** Changes external to your product that affect what you can build
or how your product reaches users. If it doesn't create platform risk or dependency
change, it belongs elsewhere.

### Section 6 — REGULATORY & POLICY

**What belongs here:** Policy and regulatory movement that could change your product,
market, or go-to-market.

- Privacy regulation: GDPR enforcement actions, US state privacy laws (CCPA, etc.),
  new proposals in the user's markets
- EU AI Act milestones and compliance deadlines
- Antitrust: actions against platforms the user builds on or competes with
- Vertical-specific regulatory moves (appended from Vertical Intel sources)
- FTC, DOJ, SEC enforcement actions relevant to the user's sector
- Tag: [GDPR], [AI ACT], [ANTITRUST], [FTC], [PRIVACY], or the relevant jurisdiction

**Scope boundary:** Policy and compliance only. Not market news, not product news.
If a regulatory action has direct competitive implications, note it here and
reference Section 2.

### Section 7 — [VERTICAL INTEL] *(dynamic section name)*

**What belongs here:** Market-specific intelligence that depends on what the user
builds and who they build for. This section's name, sources, and scope are set
at SETUP based on the user's declared vertical.

**Vertical mapping — use the appropriate label and scope:**

| Vertical | Section label | What belongs here |
|---|---|---|
| Security product | THREAT LANDSCAPE | Borrow CISO Sections 1–2 scope: active threat actors, CVEs, research publications relevant to the user's customer base |
| Fintech / payments | FINANCIAL ECOSYSTEM | Banking regulation, payment network moves, fraud trend reports, central bank policy with product implications |
| Healthcare / digital health | CLINICAL & REGULATORY | FDA digital health guidance, CMS reimbursement signals, EHR ecosystem moves, health data standards |
| Consumer social / creator | PLATFORM & CREATOR ECONOMY | Platform API changes (Instagram, TikTok, YouTube), creator monetization updates, engagement trend data |
| Enterprise SaaS | BUYER SIGNAL | CIO/CFO sentiment surveys, procurement trend reports, SaaS spend benchmarks, category-level churn data |
| Developer tools / platform | ECOSYSTEM SIGNAL | GitHub trending, open-source project momentum, Stack Overflow data, developer community sentiment |
| E-commerce / retail | COMMERCE SIGNAL | Consumer spending indexes, Shopify GMV data, platform policy changes, fulfillment and logistics signals |
| Logistics / supply chain | SUPPLY CHAIN SIGNAL | Freight rate indexes, port congestion data, geopolitical disruption signals, carrier capacity data |
| Marketplace | MARKETPLACE DYNAMICS | GMV and take-rate trends, regulatory risk to marketplace models, supply/demand liquidity signals |

If the user's vertical doesn't match the table, use the SETUP Question 3 inference
(the "bad week" question) to name and define this section appropriately.

**Scope boundary:** Vertical Intel is for market forces specific to the user's industry.
General tech news and competitor moves go in earlier sections.

### Section 8 — SPECIAL INTERESTS *(optional)*

Identical to the CISO mode Special Interests section. Render only if
`special_interests` is set in WARMUP.md. Pull 1–3 conversational items per
interest, label [INTERESTS], and position last.

---

## Product Leader Report — Batch Query Table

Run these batches concurrently during the fetch phase. Replace placeholders with
values from WARMUP.md. Run all batches before synthesizing.

| Batch | Sources covered | Query pattern |
|---|---|---|
| Company signal | Company newsroom + G2 + Gartner + press | `"[company]" announcement OR review OR analyst after:YYYY-MM-DD` |
| Competitor sweep | All competitors from `competitors:` list | `([comp1] OR [comp2] OR [comp3]) launch OR funding OR acquisition OR pricing after:YYYY-MM-DD` |
| AI frontier | OpenAI + Anthropic + Google + Meta + Mistral | `(site:openai.com OR site:anthropic.com OR site:deepmind.google OR site:ai.meta.com OR site:mistral.ai) after:YYYY-MM-DD` |
| AI in product | arXiv + Hugging Face + practitioner blogs | `AI product development OR agent framework OR LLM tooling after:YYYY-MM-DD` |
| Funding & M&A | Crunchbase + TechCrunch + SEC EDGAR | `[sector] funding OR acquisition OR IPO site:techcrunch.com OR site:crunchbase.com after:YYYY-MM-DD` |
| Platform risk | App stores + major API providers + cloud | `[platform dependencies] API change OR deprecation OR policy after:YYYY-MM-DD` |
| Regulatory | FTC + sector regulator + EU | `[sector OR company] regulatory OR compliance OR enforcement after:YYYY-MM-DD` |
| Vertical intel | Vertical-specific sources from the table above | Query pattern matched to vertical (e.g., `site:hhs.gov digital health` for healthcare) |
| Interests | One per special interest | Targeted query per interest |

Adapt all queries to the user's company, sector, and competitor list from WARMUP.md.
If a competitor list has more than five names, run two competitor sweep batches rather
than cramming all into one query (search engines truncate long OR chains).

**URL safety gate:** identical to RUN Step 2 — no exceptions. Every URL from every batch passes the same allowlist → URLScan.io check. Configured `competitors:` and `ai_vendors:` domains are pre-allowlisted. Anything that cannot be confirmed clean is excluded.

---

