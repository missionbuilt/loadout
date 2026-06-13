# The Warmup — Source Suites

Loaded on demand: read this file when running Product Leader mode, Custom mode, or when sector-specific sources are needed.

## CISO Source Suite

The default source suite for CISO mode. Load all of these unless the user
explicitly excludes one.

### Tier 1 — Government & Authoritative

These are primary sources of truth. Treat their content as high-confidence.
Never remove from the brief without user confirmation.

| Source | Search target | What it contributes |
|---|---|---|
| CISA Alerts & Advisories | site:cisa.gov advisories | Active exploits, critical advisories, joint alerts with NSA/FBI |
| CISA Known Exploited Vulnerabilities (KEV) | site:cisa.gov known-exploited-vulnerabilities | CVEs with confirmed in-the-wild exploitation |
| NVD / CVE Database | site:nvd.nist.gov OR "CVE-2026" new vulnerability | New and updated CVE records, CVSS scores |
| MITRE ATT&CK | site:attack.mitre.org | TTP context for attributed campaigns; use for tagging items from other sources |
| FBI Cyber Division | site:ic3.gov OR site:fbi.gov/investigate/cyber | Public PSAs, threat actor attributions, financial fraud patterns |
| NSA Cybersecurity Advisories | site:nsa.gov cybersecurity advisory | Nation-state TTP guidance, hardening recommendations |

### Tier 2 — Premier Research Firms

High-quality, vetted research with named analysts and editorial review.
Include all by default.

| Source | Search target | What it contributes |
|---|---|---|
| CrowdStrike Intelligence Blog | site:crowdstrike.com/blog | Adversary tracking (BEAR/SPIDER/KITTEN taxonomy), campaign analysis |
| Palo Alto Unit 42 | site:unit42.paloaltonetworks.com | Threat research, malware reverse engineering, IR findings |
| Red Canary | site:redcanary.com/blog | Behavioral detection research, open-source detection rules |
| Google Mandiant | "mandiant" threat intelligence blog | APT group tracking, IR case studies, zero-day attribution |
| Microsoft Threat Intelligence (MSTIC) | site:microsoft.com/security/blog | Windows/Azure/cloud threat actor TTPs, nation-state activity |
| Cisco Talos | site:blog.talosintelligence.com | Threat telemetry, malware family analysis, email threat data |
| Secureworks CTU | site:secureworks.com/blog | GOLD/IRON/BRONZE group tracking, ransomware intelligence |
| Recorded Future | site:recordedfuture.com/blog | Dark web intelligence, global threat signals, public research |

### Tier 3 — Reputable Security News

Reliable reporting with editorial standards. Label items [NEWS].
Include all by default.

| Source | Search target | What it contributes |
|---|---|---|
| Krebs on Security | site:krebsonsecurity.com | Investigative security reporting, breach coverage |
| The Hacker News | site:thehackernews.com | Breaking security news, vulnerability coverage |
| Dark Reading | site:darkreading.com | CISO-relevant analysis, industry reporting |
| SecurityWeek | site:securityweek.com | Vendor news, vulnerability roundups |
| BleepingComputer | site:bleepingcomputer.com | Ransomware tracking, active exploit news |
| Ars Technica Security | site:arstechnica.com/security | Technical security reporting, long-form analysis |

### Tier 4 — Vendor & Market Intelligence

For tracking M&A, funding, product launches, regulatory moves. Label items
[VENDOR] or [REGULATORY]. Read with commercial interest context.

| Source | Search target | What it contributes |
|---|---|---|
| CRN | site:crn.com security | Channel news, vendor M&A, partner moves |
| SC Magazine | site:scmagazine.com | Security product news, market coverage |
| TechCrunch Security | site:techcrunch.com/category/security | Startup funding, cybersecurity acquisitions |
| Cybersecurity Ventures | site:cybersecurityventures.com | Market reports, spending forecasts |

---

---

## Product Leader Source Suite

Default source suite for Product Leader mode. Core sources load for all users; vertical-specific sources added at SETUP.

### Tier 1 — Primary Sources

| Source | Search target | What it contributes |
|---|---|---|
| SEC EDGAR | `site:sec.gov [company] OR [competitor]` | Public filings, 8-K events, earnings, exec changes |
| Crunchbase News | `site:crunchbase.com [sector] funding OR acquisition` | Funding rounds, M&A, investor signals |
| Company newsroom | `site:[company].com/news OR /press` | Official announcements, product launches, leadership moves |
| Competitor newsrooms | `site:[competitor].com/news OR /press` | Official competitor announcements |

### Tier 2 — Research & Premium Coverage

| Source | Search target | What it contributes |
|---|---|---|
| a16z | `site:a16z.com [sector] OR [vertical]` | Market theses, sector deep-dives, portfolio signals |
| Sequoia Capital | `site:sequoiacap.com [sector]` | Market memos, economic outlook, founder research |
| The Information | `site:theinformation.com [company] OR [sector]` | Investigative tech journalism (search for public excerpts) |
| Stratechery | `site:stratechery.com [company] OR [sector]` | Strategic analysis of tech business models |
| Benedict Evans | `site:ben-evans.com [sector] OR [topic]` | Consumer tech and market structure analysis |
| CB Insights | `site:cbinsights.com [sector] intelligence` | Market maps, funding data, industry reports |
| Gartner | `site:gartner.com [sector] magic quadrant OR report` | Analyst positioning, market category definitions |
| Forrester | `site:forrester.com [sector] wave OR report` | Enterprise buyer-focused analyst coverage |
| Product Hunt | `site:producthunt.com [category]` | New product launches, early competitor signal |

