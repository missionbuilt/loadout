# Synthetic Test Epic 2 — MITRE ATT&CK Coverage Insights

*Author: [Synthetic PM] · Status: Draft for review*

---

## Executive Summary

This epic introduces a coverage insights view to our security platform: a visualization layer that shows customers which MITRE ATT&CK techniques their current detection rules cover, where gaps exist relative to the wider techniques landscape, and how their coverage compares to industry benchmarks. The goal is to give security teams the visibility they need to prioritize rule development, justify detection investments to leadership, and identify blind spots before adversaries do.

## Problem

Security teams cannot answer two questions that come up in nearly every leadership review: *"What techniques are we detecting?"* and *"Where are we exposed?"*

Today, answering these questions takes days of manual work. SOC managers and detection engineers maintain personal spreadsheets mapping their custom detection rules to ATT&CK technique IDs. When the framework updates twice a year with new techniques added, they re-do the mapping by hand. When leadership asks for a coverage report ahead of a budget conversation, the team scrambles for a week to produce a snapshot that's already stale by the time it's delivered.

What it actually feels like to be a detection engineer in this loop: you know your team is doing good work. You can name the rules you've written and the threats they catch. You can't show the picture. And the picture is exactly what leadership needs to see to fund the work. The frustration isn't that the work is invisible. It's that you can see what's missing from the picture and you can't get the rest of the org to see it with you.

Why isn't this solved already? Two reasons. The first is a data gap. Mapping detection rules to ATT&CK is hard because rules don't carry technique metadata natively — engineers add it manually, inconsistently, and the metadata decays as rules evolve. The second is a tooling gap. Existing third-party tools (DeTT&CT, Atomic Red Team coverage maps) work for static snapshots but don't integrate with live detection state, so the picture is always behind. Our product has live detection state. We have what nobody else has.

## User

Detection engineers and SOC managers at security-mature enterprises — typically 200+ endpoints, dedicated detection function, in-house rule authoring. They author and maintain 50 to 500 custom detection rules across SIEM and EDR. Leadership-facing coverage reports happen quarterly at minimum, more often when budget cycles or incidents drive them.

## Approach

The feature surfaces a coverage view that maps the customer's active detection rules to ATT&CK techniques, scores coverage by tactic, and highlights gaps weighted by adversary-group relevance (drawn from threat intel data we already license). The view supports filtering by tactic, by adversary group, by detection severity, and by data source.

AI considered and declined. We evaluated whether to use LLMs to auto-classify rules against ATT&CK techniques, but found that our existing static analysis of rule logic produces deterministic, auditable mappings — and customers will not accept *"the AI thinks this rule maps to T1059"* when the same rule deterministically can be classified by examining its query patterns. The latency and non-determinism would not be worth what the LLM adds here. We may revisit LLMs for the rule-authoring assistant in a future epic, but for coverage classification, deterministic wins.

The UI is a new Coverage view in the platform navigation, with the tactic-by-tactic heatmap as the primary visualization, drill-downs by technique, and exportable reports for leadership consumption.

## Competitive

Three players define the coverage-insights space. CrowdStrike's Falcon Insight XDR ships an ATT&CK coverage page tied to their managed detection feed — strong for customers who use their full stack, less useful for teams running custom rules in third-party SIEMs. SentinelOne's Singularity Platform includes ATT&CK mapping for their built-in detections but does not surface custom-rule coverage. Splunk's Enterprise Security suite has the most flexible coverage tooling, but its dependency on the customer maintaining clean rule metadata is exactly the bottleneck most teams already complain about. Our positioning: parity on the underlying capability, advantage on the input — we map live detection state without requiring the customer to maintain mapping metadata themselves.

## Strategic Differentiation

We do not have a durable moat on this feature. CrowdStrike and SentinelOne can build the same view, and some of their customers already get a version of it. We're building this for three reasons unrelated to moat. First, it's table stakes for mid-market and enterprise renewals — coverage visibility is the single most-requested feature from our customer advisory board for two consecutive quarters. Second, it's a wedge into the detection engineer persona, who has historically been a secondary buyer at our accounts and is becoming more strategic in customer org structures. Third, it sets up the rule-authoring assistant (next year's epic) which will use coverage data as the input that drives recommendations. Building this without a moat is the right call. The team should know that's what they're doing.

## Pricing

The coverage view is included in our Enterprise tier. Standard customers get a read-only view of their top-level tactic coverage but not technique-level detail; this becomes an upgrade signal we can convert through customer success outreach. Competitive benchmarks: CrowdStrike bundles its coverage view with Falcon Insight at no separate charge (effective $24/endpoint/month); SentinelOne does not separately price its mapping capability. Our Enterprise pricing ($31/endpoint/month) carries this capability without additional uplift. No pricing committee escalation required.

## Launch Plan

GA tied to our Q4 product release. Documentation: full module in product docs covering concept, configuration, exporting reports, and troubleshooting metadata. Field enablement: sales training and customer success training delivered three weeks before GA. Marketing: launch blog post, one customer-success case study from a design partner, and a coverage-themed power hour for top-50 accounts in the four weeks after GA.

## Success Metrics

We will measure adoption (number of accounts that view the coverage page weekly), engagement (time spent in the view, export count), and outcome (number of new detection rules created downstream of coverage gaps surfaced). MTTR for coverage gap closure serves as the proxy for "did the feature drive better security outcomes." Quarterly reviews with the product trio.

---

---

## Calibration notes

Expected Spotter verdict against this epic: **Not ready** (under v0.1.3, where Lens 9 missing on B2B security features triggers the blocker rule).

Expected lens grades:

| Lens | Expected grade | Why |
|---|---|---|
| 1. User & problem | ⚠️ Needs work | Empathy decent and current state present, but problem scope unaddressed (which MITRE matrix?) and value framing is symptom-relief, not decision-driving. Assumption surfacing weak. |
| 2. Competitive | ⚠️ Needs work | Three competitors named but no workflow specifics, no links, no explicit "what we do differently" sentence. |
| 3. Moat | ✓ Pass *(with caveat)* | Acceptable "no moat but explicit" framing, though the scope-limit on Lens 1 suggests a broader problem framing could have produced a real differentiator. Press-release sentence missing. |
| 4. Solution approach | ⚠️ Needs work | AI-considered-and-declined names only the narrow case (classification); doesn't consider AI for dynamic mapping, prioritization, recommendation. UI defaults to new view. |
| 5. Holistic impact | ✗ Missing | Cross-product cascade not addressed. |
| 6. Packaging & pricing | ✓ Pass | Tier rationale and competitor benchmarks present. |
| 7. Launch readiness | ⚠️ Needs work | Hits docs/training/blog at headline level. Missing PLG, calculators, video, customer comms. |
| 8. Post-launch ownership | ⚠️ Needs work | Three metric categories without thresholds, no telemetry, no adoption mechanics. |
| 9. Trust, governance | ✗ Missing | RBAC, audit trail, transparency not addressed for a view-only B2B security feature. Triggers the Lens 9 blocker rule. |

If your install of The Spotter produces grades that diverge significantly from this calibration table, the skill has drifted. Recheck `SKILL.md` for local edits and any `CLAUDE.md` that may be overriding the lens framework.
