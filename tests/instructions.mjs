/**
 * The Loadout — Instruction Templates for Tests
 *
 * These functions return the instruction text that the Loadout MCP server
 * sends to the agent when a skill tool is called (spotter_review, warmup_run,
 * spotter_build). Tests use these to simulate the full agent flow without
 * connecting to a live server.
 *
 * ⚠️  KEEP IN SYNC WITH index.ts ⚠️
 * When you update instruction text in index.ts, update the matching function
 * here. The version constants below are the easiest signal — if they diverge
 * from constants.ts, the tests are testing stale instructions.
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

/** Must match SPOTTER_VERSION in constants.ts */
export const SPOTTER_VERSION = "0.7.17";

/** Must match WARMUP_ENGINE_VERSION in constants.ts */
export const WARMUP_ENGINE_VERSION = "v0.8.1";

// ─── Spotter Review ───────────────────────────────────────────────────────────

/**
 * The instruction text returned by spotter_review().
 * @param {string} epic  - Full epic text
 * @param {string} [v]   - Spotter version (defaults to SPOTTER_VERSION)
 */
export function spotterReviewInstructions(epic, v = SPOTTER_VERSION) {
  return `# The Spotter v${v} — Review Mode

## The deliverable

The output of this review is an HTML file written to the user's workspace folder and registered in the Cowork artifact panel. That file IS the review.

The chat message you post at the end is a summary pointer to the artifact — not the review itself.

**Task failure:** If grades, findings, or verdicts appear in chat before the artifact file exists on disk, the task has failed. Build the artifact first. Always.

## Sequence

Execute steps 1 → 2 → 3 → 4. No grades, findings, or verdicts to chat until Step 4.

1. SETUP    — call list_artifacts → find workspace path → determine PATH A or B
2. GRADE    — load framework → grade all 9 areas silently → build SPOTTER_DATA
3. ARTIFACT — write HTML to disk → register artifact  ← THIS IS THE DELIVERABLE
4. CONFIRM  — post grade summary to chat (only after artifact exists)

## Permitted tools

Only these tools may be used. Everything else is forbidden.

  MCP:  list_artifacts · create_artifact · update_artifact
        spotter_get_skill · spotter_get_examples · spotter_get_template
  File: Read · Write · Edit · Grep

  Forbidden always: bash · mcp__workspace__bash · WebFetch · web_fetch · curl · wget

Note: spotter_get_template is an MCP tool call to the Loadout server — it is required and permitted. It is not a web fetch.

## Step 1 — Setup

a. Call list_artifacts.
b. Find workspace root:
   • Artifacts exist → take the html_path of any artifact and strip the filename.
     e.g. "/Users/jane/Projects/loadout/warmup-brief.html" → "/Users/jane/Projects/loadout"
   • No artifacts exist → find the user's selected workspace folder in your system context.
     It is the folder the user mounted in Cowork — a short, human-readable path like /Users/[name]/Projects/[folder].
     It is NOT the working directory, outputs folder, or any session/temp path.

   Validate before continuing — if the workspace root contains any of these strings, you have the WRONG path:
     "Application Support"  "sessions"  "outputs"  "uploads"  "local-agent"  "tmp"

   A correct workspace root looks like: /Users/mike/Projects/loadout
   If you cannot determine a valid workspace root, stop and ask the user to confirm their workspace folder.

c. Set target file: [workspace-root]/spotter-[epic-slug].html
   e.g. epic "Comments on Dashboards" → spotter-comments-on-dashboards.html
d. Determine path:
   • No Spotter artifact for this epic in list_artifacts → PATH B
   • Artifact exists → Read lines 1–3 of the workspace file (offset:0, limit:3)
     Line 2 is exactly "<!-- spotter-engine: v${v} -->" → PATH A
     Anything else, or cannot read → PATH B

## Step 2 — Grade (silent — no chat output)

Writing grades, findings, or verdicts to chat in this step is a task failure.
Grade exactly once — into SPOTTER_DATA. SPOTTER_DATA is the single source of truth.
Step 4 reads grades from SPOTTER_DATA. It does not re-grade independently.

a. Call spotter_get_skill({ section: "areas", intent: "Loading Spotter review framework" }).
b. Grade all nine areas against the epic silently.
   ✓ Pass → ["w","w","w"]  ·  ⚠️ Needs work → ["w","w","r"]  ·  ✗ Missing → ["r","r","r"]
c. Area 1 has 8 sub-checks and carries disproportionate weight.
   Area 9 is a gate: ✗ Missing on any B2B feature with agent actions or data access caps verdict at "Not ready."
d. Call spotter_get_examples({ area: N, intent: "..." }) if you need calibration on any area.
e. Build SPOTTER_DATA now — this is the one and only grading pass:
   epic: { name, company, teamShape, window, attempt, epicBody (full raw epic text verbatim) }
   areas: [ { id, n, name, category, question, judges, finding (1–3 sentences),
              spotterPull ("you could strengthen this by…"), handNote (optional 1-liner) } ]
   Voice: every flag is "you could strengthen this by…" — never "you missed" or "this is wrong."

## Step 3 — Artifact  ← Write the file. This is the output.

### PATH A (engine version matched — edit data block only)

a. Grep workspace file for '<script id="spotter-data">'.
b. Read that script block (2–3 lines).
c. Edit: replace the entire block with the new SPOTTER_DATA.
d. Call update_artifact with the workspace file path.

### PATH B (new file or engine mismatch — three tool calls, in order)

B-1. Call spotter_get_template({ intent: "…", spotter_data: JSON.stringify(SPOTTER_DATA), epicBody: [full raw epic text] })
     This returns a complete, self-contained HTML document with the renderer already inlined.
     Call it exactly once. Do not call it again for any reason — not to verify, not to retry.
     If the call fails, stop and report the error.

B-2. Get the HTML string from B-1. Two cases:
     • Response in context: the HTML string is directly available — use it as-is.
     • Response persisted to file: Cowork may save large responses to disk and return a file path.
       In this case, call Read on that path to retrieve the HTML string.
       The content is plain HTML — no JSON decoding, no bash, no other processing.

B-3. Call Write — file_path: [workspace-root]/spotter-[epic-slug].html
     content: the HTML string from B-2, unmodified.
     Bash is never needed for this step. If Write fails, report the error and stop.

B-4. Call create_artifact (first run) or update_artifact (re-run).
     id: "spotter-[epic-slug]"   html_path: the same file_path used in B-3

Step 3 is complete when the file is on disk and registered. Do not proceed to Step 4 until both B-3 and B-4 have succeeded.

## Step 4 — Confirm (artifact must already exist before this step)

Read grades from SPOTTER_DATA. Do not re-evaluate any area. The grades in this summary must exactly match the judges arrays in SPOTTER_DATA — if they differ, the review is wrong.

Write this and nothing else:

  Review complete — open the artifact panel to see the full report.

  **[Overall verdict]** · [N] of 9 areas passed

  | # | Area | Grade |
  |---|------|-------|
  | 1 | [name] | ✓ Pass / ⚠️ Needs work / ✗ Missing |
  | … |

  [1–2 sentences: biggest strength and the single most important thing to address.]

  *Full report → artifact panel. Questions? Reply here.*

## Epic

\`\`\`
${epic}
\`\`\`

Read all instructions above before starting. Then execute steps 1 → 2 → 3 → 4.`;
}

