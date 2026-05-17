/**
 * The Loadout — Agent Compliance Test Harness
 *
 * Runs agent instruction compliance tests against the Anthropic API.
 * All MCP and file tools are mocked — no deployed server or OAuth required.
 *
 * What this tests: given real instruction text, does the agent produce the
 * correct tool call sequence? Does it avoid forbidden tools? Does it write
 * to a valid workspace path?
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import Anthropic from "@anthropic-ai/sdk";
import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Use haiku by default (cheap, fast). Override with LOADOUT_TEST_MODEL env var.
export const MODEL     = process.env.LOADOUT_TEST_MODEL   ?? "claude-haiku-4-5-20251001";
export const MAX_TURNS = parseInt(process.env.LOADOUT_TEST_MAX_TURNS ?? "20", 10);

// Abort a run if approximate token usage exceeds this threshold.
// Prevents a looping agent from burning large amounts of API spend.
const TOKEN_BUDGET = parseInt(process.env.LOADOUT_TOKEN_BUDGET ?? "80000", 10);

// Abort if the same tool is called with identical args this many times in a row.
const DUPLICATE_CALL_LIMIT = 2;

const client = new Anthropic();

// ─── Tool schema helpers ──────────────────────────────────────────────────────

const str  = (d) => ({ type: "string",  description: d });
const num  = (d) => ({ type: "number",  description: d });
const bool = (d) => ({ type: "boolean", description: d });

/**
 * All tool schemas available to the agent under test.
 * Add new tools here as The Loadout grows.
 */
export const SCHEMAS = {
  // ── Cowork artifact tools ──────────────────────────────────────────────────
  list_artifacts: {
    name: "list_artifacts",
    description: "List all registered Cowork artifacts for the current workspace.",
    input_schema: {
      type: "object",
      properties: { intent: str("Why you are calling this tool.") },
    },
  },
  create_artifact: {
    name: "create_artifact",
    description: "Register an HTML file as a Cowork artifact.",
    input_schema: {
      type: "object",
      required: ["id", "html_path"],
      properties: {
        id:        str("Unique artifact ID."),
        html_path: str("Absolute path to the HTML file on disk."),
        title:     str("Optional display title."),
        intent:    str("Why you are calling this tool."),
      },
    },
  },
  update_artifact: {
    name: "update_artifact",
    description: "Update the file backing an existing Cowork artifact.",
    input_schema: {
      type: "object",
      required: ["id", "html_path"],
      properties: {
        id:        str("Artifact ID to update."),
        html_path: str("Absolute path to the updated HTML file."),
        intent:    str("Why you are calling this tool."),
      },
    },
  },

  // ── File tools ─────────────────────────────────────────────────────────────
  Read: {
    name: "Read",
    description: "Read a file from the local filesystem.",
    input_schema: {
      type: "object",
      required: ["file_path"],
      properties: {
        file_path: str("Absolute path to the file."),
        offset:    num("Line number to start reading from."),
        limit:     num("Number of lines to read."),
      },
    },
  },
  Write: {
    name: "Write",
    description: "Write content to a file, creating it if it does not exist.",
    input_schema: {
      type: "object",
      required: ["file_path", "content"],
      properties: {
        file_path: str("Absolute path to the file."),
        content:   str("Content to write."),
      },
    },
  },
  Edit: {
    name: "Edit",
    description: "Replace an exact string in a file.",
    input_schema: {
      type: "object",
      required: ["file_path", "old_string", "new_string"],
      properties: {
        file_path:   str("Absolute path to the file."),
        old_string:  str("Exact string to find and replace."),
        new_string:  str("Replacement string."),
        replace_all: bool("Replace all occurrences (default false)."),
      },
    },
  },
  Grep: {
    name: "Grep",
    description: "Search for a regex pattern in files.",
    input_schema: {
      type: "object",
      required: ["pattern"],
      properties: {
        pattern:     str("Regex pattern to search for."),
        path:        str("Directory or file to search."),
        output_mode: { type: "string", enum: ["content", "files_with_matches", "count"] },
        "-n":        bool("Show line numbers."),
        "-C":        num("Lines of context around each match."),
      },
    },
  },

  // ── Spotter MCP tools ──────────────────────────────────────────────────────
  spotter_review: {
    name: "spotter_review",
    description: "Prime the agent to review a B2B epic using The Spotter framework.",
    input_schema: {
      type: "object",
      required: ["epic"],
      properties: {
        epic:   str("Full text of the epic to review."),
        intent: str("Why you are calling this tool."),
      },
    },
  },
  spotter_get_skill: {
    name: "spotter_get_skill",
    description: "Load a section of the Spotter nine-area framework.",
    input_schema: {
      type: "object",
      properties: {
        section: { type: "string", enum: ["overview", "areas", "build", "full"] },
        intent:  str("Why you are calling this tool."),
      },
    },
  },
  spotter_get_examples: {
    name: "spotter_get_examples",
    description: "Load pass/fail calibration examples for one Spotter area.",
    input_schema: {
      type: "object",
      required: ["area"],
      properties: {
        area:   num("Area number (1–9)."),
        intent: str("Why you are calling this tool."),
      },
    },
  },
  spotter_get_template: {
    name: "spotter_get_template",
    description: "Build and return a complete, self-contained Spotter HTML report.",
    input_schema: {
      type: "object",
      required: ["spotter_data"],
      properties: {
        spotter_data: str("JSON string of SPOTTER_DATA object."),
        epicBody:     str("Full raw epic text verbatim."),
        intent:       str("Why you are calling this tool."),
      },
    },
  },

  // ── Spotter build/iterate tools ────────────────────────────────────────────
  spotter_build: {
    name: "spotter_build",
    description: "Prime the agent to walk a PM through building an epic from scratch.",
    input_schema: {
      type: "object",
      required: ["feature"],
      properties: {
        feature: str("Brief description of the feature to build an epic for."),
        intent:  str("Why you are calling this tool."),
      },
    },
  },

  // ── Warmup MCP tools ───────────────────────────────────────────────────────
  warmup_run: {
    name: "warmup_run",
    description: "Prime the agent to produce a Warmup daily brief.",
    input_schema: {
      type: "object",
      properties: {
        mode:   str("Brief mode: standard, deep, or quick."),
        intent: str("Why you are calling this tool."),
      },
    },
  },
  warmup_get_skill: {
    name: "warmup_get_skill",
    description: "Load a section of the Warmup skill framework.",
    input_schema: {
      type: "object",
      properties: {
        section: { type: "string", enum: ["overview", "run", "full"] },
        intent:  str("Why you are calling this tool."),
      },
    },
  },
  warmup_get_template: {
    name: "warmup_get_template",
    description: "Build and return a complete, self-contained Warmup HTML brief.",
    input_schema: {
      type: "object",
      required: ["warmup_data"],
      properties: {
        warmup_data: str("JSON string of WARMUP_DATA object."),
        intent:      str("Why you are calling this tool."),
      },
    },
  },
};

