/**
 * The Loadout — Spotter Review Compliance Tests
 *
 * Tests both PATH B (new file / engine mismatch) and PATH A (engine match)
 * to verify the agent follows the correct tool call sequence.
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { runAgent, assert, runSuite, summarize, saveRunReport } from "./harness.mjs";
import {
  spotterReviewMocks,
  spotterArtifactExists,
  fileWithCurrentSpotterVersion,
  fileWithOldSpotterVersion,
  noArtifacts,
  WORKSPACE_ROOT,
} from "./mocks.mjs";
import { spotterReviewInstructions } from "./instructions.mjs";

// ─── Shared fixtures ──────────────────────────────────────────────────────────

const TEST_EPIC = `
Feature: In-app commenting on analytics dashboards.
Users: Data analysts at mid-market B2B SaaS companies (200–2,000 employees).
Problem: Insights don't travel well. Analysts screenshot charts and share via Slack.
By the time a stakeholder follows up, the data is stale and context is gone.
Solution: Threaded comments anchored to specific charts, with @mentions and thread resolution.
Success: Stakeholders engage in-product instead of via Slack screenshots.
Measured by: comment reply rate from non-analyst roles within 30 days of beta.
Team: 2 engineers, 6 weeks. Closed beta with 3 enterprise design partners at week 4.
Security: Comments scoped to dashboard view access. No AI processing of comment content.
Pricing: Available on all paid tiers — activation and retention bet, not a monetization gate.
`.trim();

/** Minimal Cowork system context the agent needs to make path decisions. */
const SYSTEM = `You are an AI assistant in Cowork mode.
The user has selected a workspace folder: ${WORKSPACE_ROOT}
Today's date is 2026-05-17.
User: Test`;

/** Build the initial user message: call spotter_review → follow instructions */
function userMessage(epic = TEST_EPIC) {
  return (
    `You called spotter_review and received these instructions. ` +
    `Follow them exactly.\n\n` +
    spotterReviewInstructions(epic)
  );
}

// ─── Helper: run one agent test ───────────────────────────────────────────────

async function run(mocks) {
  return runAgent({
    systemPrompt: SYSTEM,
    userMessage:  userMessage(),
    tools:        mocks,
  });
}

// ─── PATH B — new file (no existing artifact) ─────────────────────────────────

const pathBTests = [
  {
    name: "PATH B · calls list_artifacts first",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.called(r, "list_artifacts");
    },
  },
  {
    name: "PATH B · calls spotter_get_skill before template",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.calledBefore(r, "spotter_get_skill", "spotter_get_template");
    },
  },
  {
    name: "PATH B · calls spotter_get_template",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.called(r, "spotter_get_template");
    },
  },
  {
    name: "PATH B · calls Write immediately after template",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.calledBefore(r, "spotter_get_template", "Write");
    },
  },
  {
    name: "PATH B · calls create_artifact after Write",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.writeBeforeArtifact(r);
    },
  },
  {
    name: "PATH B · artifact is registered",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.artifactRegistered(r);
    },
  },
  {
    name: "PATH B · no forbidden tool calls (bash / web fetch)",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.noForbiddenTools(r);
    },
  },
  {
    name: "PATH B · Write path does not contain banned fragments",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.writtenToCleanPath(r);
    },
  },
  {
    name: "PATH B · no grades or verdicts in chat before artifact",
    async fn() {
      const r = await run(spotterReviewMocks());
      return assert.noGradesBeforeArtifact(r);
    },
  },
];

// ─── PATH B — engine mismatch (artifact exists but version is stale) ──────────

const pathBMismatchTests = [
  {
    name: "PATH B (mismatch) · calls spotter_get_template despite artifact existing",
    async fn() {
      const r = await run(
        spotterReviewMocks({
          list_artifacts: spotterArtifactExists("test-feature"),
          Read:           fileWithOldSpotterVersion(),
        })
      );
      return assert.called(r, "spotter_get_template");
    },
  },
  {
    name: "PATH B (mismatch) · Write path is clean",
    async fn() {
      const r = await run(
        spotterReviewMocks({
          list_artifacts: spotterArtifactExists("test-feature"),
          Read:           fileWithOldSpotterVersion(),
        })
      );
      return assert.writtenToCleanPath(r);
    },
  },
];

// ─── PATH A — engine version matches (edit data block only) ──────────────────

const pathATests = [
  {
    name: "PATH A · does NOT call spotter_get_template",
    async fn() {
      const r = await run(
        spotterReviewMocks({
          list_artifacts: spotterArtifactExists("test-feature"),
          Read:           fileWithCurrentSpotterVersion(),
          Grep:           { schema: (await import("./harness.mjs")).SCHEMAS.Grep,
                            handler: () => `1:  <script id="spotter-data">` },
        })
      );
      return assert.notCalled(r, "spotter_get_template");
    },
  },
  {
    name: "PATH A · calls Edit before update_artifact",
    async fn() {
      const r = await run(
        spotterReviewMocks({
          list_artifacts: spotterArtifactExists("test-feature"),
          Read:           fileWithCurrentSpotterVersion(),
          Grep:           { schema: (await import("./harness.mjs")).SCHEMAS.Grep,
                            handler: () => `1:  <script id="spotter-data">` },
        })
      );
      return assert.calledBefore(r, "Edit", "update_artifact");
    },
  },
  {
    name: "PATH A · artifact is updated",
    async fn() {
      const r = await run(
        spotterReviewMocks({
          list_artifacts: spotterArtifactExists("test-feature"),
          Read:           fileWithCurrentSpotterVersion(),
          Grep:           { schema: (await import("./harness.mjs")).SCHEMAS.Grep,
                            handler: () => `1:  <script id="spotter-data">` },
        })
      );
      return assert.called(r, "update_artifact");
    },
  },
  {
    name: "PATH A · no forbidden tool calls",
    async fn() {
      const r = await run(
        spotterReviewMocks({
          list_artifacts: spotterArtifactExists("test-feature"),
          Read:           fileWithCurrentSpotterVersion(),
          Grep:           { schema: (await import("./harness.mjs")).SCHEMAS.Grep,
                            handler: () => `1:  <script id="spotter-data">` },
        })
      );
      return assert.noForbiddenTools(r);
    },
  },
];

// ─── Capture run — saves a full report for quality review ────────────────────
//
// One representative PATH B run is saved to test-output/spotter-review.txt
// after every test run. Open it to inspect:
//   • The tool call sequence
//   • The SPOTTER_DATA the agent produced (grades + findings)
//   • The final chat output (Step 4 grade table)
//
// This is the artifact Mike reviews to verify quality, not just compliance.

async function captureRun() {
  const r = await run(spotterReviewMocks());
  const path = saveRunReport("spotter-review", r);
  console.log(`\n   📄 Run report saved → ${path}`);
}

// ─── Runner ───────────────────────────────────────────────────────────────────

const allResults = [
  ...await runSuite("Spotter Review · PATH B (new file)",        pathBTests),
  ...await runSuite("Spotter Review · PATH B (engine mismatch)", pathBMismatchTests),
  ...await runSuite("Spotter Review · PATH A (engine match)",    pathATests),
];

await captureRun();

// Exit with non-zero code if run directly (not via run-all.mjs)
if (process.argv[1].endsWith("spotter-review.test.mjs")) {
  process.exit(summarize(allResults));
}

export { allResults };
