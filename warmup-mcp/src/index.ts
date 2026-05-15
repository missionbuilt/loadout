/**
 * The Warmup — MCP Server (OAuth-protected)
 *
 * Hosted MCP server that exposes The Warmup's framework and mode primers
 * to MCP-compatible agents. Endpoints protected by OAuth 2.1 with Google
 * as the identity provider.
 *
 * Public routes (no auth):
 *   /              - branded landing page
 *   /preview       - sample Warmup brief walkthrough
 *   /health        - JSON health check
 *   /brand.css     - Mission Built design CSS
 *
 * OAuth flow routes (handled by the workers-oauth-provider library):
 *   /.well-known/oauth-authorization-server  - discovery metadata
 *   /authorize     - authorization endpoint (Google sign-in)
 *   /token         - token exchange
 *   /register      - dynamic client registration
 *
 * Protected MCP routes (require Bearer token):
 *   /sse           - MCP over Server-Sent Events
 *   /mcp           - MCP over Streamable HTTP
 *
 * Source: https://github.com/missionbuilt/loadout/tree/main/warmup
 * License: MIT
 */

import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

// Skill content bundled at build time via Wrangler's text imports
// (configured in wrangler.toml [[rules]] section).
import SKILL_MD from "./skill-content/SKILL.md";
import TEMPLATE_HTML from "./skill-content/warmup-template.html";

import { brandCss } from "./design";
import { authHandler, type UserProps } from "./auth";

const WARMUP_VERSION = "0.2.0";
const SERVER_VERSION = "0.2.0";
const ENGINE_VERSION = "v0.2.0"; // Bump this whenever warmup-template.html changes

