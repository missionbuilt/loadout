/**
 * Mission Built — Design System
 *
 * Design tokens extracted from missionbuilt.io. Used by:
 *  - The MCP server's landing page
 *  - The /preview route showing sample Spotter output
 *  - The /brand.css endpoint (if any external client wants to render Spotter
 *    content with the Mission Built aesthetic)
 *
 * If you fork this server and want to brand it for your own ecosystem,
 * change these tokens. Everything visual flows from here.
 */

export const BRAND = {
  // Core palette — anchored to the missionbuilt.io favicon:
  // warm-dark base, deep red barbell plates, cream bar.
  // Updated to lead with red, matching the platform-lights aesthetic.
  bg: "#171513",            // very dark warm — base background
  bgElevated: "#221d18",    // card / elevated surface (slightly warmer)
  bgSubtle: "#2a231c",      // hover / subtle elevation

  text: "#ebe5d8",          // cream — primary text (matches favicon bar)
  textMuted: "#b8ae9f",     // warm gray — secondary text
  textSubtle: "#8a8175",    // tertiary text and metadata

  accent: "#a8211a",        // deep red — primary accent (matches favicon plates)
  accentBright: "#d4322a",  // brighter red for hover states
  accentSubtle: "rgba(168, 33, 26, 0.18)",

  border: "rgba(235, 229, 216, 0.1)",
  borderStrong: "rgba(235, 229, 216, 0.22)",

  // Powerlifting platform lights — three-judge verdict system.
  // White light = good lift. Red light = no lift. Majority decides.
  //   Pass (good lift)        = ○ ○ ○  three white
  //   Needs work (split call) = ● ○ ●  red, white, red
  //   Missing (no lift)       = ● ● ●  three red
  lightWhite: "#ebe5d8",
  lightRed: "#a8211a",
  lightRedGlow: "rgba(168, 33, 26, 0.3)",
  lightBorder: "rgba(235, 229, 216, 0.25)",

  // Legacy status keys kept for compatibility — point at the lights palette.
  pass: "#ebe5d8",          // white light
  passSubtle: "rgba(235, 229, 216, 0.12)",
  needs: "#a8211a",         // red light (split decision)
  needsSubtle: "rgba(168, 33, 26, 0.18)",
  missing: "#a8211a",       // red light (no lift)
  missingSubtle: "rgba(168, 33, 26, 0.22)",
} as const;