// ─── TestRun — captures what the agent did ────────────────────────────────────

export class TestRun {
  constructor() {
    /** All tool calls in chronological order: { name, input, output } */
    this.callLog = [];
    /** Text blocks emitted to chat before the first artifact was registered */
    this.preArtifactChat = [];
    /** Full accumulated text output */
    this.finalText = "";
    /** Whether create_artifact or update_artifact was ever called */
    this.artifactRegistered = false;
    /** html_path from the artifact registration call */
    this.artifactPath = null;
    /** Set to true if the run was aborted early (forbidden tool, duplicate, budget) */
    this.aborted = false;
    /** Human-readable reason for early abort */
    this.abortReason = null;
    /** Approximate token usage across all turns */
    this.approxTokens = 0;
  }

  toolsCalledInOrder() {
    return this.callLog.map((c) => c.name);
  }

  indexOf(toolName) {
    return this.callLog.findIndex((c) => c.name === toolName);
  }

  called(toolName) {
    return this.callLog.some((c) => c.name === toolName);
  }

  callsOf(toolName) {
    return this.callLog.filter((c) => c.name === toolName);
  }

  calledBefore(toolA, toolB) {
    const a = this.indexOf(toolA);
    const b = this.indexOf(toolB);
    return a !== -1 && b !== -1 && a < b;
  }
}

// ─── Agent runner ─────────────────────────────────────────────────────────────

/**
 * Run an agent loop against the Anthropic API.
 *
 * @param {object} options
 * @param {string}   options.systemPrompt  - Cowork context + any instructions
 * @param {string}   options.userMessage   - First user turn
 * @param {object}   options.tools         - { [toolName]: { schema, handler } }
 * @param {number}   [options.maxTurns]    - Safety limit on turns (default MAX_TURNS)
 * @returns {Promise<TestRun>}
 */
const FORBIDDEN_TOOL_NAMES = new Set([
  "bash", "mcp__workspace__bash", "WebFetch", "web_fetch", "curl", "wget",
]);

