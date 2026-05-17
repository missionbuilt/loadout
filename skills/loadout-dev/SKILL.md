---
name: loadout-dev
description: >
  Expert development partner for The Loadout — the Mission Built MCP server
  (mcp.missionbuilt.io) that powers The Warmup and The Spotter skills. Use this
  skill any time you are working on the Loadout project: adding or editing a skill,
  modifying warmup-template.html or spotter-template.html, changing index.ts tools,
  bumping versions, editing SKILL.md files, running a tech lead review, or preparing
  a commit and deploy. Also use it when the user says things like "work on the warmup,"
  "add a new loadout skill," "update the spotter," "edit the template," "bump the
  version," or "review before we ship." This skill carries the full project architecture,
  hard-won lessons from past sessions, and the exact collaboration model Mike and Claude
  use — including the rule that Mike runs all terminal commands and Claude writes all code.
---

# Loadout Dev

You are working on **The Loadout** — an open-source MCP server at `mcp.missionbuilt.io`
that exposes two AI skills to Claude: **The Warmup** (daily intelligence brief) and
**The Spotter** (B2B epic review). The server is a Cloudflare Worker + Durable Objects
with Google OAuth 2.1.

Read `references/project-context.md` for the full file map, design tokens, tool inventory,
and architecture. This SKILL.md covers the collaboration model and all hard-won lessons —
read it fully before touching any file.

---

## Collaboration model — non-negotiable

**Mike runs all terminal commands. Claude writes all code.**

- Write code changes with the file tools (Read, Edit, Write).
- When a shell command is needed (git, wrangler, npm), write it as a code block
  and wait for Mike to run it and paste the output back. Never assume it succeeded.
- Never use bash to fetch URLs — use WebFetch or WebSearch tools instead.
- When in doubt about the current state of a file, Read it rather than assuming.

This keeps Mike in control of deploys, git history, and destructive operations.

---

## The one rule that causes the most problems if you forget it

**Templates live in two places. Always edit canonical first, then sync the bundled copy.**

### Warmup template

| Copy | Path |
|------|------|
| Canonical | `/Users/mike/Projects/loadout/warmup/warmup-template.html` |
| Bundled | `/Users/mike/Projects/loadout/missionbuilt-mcp/src/skill-content/warmup/warmup-template.html` |

### Spotter shell

| Copy | Path |
|------|------|
| Canonical | `/Users/mike/Projects/loadout/spotter/spotter-shell.rawjs` |
| Bundled | `/Users/mike/Projects/loadout/missionbuilt-mcp/src/skill-content/spotter/spotter-shell.rawjs` |

Every CSS, HTML, and JS change goes into the canonical copy first. Then apply the
identical change to the bundled copy. If they diverge, agents silently work against
a stale template and the Worker serves the wrong design.

After any template edit, verify both copies match with Grep before committing.

---

## Version bump rules

All version constants live in one file: `missionbuilt-mcp/src/constants.ts`

```typescript
export const SERVER_VERSION        = "1.0.33";  // Worker deploy version (semver)
export const WARMUP_VERSION        = "0.3.17";  // bump when SKILL.md or template changes
export const WARMUP_ENGINE_VERSION = "v0.3.17"; // bump when warmup-template.html changes
export const SPOTTER_VERSION       = "0.7.17";  // bump when Spotter instructions or areas change
export const THE_APPROACH_VERSION  = "0.1.4";   // bump when Approach SKILL.md or template changes
export const TOOL_COUNT            = 20;        // update when adding or removing tools
```

**What to bump for what:**

| What changed | Bump |
|---|---|
| `warmup-template.html` (any change) | `WARMUP_VERSION` + `WARMUP_ENGINE_VERSION` + `SERVER_VERSION` |
| Warmup SKILL.md or instructions only | `WARMUP_VERSION` + `SERVER_VERSION` |
| Spotter instruction text (index.ts) | `SPOTTER_VERSION` + `SERVER_VERSION` |
| Spotter template / shell JS | `SPOTTER_VERSION` + `SERVER_VERSION` |
| New tool added or removed | `TOOL_COUNT` + `SERVER_VERSION` |
| Worker infrastructure change | `SERVER_VERSION` only |

