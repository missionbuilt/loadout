/**
 * The Loadout — Mock Tool Responses
 *
 * Provides mock handlers for every MCP and file tool the agent may call.
 * Use the scenario builders to construct test-specific tool sets.
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { SCHEMAS } from "./harness.mjs";

// ─── Constants ────────────────────────────────────────────────────────────────

/** The workspace path tests expect the agent to write to. */
export const WORKSPACE_ROOT = "/Users/test/Projects/loadout";

/** Keep in sync with constants.ts SPOTTER_VERSION */
export const SPOTTER_VERSION = "0.7.17";

/** Keep in sync with constants.ts WARMUP_ENGINE_VERSION */
export const WARMUP_ENGINE_VERSION = "v0.7.7";

// ─── Minimal valid HTML templates ─────────────────────────────────────────────

/** Smallest HTML that passes the DOCTYPE + engine-marker checks */
export const MOCK_SPOTTER_HTML =
`<!DOCTYPE html>
<!-- spotter-engine: v${SPOTTER_VERSION} -->
<html lang="en">
<head><meta charset="UTF-8"><title>Spotter</title></head>
<body>
<div id="root"></div>
<script id="spotter-data">
window.SPOTTER_DATA = {"epic":{"name":"Test Epic","epicBody":""},"areas":[]};
</script>
</body>
</html>`;

/** Minimal WARMUP.md config so Read(WARMUP.md) returns valid config, not "File not found" */
export const MOCK_WARMUP_MD =
`name: Test User
timezone: America/Chicago
search_depth: standard
skip_scan: true

## Active Sources

- Hacker News | https://news.ycombinator.com | active
- TechCrunch   | https://techcrunch.com      | active`;

export const MOCK_WARMUP_HTML =
`<!DOCTYPE html>
<!-- warmup-engine: ${WARMUP_ENGINE_VERSION} -->
<!-- WARMUP_TOTAL_CHUNKS: 1 -->
<html lang="en">
<head><meta charset="UTF-8"><title>Warmup</title></head>
<script id="warmup-data">
window.WARMUP_DATA = null;
</script>
<body><script>
/* warmup-shell stub */
</script></body>
</html>`;

// ─── Scenario builders ────────────────────────────────────────────────────────

/**
 * list_artifacts returns an empty list.
 * Forces PATH B (new file) for any skill.
 */
export function noArtifacts() {
  return tool("list_artifacts", () =>
    JSON.stringify({ artifacts: [] })
  );
}

/**
 * list_artifacts returns one Spotter artifact for the given slug.
 * Agent will then Read the file to check the engine version.
 */
export function spotterArtifactExists(slug = "test-feature") {
  return tool("list_artifacts", () =>
    JSON.stringify({
      artifacts: [{
        id:        `spotter-${slug}`,
        html_path: `${WORKSPACE_ROOT}/spotter-${slug}.html`,
        title:     "Spotter Report",
      }],
    })
  );
}

/**
 * list_artifacts returns one Warmup artifact.
 * Agent will then Read the file to check the engine version.
 */
export function warmupArtifactExists() {
  return tool("list_artifacts", () =>
    JSON.stringify({
      artifacts: [{
        id:        "the-warmup",
        html_path: `${WORKSPACE_ROOT}/warmup.html`,
        title:     "Daily Brief",
      }],
    })
  );
}

/**
 * Read returns file content with the CURRENT engine version on line 2.
 * Triggers PATH A (edit data block only).
 */
export function fileWithCurrentSpotterVersion() {
  return tool("Read", () =>
    `<!DOCTYPE html>\n<!-- spotter-engine: v${SPOTTER_VERSION} -->\n<html>...`
  );
}

/**
 * Read returns file content with a stale engine version on line 2.
 * Triggers PATH B (full template rewrite).
 */
export function fileWithOldSpotterVersion() {
  return tool("Read", () =>
    `<!DOCTYPE html>\n<!-- spotter-engine: v0.0.1 -->\n<html>...`
  );
}

/** Stub warmup-data block returned when the agent reads the script block by offset. */
const MOCK_WARMUP_DATA_BLOCK =
`<script id="warmup-data">
window.WARMUP_DATA = {"meta":{"generatedAt":"08:00 CDT"}};
</script>`;

/**
 * Read returns file content with the CURRENT warmup engine version.
 * Triggers PATH A for the Warmup.
 * - WARMUP.md reads return the config stub.
 * - Offset-based reads (the agent reading the warmup-data block by line number) return
 *   a stub script block so the agent can proceed to Edit it.
 * - All other reads return the current-version HTML header (version check).
 */
export function fileWithCurrentWarmupVersion() {
  return tool("Read", ({ file_path, offset }) => {
    if (file_path && file_path.includes("WARMUP.md")) return MOCK_WARMUP_MD;
    if (offset != null && offset > 0) return MOCK_WARMUP_DATA_BLOCK;
    return `<!DOCTYPE html>\n<!-- warmup-engine: ${WARMUP_ENGINE_VERSION} -->\n<!-- WARMUP_TOTAL_CHUNKS: 1 -->\n<html>...`;
  });
}

/**
 * Read returns a file with a stale warmup engine version.
 * Triggers PATH B for the Warmup.
 * Path-aware: WARMUP.md reads return config, HTML file reads return stale-version HTML.
 */
