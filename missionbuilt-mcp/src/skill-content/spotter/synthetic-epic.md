# Synthetic Test Epic — Autonomous Triage and Response for High-Severity Endpoint Threats

*Author: [Synthetic PM] · Status: Draft for review*

> This is a deliberately gap-heavy synthetic epic used to calibrate **The Spotter**. Running the skill against this epic in **review mode** should produce a verdict of *Needs polish* with specific gaps flagged on Areas 1, 4, 5, 6, 8, and 9. Areas 2 and 3 should also surface as needing work (Area 3 entirely missing). Area 7 should grade as ⚠️ with surface-level placeholder content.
>
> The PM persona this represents: a thoughtful but mid-career B2B PM who knows the structure of an epic but hasn't internalized the deeper product-thinking areas. The skill's job is to lift this draft into something stronger — without making the PM feel they got it wrong. They didn't. They got it partway.

---

## Executive Summary

This epic introduces autonomous incident response capabilities to our endpoint security platform. When the platform detects a high-severity threat — ransomware encryption, lateral movement, credential dumping — the system will execute a pre-approved response playbook (isolate, kill, rollback, collect evidence) without waiting for analyst confirmation. The goal is to reduce mean-time-to-response from minutes to seconds.

## Problem

SOC analysts can't keep up. The number of high-severity events per analyst per shift keeps climbing, and the time required to manually triage, validate, and respond is the bottleneck. By the time a Tier 1 analyst has confirmed a ransomware encryption event and clicked "isolate host," the encryption has spread to additional machines.

Existing playbooks can automate response when the signals are clean, so customers theoretically have this capability today. They mostly don't use it.

We will solve this by adding an "autonomous mode" toggle that lets the platform act on its own confidence threshold. Operators set the threshold, the playbooks, and the scope. The agent does the work. Customers will toggle into autonomous mode based on their risk tolerance.

## User

Tier 1 SOC analysts at mid-to-large enterprises (>500 endpoints) running our endpoint security platform. They work 12-hour shifts, handle 30–80 alerts per shift, and have 2–5 years of experience.

## Approach

We'll build an AI-driven decision engine that reads detection signals, scores confidence, matches against pre-approved playbooks, and executes. The UI is a new "Autonomous Response" dashboard with a real-time feed of agent actions, override controls, and post-action review.

## Competitive

CrowdStrike Falcon and SentinelOne Singularity already offer autonomous response for some threat classes. Microsoft Defender for Endpoint has automated investigation and response (AIR). We are behind.

## Pricing

We'll bundle this with our Premium tier. Customers on Standard get a read-only view of agent recommendations.

## Launch Plan

- Documentation: Update product docs with a new module section.
- Training: Sales team training session.
- Marketing: Blog post at launch.

## Success Metrics

We'll track adoption rate of the autonomous mode toggle and reduced MTTR.

---

## Calibration notes

Expected skill verdict: **Needs polish**

Expected area grades:

| Area | Expected grade | Why |
|---|---|---|
| 1. User & problem (not solution) | ⚠️ | Thin empathy. No diagnosis of *why* customers don't already automate (product gaps, trust gaps). Solutioning leakage in the *Approach* section. |
| 2. Competitive landscape | ⚠️ | Names three competitors and asserts "we are behind" but does no analysis of how each handles it, where each is strong/weak, or where the space is for us. |
| 3. Strategic differentiation (moat) | ✗ | Completely missing. |
| 4. Solution approach | ⚠️ | "AI-driven decision engine" without explicit AI decision. Implies static playbook matching where dynamic agentic reasoning is what actually works. Defaults to "new dashboard" without UI restraint consideration. No skills-first thinking. |
| 5. Holistic impact | ✗ | When the agent isolates a host, what happens in the SIEM, case management, on-call rotation, identity systems? Cross-product cascade not considered. |
| 6. Packaging & pricing | ⚠️ | Names tier but provides no competitor pricing benchmarks, no reasoning about why this tier, no escalation flag. |
| 7. Launch readiness | ⚠️ | Hits docs/training/blog at headline level. No calculators, power hours, PLG, video, customer comms. |
| 8. Post-launch ownership | ⚠️ | "Track adoption and MTTR" — generic, no specifics. No telemetry plan, no in-product guides, no adoption mechanism. |
| 9. Trust, governance & auditability | ✗ | No mention of trust gradient, RBAC, audit trail, transparency, or human-on-the-loop pattern. Critical gap for a B2B security feature. |

If your install of **The Spotter** produces grades that diverge significantly from this calibration table, the skill has drifted. Recheck `SKILL.md` for local edits and any `CLAUDE.md` that may be overriding the area framework.
