/**
 * The Loadout — Spotter Review Mode Fixture Runner
 *
 * Reads a fixture file containing an epic, runs the agent through the full
 * Spotter review sequence (PATH B — new file), and saves a run report so you
 * can inspect the SPOTTER_DATA the agent produced and the final grade table
 * without going through the UI.
 *
 * Usage:
 *   node run-review.mjs fixtures/spotter-review-comments-on-dashboards.md
 *   node run-review.mjs fixtures/my-other-epic.md
 *
 * Fixture format:
 *   ---
 *   name: Human-readable epic name
 *   slug: url-safe-slug (optional — derived from name if omitted)
 *   ---
 *
 *   # Epic: Full epic text here
 *   (all markdown sections follow)
 *
 * Output: test-output/<slug>.txt + console summary
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { readFileSync } from "fs";
import { join, dirname, basename } from "path";
import { fileURLToPath } from "url";

import { runAgent, saveRunReport, summarize, SCHEMAS } from "./harness.mjs";
import { spotterReviewMocks, WORKSPACE_ROOT } from "./mocks.mjs";
import { spotterReviewInstructions } from "./instructions.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ─── Fixture parsing ──────────────────────────────────────────────────────────

/**
 * Parse a review fixture file into { name, slug, epic }.
 * Frontmatter block (--- ... ---) must contain a "name:" key.
 * Body is the full epic text.
 */
function parseFixture(filePath) {
  const raw = readFileSync(filePath, "utf8");

  const fmMatch = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!fmMatch) {
    throw new Error(
      `Fixture must start with a frontmatter block:\n` +
      `---\nname: Epic Name\nslug: epic-slug\n---\n\n<epic text here>`
    );
  }

  const [, frontmatter, body] = fmMatch;

  const nameMatch = frontmatter.match(/^name:\s*(.+)$/m);
  if (!nameMatch) {
    throw new Error(`Frontmatter must include a "name:" key.`);
  }

  const name = nameMatch[1].trim();

  // slug is optional — derive from name if not provided
  const slugMatch = frontmatter.match(/^slug:\s*(.+)$/m);
  const slug = slugMatch
    ? slugMatch[1].trim()
    : name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  const epic = body.trim();
  if (!epic) throw new Error(`Fixture body (epic text) is empty.`);

  return { name, slug, epic };
}

/**
 * Derive a report slug from the fixture filename.
 * e.g. "spotter-review-comments-on-dashboards.md" → "spotter-review-comments-on-dashboards"
 */
function fixtureSlug(filePath) {
  return basename(filePath).replace(/\.[^.]+$/, "");
}

// ─── Main ─────────────────────────────────────────────────────────────────────

const fixturePath = process.argv[2];

if (!fixturePath) {
  console.error(
    "\nUsage: node run-review.mjs <fixture-file>\n" +
    "  Example: node run-review.mjs fixtures/spotter-review-comments-on-dashboards.md\n"
  );
  process.exit(1);
}

const absoluteFixturePath = fixturePath.startsWith("/")
  ? fixturePath
  : join(__dirname, fixturePath);

let name, slug, epic;
try {
  ({ name, slug, epic } = parseFixture(absoluteFixturePath));
} catch (err) {
  console.error(`\n❌  Failed to parse fixture: ${err.message}\n`);
  process.exit(1);
}

const reportSlug = fixtureSlug(fixturePath);

console.log(`\n▶  Spotter Review — ${name}`);
console.log(`   Epic slug: ${slug}`);
console.log(`   Running agent in PATH B (new file) mode…\n`);

// Build the user message: agent just received spotter_review instructions
const fullMessage =
  `You called spotter_review and received these instructions. ` +
  `Follow them exactly.\n\n` +
  spotterReviewInstructions(epic);

/** Minimal Cowork system context — must match what review tests use */
const SYSTEM = `You are an AI assistant in Cowork mode.
The user has selected a workspace folder: ${WORKSPACE_ROOT}
Today's date is 2026-05-17.
User: Test`;

// PATH B mocks: no existing artifact → full template → Write → create_artifact
const mocks = spotterReviewMocks();

const run = await runAgent({
  systemPrompt: SYSTEM,
  userMessage:  fullMessage,
  tools:        mocks,
  maxTurns:     20,
});

// ─── Save report ──────────────────────────────────────────────────────────────

const reportPath = saveRunReport(reportSlug, run);
console.log(`\n📄  Run report saved → ${reportPath}\n`);

// ─── Compliance checks ────────────────────────────────────────────────────────

const results = [];

// Aborted?
if (run.aborted) {
  console.log(`⚠️  Run aborted: ${run.abortReason}`);
  results.push({ name: "Run completed without abort", ok: false, message: run.abortReason });
} else {
  results.push({ name: "Run completed without abort", ok: true });
}

