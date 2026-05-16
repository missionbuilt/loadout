# Synthetic Test Epic 3 — Adversary-Informed Vulnerability Prioritization

*Author: [Synthetic PM] · Status: Draft for review*

---

## Executive Summary

This epic introduces an adversary-informed vulnerability prioritization capability to our security platform: a prioritized work queue that fuses vulnerability data, threat intel, asset inventory, and exploit availability to tell customer vulnerability management teams which 20 patches to ship this week — not which 200 are theoretically critical. The goal is to replace CVSS-sorted backlogs with a daily-refreshed, operationally actionable queue.

## Problem

Security teams patch the wrong things. Not because they're bad at their jobs. Because the inputs they're working from are wrong.

The default prioritization signal is the Common Vulnerability Scoring System (CVSS). CVSS is a base score from 0–10 that encodes how bad a vulnerability is in the abstract — exploitability, impact, complexity. It does not account for whether the vulnerability is actually being exploited in the wild, whether the affected asset is internet-facing, whether the customer's specific configuration is vulnerable, or whether anyone has the access to weaponize it. A critical CVSS-10 vulnerability on an air-gapped internal printer should never be patched before a CVSS-7 vulnerability on the customer's internet-facing identity provider. CVSS doesn't know the difference. So vulnerability management teams patch the wrong things, and the things they actually need to patch sit in the queue.

What it feels like to be a vulnerability management engineer: you know your priority queue is wrong. You know the highest-CVSS items in the queue often don't matter. You know the items that *do* matter are buried because their CVSS is medium and they wouldn't make a default top-100 list. You spend half your time recalibrating the queue by hand against threat intel, asset inventory, and exploit availability — and the calibration goes stale the moment you finish it. The frustration isn't that you don't know what to prioritize. It's that you can't operationalize what you know.

How is this solved today? Two main paths. Some teams pay for Tenable's VPR or Qualys's TruRisk — vendor-specific prioritization scores that augment CVSS with proprietary signals. Some teams build their own with EPSS (Exploit Prediction Scoring System, from FIRST.org), CISA's Known Exploited Vulnerabilities catalog, and asset criticality data joined manually. Both paths leave gaps. The vendor scores are black-box and not portable. The DIY path is fragile and labor-intensive. Most teams end up with a hybrid that's expensive to maintain and only slightly better than CVSS-sorted.

Why isn't this solved already? Three reasons. The vulnerability data itself is high-quality and abundant — that's not the constraint. The constraint is the *joining problem*: prioritization requires fusing vulnerability data, threat intel (who's actively exploiting what), asset inventory (where it lives in the customer's environment), and configuration data (whether the customer is actually vulnerable to this CVE on this asset). No single source has all four. Most products own one or two. The teams who do it well are the ones who've invested in building the join themselves, which is rare and expensive. The second reason: the right answer is dynamic. What matters today is different from last month, and static lists go stale. The third reason: trust. When teams hand prioritization to a system they don't understand, they lose the ability to explain decisions to leadership, auditors, and themselves.

**Scope.** This feature targets external-facing vulnerability prioritization for IT assets — the patch decisions made by vulnerability management teams against the customer's CMDB and EDR-discovered inventory. We are explicitly not scoping to application-level vulnerability prioritization (separate problem, separate persona, separate data shapes), cloud workload prioritization (covered by our CSPM module, different lifecycle), or third-party risk prioritization (different stakeholder, different data sources). Each of those deserves its own epic.

**Value.** The work is not *"give the team a better score."* Scores are a means. The value is *the prioritized work queue the customer's vuln team actually patches against on Monday morning* — the top 20 items they should hit this week, with the reasoning behind each one visible and editable. That queue, refreshed daily as threat intel evolves, is what changes outcomes.

**Assumptions worth surfacing.** Three. First: customers will actually act on the prioritized queue rather than reverting to CVSS-sorted lists out of habit. We have evidence from three design partners that they will if the reasoning is visible; we don't have data at scale. Second: the threat intel feeds we license (Mandiant, Recorded Future, our own telemetry) are timely enough to drive daily refresh. Latency unknown above the 95th percentile. Third: the customer's CMDB is accurate enough to support asset-criticality joins. Anecdotally most CMDBs are 60–80% accurate; we don't yet know if that's sufficient for prioritization or if we need a CMDB-cleanup capability first.

**Alternatives considered.** Three. First: build our own proprietary score and brand it (the Tenable VPR / Qualys TruRisk path). Rejected because customers told us in interviews they want explainability, not another opaque score. Second: focus on threat intel-only prioritization (CISA KEV + EPSS). Rejected because that path misses the asset-criticality and configuration-vulnerability dimensions, which are the two that drive the biggest changes in priority. Third: build a recommendation engine that surfaces the top-20 list passively but leaves the queue in the existing UI. Rejected because the queue UI is where teams actually work; recommendations they have to navigate to get ignored. The chosen framing — replace the prioritization input directly in the workflow tool — addresses the actual constraint.

**Where we expect to learn.** Three places. First: whether teams adopt the queue as-is or want significant customization per role/team. If pilot data shows heavy customization need, we'd ship a more configurable framework rather than a managed list. Second: whether the daily refresh cadence is right. May be too aggressive for some teams (introducing volatility) or too slow for others (missing fast-moving exploits). Third: whether the explainability layer (showing why each item is prioritized) is used and trusted. If teams ignore it, we've over-invested. If they read it deeply and disagree often, the underlying model needs work, not the explanation.

