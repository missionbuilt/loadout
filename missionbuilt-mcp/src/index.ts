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
import SPOTTER_SKILL_MD from "./skill-content/spotter/SKILL.md";
import SPOTTER_AREA_EXAMPLES_MD from "./skill-content/spotter/area-examples.md";
import SPOTTER_SYNTHETIC_EPIC_MD from "./skill-content/spotter/synthetic-epic.md";
import SPOTTER_SYNTHETIC_EPIC_2_MD from "./skill-content/spotter/synthetic-epic-2.md";
import SPOTTER_SYNTHETIC_EPIC_3_MD from "./skill-content/spotter/synthetic-epic-3.md";
import SPOTTER_TEMPLATE_HTML from "./skill-content/spotter/spotter-template.html";
import WARMUP_TEMPLATE_HTML from "./skill-content/warmup/warmup-template.html";
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
      "Return the data-filled Warmup brief HTML in paginated 900-line chunks. " +
      "Pass warmup_data on EVERY chunk call — the server re-injects it each time (stateless). " +
      "Fonts are baked into the template; the brief makes no MCP calls at runtime. " +
      "Call with chunk:0 first; read <!-- WARMUP_TOTAL_CHUNKS: N --> from the response to learn the total. " +
      "Write chunk 0 to disk, then for chunks 1..N-1 call with chunk:i and Edit-replace <!-- __WARMUP_SENTINEL__ --> with each chunk. " +
      "After assembly, call create_artifact (no mcp_tools needed — fonts are baked). " +
      "Do NOT use bash to move files — use the Read/Write file tools.",
      {
        intent: intentField,
        chunk: z.number().int().min(0).default(0).describe(
          "Which 900-line chunk to return (0-indexed). Default: 0. Read <!-- WARMUP_TOTAL_CHUNKS: N --> from chunk 0 to learn the total."
        ),
        warmup_data: z.string().max(300000).describe(
          "The WARMUP_DATA JSON string produced by the Warmup workflow. Required on EVERY chunk call — the server re-injects it each time. Must be valid JSON."
        ),
      },
      async ({ chunk = 0, warmup_data }) => {
        try { JSON.parse(warmup_data); } catch (e) {
          return { content: [{ type: "text" as const, text: `[warmup_get_template] ERROR: warmup_data is not valid JSON — ${String(e)}. Fix the WARMUP_DATA object and retry.` }] };
        }
        // XSS + $-expansion safety: escape </script>, inject via replacer function.
        const safe = warmup_data.replace(/<\/script>/gi, '<\\/script>');
        const savedAt = new Date().toISOString().replace(/\.\d+Z$/, '.000Z');
        let filled = WARMUP_TEMPLATE_HTML.replace("__WARMUP_DATA__", () => safe);
        if (filled === WARMUP_TEMPLATE_HTML) {
          return { content: [{ type: "text" as const, text: "[warmup_get_template] ERROR: placeholder __WARMUP_DATA__ not found in template. Report this to the developer." }] };
        }
        filled = filled.replace("__WARMUP_SAVED_AT__", () => savedAt);
        const CHUNK_LINES = 900;
        const SENTINEL    = '<!-- __WARMUP_SENTINEL__ -->';
        const lines       = filled.split('\n');
        const totalChunks = Math.ceil(lines.length / CHUNK_LINES);
        if (chunk === 0) {
          const chunkLines = lines.slice(0, CHUNK_LINES);
          chunkLines.unshift(`<!-- WARMUP_TOTAL_CHUNKS: ${totalChunks} -->`);
          if (totalChunks > 1) chunkLines.push(SENTINEL);
          return { content: [{ type: "text" as const, text: chunkLines.join('\n') }] };
        }
        const startLine = chunk * CHUNK_LINES;
        if (startLine >= lines.length) {
          return { content: [{ type: "text" as const, text: `[warmup_get_template ERROR: chunk:${chunk} is out of range — total chunks is ${totalChunks}. Stop and report this error.]` }] };
        }
        const endLine    = Math.min((chunk + 1) * CHUNK_LINES, lines.length);
        const chunkLines = lines.slice(startLine, endLine);
        if (endLine < lines.length) chunkLines.push(SENTINEL);
        return { content: [{ type: "text" as const, text: chunkLines.join('\n') }] };
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
                `6. Run the brief using the config you just saved. Call warmup_run with the config_summary parameter set to the exact WARMUP.md content you just wrote — this skips the Read step and provides the schema guidance needed to build WARMUP_DATA correctly. Do NOT build WARMUP_DATA manually or call warmup_get_template directly from setup — the warmup_run tool handles all of that.\n\n` +
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
      "Primes the agent to generate a Warmup intelligence brief. Reads the user's WARMUP.md config, fetches live intelligence from each active source, synthesizes it into sections, runs link safety verification, synthesizes WARMUP_DATA, and renders a self-contained brief artifact. Data is injected at render time and fonts are baked in; nothing calls the server at runtime.",
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
                `## How it works (read this once)\n\n` +
                `The brief is a self-contained HTML artifact. You build WARMUP_DATA from fresh searches, then render it with warmup_get_template — the server injects your data and stamps the generated-at time, and fonts are baked into the file. No KV, no auto-refresh, no runtime calls back to the server. Each run writes a fresh brief.\n\n` +
                `## Before starting\n\n` +
                `Ensure these deferred tools are loaded — load them now via ToolSearch if any are missing:\n\n` +
                `- warmup_get_template (renders the brief)\n` +
                `- list_artifacts, create_artifact, update_artifact (Cowork)\n` +
                `- WebSearch\n\n` +
                `## Permitted tools\n\n` +
                `  MCP:  list_artifacts · create_artifact · update_artifact\n` +
                `        warmup_get_skill · warmup_get_template · WebSearch\n` +
                `  File: Read · Write · Edit · Grep\n\n` +
                `  Forbidden always: bash · mcp__workspace__bash · WebFetch · web_fetch · curl · wget\n\n` +
                `## How to generate the brief\n\n` +
                `1. WORKSPACE — call list_artifacts.\n` +
                `   • "the-warmup" exists → take its html_path and strip the filename to get the workspace root.\n` +
                `   • No "the-warmup" artifact → use the user's selected workspace folder from your system context.\n` +
                `     A correct root looks like /Users/[name]/Projects/[folder]. It must NOT contain "Application Support", "sessions", "outputs", "uploads", "local-agent", or "tmp".\n` +
                `   Read [workspace-root]/WARMUP.md. If missing, run warmup_setup first.\n\n` +
                `2. ARTIFACT ACTION — set artifact_action = "create" if no "the-warmup" artifact exists in list_artifacts, otherwise "update". Either way you render a fresh brief with this run's data (there is no skip path now that data is injected at render time).\n` +
                `   Output one chat line: "📋 Fetching intelligence now."\n\n` +
                `3. FETCH PHASE — run all batches concurrently in a single parallel pass. Standard depth: top 5 results / 200 words. Deep: top 10 / 400 words. Reject items where item.date < lookback_start. If skip_scan: true in WARMUP.md, skip step 4 and set config.skipScan: true, safety.domains: [], safety.totalUrls: 0.\n\n` +
                `   CISO mode compound batch queries (concurrent, NOT one-per-source):\n` +
                `   | Batch | Query pattern |\n` +
                `   |---|---|\n` +
                `   | Gov pulse | \`(site:cisa.gov OR site:nsa.gov OR site:ic3.gov OR site:ftc.gov) advisory alert after:YYYY-MM-DD\` |\n` +
                `   | Research | \`(site:microsoft.com/security OR site:crowdstrike.com/blog OR site:redcanary.com/blog OR site:wiz.io/blog OR site:unit42.paloaltonetworks.com) [sector] threat after:YYYY-MM-DD\` |\n` +
                `   | CVE sweep | \`(site:nvd.nist.gov OR site:cisa.gov/known-exploited-vulnerabilities) CVE critical after:YYYY-MM-DD\` |\n` +
                `   | News | \`(site:bleepingcomputer.com OR site:securityweek.com OR site:krebsonsecurity.com OR site:thehackernews.com OR site:darkreading.com) [sector] after:YYYY-MM-DD\` |\n` +
                `   | Market | \`[company OR sector] acquisition OR breach OR regulatory site:reuters.com OR site:bloomberg.com after:YYYY-MM-DD\` |\n` +
                `   | Social | \`[sector] security debate OR disclosure site:reddit.com/r/netsec after:YYYY-MM-DD\` |\n` +
                `   | Interests | One targeted query per special interest |\n\n` +
                `   For Product Leader and Custom modes, call warmup_get_skill({ section: "sources" }) for the mode-specific batch patterns.\n\n` +
                `4. SAFETY — run link safety verification on every URL (unless skip_scan).\n\n` +
                `5. SYNTHESIZE WARMUP_DATA — every field below is required:\n\n` +
                `   config (all fields required):\n` +
                `     name, mode, company, sector, region — copy verbatim from WARMUP.md\n` +
                `     reportDate: full display string e.g. "Monday, 18 May 2026" (user timezone)\n` +
                `     updated: short display string e.g. "18 May 2026"\n` +
                `     lastRun: ISO date "YYYY-MM-DD"\n` +
                `     dateRange: display string e.g. "May 11 – May 18, 2026"\n` +
                `     sourcesActive: int  sourcesQuiet: int\n` +
                `     showQuote: true (JSON boolean — never false, never omit)\n` +
                `     scanTime: "HH:MM TZ" — 24-hour, with a tz label\n` +
                `     timezone: copy from WARMUP.md (e.g. "ET", "PT", "UTC")\n` +
                `     totalLinks: int (must equal safety.totalUrls)\n` +
                `     vendors: copy from WARMUP.md; "" if blank, never omit\n` +
                `     searchDepth: "standard" | "deep" (copy from WARMUP.md)\n` +
                `     skipScan: true if skip_scan in WARMUP.md, otherwise omit\n` +
                `     (no fontToolName — fonts are baked into the template)\n\n` +
                `   sections[] — each section MUST have all four fields or the renderer throws:\n` +
                `     id: kebab-case DOM id (e.g. "threat", "emerging", "research", "industry", "social", "interests")\n` +
                `     label: heading string\n` +
                `     sub: standing editorial deck — one sentence describing the section\n` +
                `     note: null (or today-only run caveat — never repeat sub here)\n` +
                `     items: array — MUST be an array, even [] for a quiet section\n\n` +
                `   items[] — each item MUST have all five fields:\n` +
                `     dot: "d1" | "d2" | "d3" | "d4"  src: source name  tags: array ([] is fine)\n` +
                `     url: verified-safe URL  hl: headline  body: 2-3 sentence summary  date: "YYYY-MM-DD"\n` +
                `     Lead item (items[0]) only: deck — one italic "so what?" sentence\n\n` +
                `   sources[] — each entry MUST have: nm, dom, dot ("d1"-"d4"), ct ("N items" or "—"), status ("active"|"quiet"|"excluded")\n\n` +
                `   safety: domains [{domain, verdict:"ALLOWLISTED"|"CLEAN"}] — length must equal active sources count; [] if skipScan\n` +
                `           totalUrls: int (0 if skipScan)  flagged: int  scannedAt: ""\n\n` +
                `6. RENDER — write the brief with your data injected by the server.\n` +
                `   a) Call warmup_get_template({ chunk: 0, warmup_data: JSON.stringify(WARMUP_DATA) }). Read <!-- WARMUP_TOTAL_CHUNKS: N --> to learn N. The response ends with <!-- __WARMUP_SENTINEL__ --> when N > 1.\n` +
                `   b) Write chunk 0 to [workspace-root]/warmup.html (overwrite — every run is a fresh file).\n` +
                `   c) For i = 1..N-1, sequentially (never parallel): call warmup_get_template({ chunk: i, warmup_data: JSON.stringify(WARMUP_DATA) }), then Edit replace <!-- __WARMUP_SENTINEL__ --> with the chunk content. warmup_data is required on every chunk call — the server re-injects it each time.\n` +
                `   d) Verify before registering — never register an incomplete file:\n` +
                `      - Grep for "<!-- __WARMUP_SENTINEL__ -->" → must return 0 matches. If > 0, resume the loop at the next unfilled chunk until the sentinel is gone.\n` +
                `      - Read the last 3 lines → must contain "</html>". If absent, re-fetch chunk 0 fresh and re-stitch.\n` +
                `   e) Register: artifact_action === "create" → create_artifact; "update" → update_artifact. Pass id: "the-warmup" and html_path: [workspace-root]/warmup.html. No mcp_tools needed — fonts are baked and the brief makes no MCP calls at runtime.\n\n` +
                `8. DONE — one summary line in chat. The brief is complete and self-contained.\n\n` +
                `## Voice\n\n` +
                `The brief is factual and labeled. Every item shows its source and trust tier. No editorializing. No hype. Scannable and honest.\n\n` +
                `## Reference sections (call warmup_get_skill only when needed — round-trips)\n\n` +
                `- Product Leader / Custom mode batch query patterns: warmup_get_skill({ section: "sources" })\n` +
                `- Report section structures for CISO: warmup_get_skill({ section: "sections" })\n` +
                `- Anti-patterns, editorial voice: warmup_get_skill({ section: "rules" })\n` +
                `- Full schema with examples and edge cases: warmup_get_skill({ section: "schema" })\n` +
                `- Full SKILL.md (only if the above are insufficient): warmup_get_skill({ section: "full" })`,
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
      "Returns a named section of The Spotter SKILL.md. This is a HELPER tool — call it only after spotter_run has given you the review workflow and instructed you which section to load. Do NOT call this as the entry point for an epic review; always call spotter_run first. Calling this tool without first calling spotter_run produces a chat-only review with no artifact. Sections: 'areas' (all nine review areas + sub-checks — load for grading), 'review' (review output format), 'iterate' (iterate mode output format), 'build' (build mode output format), 'output' (all three output formats), 'schema' (JSON output schema), 'antipatterns' (what the skill must not do), 'full' (entire document).",
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
      "Return the data-filled Spotter worksheet HTML in paginated 900-line chunks. " +
      "Pass spotter_data on EVERY chunk call — the server re-injects it each time (stateless). " +
      "Fonts are baked in; the worksheet's live refine uses the Cowork askClaude bridge, not an MCP tool. " +
      "Call with chunk:0 first; read <!-- SPOTTER_TOTAL_CHUNKS: N --> from the response to learn the total. " +
      "Write chunk 0 to disk, then for chunks 1..N-1 call with chunk:i and Edit-replace <!-- __SPOTTER_SENTINEL__ --> with each chunk. " +
      "After assembly, call create_artifact (no mcp_tools needed — fonts are baked). " +
      "Do NOT use bash to move files — use the Read/Write file tools.",
      {
        intent: intentField,
        chunk: z.number().int().min(0).default(0).describe(
          "Which 900-line chunk to return (0-indexed). Default: 0. Read <!-- SPOTTER_TOTAL_CHUNKS: N --> from chunk 0 to learn the total."
        ),
        spotter_data: z.string().max(300000).describe(
          "The SPOTTER_DATA JSON string produced by the Spotter review. Required on EVERY chunk call — the server re-injects it each time. Must be valid JSON."
        ),
      },
      async ({ chunk = 0, spotter_data }) => {
        try { JSON.parse(spotter_data); } catch (e) {
          return { content: [{ type: "text" as const, text: `[spotter_get_template] ERROR: spotter_data is not valid JSON — ${String(e)}. Fix the SPOTTER_DATA object and retry.` }] };
        }
        // XSS + $-expansion safety: escape </script>, inject via replacer function.
        const safe = spotter_data.replace(/<\/script>/gi, '<\\/script>');
        const filled = SPOTTER_TEMPLATE_HTML.replace("__SPOTTER_DATA__", () => safe);
        if (filled === SPOTTER_TEMPLATE_HTML) {
          return { content: [{ type: "text" as const, text: "[spotter_get_template] ERROR: placeholder __SPOTTER_DATA__ not found in template. Report this to the developer." }] };
        }
        const CHUNK_LINES = 900;
        const SENTINEL    = '<!-- __SPOTTER_SENTINEL__ -->';
        const lines       = filled.split('\n');
        const totalChunks = Math.ceil(lines.length / CHUNK_LINES);
        if (chunk === 0) {
          const chunkLines = lines.slice(0, CHUNK_LINES);
          chunkLines.unshift(`<!-- SPOTTER_TOTAL_CHUNKS: ${totalChunks} -->`);
          if (totalChunks > 1) chunkLines.push(SENTINEL);
          return { content: [{ type: "text" as const, text: chunkLines.join('\n') }] };
        }
        const startLine = chunk * CHUNK_LINES;
        if (startLine >= lines.length) {
          return { content: [{ type: "text" as const, text: `[spotter_get_template ERROR: chunk:${chunk} is out of range — total chunks is ${totalChunks}. Stop and report this error.]` }] };
        }
        const endLine    = Math.min((chunk + 1) * CHUNK_LINES, lines.length);
        const chunkLines = lines.slice(startLine, endLine);
        if (endLine < lines.length) chunkLines.push(SENTINEL);
        return { content: [{ type: "text" as const, text: chunkLines.join('\n') }] };
      }
    );

    this.server.tool(
      "spotter_run",
      "REQUIRED ENTRY POINT for all Spotter epic reviews. Call this first — before any other spotter tool — when the user says 'spot my epic', 'review my epic', 'run the spotter', 'check my epic', or pastes a product epic for review. Returns the full step-by-step standalone workflow: grade the nine areas silently, build SPOTTER_DATA, render the self-contained worksheet, and register it with create_artifact. Do NOT call spotter_get_skill directly as the entry point — it only returns framework content and has no render pipeline.",
      {
        intent: intentField,
        epic: z.string().min(50).max(20000).describe("The full text of the epic to review."),
      },
      async ({ epic }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter v${SPOTTER_VERSION} — Review Mode (standalone)\n\n` +
              `## The deliverable\n\n` +
              `The output is a self-contained HTML worksheet written to the user's workspace folder and registered in the Cowork artifact panel. That file IS the review. The chat message at the end is a short pointer, not the review.\n\n` +
              `The worksheet is self-contained: fonts are baked in, and the live "Refine with Spotter" pass runs through the Cowork askClaude bridge — not an MCP tool. Nothing in the artifact calls this server at runtime.\n\n` +
              `**Task failure:** If grades, findings, or verdicts appear in chat before the artifact file exists on disk, the task has failed. Build the artifact first. Always.\n\n` +
              `## Sequence\n\n` +
              `Execute steps 1 → 2 → 3 → 4. No grades, findings, or verdicts to chat until Step 4.\n\n` +
              `1. SETUP    — call list_artifacts → find workspace path\n` +
              `2. GRADE    — load framework → grade all 9 areas silently → build SPOTTER_DATA\n` +
              `3. ARTIFACT — render filled HTML → register artifact  ← THIS IS THE DELIVERABLE\n` +
              `4. CONFIRM  — post grade summary to chat (only after the artifact exists)\n\n` +
              `## Permitted tools\n\n` +
              `  MCP:  list_artifacts · create_artifact · update_artifact · request_cowork_directory\n` +
              `        spotter_get_skill · spotter_get_examples · spotter_get_template\n` +
              `  File: Read · Write · Edit · Grep\n\n` +
              `## Step 1 — Setup\n\n` +
              `a. Call list_artifacts.\n` +
              `b. Find workspace root: take the html_path of any artifact and strip the filename; if none exist, use the user's mounted Cowork folder (a short path like /Users/[name]/Projects/[folder]). It is NOT a session/outputs/uploads/tmp path. If unsure, call request_cowork_directory and use the approved path.\n` +
              `c. Target file: [workspace-root]/spotter-[epic-slug]-[YYYY-MM-DD-HH-MM].html (the HH-MM keeps every run on a fresh panel).\n\n` +
              `## Step 2 — Grade (silent — no chat output)\n\n` +
              `a. Call spotter_get_skill({ section: "areas", intent: "Loading Spotter review framework" }).\n` +
              `b. Grade all nine areas silently. ✓ Pass → ["w","w","w"] · ⚠️ Needs work → ["w","w","r"] · ✗ Missing → ["r","r","r"].\n` +
              `c. Area 1 carries disproportionate weight (8 sub-checks). Area 9 is a gate: ✗ Missing on any B2B feature with agent actions or data access caps the verdict at "Not ready."\n` +
              `d. Call spotter_get_examples({ area: N, intent: "..." }) if you need calibration.\n` +
              `e. Build SPOTTER_DATA (the one and only grading pass):\n` +
              `   meta: { epicTitle, epicDeck ("A Spotter review · Nine areas, three judges each."), author (PM name or "PM"), date ("21 May 2026") }\n` +
              `   areas: [ { id ("a01"–"a09"), num ("01"–"09"), cat, title (standard mapping), deck (area question),\n` +
              `              verdict ("good" for Pass, "no-lift" for Needs work/Missing), verdictLabel ("Pass"/"Needs work"/"Missing"),\n` +
              `              pips (["w","w","w"] / ["w","w","r"] / ["r","r","r"]), pipSub ("3 of 3 white" ...),\n` +
              `              excerpt (verbatim epic text, or "" if isEmpty), excerptLabel, excerptMeta, isEmpty,\n` +
              `              notes: [{ type ("missing"|"suggest"|"recommend"|"observation"), body }], chips: ["short label"] } ]\n` +
              `   config: {}   (fonts are baked — no font tool name needed)\n` +
              `   Voice: every note body is "you could strengthen this by…" — never "you missed" or "this is wrong."\n\n` +
              `## Step 3 — Artifact  ← Render the file. This is the output.\n\n` +
              `B-1. Call spotter_get_template({ intent: "…", chunk: 0, spotter_data: JSON.stringify(SPOTTER_DATA) }).\n` +
              `     The server injects SPOTTER_DATA into the worksheet and returns it data-filled. Read <!-- SPOTTER_TOTAL_CHUNKS: N --> to learn N. Call each chunk exactly once.\n` +
              `B-2. Write chunk 0 to [workspace-root]/spotter-[epic-slug]-[YYYY-MM-DD-HH-MM].html, exactly as returned.\n` +
              `B-3. For i = 1..N-1 (sequential, never parallel): call spotter_get_template({ chunk: i, spotter_data: JSON.stringify(SPOTTER_DATA) }), then Edit the file replacing <!-- __SPOTTER_SENTINEL__ --> with the chunk. When done, Grep for the sentinel — it must not appear.\n` +
              `B-4. Call create_artifact — always create, never update.\n` +
              `     id: "spotter-[epic-slug]-[YYYY-MM-DD-HH-MM]"   html_path: the file from B-2\n` +
              `     No mcp_tools are needed — fonts are baked and the worksheet uses askClaude, not an MCP tool.\n\n` +
              `Step 3 is complete when the file is on disk and registered. The data is already injected — there is no separate SPOTTER_DATA edit step.\n\n` +
              `## Step 4 — Confirm (artifact must already exist)\n\n` +
              `Read grades from SPOTTER_DATA — do not re-evaluate. Write this and nothing else:\n\n` +
              `  Review complete — open the artifact panel to see the full worksheet.\n\n` +
              `  **[Overall verdict]** · [N] of 9 areas passed\n\n` +
              `  | # | Area | Grade |\n` +
              `  |---|------|-------|\n` +
              `  | 1 | [name] | ✓ Pass / ⚠️ Needs work / ✗ Missing |\n` +
              `  | … |\n\n` +
              `  [1–2 sentences: biggest strength and the single most important thing to address.]\n\n` +
              `  *Full worksheet → artifact panel. Questions? Reply here.*\n\n` +
              `## Epic\n\n\`\`\`\n${epic}\n\`\`\`\n\n` +
              `Read all instructions above before starting. Then execute steps 1 → 2 → 3 → 4.`,
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
      "Return the data-filled Approach HTML in paginated 900-line chunks. " +
      "Pass approach_data on EVERY chunk call — the server re-injects it each time (stateless). " +
      "Call with chunk:0 first; read <!-- APPROACH_TOTAL_CHUNKS: N --> from the response " +
      "to learn the total. Write chunk 0 to disk, then for chunks 1..N-1 call with chunk:i " +
      "and Edit-replace <!-- __APPROACH_SENTINEL__ --> with each chunk. " +
      "After assembly, call create_artifact. " +
      "Do NOT use bash to move files — use the Read/Write file tools.",
      {
        intent: intentField,
        chunk: z
          .number()
          .int()
          .min(0)
          .default(0)
          .describe(
            "Which 900-line chunk to return (0-indexed). Default: 0. " +
            "Read <!-- APPROACH_TOTAL_CHUNKS: N --> from chunk 0 to learn the total number of chunks."
          ),
        approach_data: z.string().max(300000).describe(
          "The APPROACH_DATA JSON string produced by The Approach workflow. " +
          "Required on EVERY chunk call — the server re-injects it each time. " +
          "Must be valid JSON matching the APPROACH_DATA schema."
        ),
      },
      async ({ chunk = 0, approach_data }) => {
        // Validate JSON before injection — malformed data produces a near-blank silent brief otherwise.
        try { JSON.parse(approach_data); } catch (e) {
          return {
            content: [{
              type: "text" as const,
              text: `[approach_get_template] ERROR: approach_data is not valid JSON — ${String(e)}. Fix the APPROACH_DATA object and retry.`,
            }],
          };
        }

        // XSS safety: article/intel text can contain </script> — escape before injection.
        // Replacer-function safety: content can contain $', $&, $` — replacer bypasses expansion.
        const safe = approach_data.replace(/<\/script>/gi, '<\\/script>');
        const PLACEHOLDER = "__APPROACH_DATA__";
        const filled = APPROACH_TEMPLATE_HTML.replace(PLACEHOLDER, () => safe);
        if (filled === APPROACH_TEMPLATE_HTML) {
          return {
            content: [{
              type: "text" as const,
              text: "[approach_get_template] ERROR: placeholder __APPROACH_DATA__ not found in template. Report this to the developer.",
            }],
          };
        }

        // Paginated delivery — same pattern as warmup_get_template.
        // The filled HTML is ~1100-1200 lines. Cowork auto-persists MCP responses over ~67KB
        // to disk as a file path, which agents then try to move with bash (which fails because
        // bash runs in a sandbox). Chunking at 900 lines keeps each response well under the
        // threshold. approach_data is re-injected on every call so no server-side caching needed.
        const CHUNK_LINES = 900;
        const SENTINEL    = '<!-- __APPROACH_SENTINEL__ -->';
        const lines       = filled.split('\n');
        const totalChunks = Math.ceil(lines.length / CHUNK_LINES);

        if (chunk === 0) {
          const chunkLines = lines.slice(0, CHUNK_LINES);
          // Prepend total-chunks header so the agent knows how many calls to make.
          chunkLines.unshift(`<!-- APPROACH_TOTAL_CHUNKS: ${totalChunks} -->`);
          if (totalChunks > 1) chunkLines.push(SENTINEL);
          return { content: [{ type: "text" as const, text: chunkLines.join('\n') }] };
        }

        // Chunks 1+: serve the appropriate slice of filled lines.
        const startLine = chunk * CHUNK_LINES;
        if (startLine >= lines.length) {
          return {
            content: [{
              type: "text" as const,
              text: `[approach_get_template ERROR: chunk:${chunk} is out of range — total chunks is ${totalChunks}. Stop and report this error.]`,
            }],
          };
        }
        const endLine   = Math.min((chunk + 1) * CHUNK_LINES, lines.length);
        const chunkLines = lines.slice(startLine, endLine);
        const isLast    = endLine >= lines.length;
        if (!isLast) chunkLines.push(SENTINEL);
        return { content: [{ type: "text" as const, text: chunkLines.join('\n') }] };
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
              "",
              "## Render — chunked template (matches Warmup pattern)",
              "",
              "Every Approach brief is built from scratch using approach_get_template. No Path A/B.",
              "approach_data is required on EVERY chunk call — the server re-injects it each time.",
              "",
              "  1. Assemble the complete APPROACH_DATA object (see approach_get_skill section:'schema').",
              "  2. Call approach_get_template({ chunk: 0, approach_data: JSON.stringify(APPROACH_DATA) }).",
              "     Read <!-- APPROACH_TOTAL_CHUNKS: N --> from the response to learn N.",
              "     The response ends with <!-- __APPROACH_SENTINEL__ --> when N > 1.",
              "  3. Write chunk 0 to [workspace-root]/approach-brief.html using the Write file tool.",
              "  4. For chunks 1..N-1 (sequentially, NEVER parallel):",
              "       Call approach_get_template({ chunk: i, approach_data: JSON.stringify(APPROACH_DATA) }).",
              "       Edit approach-brief.html: old_string='<!-- __APPROACH_SENTINEL__ -->' → new_string=[chunk text].",
              "       Wait for Edit to succeed before starting i+1.",
              "  5. Verify: Grep approach-brief.html for <!-- __APPROACH_SENTINEL__ -->. Must be 0 matches.",
              "  6. Call create_artifact({ html_path: '...approach-brief.html' }).",
              "  Do NOT use bash to move or copy files — use Read/Write file tools with real macOS paths.",
              "",
              "## Fonts",
              "",
              "Fonts load from the Google Fonts CDN with a system-font fallback — nothing to configure, and no font tool is needed.",
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
