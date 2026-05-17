/**
 * Mission Built MCP Server (OAuth-protected)
 *
 * Unified MCP server for The Loadout — exposes all skills from the Mission
 * Built ecosystem (The Warmup, The Spotter) through a single endpoint.
 *
 * Public routes (no auth):
 *   /              - landing page
 *   /preview       - skill walkthrough
 *   /health        - JSON health check
 *   /brand.css     - Mission Built design CSS
 *
 * OAuth flow routes (handled by workers-oauth-provider):
 *   /.well-known/oauth-authorization-server  - discovery metadata
 *   /authorize     - authorization endpoint (Google sign-in)
 *   /token         - token exchange
 *   /register      - dynamic client registration
 *
 * Protected MCP routes (require Bearer token):
 *   /sse           - MCP over Server-Sent Events
 *
 * Source: https://github.com/missionbuilt/loadout
 * License: MIT
 */

import OAuthProvider from "@cloudflare/workers-oauth-provider";
import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";
import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

// Skill content bundled at build time via Wrangler text imports.
import WARMUP_SKILL_MD from "./skill-content/warmup/SKILL.md";
import WARMUP_TEMPLATE_HTML from "./skill-content/warmup/warmup-template.html";
import SPOTTER_SKILL_MD from "./skill-content/spotter/SKILL.md";
import SPOTTER_AREA_EXAMPLES_MD from "./skill-content/spotter/area-examples.md";
import SPOTTER_SYNTHETIC_EPIC_MD from "./skill-content/spotter/synthetic-epic.md";
import SPOTTER_SYNTHETIC_EPIC_2_MD from "./skill-content/spotter/synthetic-epic-2.md";
import SPOTTER_SYNTHETIC_EPIC_3_MD from "./skill-content/spotter/synthetic-epic-3.md";
import SPOTTER_TEMPLATE_HTML from "./skill-content/spotter/spotter-template.html";
import SPOTTER_SHELL_JS from "./spotter-shell.rawjs";
import APPROACH_SKILL_MD from "./skill-content/the-approach/SKILL.md";
import APPROACH_TEMPLATE_HTML from "./skill-content/the-approach/approach-template.html";

import { brandCss } from "./design";
import { authHandler, type UserProps } from "./auth";
import { SERVER_VERSION, WARMUP_VERSION, WARMUP_ENGINE_VERSION, SPOTTER_VERSION, THE_APPROACH_VERSION } from "./constants";

/**
 * Extract a named section from SKILL.md by heading boundary.
 * Prevents tool responses from embedding the full ~90KB document.
 *
 * Available sections:
 *   "setup"    – SETUP Mode (first-run flow, question order, WARMUP.md format)
 *   "run"      – RUN Mode steps 1–6 (full run workflow + schema + source rules)
 *   "config"   – CONFIGURE Mode (add/remove/exclude sources)
 *   "schema"   – Step 4 Render phase only (WARMUP_DATA JSON schema + rules)
 *   "sources"  – Source suites for CISO, Product Leader, Sector-Specific
 *   "sections" – Report section structures (CISO + Product Leader)
 *   "rules"    – Anti-patterns and editorial voice
 *   "warmupmd" – WARMUP.md config format reference
 *   "full"     – Entire SKILL.md (use only when a specific section is insufficient)
 */
function getSkillSection(md: string, section: string): string {
  const boundaries: Record<string, [string, string | null]> = {
    setup:    ["## SETUP Mode",                            "## RUN Mode"],
    run:      ["## RUN Mode",                              "## CONFIGURE Mode"],
    config:   ["## CONFIGURE Mode",                        "## CISO Source Suite"],
    schema:   ["### Step 4 — Render phase",                "### Step 5 — Summary line"],
    sources:  ["## CISO Source Suite",                     "## CISO Report"],
    sections: ["## CISO Report",                           "## Custom Mode — Source-Building Rules"],
    rules:    ["## Anti-Patterns",                         "## Voice"],
    warmupmd: ["## WARMUP.md Config Format",               "## Anti-Patterns"],
  };
  if (section === "full" || !boundaries[section]) return md;
  const [startMark, endMark] = boundaries[section];
  const si = md.indexOf(startMark);
  if (si === -1) return `[Section "${section}" not found in SKILL.md — use section:"full" to load everything]`;
  const ei = endMark ? md.indexOf(endMark, si) : md.length;
  return md.slice(si, ei === -1 ? md.length : ei).trim();
}

/**
 * Extract a named section from Spotter SKILL.md by heading boundary.
 * Prevents tool responses from embedding the full ~29KB document.
 *
 * Available sections:
 *   "areas"        – The nine review areas (all sub-checks) — largest section, load for grading
 *   "review"       – Review mode output format only (verdict, per-area blocks, push-forward offer)
 *   "iterate"      – Iterate mode output format only
 *   "build"        – Build mode output format only
 *   "output"       – All three output format sections together (review + iterate + build)
 *   "schema"       – Structured output schema (JSON fields, rules, forward-compat notes)
 *   "antipatterns" – Anti-patterns list (what the skill must not do)
 *   "full"         – Entire SKILL.md (use only when a specific section is insufficient)
 */
function getSpotterSkillSection(md: string, section: string): string {
  const boundaries: Record<string, [string, string | null]> = {
    areas:        ["## The nine areas",             "## Output formats by mode"],
    output:       ["## Output formats by mode",    "## Structured output schema"],
    review:       ["### Review mode",               "### Iterate mode"],
    iterate:      ["### Iterate mode",              "### Build mode"],
    build:        ["### Build mode",                "## Structured output schema"],
    schema:       ["## Structured output schema",   "## Anti-patterns"],
    antipatterns: ["## Anti-patterns",              "## Examples"],
  };
  if (section === "full" || !boundaries[section]) return md;
  const [startMark, endMark] = boundaries[section];
  const si = md.indexOf(startMark);
  if (si === -1) return `[Section "${section}" not found in Spotter SKILL.md — use section:"full" to load everything]`;
  const ei = endMark ? md.indexOf(endMark, si) : md.length;
  return md.slice(si, ei === -1 ? md.length : ei).trim();
}

/**
 * Extract examples for a specific area from area-examples.md.
 * Each area is delimited by "## Area N" headings.
 * Pass area=0 to return the full document.
 */
function getSpotterAreaExamples(md: string, area: number): string {
  if (area === 0) return md;
  const startMark = `## Area ${area}`;
  const si = md.indexOf(startMark);
  if (si === -1) return `[Area ${area} not found in area-examples.md — use area:0 to load all examples]`;
  const nextMark = `## Area ${area + 1}`;
  const ei = md.indexOf(nextMark, si);
  return md.slice(si, ei === -1 ? md.length : ei).trim();
}

/**
 * Extract a named section from The Approach SKILL.md by heading boundary.
 *
 * Available sections:
 *   "intake"   - INTAKE Mode (Step 0)
 *   "research" - RESEARCH Phase (Step 1)
 *   "schema"   - APPROACH_DATA schema
 *   "render"   - RENDER Phase (Step 2)
 *   "rules"    - Editorial rules
 *   "config"   - APPROACH.md config format
 *   "full"     - Entire SKILL.md
 */