// ─── Spotter Build ────────────────────────────────────────────────────────────

/**
 * The instruction text returned by spotter_build().
 * @param {string} feature - Brief feature description
 * @param {string} [v]     - Spotter version
 */
export function spotterBuildInstructions(feature, v = SPOTTER_VERSION) {
  return `# The Spotter v${v} — Build Mode

A PM is building an epic for: **${feature}**.

## How to run build mode

1. Call spotter_get_skill({ section: "areas", intent: "Loading Spotter build framework" }) to load the area framework and sub-checks before starting.
2. Walk the PM through the nine areas with guiding questions. Ask — don't lecture.
3. Linger on Area 1: empathy (A), current state (B), why-not-solved (C), no solutioning (D), scope/value framing (E), assumptions surfaced (F), alternatives considered (G), epistemic openness (H). Get real answers on all eight sub-checks before moving to Area 2.
4. If the PM rushes past the user, gently slow them down: "Before we go further, can you tell me what it actually feels like to be this user on a hard day?"
5. Call spotter_get_skill({ section: "build", intent: "Loading build output format" }) when ready to draft the final epic.
6. The output at the end is a polished draft epic structured by area.
7. After delivering the draft, post this exact closing line — do not paraphrase it:
   Draft complete. Want to run it through The Spotter review to grade all nine areas and get a full report?

## Voice

Critique, not criticism. Ask questions; don't lecture. Every flag is "you could strengthen this by..." — never "you missed..."

Begin with Area 1. Ask about the user first.`;
}

// ─── Warmup Run ───────────────────────────────────────────────────────────────

/**
 * The instruction text returned by warmup_run().
 * @param {string} [v] - Warmup engine version
 */
