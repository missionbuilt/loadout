/**
 * The Loadout — Spotter Build Mode Compliance Tests
 *
 * Verifies that build mode loads the framework before engaging,
 * asks questions before drafting, and posts the handoff line after the draft.
 *
 * Note: build mode is conversational, so tests simulate a short PM exchange
 * rather than a single-turn completion.
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { runAgent, assert, runSuite, summarize } from "./harness.mjs";
import { spotterBuildMocks } from "./mocks.mjs";
import { spotterBuildInstructions } from "./instructions.mjs";

// ─── Shared fixtures ──────────────────────────────────────────────────────────

const FEATURE = "in-app commenting on analytics dashboards";

const SYSTEM = `You are an AI assistant in Cowork mode.
Today's date is 2026-05-17.
User: Test`;

/**
 * Build mode is multi-turn. We simulate two turns:
 * 1. Agent receives instructions and asks first question
 * 2. PM provides a rich enough answer to move things forward
 * 3. We check the final output for compliance
 */
async function runBuildMode(pmReplies = []) {
  // Turn 1: prime with instructions
  const instructions = spotterBuildInstructions(FEATURE);
  const primeMessage =
    `You called spotter_build and received these instructions. Follow them exactly.\n\n` +
    instructions;

  // We run with a fixed set of PM replies injected as additional turns.
  // For compliance tests, we just need enough context to reach the draft stage.
  const { runAgent: _run, SCHEMAS } = await import("./harness.mjs");

  const mocks = spotterBuildMocks();

  // Simple single-pass: send instructions and a trailing PM response so the
  // agent can reach the draft stage in one context window.
  const fullMessage =
    primeMessage +
    (pmReplies.length
      ? `\n\n---\nPM response to your first question:\n${pmReplies.join("\n\n")}`
      : "");

  return runAgent({
    systemPrompt: SYSTEM,
    userMessage:  fullMessage,
    tools:        mocks,
    maxTurns:     15,
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

const buildTests = [
  {
    name: "loads spotter_get_skill with section:areas before asking questions",
    async fn() {
      const r = await runBuildMode();
      return assert.called(r, "spotter_get_skill");
    },
  },
  {
    name: "does not call spotter_get_template (build mode produces a doc, not a report)",
    async fn() {
      const r = await runBuildMode([
        "Our users are data analysts at mid-market companies. They spend their days building reports in our product and then screenshotting charts to Slack because there's no structured way to discuss a specific data point in context.",
        "The current workaround is screenshots in Slack. It's been this way for three years. Nobody files tickets about it because it only takes ten seconds — but the insight dies the moment the screenshot is taken.",
        "We haven't solved it because it always loses to chart types and query performance in prioritization. The pain is chronic, not acute.",
      ]);
      return assert.notCalled(r, "spotter_get_template");
    },
  },
  {
    name: "does not call create_artifact (build mode output is a document, not an HTML artifact)",
    async fn() {
      const r = await runBuildMode([
        "Analysts. They build dashboards and share them with finance and ops stakeholders who rarely log in.",
      ]);
      // Build mode should not register an artifact — it produces a draft doc
      if (r.called("create_artifact")) {
        return { ok: false, message: "create_artifact was called in build mode — expected document output only" };
      }
      return { ok: true, message: null };
    },
  },
  {
    name: "no forbidden tool calls",
    async fn() {
      const r = await runBuildMode();
      return assert.noForbiddenTools(r);
    },
  },
  {
    name: "handoff line appears in output after draft is complete",
    async fn() {
      // Provide full PM answers across all areas to push the agent to draft
      const fullAnswers = [
        // Area 1 — user understanding
        "Our user is a data analyst at a 500-person SaaS company. They build dashboards and share them with finance and ops who never log back in.",
        "Current state: they screenshot charts and paste to Slack. The conversation happens off-platform on a dead copy of the data.",
        "It's unsolved because the workaround takes ten seconds and nobody files a ticket. The pain is invisible.",
        "We're not designing a solution yet — we're trying to understand the problem.",
        "Value: if stakeholders engage in-product, the analyst gets feedback on live data instead of stale screenshots.",
        "Assumption: decision-makers will come into the product if we send them a direct link with context.",
        "We looked at Slack integration and a digest feature. Both move the conversation off-platform.",
        "We might be wrong that comments solve this. Deep linking or a better share flow might matter more.",
        // Area 2 — competitive
        "Tableau comments are view-level, not element-level. Power BI lives in Teams. Looker gates it behind Enterprise.",
        // Area 3 — differentiation
        "We already have element identity for every chart. Anchoring is cheap for us; a competitor would have to build it first.",
        // Area 4 — solution
        "Side panel, no AI in v1. Could expose a webhook API for external comment creation.",
        // Area 5 — impact
        "Touches notifications, permissions model, and data lifecycle. Comments as platform infrastructure.",
        // Area 6 — pricing
        "Free on all paid tiers. Retention bet, not a monetization gate.",
        // Area 7 — launch
        "Three named enterprise accounts for closed beta. Marketing not yet in the epic.",
        // Area 8 — post-launch
        "Target: 40% of externally shared dashboards have one non-analyst comment within 60 days.",
        // Area 9 — trust
        "Comments scoped to dashboard access. Per-dashboard setting to restrict to internal users only before GA.",
      ];

      const r = await runBuildMode(fullAnswers);
      // Check for the handoff concept — agent may paraphrase the exact wording
      const hasHandoff =
        r.finalText.toLowerCase().includes("spotter review") &&
        (r.finalText.toLowerCase().includes("draft complete") ||
         r.finalText.toLowerCase().includes("run it through") ||
         r.finalText.toLowerCase().includes("grade") ||
         r.finalText.toLowerCase().includes("want to run"));
      if (!hasHandoff) {
        return { ok: false, message: `Handoff line not found in output. Final text ends with:\n     …${r.finalText.slice(-300)}` };
      }
      return { ok: true, message: null };
    },
  },
];

// ─── Runner ───────────────────────────────────────────────────────────────────

const allResults = await runSuite("Spotter Build Mode", buildTests);

if (process.argv[1].endsWith("spotter-build.test.mjs")) {
  process.exit(summarize(allResults));
}

export { allResults };
