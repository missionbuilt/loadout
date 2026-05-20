---
name: the-approach
description: >
  The Approach. A pre-call intelligence brief for sellers and technical sellers.
  Researches a target company before a sales call — incidents, filings, earnings,
  market signal, leadership, tech stack, competitor footprint — and generates a
  structured field brief with business sections for the AE and technical sections
  for the SE, with a scripted opener and ranked demo plan.
  Trigger phrases: "approach", "run the approach", "brief me on", "prep me for",
  "research for my call", "build the approach", "the approach for", "run approach".
license: MIT
author: H. Michael Nichols
version: 0.2.0
part_of: The Loadout
---

# The Approach

## Why "The Approach"

In the gym, the approach to the bar is not incidental — it is deliberate. You
know your opener. You know your second and your third. You have studied the
competition. You walk up to the bar already inside the lift.

The Approach does the same thing before a sales call. Before the deck. Before
the discovery script. Before the awkward first silence. You know who is in the
room, what they have said in public, what has already hit their stack, and what
the three moves are before you dial in.

The brief is divided into two acts: business (for the AE, above the fold) and
technical (for the SE, below). Both halves travel in one document. Both get read
before the call.

---

## INTAKE Mode (Step 0 — run once per call)

**Trigger:** "approach", "run the approach", "brief me on [company]", "prep me
for my call with [company]", "build the approach for [company]", or any phrasing
that names a target company and implies an upcoming meeting.

**If an APPROACH.md config file exists** in the user's workspace folder (same
folder as any existing artifact), read it first. Fields found there do not need
to be asked again — go straight to the missing ones.

**Collect from the user (in order of priority):**

1. **Target company** — name, website if known. Required; do not proceed without it.
2. **Meeting contacts** — who are they meeting? Name and title if known. At minimum the team (e.g. "IT operations", "SOC", "CISO + VP of IT"). Optional but valuable.
3. **Meeting context** — one to two sentences: what is this call about? Who is the seller and what are they selling? Example: "We work at Elastic and are talking to them about agentic security operations."
4. **Meeting date and time** — for the countdown timer and date-anchoring the research.
5. **Seller name** — who is running the call? (AE name, SE name if joint.)

**What NOT to ask:**
- Do not ask about desired format or length — the brief format is fixed.
- Do not ask about research depth — always standard.
- Do not ask about sources — the source suite is fixed.
- Never ask more than two clarifying questions in one turn.

**After collecting the above:** confirm in one short line and move to the Research phase.

---

## RESEARCH Phase (Step 1)

Before starting searches, output this line in chat:
*"🔍 Researching [Target Company] across [N] source categories — give me a few minutes."*

Run all search batches concurrently. Fire all in a single parallel pass.

### Source tiers

| Tier | Code | What it means |
|---|---|---|
| d1 | Official/regulatory | SEC, CISA, regulator sites, company press releases |
| d2 | Company-direct | Company website, official blog, company social |
| d3 | Tier-1 press/analyst | Bloomberg, Reuters, WSJ, TechCrunch, Gartner, trade pubs |
| d4 | Community/social | LinkedIn, X/Twitter, Reddit, YouTube, podcasts |

### Search batch table

Run all batches concurrently. Replace `[TARGET]` with the target company name,
`[DOMAIN]` with their primary domain (infer from name if not given), and
`[DATE]` with the date 90 days prior to today.