export const TYPE = {
  serif: `'Iowan Old Style', 'Lora', Georgia, 'Times New Roman', serif`,
  sans: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`,
  mono: `ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace`,
} as const;

export const STENCIL = "▮▮▮";

/**
 * Returns the full Mission Built CSS as a string. Inlined into pages or
 * served at /brand.css for any external client that wants to render Spotter
 * content with the same aesthetic.
 */
export function brandCss(): string {
  return `
:root {
  --mb-bg: ${BRAND.bg};
  --mb-bg-elevated: ${BRAND.bgElevated};
  --mb-bg-subtle: ${BRAND.bgSubtle};
  --mb-text: ${BRAND.text};
  --mb-text-muted: ${BRAND.textMuted};
  --mb-text-subtle: ${BRAND.textSubtle};
  --mb-accent: ${BRAND.accent};
  --mb-accent-bright: ${BRAND.accentBright};
  --mb-accent-subtle: ${BRAND.accentSubtle};
  --mb-border: ${BRAND.border};
  --mb-border-strong: ${BRAND.borderStrong};
  --mb-pass: ${BRAND.pass};
  --mb-pass-subtle: ${BRAND.passSubtle};
  --mb-needs: ${BRAND.needs};
  --mb-needs-subtle: ${BRAND.needsSubtle};
  --mb-missing: ${BRAND.missing};
  --mb-missing-subtle: ${BRAND.missingSubtle};
  --mb-light-white: ${BRAND.lightWhite};
  --mb-light-red: ${BRAND.lightRed};
  --mb-light-red-glow: ${BRAND.lightRedGlow};
  --mb-light-border: ${BRAND.lightBorder};
  --mb-font-serif: ${TYPE.serif};
  --mb-font-sans: ${TYPE.sans};
  --mb-font-mono: ${TYPE.mono};
}

* { box-sizing: border-box; }

html { background: var(--mb-bg); scroll-behavior: smooth; }

body {
  margin: 0;
  background: var(--mb-bg);
  color: var(--mb-text);
  font-family: var(--mb-font-sans);
  font-size: 16px;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.mb-container {
  max-width: 720px;
  margin: 0 auto;
  padding: 4rem 1.5rem 6rem;
}

.mb-stencil {
  font-family: var(--mb-font-mono);
  font-size: 13px;
  letter-spacing: 0.08em;
  color: var(--mb-text-muted);
  text-transform: uppercase;
  margin: 0 0 1.5rem;
}

.mb-stencil .mb-stencil-bars {
  color: var(--mb-accent);
  margin: 0 0.5em;
  letter-spacing: 0.2em;
}

.mb-hero {
  font-family: var(--mb-font-serif);
  font-size: 56px;
  font-weight: 500;
  line-height: 1.05;
  letter-spacing: -0.02em;
  margin: 0 0 0.5rem;
  color: var(--mb-text);
}

.mb-hero-period {
  color: var(--mb-accent);
}

.mb-tagline {
  font-family: var(--mb-font-serif);
  font-style: italic;
  font-size: 22px;
  line-height: 1.4;
  color: var(--mb-text-muted);
  margin: 0 0 3rem;
  font-weight: 400;
}

.mb-section {
  margin: 3rem 0;
}

.mb-section-label {
  font-family: var(--mb-font-mono);
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--mb-text-subtle);
  text-transform: uppercase;
  margin: 0 0 0.75rem;
}

h2.mb-h2 {
  font-family: var(--mb-font-serif);
  font-size: 32px;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.015em;
  margin: 0 0 1rem;
  color: var(--mb-text);
}

.mb-h2-eyebrow {
  font-family: var(--mb-font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--mb-light-red);
  margin: 0 0 8px;
  display: block;
}

h3.mb-h3 {
  font-family: var(--mb-font-sans);
  font-size: 16px;
  font-weight: 500;
  margin: 1.5rem 0 0.5rem;
  color: var(--mb-text);
}

p.mb-p {
  margin: 0 0 1rem;
  color: var(--mb-text);
  font-size: 16px;
  line-height: 1.7;
}

a.mb-link {
  color: var(--mb-accent);
  text-decoration: none;
  border-bottom: 1px solid currentColor;
  transition: color 0.15s ease;
}

a.mb-link:hover {
  color: var(--mb-accent-bright);
}

code.mb-code {
  font-family: var(--mb-font-mono);
  font-size: 13px;
  background: var(--mb-bg-elevated);
  color: var(--mb-text);
  padding: 2px 6px;
  border-radius: 3px;
  border: 0.5px solid var(--mb-border);
}

pre.mb-pre {
  font-family: var(--mb-font-mono);
  font-size: 13px;
  background: var(--mb-bg-elevated);
  color: var(--mb-text);
  padding: 1rem 1.25rem;
  border-radius: 4px;
  border: 0.5px solid var(--mb-border);
  overflow-x: auto;
  line-height: 1.6;
  margin: 1rem 0;
}

pre.mb-pre code {
  background: transparent;
  padding: 0;
  border: none;
  font-size: inherit;
  color: inherit;
}

.mb-card {
  background: var(--mb-bg-elevated);
  border: 0.5px solid var(--mb-border);
  border-radius: 6px;
  padding: 1.5rem 1.75rem;
  margin: 1.5rem 0;
}

.mb-divider {
  border: none;
  border-top: 0.5px solid var(--mb-border);
  margin: 3rem 0;
}

.mb-meta-row {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
  font-family: var(--mb-font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
  color: var(--mb-text-subtle);
  text-transform: uppercase;
  margin: 1.5rem 0;
}

.mb-meta-row strong {
  display: block;
  font-family: var(--mb-font-sans);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
  color: var(--mb-text);
  margin-top: 2px;
}

.mb-tool-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.mb-tool-list li {
  padding: 0.6rem 0;
  border-bottom: 0.5px solid var(--mb-border);
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 1rem;
  align-items: baseline;
}

.mb-tool-list li:last-child { border-bottom: none; }

.mb-tool-list code {
  font-family: var(--mb-font-mono);
  font-size: 13px;
  color: var(--mb-accent);
}

.mb-tool-list span {
  font-size: 14px;
  color: var(--mb-text-muted);
  line-height: 1.5;
}

/* Lens grading widgets — used in /preview and any client that renders
   Spotter output as cards. */

/* Section break — strong visual transition between overview and example.
   Stencil bars + label, designed to be unmissable. */
.mb-section-break {
  display: flex;
  align-items: center;
  gap: 18px;
  margin: 3.5rem 0 2rem;
}

.mb-section-break-rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--mb-light-red), transparent);
}

.mb-section-break-rule.mb-section-break-rule-end {
  background: linear-gradient(to left, transparent, var(--mb-light-red), transparent);
}