/**
 * Run an agent loop against the Anthropic API.
 *
 * Safeguards (all abort the run and set run.aborted = true):
 *   - Forbidden tool called (bash, web fetch) → immediate abort
 *   - Same tool+args called DUPLICATE_CALL_LIMIT times in a row → abort
 *   - Approximate token spend exceeds TOKEN_BUDGET → abort
 *   - Turn count exceeds maxTurns → stop (not an error, just ends)
 *
 * @param {object} options
 * @param {string}   options.systemPrompt  - Cowork context + any instructions
 * @param {string}   options.userMessage   - First user turn
 * @param {object}   options.tools         - { [toolName]: { schema, handler } }
 * @param {number}   [options.maxTurns]    - Safety limit on turns (default MAX_TURNS)
 * @returns {Promise<TestRun>}
 */
export async function runAgent({ systemPrompt, userMessage, tools, maxTurns = MAX_TURNS }) {
  const run = new TestRun();
  const toolSchemas = Object.values(tools)
    .filter((t) => t?.schema)
    .map((t) => t.schema);
  const messages = [{ role: "user", content: userMessage }];

  // Track consecutive duplicate calls: key → count
  const dupTracker = new Map();

  for (let turn = 0; turn < maxTurns; turn++) {
    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 4096,
      system: systemPrompt,
      tools: toolSchemas,
      messages,
    });

    // Approximate token tracking (chars ÷ 4 is a rough but fast estimate)
    run.approxTokens += JSON.stringify(response).length / 4;
    if (run.approxTokens > TOKEN_BUDGET) {
      run.aborted = true;
      run.abortReason = `Token budget exceeded (~${Math.round(run.approxTokens).toLocaleString()} tokens). Increase LOADOUT_TOKEN_BUDGET to allow longer runs.`;
      break;
    }

    // Accumulate text output
    for (const block of response.content) {
      if (block.type === "text" && block.text.trim()) {
        if (!run.artifactRegistered) run.preArtifactChat.push(block.text);
        run.finalText += block.text;
      }
    }

    const toolCalls = response.content.filter((b) => b.type === "tool_use");
    if (toolCalls.length === 0 || response.stop_reason === "end_turn") break;

    // ── Safeguard: forbidden tool ────────────────────────────────────────────
    const forbiddenCall = toolCalls.find(
      (c) => FORBIDDEN_TOOL_NAMES.has(c.name) || c.name.toLowerCase().includes("bash")
    );
    if (forbiddenCall) {
      run.callLog.push({
        name: forbiddenCall.name,
        input: forbiddenCall.input,
        output: "ABORTED: forbidden tool",
      });
      run.aborted = true;
      run.abortReason = `Forbidden tool called: "${forbiddenCall.name}" — run aborted to prevent token waste.`;
      break;
    }

    // ── Safeguard: duplicate call detection ───────────────────────────────────
    let duplicateDetected = false;
    for (const call of toolCalls) {
      // Exclude args that naturally change each call (intent, content)
      const stableInput = { ...call.input };
      delete stableInput.intent;
      delete stableInput.content; // Write content changes intentionally
      const key = `${call.name}:${JSON.stringify(stableInput)}`;
      const count = (dupTracker.get(key) ?? 0) + 1;
      dupTracker.set(key, count);
      if (count > DUPLICATE_CALL_LIMIT) {
        run.aborted = true;
        run.abortReason = `Duplicate call loop: "${call.name}" called ${count} times with identical args — aborting to prevent token waste.`;
        duplicateDetected = true;
        break;
      }
    }
    if (duplicateDetected) break;

    messages.push({ role: "assistant", content: response.content });

    const results = [];
    for (const call of toolCalls) {
      const mock = tools[call.name];

      // Unmocked tool = not available — return an error so the agent knows
      const output = mock
        ? await mock.handler(call.input, run)
        : `Error: tool "${call.name}" is not available in this test environment.`;

      // Track artifact registration
      if (call.name === "create_artifact" || call.name === "update_artifact") {
        run.artifactRegistered = true;
        run.artifactPath = call.input.html_path ?? null;
      }

      run.callLog.push({ name: call.name, input: call.input, output });

      // Clear dup tracker only for tools that legitimately repeat with no limit.
      // Write and Edit are intentionally excluded — their counts must accumulate
      // so that looping Write calls (agent writing HTML in chunks) trigger abort.
      if (!["list_artifacts", "Read", "Grep", "Write", "Edit"].includes(call.name)) {
        dupTracker.clear();
      }

      results.push({
        type: "tool_result",
        tool_use_id: call.id,
        content: typeof output === "string" ? output : JSON.stringify(output),
      });
    }

    messages.push({ role: "user", content: results });
  }

  return run;
}

