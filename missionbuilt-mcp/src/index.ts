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

import { brandCss } from "./design";
import { authHandler, type UserProps } from "./auth";

const SERVER_VERSION = "1.0.0";

// ── Warmup constants ──────────────────────────────────────────────────────────

const WARMUP_VERSION = "0.3.1";
const WARMUP_ENGINE_VERSION = "v0.3.1";

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

const SPOTTER_VERSION = "0.2.0";

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
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Example: 'Checking authenticated identity'. Keep it under 100 characters."
        ),
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
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Example: 'Loading Mission Built design CSS'. Keep it under 100 characters."
        ),
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
      "Returns the full SKILL.md for The Warmup — the framework, three modes (CISO / Product Leader / Custom), setup flow, source tiers, section structure, output format, and safety verification protocol. Call this first when setting up The Warmup or generating a brief.",
      {
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Examples: 'Loading Warmup skill framework to begin setup', 'Reading Warmup framework before generating brief'. Keep it under 100 characters."
        ),
      },
      async () => ({
        content: [{ type: "text" as const, text: WARMUP_SKILL_MD }],
      })
    );

    this.server.tool(
      "warmup_list_modes",
      "Returns the three Warmup modes with names, descriptions, and the five brief sections each produces. Useful for clients that want to render a mode-picker or for an agent that needs a quick overview before loading the full SKILL.md.",
      {
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Example: 'Loading available Warmup modes'. Keep it under 100 characters."
        ),
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
      "Returns the canonical warmup-template.html engine — the full Iron Log-branded HTML artifact with all CSS, JS, PDF builder, deep dive modal, section collapse, and accessibility code. Call on every first run (no existing artifact) or after any engine update. Replace only the <script id=\"warmup-data\"> block with fresh WARMUP_DATA. Never build the artifact from scratch.",
      {
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Examples: 'Loading HTML template — first run, no existing artifact', 'Loading updated engine to replace stale artifact'. Keep it under 100 characters."
        ),
      },
      async () => ({
        content: [{ type: "text" as const, text: WARMUP_TEMPLATE_HTML }],
      })
    );

    this.server.tool(
      "warmup_setup",
      "Primes the agent to run The Warmup's setup flow for a new user. Walks the user through mode selection, sector/product area, company, and region, builds and reviews their source suite, saves config to WARMUP.md, and runs a test brief.",
      {
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Examples: 'Setting up Warmup — first time, mode not yet chosen', 'Configuring CISO mode for Healthcare sector'. Keep it under 100 characters."
        ),
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
                `2. Collect the required config fields for that mode (see SKILL.md Setup section).\n` +
                `3. Build the source suite based on their answers. Show it to the user for review.\n` +
                `4. Save config to WARMUP.md at their project root using the schema in WARMUP.example.md.\n` +
                `5. Run a test brief using the saved config. Deliver it as a Cowork artifact or a markdown summary.\n\n` +
                `## Voice\n\n` +
                `Ask one question at a time. Plain language — never internal-framework prompts. ` +
                `The user is setting up their morning routine, not configuring a system. Keep it fast.\n\n` +
                `## SKILL.md\n\n${WARMUP_SKILL_MD}\n\n` +
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
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Examples: 'Generating CISO brief for Elastic · 7-day lookback', 'Running first Warmup brief (30-day bootstrap)'. Keep it under 100 characters."
        ),
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
                `1. Read WARMUP.md from the project root (or use the provided config_summary).\n` +
                `2. For each active source, fetch recent content using the adaptive lookback window.\n` +
                `3. Run the link safety verification protocol on all URLs before including them.\n` +
                `4. Synthesize content into the five sections for the user's mode.\n` +
                `5. Deliver as a live Cowork artifact (Iron Log HTML design). One summary line in chat.\n\n` +
                `## Voice\n\n` +
                `The brief is factual and labeled. Every item shows its source and trust tier. ` +
                `No editorializing. No hype. Keep it scannable and honest.\n\n` +
                `## SKILL.md\n\n${WARMUP_SKILL_MD}`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "warmup_config",
      "Primes the agent to manage the user's Warmup source configuration. Handles add, remove, and exclude operations on active sources in WARMUP.md. Always reads current config before making changes, shows the proposed change for confirmation, then writes.",
      {
        intent: z.string().describe(
          "One sentence shown in the permission dialog. Examples: 'Adding BleepingComputer to active sources', 'Showing current source configuration'. Keep it under 100 characters."
        ),
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
          show: "Read WARMUP.md and display the current active sources, quiet sources, and excluded sources in a clean summary.",
          add: `Add "${source ?? "[source]"}" to the user's active sources in WARMUP.md. Ask for the URL and tier (Authoritative / Research / News / Vendor) if not provided. Show the proposed addition for confirmation before writing.`,
          remove: `Remove "${source ?? "[source]"}" from WARMUP.md entirely. Show the current entry and confirm with the user before writing.`,
          exclude: `Mark "${source ?? "[source]"}" as excluded in WARMUP.md (move to the Excluded Sources section). It will remain listed but be skipped in future briefs. Confirm before writing.`,
        };

        return {
          content: [
            {
              type: "text" as const,
              text:
                `# The Warmup — Config\n\n` +
                `${actionInstructions[action]}\n\n` +
                `## Rules\n\n` +
                `- Always read the current WARMUP.md before making any changes.\n` +
                `- Show the proposed change clearly before writing.\n` +
                `- Preserve all other config fields — only touch the section being modified.\n` +
                `- Update the \`updated\` field to today's date after any write.\n\n` +
                `## SKILL.md\n\n${WARMUP_SKILL_MD}`,
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
      {},
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_SKILL_MD }],
      })
    );

    this.server.tool(
      "spotter_get_examples",
      "Returns the full lens-examples.md content with 64 worked examples across the nine lenses — strong (✓), needs-work (⚠️), and missing (✗) variants with teaching notes. Use when calibrating grading or teaching by contrast.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_LENS_EXAMPLES_MD }],
      })
    );

    this.server.tool(
      "spotter_get_calibration_epic",
      "Returns a synthetic B2B security epic used to calibrate The Spotter. Running a review against it should produce verdict 'Needs polish' with specific gaps on Lenses 1, 4, 5, 6, 8, and 9. Use to verify a fresh install is producing expected output.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: SPOTTER_SYNTHETIC_EPIC_MD }],
      })
    );

    this.server.tool(
      "spotter_list_lenses",
      "Returns the nine lenses with names and weight notes. Useful for clients that want to render lens cards or for an agent that needs a quick overview before loading the full SKILL.md.",
      {},
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
