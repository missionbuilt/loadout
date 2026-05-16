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
 *   /mcp           - MCP over Streamable HTTP
 *
 * Source: https://github.com/missionbuilt/loadout
 * License: MIT
 */

import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

// Skill content bundled at build time via Wrangler text imports.
import WARMUP_SKILL_MD from "./skill-content/warmup/SKILL.md";
import WARMUP_TEMPLATE_HTML from "./skill-content/warmup/warmup-template.html";
import SPOTTER_SKILL_MD from "./skill-content/spotter/SKILL.md";
import SPOTTER_LENS_EXAMPLES_MD from "./skill-content/spotter/lens-examples.md";
import SPOTTER_SYNTHETIC_EPIC_MD from "./skill-content/spotter/synthetic-epic.md";
import SPOTTER_SYNTHETIC_EPIC_2_MD from "./skill-content/spotter/synthetic-epic-2.md";
import SPOTTER_SYNTHETIC_EPIC_3_MD from "./skill-content/spotter/synthetic-epic-3.md";

import { brandCss } from "./design";
import { authHandler, type UserProps } from "./auth";

const SERVER_VERSION = "1.0.0";

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

// ── Shared param schemas ──────────────────────────────────────────────────────

/** Re-used across every tool that shows a Cowork permission dialog. */
const intentField = z.string().describe(
  "Permission dialog text — one sentence, ≤100 chars. E.g. 'Loading Warmup skill framework'."
);

// ── Warmup constants ──────────────────────────────────────────────────────────

const WARMUP_VERSION = "0.3.11";
const WARMUP_ENGINE_VERSION = "v0.3.10";

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

const SPOTTER_VERSION = "0.3.0";

