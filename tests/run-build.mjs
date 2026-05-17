/**
 * The Loadout — Spotter Build Mode Fixture Runner
 *
 * Reads a fixture file, extracts the feature and PM answers, then runs the
 * agent in direct mode (skipping the conversational Q&A) and saves a run
 * report so you can review the draft output without copy-pasting turn by turn.
 *
 * Usage:
 *   node run-build.mjs fixtures/spotter-build-commenting.md
 *   node run-build.mjs fixtures/my-other-feature.md
 *
 * Fixture format:
 *   ---
 *   feature: brief feature description here
 *   ---
 *
 *   Area 1 — ... answers ...
 *   Area 2 — ... answers ...
 *   (etc.)
 *
 * Output: test-output/<fixture-slug>.txt + console summary
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { readFileSync } from "fs";
import { join, dirname, basename } from "path";
import { fileURLToPath } from "url";

import { runAgent, saveRunReport, summarize } from "./harness.mjs";
import { spotterBuildMocks } from "./mocks.mjs";
import { spotterBuildInstructions } from "./instructions.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ─── Fixture parsing ──────────────────────────────────────────────────────────

/**
 * Parse a fixture file into { feature, answers }.
 * Frontmatter block (--- ... ---) must contain a "feature:" key.
 * Everything after the closing --- is the PM answers body.
 */
function parseFixture(filePath) {
  const raw = readFileSync(filePath, "utf8");

  const fmMatch = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!fmMatch) {
    throw new Error(
      `Fixture must start with a frontmatter block:\n` +
      `---\nfeature: your feature description\n---\n\n<answers here>`
    );
  }

  const [, frontmatter, body] = fmMatch;

  const featureMatch = frontmatter.match(/^feature:\s*(.+)$/m);
  if (!featureMatch) {
    throw new Error(`Frontmatter must include a "feature:" key.`);
  }

  const feature = featureMatch[1].trim();
  const answers = body.trim();

  if (!answers) {
    throw new Error(`Fixture body (PM answers) is empty.`);
  }

  return { feature, answers };
}

/**
 * Derive a slug from the fixture filename for use in the report filename.
 * e.g. "spotter-build-commenting.md" → "spotter-build-commenting"
 */
function fixtureSlug(filePath) {
  return basename(filePath).replace(/\.[^.]+$/, "");
}

// ─── Main ─────────────────────────────────────────────────────────────────────

const fixturePath = process.argv[2];

if (!fixturePath) {
  console.error(
    "\nUsage: node run-build.mjs <fixture-file>\n" +
    "  Example: node run-build.mjs fixtures/spotter-build-commenting.md\n"
  );
  process.exit(1);
}

const absoluteFixturePath = fixturePath.startsWith("/")
  ? fixturePath
  : join(__dirname, fixturePath);

let feature, answers;
try {
  ({ feature, answers } = parseFixture(absoluteFixturePath));
} catch (err) {
  console.error(`\n❌  Failed to parse fixture: ${err.message}\n`);
  process.exit(1);
}

const slug = fixtureSlug(fixturePath);

console.log(`\n▶  Spotter Build — ${slug}`);
console.log(`   Feature: ${feature}`);
console.log(`   Running agent in direct mode (answers pre-supplied)…\n`);

// Build the full message: instruction text + completion signal + answers
const instructions = spotterBuildInstructions(feature);
const mocks = spotterBuildMocks();

const completionSignal =
  `\n\n---\n` +
  `The PM has now answered questions across all nine areas. ` +
  `The conversation phase is complete. ` +
  `Proceed to step 5: call spotter_get_skill({ section: "build" }) and write the polished draft epic, ` +
  `then post the closing handoff line.\n\n` +
  `PM answers provided:\n${answers}`;

const fullMessage =
  `You called spotter_build and received these instructions. Follow them exactly.\n\n` +
  instructions +
  completionSignal;

const SYSTEM = `You are an AI assistant in Cowork mode.
Today's date is 2026-05-17.
User: Test`;

const run = await runAgent({
  systemPrompt: SYSTEM,
  userMessage: fullMessage,
  tools: mocks,
  maxTurns: 20,
});

// ─── Save report ──────────────────────────────────────────────────────────────

const reportPath = saveRunReport(slug, run);
console.log(`\n📄  Run report saved → ${reportPath}\n`);

// ─── Console summary ──────────────────────────────────────────────────────────

const results = [];

if (run.aborted) {
  console.log(`⚠️  Run aborted: ${run.abortReason}`);
  results.push({ name: "Run completed without abort", ok: false, message: run.abortReason });
} else {
  results.push({ name: "Run completed without abort", ok: true });
}

// Check: loaded framework before drafting
if (run.called("spotter_get_skill")) {
  results.push({ name: "spotter_get_skill called (framework loaded)", ok: true });
} else {
  results.push({ name: "spotter_get_skill called (framework loaded)", ok: false, message: "spotter_get_skill was never called" });
}

// Check: no template or artifact (build mode produces a document, not an HTML artifact)
if (run.called("spotter_get_template")) {
  results.push({ name: "no spotter_get_template (build is a doc, not an artifact)", ok: false, message: "spotter_get_template was called — build mode should not produce an HTML artifact" });
} else {
  results.push({ name: "no spotter_get_template (build is a doc, not an artifact)", ok: true });
}

// Check: handoff line
const hasHandoff =
  run.finalText.toLowerCase().includes("spotter review") &&
  (run.finalText.toLowerCase().includes("draft complete") ||
   run.finalText.toLowerCase().includes("run it through") ||
   run.finalText.toLowerCase().includes("grade") ||
   run.finalText.toLowerCase().includes("want to run"));

results.push({
  name: "handoff line present",
  ok: hasHandoff,
  message: hasHandoff ? null : `Handoff line not found. Output ends with:\n     …${run.finalText.slice(-300)}`,
});

// Print results
console.log("Checks:");
for (const r of results) {
  const icon = r.ok ? "✅" : "❌";
  console.log(`  ${icon}  ${r.name}`);
  if (!r.ok && r.message) console.log(`       ${r.message}`);
}

// Separator then draft preview
const draftPreview = run.finalText.trim().slice(0, 600);
console.log(`\n${"─".repeat(60)}`);
console.log("DRAFT PREVIEW (first 600 chars):");
console.log(`${"─".repeat(60)}`);
console.log(draftPreview || "  (no output)");
if (run.finalText.length > 600) console.log(`  … (${run.finalText.length} chars total — see full report)`);
console.log(`${"─".repeat(60)}\n`);

process.exit(summarize(results));