| Batch | Query pattern |
|---|---|
| **Company snapshot** | `"[TARGET]" company overview news funding revenue headcount after:[DATE]` |
| **Leadership** | `"[TARGET]" CEO CISO CTO CIO VP OR "chief" after:[DATE]` |
| **Financial** | `"[TARGET]" site:sec.gov OR earnings OR "annual report" OR revenue OR investor after:[DATE]` |
| **Incidents / breaches** | `"[TARGET]" breach OR ransomware OR incident OR "data leak" OR CVE after:[DATE]` |
| **Industry context** | `[sector/industry from meeting context] news trends competitors after:[DATE]` |
| **Social signal** | `"[TARGET]" site:linkedin.com OR site:twitter.com OR site:x.com OR podcast interview after:[DATE]` |
| **Tech stack** | `"[TARGET]" site:linkedin.com jobs OR "job posting" OR "we use" OR "built with" technology OR stack` |
| **Market/analyst** | `"[TARGET]" analyst OR Gartner OR Forrester OR "market position" OR competitor after:[DATE]` |
| **Speaking / press** | `"[TARGET]" site:youtube.com OR conference OR podcast OR keynote OR interview OR speaking after:[DATE]` |

**Per-contact searches (run for each named contact):**

| Batch | Query pattern |
|---|---|
| **Contact LinkedIn** | `"[CONTACT NAME]" "[TARGET]" site:linkedin.com` |
| **Contact posts** | `"[CONTACT NAME]" "[TARGET]" site:linkedin.com OR site:x.com OR podcast after:[DATE]` |
| **Contact press** | `"[CONTACT NAME]" "[TARGET]" interview OR quote OR conference after:[DATE]` |

**Headshot search (best-effort, not blocking):**

Try `"[CONTACT NAME]" "[TARGET]" site:linkedin.com` — if a photo URL is returned, include it. If not, use initials only.

### What to surface for each section

**Company Snapshot:** Founding year, HQ, headcount, revenue (public or estimated), ownership (public/private/PE-backed), key products/services, notable recent news. Look for a single "company in motion" signal — the thing that is *changing* this quarter.

**Leadership & People:** For each named contact — title, background, prior companies, public statements in the last 90 days, LinkedIn URL, any conference talks or podcast appearances. Flag if they are newly hired or newly promoted. Note the buying signal vocabulary they use.

**Financial Posture:** Public: pull SEC filings (10-K, 10-Q, 8-K disclosures including any cyber-incident disclosures), earnings call transcripts, investor notes. Private: triangulate from trade press, Inc 5000, Bloomberg private profile, Glassdoor, funding announcements. Identify recent capex signals, cost-cutting signals, or budget comments.

**Industry Context:** What is happening in the target company's sector this quarter? Competitor incidents or outages. Regulatory changes. Analyst sentiment. Market tailwinds/headwinds. What would a well-read peer of the contact have noticed this week?

**Social Signal:** What has the named contact(s) or the company account posted in the last 30 days? LinkedIn posts, X/Twitter, YouTube, podcast quotes. Surface the most signal-dense quote verbatim. Note engagement levels if available.

**Tech Stack:** Infer from job postings (LinkedIn, company careers page), BuiltWith/Wappalyzer fingerprints, blog posts, conference talks, GitHub orgs. Build a table: layer → tool → integration fit → evidence. Flag any known competitors to the seller's product. Flag any custom-built systems that imply integration work.

**Security Events:** Known breaches, ransomware incidents, CVEs affecting their stack, regulatory actions, SEC 8-K cyber disclosures. Map to MITRE ATT&CK TTPs if a specific incident is documented. Note dwell time and recovery cost if public.

**Demo Prep:** Based on all findings, recommend 2–4 specific demos or product moments ranked by relevance. Each recommendation must tie to a specific finding (e.g., "they had a LockBit 3.0 incident — show the lateral movement detection for that TTP cluster"). Include "run when" and "audible if" footers for each.

**Risk Flags:** Anything that should slow the team down — procurement complexity, timing constraints, stakeholder gaps, known incumbent competitors with deep roots, integration difficulty, compliance requirements.

**Opener & Discovery:** Write a scripted 2-minute opener (not a pitch — a conversation starter based on a specific public signal from the contact). Then write 5–6 ranked discovery questions for the AE and 5–6 for the SE, drawn directly from what the research surfaced.

---

## APPROACH_DATA Schema (v0.1.0)

Build this object during synthesis. Every field below is required unless marked
optional. Write all prose in active voice, present tense, and tight sentences.