.mb-section-break-label {
  font-family: var(--mb-font-mono);
  font-size: 12px;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--mb-light-red);
  white-space: nowrap;
  font-weight: 500;
}

.mb-section-break-stencil {
  color: var(--mb-light-red);
  letter-spacing: 0.15em;
  margin: 0 4px;
}

/* Example container — frames the entire sample output to distinguish it
   visually from the overview content above. Red accent border + badge. */
.mb-example-container {
  background: rgba(168, 33, 26, 0.04);
  border: 0.5px solid rgba(168, 33, 26, 0.22);
  border-left: 3px solid var(--mb-light-red);
  border-radius: 8px;
  padding: 2.5rem 2rem 2rem;
  margin: 0 0 1rem;
  position: relative;
}

.mb-example-badge {
  position: absolute;
  top: -11px;
  left: 1.5rem;
  background: var(--mb-bg);
  padding: 3px 14px;
  font-family: var(--mb-font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--mb-light-red);
  border: 0.5px solid rgba(168, 33, 26, 0.4);
  border-radius: 3px;
  font-weight: 500;
}

.mb-example-end {
  margin-top: 2rem;
  text-align: center;
  font-family: var(--mb-font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--mb-text-subtle);
  padding-top: 1.5rem;
  border-top: 0.5px solid rgba(168, 33, 26, 0.15);
}

/* Lens chart — quick interactive overview of all 9 lenses + their lights.
   Each row is clickable, scrolls to the detailed write-up below. */
.mb-lens-chart {
  background: rgba(0, 0, 0, 0.18);
  border: 0.5px solid var(--mb-border);
  border-radius: 6px;
  margin: 1.25rem 0 0;
  /* overflow: visible so tooltips on top rows aren't clipped */
}

.mb-lens-chart-row {
  display: grid;
  grid-template-columns: 42px 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 12px 16px;
  border-top: 0.5px solid var(--mb-border);
  cursor: pointer;
  transition: background 0.15s ease, padding-left 0.15s ease;
  text-decoration: none;
  color: var(--mb-text);
}

.mb-lens-chart-row:first-of-type {
  border-top: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
}

.mb-lens-chart-row:last-of-type {
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
}

.mb-lens-chart-row:hover {
  background: rgba(168, 33, 26, 0.1);
  padding-left: 20px;
}

.mb-lens-chart-num {
  font-family: var(--mb-font-mono);
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--mb-text-subtle);
}

.mb-lens-chart-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--mb-text);
}

.mb-lens-chart-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mb-lens-chart-status-label {
  font-family: var(--mb-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--mb-text-muted);
  min-width: 82px;
  text-align: right;
}

.mb-lens-chart-status-label.mb-status-pass {
  color: var(--mb-light-white);
}
.mb-lens-chart-status-label.mb-status-needs {
  color: var(--mb-text-muted);
}
.mb-lens-chart-status-label.mb-status-missing {
  color: var(--mb-light-red);
}

.mb-gate-badge {
  background: rgba(168, 33, 26, 0.18);
  color: var(--mb-light-red);
  font-family: var(--mb-font-mono);
  font-size: 9px;
  padding: 2px 7px;
  border-radius: 3px;
  letter-spacing: 0.14em;
  margin-left: 8px;
  border: 0.5px solid rgba(168, 33, 26, 0.4);
  text-transform: uppercase;
  font-weight: 500;
}

/* Lights with hover tooltip — explains the platform-lights system inline. */
.mb-lights-tooltip {
  position: relative;
  cursor: help;
}

.mb-lights-tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  background: var(--mb-bg-elevated);
  color: var(--mb-text);
  font-family: var(--mb-font-mono);
  font-size: 10.5px;
  letter-spacing: 0.04em;
  text-transform: none;
  padding: 7px 11px;
  border-radius: 4px;
  border: 0.5px solid rgba(168, 33, 26, 0.4);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 0.15s ease, transform 0.15s ease;
  z-index: 10;
}

.mb-lights-tooltip:hover::after {
  opacity: 1;
  transform: translateY(0);
}

/* Anchor scroll offset for clickable lens links */
.mb-lens-card {
  scroll-margin-top: 2rem;
}

/* Chat thread — used in preview to showcase the conversational workflow.
   User messages right-aligned with a red-tinted background, Spotter messages
   left-aligned on the elevated surface. The slash command gets accent color
   to make the trigger visually obvious. */

.mb-chat-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin: 1.5rem 0 0;
}