// ─── Artifact output ──────────────────────────────────────────────────────────

/**
 * Save a human-readable run report to test-output/[name].txt.
 * Shows tool sequence, SPOTTER_DATA / WARMUP_DATA passed to the template,
 * pre-artifact chat, and final chat output.
 *
 * Call this from your test file after a representative run to give Mike
 * a reviewable artifact without re-running manually.
 *
 * @param {string}  name  - Filename slug (no extension)
 * @param {TestRun} run
 * @returns {string} Absolute path to the saved file
 */
export function saveRunReport(name, run) {
  const outDir = join(__dirname, "test-output");
  mkdirSync(outDir, { recursive: true });
  const outPath = join(outDir, `${name}.txt`);

  const sep = "─".repeat(60);

  const toolLines = run.callLog.map((c, i) => {
    const args = Object.entries(c.input ?? {})
      .filter(([k]) => k !== "intent" && k !== "content") // skip noisy args
      .map(([k, v]) => {
        const s = typeof v === "string" ? v : JSON.stringify(v);
        return `${k}: ${s.length > 100 ? s.slice(0, 100) + "…" : s}`;
      })
      .join(", ");
    return `  ${String(i + 1).padStart(2)}. ${c.name}${args ? `  (${args})` : ""}`;
  });

  // Capture template data args for quality review
  const templateCalls = [
    ...run.callsOf("spotter_get_template"),
    ...run.callsOf("warmup_get_template"),
  ];
  const templateDataLines = templateCalls.flatMap((c) => {
    const dataKey = c.input.spotter_data ?? c.input.warmup_data ?? null;
    if (!dataKey) return ["  (no data arg found)"];
    try {
      const parsed = JSON.parse(dataKey);
      return [JSON.stringify(parsed, null, 2)
        .split("\n")
        .slice(0, 80) // first 80 lines — enough to review
        .map((l) => "  " + l)
        .join("\n")];
    } catch {
      return [`  ${dataKey.slice(0, 500)}`];
    }
  });

  const lines = [
    `The Loadout — Agent Run Report`,
    `Name:   ${name}`,
    `Date:   ${new Date().toISOString()}`,
    `Model:  ${MODEL}`,
    `Turns:  ${Math.ceil(run.callLog.length / 2)} approx`,
    `Tokens: ~${Math.round(run.approxTokens).toLocaleString()}`,
    run.aborted ? `\n⚠️  ABORTED: ${run.abortReason}` : "",
    "",
    sep,
    "TOOL SEQUENCE",
    sep,
    toolLines.length ? toolLines.join("\n") : "  (no tool calls)",
    "",
    sep,
    "TEMPLATE DATA (what was graded / synthesized)",
    sep,
    templateDataLines.length ? templateDataLines.join("\n") : "  (template was not called)",
    "",
    sep,
    "PRE-ARTIFACT CHAT (text before artifact was registered)",
    sep,
    run.preArtifactChat.length
      ? run.preArtifactChat.map((t) => t.trim()).join("\n\n---\n\n")
      : "  (none — good)",
    "",
    sep,
    "FINAL CHAT OUTPUT",
    sep,
    run.finalText.trim() || "  (none)",
  ].filter((l) => l !== undefined);

  writeFileSync(outPath, lines.join("\n") + "\n");
  return outPath;
}

// ─── Assertions ───────────────────────────────────────────────────────────────

const BANNED_PATH_FRAGMENTS = [
  "Application Support",
  "sessions",
  "/outputs",
  "uploads",
  "local-agent",
  "/tmp",
  "/temp",
];

function pass()          { return { ok: true,  message: null }; }
function fail(message)   { return { ok: false, message }; }