**Also bump `tests/instructions.mjs`:** the `SPOTTER_VERSION` and `WARMUP_ENGINE_VERSION`
constants at the top of that file must stay in sync with `constants.ts` manually.
If they diverge, the test suite runs against stale instructions and will miss regressions.
There is no automated sync — this is a manual discipline.

**Why `WARMUP_ENGINE_VERSION` is critical:** agents use it to decide whether to reload
the full template (Path B) or just swap out the data block (Path A). If you change
the template but don't bump the engine version, every agent with an existing artifact
takes Path A and never picks up your new HTML. The old layout stays frozen forever.

---

## Commit and deploy workflow

```bash
git add -A
git commit -m 'spotter v0.7.17 — short description of what changed'
git push
cd missionbuilt-mcp
npx wrangler deploy
```

**Verify after deploy:** `https://mcp.missionbuilt.io/health` — `server_version` must match
`SERVER_VERSION` in constants.ts.

**The `$` trap in commit messages:** the shell interprets `$'`, `$&`, and `` $` `` as
special sequences inside double-quoted strings. Use single quotes for commit messages
or avoid `$` in the message body entirely.

**Separate git add from the tests directory:** if your working directory is `tests/`,
running `git add tests/` will try to find `tests/tests/` and fail. Always `cd` to the
repo root before staging, or use relative paths like `git add ../missionbuilt-mcp/src/`.

---

## Agent instruction framing — lessons from Spotter development

These are the hardest-won lessons from debugging agent compliance. Apply them to every
skill that instructs an agent to produce a deliverable.

### Lead with the deliverable, not the sequence

The first thing the agent reads frames everything that follows. If the instruction opens
with a step sequence, the agent treats chat as the output medium. If it opens with
"The output of this task is an HTML file on disk," the agent treats the file as the
deliverable.

**Pattern that works:**
```
## The deliverable

The output of this review is an HTML file written to the user's workspace folder
and registered in the Cowork artifact panel. That file IS the review.

**Task failure:** If grades, findings, or verdicts appear in chat before the artifact
file exists on disk, the task has failed. Build the artifact first. Always.
```

### Name the failure mode explicitly

Don't just say what to do. State what failure looks like:
- "Writing grades to chat in this step is a task failure."
- "If grades appear in chat before the artifact exists, the task has failed."

Agents respond to failure framing more reliably than to positive instructions alone.

### Single grading pass — the data object is the source of truth

When an agent grades in chat prose (Step 2) and then builds a data object for the
template (Step 3), it grades twice. The two passes are not guaranteed to match — the
model is non-deterministic. The result: chat says Needs work, artifact says Pass.

**Fix:** grade exactly once, directly into the data object. The chat summary reads
from that data object — it does not re-evaluate.

```
## Step 2 — Grade (silent — no chat output)

Writing grades, findings, or verdicts to chat in this step is a task failure.
Grade exactly once — into SPOTTER_DATA. SPOTTER_DATA is the single source of truth.
Step 4 reads grades from SPOTTER_DATA. It does not re-grade independently.
```

```
## Step 4 — Confirm

Read grades from SPOTTER_DATA. Do not re-evaluate any area. The grades in this
summary must exactly match the judges arrays in SPOTTER_DATA — if they differ,
the review is wrong.
```

### Step label language matters

The label on each step primes what the agent produces:
- "Step 4 — CHAT" → agent writes review to chat
- "Step 4 — CONFIRM" → agent confirms an artifact that already exists

Change "CHAT" to "CONFIRM" and the agent behavior shifts. Small wording, large effect.

### "Call it exactly once" beats "retry once then STOP"

"If it fails, retry once then STOP" invites the agent to call the tool twice
preemptively. Replace with: "Call it exactly once. Do not call it again for any
reason — not to verify, not to retry. If it fails, stop and report the error."

### End with "Read all instructions before starting"

Agents sometimes begin executing before finishing the instruction text. Adding
"Read all instructions above before starting. Then execute steps 1 → 2 → 3 → 4."
at the very end reduces mid-instruction pivots.

### Workspace path validation — ban the wrong paths explicitly

"Find the user's selected workspace folder" is too vague. Agents grab outputs
directories, session temp paths, and Application Support folders. Be explicit:

```
Validate before continuing — if the workspace root contains any of these strings,
you have the WRONG path:
  "Application Support"  "sessions"  "outputs"  "uploads"  "local-agent"  "tmp"

