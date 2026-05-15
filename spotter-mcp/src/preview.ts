/**
 * /preview route — renders the worked Spotter walkthrough.
 *
 * Visitors who hit this page see one synthetic epic taken through all three
 * Spotter phases: Build, Iterate, Review. The content here is the actual
 * output of running the v0.2.0 skill against examples/synthetic-epic-3.md
 * (adversary-informed vulnerability prioritization).
 *
 * Design is a 1:1 of the v3 missionbuilt.io walkthrough mockup. Iron Log
 * tokens throughout: warm charcoal base, chalk text, oxblood as the single
 * accent, army green only on small status marks, no rounded corners, no
 * shadows. Three fonts: Oswald display, Merriweather body, JetBrains Mono
 * for eyebrows and labels.
 */

interface PreviewArgs {
  origin: string;
  githubUrl: string;
}

function escape(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ============================================================
 * Captured Spotter output for synthetic-epic-3
 * Adversary-Informed Vulnerability Prioritization
 *
 * These constants are the actual outputs of running the v0.2.0
 * skill against synthetic-epic-3.md. Per the skill's calibration
 * note: verdict is Not ready (Lens 9 borderline missing on an AI
 * feature triggers the blocker rule).
 * ============================================================ */

const EPIC_NAME = "Adversary-Informed Vulnerability Prioritization";

interface ChatMessage {
  who: "spotter" | "you";
  body: string;
}

const BUILD_TRIGGER = "use the spotter to build an epic on adversary-informed vulnerability prioritization";

const BUILD_CHAT: ChatMessage[] = [
  {
    who: "spotter",
    body: "Let's start with the user. Who feels this most, and what's hard about it for them today?",
  },
  {
    who: "you",
    body: "vuln management engineers at enterprises. they patch the wrong things because CVSS doesn't know what's actually being exploited or what assets matter",
  },
  {
    who: "spotter",
    body: "Good. Now the harder question — what does it feel like to be one of those engineers on a Monday morning, looking at their patch queue?",
  },
  {
    who: "you",
    body: "they know the queue is wrong. half their time is spent recalibrating it by hand against threat intel and asset data. the calibration goes stale the moment they finish",
  },
  {
    who: "spotter",
    body: "Capturing that. Next: how is this solved today? Tooling, workarounds — what do these engineers already lean on?",
  },
];

interface DraftRow {
  name: string;
  line: string;
}

const BUILD_DRAFT: DraftRow[] = [
  {
    name: "The user and the problem",
    line: "VM engineers at security-mature enterprises. They patch the wrong things because CVSS-sorted backlogs miss what matters. Half their time is hand-recalibrating against threat intel and asset data. The work queue, not the score, is the goal.",
  },
  {
    name: "Competitive landscape",
    line: "Tenable VPR, Qualys TruRisk, Rapid7 Active Risk. All three score well in RFPs but underperform in adoption because scores live in a column users have to choose to sort by.",
  },
  {
    name: "What we're betting on",
    line: "The four-way join — first-party telemetry, threat intel, EDR-discovered inventory, agent-side configuration. Competitors have one or two; we have all four. 18–24 month window before parity.",
  },
  {
    name: "How we'll build it",
    line: "AI accelerated. LLM reasoning powers the explainability layer and the daily refresh logic. Static rules would force every customer to use the same weighting.",
  },
  {
    name: "What else changes",
    line: "Stub. Ticketing integration named; full cascade still to draft.",
  },
  {
    name: "Packaging and pricing",
    line: "Premium and Enterprise. Included in the existing VM module. No tier upsell. Pricing committee notified.",
  },
  {
    name: "Launch readiness",
    line: "GA tied to Q2 release. Documentation with migration guide. Field enablement. Launch blog and case study from a design partner.",
  },
  {
    name: "After it ships",
    line: "Adoption, patch SLA improvement, NPS. Quarterly review.",
  },
  {
    name: "Trust and governance",
    line: "Stub. Manual overrides with audit trail named; granular trust model and RBAC still to draft.",
  },
];

const ITERATE_TRIGGER = "iterate on this epic with the spotter — trust and governance";

const ITERATE_CHAT: ChatMessage[] = [
  {
    who: "you",
    body: "the trust and governance section is thin — what do i need to add",
  },
  {
    who: "spotter",
    body:
      "Read it. You've got the audit trail piece, which is the floor. The gap is the trust gradient — for a B2B AI feature, customers earn trust signal by signal, not in a binary toggle. Four places to push.",
  },
];

interface Suggestion {
  num: string;
  bold: string;
  text: string;
}

const ITERATE_SUGGESTIONS: Suggestion[] = [
  {
    num: "01",
    bold: "Describe the trust gradient.",
    text:
      "Customers don't trust the prioritized queue all at once. They trust it signal by signal: observation → recommendation → approve-to-execute → auto-execute. Spell out the four levels and the rules for moving between them.",
  },
  {
    num: "02",
    bold: "Name who can grant trust at each level.",
    text:
      "SOC manager? CISO? Tier 2 analyst? Map to real roles. RBAC isn't a launch-day afterthought for a feature that changes which patches get priority.",
  },
  {
    num: "03",
    bold: "Commit to transparency in writing.",
    text:
      "The Approach section mentions the explainability layer. Lens 9 needs the commitment: AI-driven priority changes show their reasoning, the team has read it, and the action is logged.",
  },
  {
    num: "04",
    bold: "Describe the audit trail surface.",
    text:
      "Every priority change — agent-driven or human-driven — produces an auditable record: who, what, when, why, evidence, outcome. Compliance teams will require this. The epic should name it.",
  },
];

const REVIEW_TRIGGER = "run the spotter on this epic";

const REVIEW_CHAT: ChatMessage[] = [
  { who: "you", body: "full review please" },
  {
    who: "spotter",
    body:
      "Done. Verdict: Not ready. Strong on the user and the problem. Trust and governance is missing on an AI feature, which triggers the blocker. Full report below.",
  },
];

type Verdict = "pass" | "work" | "miss";

interface LensRow {
  name: string;
  status: Verdict;
  label: string;
  weight: string;
  // light pattern for the marks column
  lights: ["w" | "r", "w" | "r", "w" | "r"];
}

const REVIEW_LENSES: LensRow[] = [
  { name: "The user and the problem", status: "pass", label: "Pass", weight: "12%", lights: ["w", "w", "w"] },
  { name: "Competitive landscape", status: "work", label: "Needs work", weight: "10%", lights: ["r", "w", "r"] },
  { name: "What we're betting on", status: "work", label: "Needs work", weight: "14%", lights: ["r", "w", "r"] },
  { name: "How we'll build it", status: "work", label: "Needs work", weight: "12%", lights: ["r", "w", "r"] },
  { name: "What else changes", status: "miss", label: "Missing", weight: "10%", lights: ["r", "r", "r"] },
  { name: "Packaging and pricing", status: "work", label: "Needs work", weight: "9%", lights: ["r", "w", "r"] },
  { name: "Launch readiness", status: "work", label: "Needs work", weight: "11%", lights: ["r", "w", "r"] },
  { name: "After it ships", status: "work", label: "Needs work", weight: "10%", lights: ["r", "w", "r"] },
  { name: "Trust and governance", status: "miss", label: "Missing · blocker", weight: "12%", lights: ["r", "r", "r"] },
];

interface LensDetail {
  name: string;
  status: Verdict;
  label: string;
  lights: ["w" | "r", "w" | "r", "w" | "r"];
  headline: string;
  bullets: string[];
}

const REVIEW_DETAILS: LensDetail[] = [
  {
    name: "Trust and governance",
    status: "miss",
    label: "Missing · triggers blocker",
    lights: ["r", "r", "r"],
    headline: "Manual overrides with an audit trail is the floor, not the trust story.",
    bullets: [
      "Describe the gradient: observation → recommendation → approve-to-execute → auto-execute. Customers earn trust signal by signal, not in a binary toggle.",
      "Name who in the customer org can grant trust at each level. SOC manager, CISO, Tier 2 analyst — map to real roles.",
      "Commit to transparency. AI-driven priority changes show their reasoning, and the team has read it. No silent autonomy.",
      "This is the lens that escalates the verdict. Even rough text here moves the epic out of Not ready.",
    ],
  },
  {
    name: "What else changes",
    status: "miss",
    label: "Missing",
    lights: ["r", "r", "r"],
    headline: "Ticketing is mentioned in passing. The rest of the cascade isn't named.",
    bullets: [
      "Name what else changes when the prioritized queue replaces CVSS-sorted as the default workflow. Dashboards, reports to leadership, notification flows, compliance exports.",
      "Adjacent areas where users will ask \"why isn't this also updated?\" — and the explicit answer to each.",
      "Side effects. A workflow change that improves VM but leaves change management or compliance reporting untouched might net negative.",
    ],
  },
  {
    name: "How we'll build it",
    status: "work",
    label: "Needs work",
    lights: ["r", "w", "r"],
    headline: "AI accelerated is clear. Skills-first and UI restraint are missing.",
    bullets: [
      "Address skills-first thinking. Could the prioritization capability be exposed as a skill or MCP tool so it lives beyond the UI and composes into other agentic workflows? The four-way join is reusable IP.",
      "A new \"Prioritized Queue view\" is a new screen. Test whether the prioritization could happen in the existing list view, replacing the sort order. New screens are the most expensive way to ship a capability.",
    ],
  },
  {
    name: "Launch readiness",
    status: "work",
    label: "Needs work",
    lights: ["r", "w", "r"],
    headline: "Marquee bullets hit. Rollback, sequencing, and PLG are missing.",
    bullets: [
      "Add the PLG layer. In-product guides, walkthroughs, tours. Customers who don't read the launch blog discover this in the product.",
      "Name the rollback. If the prioritized queue underperforms, can teams revert to CVSS-sorted easily? Migration guide is one-way.",
      "Sequencing details. Quiet beta, design-partner cohort, GA — what's the cadence and what are the gate criteria between waves?",
      "Calculators or proof tools. For a feature that changes how teams patch, a \"what would this have caught last quarter?\" lookback tool is high-leverage enablement.",
    ],
  },
];

/* ============================================================
 * Render helpers
 * ============================================================ */

function renderMarks(lights: ["w" | "r", "w" | "r", "w" | "r"], size: "sm" | "lg" = "sm"): string {
  const cls = size === "lg" ? "pv-marks pv-marks-lg" : "pv-marks";
  const dots = lights.map((c) => `<span class="pv-mark-${c}"></span>`).join("");
  return `<span class="${cls}">${dots}</span>`;
}

function renderChat(messages: ChatMessage[]): string {
  const rows = messages
    .map(
      (m) => `
      <div class="pv-msg pv-msg-${m.who}">
        <div class="pv-who">${m.who === "spotter" ? "Spotter" : "You"}</div>
        <div class="pv-body">${escape(m.body)}</div>
      </div>`,
    )
    .join("");
  return `<div class="pv-chat">${rows}</div>`;
}

function renderTrigger(cmd: string): string {
  return `
    <div class="pv-trigger">
      <span class="pv-trigger-label">Start with</span>
      <span class="pv-trigger-cmd">${escape(cmd)}</span>
    </div>`;
}

function renderBuildDeliverable(): string {
  const rows = BUILD_DRAFT.map(
    (r) => `
      <li class="pv-draft-row">
        <span class="pv-check">✓</span>
        <div>
          <p class="pv-draft-name">${escape(r.name)}</p>
          <p class="pv-draft-line">${escape(r.line)}</p>
        </div>
      </li>`,
  ).join("");

  return `
    <div class="pv-deliverable">
      <span class="pv-deliverable-badge">Deliverable · Draft</span>
      <p class="pv-deliverable-title">Working draft · ${escape(EPIC_NAME)} v0.1</p>
      <h3 class="pv-deliverable-h3">First-pass epic, organized by what a strong epic answers.</h3>
      <ul class="pv-draft-list">${rows}</ul>
    </div>`;
}

function renderIterateDeliverable(): string {
  const rows = ITERATE_SUGGESTIONS.map(
    (s) => `
      <li class="pv-suggest-row">
        <span class="pv-suggest-num">${s.num}</span>
        <p class="pv-suggest-text"><strong>${escape(s.bold)}</strong> ${escape(s.text)}</p>
      </li>`,
  ).join("");

  return `
    <div class="pv-deliverable">
      <span class="pv-deliverable-badge">Deliverable · Suggestions</span>
      <p class="pv-deliverable-title">Section · Trust and governance</p>
      <h3 class="pv-deliverable-h3">Four places to push.</h3>
      <ul class="pv-suggest-list">${rows}</ul>
    </div>`;
}

function renderReviewDeliverable(): string {
  const passCount = REVIEW_LENSES.filter((l) => l.status === "pass").length;
  const workCount = REVIEW_LENSES.filter((l) => l.status === "work").length;
  const missCount = REVIEW_LENSES.filter((l) => l.status === "miss").length;

  const lensRows = REVIEW_LENSES.map(
    (l) => `
      <li class="pv-lens-row">
        ${renderMarks(l.lights)}
        <span class="pv-lens-name">${escape(l.name)}</span>
        <span class="pv-lens-verdict pv-verdict-${l.status}">${escape(l.label)}</span>
        <span class="pv-lens-weight">${escape(l.weight)}</span>
      </li>`,
  ).join("");

  const detailRows = REVIEW_DETAILS.map(
    (d) => `
      <div class="pv-detail-row">
        <div class="pv-detail-head">
          ${renderMarks(d.lights, "lg")}
          <span class="pv-detail-name">${escape(d.name)}</span>
          <span class="pv-detail-verdict pv-verdict-${d.status}">${escape(d.label)}</span>
        </div>
        <p class="pv-detail-headline">"${escape(d.headline)}"</p>
        <p class="pv-detail-sublabel">You could strengthen this by</p>
        <ul class="pv-detail-bullets">
          ${d.bullets.map((b) => `<li>${escape(b)}</li>`).join("")}
        </ul>
      </div>`,
  ).join("");

  return `
    <div class="pv-deliverable">
      <span class="pv-deliverable-badge">Deliverable · Verdict</span>
      <p class="pv-deliverable-title">Epic · ${escape(EPIC_NAME)}</p>
      <h3 class="pv-deliverable-h3">Strong on the user and the problem. Trust and governance triggers the blocker.</h3>

      <div class="pv-summary">
        <div class="pv-summary-cell pv-summary-pass"><p class="pv-summary-k">Pass</p><p class="pv-summary-v">${passCount}</p></div>
        <div class="pv-summary-cell pv-summary-work"><p class="pv-summary-k">Needs work</p><p class="pv-summary-v">${workCount}</p></div>
        <div class="pv-summary-cell pv-summary-miss"><p class="pv-summary-k">Missing</p><p class="pv-summary-v">${missCount}</p></div>
      </div>

      <ul class="pv-lens-list">${lensRows}</ul>

      <div class="pv-detail-block">
        <p class="pv-detail-sublabel pv-detail-toplabel">Where to push next</p>
        ${detailRows}
      </div>
    </div>`;
}

/* ============================================================
 * Scoped CSS — Iron Log tokens inlined to keep this page
 * standalone. Matches the v3 mockup 1:1.
 * ============================================================ */

function previewCss(): string {
  return `
@import url("https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Merriweather:wght@300;400;700&family=JetBrains+Mono:wght@400;500;600&display=swap");

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #171513; color: #ebe5d8; font-family: 'Merriweather', Georgia, serif; }
a { color: inherit; }

.pv-page { background: #171513; color: #ebe5d8; font-family: 'Merriweather', Georgia, serif; min-height: 100vh; }

/* Top nav */
.pv-topnav { display: flex; justify-content: space-between; align-items: center; padding: 18px 56px; border-bottom: 1px solid #2a2622; }
.pv-lockup { font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 16px; letter-spacing: 0.08em; color: #ebe5d8; text-transform: uppercase; display: flex; align-items: center; gap: 9px; }
.pv-lockup-square { width: 7px; height: 7px; background: #a8211a; display: inline-block; }
.pv-nav { display: flex; gap: 28px; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: #a8a094; font-weight: 500; }
.pv-nav a { color: #a8a094; text-decoration: none; }
.pv-nav a.pv-nav-active { color: #ebe5d8; }
.pv-nav a:hover { color: #ebe5d8; }

/* Breadcrumb */
.pv-crumbs { padding: 24px 56px 0; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: #5a564f; }
.pv-crumbs a { color: #a8a094; text-decoration: none; }
.pv-crumbs a:hover { color: #ebe5d8; }
.pv-crumbs .pv-sep { color: #5a564f; margin: 0 10px; }

/* Hero */
.pv-hero { padding: 32px 56px 24px; text-align: center; }
.pv-eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.24em; text-transform: uppercase; color: #a8211a; margin: 0 0 28px; display: flex; align-items: center; justify-content: center; gap: 14px; }
.pv-dots { color: #a8211a; letter-spacing: 0.1em; }
.pv-hero h1 { font-family: 'Oswald', sans-serif; font-weight: 700; text-transform: uppercase; font-size: clamp(56px, 11vw, 108px); letter-spacing: -0.02em; line-height: 0.95; margin: 0 0 22px; color: #ebe5d8; }
.pv-hero h1 .pv-period { color: #a8211a; }
.pv-hero-sub { font-family: 'Oswald', sans-serif; font-weight: 400; font-size: 22px; letter-spacing: 0.04em; text-transform: uppercase; color: #a8a094; margin: 0 auto; max-width: 720px; }

/* Intro */
.pv-intro { padding: 36px 56px 32px; max-width: 780px; margin: 0 auto; text-align: center; }
.pv-intro p { font-family: 'Merriweather', Georgia, serif; font-size: 16px; line-height: 1.65; color: #a8a094; margin: 0; }
.pv-intro p strong { color: #ebe5d8; font-weight: 700; }

/* Sticky jump bar */
.pv-jumpbar { position: sticky; top: 0; background: #171513; border-top: 1px solid #2a2622; border-bottom: 1px solid #2a2622; padding: 14px 56px; display: flex; justify-content: center; gap: 36px; z-index: 10; }
.pv-jumpbar a { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase; color: #a8a094; text-decoration: none; display: flex; align-items: center; gap: 8px; }
.pv-jumpbar a .pv-jump-n { color: #5a564f; }
.pv-jumpbar a:hover { color: #ebe5d8; }
.pv-jumpbar .pv-jump-sep { color: #5a564f; font-family: 'JetBrains Mono', monospace; font-size: 11px; }

/* Phase section */
.pv-phase-section { padding: 56px 56px 56px; max-width: 980px; margin: 0 auto; scroll-margin-top: 60px; }
.pv-phase-header { margin-bottom: 32px; }
.pv-phase-stencil { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.24em; text-transform: uppercase; color: #a8211a; margin: 0 0 14px; }
.pv-phase-header h2 { font-family: 'Oswald', sans-serif; font-weight: 700; text-transform: uppercase; font-size: 48px; letter-spacing: 0.01em; line-height: 1; color: #ebe5d8; margin: 0 0 12px; }
.pv-phase-header h2 .pv-mode { color: #a8211a; }
.pv-phase-when { font-family: 'Oswald', sans-serif; font-weight: 500; text-transform: uppercase; font-size: 14px; letter-spacing: 0.06em; color: #a8a094; margin: 0 0 18px; }
.pv-phase-desc { font-family: 'Merriweather', Georgia, serif; font-size: 16px; line-height: 1.65; color: #a8a094; margin: 0; max-width: 780px; }

/* Sub-label */
.pv-sub-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 0.24em; text-transform: uppercase; color: #5a564f; margin: 32px 0 14px; }

/* Trigger panel */
.pv-trigger { display: grid; grid-template-columns: auto 1fr; gap: 18px; align-items: center; border-top: 1px solid #2a2622; border-bottom: 1px solid #2a2622; padding: 18px 0; margin-bottom: 20px; }
.pv-trigger-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.24em; text-transform: uppercase; color: #a8211a; }
.pv-trigger-cmd { font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #ebe5d8; }
.pv-trigger-cmd::before { content: '> '; color: #5a564f; }

/* Chat thread */
.pv-chat { border-top: 1px solid #2a2622; border-bottom: 1px solid #2a2622; padding: 8px 0; }
.pv-msg { display: grid; grid-template-columns: 80px 1fr; gap: 24px; padding: 18px 0; border-bottom: 1px solid #221f1c; }
.pv-msg:last-child { border-bottom: none; }
.pv-who { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: #5a564f; padding-top: 3px; }
.pv-msg-spotter .pv-who { color: #a8211a; }
.pv-msg-you .pv-who { color: #a8a094; }
.pv-body { font-family: 'Merriweather', Georgia, serif; font-size: 15px; line-height: 1.65; color: #ebe5d8; }
.pv-msg-you .pv-body { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #a8a094; }

/* Deliverable card */
.pv-deliverable { background: #1f1c19; border: 1px solid #2a2622; padding: 32px; margin: 24px 0 0; position: relative; }
.pv-deliverable-badge { position: absolute; top: -1px; left: -1px; background: #a8211a; color: #ebe5d8; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; padding: 6px 14px; }
.pv-deliverable-title { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; color: #5a564f; margin: 14px 0 6px; }
.pv-deliverable-h3 { font-family: 'Oswald', sans-serif; font-weight: 600; text-transform: uppercase; font-size: 22px; letter-spacing: 0.02em; color: #ebe5d8; margin: 0 0 18px; }

/* Build draft list */
.pv-draft-list { margin: 0; padding: 0; list-style: none; border-top: 1px solid #2a2622; }
.pv-draft-row { display: grid; grid-template-columns: 20px 1fr; gap: 14px; align-items: start; padding: 14px 0; border-bottom: 1px solid #2a2622; }
.pv-check { font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #7a8b3a; font-weight: 600; line-height: 1.3; }
.pv-draft-name { font-family: 'Oswald', sans-serif; font-weight: 600; text-transform: uppercase; font-size: 13px; letter-spacing: 0.04em; color: #ebe5d8; margin: 0 0 6px; }
.pv-draft-line { font-family: 'Merriweather', Georgia, serif; font-size: 14px; line-height: 1.55; color: #a8a094; margin: 0; }

/* Iterate suggestions */
.pv-suggest-list { margin: 0; padding: 0; list-style: none; }
.pv-suggest-row { display: grid; grid-template-columns: auto 1fr; gap: 14px; padding: 14px 0; border-top: 1px solid #2a2622; align-items: start; }
.pv-suggest-row:first-child { border-top: none; }
.pv-suggest-num { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: #a8211a; padding-top: 2px; }
.pv-suggest-text { font-family: 'Merriweather', Georgia, serif; font-size: 15px; line-height: 1.6; color: #ebe5d8; margin: 0; }
.pv-suggest-text strong { color: #ebe5d8; font-weight: 700; }

/* Review summary stats */
.pv-summary { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0; border-top: 1px solid #2a2622; border-bottom: 1px solid #2a2622; margin: 8px 0 24px; }
.pv-summary-cell { padding: 18px 22px; border-right: 1px solid #2a2622; }
.pv-summary-cell:last-child { border-right: none; }
.pv-summary-k { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase; color: #5a564f; margin: 0 0 6px; }
.pv-summary-v { font-family: 'Oswald', sans-serif; font-weight: 600; font-size: 22px; letter-spacing: 0.02em; text-transform: uppercase; margin: 0; }
.pv-summary-pass .pv-summary-v { color: #ebe5d8; }
.pv-summary-work .pv-summary-v { color: #a8a094; }
.pv-summary-miss .pv-summary-v { color: #a8211a; }

/* Lens list (review table) */
.pv-lens-list { margin: 0; padding: 0; list-style: none; border-top: 1px solid #2a2622; }
.pv-lens-row { display: grid; grid-template-columns: 32px 1fr 130px 56px; gap: 16px; align-items: center; padding: 14px 0; border-bottom: 1px solid #2a2622; }
.pv-lens-name { font-family: 'Oswald', sans-serif; font-weight: 500; text-transform: uppercase; font-size: 14px; letter-spacing: 0.04em; color: #ebe5d8; }
.pv-lens-verdict { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; text-align: right; }
.pv-lens-weight { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 0.12em; text-transform: uppercase; color: #5a564f; text-align: right; }
.pv-verdict-pass { color: #7a8b3a; }
.pv-verdict-work { color: #a8a094; }
.pv-verdict-miss { color: #a8211a; }

/* Marks (the lights) */
.pv-marks { display: inline-flex; gap: 3px; }
.pv-marks span { width: 8px; height: 8px; border: 1px solid #2a2622; display: inline-block; }
.pv-marks-lg span { width: 10px; height: 10px; }
.pv-mark-w { background: #ebe5d8; }
.pv-mark-r { background: #a8211a; }

/* Detail block */
.pv-detail-block { padding: 24px 0 0; border-top: 1px solid #2a2622; margin-top: 24px; }
.pv-detail-row { padding: 22px 0; border-bottom: 1px solid #2a2622; }
.pv-detail-row:last-child { border-bottom: none; }
.pv-detail-head { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; flex-wrap: wrap; }
.pv-detail-name { font-family: 'Oswald', sans-serif; font-weight: 600; text-transform: uppercase; font-size: 18px; letter-spacing: 0.04em; color: #ebe5d8; }
.pv-detail-verdict { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; }
.pv-detail-headline { font-family: 'Merriweather', Georgia, serif; font-style: italic; font-size: 15px; line-height: 1.55; color: #ebe5d8; margin: 0 0 14px; }
.pv-detail-sublabel { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase; color: #5a564f; margin: 8px 0 8px; }
.pv-detail-toplabel { margin: 0 0 14px; }
.pv-detail-bullets { margin: 0; padding: 0 0 0 18px; list-style: disc; color: #a8a094; }
.pv-detail-bullets li { font-family: 'Merriweather', Georgia, serif; font-size: 14px; line-height: 1.6; color: #a8a094; margin-bottom: 6px; }

/* Divider */
.pv-divider { border: none; border-top: 1px dashed #221f1c; margin: 0 56px; }

/* Back CTA */
.pv-cta-back { padding: 48px 56px 16px; text-align: center; }
.pv-cta-back a { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: #ebe5d8; text-decoration: none; border-bottom: 1px solid #a8211a; padding-bottom: 4px; }
.pv-cta-back a:hover { color: #a8211a; }

/* Closer */
.pv-closer { padding: 48px 56px; text-align: center; border-top: 1px solid #2a2622; margin-top: 32px; }
.pv-closer p { font-family: 'Oswald', sans-serif; font-weight: 500; text-transform: uppercase; font-size: 22px; letter-spacing: 0.06em; color: #ebe5d8; margin: 0; }
.pv-closer p .pv-accent { color: #a8211a; }

/* Footer */
.pv-footer { padding: 28px 56px; border-top: 1px solid #2a2622; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; color: #5a564f; display: flex; justify-content: space-between; }
.pv-footer a { color: #a8a094; text-decoration: none; }
.pv-footer a:hover { color: #ebe5d8; }

/* Selection + focus */
::selection { background: #5e1e1c; color: #ebe5d8; }
:focus-visible { outline: 2px solid #a8211a; outline-offset: 2px; }

/* Responsive */
@media (max-width: 720px) {
  .pv-topnav { padding: 14px 24px; flex-direction: column; gap: 14px; align-items: flex-start; }
  .pv-nav { flex-wrap: wrap; gap: 16px; }
  .pv-crumbs, .pv-hero, .pv-intro, .pv-jumpbar, .pv-phase-section, .pv-cta-back, .pv-closer, .pv-footer { padding-left: 24px; padding-right: 24px; }
  .pv-divider { margin-left: 24px; margin-right: 24px; }
  .pv-deliverable { padding: 24px 20px; }
  .pv-jumpbar { gap: 18px; }
  .pv-lens-row { grid-template-columns: 28px 1fr; row-gap: 4px; }
  .pv-lens-verdict, .pv-lens-weight { grid-column: 2; text-align: left; }
  .pv-footer { flex-direction: column; gap: 8px; }
}
`;
}

/* ============================================================
 * Page render
 * ============================================================ */

export function renderPreview(args: PreviewArgs): string {
  const { origin, githubUrl } = args;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#171513">
  <title>The Spotter · Walkthrough</title>
  <meta name="description" content="One synthetic epic taken through all three Spotter phases — Build, Iterate, Review. The actual output of running the v0.2.0 skill against a sample epic.">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <style>${previewCss()}</style>
</head>
<body>
  <div class="pv-page">

    <header class="pv-topnav">
      <div class="pv-lockup">MISSION <span class="pv-lockup-square"></span> BUILT</div>
      <nav class="pv-nav">
        <a href="https://missionbuilt.io/">The Book</a>
        <a href="https://missionbuilt.io/chapters">Chapters</a>
        <a class="pv-nav-active" href="https://missionbuilt.io/loadout">The Loadout</a>
        <a href="https://missionbuilt.io/about">About</a>
        <a href="${escape(githubUrl)}">Source</a>
      </nav>
    </header>

    <div class="pv-crumbs">
      <a href="https://missionbuilt.io/loadout">The Loadout</a><span class="pv-sep">/</span><a href="https://missionbuilt.io/loadout/spotter">The Spotter</a><span class="pv-sep">/</span>Sample
    </div>

    <section class="pv-hero">
      <p class="pv-eyebrow"><span class="pv-dots">▮▮▮</span><span>Spotter MCP · Worked sample</span><span class="pv-dots">▮▮▮</span></p>
      <h1>Walkthrough<span class="pv-period">.</span></h1>
      <p class="pv-hero-sub">All three phases on one synthetic epic.</p>
    </section>

    <div class="pv-intro">
      <p>One epic — <strong>${escape(EPIC_NAME)}</strong> — taken through each of the Spotter's three phases. Real output from the v0.2.0 skill, not a mockup.</p>
    </div>

    <nav class="pv-jumpbar" aria-label="Phase navigation">
      <a href="#build"><span class="pv-jump-n">01</span> Build</a>
      <span class="pv-jump-sep">·</span>
      <a href="#iterate"><span class="pv-jump-n">02</span> Iterate</a>
      <span class="pv-jump-sep">·</span>
      <a href="#review"><span class="pv-jump-n">03</span> Review</a>
    </nav>

    <section id="build" class="pv-phase-section">
      <header class="pv-phase-header">
        <p class="pv-phase-stencil">Phase 01</p>
        <h2><span class="pv-mode">Build.</span></h2>
        <p class="pv-phase-when">Starting from blank</p>
        <p class="pv-phase-desc">You have an initiative and a blank page. The Spotter walks you through the questions a strong epic answers, one at a time, and turns your answers into a working draft.</p>
      </header>

      ${renderTrigger(BUILD_TRIGGER)}

      <p class="pv-sub-label">Conversation</p>
      ${renderChat(BUILD_CHAT)}

      ${renderBuildDeliverable()}
    </section>

    <hr class="pv-divider">

    <section id="iterate" class="pv-phase-section">
      <header class="pv-phase-header">
        <p class="pv-phase-stencil">Phase 02</p>
        <h2><span class="pv-mode">Iterate.</span></h2>
        <p class="pv-phase-when">Working a draft</p>
        <p class="pv-phase-desc">You have a draft and one section is weaker than the rest. Tell the Spotter which one, and you'll get specific suggestions for how to strengthen it.</p>
      </header>

      ${renderTrigger(ITERATE_TRIGGER)}

      <p class="pv-sub-label">Conversation</p>
      ${renderChat(ITERATE_CHAT)}

      ${renderIterateDeliverable()}
    </section>

    <hr class="pv-divider">

    <section id="review" class="pv-phase-section">
      <header class="pv-phase-header">
        <p class="pv-phase-stencil">Phase 03</p>
        <h2><span class="pv-mode">Review.</span></h2>
        <p class="pv-phase-when">Before stakeholders see it</p>
        <p class="pv-phase-desc">The epic is complete. The Spotter walks all nine sections, calls a verdict on each, and gives you a headline plus suggestions where strengthening is worth your time.</p>
      </header>

      ${renderTrigger(REVIEW_TRIGGER)}

      <p class="pv-sub-label">Conversation</p>
      ${renderChat(REVIEW_CHAT)}

      ${renderReviewDeliverable()}

      <div class="pv-cta-back">
        <a href="https://missionbuilt.io/loadout/spotter">← Back to The Spotter</a>
      </div>
    </section>

    <div class="pv-closer">
      <p>A spotter lifts the lifter. <span class="pv-accent">Not the bar.</span></p>
    </div>

    <footer class="pv-footer">
      <span>Real strength is lifting others</span>
      <span><a href="${escape(githubUrl)}">github.com/missionbuilt/loadout</a></span>
    </footer>

  </div>
</body>
</html>`;
}
