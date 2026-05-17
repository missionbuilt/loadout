/**
 * The Loadout — Warmup Compliance Tests
 *
 * Tests PATH B (new file / stale engine) and PATH A (engine match) to verify
 * the agent follows the correct tool call sequence and never writes HTML from
 * scratch or calls bash.
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

// ─── PATH B — new file (no existing artifact) ─────────────────────────────────

const pathBTests = [
  {
    name: "PATH B · calls list_artifacts",
    async fn() {
      const r = await run(warmupMocks());
      return assert.called(r, "list_artifacts");
    },
  },
  {
    name: "PATH B · calls warmup_get_template",
    async fn() {
      const r = await run(warmupMocks());
      return assert.called(r, "warmup_get_template");
    },
  },
  {
    name: "PATH B · calls Write after warmup_get_template",
    async fn() {
      const r = await run(warmupMocks());
      return assert.warmupTemplateBeforeWrite(r);
    },
  },
  {
    name: "PATH B · calls create_artifact after Write",
    async fn() {
      const r = await run(warmupMocks());
      return assert.writeBeforeArtifact(r);
    },
  },
  {
    name: "PATH B · artifact is registered",
    async fn() {
      const r = await run(warmupMocks());
      return assert.artifactRegistered(r);
    },
  },
  {
    name: "PATH B · no forbidden tool calls",
    async fn() {
      const r = await run(warmupMocks());
      return assert.noForbiddenTools(r);
    },
  },
  {
    name: "PATH B · Write path does not contain banned fragments",
    async fn() {
      const r = await run(warmupMocks());
      return assert.writtenToCleanPath(r);
    },
  },
  {
    name: "PATH B · does not write HTML from scratch (warmup_get_template must be called)",
    async fn() {
      const r = await run(warmupMocks());
      // If Write is called without warmup_get_template being called first,
      // the agent wrote HTML from memory — a known anti-pattern.
      if (r.called("Write") && !r.called("warmup_get_template")) {
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
    async fn() {
      const r = await run(
        warmupMocks({
          list_artifacts: warmupArtifactExists(),
          Read:           fileWithOldWarmupVersion(),
        })
      );
      return assert.called(r, "warmup_get_template");
    },
  },
  {
    name: "PATH B (stale) · calls update_artifact (not create_artifact) after Write",
    async fn() {
      const r = await run(
        warmupMocks({
          list_artifacts: warmupArtifactExists(),
          Read:           fileWithOldWarmupVersion(),
        })
      );
      // For stale engine, agent should update the existing artifact, not create a new one
      return assert.called(r, "update_artifact");
    },
  },
];

// ─── PATH A — engine version matches (edit data block only) ──────────────────

const pathATests = [
  {
    name: "PATH A · does NOT call warmup_get_template",
    async fn() {
      const r = await run(
        warmupMocks({
          list_artifacts: warmupArtifactExists(),
          Read:           fileWithCurrentWarmupVersion(),
          Grep: {
            schema:  SCHEMAS.Grep,
            handler: () => `42:  <script id="warmup-data">`,
          },
        })
      );
      return assert.notCalled(r, "warmup_get_template");
    },
  },
  {
    name: "PATH A · calls Edit to update data block",
    async fn() {
      const r = await run(
        warmupMocks({
          list_artifacts: warmupArtifactExists(),
          Read:           fileWithCurrentWarmupVersion(),
          Grep: {
            schema:  SCHEMAS.Grep,
            handler: () => `42:  <script id="warmup-data">`,
          },
        })
      );
      return assert.called(r, "Edit");
    },
  },
  {
    name: "PATH A · calls update_artifact after Edit",
    async fn() {
      const r = await run(
        warmupMocks({
          list_artifacts: warmupArtifactExists(),
          Read:           fileWithCurrentWarmupVersion(),
          Grep: {
            schema:  SCHEMAS.Grep,
            handler: () => `42:  <script id="warmup-data">`,
          },
        })
      );
      return assert.calledBefore(r, "Edit", "update_artifact");
    },
  },
  {
    name: "PATH A · no forbidden tool calls",
    async fn() {
      const r = await run(
        warmupMocks({
          list_artifacts: warmupArtifactExists(),
          Read:           fileWithCurrentWarmupVersion(),
          Grep: {
            schema:  SCHEMAS.Grep,
            handler: () => `42:  <script id="warmup-data">`,
          },
        })
      );
      return assert.noForbiddenTools(r);
    },
  },
];

// ─── Capture run — saves a full report for quality review ────────────────────

async function captureRun() {
  const r = await run(warmupMocks());
  const path = saveRunReport("warmup", r);
  console.log(`\n   📄 Run report saved → ${path}`);
}

// ─── Runner ───────────────────────────────────────────────────────────────────

const allResults = [
  ...await runSuite("Warmup · PATH B (new file)",       pathBTests),
  ...await runSuite("Warmup · PATH B (stale engine)",   pathBStaleTests),
  ...await runSuite("Warmup · PATH A (engine match)",   pathATests),
];

await captureRun();

if (process.argv[1].endsWith("warmup.test.mjs")) {
  process.exit(summarize(allResults));
}

export { allResults };