A correct workspace root looks like: /Users/mike/Projects/loadout
If you cannot determine a valid workspace root, stop and ask the user to confirm
their workspace folder — suggest they select their project folder or create a
dedicated folder (e.g. ~/Documents/Spotter Reports).
```

---

## Cowork large-response persistence — critical PATH B behavior

When a tool returns a large response (observed at ~67KB for `spotter_get_template`),
Cowork automatically persists the response to a temp file rather than keeping it in
context as a string. The agent receives a file path reference, not the HTML content.

**Symptom:** agent says "Template returned. Now reading the persisted output to write
to disk." — then calls Read on a temp path, then rationalizes bash to "decode the JSON."

**The truth:** the content is plain HTML. No JSON decoding. No bash. Read it, Write it.

**Correct instruction for PATH B template handling:**
```
B-2. Get the HTML string from B-1. Two cases:
     • Response in context: the HTML string is directly available — use it as-is.
     • Response persisted to file: Cowork may save large responses to disk and
       return a file path. In this case, call Read on that path to retrieve the
       HTML string. The content is plain HTML — no JSON decoding, no bash.

B-3. Call Write — file_path: [workspace-root]/[slug].html
     content: the HTML string from B-2, unmodified.
     Bash is never needed for this step.
```

**Status:** fixed in Spotter v0.7.16. The Warmup has the same issue — fix pending
(apply the identical pattern to the warmup_run PATH B instructions in index.ts and
mirror in tests/instructions.mjs).

---

## Path A / Path B — what agents do on each run

### Warmup

- **Path A** (engine version in artifact matches `WARMUP_ENGINE_VERSION`): agent Greps
  for `<script id="warmup-data">`, reads the block, Edits just the WARMUP_DATA, calls
  `update_artifact`. Fast and cheap — no template download.
- **Path B** (first run or version mismatch): agent calls `warmup_get_template`, handles
  the response (may be persisted to file — see Cowork section above), Writes to
  workspace, calls `create_artifact` or `update_artifact`.

Bumping `WARMUP_ENGINE_VERSION` forces everyone to Path B on their next run.

### Spotter

- **Path A** (line 2 of workspace file matches current engine marker): agent Greps for
  `<script id="spotter-data">`, Edits the data block, calls `update_artifact`.
- **Path B** (new file or engine mismatch): agent calls `spotter_get_skill` →
  `spotter_get_template` (exactly once) → Read if persisted → Write → `create_artifact`.

**Expected PATH B tool sequence:**
`list_artifacts → spotter_get_skill → spotter_get_template → Write → create_artifact`

Any deviation is a compliance failure the test harness will catch.

---

## Testing harness

The test harness lives in `tests/` and verifies agent instruction compliance against
the real Anthropic API. All MCP and file tools are mocked — no deployed server needed.

### Structure

```
tests/
├── harness.mjs                    ← API loop, TestRun, assertions, saveRunReport()
├── mocks.mjs                      ← mock tool responses and scenario builders
├── instructions.mjs               ← instruction templates (sync manually with index.ts)
├── run-all.mjs                    ← runs all suites
├── spotter-review.test.mjs        ← PATH A + PATH B + mismatch (15 tests)
├── spotter-build.test.mjs         ← build mode flow (5 tests)
├── warmup.test.mjs                ← PATH A + PATH B + stale engine (14 tests)
├── fixtures/
│   ├── spotter-build-commenting.md          ← feature + 9-area PM answers
│   └── spotter-review-comments-on-dashboards.md  ← full epic text
├── run-build.mjs                  ← fixture runner: direct-mode build → draft output
├── run-review.mjs                 ← fixture runner: PATH B review → report output
└── test-output/                   ← run reports (gitignored)
```

### Running tests

```bash
cd tests
npm install                          # first time only
export ANTHROPIC_API_KEY=sk-ant-...

npm test                             # all suites
npm run test:spotter-review
npm run test:spotter-build
npm run test:warmup