```json
{
  "config": {
    "seller": "Mike",
    "sellerCompany": "Elastic",
    "sellerProduct": "Elastic Security",
    "targetCompany": "Acme Financial Group",
    "targetDomain": "acmefinancial.com",
    "targetIndustry": "Financial Services",
    "meetingWith": "Rebecca Torres, CISO · Marcus Webb, VP IT Ops",
    "meetingContext": "Agentic security operations",
    "meetingDate": "Friday, 16 May 2026",
    "meetingTime": "14:30 ET",
    "generatedAt": "09:14 ET",
    "generatedDate": "16 May 2026",
    "sourcesActive": 24,
    "sourcesQuiet": 6,
    "intelItems": 18,
    "riskFlags": 3,
    "peopleFound": 2,
    "totalLinks": 22,
    "fontToolName": "mcp__<uuid>__warmup_get_fonts"
  },

  "scouting": {
    "whoTheyAre": "One or two sentences: company in plain terms.",
    "whatIsChanging": "One or two sentences: what is different THIS quarter.",
    "howWePlayIt": "One sentence: the tactical read. What to lead with."
  },

  "companyFacts": [
    { "k": "Founded", "v": "2006 · Columbus OH" },
    { "k": "Ownership", "v": "Private · founder-led" },
    { "k": "Headcount", "v": "~1,400" },
    { "k": "Revenue", "v": "$700M+ est. · FY24" },
    { "k": "Stack signal", "v": "Shopify Plus · AWS · NetSuite" },
    { "k": "Generated", "v": "09:14 ET · 16 May 2026" }
  ],

  "sections": [
    {
      "id": "snapshot",
      "act": 1,
      "kicker": "Section one",
      "title": "Company snapshot",
      "sub": "What they do, how they make money, and what shape they're in this quarter.",
      "lead": {
        "tier": "d2",
        "src": "acmefinancial.com / About",
        "date": "2026-05-12",
        "tags": [
          { "cls": "t-type", "text": "PROFILE" }
        ],
        "url": "https://example.com",
        "hl": "Lead headline — the single most important fact about this company right now.",
        "deck": "One italic sentence — the 'so what?' of the lead.",
        "body": "Two to three paragraph summary in plain prose. Drop cap on the first letter is automatic.",
        "marginNote": null,
        "callout": "What to do with this: specific, tactical, one to three sentences."
      },
      "items": [
        {
          "tier": "d3",
          "src": "Bloomberg",
          "date": "2026-05-08",
          "tags": [],
          "url": "https://example.com",
          "hl": "Supporting item headline.",
          "body": "Two to three sentence summary."
        }
      ]
    }
  ],

  "people": [
    {
      "name": "Rebecca Torres",
      "title": "CISO",
      "initials": "RT",
      "linkedinUrl": "https://linkedin.com/in/example",
      "photoUrl": null,
      "background": "Ex-JPMorgan (12 yrs). Splunk and CrowdStrike background. Detection fidelity obsessed.",
      "recentSignal": "Publicly said 'my tolerance for SIEM noise is zero' on a podcast in March.",
      "keyQuote": "My tolerance for SIEM noise is zero.",
      "priorStack": "Splunk Enterprise, CrowdStrike",
      "meetingRole": "primary",
      "audienceFor": "both"
    }
  ],

  "stack": [
    {
      "layer": "SIEM",
      "tool": "Splunk Enterprise",
      "fit": "competitor",
      "fitLabel": "COMPETITOR",
      "evidence": "Multiple job postings reference Splunk administration. CISO background is Splunk.",
      "note": "Frame around Splunk's detection gaps, not feature comparison."
    },
    {
      "layer": "EDR",
      "tool": "CrowdStrike",
      "fit": "supported",
      "fitLabel": "INTEGRATED",
      "evidence": "Job postings list CrowdStrike as required skill.",
      "note": null
    }
  ],

  "plays": [
    {
      "num": 1,
      "audience": "ae",
      "priority": "featured",
      "title": "Open on the Dec 2025 dwell period.",
      "cat": "Incident history · Credibility",
      "finding": "The LockBit 3.0 incident had a 19-day dwell period. Their legacy SIEM missed it. That is the reason for this call — everything downstream flows from that failure.",
      "intel": [
        {
          "body": "Name the dwell period first. 'We know 19 days is a long time to not know you have a problem.' Then stop.",
          "src": "internal · call strategy",
          "srcDate": null
        },
        {
          "body": "Do not pitch features. Pitch the answer to the specific failure: lateral movement detection the SIEM didn't surface.",
          "src": "SEC 8-K · Dec 14 2025",
          "srcDate": "2025-12-14"
        }
      ],
      "runWhen": "first 90 seconds, before any product talk",
      "audible": "if Torres opens with Splunk pricing questions, acknowledge and come back to this",
      "handNote": "★ this is the call"
    }
  ],

  "opener": {
    "lines": [
      { "type": "quote", "text": "Rebecca — thanks for making time. Before we get into anything else, I want to ask about December." },
      { "type": "beat", "text": "Beat. Let her respond." },
      { "type": "quote", "text": "Nineteen days is a long time to not know you have a problem. That's what we're here to talk about — what would have caught it, and how quickly." },
      { "type": "beat", "text": "Beat. Hand it to her." }
    ],
    "stageDirection": "Do not open the deck for at least 8 minutes after this. Earn the deck.",
    "handNote": "— briefed by The Approach, 09:14 ET"
  },

  "discovery": {
    "business": [
      "What does success look like for you in the next 90 days — not the project, the feeling?",
      "Who else needs to bless a security tooling change at this point in your tenure?",
      "Where is the budget for security infrastructure living — your line, a shared one, or post-incident capital?",
      "How long is your decision cycle for something in this price band?",
      "What does the board want to hear after December — and have you had that conversation yet?"
    ],
    "technical": [
      "What was the detection coverage gap that allowed the 19-day dwell — do you have a postmortem?",
      "What is your current SIEM data retention and ingestion cap, and are you bumping against it?",
      "How is your CrowdStrike telemetry flowing into the SIEM today — is there a connector, or manual export?",
      "Who owns detection rule tuning, and how often does the team touch them?",
      "What does your alert-to-incident workflow look like — where does the human get involved?",
      "What integrations exist between your IR platform and your ticketing system?"
    ]
  },

  "risks": [
    {
      "level": "red",
      "type": "contract",
      "title": "New CISO on day one of tenure.",
      "body": "Torres starts June 1. She will not sign a contract before she has had her first all-hands. Do not push for a fast close — you will lose trust. Run a discovery-heavy call one, earn call two."
    },
    {
      "level": "amber",
      "type": "competitor",
      "title": "Splunk incumbent. Deep roots.",
      "body": "The team knows Splunk. The CISO came from a Splunk shop. Do not position against Splunk by name — position around the detection failure that Splunk missed."
    }
  ],

  "sources": [
    { "nm": "SEC EDGAR", "tier": "d1", "ct": "3 items", "status": "active" },
    { "nm": "CISA KEV", "tier": "d1", "ct": "2 items", "status": "active" },
    { "nm": "acmefinancial.com", "tier": "d2", "ct": "4 items", "status": "active" },
    { "nm": "LinkedIn · Rebecca Torres", "tier": "d4", "ct": "7 items", "status": "active" },
    { "nm": "Bloomberg", "tier": "d3", "ct": "1 item", "status": "active" },
    { "nm": "BleepingComputer", "tier": "d3", "ct": "2 items", "status": "active" },
    { "nm": "Reddit · r/netsec", "tier": "d4", "ct": "—", "status": "quiet" }
  ],

  "safety": {
    "total": 22,
    "clean": 22,
    "flagged": 0,
    "scannedAt": "09:14 ET"
  }
}
```

