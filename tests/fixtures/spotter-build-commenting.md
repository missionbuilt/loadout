---
feature: in-app commenting on analytics dashboards — letting users leave threaded comments on specific charts or data points, tag teammates, and resolve threads
---

Area 1 — User, Problem, Why Unsolved, Assumptions, Alternatives, Epistemic Openness

Our primary user is a data analyst at a mid-market B2B SaaS company — 200 to 2,000 employees. They spend most of their day in our analytics product building reports and sharing them with ops and finance stakeholders. The hard part of their day is that insights don't travel well. They screenshot charts, paste them into Slack, and then context gets lost in the thread. By the time a decision-maker asks a follow-up question two days later, the analyst has moved on and has to reconstruct everything.

I think it's a prioritization trap. Commenting feels like a "nice to have" collaboration feature, not a core analytics capability — so it keeps losing to things like new chart types or faster query performance. The other part is that our customers have worked around it so long with Slack that the pain is normalized. They don't file support tickets about it because exporting a screenshot takes ten seconds. The friction is real but it's chronic, not acute. It took us sitting in six customer sessions and watching analysts apologize for their own workflow before we took it seriously. The workaround made the problem invisible.

On assumptions: the analyst behavior one feels settled — we have enough qualitative signal that they want the conversation anchored to live data, not a screenshot. The decision-maker assumption is wide open. We've never successfully gotten that persona into the product for anything other than one-off report views. We're betting that an email notification with a direct link lowers the barrier enough, but we haven't tested it. If we're wrong, we'd see it in notification click-through rates and comment reply rates from non-analyst roles within the first 30 days of beta.

On alternatives: we looked at three. A Slack integration with two-way threading was on the table longest — it meets stakeholders where they are, but we kept coming back to the fact that it concedes the product as the system of record. A scheduled digest with annotated snapshots solved for async broadcast, not conversation. A simple notes field was the most conservative option but it's not collaborative — one person's note, no threading, no mention, no resolution.

On epistemic openness: the scenario that changes everything is analysts adopt it but stakeholders don't. If that's the finding at 60 days, the feature becomes a personal annotation tool, not a collaboration layer. The other signal I'm watching is whether people use chart-level comments or anchor everything at the dashboard level. If chart-level precision turns out not to matter, the whole interaction model might be wrong and a simpler notes panel wins.

Area 2 — Competitive Landscape

Tableau has had commenting since 2019 but it's bolted on. Comments live in a sidebar panel that's separate from the viz — you can't anchor a comment to a specific mark or data point, only to the view as a whole. The conversation is spatially disconnected from the thing being discussed. Power BI's approach is similar structurally — comments are view-level, not element-level. What's different is that it lives inside Teams for a lot of their install base, which means the conversation actually happens where the stakeholders are. The breakdown is that Teams threading and dashboard state get out of sync fast. There's no resolution model. On Looker — my honest read is that it's a positioning call more than a build cost thing. Gating comments behind Enterprise signals that collaboration is infrastructure, not a feature.

The daylight I think is real: none of them do element-level anchoring well. And none of them have a resolution model that means anything — there's no concept of "this question was answered and here's the outcome." The workflow moment we could own is the review session — a team sits down to walk through a dashboard before a planning meeting, they work through open questions, and they close the loop before they leave. That moment doesn't exist anywhere in Tableau, Power BI, or Looker.

Area 3 — Strategic Differentiation

We sit at the point where the data is live and the decision-maker has already been sent a link — our share flow is the mechanism that gets stakeholders into dashboards in the first place. Our stakeholders get there because an analyst sent them something and asked them to look. That's a warmer entry point. Second, our data model is at the chart level — we already have element identity for every visualization. Anchoring a comment to a specific chart isn't a new abstraction we'd have to build. The real defensibility argument is that our buyer — the ops and finance stakeholder in a mid-market company — is underserved by Tableau and Power BI because those products are analyst tools first. We're building for the person who receives the dashboard, not the person who builds it.