function getApproachSkillSection(md: string, section: string): string {
  const boundaries: Record<string, [string, string | null]> = {
    intake:   ["## INTAKE Mode",              "## RESEARCH Phase"],
    research: ["## RESEARCH Phase",           "## APPROACH_DATA Schema"],
    schema:   ["## APPROACH_DATA Schema",     "## RENDER Phase"],
    render:   ["## RENDER Phase",             "## Editorial rules"],
    rules:    ["## Editorial rules",          "## APPROACH.md config format"],
    config:   ["## APPROACH.md config format", "## Version history"],
  };
  if (section === "full" || !boundaries[section]) return md;
  const [startMark, endMark] = boundaries[section];
  const si = md.indexOf(startMark);
  if (si === -1) return `[Section "${section}" not found in The Approach SKILL.md — use section:"full" to load everything]`;
  const ei = endMark ? md.indexOf(endMark, si) : md.length;
  return md.slice(si, ei === -1 ? md.length : ei).trim();
}

// ── Shared param schemas ──────────────────────────────────────────────────────

/** Re-used across every tool that shows a Cowork permission dialog. */
const intentField = z.string().describe(
  "Permission dialog text — one sentence, ≤100 chars. E.g. 'Loading Warmup skill framework'."
);

// ── Warmup constants ──────────────────────────────────────────────────────────

const WARMUP_MODES = [
  {
    id: "ciso",
    name: "CISO Mode",
    description:
      "Built for cybersecurity executives. Loads a pre-curated source suite: CISA advisories, the KEV catalog, MITRE ATT&CK, Tier 1 threat intel vendors, and sector-specific sources for Healthcare, Financial Services, Energy, Government, and Manufacturing/OT.",
    sections: [
      "Threat Landscape — active threat actors, MITRE-mapped TTPs, CrowdStrike taxonomy",
      "Emerging Threats — new CVEs, CISA KEV additions, zero-days, new malware families",
      "Research Digest — new publications from Tier 1 and Tier 2 sources",
      "Industry Intel — M&A, product launches, leadership changes, regulatory moves",
      "Social Signal — high-signal community discussion, clearly labeled as unverified",
    ],
  },
  {
    id: "product_leader",
    name: "Product Leader Mode",
    description:
      "Built for product managers, CPOs, and product-oriented executives. Covers competitor moves, AI model releases, market funding, key voices to track, and the analyst and news sources that matter for your vertical.",
    sections: [
      "Company Intel — news, earnings, product launches, and leadership moves from your org",
      "Competitor Moves — product announcements, pricing changes, hiring signals, positioning shifts",
      "AI and Tooling — model releases, capability updates, developer tooling relevant to your roadmap",
      "Market and Funding — VC rounds, M&A, analyst reports, regulatory moves in your vertical",
      "Social Signal — high-signal community discussion, clearly labeled as unverified",
    ],
  },
  {
    id: "custom",
    name: "Custom Mode",
    description:
      "Describe your morning interests in plain language. The Warmup builds a source suite from scratch — stocks, industry news, competitor blogs, AI releases, policy changes, local business news. Every recommended source comes with a tier rating.",
    sections: [
      "Sections are built dynamically based on your described interests during setup",
    ],
  },
];

// ── Spotter constants ─────────────────────────────────────────────────────────

const SPOTTER_AREAS = [
  { id: 1, name: "The user and the problem", weight: "foundation — heaviest area, 8 sub-checks" },
  { id: 2, name: "Competitive landscape", weight: "standard" },
  { id: 3, name: "What we're betting on", weight: "standard, includes press-release test" },
  { id: 4, name: "How we'll build it", weight: "standard, 4 sub-checks" },
  { id: 5, name: "What else changes", weight: "standard" },
  { id: 6, name: "Packaging and pricing", weight: "standard" },
  { id: 7, name: "Launch readiness", weight: "standard, lifecycle framing" },
  { id: 8, name: "After it ships", weight: "standard" },
  { id: 9, name: "Trust and governance", weight: "gate — ✗ Missing on B2B features caps verdict at Not ready" },
];

// ── Env ───────────────────────────────────────────────────────────────────────

interface Env {
  MCP_OBJECT: DurableObjectNamespace;
  OAUTH_KV: KVNamespace;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  COOKIE_ENCRYPTION_KEY: string;
  OAUTH_PROVIDER: OAuthHelpers;
}

// ── Agent ─────────────────────────────────────────────────────────────────────

export class MissionBuiltMCP extends McpAgent<Env, UserProps> {
  server = new McpServer({
    name: "missionbuilt",
    version: SERVER_VERSION,
  });

