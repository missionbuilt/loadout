# Floodlight — Design Spec

Rationale and locked decisions behind the skill. Read this before changing the catalog,
the template, or the intake flow. For *using* the skill, see `SKILL.md`.

## Thesis

The first step to security is visibility. Floodlight builds the visibility plan first —
it shows where you could watch an attacker move and where you're blind, so the next dollar
goes to the darkest corner. It is a **starting overview, not a CISO**: no maturity grade,
no peer benchmark, no confident named attribution.

## Three inputs (and why only three)

Fewer questions, higher completion. Intake collects: (1) company name, (2) a one-tap
confirmation of inferred industry/region, (3) environment shape (cloud-first / hybrid /
on-prem) with two gates — *run OT/ICS?* (ATT&CK for ICS scope) and *build/deploy AI/ML?*
(MITRE ATLAS adjacency).

**Context vs. current state.** Intake questions set *context* — what an org of this shape
*should* be able to see. Current state — what they *have* — is captured by in-report
toggles, not interrogated up front. This split is deliberate; don't move current-state
questions into intake.

## Two-layer data model (the trust decision)

- **Baked framework** (`floodlight-catalog.json`, version-stamped): tactics, choke points,
  log sources with specific fields and event types, technique→source mappings, and
  retention-by-regulation. Baking this prevents hallucinated event IDs and fields — the
  failure mode that would make the report worse than useless.
- **Live company layer** (`FLOODLIGHT_DATA`): sector/region adversaries, verified breaches,
  applicable regulations — researched at runtime and cited. No uncited claims.

Grounded in MITRE ATT&CK v18 (Oct 2025 — the Detection Strategy / Analytics / Log Sources
model that replaced the deprecated Data Source objects), the CTID Top ATT&CK Techniques
(prevalence + choke points + actionability), DeTT&CT (visibility/data-quality scoring),
and Red Canary prevalence data.

## Output — action-first

- **Hero: ATT&CK Tactic Coverage strip.** Deliberately labeled "Tactic Coverage," not
  "kill chain." Instrumentable tactics Initial Access → Impact (~12); Reconnaissance and
  Resource Development are greyed as external / un-instrumentable. Cells are green / amber /
  red by **threat-weighted visibility**, where amber = a source exists but quality or
  retention is insufficient (blind vs. not-good-enough). The strip is a decomposition of
  the headline KPI and must reconcile with it.
- **Choke-point tactics badged.** The convergence points an attacker can't avoid. The #1
  priority is a red cell that is also a choke point — catch them where they can't route around.
- **Quick-wins roadmap** ranked by marginal coverage gain per added source.
- **Per-source quality/retention flags**; click a cell → techniques → log source + exact
  fields + retention. Toggling a source recolors the map live.
- **Plain-English risk read** auto-generated from the worst cells.

## Weighting model (transparent, in the template)

`techWeight = 1 + chokepoint(1.5) + prevalence(1) + risingTrend(0.5) + adversaryBoost`.
Adversary boost comes from `FLOODLIGHT_DATA.adversaries[].techniques` matched to catalog
IDs, scaled by `rank`. Coverage is **depth-weighted**: a technique covered by one of three
applicable sources scores as a fraction, not full — single-source coverage that EDR-killers
or log-clearing can destroy is partial by design.

## Catalog emphasis (v0.3.0)

- **Identity-first.** Crown-jewel sources lead with identity / cloud / email (matching
  Red Canary 2025 top techniques). Includes AiTM token theft (T1539), MFA bombing (T1621),
  modify-auth (T1556), Golden SAML (T1606.002), and an `nhi_monitoring` source for
  non-human / AI-agent identities (~80:1 over humans).
- **Tempo.** Execution (TA0002) and Defense Evasion (TA0005) flagged `highTempo` and
  weighted heavily — breakout time ~29 min, and Defense Evasion attacks the sensors
  themselves (BYOVD / EDR-killers). The report must argue for breadth, redundancy, and
  off-host log shipping that survives endpoint blinding.

## Locked calls

- Retention mapped per regulation (PCI ~1yr; M-21-31 = 30 months but **federal-only**;
  HIPAA; NERC; SOC 2; GDPR/CCPA). Name the detection-vs-data-minimization tension for GDPR.
- **No benchmarking** — guessing a benchmark wrong is worse than omitting it.
- **Attribution humility** — sector/region targeting over confident named attribution.
- **Assumptions are first-class and editable** — every inference is shown and re-runnable.
- Export to HTML and print-to-PDF; fully self-contained offline file.

## Architecture

Standalone, disconnected — no MCP server. `scripts/inject.py` fills the baked catalog and
the per-run data into `floodlight-template.html` and writes one self-contained HTML file.
Chosen for portable deploy and because a security posture is exactly the kind of thing
users should be able to run with their data staying put. Follows the same self-contained
pattern as The Warmup, The Approach, and The Spotter standalone editions.
