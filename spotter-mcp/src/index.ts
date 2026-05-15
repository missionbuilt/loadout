/**
 * The Spotter — MCP Server (OAuth-protected)
 *
 * Hosted MCP server that exposes The Spotter's framework, examples, and
 * calibration content to MCP-compatible agents. As of v0.2, MCP endpoints
 * are protected by OAuth 2.1 with Google as the identity provider, making
 * the server usable from Claude Desktop's UI-based MCP connector flow.
 *
 * Public routes (no auth):
 *   /              - branded landing page
 *   /preview       - sample Spotter review
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
 * Source: https://github.com/missionbuilt/loadout/tree/main/spotter
 * License: MIT
 */

import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

// Skill content bundled at build time via Wrangler's text imports
// (configured in wrangler.toml [[rules]] section).
import SKILL_MD from "./skill-content/SKILL.md";
import LENS_EXAMPLES_MD from "./skill-content/lens-examples.md";
import SYNTHETIC_EPIC_MD from "./skill-content/synthetic-epic.md";

import { brandCss } from "./design";
import { authHandler, type UserProps } from "./auth";

const SPOTTER_VERSION = "0.2.0";
const SERVER_VERSION = "0.3.0";

const LENSES = [
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

interface Env {
  MCP_OBJECT: DurableObjectNamespace;
  OAUTH_KV: KVNamespace;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  COOKIE_ENCRYPTION_KEY: string;
  OAUTH_PROVIDER: any; // OAuthHelpers, injected by workers-oauth-provider
}

/**
 * The Spotter's MCP agent. Inherits user identity from the OAuth flow
 * via the third type parameter (Props).
 */
export class SpotterMCP extends McpAgent<Env, UserProps> {
  server = new McpServer({
    name: "the-spotter",
    version: SERVER_VERSION,
  });

  async init() {
    // ---- TOOLS ----

    this.server.tool(
      "spotter_get_skill",
      "Returns the full SKILL.md content for The Spotter — the framework, modes (build/iterate/review), nine lenses with sub-checks, output formats, anti-patterns, and the structured output schema. Call this first when running a review on an epic, building a new epic, or iterating on a draft.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: SKILL_MD }],
      })
    );

    this.server.tool(
      "spotter_get_examples",
      "Returns the full lens-examples.md content with 64 worked examples across the nine lenses — strong (✓), needs-work (⚠️), and missing (✗) variants with teaching notes. Use this when teaching by contrast or when grading needs calibration against the canonical patterns.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: LENS_EXAMPLES_MD }],
      })
    );

    this.server.tool(
      "spotter_get_calibration_epic",
      "Returns a synthetic B2B security epic (agentic incident response) used to calibrate The Spotter. Running The Spotter against this epic should produce verdict 'Needs polish' with specific gaps flagged on Lenses 1, 4, 5, 6, 8, and 9. Use to verify your install or render of The Spotter is producing expected output.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: SYNTHETIC_EPIC_MD }],
      })
    );

    this.server.tool(
      "spotter_list_lenses",
      "Returns the nine lenses with their names and weight notes. Useful when an agent needs an overview before fetching the full SKILL.md, or for clients that want to render lens cards.",
      {},
      async () => ({
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ version: SPOTTER_VERSION, lenses: LENSES }, null, 2),
          },
        ],
      })
    );

    this.server.tool(
      "spotter_get_brand_css",
      "Returns the Mission Built design system as a CSS string. Useful for clients that want to render Spotter output as branded HTML cards instead of plain markdown. The CSS uses --mb-* custom properties and provides utility classes for verdicts, lens cards, and editorial typography.",
      {},
      async () => ({
        content: [{ type: "text" as const, text: brandCss() }],
      })
    );

    this.server.tool(
      "spotter_whoami",
      "Returns the authenticated user's identity (name and email) for the current MCP session. Useful for personalizing reviews or confirming the OAuth connection is active.",
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
      "spotter_review",
      "Primes the agent to review a B2B product epic using The Spotter's framework. Returns the SKILL.md content plus an instruction block telling the agent to apply review mode to the provided epic text. Use when the user pastes an epic and asks for a review.",
      {
        epic: z.string().min(50).describe("The full text of the epic to review. Should include problem statement, user, approach, competitive, pricing, and launch sections at minimum."),
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
              `4. Use the *critique-not-criticism* voice throughout: every flag is "you could strengthen this by..." — never "you missed..."\n` +
              `5. End with a Questions to ask the PM section and, if verdict is Needs polish or Not ready, an offer to work through specific gaps.\n\n` +
              `## SKILL.md\n\n${SKILL_MD}\n\n` +
              `## Epic to review\n\n${epic}\n\n` +
              `Now produce the review. Open with the verdict. Walk all nine lenses. Close with Questions to ask the PM and the push-forward offer.`,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_build",
      "Primes the agent to help a PM build a new epic from scratch using The Spotter's framework. The agent walks the PM through the nine lenses with guiding questions, lingering on Lens 1 before moving on. Output is a polished draft epic at the end.",
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
              `Use the *critique-not-criticism* voice. Ask questions; don't lecture. If the PM rushes past the user, gently slow them down: "Before we go further, can you tell me what it actually feels like to be this user on a hard day?"\n\n` +
              `## SKILL.md\n\n${SKILL_MD}\n\n` +
              `Begin with Lens 1. Ask about the user first.`,
          },
        ],
      })
    );

    this.server.tool(
      "spotter_iterate",
      "Primes the agent to push a partial draft epic forward using The Spotter's framework. The agent engages only the lenses that have content, asks targeted questions, and offers structure where the PM is stuck.",
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
              `Use the *critique-not-criticism* voice. Each suggestion uses "you could strengthen this by..." framing.\n\n` +
              `For lenses not yet drafted, ask: "Have you started thinking about [lens]? I can help you frame it."\n\n` +
              `## SKILL.md\n\n${SKILL_MD}\n\n` +
              `## Draft to iterate on\n\n${draft}\n\n` +
              `Walk the lenses present in the draft. Push each one forward.`,
          },
        ],
      })
    );

    // ---- RESOURCES ----

    this.server.resource(
      "skill",
      "spotter://skill",
      {
        name: "The Spotter — SKILL.md",
        description: "The full framework: philosophy, modes, nine lenses, sub-checks, output formats, anti-patterns, structured output schema.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "spotter://skill", mimeType: "text/markdown", text: SKILL_MD }],
      })
    );

    this.server.resource(
      "examples",
      "spotter://examples",
      {
        name: "The Spotter — Lens Examples",
        description: "64 worked examples across the nine lenses with teaching notes. Strong / needs-work / missing patterns calibrated through three rounds of testing.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "spotter://examples", mimeType: "text/markdown", text: LENS_EXAMPLES_MD }],
      })
    );

    this.server.resource(
      "calibration-epic",
      "spotter://calibration-epic",
      {
        name: "The Spotter — Calibration Epic",
        description: "Synthetic B2B security epic used as a calibration target. Running The Spotter against it produces a known verdict and lens-grade pattern.",
        mimeType: "text/markdown",
      },
      async () => ({
        contents: [{ uri: "spotter://calibration-epic", mimeType: "text/markdown", text: SYNTHETIC_EPIC_MD }],
      })
    );

    this.server.resource(
      "brand-css",
      "spotter://brand-css",
      {
        name: "The Spotter — Mission Built Brand CSS",
        description: "The Mission Built design system as a CSS stylesheet. Use to render Spotter output as branded HTML cards in compatible clients.",
        mimeType: "text/css",
      },
      async () => ({
        contents: [{ uri: "spotter://brand-css", mimeType: "text/css", text: brandCss() }],
      })
    );
  }
}

/**
 * The Worker entry point. Wraps the MCP agent with OAuthProvider so that
 * /sse requires a valid Bearer token, while public routes (landing, preview,
 * health, brand.css) and OAuth flow routes are handled by authHandler.
 *
 * Uses the current agents library API: McpAgent.mount(path) returns a fetch
 * handler that the OAuthProvider wraps with auth enforcement.
 */
export default new OAuthProvider({
  apiRoute: "/sse",
  apiHandler: SpotterMCP.mount("/sse") as any,
  defaultHandler: authHandler as any,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register",
});
