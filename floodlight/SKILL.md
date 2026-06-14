---
name: floodlight
description: "Floodlight. A visibility-first security posture overview built from three inputs — where you can see an attacker and where you're blind, mapped to ATT&CK tactics. Triggers: \"run floodlight\", \"build my security posture\", \"where am I blind\", \"visibility assessment\"."
license: MIT
author: H. Michael Nichols
version: 0.1.0
part_of: The Loadout
---

# Floodlight

## Full description

Floodlight builds an initial security-visibility posture from three quick inputs — company name, industry and region, and the shape of the environment. The output is an **ATT&CK Tactic Coverage** map: tactic by tactic, where you can see an attacker and where you're blind, weighted by what adversaries actually use and grounded in DeTT&CT, the CTID Top ATT&CK Techniques, and MITRE ATT&CK v18. The thesis is simple — the first step to security is visibility — so Floodlight builds the visibility plan first. It runs disconnected: no MCP server, no data leaves the room. Trigger phrases: "floodlight", "run floodlight", "build my security posture", "where am I blind", "visibility assessment", "security visibility map", "what should I be logging".

## Why "Floodlight"

You can't lift in the dark, and you can't defend what you can't see. A floodlight
doesn't catch the intruder for you — it removes the place they were counting on to
hide. That's the whole posture in one image: before you buy another tool or write
another detection, you flood light across the room and find out which corners are
already lit and which are black.

Floodlight is a **starting overview, not a CISO**. It does not grade your program,
benchmark you against peers, or claim to know what targets your specific company.
It shows you, honestly, where your telemetry would let you watch an attacker move —
and where it wouldn't — so the next dollar and the next hour go to the darkest
corner first.

---

## What this is NOT

State this plainly if the user expects more. Floodlight does **not**:

- Replace a CISO, a detection-engineering program, or a real risk assessment.
- Benchmark the org against peers or assign a maturity grade. (Guessing a benchmark
  wrong is worse than omitting it.)
- Claim confident attribution — "APT-X is targeting *you*." It reasons from
  **sector and region** ("organizations like yours are most often hit by…"), not
  named certainty.
- Audit the live environment. It works from what the user tells it plus public
  research. Everything it assumes is shown, labeled, and editable.

The honesty is the product. A modest, correct map beats a confident, wrong one.

---

## INTAKE Mode (Step 0 — run once)

Keep this short. Fewer questions means more people finish. **Three inputs, that's it.**
Infer what you can and let the user correct with one tap.

1. **Company name.** Required. From the name alone, infer the likely industry and
   region and say so — don't make them type it.
2. **Industry & region — confirm the inference.** "Looks like *fintech, US* — right?"
   One-tap correct. This sets sector-based adversary research and applicable regulations.
3. **Environment shape.** Cloud-first / hybrid / on-prem, plus two yes/no gates:
   - **Run OT/ICS?** (gates whether you note ATT&CK for ICS as out of scope.)
   - **Build or deploy AI/ML?** (gates whether you note MITRE ATLAS as adjacent.)

**Design principle — context vs. current state.** Intake questions set *context*: what
an org of this shape *should* be able to see. They do **not** ask "what do you have
today?" item by item — that's captured *in the report*, where the user toggles each
log source on or off and the map recolors live. Don't drag current-state interrogation
into intake.