export function fileWithOldWarmupVersion() {
  return tool("Read", ({ file_path }) => {
    if (file_path && file_path.includes("WARMUP.md")) return MOCK_WARMUP_MD;
    return `<!DOCTYPE html>\n<!-- warmup-engine: v0.0.1 -->\n<html>...`;
  });
}

// ─── Standard mock sets ───────────────────────────────────────────────────────

/**
 * Full mock set for Spotter review tests.
 * Pass scenario overrides to swap individual tools.
 *
 * @param {object} overrides  - { toolName: mockTool(...) }
 */
export function spotterReviewMocks(overrides = {}) {
  return {
    list_artifacts:       noArtifacts(),
    Read:                 tool("Read",  ({ file_path }) => `File not found: ${file_path}`),
    Write:                tool("Write", ({ file_path, content }) =>
                            `Written ${content?.length ?? 0} chars to ${file_path}`),
    Edit:                 tool("Edit",  () => "Edit applied."),
    Grep:                 tool("Grep",  () => "No matches."),
    spotter_get_skill:    tool("spotter_get_skill", ({ section }) =>
                            spotterSkillStub(section)),
    spotter_get_examples: tool("spotter_get_examples", ({ area }) =>
                            `# Examples for Area ${area}\nPass: ...\nFail: ...`),
    spotter_get_template: tool("spotter_get_template", () => MOCK_SPOTTER_HTML),
    create_artifact:      tool("create_artifact",  ({ id }) => `Artifact "${id}" registered.`),
    update_artifact:      tool("update_artifact",  ({ id }) => `Artifact "${id}" updated.`),
    ...overrides,
  };
}

/**
 * Full mock set for Spotter build mode tests.
 */
export function spotterBuildMocks(overrides = {}) {
  return {
    spotter_get_skill:    tool("spotter_get_skill", ({ section }) =>
                            spotterSkillStub(section)),
    spotter_get_examples: tool("spotter_get_examples", ({ area }) =>
                            `# Examples for Area ${area}\nPass: ...\nFail: ...`),
    ...overrides,
  };
}

/**
 * Full mock set for Warmup tests.
 */
export function warmupMocks(overrides = {}) {
  return {
    list_artifacts:    noArtifacts(),
    // Path-aware: WARMUP.md returns config so the agent doesn't try to create it.
    // Any other path (e.g. warmup.html on first run) returns "File not found".
    Read:              tool("Read", ({ file_path }) => {
                         if (file_path && file_path.includes("WARMUP.md")) return MOCK_WARMUP_MD;
                         return `File not found: ${file_path}`;
                       }),
    Write:             tool("Write", ({ file_path, content }) =>
                         `Written ${content?.length ?? 0} chars to ${file_path}`),
    Edit:              tool("Edit",  () => "Edit applied."),
    Grep:              tool("Grep",  () => "No matches."),
    WebSearch:         tool("WebSearch", ({ query }) =>
                         JSON.stringify({ results: [], query, note: "No results in test environment — skip_scan:true, proceed to render." })),
    warmup_get_skill:  tool("warmup_get_skill",   () => warmupSkillStub()),
    warmup_get_template: tool("warmup_get_template", () => MOCK_WARMUP_HTML),
    create_artifact:   tool("create_artifact",  ({ id }) => `Artifact "${id}" registered.`),
    update_artifact:   tool("update_artifact",  ({ id }) => `Artifact "${id}" updated.`),
    ...overrides,
  };
}

// ─── Stub content ─────────────────────────────────────────────────────────────

function spotterSkillStub(section) {
  if (section === "areas") {
    return `# Spotter Areas

Area 1: User Understanding — Does the epic demonstrate deep user empathy?
  Sub-checks: (A) empathy, (B) current state, (C) why-not-solved, (D) no solutioning,
  (E) scope/value, (F) assumptions, (G) alternatives, (H) epistemic openness.

Area 2: Competitive Landscape — Does it name and differentiate from alternatives?
Area 3: Strategic Differentiation — Why this company, why now?
Area 4: Solution Approach — Is the approach justified and appropriately scoped?
Area 5: Holistic Impact — Does it map cross-cutting concerns?
Area 6: Packaging & Pricing — Is the business model considered?
Area 7: Launch Readiness — Is there a go-to-market plan?
Area 8: Post-Launch Ownership — Are metrics and ownership defined?
Area 9: Trust & Governance — Are security and compliance addressed?
  Gate: ✗ Missing on any B2B feature with agent actions or data access caps verdict at "Not ready."

Grade: ✓ Pass → ["w","w","w"] · ⚠️ Needs work → ["w","w","r"] · ✗ Missing → ["r","r","r"]`;
  }
  if (section === "build") {
    return `# Spotter Build Output Format

Produce a structured draft epic with one section per area. Each section should:
- State what is known
- Flag what is assumed
- Identify what remains open

End with a summary of the top three open questions.`;
  }
  return `# Spotter Framework Overview\n\nNine-area framework for reviewing B2B product epics.\nCall with section: "areas" to load the grading criteria.`;
}

function warmupSkillStub() {
  return `# Warmup Framework

Sections: news, markets, priorities, reflection.
Produce a WARMUP_DATA JSON object with one entry per section.
Call warmup_get_template to build the HTML artifact.`;
}

// ─── Internal helper ──────────────────────────────────────────────────────────

/** Create a mock tool with schema from SCHEMAS and a custom handler. */
function tool(name, handler) {
  return { schema: SCHEMAS[name], handler };
}