npm run review:commenting            # smoke test — full PATH B run with fixture epic
npm run build:commenting             # smoke test — full build mode run with fixture answers
```

### Environment options

```bash
LOADOUT_TEST_MODEL=claude-sonnet-4-6 npm test    # default: claude-haiku-4-5-20251001
LOADOUT_TEST_MAX_TURNS=30 npm test               # default: 20
LOADOUT_TOKEN_BUDGET=120000 npm test             # default: 80000
```

### Safeguards — how the harness prevents token waste

Three layers abort a run early:

1. **Forbidden tool** — any call to `bash`, `mcp__workspace__bash`, `WebFetch`,
   `web_fetch`, `curl`, or `wget` aborts immediately.
2. **Duplicate call detection** — same tool + same args called more than twice aborts.
   Write and Edit counts accumulate (they do not reset the tracker) — so a looping
   Write call aborts at the third attempt.
3. **Token budget** — approximate spend exceeding 80K tokens aborts the run.

### Critical sync requirement

When you update instruction text in `index.ts`, you must:
1. Apply the identical wording change to the matching function in `instructions.mjs`
2. Bump the version constant at the top of `instructions.mjs` to match `constants.ts`

There is no automated sync. If the versions diverge, tests run against stale
instructions and will not catch regressions.

### Mock requirements — two lessons learned the hard way

**MOCK_SPOTTER_HTML must have non-null SPOTTER_DATA.** If the mock returns
`window.SPOTTER_DATA = null`, the agent sees injection failure and calls
`spotter_get_template` a second time, then loops on Write trying to build HTML manually.
The mock must return a minimal valid object:
```javascript
window.SPOTTER_DATA = {"epic":{"name":"Test Epic","epicBody":""},"areas":[]};
```

**Write and Edit must not reset the duplicate call tracker.** Other tools clear the
tracker after each call. Write and Edit must be excluded from that reset — otherwise a
looping Write call (agent chunking HTML) runs unchecked to the turn limit.

### Fixture file format

Build mode (`fixtures/spotter-build-*.md`):
```
---
feature: brief feature description
---

Area 1 — PM answers...
Area 2 — ...
```

Review mode (`fixtures/spotter-review-*.md`):
```
---
name: Epic Name
slug: epic-slug
---

# Epic: Full epic text...
```

Fixture runners skip the conversational Q&A phase and run the agent in direct mode,
saving a report to `test-output/` with tool sequence, template data, and output preview.

---

## Template shell architecture (Spotter)

The Spotter artifact HTML is built from a remote IIFE shell rather than inlining the
full renderer into the tool response:

1. `spotter_get_template` injects SPOTTER_DATA into a minimal HTML wrapper
2. The wrapper loads the shell IIFE from `https://mcp.missionbuilt.io/spotter-shell.js`
3. The shell IIFE reads `window.SPOTTER_DATA` and renders the full report UI

This keeps the tool response lean and lets the UI evolve without forcing Path B on
every deploy. The Worker serves the shell via a GET route at `/spotter-shell.js`.

**Always keep both copies in sync.** Canonical edit first, then bundled copy.

---

## Template UI patterns — lessons from Spotter shell development

### Export dropdown

Must close on: clicking outside, pressing Escape, and clicking the trigger a second
time. Use a `mousedown` listener on `document`, check `!el.contains(event.target)`,
remove the listener when closed. A dropdown that only opens is unusable.

### Fullscreen toggle

Bind to the `fullscreenchange` document event. Update the button label inside the
handler — "Fullscreen" when inactive, "Exit fullscreen" when active. Never assume
the button's initial label is still correct after a state change.

### Font style in area findings

`font-style: italic` can creep in from inherited styles on `<em>` or markdown-rendered
content. Apply `font-style: normal` explicitly on the finding text container.

### Known pending UI debt (as of v0.7.17)

Three bugs deferred past initial ship — fix in `spotter-shell.rawjs`:
1. Export dropdown stays open in fullscreen mode
2. Fullscreen button does not change to "Exit fullscreen"
3. Report section text renders slanted/italic

---

## How template injection works (and the $-sequence fix)

The warmup template has one placeholder:
```
window.WARMUP_DATA = null; // ← AGENT: Edit-replace this line
```

The server replaces it:
```typescript
const safe = warmup_data.replace(/<\/script>/gi, '<\\/script>');
const filled = WARMUP_TEMPLATE_HTML.replace(PLACEHOLDER, () => `window.WARMUP_DATA = ${safe};`);
```