const SPOTTER_LENSES = [
  { id: 1, name: "The user and the problem", weight: "foundation — heaviest lens, 8 sub-checks" },
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
  OAUTH_PROVIDER: any;
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
        const PLACEHOLDER = `window.WARMUP_DATA = null; // ← AGENT: Edit-replace this line with your WARMUP_DATA JSON object (see SKILL.md Path B)`;
        const filled = WARMUP_TEMPLATE_HTML.replace(PLACEHOLDER, `window.WARMUP_DATA = ${warmup_data};`);
        const injected = filled !== WARMUP_TEMPLATE_HTML;
        return {
          content: [
            {
              type: "text" as const,
              text: injected
                ? filled
                : `[warmup_get_template ERROR: WARMUP_DATA placeholder not found — injection failed. Raw template returned.]

${WARMUP_TEMPLATE_HTML}`,
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
        const configNote = config_summary
          ? `The user's WARMUP.md has been provided:\n\n${config_summary}\n\nProceed directly to source fetching.`
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
                `3. TEMPLATE RULE — NON-NEGOTIABLE: The artifact HTML comes only from warmup_get_template. NEVER write HTML from scratch. NEVER reconstruct the template from training memory. NEVER simplify or abbreviate the template. The template is 128KB by design. Your only job is supply WARMUP_DATA; the template renders itself.\n` +
                `4. For each active source, call the WebSearch tool to fetch recent content using the adaptive lookback window. Reject any item where item.date < lookback_start before routing to sections.\n` +
                `5. Run the link safety verification protocol on all URLs before including them.\n` +
                `6. Synthesize content into sections. Build WARMUP_DATA with all required fields:\n` +
                `   - config.showQuote: true (JSON boolean — required, not optional)\n` +
                `   - config.scanTime: current generation time as "HH:MM TZ" (use WARMUP.md timezone; default UTC if not set)\n` +
                `   - config.vendors: copy verbatim from WARMUP.md vendors field; write "" if blank, never omit\n` +
                `   - safety.domains: one entry per active source — required; empty array means safety panel does not render\n` +
                `   - safety.totalUrls: count of verified-safe clickable URLs in the brief (must equal config.totalLinks)\n` +
                `   - sources[].status: "active" | "quiet" | "excluded" — exact strings only\n` +
                `   - sources[].ct: "N items" for active sources, "—" for quiet sources\n` +
                `7. Render the artifact:\n` +
                `   PATH A (version match — no template reload): edit the existing html_path file — use the Read file tool to read it, then the Edit tool to find and replace the old window.WARMUP_DATA = {...}; line with the new WARMUP_DATA. Call update_artifact. Done.\n` +
                `   PATH B / FIRST RUN (engine update or new artifact): Call warmup_get_template({ intent: "...", warmup_data: JSON.stringify(WARMUP_DATA) }). The server injects the data and returns filled, artifact-ready HTML. Write the returned HTML to disk with the Write tool. Call create_artifact (new) or update_artifact (replacing stale). Done.\n` +
                `   NEVER write your own HTML. NEVER generate a shorter version of the template. The warmup_get_template response IS the complete artifact — write it as-is.\n` +
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
        const actionInstructions: Record<string, string> = {
          show: "Use the Read file tool to read WARMUP.md from the user's project root. If you do not know the project root path, call list_artifacts — the html_path from 'the-warmup' reveals the workspace folder, and WARMUP.md lives there. Display current active, quiet, and excluded sources in a clean summary.",
          add: `Use the Read file tool to read WARMUP.md first. Then add "${source ?? "[source]"}" to the user's active sources. Ask for the URL and tier (Authoritative / Research / News / Vendor) if not provided. Format: "- Name | URL | active". Show the proposed addition for confirmation before writing.`,
          remove: `Use the Read file tool to read WARMUP.md first. Then remove "${source ?? "[source]"}" from WARMUP.md entirely. Show the current entry and confirm with the user before writing.`,
          exclude: `Use the Read file tool to read WARMUP.md first. Then mark "${source ?? "[source]"}" as excluded by moving it to the ## Excluded Sources section with format: "- Name | URL | excluded". Confirm before writing.`,
        };

        return {
          content: [
            {
              type: "text" as const,
              text:
                `# The Warmup — Config\n\n` +
                `${actionInstructions[action]}\n\n` +
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
      "Returns the full SKILL.md for The Spotter — the framework, modes (build/iterate/review), nine lenses with sub-checks, output formats, anti-patterns, and the structured output schema. Call this first when running a review, building an epic, or iterating on a draft.",
      { intent: intentField },
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_SKILL_MD }],
      })
    );

    this.server.tool(
      "spotter_get_examples",
      "Returns the full lens-examples.md content with 64 worked examples across the nine lenses — strong (✓), needs-work (⚠️), and missing (✗) variants with teaching notes. Use when calibrating grading or teaching by contrast.",
      { intent: intentField },
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_LENS_EXAMPLES_MD }],
      })
    );

    this.server.tool(
      "spotter_get_calibration_epic",
      "Returns synthetic calibration epic #1 — a B2B security epic with deliberate gaps. Running a review against it should produce verdict 'Needs polish' with specific gaps on Lenses 1, 4, 5, 6, 8, and 9. Use to verify a fresh install is producing expected output. For all three calibration epics, call spotter_get_calibration_epics instead.",
      { intent: intentField },
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_SYNTHETIC_EPIC_MD }],
      })
    );

    this.server.tool(
      "spotter_get_calibration_epics",
      "Returns all three synthetic calibration epics concatenated. Use to run a batch calibration pass or to compare how The Spotter grades epics at different quality levels. Epic 1 targets 'Needs polish' (gaps on L1, L4, L5, L6, L8, L9). Epics 2 and 3 are well-formed security platform epics for grading range calibration.",
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
      "spotter_list_lenses",
      "Returns the nine lenses with names and weight notes. Useful for clients that want to render lens cards or for an agent that needs a quick overview before loading the full SKILL.md.",
      { intent: intentField },
      async () => ({
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ version: SPOTTER_VERSION, lenses: SPOTTER_LENSES }, null, 2),
          },
        ],
      })
    );

    this.server.tool(
      "spotter_review",
      "Primes the agent to review a B2B product epic using The Spotter's nine-lens framework. Returns the framework and an instruction block telling the agent to apply review mode to the provided epic.",
      {
        intent: intentField,
        epic: z.string().min(50).describe("The full text of the epic to review."),
      },
      async ({ epic }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter — Review Mode\n\n` +
              `You have been asked to review the following B2B product epic using The Spotter v${SPOTTER_VERSION}.\n\n` +
              `## How to run this review\n\n` +
              `1. Read the SKILL.md framework below in full before grading.\n` +
              `2. Walk all nine lenses in order. Grade each lens ✓ Pass / ⚠️ Needs work / ✗ Missing.\n` +
              `3. Lens 1 carries disproportionate weight (foundation). Lens 9 is a gate (✗ Missing on a B2B feature with agent action, data access, or new permission surfaces caps the verdict at Not ready).\n` +
              `4. Use the critique-not-criticism voice throughout: every flag is "you could strengthen this by..." — never "you missed..."\n` +
              `5. End with a Questions to ask the PM section and, if verdict is Needs polish or Not ready, an offer to work through specific gaps.\n\n` +
              `## SKILL.md\n\n${SPOTTER_SKILL_MD}\n\n` +
              `## Epic to review\n\n${epic}\n\n` +
              `Now produce the review. Open with the verdict. Walk all nine lenses. Close with Questions to ask the PM and the push-forward offer.`,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_build",
      "Primes the agent to help a PM build a new epic from scratch using The Spotter's framework. The agent walks the PM through the nine lenses with guiding questions, lingering on Lens 1 before moving on. Output is a polished draft epic.",
      {
        intent: intentField,
        feature: z.string().describe("Brief description of the feature or capability the PM wants to build an epic for."),
      },
      async ({ feature }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter — Build Mode\n\n` +
              `A PM is building an epic for: **${feature}**.\n\n` +
              `Walk them through the nine lenses with guiding questions. Linger on Lens 1 (especially empathy, current state, why-not-solved, scope/value, assumptions, alternatives, openness) before moving on. The output at the end is a polished draft epic structured by lens.\n\n` +
              `Use the critique-not-criticism voice. Ask questions; don't lecture. If the PM rushes past the user, gently slow them down.\n\n` +
              `## SKILL.md\n\n${SPOTTER_SKILL_MD}\n\n` +
              `Begin with Lens 1. Ask about the user first.`,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_iterate",
      "Primes the agent to push a partial draft epic forward. The agent engages only the lenses that have content, asks targeted questions for each gap, and offers structure where the PM is stuck.",
      {
        intent: intentField,
        draft: z.string().min(50).describe("The current partial draft of the epic. Can be incomplete or rough."),
      },
      async ({ draft }) => ({
        content: [
          {
            type: "text" as const,
            text:
              `# The Spotter — Iterate Mode\n\n` +
              `A PM has a partial draft they want to push forward. Engage only the lenses that have content; ask targeted questions for each gap. Offer structure where the PM is stuck.\n\n` +
              `Use the critique-not-criticism voice. Each suggestion uses "you could strengthen this by..." framing.\n\n` +
              `## SKILL.md\n\n${SPOTTER_SKILL_MD}\n\n` +
              `## Draft to iterate on\n\n${draft}\n\n` +
              `Walk the lenses present in the draft. Push each one forward.`,
          },
        ],
      })
    );

    // ══════════════════════════════════════════════════════════════════════════
    // RESOURCES
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
        description: "Full framework: philosophy, modes, nine lenses, sub-checks, output formats, anti-patterns, structured output schema.",
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
        name: "The Spotter — Lens Examples",
        description: "64 worked examples across nine lenses with teaching notes.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "loadout://spotter/examples", mimeType: "text/markdown", text: SPOTTER_LENS_EXAMPLES_MD }],
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