export function warmupRunInstructions(v = WARMUP_ENGINE_VERSION) {
  return `# The Warmup — Run Brief

**Engine version: ${v}**

Read the user's WARMUP.md from their project root before proceeding. If it does not exist, run warmup_setup first.

## Permitted tools

Only these tools may be used. Everything else is forbidden.

  MCP:  list_artifacts · create_artifact · update_artifact
        warmup_get_skill · warmup_get_template · WebSearch
  File: Read · Write · Edit · Grep

  Forbidden always: bash · mcp__workspace__bash · WebFetch · web_fetch · curl · wget

## How to generate the brief

1. Find workspace root — call list_artifacts:
   • "the-warmup" exists → take its html_path and strip the filename to get the root.
     e.g. "/Users/jane/Projects/loadout/warmup.html" → "/Users/jane/Projects/loadout"
   • No "the-warmup" artifact → find the user's selected workspace folder in your system context.
     It is the folder the user mounted in Cowork — a short, human-readable path like /Users/[name]/Projects/[folder].
     It is NOT the working directory, outputs folder, or any session/temp path.
   Validate: if the workspace root contains any of these strings, you have the WRONG path:
     "Application Support"  "sessions"  "outputs"  "uploads"  "local-agent"  "tmp"
   A correct workspace root looks like: /Users/mike/Projects/loadout
   If you cannot determine a valid workspace root, stop and ask the user to confirm their workspace folder.
   Then read [workspace-root]/WARMUP.md. If WARMUP.md does not exist, run warmup_setup first.
2. Artifact and engine check — call list_artifacts.
   a) "the-warmup" does not exist → first run: set mode = "create". Proceed to step 4.
   b) "the-warmup" exists → use the Read file tool to read the first 10 lines of html_path.
      - File cannot be read → treat as first run: set mode = "create". Proceed to step 4.
      - First 10 lines contain <!-- warmup-engine: ${v} --> → Path A (version match). Proceed to step 4.
      - First 10 lines contain any other version or no marker → Path B (stale engine): set mode = "create". Proceed to step 4.
   Output this line in chat before proceeding: "📋 Artifact ready · [first run / engine match / engine update] · Fetching intelligence now."
3. TEMPLATE RULE — NON-NEGOTIABLE: The artifact HTML comes ONLY from warmup_get_template (PATH B) or the existing artifact file (PATH A). NEVER write HTML from scratch. NEVER reconstruct the template from training memory.
4. Fetch phase: for each active source, call WebSearch.
5. Run the link safety verification protocol on all URLs before including them.
6. Synthesize content into sections and build WARMUP_DATA.
7. Render the artifact:
   PATH A (version match — no template reload):
     a) Use Grep to find "<script id=\\"warmup-data\\">" in html_path.
     b) Use Read with offset+limit to read only that script block.
     c) Use Edit to replace the block with new WARMUP_DATA. Call update_artifact. Done.
   PATH B / FIRST RUN (engine update or new artifact):
     B-1. Call warmup_get_template({ intent: "...", chunk: 0 }) — do NOT pass warmup_data.
          The response is ~20KB and returned inline — no file read needed.
          Read <!-- WARMUP_TOTAL_CHUNKS: N --> from the response to learn N.
          The response ends with <!-- __WARMUP_SENTINEL__ --> when N > 1.
          If the call returns an error string, stop and report the error.
     B-2. Call Write — file_path: [workspace-root]/warmup.html
          content: exactly the text from B-1, verbatim.
     B-3. Inject WARMUP_DATA — call Edit immediately after Write.
          Match the ENTIRE 3-line script block (pure ASCII, no special characters):
          old_string (copy exactly, including newlines):
            <script id="warmup-data">
            window.WARMUP_DATA = null; // WARMUP-DATA-PLACEHOLDER
            </script>
          new_string (substitute your actual JSON):
            <script id="warmup-data">
            window.WARMUP_DATA = [JSON.stringify(WARMUP_DATA)];
            </script>
          ⚠ XSS: escape any </script> inside the JSON as <\\/script>.
          ⚠ CRITICAL: If Edit returns any error, STOP and report it. Do NOT proceed to B-4 with WARMUP_DATA still null — the artifact will be blank.
          Wait for Edit to succeed before B-4.
     B-4. ⚠ SEQUENTIAL ONLY — apply chunks one at a time, strictly in order.
          Do NOT fire Edit calls in parallel. The sentinel must be present before each Edit.
          Parallel Edits race to replace the same sentinel and corrupt the file.
          Repeat for i = 1, 2, … N-1:
            a. Call warmup_get_template({ intent: "...", chunk: i }).
               If the call returns an error string, stop and report it.
            b. Call Edit — old_string: "<!-- __WARMUP_SENTINEL__ -->"
                          new_string: [text from step a]
               Wait for Edit to succeed before starting i+1.
     B-5. Verify assembly: Grep warmup.html for "<!-- __WARMUP_SENTINEL__ -->".
          If found, assembly is incomplete — stop and report the error.
     B-6. Call create_artifact (first run) or update_artifact (stale engine).
          html_path: [workspace-root]/warmup.html
          ⚠ Do NOT call create_artifact or update_artifact before B-5 passes.
   NEVER write your own HTML. One summary line in chat — the brief is the artifact.

## Voice

The brief is factual and labeled. Every item shows its source and trust tier.
No editorializing. No hype. Keep it scannable and honest.`;
}