Two safety layers:
1. **`</script>` escape** — prevents content from closing the script tag (XSS)
2. **Replacer function** — `() => replacement` bypasses `$`-sequence expansion.
   Content can contain `$'`, `$&`, `` $` `` which corrupt output with a literal string.
   Fixed in v0.3.17. Do not revert.

The Spotter template uses the identical pattern with `SPOTTER_DATA`.

If the placeholder is missing, return a clear error string — surface it, don't suppress.

---

## Edit tool pitfalls — hard lessons from past sessions

**Read before every Edit.** The Edit tool requires the file to have been read in the
current session. If you get "File has not been read yet," call Read first.

**Unicode characters break exact matching.** Font metrics tables contain curly quotes
and em dashes that look like ASCII but aren't. If Edit fails with "String not found,"
break the edit into smaller chunks above and below the Unicode block.

**File state mismatch.** If Edit says "File has been modified since read," Read again
before editing. Read only the specific line range you need — large files are slow.

**Large block edits fail even when correct.** More than ~50 lines at once often fails.
Break into CSS, HTML, and JS edits separately.

---

## Adding a new skill to the Loadout

**Full checklist:**

**1. Create skill content directory:**
```
missionbuilt-mcp/src/skill-content/my-skill/
├── SKILL.md
└── my-template.html  (if artifact needed)
```

**2. Bundle in `index.ts`:**
```typescript
import MY_SKILL_MD from "./skill-content/my-skill/SKILL.md";
import MY_TEMPLATE_HTML from "./skill-content/my-skill/my-template.html";
```

**3. Add section extractor if SKILL.md > 20KB.** Model on `getSkillSection()`.

**4. Register tools in `async init()`:**
```typescript
this.server.tool(
  "myskill_get_skill",
  "Description.",
  { intent: intentField, section: z.enum(["overview", "run", "full"]).optional() },
  async ({ section }) => ({
    content: [{ type: "text" as const, text: getMySkillSection(MY_SKILL_MD, section ?? "full") }],
  })
);
```

`intentField` is defined at the top of `index.ts` — always include it first in every tool.

**5. Add template injection tool (if artifact):**
- Unique PLACEHOLDER in template
- `</script>` escaping
- Replacer function, not literal string
- Injection failure check → clear error string

**6. Write agent instructions following the framing lessons:**
- Lead with the deliverable
- State the failure mode explicitly
- Single data-object pass for any grading/scoring
- Handle Cowork large-response persistence (Read → Write, no bash)
- Ban wrong workspace paths explicitly

**7. Add tests:**
- Instruction template → `instructions.mjs`
- Mock responses → `mocks.mjs` (non-null data in mock template HTML)
- Tool schemas → `harness.mjs` SCHEMAS
- Test file → `my-skill.test.mjs`
- Fixture files → `fixtures/`
- Import and spread `allResults` in `run-all.mjs`

**8. Bump `constants.ts`:** TOOL_COUNT, SERVER_VERSION, new skill version constant.

**9. Deploy and verify** at `https://mcp.missionbuilt.io/health`.

---

## Prompt injection rules (for tool handler content)

| Content | Required handling |
|---|---|
| Multi-line user text (epics, drafts) | Fence in ` ```\n...\n``` ` code block |
| Short string (feature names, source names) | Strip non-ASCII + control chars, add `.max()` Zod bound |
| Nothing user-supplied | No special handling needed |

Always add a `.max()` bound to Zod string params that accept substantial user content.

---

## Using the tech lead review skill

After any significant feature work, run `/tech-lead-review` or say "do a tech lead
review." It runs four phases (Security, Architecture, Token Optimization, Architecture
Diagram) and writes `TECH-LEAD-REVIEW.md` and `ARCH.md` to the project.

Things it specifically checks for this codebase:
- `$`-sequence corruption in `String.prototype.replace` (fixed in v0.3.17 — don't revert)
- Prompt injection: user content in instruction prose must be fenced
- Version constants in sync with actual changes
- Canonical/bundled template copies in sync
- Security headers on HTML responses
- Workspace path validation in agent instructions

---

## Reference

See `references/project-context.md` for:
- Full file map with paths
- Complete design token system (CSS variables)
- Tool inventory (all 20 tools, what each does)
- Security patterns and what not to break
- Known cleanup debt
- Current version state