---

## RENDER Phase (Step 2)

Every Approach brief is built fresh from `approach_get_template`. There is no Path A / Path B and no engine version check — one path, every time.

```
a) Identify your loaded warmup_get_fonts tool name. It looks like:
      "mcp__<uuid>__warmup_get_fonts"
   The UUID prefix changes per session — use the exact name from your loaded tool list.

b) Ensure config.fontToolName is set in APPROACH_DATA:
      "config": {
        "fontToolName": "mcp__<uuid>__warmup_get_fonts",
        ... (all other config fields)
      }

c) Call approach_get_template({ approach_data: JSON.stringify(APPROACH_DATA) }).
   The server injects the data, escapes </script> sequences, and returns the
   complete filled HTML (~150KB). Do not double-escape — the server handles it.

d) Write the returned HTML to [workspace_root]/approach-brief.html using the
   Write file tool. Write it exactly as returned — do not edit the content.

e) Call create_artifact (or update_artifact if re-running for the same company):
      id: "the-approach"
      html_path: [path to approach-brief.html]
      mcp_tools: ["mcp__<uuid>__warmup_get_fonts"]
   Without mcp_tools, Cowork blocks the font call and the brief renders in fallback fonts.
```

---

## Summary line

After rendering, output one summary line in chat:

*"[N] intel items · [N] people profiled · [N] plays · [N] risk flags · [N] sources active"*