## User

Vulnerability management engineers and security operations leaders at security-mature enterprises (typically 1,000+ employees, 5,000+ endpoints, dedicated VM function). They manage 50–500 patches per month against a backlog that's chronically larger than capacity. They report to security leadership monthly with metrics on patch SLA compliance and risk reduction.

## Approach

The feature surfaces the prioritized queue as a primary workflow surface in our vulnerability management module. The queue refreshes daily, incorporating threat intel updates and asset inventory changes. Each item shows the reasoning behind its priority — which signals contributed, what changed since yesterday, what the customer's team has previously patched in this class. The queue supports per-team filtering, manual overrides with audit trail, and export to ticketing systems.

AI accelerated. LLM reasoning powers the explainability layer — translating the multi-signal scoring into prose a vulnerability engineer can use in their report to leadership. LLMs also drive the daily refresh logic, weighing new threat intel against ongoing operational context to determine which items move in priority. Static rule-based prioritization would force every customer to use the same weighting; LLM-based reasoning lets the model account for the customer's specific environment and history.

The UI is a new "Prioritized Queue" view in the vulnerability management module, replacing the existing CVSS-sorted list as the default workflow.

## Competitive

Three vendors lead this space. Tenable's VPR (Vulnerability Priority Rating) is the most adopted; closed model, not portable. Qualys's TruRisk is similar in approach. Rapid7's Active Risk score is the newer entrant and the most transparent of the three. Each scores well in customers' RFPs but underperforms in actual operational adoption because the score doesn't replace CVSS in the workflow — it lives in a separate column users have to choose to sort by. Our positioning: ship the prioritized work queue, not a score.

## Strategic Differentiation

The moat candidate is the join. We are one of the few platforms that combines first-party detection telemetry (we see exploits in the wild on customer endpoints), threat intel licensing, asset inventory from our EDR footprint, and configuration data from our agent. Tenable, Qualys, and Rapid7 each have one or two of these; none have all four. Whether this is a durable moat depends on whether competitors invest in closing the gap — our customer data suggests they're starting to. We'd estimate 18–24 months of advantage before parity, which is enough to establish workflow lock-in if execution is good.

## Pricing

The prioritized queue is included in our Premium and Enterprise tiers as part of the existing vulnerability management module. No tier upsell is required; this is renewal table-stakes for our existing customer base. Pricing committee notified, no approval needed.

## Launch Plan

GA tied to our Q2 product release. Documentation: full module update, with migration guide for customers transitioning from CVSS-sorted workflows. Field enablement: sales training and customer success briefing. Marketing: launch blog and case study from design partner.

## Success Metrics

We will track adoption (percentage of vulnerability management customers using the prioritized queue weekly), patch SLA improvement (median time to patch for top-20 items, measured against the customer's baseline), and customer satisfaction (NPS lift among VM teams). Quarterly review.

---

---

## Calibration notes

Expected Spotter verdict against this epic: **Not ready** (under v0.1.3 — strong Lens 1, but Lens 9 effectively missing triggers the blocker rule).

This epic was designed to test whether The Spotter correctly recognizes strong Lens 1 work. The Problem section explicitly addresses all 8 Lens 1 sub-checks — empathy, current state, why-not-solved, no-solutioning, scope and value, assumptions, alternatives considered, and epistemic openness. Other sections are deliberately lighter so the verdict stays honest.

Expected lens grades:

| Lens | Expected grade | Why |
|---|---|---|
| 1. User & problem | ✓ Pass (strong) | All 8 sub-checks pass. This is the validation case for v0.1.2/v0.1.3 — the skill should recognize good work, not just bad. |
| 2. Competitive | ⚠️ Needs work | Three competitors named but workflow specifics, links, and explicit "what we do differently" articulation are missing under v0.1.3's bar. |
| 3. Moat | ⚠️ Needs work | Specific moat present, but the press-release sentence is missing — no outside-in customer framing. |
| 4. Solution approach | ⚠️ Needs work | AI accelerated decision strong. Skills-first not addressed. UI defaults to new view. |
| 5. Holistic impact | ✗ Missing | Cross-product cascade unaddressed (ticketing integration mentioned in passing only). |
| 6. Packaging & pricing | ⚠️ Needs work | Tier with rationale present, but no competitor pricing benchmarks. |
| 7. Launch readiness | ⚠️ Needs work | Docs/training/blog hit; PLG, calculators, video, customer comms, sequencing details missing. |
| 8. Post-launch ownership | ⚠️ Needs work | Three metric categories without thresholds, no telemetry plan, no adoption mechanics. |
| 9. Trust, governance | ⚠️ Needs work *(borderline ✗)* | "Manual overrides with audit trail" mentioned; no RBAC, no granular trust framework, no transparency commitments. Some leaders grade this ✗ Missing, which would trigger the Lens 9 blocker rule and elevate the verdict to *Not ready*. |

This calibration demonstrates two things: (1) v0.1.3 correctly recognizes strong Lens 1 work without over-flagging, and (2) the Lens 9 blocker rule has bite even when most other lenses are passing or near-passing. The single most important Lens 1 result is that all 8 sub-checks pass on an epic that did the work — confirming the lens isn't a one-way ratchet that only flags problems.