export const assert = {
  /** toolA must appear in the call log before toolB */
  calledBefore(run, toolA, toolB) {
    if (!run.called(toolA)) return fail(`"${toolA}" was never called`);
    if (!run.called(toolB)) return fail(`"${toolB}" was never called`);
    if (!run.calledBefore(toolA, toolB)) {
      return fail(
        `Expected "${toolA}" before "${toolB}".\n` +
        `     Sequence: ${run.toolsCalledInOrder().join(" → ")}`
      );
    }
    return pass();
  },

  /** Tool must have been called at least once */
  called(run, toolName) {
    if (!run.called(toolName)) return fail(`"${toolName}" was never called`);
    return pass();
  },

  /** Tool must NOT have been called */
  notCalled(run, toolName) {
    if (run.called(toolName)) {
      return fail(
        `"${toolName}" was called but should not have been.\n` +
        `     Sequence: ${run.toolsCalledInOrder().join(" → ")}`
      );
    }
    return pass();
  },

  /** No bash or web-fetch tools may appear in the call log */
  noForbiddenTools(run) {
    if (run.aborted && run.abortReason?.includes("Forbidden tool")) {
      return fail(run.abortReason);
    }
    const hit = run.callLog.find(
      (c) => FORBIDDEN_TOOL_NAMES.has(c.name) || c.name.toLowerCase().includes("bash")
    );
    if (hit) return fail(`Forbidden tool called: "${hit.name}"`);
    return pass();
  },

  /** Run must not have been aborted (covers duplicate loops and budget overruns) */
  notAborted(run) {
    if (run.aborted) return fail(`Run aborted: ${run.abortReason}`);
    return pass();
  },

  /** Every Write call must use a path that does not contain banned fragments */
  writtenToCleanPath(run) {
    const writes = run.callsOf("Write");
    if (writes.length === 0) return fail("No Write call found");
    for (const w of writes) {
      const path = w.input.file_path ?? "";
      for (const banned of BANNED_PATH_FRAGMENTS) {
        if (path.includes(banned)) {
          return fail(`Write path contains banned fragment "${banned}":\n     ${path}`);
        }
      }
    }
    return pass();
  },

  /** Write must come before create_artifact in the call log */
  writeBeforeArtifact(run) {
    return assert.calledBefore(run, "Write", "create_artifact");
  },

  /** Either create_artifact or update_artifact must have been called */
  artifactRegistered(run) {
    const ok = run.called("create_artifact") || run.called("update_artifact");
    if (!ok) return fail("Neither create_artifact nor update_artifact was called");
    return pass();
  },

  /** spotter_get_template must come before Write */
  templateBeforeWrite(run) {
    return assert.calledBefore(run, "spotter_get_template", "Write");
  },

  /** warmup_get_template must come before Write */
  warmupTemplateBeforeWrite(run) {
    return assert.calledBefore(run, "warmup_get_template", "Write");
  },

  /** Chat output before artifact must not contain grade markers */
  noGradesBeforeArtifact(run) {
    const gradePattern = /✓ Pass|⚠️ Needs work|✗ Missing|\| # \| Area/;
    for (const text of run.preArtifactChat) {
      if (gradePattern.test(text)) {
        return fail("Grade output found in chat before artifact was registered");
      }
    }
    return pass();
  },

  /** Final text output must contain a given substring */
  outputContains(run, substring) {
    if (!run.finalText.includes(substring)) {
      return fail(`Expected output to contain: "${substring}"`);
    }
    return pass();
  },
};

// ─── Test runner ──────────────────────────────────────────────────────────────

/**
 * Run a named suite of tests. Each test is { name, fn } where fn returns
 * an assertion result { ok, message } or throws.
 *
 * @param {string} suiteName
 * @param {Array<{name: string, fn: () => Promise<{ok,message}>}>} tests
 * @returns {Promise<Array<{name, ok, message}>>}
 */
export async function runSuite(suiteName, tests) {
  console.log(`\n▶  ${suiteName}`);
  const results = [];

  for (const { name, fn } of tests) {
    process.stdout.write(`   ${name} … `);
    try {
      const result = await fn();
      if (result.ok) {
        console.log("✅");
        results.push({ name, ok: true });
      } else {
        console.log("❌");
        console.log(`     ${result.message}`);
        results.push({ name, ok: false, message: result.message });
      }
    } catch (err) {
      console.log("❌");
      console.log(`     ${err.message}`);
      results.push({ name, ok: false, message: err.message });
    }
  }

  return results;
}

/**
 * Print a final summary and return an exit code (0 = all pass, 1 = failures).
 */
export function summarize(allResults) {
  const total  = allResults.length;
  const passed = allResults.filter((r) => r.ok).length;
  const failed = total - passed;

  console.log("\n──────────────────────────────────────");
  if (failed === 0) {
    console.log(`✅  All ${total} tests passed`);
  } else {
    console.log(`❌  ${failed} failed · ${passed} passed · ${total} total`);
    for (const r of allResults.filter((r) => !r.ok)) {
      console.log(`   • ${r.name}: ${r.message}`);
    }
  }
  console.log("──────────────────────────────────────\n");

  return failed === 0 ? 0 : 1;
}