  async init() {

    // ══════════════════════════════════════════════════════════════════════════
    // SHARED TOOLS
    // ══════════════════════════════════════════════════════════════════════════

    this.server.tool(
      "loadout_whoami",
      "Returns the authenticated user's identity (name and email) for the current MCP session. Useful for personalizing skill output or confirming the OAuth connection is active.",
      {
        intent: intentField,
      },
      async () => {
        const props = this.props;
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  email: props?.email ?? "unknown",
                  name: props?.name ?? "unknown",
                  authenticated: Boolean(props?.email),
                },
                null,
                2
              ),
            },
          ],
        };
      }
    );

    this.server.tool(
      "loadout_get_brand_css",
      "Returns the Mission Built design system as a CSS string. Use to render any Loadout skill output (Warmup briefs, Spotter reviews) as branded HTML in compatible clients. The CSS uses --mb-* custom properties.",
      {
        intent: intentField,
      },
      async () => ({
        content: [{ type: "text" as const, text: brandCss() }],
      })
    );

    // ══════════════════════════════════════════════════════════════════════════
    // THE WARMUP
    // ══════════════════════════════════════════════════════════════════════════

    this.server.tool(
      "warmup_get_skill",
      "Returns a section of the Warmup SKILL.md. Use the 'section' param to load only what you need — avoids loading the full ~90KB document. Sections: 'schema' (WARMUP_DATA render schema + field rules), 'sources' (source suites, tiers, batch queries), 'sections' (report section structures for CISO + Product Leader), 'run' (full run flow), 'setup' (first-run setup flow), 'config' (add/remove sources), 'rules' (anti-patterns + editorial voice), 'warmupmd' (WARMUP.md config format), 'full' (everything — use only when a specific section is insufficient).",
      {
        intent: intentField,
        section: z
          .enum(["setup", "run", "config", "schema", "sources", "sections", "rules", "warmupmd", "full"])
          .optional()
          .describe(
            "Which section to return. Defaults to 'full'. Prefer specific sections: 'schema' during render, 'sources' during fetch, 'sections' when writing section content, 'rules' for anti-pattern checks, 'setup' during first-run setup, 'warmupmd' to check WARMUP.md format."
          ),
      },
      async ({ section }) => ({
        content: [{ type: "text" as const, text: getSkillSection(WARMUP_SKILL_MD, section ?? "full") }],
      })
    );

    this.server.tool(
      "warmup_list_modes",
      "Returns the three Warmup modes with names, descriptions, and the five brief sections each produces. Useful for clients that want to render a mode-picker or for an agent that needs a quick overview before loading the full SKILL.md.",
      {
        intent: intentField,
      },
      async () => ({
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ version: WARMUP_VERSION, modes: WARMUP_MODES }, null, 2),
          },
        ],
      })
    );

    this.server.tool(
      "warmup_get_template",
      "Returns the canonical warmup-template.html engine with WARMUP_DATA already injected — artifact-ready HTML, no Edit step required. Build your complete WARMUP_DATA object first, then pass it as a JSON string. The server replaces the placeholder and returns the filled artifact. Write the result to disk and call create_artifact or update_artifact. Never reconstruct or invent the HTML yourself.",
      {
        intent: intentField,
        warmup_data: z
          .string()
          .describe(
            "The full WARMUP_DATA JSON object serialised as a string via JSON.stringify(). " +
            "Required. The server injects it server-side and returns filled, artifact-ready HTML."
          ),
      },
      async ({ warmup_data }) => {
        // Inject WARMUP_DATA server-side — eliminates the fragile Write→Read→Edit cycle
        // that caused agents to abandon the template and generate their own HTML.
        //
        // XSS safety: article titles/bodies can contain </script> which would break
        // the script tag if injected verbatim. Escape before injection.
        //
        // Replacer-function safety: String.prototype.replace(literal, literal) interprets
        // $', $&, $` as special sequences. Article content can contain these (e.g. stock
        // tickers, price strings). A replacer function bypasses special-sequence expansion.
        const safe = warmup_data.replace(/<\/script>/gi, '<\\/script>');
        const PLACEHOLDER = `window.WARMUP_DATA = null; // ← AGENT: Edit-replace this line with your WARMUP_DATA JSON object (see SKILL.md Path B)`;
        const filled = WARMUP_TEMPLATE_HTML.replace(PLACEHOLDER, () => `window.WARMUP_DATA = ${safe};`);
        const injected = filled !== WARMUP_TEMPLATE_HTML;
        return {
          content: [
            {
              type: "text" as const,
              text: injected
                ? filled
                : `[warmup_get_template ERROR: WARMUP_DATA placeholder not found in template — injection failed. Do NOT use the raw template. Call warmup_get_template again.]`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "warmup_setup",
      "Primes the agent to run The Warmup's setup flow for a new user. Ask mode, then company name FIRST — use a web search to auto-determine sector, region, and competitors from the company name, present findings for confirmation, then ask only what could not be looked up. Saves config to WARMUP.md and runs a test brief.",
      {
        intent: intentField,
        mode: z
          .enum(["ciso", "product_leader", "custom"])
          .optional()
          .describe("The mode to set up. If omitted, the agent asks the user to choose."),
      },
      async ({ mode }) => {
        const modeContext = mode
          ? `The user has indicated they want ${mode === "ciso" ? "CISO Mode" : mode === "product_leader" ? "Product Leader Mode" : "Custom Mode"}. Start from step 2 of the setup flow for that mode.`
          : "Ask the user which mode fits them best before beginning setup.";

        return {
          content: [
            {
              type: "text" as const,
              text:
                `# The Warmup — Setup\n\n` +
                `${modeContext}\n\n` +
                `## How to run setup\n\n` +
                `1. Ask which mode fits the user (CISO / Product Leader / Custom) if not already known.\n` +
                `2. Ask the user's name for the brief header.\n` +
                `3. Ask for company name FIRST — then call the WebSearch tool to auto-determine sector, region, and competitors. Present all findings in one confirmation message. Ask only what the search could not determine.\n` +
                `4. Build the source suite based on confirmed answers. Show it to the user for review.\n` +
                `5. Use the Write file tool to save WARMUP.md at the user's project root. Use the schema in the ## WARMUP.md Config Format section of SKILL.md below — do not invent fields or omit required ones. Include showQuote: true in the Profile section.\n` +
                `6. Run a test brief using the saved config. Deliver it as a Cowork artifact.\n\n` +
                `## CRITICAL: Question order for CISO and Product Leader modes\n\n` +
                `After company confirmation, you MUST still ask the follow-up questions below. Do not skip them — they cannot be looked up.\n\n` +
                `**CISO follow-ups (ask after confirmation):**\n` +
                `- Any executives, security leaders, or board members they want to follow? Suggest 2–3 relevant names based on the company/sector (e.g. known CISOs, threat intel voices). They can add, remove, or skip.\n` +
                `- Any personal interests for the end of the brief? (sports, markets, hobby — totally optional, but ask)\n\n` +
                `**Product Leader follow-ups (ask after confirmation):**\n` +
                `- Which AI vendors or tools matter to their roadmap? Suggest a list based on their product area, let them edit.\n` +
                `- Any executives, investors, analysts, or journalists they want to follow? Suggest 2–3 relevant names. They can add, remove, or skip.\n` +
                `- Any personal interests for the end of the brief? (sports, markets, hobby — totally optional, but ask)\n\n` +
                `Full question order: Mode → Name → Company (web search) → confirm → follow-ups above → source review → save → run brief.\n` +
                `Do NOT ask sector or region before asking for the company name.\n` +
                `If the user skips company, ask sector, region, vendors, execs, interests manually.\n\n` +
                `## Voice\n\n` +
                `Ask one question at a time. Plain language — never internal-framework prompts. ` +
                `The user is setting up their morning routine, not configuring a system. Keep it fast.\n\n` +
                `## Reference sections (call warmup_get_skill with the section param as needed)\n\n` +
                `- Detailed setup flow and question order: warmup_get_skill({ section: "setup", intent: "..." })\n` +
                `- Source suites and tier definitions: warmup_get_skill({ section: "sources", intent: "..." })\n` +
                `- WARMUP.md config format reference: warmup_get_skill({ section: "warmupmd", intent: "..." })\n` +
                `- Full SKILL.md (only if above sections are insufficient): warmup_get_skill({ section: "full", intent: "..." })\n\n` +
                `Begin with mode selection if not yet known, or with the first config question for the given mode.`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "warmup_run",
      "Primes the agent to generate a Warmup intelligence brief. Reads the user's WARMUP.md config, fetches live intelligence from each active source, synthesizes it into the five sections, runs link safety verification, and renders the output as a live HTML artifact. One summary line in chat — the brief is the artifact.",
      {
        intent: intentField,
        config_summary: z
          .string()
          .optional()
          .describe("Optional: the contents of the user's WARMUP.md, if already read. If omitted, the agent reads it first."),
      },
      async ({ config_summary }) => {
        // config_summary is isolated as a fenced data block rather than spliced
        // into instruction prose — prevents adversarial WARMUP.md content from
        // overwriting the agent's operating instructions.
        const configNote = config_summary
          ? `The user's WARMUP.md has been provided. Proceed directly to source fetching.\n\n## WARMUP.md (provided)\n\n\`\`\`\n${config_summary.slice(0, 8000)}\n\`\`\``
          : "Read the user's WARMUP.md from their project root before proceeding. If it does not exist, run warmup_setup first.";

        return {
          content: [
            {
              type: "text" as const,
              text:
                `# The Warmup — Run Brief\n\n` +
                `**Engine version: ${WARMUP_ENGINE_VERSION}**\n\n` +
                `${configNote}\n\n` +
                `## How to generate the brief\n\n` +
                `1. Use the Read file tool (not bash) to read WARMUP.md from the user's project root. If you do not know the project root path, call list_artifacts first — the html_path from "the-warmup" reveals the workspace folder, and WARMUP.md lives there. If no artifact and no WARMUP.md, run warmup_setup first.\n` +
                `2. Artifact and engine check — call list_artifacts.\n` +
                `   a) "the-warmup" does not exist → first run: set mode = "create". Proceed to step 4.\n` +
                `   b) "the-warmup" exists → use the Read file tool to read the first 10 lines of html_path.\n` +
                `      - File cannot be read → treat as first run: set mode = "create". Proceed to step 4.\n` +
                `      - First 10 lines contain <!-- warmup-engine: ${WARMUP_ENGINE_VERSION} --> → Path A (version match). Proceed to step 4.\n` +
                `      - First 10 lines contain any other version or no marker → Path B (stale engine): set mode = "create". Proceed to step 4.\n` +
                `   Output this line in chat before proceeding: "📋 Artifact ready · [first run / engine match / engine update] · Fetching intelligence now."\n` +
                `3. TEMPLATE RULE — NON-NEGOTIABLE: The artifact HTML comes ONLY from warmup_get_template (PATH B) or the existing artifact file (PATH A). NEVER write HTML from scratch. NEVER reconstruct the template from training memory. Every time an agent generates HTML from memory, the design is wrong — wrong colors, wrong layout, invented stat labels. The correct design lives only in warmup_get_template.\n` +
                `4. Fetch phase: for each active source, call WebSearch. Budget: check search_depth in WARMUP.md — standard (default) = top 5 results per batch, 200 words/article; deep = top 10 results, 400 words/article. Standard is recommended for daily use (~40–60K fetch tokens); deep is ~2× that for broader coverage. Reject any item where item.date < lookback_start before routing to sections. If skip_scan: true in WARMUP.md, skip the URL safety check (step 5) and set config.skipScan: true, safety.domains: [], safety.totalUrls: 0 in WARMUP_DATA.\n` +
                `5. Run the link safety verification protocol on all URLs before including them (unless skip_scan: true — see step 4).\n` +
                `6. Synthesize content into sections. Build WARMUP_DATA with all required fields:\n` +
                `   - config.showQuote: true (JSON boolean — required, not optional)\n` +
                `   - config.scanTime: current generation time as "HH:MM TZ" (use WARMUP.md timezone; default UTC if not set)\n` +
                `   - config.vendors: copy verbatim from WARMUP.md vendors field; write "" if blank, never omit\n` +
                `   - config.skipScan: true if skip_scan: true in WARMUP.md, otherwise omit\n` +
                `   - config.searchDepth: copy from WARMUP.md search_depth field ("standard" or "deep"); default "standard" if not set\n` +
                `   - safety.domains: one entry per active source — required; set [] if skipScan; empty array means safety panel does not render\n` +
                `   - safety.totalUrls: count of verified-safe clickable URLs in the brief (must equal config.totalLinks); set 0 if skipScan\n` +
                `   - sources[].status: "active" | "quiet" | "excluded" — exact strings only\n` +
                `   - sources[].ct: "N items" for active sources, "—" for quiet sources\n` +
                `7. Render the artifact:\n` +
                `   PATH A (version match — no template reload): do NOT read the full 131KB file.\n` +
                `     a) Use the Grep tool to find the line number of "<script id=\\"warmup-data\\">" in html_path.\n` +
                `     b) Use the Read file tool with offset+limit to read only the <script id="warmup-data">…</script> block (~10–20 lines).\n` +
                `     c) Use the Edit tool to replace that entire block with the new WARMUP_DATA. Call update_artifact. Done. No bash.\n` +
                `   PATH B / FIRST RUN (engine update or new artifact):\n` +
                `     a) Call warmup_get_template({ intent: "...", warmup_data: JSON.stringify(WARMUP_DATA) }). Server injects WARMUP_DATA and returns filled, artifact-ready HTML. If response begins with "[warmup_get_template ERROR", call it again.\n` +
                `     b) Use the Write file tool to write the HTML string to disk. Write path: use existing html_path if updating stale engine; for first run, write to [project_root]/warmup.html. The Write file tool writes directly to user's filesystem — do NOT use bash, shell, or python.\n` +
                `     c) Call create_artifact (first run) or update_artifact (stale engine). Done.\n` +
                `   NEVER write your own HTML. NEVER use bash for any part of the render step.\n` +
                `   One summary line in chat — the brief is the artifact.\n\n` +
                `## Voice\n\n` +
                `The brief is factual and labeled. Every item shows its source and trust tier. ` +
                `No editorializing. No hype. Keep it scannable and honest.\n\n` +
                `## Reference sections (call warmup_get_skill with the section param when you need details)\n\n` +
                `- Source tiers, batch query templates, sector-specific sources (Step 2 fetch phase): warmup_get_skill({ section: "sources", intent: "Loading source tiers for fetch phase" })\n` +
                `- Report section structures — what goes in each section, lead vs grid items (Step 3 synthesis): warmup_get_skill({ section: "sections", intent: "Loading section structures for synthesis" })\n` +
                `- WARMUP_DATA JSON schema, all field rules, date filter, sub field, safety panel (Step 4 render): warmup_get_skill({ section: "schema", intent: "Loading WARMUP_DATA schema for render" })\n` +
                `- Anti-patterns, editorial voice, hard rules: warmup_get_skill({ section: "rules", intent: "Checking anti-patterns" })\n` +
                `- Full SKILL.md (only if the above sections are collectively insufficient): warmup_get_skill({ section: "full", intent: "..." })`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "warmup_config",
      "Primes the agent to manage the user's Warmup source configuration. Handles add, remove, and exclude operations on active sources in WARMUP.md. Always reads current config before making changes, shows the proposed change for confirmation, then writes.",
      {
        intent: intentField,
        action: z
          .enum(["add", "remove", "exclude", "show"])
          .describe("What to do: add a new source, remove one, exclude one (skips it in the brief but keeps it listed), or show the current config."),
        source: z
          .string()
          .optional()
          .describe("The source name or URL to act on. Not required for show."),
      },
      async ({ action, source }) => {
        // Sanitize `source` before embedding in instruction text — prevents prompt
        // injection if a user passes adversarial content as the source name.
        const safeSource = source
          ? source.replace(/[\r\n]+/g, ' ').replace(/[^\x20-\x7E]/g, '').slice(0, 120).trim()
          : null;
        const sourceLabel = safeSource ?? "[source]";

        const actionInstructions: Record<string, string> = {
          show: "Use the Read file tool to read WARMUP.md from the user's project root. If you do not know the project root path, call list_artifacts — the html_path from 'the-warmup' reveals the workspace folder, and WARMUP.md lives there. Display current active, quiet, and excluded sources in a clean summary.",
          add: `Use the Read file tool to read WARMUP.md first. Then add the source named below to the user's active sources. Ask for the URL and tier (Authoritative / Research / News / Vendor) if not provided. Format: "- Name | URL | active". Show the proposed addition for confirmation before writing.`,
          remove: `Use the Read file tool to read WARMUP.md first. Then remove the source named below from WARMUP.md entirely. Show the current entry and confirm with the user before writing.`,
          exclude: `Use the Read file tool to read WARMUP.md first. Then mark the source named below as excluded by moving it to the ## Excluded Sources section with format: "- Name | URL | excluded". Confirm before writing.`,
        };

        return {
          content: [
            {
              type: "text" as const,
              text:
                `# The Warmup — Config\n\n` +
                `${actionInstructions[action]}\n\n` +
                (safeSource ? `## Target source\n\n\`\`\`\n${sourceLabel}\n\`\`\`\n\n` : '') +
                `## Rules\n\n` +
                `- Always use the Read file tool (not bash) to read the current WARMUP.md before making any changes.\n` +
                `- Show the proposed change clearly before writing.\n` +
                `- Preserve all other config fields — only touch the section being modified.\n` +
                `- You MUST update the \`updated\` field to today's date (YYYY-MM-DD) after any write. This is required — it drives the source emergence check schedule.\n\n` +
                `## Reference sections (call warmup_get_skill with the section param as needed)\n\n` +
                `- CONFIGURE mode rules and source emergence check: warmup_get_skill({ section: "config", intent: "Loading config rules" })\n` +
                `- Source suites (for recommending sources to add): warmup_get_skill({ section: "sources", intent: "Loading source suites for recommendation" })\n` +
                `- WARMUP.md config format: warmup_get_skill({ section: "warmupmd", intent: "Checking WARMUP.md format" })`,
            },
          ],
        };
      }
    );

    // ══════════════════════════════════════════════════════════════════════════
    // THE SPOTTER
    // ══════════════════════════════════════════════════════════════════════════

    this.server.tool(
      "spotter_get_skill",
      "Returns a section of The Spotter SKILL.md. Use the 'section' param to load only what you need — avoids loading the full ~29KB document every call. Sections: 'areas' (all nine review areas + sub-checks — load this for grading), 'review' (review mode output format), 'iterate' (iterate mode output format), 'build' (build mode output format), 'output' (all three output formats together), 'schema' (structured JSON output schema), 'antipatterns' (what the skill must not do), 'full' (everything — use only when a specific section is insufficient).",
      {
        intent: intentField,
        section: z
          .enum(["areas", "review", "iterate", "build", "output", "schema", "antipatterns", "full"])
          .optional()
          .describe(
            "Which section to return. Defaults to 'full'. Prefer targeted sections: 'areas' when walking area checks, 'review'/'iterate'/'build' for the relevant output format, 'schema' when emitting structured JSON output, 'antipatterns' for a quick anti-pattern check."
          ),
      },
      async ({ section }) => ({
        content: [{ type: "text" as const, text: getSpotterSkillSection(SPOTTER_SKILL_MD, section ?? "full") }],
      })
    );

    this.server.tool(
      "spotter_get_examples",
      "Returns worked examples from area-examples.md — strong (✓), needs-work (⚠️), and missing (✗) variants with teaching notes. Use the 'area' param (1–9) to load examples for a single area, or 0 for all areas. Prefer loading one area at a time during a review to avoid loading the full 64KB document.",
      {
        intent: intentField,
        area: z
          .number()
          .int()
          .min(0)
          .max(9)
          .optional()
          .describe(
            "Which area to load examples for (1–9). Pass 0 to load all areas (64KB — use sparingly). Defaults to 0 (all). Prefer specific area numbers during a review."
          ),
      },
      async ({ area }) => ({
        content: [{ type: "text" as const, text: getSpotterAreaExamples(SPOTTER_AREA_EXAMPLES_MD, area ?? 0) }],
      })
    );

    this.server.tool(
      "spotter_get_calibration_epic",
      "Returns synthetic calibration epic #1 — a B2B security epic with deliberate gaps. Running a review against it should produce verdict 'Needs polish' with specific gaps on Areas 1, 4, 5, 6, 8, and 9. Use to verify a fresh install is producing expected output. For all three calibration epics, call spotter_get_calibration_epics instead.",
      { intent: intentField },
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_SYNTHETIC_EPIC_MD }],
      })
    );

    this.server.tool(
      "spotter_get_calibration_epics",
      "Returns all three synthetic calibration epics concatenated. Use to run a batch calibration pass or to compare how The Spotter grades epics at different quality levels. Epic 1 targets 'Needs polish' (gaps on Areas 1, 4, 5, 6, 8, 9). Epics 2 and 3 are well-formed security platform epics for grading range calibration.",
      { intent: intentField },
      async () => ({
        content: [
          {
            type: "text" as const,
            text:
              `# Spotter Calibration Epics — All Three\n\n` +
              `---\n\n## Epic 1 (gap-heavy — target verdict: Needs polish)\n\n` +
              SPOTTER_SYNTHETIC_EPIC_MD +
              `\n\n---\n\n## Epic 2 (MITRE ATT&CK Coverage Insights)\n\n` +
              SPOTTER_SYNTHETIC_EPIC_2_MD +
              `\n\n---\n\n## Epic 3 (Adversary-Informed Vulnerability Prioritization)\n\n` +
              SPOTTER_SYNTHETIC_EPIC_3_MD,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_list_areas",
      "Returns the nine review areas with names and weight notes. Useful for clients that want to render area cards or for an agent that needs a quick overview before loading the full SKILL.md.",
      { intent: intentField },
      async () => ({
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ version: SPOTTER_VERSION, areas: SPOTTER_AREAS }, null, 2),
          },
        ],
      })
    );

    this.server.tool(
      "spotter_get_template",
      `Returns a complete, self-contained artifact HTML document with SPOTTER_DATA already injected — ready to write to disk and pass to create_artifact or update_artifact. Build your complete SPOTTER_DATA object first, then pass it as a JSON string. The server inlines the renderer and returns filled, artifact-ready HTML. Write the result to disk and call create_artifact or update_artifact. Never reconstruct or invent the HTML yourself — the correct design lives only in this tool.

SPOTTER_DATA schema (all fields):
{
  mode: "review",                    // always "review" for a completed review
  epic: {
    name: string,                    // Epic title (required)
    company?: string,                // Company name (optional)
    teamShape?: string,              // e.g. "3 eng · 1 design" (optional)
    window?: string,                 // e.g. "6 weeks" (optional)
    attempt?: number,                // Attempt/sprint number (optional)
    epicBody: string,                // REQUIRED — the full verbatim epic text; rendered at the bottom of the report under "Original Epic"
  },
  user: {
    name: string,                    // PM's first name (required)
    timestamp?: string,              // e.g. "16 May 2026 · 14:22 ET" (optional, defaults to today)
  },
  areas: Array<{
    id: string,                      // kebab-case slug, e.g. "user-and-problem"
    n: number,                       // 1–9
    name: string,                    // Display name (use SKILL.md area names exactly)
    category: string,                // Grouping label — see mapping below
    question: string,                // The one-line area question
    judges: [string|null, string|null, string|null],  // 3 vote slots: "w" (white), "r" (red), or null
    finding: string,                 // The main review observation (1–3 sentences)
    spotterPull?: string|null,       // Key pull quote — the "you could strengthen this by..." insight (optional)
    handNote?: string|null,          // Most critical 1-liner, rendered in Permanent Marker (optional — use sparingly)
    active?: boolean,                // false for a completed review
  }>
}

Judge encoding — map SKILL.md grades to the three-light system:
  ✓ Pass       → ["w", "w", "w"]   (all white — Good Lift)
  ⚠️ Needs work → ["w", "w", "r"]   (two white, one red — still a Lift, but one judge flagged)
  ✗ Missing    → ["r", "r", "r"]   (all red — No-Lift, triggers rerack)

Area name + category mapping (use exactly, in order):
  n:1  id:"user-and-problem"       name:"The user & the problem"          category:"Foundation"
  n:2  id:"competitive-landscape"  name:"Competitive landscape"           category:"Strategy"
  n:3  id:"strategic-moat"         name:"Strategic differentiation"       category:"Strategy"
  n:4  id:"solution-approach"      name:"Solution approach"               category:"Solution"
  n:5  id:"holistic-impact"        name:"Holistic impact"                 category:"Impact"
  n:6  id:"packaging-pricing"      name:"Packaging & pricing"             category:"GTM"
  n:7  id:"launch-readiness"       name:"Launch readiness"                category:"Launch"
  n:8  id:"post-launch-ownership"  name:"Post-launch ownership"           category:"Post-launch"
  n:9  id:"trust-governance"       name:"Trust, governance & auditability" category:"Governance"`,
      {
        intent: intentField,
        spotter_data: z
          .string()
          .describe(
            "The full SPOTTER_DATA JSON object serialised as a string via JSON.stringify(). " +
            "Required. The server injects it server-side and returns filled, artifact-ready HTML."
          ),
      },
      async ({ spotter_data }) => {
        // XSS safety: epic text can contain </script> which breaks the script tag
        // if injected verbatim. Escape before injection — same as warmup_get_template.
        //
        // Replacer-function safety: epic text can contain $', $&, $` (price strings,
        // technical content). A replacer function bypasses special-sequence expansion.
        const safe = spotter_data.replace(/<\/script>/gi, '<\\/script>');
        const PLACEHOLDER = `window.SPOTTER_DATA = null; /* spotter-data-placeholder */`;

        // Build the shell-inlined template at request time. Inlining the renderer
        // (spotter-shell.rawjs) makes the artifact fully self-contained — no external
        // script fetch needed, compatible with Cowork's Content Security Policy.
        const shellInlined =
          `<!DOCTYPE html>\n` +
          `<!-- spotter-engine: v${SPOTTER_VERSION} -->\n` +
          `<html lang="en">\n` +
          `<head>\n` +
          `  <meta charset="UTF-8">\n` +
          `  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n` +
          `  <title>The Spotter \xB7 Field Review</title>\n` +
          `</head>\n` +
          `<body>\n` +
          `<script id="spotter-data">\n` +
          `${PLACEHOLDER}\n` +
          `</script>\n` +
          `<script>\n` +
          `${SPOTTER_SHELL_JS}\n` +
          `</script>\n` +
          `</body>\n` +
          `</html>`;

        const filled = shellInlined.replace(PLACEHOLDER, () => `window.SPOTTER_DATA = ${safe};`);
        const injected = filled !== shellInlined;
        return {
          content: [
            {
              type: "text" as const,
              text: injected
                ? filled
                : `[spotter_get_template ERROR: SPOTTER_DATA placeholder not found — injection failed. Do NOT use raw output. Call spotter_get_template again.]`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "spotter_review",
      "Primes the agent to review a B2B product epic using The Spotter's nine-area framework. Returns instructions and the epic — agent loads framework sections on demand via spotter_get_skill.",
      {
        intent: intentField,
        epic: z.string().min(50).max(20000).describe("The full text of the epic to review."),
      },
      async ({ epic }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter v${SPOTTER_VERSION} — Review Mode\n\n` +
              `## The deliverable\n\n` +
              `The output of this review is an HTML file written to the user's workspace folder and registered in the Cowork artifact panel. That file IS the review.\n\n` +
              `The chat message you post at the end is a summary pointer to the artifact — not the review itself.\n\n` +
              `**Task failure:** If grades, findings, or verdicts appear in chat before the artifact file exists on disk, the task has failed. Build the artifact first. Always.\n\n` +
              `## Sequence\n\n` +
              `Execute steps 1 → 2 → 3 → 4. No grades, findings, or verdicts to chat until Step 4.\n\n` +
              `1. SETUP    — call list_artifacts → find workspace path → determine PATH A or B\n` +
              `2. GRADE    — load framework → grade all 9 areas silently → build SPOTTER_DATA\n` +
              `3. ARTIFACT — write HTML to disk → register artifact  ← THIS IS THE DELIVERABLE\n` +
              `4. CONFIRM  — post grade summary to chat (only after artifact exists)\n\n` +
              `## Permitted tools\n\n` +
              `Only these tools may be used. Everything else is forbidden.\n\n` +
              `  MCP:  list_artifacts · create_artifact · update_artifact\n` +
              `        spotter_get_skill · spotter_get_examples · spotter_get_template\n` +
              `  File: Read · Write · Edit · Grep\n\n` +
              `  Forbidden always: bash · mcp__workspace__bash · WebFetch · web_fetch · curl · wget\n\n` +
              `Note: spotter_get_template is an MCP tool call to the Loadout server — it is required and permitted. It is not a web fetch.\n\n` +
              `## Step 1 — Setup\n\n` +
              `a. Call list_artifacts.\n` +
              `b. Find workspace root: take the html_path of any existing artifact and strip the filename.\n` +
              `   e.g. "/Users/jane/Projects/loadout/warmup-brief.html" → workspace root is "/Users/jane/Projects/loadout"\n` +
              `   If no artifacts exist, use the Cowork selected folder from your system context.\n` +
              `c. Set target file: [workspace-root]/spotter-[epic-slug].html\n` +
              `   e.g. epic "Comments on Dashboards" → spotter-comments-on-dashboards.html\n` +
              `d. Determine path:\n` +
              `   • No Spotter artifact for this epic in list_artifacts → PATH B\n` +
              `   • Artifact exists → Read lines 1–3 of the workspace file (offset:0, limit:3)\n` +
              `     Line 2 is exactly "<!-- spotter-engine: v${SPOTTER_VERSION} -->" → PATH A\n` +
              `     Anything else, or cannot read → PATH B\n\n` +
              `The workspace root is always a user folder like /Users/[name]/…\n` +
              `Never use a path containing "Application Support", "sessions", "outputs", or "uploads".\n\n` +
              `## Step 2 — Grade (silent — no chat output)\n\n` +
              `a. Call spotter_get_skill({ section: "areas", intent: "Loading Spotter review framework" }).\n` +
              `b. Grade all nine areas against the epic. Keep grades internal — do not write them to chat.\n` +
              `   ✓ Pass → ["w","w","w"]  ·  ⚠️ Needs work → ["w","w","r"]  ·  ✗ Missing → ["r","r","r"]\n` +
              `c. Area 1 has 8 sub-checks and carries disproportionate weight.\n` +
              `   Area 9 is a gate: ✗ Missing on any B2B feature with agent actions or data access caps verdict at "Not ready."\n` +
              `d. Call spotter_get_examples({ area: N, intent: "..." }) if you need calibration on any area.\n` +
              `e. Build SPOTTER_DATA:\n` +
              `   epic: { name, company, teamShape, window, attempt, epicBody (full raw epic text verbatim) }\n` +
              `   areas: [ { id, n, name, category, question, judges, finding (1–3 sentences),\n` +
              `              spotterPull ("you could strengthen this by…"), handNote (optional 1-liner) } ]\n` +
              `   Voice: every flag is "you could strengthen this by…" — never "you missed" or "this is wrong."\n\n` +
              `## Step 3 — Artifact  ← Write the file. This is the output.\n\n` +
              `### PATH A (engine version matched — edit data block only)\n\n` +
              `a. Grep workspace file for '<script id="spotter-data">'.\n` +
              `b. Read that script block (2–3 lines).\n` +
              `c. Edit: replace the entire block with:\n` +
              `     <script id="spotter-data">\n` +
              `     window.SPOTTER_DATA = [JSON.stringify(SPOTTER_DATA)];\n` +
              `     </script>\n` +
              `d. Call update_artifact with the workspace file path.\n\n` +
              `### PATH B (new file or engine mismatch — three tool calls, in order)\n\n` +
              `B-1. Call spotter_get_template({ intent: "…", spotter_data: JSON.stringify(SPOTTER_DATA), epicBody: [full raw epic text] })\n` +
              `     This returns a complete, self-contained HTML document with the renderer already inlined.\n` +
              `     There is nothing to fetch, verify, or modify. If it fails, retry once then STOP.\n\n` +
              `B-2. Call Write immediately — the content parameter is the exact string returned by B-1.\n` +
              `     file_path: [workspace-root]/spotter-[epic-slug].html\n` +
              `     content:   the exact string returned by spotter_get_template, unmodified\n\n` +
              `     IMPORTANT: Do not Read, Grep, move, or bash the template file before writing.\n` +
              `     Do not treat the template as a file on disk — it is a string in memory from B-1.\n` +
              `     "Too large to read" and "needs bash to move" are not valid reasons to deviate.\n` +
              `     Write the string directly. If Write fails, report the error and stop.\n\n` +
              `B-3. Call create_artifact (first run) or update_artifact (re-run).\n` +
              `     id: "spotter-[epic-slug]"   html_path: the same file_path used in B-2\n\n` +
              `Step 3 is complete when the file is on disk and registered. Do not proceed to Step 4 until both B-2 and B-3 have succeeded.\n\n` +
              `## Step 4 — Confirm (artifact must already exist before this step)\n\n` +
              `Write this and nothing else:\n\n` +
              `  Review complete — open the artifact panel to see the full report.\n\n` +
              `  **[Overall verdict]** · [N] of 9 areas passed\n\n` +
              `  | # | Area | Grade |\n` +
              `  |---|------|-------|\n` +
              `  | 1 | [name] | ✓ Pass / ⚠️ Needs work / ✗ Missing |\n` +
              `  | … |\n\n` +
              `  [1–2 sentences: biggest strength and the single most important thing to address.]\n\n` +
              `  *Full report → artifact panel. Questions? Reply here.*\n\n` +
              `## Epic\n\n\`\`\`\n${epic}\n\`\`\`\n\n` +
              `Read all instructions above before starting. Then execute steps 1 → 2 → 3 → 4.`,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_build",
      "Primes the agent to help a PM build a new epic from scratch using The Spotter's framework. The agent walks the PM through the nine areas with guiding questions, lingering on Area 1 before moving on. Output is a polished draft epic.",
      {
        intent: intentField,
        feature: z.string().describe("Brief description of the feature or capability the PM wants to build an epic for."),
      },
      async ({ feature }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter v${SPOTTER_VERSION} — Build Mode\n\n` +
              `A PM is building an epic for: **${feature}**.\n\n` +
              `## How to run build mode\n\n` +
              `1. Call spotter_get_skill({ section: "areas", intent: "Loading Spotter build framework" }) to load the area framework and sub-checks before starting.\n` +
              `2. Walk the PM through the nine areas with guiding questions. Ask — don't lecture.\n` +
              `3. Linger on Area 1: empathy (A), current state (B), why-not-solved (C), no solutioning (D), scope/value framing (E), assumptions surfaced (F), alternatives considered (G), epistemic openness (H). Get real answers on all eight sub-checks before moving to Area 2.\n` +
              `4. If the PM rushes past the user, gently slow them down: "Before we go further, can you tell me what it actually feels like to be this user on a hard day?"\n` +
              `5. Call spotter_get_skill({ section: "build", intent: "Loading build output format" }) when ready to draft the final epic.\n` +
              `6. The output at the end is a polished draft epic structured by area.\n` +
              `7. After delivering the draft, post this closing line exactly:\n` +
              `   "Draft complete. Want to run it through The Spotter review to grade all nine areas and get a full report?"\n\n` +
              `## Voice\n\n` +
              `Critique, not criticism. Ask questions; don't lecture. Every flag is "you could strengthen this by..." — never "you missed..."\n\n` +
              `Begin with Area 1. Ask about the user first.`,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_iterate",
      "Primes the agent to push a partial draft epic forward. The agent engages only the areas that have content, asks targeted questions for each gap, and offers structure where the PM is stuck.",
      {
        intent: intentField,
        draft: z.string().min(50).max(20000).describe("The current partial draft of the epic. Can be incomplete or rough."),
      },
      async ({ draft }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter v${SPOTTER_VERSION} — Iterate Mode\n\n` +
              `A PM has a partial draft they want to push forward.\n\n` +
              `## How to run iterate mode\n\n` +
              `1. Call spotter_get_skill({ section: "areas", intent: "Loading Spotter framework for iteration" }) to load the area framework and sub-checks before engaging.\n` +
              `2. Scan the draft for which areas have content — engage only those.\n` +
              `3. For each area with content: acknowledge what's there, ask one or two specific questions that push the section forward, offer structure where the PM is stuck.\n` +
              `4. For areas not yet drafted, ask: "Have you started thinking about [area]? I can help you frame it."\n` +
              `5. Call spotter_get_skill({ section: "iterate", intent: "Loading iterate output format" }) for the output format guidance.\n\n` +
              `## Voice\n\n` +
              `Critique, not criticism. Each suggestion uses "you could strengthen this by..." framing — never "you missed..."\n\n` +
              `## Draft to iterate on\n\n\`\`\`\n${draft}\n\`\`\`\n\n` +
              `Load the areas (step 1), then walk the areas present in the draft. Push each one forward.`,
          },
        ],
      })
    );

    // ══════════════════════════════════════════════════════════════════════════
    // ── approach_get_skill ──────────────────────────────────────────────────
    this.server.tool(
      "approach_get_skill",
      "Retrieve a section of The Approach SKILL.md. " +
      "Sections: intake, research, schema, render, rules, config, full.\n\n" +
      "Load sections on demand as you reach each phase — do not load 'full' unless debugging. " +
      "The 'render' section includes the Summary line output instructions.",
      {
        intent: intentField,
        section: z.enum(["intake","research","schema","render","rules","config","full"]).describe(
          "Which section to return. intake=workflow overview, research=data gathering, " +
          "schema=output format, render=template injection+summary line, rules=editorial guidelines, " +
          "config=APPROACH.md format, full=entire document."
        ),
      },
      async ({ section }) => {
        const text = getApproachSkillSection(APPROACH_SKILL_MD, section);
        return { content: [{ type: "text" as const, text }] };
      }
    );

    // ── approach_get_template ────────────────────────────────────────────────
    this.server.tool(
      "approach_get_template",
      "DEPRECATED in Cowork environments — do NOT call this tool. " +
      "The response (~131KB) exceeds Cowork's inline context limit and will be offloaded " +
      "to a temp file the agent cannot use. Follow the RENDER Phase in SKILL.md instead: " +
      "Read approach-template.html from disk, Write to approach-artifact.html, then Edit the " +
      "__APPROACH_DATA__ placeholder. This tool is retained for non-Cowork callers only.",
      {
        intent: intentField,
        approach_data: z.string().max(50000).describe(
          "The APPROACH_DATA JSON string produced by The Approach workflow. " +
          "Must be valid JSON matching the APPROACH_DATA schema (v0.1.0)."
        ),
      },
      async ({ approach_data }) => {
        const safe = approach_data.replace(/<\/script>/gi, '<\\/script>');
        const PLACEHOLDER = "__APPROACH_DATA__";
        const filled = APPROACH_TEMPLATE_HTML.replace(PLACEHOLDER, () => safe);
        const injected = filled !== APPROACH_TEMPLATE_HTML;
        if (!injected) {
          return {
            content: [{
              type: "text" as const,
              text: "[approach_get_template] ERROR: placeholder __APPROACH_DATA__ not found in template.",
            }],
          };
        }
        return { content: [{ type: "text" as const, text: filled }] };
      }
    );

    // ── approach_run ─────────────────────────────────────────────────────────
    this.server.tool(
      "approach_run",
      "Prime the agent to run The Approach workflow end-to-end: read the caller's APPROACH.md " +
      "config, execute INTAKE then RESEARCH then schema assembly then template render then artifact creation.",
      {
        intent: intentField,
        approach_md_path: z.string().max(500).optional().describe(
          "Path to the APPROACH.md config file. Defaults to APPROACH.md in the workspace root if omitted."
        ),
      },
      async ({ approach_md_path }) => {
        const safePath = approach_md_path
          ? approach_md_path.replace(/[^\x20-\x7E]/g, "").replace(/[<>'"]/g, "")
          : "";
        const pathHint = safePath
          ? `The APPROACH.md config is at: ${safePath}`
          : "Look for APPROACH.md in the workspace root. If not found, ask the user.";
        return {
          content: [{
            type: "text" as const,
            text: [
              `# The Approach v${THE_APPROACH_VERSION} — Workflow`,
              "",
              "Run the workflow in order: INTAKE → RESEARCH → SCHEMA → RENDER → SUMMARY.",
              "Load each phase with approach_get_skill as you reach it — do not load 'full'.",
              "",
              "  • approach_get_skill(section:'intake')    — Step 0: collect inputs from user",
              "  • approach_get_skill(section:'research')  — Step 1: run search batches",
              "  • approach_get_skill(section:'schema')    — Step 1→2: assemble APPROACH_DATA",
              "  • approach_get_skill(section:'render')    — Step 2: write artifact (includes Summary line)",
              "  • approach_get_skill(section:'rules')     — validate editorial quality",
              "  • approach_get_skill(section:'config')    — only if APPROACH.md config is needed",
              "",
              pathHint,
            ].join("\n"),
          }],
        };
      }
    );


    // RESOURCES
    this.server.resource(
      "approach-skill",
      "loadout://approach/skill",
      { description: "The Approach SKILL.md — structured decision-brief workflow reference" },
      async () => ({
        contents: [{
          uri: "loadout://approach/skill",
          mimeType: "text/markdown",
          text: APPROACH_SKILL_MD,
        }],
      })
    );

    // ══════════════════════════════════════════════════════════════════════════

    this.server.resource(
      "warmup-skill",
      "loadout://warmup/skill",
      {
        name: "The Warmup — SKILL.md",
        description: "Full framework: philosophy, three modes, setup flow, source tiers, section structure, output format, safety protocol.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "loadout://warmup/skill", mimeType: "text/markdown", text: WARMUP_SKILL_MD }],
      })
    );

    this.server.resource(
      "spotter-skill",
      "loadout://spotter/skill",
      {
        name: "The Spotter — SKILL.md",
        description: "Full framework: philosophy, modes, nine review areas, sub-checks, output formats, anti-patterns, structured output schema.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "loadout://spotter/skill", mimeType: "text/markdown", text: SPOTTER_SKILL_MD }],
      })
    );

    this.server.resource(
      "spotter-examples",
      "loadout://spotter/examples",
      {
        name: "The Spotter — Area Examples",
        description: "64 worked examples across nine review areas with teaching notes.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "loadout://spotter/examples", mimeType: "text/markdown", text: SPOTTER_AREA_EXAMPLES_MD }],
      })
    );

    this.server.resource(
      "spotter-calibration-2",
      "loadout://spotter/calibration/2",
      {
        name: "The Spotter — Calibration Epic 2",
        description: "Synthetic B2B security epic: MITRE ATT&CK Coverage Insights. Well-formed epic for grading range calibration.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "loadout://spotter/calibration/2", mimeType: "text/markdown", text: SPOTTER_SYNTHETIC_EPIC_2_MD }],
      })
    );

    this.server.resource(
      "spotter-calibration-3",
      "loadout://spotter/calibration/3",
      {
        name: "The Spotter — Calibration Epic 3",
        description: "Synthetic B2B security epic: Adversary-Informed Vulnerability Prioritization. Well-formed epic for grading range calibration.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "loadout://spotter/calibration/3", mimeType: "text/markdown", text: SPOTTER_SYNTHETIC_EPIC_3_MD }],
      })
    );

    this.server.resource(
      "brand-css",
      "loadout://brand-css",
      {
        name: "Mission Built — Brand CSS",
        description: "The Mission Built design system as a CSS stylesheet.",
        mimeType: "text/css",
      },
      async () => ({
        contents: [{ uri: "loadout://brand-css", mimeType: "text/css", text: brandCss() }],
      })
    );
  }
}

// ── Worker entry point ────────────────────────────────────────────────────────

export default new OAuthProvider({
  apiRoute: "/sse",
  apiHandler: MissionBuiltMCP.mount("/sse") as any,
  defaultHandler: authHandler as any,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register",
});
