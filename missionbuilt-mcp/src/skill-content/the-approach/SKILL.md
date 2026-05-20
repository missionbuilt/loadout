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
version: 0.2.4
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

## APPROACH_DATA Schema (v0.2 · C1 editorial design)

Build this object during synthesis. Every field is required unless marked optional.
Write all prose in active voice, present tense, tight sentences.

### Text formatting tokens (used inside string fields)

| Token | Renders as |
|---|---|
| `**text**` | `<strong>text</strong>` (bold) |
| `_text_` | `<em>text</em>` (italic) |
| `{chip:confirmed:I · Pain}` | Green MEDDPICC chip |
| `{chip:partial:C · Champion}` | Amber MEDDPICC chip |
| `{chip:unknown:D · Process}` | Grey MEDDPICC chip |

Use tokens in: `meta.deck`, `meddpicc.deck`, `sections[].deck`, `sections[].tldr`, `sections[].action`, and `prose[].text` (type "p" items only).

### Source tier dot classes

| `tier` value | Dot color | Use for |
|---|---|---|
| `"company"` | blood-red | Company's own site, press release, official blog |
| `"press"` | dark ink | Tier-1 press, trade pubs, analyst reports |
| `"social"` | faint | LinkedIn, X, Reddit, podcasts |
| `""` (omit) | army-green | Regulatory (CISA, SEC), third-party data |

```json
{
  "config": {
    "fontToolName": "mcp__<uuid>__warmup_get_fonts"
  },

  "meta": {
    "company":       "Rogue Fitness",
    "contact":       "Jock Padgett",
    "contactTitle":  "Chief Technology Officer",
    "seller":        "Mike (AE)",
    "se":            "Sarah (SE)",
    "callTime":      "14:30 ET",
    "callDate":      "Wed 20 May 2026",
    "briefNumber":   "001",
    "deck":          "A brief for the first call with Jock Padgett, CTO — selling Elastic Security.",
    "sourceCount":   "14",
    "generated":     "20 May 2026",
    "readingTime":   "~14 min"
  },

  "meddpicc": {
    "title": "Where we stand on the deal.",
    "deck": "Eight dimensions, scored from public intel. **Pain** is confirmed — Padgett named it publicly.",
    "cells": [
      {
        "letter":   "M",
        "label":    "Metrics",
        "status":   "partial",
        "headline": "Breach cost, OT downtime, MILO fleet exposure",
        "evidence": "No named baseline yet. Peer breach data gives proxy numbers to anchor the conversation.",
        "next":     "Ask: \'What does an hour of OT downtime cost you, ballpark?\'"
      },
      {
        "letter":   "E",
        "label":    "Economic Buyer",
        "status":   "partial",
        "headline": "Padgett likely owns infra security — Henniger above $1M",
        "evidence": "CFO seat is vacant; Bill acting. Threshold unknown.",
        "next":     "Confirm signing authority in back half of call."
      },
      {
        "letter":   "D",
        "label":    "Decision Criteria",
        "status":   "unknown",
        "headline": "Not formalised — opportunity to shape",
        "evidence": "No public RFP. Conference talk emphasises operational visibility.",
        "next":     "Ask: \'How will you know which platform is the right fit?\'"
      },
      {
        "letter":   "D",
        "label":    "Decision Process",
        "status":   "unknown",
        "headline": "Founder-led, fast — mechanics unknown",
        "evidence": "No board, no PE. Bill makes calls quickly.",
        "next":     "Ask: \'Walk me through how a decision like this gets made here.\'"
      },
      {
        "letter":   "P",
        "label":    "Paper Process",
        "status":   "unknown",
        "headline": "Procurement, legal — all air",
        "evidence": "Private company. No SOC 2 mandate visible.",
        "next":     "Defer to call 2 unless raised."
      },
      {
        "letter":   "I",
        "label":    "Identify Pain",
        "status":   "confirmed",
        "headline": "Named publicly at DefCon — OT/IT convergence, MILO fleet, PCI scope",
        "evidence": "DefCon 31 (Aug 2023): \'Security has to live where the work happens.\'",
        "next":     "Quote his DefCon phrase. Don\'t re-discover what he already named."
      },
      {
        "letter":   "C",
        "label":    "Champion",
        "status":   "partial",
        "headline": "Padgett = likely buyer and champion in one",
        "evidence": "Military background, broad mandate, publicly committed to the problem.",
        "next":     "Identify one SecOps ally by call 2."
      },
      {
        "letter":   "C",
        "label":    "Competition",
        "status":   "partial",
        "headline": "Splunk incumbent inferred",
        "evidence": "3 job posts require \'Splunk or equivalent SIEM experience.\'",
        "next":     "Ask: \'What are you running today for SIEM and endpoint?\'"
      }
    ]
  },

  "sections": [
    {
      "id":     "snapshot",
      "number": "01",
      "for":    "the AE",
      "title":  "Company snapshot.",
      "deck":   "What they do, how they make money, and what shape they\'re in.",
      "tldr":   "Founder-led. Private. **$700M+ revenue**. DTC e-commerce is the spine. **$45M manufacturing expansion** broke ground March 2026.",
      "prose":  [
        {
          "type": "p",
          "text": "Founded 2006. ~1,400 employees in Columbus OH. **Rogue Fitness** is the dominant US strength-equipment maker.",
          "source": { "text": "roguefitness.com · Apr 2026", "tier": "company" }
        },
        {
          "type": "pull",
          "text": "$45M expansion broke ground in March — five more years of demand we already have on the books.",
          "cite": "Bill Henniger to Columbus Business First, 12 March 2026"
        },
        {
          "type": "pull",
          "chip": { "text": "I · Pain", "status": "confirmed" },
          "text": "Quote that directly names the pain.",
          "cite": "Source name · date"
        },
        {
          "type": "facts",
          "items": [
            { "k": "Revenue",   "v": "$700M+", "note": "FY24, triangulated" },
            { "k": "Headcount", "v": "~1,400", "note": "Columbus, hiring fast" },
            { "k": "Capex",     "v": "$45M",   "note": "West Jefferson, Mar 2026" }
          ]
        },
        {
          "type": "table",
          "rows": [
            { "layer": "Storefront", "tool": "Shopify Plus", "status": "Native",  "statusClass": "",    "note": "Out of the box." },
            { "layer": "ERP",        "tool": "NetSuite",     "status": "Native",  "statusClass": "",    "note": "Standard connector." },
            { "layer": "IoT",        "tool": "MILO fleet",   "status": "Paired",  "statusClass": "gap", "note": "2-3 week sprint." },
            { "layer": "SIEM",       "tool": "Splunk (inf.)", "status": "Confirm", "statusClass": "unk", "note": "Confirm in discovery." }
          ]
        },
        {
          "type": "opener",
          "script": "The verbatim opener text the AE reads aloud — ~90 seconds. Root it in a specific public signal from the contact.",
          "beats": ["Pause. Let him redirect if needed. Either answer maps to a demo."]
        },
        {
          "type": "questions",
          "items": [
            {
              "chip": { "text": "I · Pain", "status": "confirmed" },
              "text": "Discovery question targeting the confirmed pain dimension."
            },
            {
              "chip": { "text": "D · Criteria", "status": "unknown" },
              "text": "Discovery question targeting an unknown MEDDPICC cell."
            }
          ]
        }
      ],
      "action": "What the AE or SE should _do_ with this section. One to three sentences, specific to this company and this contact."
    }
  ],

  "actDivider": {
    "kicker": "Handoff · For Sarah, the SE",
    "title":  "Technical posture.",
    "deck":   "Stack, security events, demo prep, and risk flags. What the SE reads on the elevator up."
  },

  "product": "Elastic Security pre-call brief",
  "version": "v0.2.4"
}
```