const MODES = [
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

interface Env {
  MCP_OBJECT: DurableObjectNamespace;
  OAUTH_KV: KVNamespace;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  COOKIE_ENCRYPTION_KEY: string;
  OAUTH_PROVIDER: any; // OAuthHelpers, injected by workers-oauth-provider
}

/**
 * The Warmup's MCP agent. Inherits user identity from the OAuth flow
 * via the third type parameter (Props).
 */
export class WarmupMCP extends McpAgent<Env, UserProps> {
  server = new McpServer({
    name: "the-warmup",
    version: SERVER_VERSION,
  });

  async init() {
    // ---- TOOLS ----

    this.server.tool(
      "warmup_get_skill",
      "Returns the full SKILL.md content for The Warmup — the framework, three modes (CISO / Product Leader / Custom), setup flow, source tiers, section structure, output format, and safety verification protocol. Call this first when setting up The Warmup or when generating a brief.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: SKILL_MD }],
      })
    );

    this.server.tool(
      "warmup_list_modes",
      "Returns the three Warmup modes with names, descriptions, and the five brief sections each produces. Useful for clients that want to render a mode-picker or for an agent that needs a quick overview before loading the full SKILL.md.",
      {},
      async () => ({
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ version: WARMUP_VERSION, modes: MODES }, null, 2),
          },
        ],
      })
    );

    this.server.tool(
      "warmup_get_brand_css",
      "Returns the Mission Built design system as a CSS string. Useful for clients that want to render Warmup brief output as branded HTML instead of plain markdown. The CSS uses --mb-* custom properties and provides utility classes for the Iron Log aesthetic.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: brandCss() }],
      })
    );

    this.server.tool(
      "warmup_get_template",
      "Returns the canonical warmup-template.html engine — the full Iron Log-branded HTML artifact with all CSS, JS, PDF builder, deep dive modal, section collapse, and accessibility code. Call this on every first run (no existing artifact) or after any engine fix. Replace only the <script id=\"warmup-data\"> block with fresh WARMUP_DATA. Never build the artifact from scratch.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: TEMPLATE_HTML }],
      })
    );

    this.server.tool(
      "warmup_whoami",
      "Returns the authenticated user's identity (name and email) for the current MCP session. Useful for personalizing the brief greeting or confirming the OAuth connection is active.",
      {},
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
      "warmup_setup",
      "Primes the agent to run The Warmup's setup flow for a new user. Returns the SKILL.md framework plus setup instructions. The agent walks the user through 4 questions (mode selection, sector or product area, company, region/vendors), builds their source suite, shows it for review, saves config to WARMUP.md, and runs a test brief.",
      {
        intent: z
          .string()
          .describe(
            "One sentence shown in the permission dialog describing this setup. Always fill this in. Examples: 'Setting up Warmup — first time, mode not yet chosen', 'Setting up Warmup in CISO mode for Healthcare sector', 'Configuring Product Leader mode for Acme Corp'. Keep it under 100 characters."
          ),
        mode: z
          .enum(["ciso", "product_leader", "custom"])
          .optional()
          .describe(
            "The mode to set up. If omitted, the agent asks the user to choose."
          ),
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
                `## SKILL.md\n\n${SKILL_MD}\n\n` +
                `Begin with mode selection if not yet known, or with the first config question for the given mode.`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "warmup_run",
      "Primes the agent to generate a Warmup intelligence brief. Reads the user's WARMUP.md config (which the agent should locate at the project root), fetches live intelligence from each active source, synthesizes it into the five sections, runs the link safety verification protocol, and renders the output as a live HTML artifact. One summary line in chat — the brief is the artifact.",
      {
        intent: z
          .string()
          .describe(
            "One sentence shown in the permission dialog describing this run. Always fill this in. Examples: 'Generating CISO brief for Elastic · 7-day lookback', 'Running first Warmup brief (30-day bootstrap)', 'Product Leader brief for Acme Corp · catch-up run'. Keep it under 100 characters."
          ),
        config_summary: z
          .string()
          .optional()
          .describe(
            "Optional: the contents of the user's WARMUP.md, if already read. If omitted, the agent reads it from the project root first."
          ),
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
                `**Engine version: ${ENGINE_VERSION}**\n\n` +
                `${configNote}\n\n` +
                `## How to generate the brief\n\n` +
                `1. Read WARMUP.md from the project root (or use the provided config_summary).\n` +
                `2. For each active source, fetch recent content from the last window_override days (or adaptive window if blank).\n` +
                `3. Run the link safety verification protocol on all URLs before including them in the brief.\n` +
                `4. Synthesize content into the five sections appropriate for the user's mode.\n` +
                `5. Deliver as a live Cowork artifact (Iron Log HTML design). One summary line in chat.\n\n` +
                `## Voice\n\n` +
                `The brief body is factual and labeled. Every item shows its source and trust tier. ` +
                `No editorializing. No hype. The user reads this before their first meeting — ` +
                `keep it scannable and honest.\n\n` +
                `## SKILL.md\n\n${SKILL_MD}`,
            },
          ],
        };
      }
    );

    this.server.tool(
      "warmup_config",
      "Primes the agent to manage the user's Warmup source configuration. Handles add, remove, and exclude operations on active sources in WARMUP.md. Always reads the current config before making changes, shows the proposed change for confirmation, then writes the updated file.",
      {
        intent: z
          .string()
          .describe(
            "One sentence shown in the permission dialog describing this config change. Always fill this in. Examples: 'Adding BleepingComputer to active sources', 'Excluding Dark Reading from brief', 'Showing current source configuration'. Keep it under 100 characters."
          ),
        action: z
          .enum(["add", "remove", "exclude", "show"])
          .describe(
            "What to do: add a new source, remove one, exclude one (keeps it listed but skips it in the brief), or show the current config."
          ),
        source: z
          .string()
          .optional()
          .describe(
            "The source name or URL to add, remove, or exclude. Not required for show."
          ),
      },
      async ({ action, source }) => {
        const actionInstructions: Record<string, string> = {
          show: "Read WARMUP.md and display the current active sources, quiet sources, and excluded sources in a clean summary.",
          add: `Add "${source ?? "[source]"}" to the user's active sources in WARMUP.md. Ask for the URL and tier (Authoritative / Research / News / Vendor) if not provided. Show the proposed addition for confirmation before writing.`,
          remove: `Remove "${source ?? "[source]"}" from WARMUP.md entirely. Show the current entry and confirm with the user before writing.`,
          exclude: `Mark "${source ?? "[source]"}" as excluded in WARMUP.md (move to the Excluded Sources section). It will remain listed but be skipped in future briefs. Confirm with the user before writing.`,
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
                `## SKILL.md\n\n${SKILL_MD}`,
            },
          ],
        };
      }
    );

    // ---- RESOURCES ----

    this.server.resource(
      "skill",
      "warmup://skill",
      {
        name: "The Warmup — SKILL.md",
        description:
          "The full framework: philosophy, three modes, setup flow, source tiers, section structure, output format, safety verification protocol.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "warmup://skill", mimeType: "text/markdown", text: SKILL_MD }],
      })
    );

    this.server.resource(
      "brand-css",
      "warmup://brand-css",
      {
        name: "The Warmup — Mission Built Brand CSS",
        description:
          "The Mission Built design system as a CSS stylesheet. Use to render Warmup brief output as branded HTML in compatible clients.",
        mimeType: "text/css",
      },
      async () => ({
        contents: [{ uri: "warmup://brand-css", mimeType: "text/css", text: brandCss() }],
      })
    );
  }
}

/**
 * The Worker entry point. Wraps the MCP agent with OAuthProvider so that
 * /sse requires a valid Bearer token, while public routes (landing, preview,
 * health, brand.css) and OAuth flow routes are handled by authHandler.
 */
export default new OAuthProvider({
  apiRoute: "/sse",
  apiHandler: WarmupMCP.mount("/sse") as any,
  defaultHandler: authHandler as any,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register",
});
