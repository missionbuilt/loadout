/**
 * The Loadout — Warmup Compliance Tests
 *
 * Tests PATH B (new file / stale engine) and PATH A (engine match) to verify
 * the agent follows the correct tool call sequence and never writes HTML from
 * scratch or calls bash.
 *
 * Each scenario runs the agent ONCE. All assertions for that scenario share the
 * same result — this eliminates flakiness from per-test independent agent runs.
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { runAgent, assert, runSuite, summarize, saveRunReport, SCHEMAS } from "./harness.mjs";
import {
  warmupMocks,
  warmupArtifactExists,
  fileWithCurrentWarmupVersion,
  fileWithOldWarmupVersion,
  WORKSPACE_ROOT,
} from "./mocks.mjs";
import { warmupRunInstructions } from "./instructions.mjs";

// ─── Shared fixtures ──────────────────────────────────────────────────────────

const SYSTEM = `You are an AI assistant in Cowork mode.
The user has selected a workspace folder: ${WORKSPACE_ROOT}
Today's date is 2026-05-17.
User: Test`;

/** Simulate having already read WARMUP.md so the agent skips that step. */
const MOCK_WARMUP_MD = `
# Warmup Config

name: Test User
timezone: America/Chicago
search_depth: standard
skip_scan: true

## Active Sources

- Hacker News | https://news.ycombinator.com | active
- TechCrunch   | https://techcrunch.com      | active
`.trim();

function userMessage() {
  return (
    `You called warmup_run with the WARMUP.md already loaded. ` +
    `Follow these instructions exactly.\n\n` +
    warmupRunInstructions() +
    `\n\n## WARMUP.md (provided)\n\n\`\`\`\n${MOCK_WARMUP_MD}\n\`\`\``
  );
}

async function run(mocks) {
  return runAgent({
    systemPrompt: SYSTEM,
    userMessage:  userMessage(),
    tools:        mocks,
  });
}

// ─── Pre-run all scenarios once (shared results eliminate per-test flakiness) ──

const grepMock = {
  schema:  SCHEMAS.Grep,
  handler: () => `42:  <script id="warmup-data">`,
};

console.log("  Running PATH B (new file)…");
const pathBResult = await run(warmupMocks());

console.log("  Running PATH B (stale engine)…");
const pathBStaleResult = await run(warmupMocks({
  list_artifacts: warmupArtifactExists(),
  Read:           fileWithOldWarmupVersion(),
}));

console.log("  Running PATH A (engine match)…");
const pathAResult = await run(warmupMocks({
  list_artifacts: warmupArtifactExists(),
  Read:           fileWithCurrentWarmupVersion(),
  Grep:           grepMock,
}));

// ─── PATH B — new file (no existing artifact) ─────────────────────────────────

const pathBTests = [
  {
    name: "PATH B · calls list_artifacts",
    async fn() { return assert.called(pathBResult, "list_artifacts"); },
  },
  {
    name: "PATH B · calls warmup_get_template",
    async fn() { return assert.called(pathBResult, "warmup_get_template"); },
  },
  {
    name: "PATH B · calls Write after warmup_get_template",
    async fn() { return assert.warmupTemplateBeforeWrite(pathBResult); },
  },
  {
    name: "PATH B · calls create_artifact after Write",
    async fn() { return assert.writeBeforeArtifact(pathBResult); },
  },
  {
    name: "PATH B · artifact is registered",
    async fn() { return assert.artifactRegistered(pathBResult); },
  },
  {
    name: "PATH B · no forbidden tool calls",
    async fn() { return assert.noForbiddenTools(pathBResult); },
  },
  {
    name: "PATH B · Write path does not contain banned fragments",
    async fn() { return assert.writtenToCleanPath(pathBResult); },
  },
  {
    name: "PATH B · does not write HTML from scratch (warmup_get_template must be called)",
    async fn() {
      if (pathBResult.called("Write") && !pathBResult.called("warmup_get_template")) {
        return { ok: false, message: "Write called without warmup_get_template — agent wrote HTML from scratch" };
      }
      return { ok: true, message: null };
    },
  },
];

// ─── PATH B — stale engine (artifact exists but version is old) ───────────────

const pathBStaleTests = [
  {
    name: "PATH B (stale) · calls warmup_get_template despite artifact existing",
    async fn() { return assert.called(pathBStaleResult, "warmup_get_template"); },
  },
  {
    name: "PATH B (stale) · calls update_artifact (not create_artifact) after Write",
    async fn() { return assert.called(pathBStaleResult, "update_artifact"); },
  },
];

// ─── PATH A — engine version matches (edit data block only) ──────────────────

const pathATests = [
  {
    name: "PATH A · does NOT call warmup_get_template",
    async fn() { return assert.notCalled(pathAResult, "warmup_get_template"); },
  },
  {
    name: "PATH A · calls Edit to update data block",
    async fn() { return assert.called(pathAResult, "Edit"); },
  },
  {
    name: "PATH A · calls update_artifact after Edit",
    async fn() { return assert.calledBefore(pathAResult, "Edit", "update_artifact"); },
  },
  {
    name: "PATH A · no forbidden tool calls",
    async fn() { return assert.noForbiddenTools(pathAResult); },
  },
];

// ─── Capture run — saves a full report for quality review ────────────────────

const path = saveRunReport("warmup", pathBResult);
console.log(`\n   📄 Run report saved → ${path}`);

// ─── Runner ───────────────────────────────────────────────────────────────────

const allResults = [
  ...await runSuite("Warmup · PATH B (new file)",       pathBTests),
  ...await runSuite("Warmup · PATH B (stale engine)",   pathBStaleTests),
  ...await runSuite("Warmup · PATH A (engine match)",   pathATests),
];

if (process.argv[1].endsWith("warmup.test.mjs")) {
  process.exit(summarize(allResults));
}

export { allResults };