@media (max-width: 720px) {
  .mb-chat-columns {
    grid-template-columns: 1fr;
    gap: 32px;
  }
}

.mb-chat-meta {
  font-family: var(--mb-font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--mb-light-red);
  margin: 0 0 10px;
}

.mb-chat-thread {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mb-chat-msg {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.55;
  max-width: 92%;
  word-wrap: break-word;
}

.mb-chat-msg-user {
  align-self: flex-end;
  background: rgba(168, 33, 26, 0.15);
  border: 0.5px solid rgba(168, 33, 26, 0.4);
  color: var(--mb-text);
  border-bottom-right-radius: 2px;
}

.mb-chat-msg-spotter {
  align-self: flex-start;
  background: var(--mb-bg-elevated);
  border: 0.5px solid var(--mb-border);
  color: var(--mb-text);
  border-bottom-left-radius: 2px;
}

.mb-chat-msg.mb-chat-msg-paste {
  font-family: var(--mb-font-mono);
  font-size: 12px;
  color: var(--mb-text-muted);
  background: rgba(168, 33, 26, 0.08);
  white-space: pre-line;
}

.mb-chat-slash {
  font-family: var(--mb-font-mono);
  color: var(--mb-light-red);
  font-weight: 500;
}

.mb-chat-leadin {
  font-family: var(--mb-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--mb-text-subtle);
  text-align: center;
  margin: 1rem 0 0;
}

/* Platform lights — three-judge verdict from powerlifting.
   Three small lights + a text label. Visually unmistakable. */
.mb-verdict {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--mb-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--mb-text);
  padding: 6px 12px 6px 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 999px;
  border: 0.5px solid var(--mb-light-border);
}

.mb-lights {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.mb-light {
  display: inline-block;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.35);
}

.mb-light.mb-light-white {
  background: var(--mb-light-white);
  box-shadow: 0 0 4px rgba(235, 229, 216, 0.4);
}

.mb-light.mb-light-red {
  background: var(--mb-light-red);
  box-shadow: 0 0 6px var(--mb-light-red-glow);
}

.mb-verdict.mb-pass {
  color: var(--mb-light-white);
  border-color: rgba(235, 229, 216, 0.35);
}

.mb-verdict.mb-needs {
  color: var(--mb-light-white);
  border-color: rgba(168, 33, 26, 0.5);
}

.mb-verdict.mb-missing {
  color: var(--mb-light-red);
  border-color: var(--mb-light-red);
  background: rgba(168, 33, 26, 0.12);
}

.mb-lens-card {
  background: var(--mb-bg-elevated);
  border: 0.5px solid var(--mb-border);
  border-radius: 6px;
  padding: 1.25rem 1.5rem;
  margin: 1rem 0;
}

.mb-lens-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.mb-lens-card-title {
  font-family: var(--mb-font-serif);
  font-size: 18px;
  font-weight: 500;
  margin: 0;
  color: var(--mb-text);
}

.mb-lens-card-num {
  font-family: var(--mb-font-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--mb-text-subtle);
  text-transform: uppercase;
}

.mb-lens-card-section-label {
  font-family: var(--mb-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--mb-text-subtle);
  margin: 1rem 0 0.5rem;
}

.mb-lens-card ul {
  margin: 0.5rem 0 0.75rem;
  padding-left: 1.2rem;
}

.mb-lens-card li {
  margin: 0.4rem 0;
  color: var(--mb-text);
  line-height: 1.6;
  font-size: 15px;
}

.mb-lens-card .mb-principle {
  font-family: var(--mb-font-serif);
  font-style: italic;
  color: var(--mb-text-muted);
  font-size: 15px;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 0.5px solid var(--mb-border);
}

.mb-footer {
  font-family: var(--mb-font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
  color: var(--mb-text-subtle);
  text-transform: uppercase;
  margin-top: 4rem;
  padding-top: 2rem;
  border-top: 0.5px solid var(--mb-border);
}

.mb-footer-line {
  font-family: var(--mb-font-serif);
  font-style: italic;
  font-size: 18px;
  letter-spacing: 0;
  text-transform: none;
  color: var(--mb-accent);
  margin: 0 0 1rem;
}

.mb-footer a {
  color: var(--mb-text-muted);
}

@media (max-width: 600px) {
  .mb-container { padding: 2.5rem 1.25rem 4rem; }
  .mb-hero { font-size: 40px; }
  .mb-tagline { font-size: 18px; }
  h2.mb-h2 { font-size: 22px; }
  .mb-tool-list li { grid-template-columns: 1fr; gap: 0.25rem; }
}
`;
}