### Sections reference

Build 9 sections in this order. Use the IDs and `for` values exactly:

| # | id | for | title |
|---|---|---|---|
| 01 | `snapshot`   | `the AE` | Company snapshot. |
| 02 | `leadership` | `the AE` | Leadership & the buyer. |
| 03 | `financial`  | `the AE` | Financial posture. |
| 04 | `industry`   | `the AE` | Industry context. |
| 05 | `signal`     | `the AE` | Recent signal. |
| 06 | `stack`      | `the SE` | Stack & integrations. |
| 07 | `security`   | `the SE` | Public security events. |
| 08 | `demos`      | `the SE` | Demo prep. |
| 09 | `opener`     | `both`   | Opener & discovery. |

The `actDivider` renders automatically before the first `"the SE"` section. Section 09 (`opener`) must contain prose items of type `opener` and `questions`.

### Prose item type reference

| `type` | Required fields | Optional fields |
|---|---|---|
| `p` | `text` (string, supports rich tokens) | `source.text`, `source.tier` |
| `pull` | `text`, `cite` | `chip.text`, `chip.status` |
| `facts` | `items[]` → `k`, `v` | `note` per item |
| `table` | `rows[]` → `layer`, `tool`, `status`, `note` | `statusClass` ("gap" or "unk") |
| `opener` | `script` | `beats[]` (array of strings) |
| `questions` | `items[]` → `text` | `chip.text`, `chip.status` per item |

### MEDDPICC cell `status` values

`"confirmed"` — evidence is in hand, public, datable.
`"partial"` — evidence exists but requires confirmation on the call.
`"unknown"` — no signal; the call must generate it.

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
| 0.2.1 | C1 editorial redesign — Oswald/Merriweather/JetBrains Mono type scale, cream paper palette, full MEDDPICC scorecard at end of report, act divider, facts strip, pull quote, stack table, opener box, TL;DR card, action footer. |
| 0.2.2 | Section heading structure: sec-num → sec-title (kicker) → sec-subtitle (title) → sec-deck. Foot style matches Warmup/Spotter double-rule colophon. Footer links to missionbuilt.io. |
| 0.2.3 | Renderer field name fixes (silent blank output): pull text, facts k/v, opener script/beats[], questions chip, meta generated/sourceCount. Colophon seller path corrected to C.config.seller. JSON validation in approach_get_template. |