// list_artifacts called first
results.push(
  run.called("list_artifacts")
    ? { name: "list_artifacts called (setup step)", ok: true }
    : { name: "list_artifacts called (setup step)", ok: false, message: "list_artifacts was never called" }
);

// Framework loaded before template
const skillBeforeTemplate =
  run.called("spotter_get_skill") &&
  (!run.called("spotter_get_template") ||
   run.callLog.findIndex(c => c.name === "spotter_get_skill") <
   run.callLog.findIndex(c => c.name === "spotter_get_template"));
results.push(
  skillBeforeTemplate
    ? { name: "spotter_get_skill before template (framework loaded)", ok: true }
    : { name: "spotter_get_skill before template (framework loaded)", ok: false,
        message: "spotter_get_skill not called before spotter_get_template" }
);

// Template called
results.push(
  run.called("spotter_get_template")
    ? { name: "spotter_get_template called (PATH B template fetch)", ok: true }
    : { name: "spotter_get_template called (PATH B template fetch)", ok: false,
        message: "spotter_get_template was never called" }
);

// Write before create_artifact
const writeIdx    = run.callLog.findIndex(c => c.name === "Write");
const artifactIdx = run.callLog.findIndex(c => c.name === "create_artifact" || c.name === "update_artifact");
const writeBeforeArtifact = writeIdx !== -1 && artifactIdx !== -1 && writeIdx < artifactIdx;
results.push(
  writeBeforeArtifact
    ? { name: "Write before create_artifact (file on disk first)", ok: true }
    : { name: "Write before create_artifact (file on disk first)", ok: false,
        message: `Write index: ${writeIdx}, artifact index: ${artifactIdx}` }
);

// Artifact registered
const artifactRegistered = run.called("create_artifact") || run.called("update_artifact");
results.push(
  artifactRegistered
    ? { name: "artifact registered (create_artifact or update_artifact)", ok: true }
    : { name: "artifact registered (create_artifact or update_artifact)", ok: false,
        message: "Neither create_artifact nor update_artifact was called" }
);

// No forbidden tools
const forbiddenHit = run.callLog.find(
  c => ["bash","mcp__workspace__bash","WebFetch","web_fetch","curl","wget"].includes(c.name) ||
       c.name.toLowerCase().includes("bash")
);
results.push(
  !forbiddenHit && !run.abortReason?.includes("Forbidden tool")
    ? { name: "no forbidden tool calls (bash / web fetch)", ok: true }
    : { name: "no forbidden tool calls (bash / web fetch)", ok: false,
        message: forbiddenHit ? `Forbidden tool called: "${forbiddenHit.name}"` : run.abortReason }
);

// Write path is clean
const writeCalls = run.callLog.filter(c => c.name === "Write");
const BANNED = ["Application Support","sessions","/outputs","uploads","local-agent","/tmp","/temp"];
const dirtyWrite = writeCalls.find(w =>
  BANNED.some(banned => (w.input.file_path ?? "").includes(banned))
);
results.push(
  writeCalls.length === 0
    ? { name: "Write path is clean", ok: false, message: "No Write call found" }
    : dirtyWrite
      ? { name: "Write path is clean", ok: false,
          message: `Write path contains banned fragment: ${dirtyWrite.input.file_path}` }
      : { name: "Write path is clean", ok: true }
);

// No grades in chat before artifact
const gradePattern = /✓ Pass|⚠️ Needs work|✗ Missing|\| # \| Area/;
const gradeBeforeArtifact = run.preArtifactChat.some(t => gradePattern.test(t));
results.push(
  gradeBeforeArtifact
    ? { name: "no grades in chat before artifact", ok: false,
        message: "Grade output found in chat before artifact was registered" }
    : { name: "no grades in chat before artifact", ok: true }
);

// Print results
console.log("Checks:");
for (const r of results) {
  const icon = r.ok ? "✅" : "❌";
  console.log(`  ${icon}  ${r.name}`);
  if (!r.ok && r.message) console.log(`       ${r.message}`);
}

// Tool sequence
console.log(`\n${"─".repeat(60)}`);
console.log("TOOL SEQUENCE:");
console.log(`${"─".repeat(60)}`);
run.callLog.forEach((c, i) => {
  const extra = c.name === "Write" && c.input.file_path
    ? `  → ${c.input.file_path}`
    : c.name === "spotter_get_template"
      ? "  (template fetched)"
      : "";
  console.log(`  ${String(i + 1).padStart(2)}. ${c.name}${extra}`);
});

// Grade table preview from final chat
console.log(`\n${"─".repeat(60)}`);
console.log("FINAL CHAT OUTPUT (grade table):");
console.log(`${"─".repeat(60)}`);
const preview = run.finalText.trim().slice(0, 800);
console.log(preview || "  (no output)");
if (run.finalText.length > 800) console.log(`  … (${run.finalText.length} chars total — see full report)`);
console.log(`${"─".repeat(60)}\n`);

process.exit(summarize(results));