### Tier 3 — News & Community

Label items [NEWS] or [COMMUNITY].

| Source | Search target | What it contributes |
|---|---|---|
| TechCrunch | `site:techcrunch.com [company] OR [sector]` | Funding news, product launches, startup coverage |
| The Verge | `site:theverge.com [company] OR [product category]` | Consumer tech, platform policy, product reviews |
| Wired | `site:wired.com [company] OR [sector]` | Long-form technology and business reporting |
| Fast Company | `site:fastcompany.com [company] OR innovation` | Innovation, design, product culture |
| Reuters / Bloomberg | `site:reuters.com OR site:bloomberg.com [company] OR [sector]` | Breaking M&A (Tier 1); market color (Tier 3) |
| Lenny's Newsletter | `site:lennysnewsletter.com [topic]` | Practitioner PM and growth content |
| Reforge Blog | `site:reforge.com/blog [topic]` | Product growth and retention frameworks |
| Hacker News | `site:news.ycombinator.com [company] OR [product]` | Developer community signal; earliest mention of product issues |
| LinkedIn | `[person] OR [company] site:linkedin.com` | Exec commentary, people moves, product announcements |

### Tier 4 — Vendor & Analyst Marketing

| Source | Search target | What it contributes |
|---|---|---|
| G2 | `site:g2.com [company] OR [competitor] reviews` | Customer review signal, competitive grids |
| Capterra | `site:capterra.com [company] OR [competitor]` | B2B buyer reviews, alternative discovery |
| Trustpilot | `site:trustpilot.com [company] OR [competitor]` | Consumer review signal |
| Vendor blogs | `site:[vendor].com/blog [product area]` | AI vendor product updates, API changes |

### AI Vendor Sources (always included for Product Leader)

| Source | Search target | What it contributes |
|---|---|---|
| OpenAI Blog | `site:openai.com/blog` | Model releases, API changes, pricing |
| Anthropic | `site:anthropic.com/news OR /research` | Model releases, safety research, API updates |
| Google DeepMind | `site:deepmind.google OR site:blog.google/technology/ai` | Research, Gemini updates, infrastructure |
| Meta AI | `site:ai.meta.com/blog OR site:research.facebook.com` | Open-source models (Llama), research |
| Mistral AI | `site:mistral.ai/news` | European frontier model moves, open-weight releases |
| Hugging Face | `site:huggingface.co/blog` | Open-source model ecosystem, tooling |
| arXiv cs.AI | `site:arxiv.org cs.AI [topic]` | Pre-print research; leading indicator of capability direction |

Additional AI vendor sources from `ai_vendors:` in WARMUP.md appended at runtime.

### Vertical-Specific Sources (Product Leader)

| Vertical | Add These Sources |
|---|---|
| **Security product** | Full CISO Tier 1–2 suite (CISA, NVD, CrowdStrike, Unit 42, MSTIC, Red Canary, etc.) |
| **Fintech / payments** | OCC (`site:occ.gov`), CFPB (`site:consumerfinance.gov`), FS-ISAC, Payments Dive, PYMNTS |
| **Healthcare / digital health** | FDA Digital Health, CMS (`site:cms.gov`), Rock Health, HIMSS |
| **Consumer social / creator** | Social Media Today, Creator Economy Report, platform dev blogs (Meta, TikTok, YouTube, Snap) |
| **Enterprise SaaS** | Bessemer State of Cloud, SaaStr, ChartMogul blog, Lighter Capital |
| **Developer tools / platform** | GitHub Blog, Stack Overflow Developer Survey, npm trends, CNCF reports, Changelog |
| **E-commerce / retail** | Digital Commerce 360, Shopify Engineering Blog, NRF research, Morning Brew Retail |
| **Logistics / supply chain** | FreightWaves, Supply Chain Dive, Flexport blog |
| **Marketplace** | a16z marketplace posts, NFX (`site:nfx.com`), a16z marketplace essays |

## Sector-Specific Sources

Append these when the user's sector matches. Add to the appropriate tier in
the source suite.

| Sector | Add These Sources |
|---|---|
| Healthcare | HHS HC3 (`site:hhs.gov hc3`), Health-ISAC news (`site:h-isac.org`), AHA cybersecurity alerts |
| Financial Services | FS-ISAC public blog (`site:fsisac.com`), OCC alerts (`site:occ.gov`), FFIEC guidance |
| Energy / Utilities | E-ISAC (`site:eisac.com`), CISA ICS-CERT (`site:cisa.gov ics-cert`), NERC CIP updates |
| Government / Public Sector | FedRAMP news, FISMA updates, DoD CMMC bulletins (`site:dodcio.defense.gov`) |
| Technology | GitHub Security Advisories (`site:github.com/advisories`), Wiz Research (`site:wiz.io/blog`), Snyk Vulnerability DB |
| Retail / Consumer | PCI Security Council (`site:pcisecuritystandards.org`), NRF security news |
| Manufacturing / OT | Dragos OT Intel (`site:dragos.com/blog`), Claroty Research (`site:claroty.com/team82`), Nozomi Research |
| Critical Infrastructure | Extends Energy + Government sources; add ICS-CERT advisories explicitly |

---

