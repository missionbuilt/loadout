/**
 * /preview route — renders a worked Warmup walkthrough.
 *
 * Shows The Warmup running end-to-end: setup flow, a generated brief, and
 * source management. All content is real skill output applied to a synthetic
 * Product Leader profile (cloud security startup, financial services vertical).
 *
 * Design follows the Iron Log system: warm charcoal base, chalk text, oxblood
 * as the single accent, army green for the Live status mark only.
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

// ---- SYNTHETIC PROFILE ----
// Product Leader mode. Cloud security startup, financial services vertical.
// Generic enough to be universally readable. No real company names.

const PROFILE_NAME = "a cloud security startup";
const PROFILE_SECTOR = "Financial Services";
const PROFILE_MODE = "Product Leader";

// ---- SETUP PHASE ----

interface ChatMsg {
  who: "warmup" | "you";
  body: string;
}

const SETUP_TRIGGER = "warmup setup";

const SETUP_CHAT: ChatMsg[] = [
  {
    who: "warmup",
    body: "Which mode fits you best? CISO Mode is built for security executives — threat intel, CVEs, sector advisories. Product Leader Mode is built for PMs and CPOs — competitor moves, market signals, AI releases. Custom Mode is for anything else. What does your morning look like?",
  },
  {
    who: "you",
    body: "product leader. fintech security startup. want competitor moves, funding rounds, AI tooling",
  },
  {
    who: "warmup",
    body: "Product Leader Mode. A few quick questions. What's your product area — what specifically are you building?",
  },
  {
    who: "you",
    body: "cloud security platform. compliance automation, threat detection for financial services",
  },
  {
    who: "warmup",
    body: "Got it. Who are you watching? Name your main competitors — 3 to 6 is enough to start.",
  },
  {
    who: "you",
    body: "Wiz, Orca Security, Lacework, Snyk, Datadog Security",
  },
  {
    who: "warmup",
    body: "Building your source suite now. I'll pull from Tier 1 regulatory sources, analyst firms, and the competitor newsrooms. One more: any specific people you want to track — execs, analysts, investors in your space?",
  },
  {
    who: "you",
    body: "not for now",
  },
];

// ---- SAMPLE BRIEF ----

interface BriefSection {
  id: string;
  label: string;
  items: { headline: string; source: string; tier: string; detail: string }[];
}

const BRIEF_DATE = "Friday, May 15, 2026";
const BRIEF_WINDOW = "Last 48 hours";

const BRIEF_SECTIONS: BriefSection[] = [
  {
    id: "company",
    label: "Company Intel",
    items: [
      {
        headline: "No new SEC filings or press releases in the last 48 hours.",
        source: "SEC EDGAR, Company Newsroom",
        tier: "Tier 1",
        detail: "Clean window. Nothing to flag before the morning standup.",
      },
    ],
  },
  {
    id: "competitors",
    label: "Competitor Moves",
    items: [
      {
        headline: "Wiz expands platform to cover AI workload security — new capability announced at RSA.",
        source: "Wiz Newsroom",
        tier: "Tier 4",
        detail: "Coverage includes model inference endpoints and training pipelines. Positioned as an extension of existing CNAPP. Watch for customer adoption signals in G2 reviews over the next 30 days.",
      },
      {
        headline: "Snyk raises $150M Series G at $7.4B valuation, accelerates into enterprise compliance.",
        source: "TechCrunch, Crunchbase",
        tier: "Tier 3",
        detail: "Round led by existing investors. Stated use: enterprise expansion and regulatory compliance tooling. Direct pressure on compliance automation positioning.",
      },
      {
        headline: "Lacework lays off 20% of workforce, consolidates product lines.",
        source: "The Information, BleepingComputer",
        tier: "Tier 3",
        detail: "Second reduction in 18 months. Platform consolidation suggests they're narrowing to core CNAPP. Potential opportunity to pick up displaced customers.",
      },
    ],
  },
  {
    id: "ai",
    label: "AI and Tooling",
    items: [
      {
        headline: "Anthropic releases Claude 4 with extended context and improved code reasoning.",
        source: "Anthropic",
        tier: "Tier 2",
        detail: "200K context window now standard. Relevant to detection-rule generation and compliance doc summarization use cases.",
      },
      {
        headline: "GitHub Copilot adds security vulnerability scanning to pull request reviews.",
        source: "GitHub Blog",
        tier: "Tier 2",
        detail: "Now flags OWASP Top 10 issues inline. Could shift developer expectation of where security feedback lives — worth watching for positioning impact.",
      },
    ],
  },
  {
    id: "market",
    label: "Market and Funding",
    items: [
      {
        headline: "Gartner publishes updated CNAPP Market Guide — consolidation trend accelerating.",
        source: "Gartner",
        tier: "Tier 2",
        detail: "Report cites 40% of enterprises planning to reduce security vendor count by 2026. Platforms with integrated compliance and detection favored over point solutions. Useful data point for enterprise sales conversations.",
      },
      {
        headline: "DORA compliance deadline extended 6 months for Tier 2 financial institutions.",
        source: "European Banking Authority",
        tier: "Tier 1",
        detail: "New deadline: January 2027. Extends the window for compliance automation selling motion in EU-headquartered financial services accounts.",
      },
    ],
  },
  {
    id: "social",
    label: "Social Signal",
    items: [
      {
        headline: "Security engineers on Hacker News debating whether CNAPP vendors oversell detection accuracy.",
        source: "Hacker News (YC)",
        tier: "Tier 3",
        detail: "Thread has 140 comments. Consensus: false positive rate is the #1 evaluation criterion. Unverified community signal — but consistent with what we hear in customer calls.",
      },
    ],
  },
];

// ---- SAFETY SCAN ----

interface SafetyDomain {
  domain: string;
  verdict: "Clean";
  urls: number;
}

const SAFETY_DOMAINS: SafetyDomain[] = [
  { domain: "wiz.io", verdict: "Clean", urls: 1 },
  { domain: "techcrunch.com", verdict: "Clean", urls: 2 },
  { domain: "crunchbase.com", verdict: "Clean", urls: 1 },
  { domain: "theinformation.com", verdict: "Clean", urls: 1 },
  { domain: "bleepingcomputer.com", verdict: "Clean", urls: 1 },
  { domain: "anthropic.com", verdict: "Clean", urls: 1 },
  { domain: "github.blog", verdict: "Clean", urls: 1 },
  { domain: "gartner.com", verdict: "Clean", urls: 1 },
  { domain: "eba.europa.eu", verdict: "Clean", urls: 1 },
  { domain: "news.ycombinator.com", verdict: "Clean", urls: 1 },
];

export function renderPreview(args: PreviewArgs): string {
  const { origin, githubUrl } = args;

  const setupChatHtml = SETUP_CHAT.map((msg) => {
    const cls = msg.who === "you" ? "mb-chat-msg mb-chat-msg-user" : "mb-chat-msg mb-chat-msg-spotter";
    return `<div class="${cls}">${escape(msg.body)}</div>`;
  }).join("\n");

  const briefSectionsHtml = BRIEF_SECTIONS.map((sec) => {
    const itemsHtml = sec.items.map((item) => `
      <div class="pv-brief-item">
        <div class="pv-item-headline">${escape(item.headline)}</div>
        <div class="pv-item-meta">
          <span class="pv-item-source">${escape(item.source)}</span>
          <span class="pv-item-tier">${escape(item.tier)}</span>
        </div>
        <div class="pv-item-detail">${escape(item.detail)}</div>
      </div>`).join("\n");

    return `
      <div class="pv-brief-section" id="section-${sec.id}">
        <div class="pv-section-label">${escape(sec.label)}</div>
        ${itemsHtml}
      </div>`;
  }).join("\n");

  const safetyHtml = SAFETY_DOMAINS.map((d) => `
    <div class="pv-safety-row">
      <span class="pv-safety-check">✓</span>
      <span class="pv-safety-domain">${escape(d.domain)}</span>
      ${d.urls > 1 ? `<span class="pv-safety-urls">${d.urls} urls</span>` : ""}
      <span class="pv-safety-verdict">Clean</span>
    </div>`).join("\n");

  const totalUrls = SAFETY_DOMAINS.reduce((sum, d) => sum + d.urls, 0);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#171513">
  <title>The Warmup · Walkthrough</title>
  <meta name="description" content="A worked walkthrough of The Warmup — setup, brief, and source management on a synthetic Product Leader profile.">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="manifest" href="/site.webmanifest">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Merriweather:ital,wght@0,300;0,400;0,700;1,300;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    /* ---- Iron Log base (from design.ts tokens) ---- */
    :root {
      --bg: #171513;
      --panel: #1f1c19;
      --rule: #2a2622;
      --rule-soft: #221f1c;
      --chalk: #ebe5d8;
      --chalk-dim: #a8a094;
      --chalk-faint: #5a564f;
      --blood: #a8211a;
      --army: #7a8b3a;
      --font-display: 'Oswald', 'Archivo Narrow', sans-serif;
      --font-serif: 'Merriweather', Georgia, serif;
      --font-mono: 'JetBrains Mono', ui-monospace, monospace;
      --pad: 56px;
    }
    *, *::before, *::after { box-sizing: border-box; }
    html { background: var(--bg); scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--chalk);
      font-family: var(--font-serif);
      font-size: 16px;
      line-height: 1.65;
      -webkit-font-smoothing: antialiased;
    }
    a { color: var(--chalk-dim); text-decoration: none; }
    a:hover { color: var(--chalk); }

    /* ---- Nav ---- */
    .pv-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px var(--pad);
      border-bottom: 1px solid var(--rule);
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }
    .pv-nav-mark { color: var(--chalk); }
    .pv-nav-mark span { color: var(--blood); }
    .pv-nav-links { display: flex; gap: 24px; color: var(--chalk-faint); }

    /* ---- Breadcrumb ---- */
    .pv-crumb {
      padding: 16px var(--pad) 0;
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--chalk-faint);
    }
    .pv-crumb a { color: var(--chalk-dim); }
    .pv-crumb a:hover { color: var(--chalk); }

    /* ---- Hero ---- */
    .pv-hero {
      padding: 40px var(--pad) 28px;
      text-align: center;
    }
    .pv-eyebrow {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.24em;
      color: var(--blood);
      text-transform: uppercase;
      margin: 0 0 18px;
    }
    .pv-eyebrow .dots { letter-spacing: 0.04em; opacity: 0.65; }
    .pv-h1 {
      margin: 0;
      font-family: var(--font-display);
      font-weight: 700;
      font-size: clamp(48px, 9vw, 96px);
      line-height: 0.95;
      letter-spacing: -0.02em;
      color: var(--chalk);
      text-transform: uppercase;
    }
    .pv-h1 .dot { color: var(--blood); }
    .pv-subtitle {
      margin: 20px auto 0;
      max-width: 680px;
      font-family: var(--font-display);
      font-weight: 400;
      font-size: clamp(14px, 2vw, 20px);
      color: var(--chalk-dim);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .pv-profile-pill {
      display: inline-block;
      margin-top: 18px;
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--chalk-faint);
      border: 1px solid var(--rule);
      padding: 4px 12px;
    }

    /* ---- Jump bar ---- */
    .pv-jump {
      display: flex;
      gap: 0;
      margin: 0 var(--pad);
      border-top: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }
    .pv-jump a {
      padding: 12px 24px;
      color: var(--chalk-faint);
      border-right: 1px solid var(--rule);
      transition: color 120ms;
    }
    .pv-jump a:hover { color: var(--chalk); }
    .pv-jump a:last-child { border-right: none; }

    /* ---- Phase blocks ---- */
    .pv-phase {
      padding: 56px var(--pad) 0;
      max-width: 1080px;
    }
    .pv-phase-eyebrow {
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: var(--chalk-faint);
      margin: 0 0 14px;
    }
    .pv-phase-h2 {
      margin: 0 0 6px;
      font-family: var(--font-display);
      font-weight: 700;
      font-size: clamp(32px, 5vw, 52px);
      line-height: 0.95;
      letter-spacing: -0.01em;
      text-transform: uppercase;
    }
    .pv-phase-h2 .dot { color: var(--blood); }
    .pv-phase-when {
      margin: 0 0 20px;
      font-family: var(--font-display);
      font-weight: 500;
      font-size: 13px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--blood);
    }
    .pv-phase-desc {
      max-width: 760px;
      font-family: var(--font-serif);
      font-size: 17px;
      line-height: 1.65;
      color: var(--chalk-dim);
      margin: 0 0 28px;
    }

    /* ---- Trigger bar ---- */
    .pv-trigger {
      margin: 0 0 24px;
      padding: 14px 18px;
      border-top: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--chalk-faint);
      letter-spacing: 0.06em;
    }
    .pv-trigger-label {
      font-size: 10px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--chalk-faint);
      margin-bottom: 6px;
    }
    .pv-trigger-cmd { color: var(--chalk); }

    /* ---- Chat thread ---- */
    .pv-chat { display: flex; flex-direction: column; gap: 10px; max-width: 680px; margin-bottom: 32px; }
    .pv-msg {
      padding: 11px 15px;
      font-family: var(--font-serif);
      font-size: 15px;
      line-height: 1.55;
      max-width: 90%;
    }
    .pv-msg-warmup {
      align-self: flex-start;
      background: var(--panel);
      border: 1px solid var(--rule);
      color: var(--chalk);
    }
    .pv-msg-you {
      align-self: flex-end;
      background: rgba(168,33,26,0.10);
      border: 1px solid rgba(168,33,26,0.28);
      color: var(--chalk-dim);
      font-family: var(--font-mono);
      font-size: 13px;
    }

    /* ---- Deliverable card ---- */
    .pv-deliverable {
      position: relative;
      padding: 32px 28px 24px;
      background: var(--panel);
      border: 1px solid var(--rule);
      margin-bottom: 8px;
    }
    .pv-deliverable-badge {
      position: absolute;
      top: 0;
      right: 0;
      background: var(--blood);
      color: var(--chalk);
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      padding: 5px 12px;
    }
    .pv-deliverable-label {
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--chalk-faint);
      margin: 0 0 10px;
    }
    .pv-deliverable-title {
      font-family: var(--font-display);
      font-weight: 600;
      font-size: 22px;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      color: var(--chalk);
      margin: 0 0 6px;
    }
    .pv-deliverable-meta {
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--chalk-dim);
      margin: 0 0 24px;
    }

    /* ---- Brief sections ---- */
    .pv-brief-section {
      margin-bottom: 24px;
      border-top: 1px solid var(--rule);
      padding-top: 18px;
    }
    .pv-section-label {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--blood);
      margin: 0 0 14px;
    }
    .pv-brief-item { margin-bottom: 18px; }
    .pv-item-headline {
      font-family: var(--font-display);
      font-weight: 500;
      font-size: 16px;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      color: var(--chalk);
      margin: 0 0 6px;
    }
    .pv-item-meta {
      display: flex;
      gap: 14px;
      margin-bottom: 6px;
    }
    .pv-item-source {
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--chalk-faint);
    }
    .pv-item-tier {
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--army);
    }
    .pv-item-detail {
      font-family: var(--font-serif);
      font-size: 14px;
      line-height: 1.6;
      color: var(--chalk-dim);
    }

    /* ---- Safety panel ---- */
    .pv-safety {
      margin-top: 24px;
      border-top: 1px solid var(--rule);
      padding-top: 18px;
    }
    .pv-safety-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 14px;
    }
    .pv-safety-title {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--chalk-faint);
    }
    .pv-safety-summary {
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--army);
    }
    .pv-safety-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 7px 0;
      border-top: 1px solid var(--rule-soft);
      font-family: var(--font-mono);
      font-size: 11px;
    }
    .pv-safety-check { color: var(--army); flex-shrink: 0; }
    .pv-safety-domain { color: var(--chalk); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .pv-safety-urls { color: var(--chalk-faint); font-size: 10px; flex-shrink: 0; }
    .pv-safety-verdict { color: var(--army); letter-spacing: 0.14em; text-transform: uppercase; font-size: 10px; flex-shrink: 0; }

    /* ---- Dashed divider ---- */
    .pv-dashed {
      margin: 56px var(--pad);
      border: none;
      border-top: 1px dashed var(--rule-soft);
    }

    /* ---- Closer ---- */
    .pv-closer {
      margin-top: 56px;
      padding: 48px var(--pad);
      border-top: 1px solid var(--rule);
      text-align: center;
    }
    .pv-closer p {
      margin: 0;
      font-family: var(--font-display);
      font-weight: 500;
      font-size: 22px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--chalk);
    }
    .pv-closer strong { font-weight: 500; color: var(--blood); }

    /* ---- Footer ---- */
    .pv-foot {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      padding: 22px var(--pad) 40px;
      border-top: 1px solid var(--rule);
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--chalk-faint);
    }
    .pv-foot a { color: var(--chalk-dim); }
    .pv-foot a:hover { color: var(--chalk); }

    /* ---- Responsive ---- */
    @media (max-width: 720px) {
      :root { --pad: 24px; }
      .pv-jump { flex-wrap: wrap; }
      .pv-jump a { font-size: 10px; padding: 10px 16px; }
      .pv-foot { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>

  <!-- NAV -->
  <nav class="pv-nav">
    <span class="pv-nav-mark">MISSION <span>▪</span> BUILT</span>
    <div class="pv-nav-links">
      <a href="https://missionbuilt.io/">The Book</a>
      <a href="https://missionbuilt.io/loadout">The Loadout</a>
      <a href="${githubUrl}">Source</a>
    </div>
  </nav>

  <!-- BREADCRUMB -->
  <nav class="pv-crumb" aria-label="Breadcrumb">
    <a href="https://missionbuilt.io/loadout">The Loadout</a> /
    <a href="https://missionbuilt.io/loadout/warmup">The Warmup</a> /
    <span>Walkthrough</span>
  </nav>

  <!-- HERO -->
  <section class="pv-hero">
    <p class="pv-eyebrow">
      <span class="dots">▮▮▮</span>
      The Warmup · Worked sample
      <span class="dots">▮▮▮</span>
    </p>
    <h1 class="pv-h1">Walkthrough<span class="dot">.</span></h1>
    <p class="pv-subtitle">Setup, brief, and source management on one synthetic profile.</p>
    <span class="pv-profile-pill">${escape(PROFILE_MODE)} mode · ${escape(PROFILE_SECTOR)} · ${escape(PROFILE_NAME)}</span>
  </section>

  <!-- JUMP BAR -->
  <nav class="pv-jump" aria-label="Phase navigation">
    <a href="#setup">01 Setup</a>
    <a href="#brief">02 Run the brief</a>
    <a href="#config">03 Manage sources</a>
  </nav>

  <!-- ===== PHASE 01 — SETUP ===== -->
  <section class="pv-phase" id="setup">
    <p class="pv-phase-eyebrow">Phase 01</p>
    <h2 class="pv-phase-h2">Setup<span class="dot">.</span></h2>
    <p class="pv-phase-when">First run</p>
    <p class="pv-phase-desc">
      You have never run the Warmup before. It walks you through four questions,
      builds your source suite, shows it for review, and saves your config to
      <code style="font-family:var(--font-mono);font-size:0.9em;color:var(--chalk)">WARMUP.md</code>
      at your project root.
    </p>

    <div class="pv-trigger">
      <div class="pv-trigger-label">Start with</div>
      <span class="pv-trigger-cmd">${escape(SETUP_TRIGGER)}</span>
    </div>

    <div class="pv-chat">
      ${setupChatHtml}
    </div>

    <div class="pv-deliverable">
      <div class="pv-deliverable-badge">Deliverable · Config</div>
      <p class="pv-deliverable-label">WARMUP.md · saved to project root</p>
      <div class="pv-deliverable-title">Source suite ready. 22 active sources across 4 tiers.</div>
      <p class="pv-deliverable-meta">Product Leader · Financial Services · ${escape(PROFILE_NAME)}</p>

      <div style="font-family:var(--font-mono);font-size:12px;color:var(--chalk-dim);line-height:1.8;border-top:1px solid var(--rule);padding-top:16px;">
        <div style="color:var(--chalk-faint);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:10px;">Tier 1 — Authoritative</div>
        <div>SEC EDGAR · CISA Alerts · NVD CVE · Crunchbase</div>
        <div style="color:var(--chalk-faint);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;margin:14px 0 10px;">Tier 2 — Research</div>
        <div>Gartner · Forrester · CB Insights · a16z · Anthropic · OpenAI Blog · Google DeepMind · arXiv cs.AI</div>
        <div style="color:var(--chalk-faint);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;margin:14px 0 10px;">Tier 3 — News</div>
        <div>TechCrunch · The Verge · BleepingComputer · SecurityWeek · Wired · Hacker News (YC)</div>
        <div style="color:var(--chalk-faint);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;margin:14px 0 10px;">Tier 4 — Vendor Intel</div>
        <div>Wiz Newsroom · Orca Blog · Lacework Blog · Snyk Blog · Datadog Blog</div>
      </div>
    </div>
  </section>

  <hr class="pv-dashed">

  <!-- ===== PHASE 02 — RUN THE BRIEF ===== -->
  <section class="pv-phase" id="brief">
    <p class="pv-phase-eyebrow">Phase 02</p>
    <h2 class="pv-phase-h2">Run the brief<span class="dot">.</span></h2>
    <p class="pv-phase-when">Each morning</p>
    <p class="pv-phase-desc">
      Config is saved. Now you run it. The Warmup reads your sources,
      runs the link safety verification, synthesizes the five sections, and
      delivers a live HTML document. One line in chat. The brief is the artifact.
    </p>

    <div class="pv-trigger">
      <div class="pv-trigger-label">Start with</div>
      <span class="pv-trigger-cmd">run warmup</span>
      &nbsp;<span style="color:var(--chalk-faint);font-size:11px">or</span>&nbsp;
      <span class="pv-trigger-cmd">start my warmup</span>
    </div>

    <div class="pv-deliverable">
      <div class="pv-deliverable-badge">Deliverable · Brief</div>
      <p class="pv-deliverable-label">Product Leader · ${escape(BRIEF_DATE)} · ${escape(BRIEF_WINDOW)}</p>
      <div class="pv-deliverable-title">5 sections · 22 sources · 10 domains scanned · all clear</div>
      <p class="pv-deliverable-meta">${escape(PROFILE_NAME)} · ${escape(PROFILE_SECTOR)}</p>

      ${briefSectionsHtml}

      <!-- Safety panel -->
      <div class="pv-safety">
        <div class="pv-safety-header">
          <span class="pv-safety-title">Link Safety Verification</span>
          <span class="pv-safety-summary">${SAFETY_DOMAINS.length} domains · ${totalUrls} urls · 0 flagged</span>
        </div>
        ${safetyHtml}
      </div>
    </div>
  </section>

  <hr class="pv-dashed">

  <!-- ===== PHASE 03 — MANAGE SOURCES ===== -->
  <section class="pv-phase" id="config">
    <p class="pv-phase-eyebrow">Phase 03</p>
    <h2 class="pv-phase-h2">Manage sources<span class="dot">.</span></h2>
    <p class="pv-phase-when">Anytime</p>
    <p class="pv-phase-desc">
      Your source suite is yours. Add sources you find useful. Exclude ones
      that are quiet or off-topic. The Warmup shows the proposed change and
      confirms before writing.
    </p>

    <div class="pv-trigger">
      <div class="pv-trigger-label">Examples</div>
      <div style="display:flex;flex-direction:column;gap:6px;margin-top:6px;">
        <span class="pv-trigger-cmd">show my warmup sources</span>
        <span class="pv-trigger-cmd">add The Information to my warmup</span>
        <span class="pv-trigger-cmd">exclude Orca Blog from warmup</span>
      </div>
    </div>

    <div class="pv-chat">
      <div class="pv-msg pv-msg-you">exclude orca blog from warmup — it's been quiet for months</div>
      <div class="pv-msg pv-msg-warmup">Orca Blog is currently active in your Tier 4 sources. I'll move it to Excluded Sources — it stays listed but won't be fetched in future briefs. Confirm?</div>
      <div class="pv-msg pv-msg-you">yes</div>
      <div class="pv-msg pv-msg-warmup">Done. Orca Blog moved to Excluded Sources. Your WARMUP.md is updated. 21 active sources remaining.</div>
    </div>
  </section>

  <!-- CLOSER -->
  <section class="pv-closer">
    <p>Know what moved. <strong>Then go move things.</strong></p>
  </section>

  <!-- FOOTER -->
  <footer class="pv-foot">
    <span>Real strength is lifting others</span>
    <a href="${githubUrl}" target="_blank" rel="noopener">github.com/missionbuilt/loadout</a>
  </footer>

</body>
</html>`;
}