Then one sentence: the single most important thing the team should know walking into this call.

Nothing else in chat. The brief is the artifact. Do not duplicate its content in chat.

---

## Editorial rules

- Every lead item must have a specific, named fact — no generic observations.
- Every "what to do with this" callout must be action-specific to THIS company and THIS contact.
- Every play must tie to a specific research finding — not a generic best practice.
- The opener script must quote an actual statement or public signal — not an invented conversation.
- If a contact has a headshot URL, include it. If not, use initials only — do not fabricate images.
- LinkedIn URLs: include only if found in search results. Do not construct them from name + company.
- SEC filings, 8-Ks, earnings transcripts: always quote the specific document and date.
- Source tier dots: use the correct tier code (d1–d4) for every item.
- The opener script is written for the AE. Flag the SE handoff point explicitly.
- Risk flags must be RED or AMBER only. Never GREEN.
- Never invent financial figures. State confidence level if triangulated.

---

## APPROACH.md config format


If a file named `APPROACH.md` exists in the user's workspace folder, read it
before intake and skip any fields already defined there.

```markdown
# The Approach · Config

seller: Mike Rapaport
seller_company: Sightline
seller_product: Sightline Observability
timezone: ET
default_se: Sarah Lim
```

After a successful run, offer to save or update the seller config:
*"Say 'save approach config' to write your seller info to APPROACH.md so you
don't have to re-enter it next time."*

---

## Version history

| Version | Change |
|---|---|
| 0.1.0 | Initial release — V1 cream paper design + V2 Scout Sheet quirks. Joint AE+SE brief. |
| 0.1.1 | RENDER Phase rewrite — explicit Path A/B split. Ban approach_get_template on repeat runs. |
| 0.1.2 | Path B rewrite — Read/Write file tools instead of approach_get_template for first run. |
| 0.1.3 | approach_run now loads per-section via approach_get_skill. Render boundary includes Summary line. |
| 0.1.4 | Remote shell architecture. Path B writes a 14-line skeleton; CSS and renderer load from mcp.missionbuilt.io/approach-shell.js. Zero template-read tokens on first run. |
| 0.1.5 | MCP font loader replaces Google Fonts CDN (blocked by Cowork CSP). Add config.fontToolName to APPROACH_DATA schema. Pass mcp_tools on create_artifact. XSS escaping fixes: buildSecNav nav link text, colophon date fields. |
| 0.2.0 | Inline template architecture. approach_get_template now returns complete filled HTML — no remote shell, no Path A/B. Single-path render: call approach_get_template → write HTML → create_artifact. Font loader baked into template. Schema fixes: act field is number (2=SE), plays.num is number not string. |