Press-release sentence: "Before: your analyst sends a dashboard link, the conversation happens in Slack, and the decision gets made on a screenshot that's already stale. After: the question, the answer, and the outcome live on the live data." The blurry part is retention — we haven't confirmed with legal whether "permanently" is accurate at 90-day retention.

Area 4 — Solution Approach

AI doesn't touch comment content in v1. Reasoning: trust and consent model not designed yet. Worth flagging for v2: thread summarization before planning meetings. On skills-first: a webhook that fires when a thread is created or resolved is low-cost and immediately useful. A write API for programmatic comments is more interesting — architecture implication is treating comments as a first-class resource from day one. On UI: side panel was the safe call. Panel keeps the viz untouched across dense dashboards. Tradeoff: weaker spatial connection. Haven't prototyped inline anchoring vs. panel to know if precision matters to users.

Area 5 — Holistic Impact

Notification dependency and partial data lifecycle mapping done. Permissions largely unmapped — "view access can comment" is the default but we haven't thought through external share link viewers or contractor SSO access. Org admin controls are entirely unmapped — no cross-instance visibility, no audit log. On data lifecycle: soft-delete with chart is the working assumption. Dashboard duplication and chart moves are gaps — not written down. Search and discoverability: completely unmapped. No comment inbox, no activity feed. Meta-gap: we've been designing this as a chart-level feature when it's actually instance-level infrastructure.

Area 6 — Packaging & Pricing

Betting on activation and retention, in that order. Dashboards go dark after analysts build them — if comments drive stakeholder engagement, they solve a retention problem we care about more than a monetization problem right now. Haven't pressure-tested this against actual expansion data. The usage dimension is uncomfortable — a VP of Finance checking dashboards and leaving comments is an active user our pricing model is blind to. The seat model doesn't capture read-and-reply users. This decision needs product, pricing, and finance in the room — it's a business model question, not a product scope decision. The epic shouldn't go to engineering commit without that conversation on record.

Area 7 — Launch Readiness

Three named enterprise accounts — Acme Health, Northwind, Lattice Logistics — are the obvious beta cohort. Haven't committed to it or looped in CSMs. Instinct: closed beta, dedicated onboarding calls, direct PM line. Documentation: blank — no writer assigned, no timeline, haven't decided if docs are a ship requirement. Field enablement: AEs need a one-pager and a pre-seeded demo environment. Demo script matters more than a deck — the feature is interactive. Launch posture: marquee, not quiet. The feature requires behavior change from a persona who isn't already in the product daily. Marketing isn't in this epic anywhere and they should be.

Area 8 — Post-Launch Ownership

Leading indicator: within 60 days of GA, 40% of externally-shared dashboards have at least one comment from a non-analyst role. Beta threshold: two of three named accounts have a resolved thread within 30 days. Telemetry list: comment created (with role, chart ID, dashboard ID), thread resolved (time-to-resolution, resolver role), @mention sent (whether mentioned user had visited before), notification opened (by channel and role), panel opened without commenting, comment replied to (replier role, time since original), dashboard viewed by non-analyst after comment created. This list needs to be a build requirement. Ownership after GA: unassigned. Should sit with PM for first 90 days, then move to growth analyst. Dashboard to support weekly review not yet built.

Area 9 — Trust, Governance & Auditability

CRUD model: comment owner can edit/delete their own. Haven't defined dashboard owner or admin deletion rights. Minimum floor needed: comment owner edits/deletes own, dashboard owner deletes any comment on their dashboard, org admin deletes anything. Org admin controls: entirely unmapped. No cross-instance visibility, no export, no audit log. Legal hold requests would require manual infrastructure export — not acceptable for enterprise. Audit log is a procurement requirement for regulated verticals. Data retention: 30-day soft delete was carried over from chart data model, not a deliberate policy. No configurable retention. Haven't confirmed with legal whether comments fall under existing DPA. Blast radius scenario: stakeholder leaves a comment with confidential deal info on an externally-shared dashboard — visible to anyone with the link, including unauthenticated external viewers we can't enumerate. No controls to prevent it. Two pre-GA requirements regardless of segment: per-dashboard setting restricting comments to authenticated internal users only, and a UI indicator when a dashboard has external viewers.