**What NOT to ask:** report format or length (fixed), framework choice (fixed —
ATT&CK v18 + the bundled catalog), or a tool inventory (that's the in-report toggles).
Never ask more than two clarifying questions in one turn.

**After collecting the three:** confirm in one line and move to Research.

---

## The two layers — baked vs. live

Trust is make-or-break for this skill, so the two halves of the data are sourced
differently and must never be confused.

**Baked framework layer — `floodlight-catalog.json` (do not invent).** Tactics,
choke points, log sources, the specific fields and event types each source provides,
retention-by-regulation, and the technique→source mappings are a curated,
version-stamped catalog. **Read `floodlight-catalog.json` from this folder** and use
its IDs verbatim. Never invent an event ID, field name, technique ID, or retention
figure — if it isn't in the catalog, leave it out. This is what keeps the report from
hallucinating a plausible-sounding-but-wrong detection.

**Live company layer — researched at runtime and cited.** Sector/region adversaries,
verified public breaches, and applicable regulations are gathered live and attributed.
You assemble this into `FLOODLIGHT_DATA` (schema below). No uncited breach claims, ever.

---

## RESEARCH Phase (Step 1)

Before searching, output one line in chat:
*"🔦 Mapping the threat landscape for [Company] — [industry], [region]. One minute."*

Run these batches concurrently. Replace `[SECTOR]`, `[REGION]`, `[COMPANY]`, and use
`[DATE]` = 18 months prior to today for breach recency.

| Batch | Query pattern | Feeds |
|---|---|---|
| **Sector adversaries** | `[SECTOR] sector top threat actors ransomware 2025 2026 targeting` | `adversaries[]` |
| **Region adversaries** | `threat actors targeting [REGION] [SECTOR] eCrime nation-state` | `adversaries[]` |
| **Technique prevalence** | `[SECTOR] most common attack techniques initial access MITRE ATT&CK` | `adversaries[].techniques`, `adversaryDeck` |
| **Verified breaches** | `"[COMPANY]" breach OR ransomware OR "data incident" after:[DATE]` | `otherPriorities`, `assumptions` |
| **Sector breaches** | `[SECTOR] [REGION] breach ransomware incident after:[DATE]` | `adversaryDeck`, `otherPriorities` |
| **Regulations** | `[SECTOR] [REGION] compliance log retention requirement PCI HIPAA NERC SOC2` | `regulations[]` |

**Map each adversary's techniques to catalog technique IDs.** When research says a
group leans on phishing, valid-account abuse, or AiTM token theft, find the matching
`T####` IDs in `floodlight-catalog.json` and put those IDs in `adversaries[].techniques`.
The renderer uses them to boost the weighting on tactics those adversaries actually hit.
If you can't map a described behavior to a catalog technique, drop it rather than invent
an ID.

**Attribution humility.** Prefer "organizations in [sector] are most frequently hit by
[group/behavior]" over "[group] is attacking you." Rank adversaries 1–5 by relevance to
the sector/region, not by certainty about this one company.

**Regulations** must be the catalog's IDs only — currently: `pci`, `hipaa`, `m2131`
(federal only — don't apply to private orgs), `nerc`, `soc2`, `gdpr`. Include only what
plausibly applies to this org's sector/region. Name the detection-vs-data-minimization
tension when `gdpr` is included.

---

## FLOODLIGHT_DATA schema

Build this object during synthesis. Only the company-specific layer lives here — the
framework comes from the catalog. Every field optional unless marked required; the
renderer degrades gracefully on anything omitted. Rich-text tokens `**bold**` and
`_italic_` are supported in `deck`, `adversaryDeck`, `why`, `otherPriorities[].body`,
and `assumptions[]`.

```json
{
  "meta": {
    "company":   "Northwind Mutual",          // required
    "industry":  "Regional insurance",         // required
    "region":    "US (Midwest)",               // required
    "deck":      "A visibility-first read of where Northwind can watch an attacker move — and where the room is dark.",
    "subtitle":  "Hybrid · no OT · deploys ML underwriting",   // optional eyebrow line
    "generated": "13 Jun 2026"                 // date only, from system context
  },

  "applicableSources": [
    "cloud_signin", "identity_audit", "process_creation", "powershell_logs",
    "windows_auth", "email_security", "network_flow", "dns_query", "edr_endpoint"
  ],
  // OPTIONAL. Log-source IDs (from the catalog) that this org *should* have given its
  // shape. Omit to default to every crown-jewel source. Trim on-prem-only sources for a
  // cloud-first shop; keep the identity/cloud/email core for everyone.

  "currentState": {
    "enabledSources": ["cloud_signin", "email_security", "edr_endpoint"]
    // What they say they have TODAY. Default to a conservative few or empty — the user
    // toggles the rest up in the report and the map recolors live.
  },

  "adversaryDeck": "Mid-market insurers are squarely in the eCrime ransomware lane, with identity-first intrusions leading.",

  "adversaries": [
    {
      "rank": 1,                                // 1 = most relevant to this sector/region
      "name": "Ransomware affiliates (eCrime)",
      "motivation": "Financial",
      "why": "Insurance carriers hold dense PII and pay to restore operations — a top eCrime target in 2025–26.",
      "techniques": ["T1566", "T1078.004", "T1539", "T1486"],   // catalog technique IDs
      "citation": "Red Canary Threat Detection Report 2025",
      "citationUrl": "https://redcanary.com/threat-detection-report/"
    }
  ],

  "otherPriorities": [
    { "title": "Recent sector incident", "body": "A peer carrier disclosed a ransomware event in Q1 2026 — **identity** was the entry point." }
  ],

  "regulations": ["pci", "hipaa", "gdpr"],      // catalog IDs only

  "assumptions": [
    "Hybrid environment, cloud-first identity (Entra/Okta). No OT/ICS.",
    "Deploys ML for underwriting — ATLAS is adjacent but out of scope for this map.",
    "No verified public breach found for Northwind itself; sector data used as proxy."
  ]
}
```

### Field reference

| Field | Required | Notes |
|---|---|---|
| `meta.company` / `industry` / `region` | yes | Header identity + framing. |
| `meta.deck` / `subtitle` / `generated` | no | Deck supports rich tokens. `generated` is date-only. |
| `applicableSources[]` | no | Catalog source IDs the org *should* have. Defaults to all crown-jewel. |
| `currentState.enabledSources[]` | no | Catalog source IDs they have *today*. Drives initial colors; user toggles live. |
| `adversaries[]` | recommended | `rank` 1–5, `techniques` = catalog IDs, `citation`(+`citationUrl`) required when a claim is made. |
| `adversaryDeck` | no | One-line framing above the adversary list. |
| `otherPriorities[]` | no | `title` + `body` (rich). Verified incidents, sector context. |
| `regulations[]` | no | Catalog reg IDs only. Drives the retention table. |
| `assumptions[]` | recommended | First-class and editable — every inference you made, in plain language. |

**Assumptions are not optional in spirit.** Every guess you made — environment shape,
proxy data, scope calls — goes in `assumptions[]`. They drive the analysis and the user
corrects them and re-runs. Showing your work is how a disconnected skill earns trust.

---

## RENDER Phase (Step 2)

Every Floodlight posture is built locally from the bundled `floodlight-template.html`
and `floodlight-catalog.json`. No MCP server, no network call, no font tool. One path.

```
a) Write the assembled FLOODLIGHT_DATA object to a temp file as JSON:
      [workspace]/floodlight-data.json
   Write it with a file tool or heredoc. Do not escape anything yourself —
   the inject script handles </script> escaping.

b) Run the bundled injection script (note: FOUR arguments — data, catalog,
   template, output):
      python3 [skill_dir]/scripts/inject.py \
        floodlight-data.json \
        [skill_dir]/floodlight-catalog.json \
        [skill_dir]/floodlight-template.html \
        floodlight-posture.html
   The script validates both JSON inputs, escapes </script> sequences, and
   replaces __FLOODLIGHT_DATA__ and __FLOODLIGHT_CATALOG__. It prints
   "[inject] OK" on success and a specific error (invalid JSON / missing
   placeholder) on failure. Fix the data and re-run if it fails.

c) FALLBACK — no shell available (e.g. a chat-only environment):
   Do the same steps with file tools directly:
     1. Read [skill_dir]/floodlight-template.html and
        [skill_dir]/floodlight-catalog.json.
     2. In BOTH the data JSON and the catalog JSON, replace every "</script>"
        (case-insensitive) with "<\/script>".
     3. Replace the literal token __FLOODLIGHT_CATALOG__ with the escaped
        catalog JSON, and __FLOODLIGHT_DATA__ with the escaped data JSON.
        Literal string swaps — do not use regex replacement, and do not alter
        any other template content.
     4. Write the result to floodlight-posture.html.

d) Surface floodlight-posture.html to the user with the environment's file
   presentation mechanism. The file is fully self-contained: open it in any
   browser, toggle sources on the page, export to HTML or print to PDF. Fonts
   load from the Google Fonts CDN when reachable and fall back to system fonts
   on locked-down networks.
```

---

## Summary line

After rendering, output one summary line in chat:

*"[N] tactics mapped · [N] choke points · [N] dark / [N] partial / [N] lit · top gap: [tactic]"*

Then one sentence: the single darkest, highest-leverage corner — the red choke-point
tactic the user should close first. Nothing else in chat. The posture is the artifact;
don't duplicate it.

---

## Editorial rules

- **Visibility first, always.** The recommendation is what to *see*, not what to *buy*.
  Never name a vendor product as the answer.
- **No invented framework facts.** Event IDs, fields, technique IDs, retention figures —
  catalog or nothing.
- **No uncited live claims.** Every breach, adversary, or regulation assertion carries a
  source. Sector proxies are labeled as proxies in `assumptions[]`.
- **No benchmarking, no maturity grade.** State where they can and can't see. Don't
  score them against an invented peer set.
- **Attribution humility.** Sector/region targeting language, not confident named attribution.
- **Choke points lead.** When ranking what to fix, a red cell that is also a choke point
  outranks a red cell that isn't — catch them where they can't avoid you.
- **Assumptions are visible and editable.** Surface every inference; invite correction.
- **Redundancy over single-source coverage.** A tactic covered by one log source that
  EDR-killers or log-clearing can destroy is *partial*, not done. The weighting already
  rewards depth — your prose should too.

---

## Version history

| Version | Change |
|---|---|
| 0.1.0 | Initial public release. Self-contained standalone edition — three-input intake, live sector/region adversary research, baked `floodlight-catalog.json` (v0.3.0: 14 tactics, 18 log sources, 71 techniques, 13 choke points, retention-by-regulation), `scripts/inject.py` local render against `floodlight-template.html`, interactive in-report source toggles with live recolor, HTML/PDF export. No MCP dependency. |
