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
and architecture. This SKILL.md covers the collaboration model and workflow — the things
you need to know before touching any file.

---

## Collaboration model — non-negotiable

**Mike runs all terminal commands. Claude writes all code.**

- Write code changes with the file tools (Read, Edit, Write).
- When a shell command is needed (git, wrangler, npm, grep), write it as a code block
  and wait for Mike to run it and paste the output back. Never assume it succeeded.
- Never use bash to fetch URLs — use WebFetch or WebSearch tools instead.
- When in doubt about the current state of a file, Read it rather than assuming.

This is the model because bash was historically unavailable in some sessions, and
because it keeps Mike in control of deploys, git history, and destructive operations.

---

## The one rule that causes the most problems if you forget it

**The warmup template lives in two places. Always edit canonical first, then sync the bundled copy.**

| Copy | Path |
|------|------|
| Canonical (agents read/write this) | `/Users/mike/Projects/loadout/warmup/warmup-template.html` |
| Bundled (Worker imports this at build time) | `/Users/mike/Projects/loadout/missionbuilt-mcp/src/skill-content/warmup/warmup-template.html` |

Every CSS, HTML, and JS change goes into the canonical copy first. Then apply the
identical change to the bundled copy. If they diverge, agents silently work against
a stale template and the Worker serves the wrong design.

After any template edit, verify with Grep:
```
grep -c "YOUR_NEW_STRING" warmup/warmup-template.html
grep -c "YOUR_NEW_STRING" missionbuilt-mcp/src/skill-content/warmup/warmup-template.html
```
Both counts must match.

---

## Version bump rules

All version constants live in one file: `missionbuilt-mcp/src/constants.ts`

```typescript
export const SERVER_VERSION        = "1.0.1";   // Worker deploy version (semver)
export const WARMUP_VERSION        = "0.3.17";  // bump when SKILL.md or template changes
export const WARMUP_ENGINE_VERSION = "v0.3.17"; // bump when warmup-template.html changes
export const SPOTTER_VERSION       = "0.6.0";   // bump when Spotter SKILL.md/areas change
export const TOOL_COUNT            = 17;        // update when adding or removing tools
```

**What to bump for what:**

| What changed | Bump |
|---|---|
| `warmup-template.html` (any change) | `WARMUP_VERSION` + `WARMUP_ENGINE_VERSION` |
| Warmup `SKILL.md` only | `WARMUP_VERSION` |
| Spotter `SKILL.md` or area changes | `SPOTTER_VERSION` |
| New tool added or removed | `TOOL_COUNT` |
| Worker infrastructure change | `SERVER_VERSION` |

**Why `WARMUP_ENGINE_VERSION` is critical:** agents use it to decide whether to reload
the full template (Path B) or just swap out the WARMUP_DATA block (Path A). If you
change the template but don't bump the engine version, every agent with an existing
artifact takes Path A — targeted data update only — and never picks up your new HTML.
The old toolbar/layout stays frozen in their artifact forever.

---

## Commit and deploy workflow

```bash
git add -A
git commit -m "warmup v0.3.17 — short description of what changed"
npx wrangler deploy
```

**Verify after deploy:** `https://mcp.missionbuilt.io/health` — `server_version` must match
`SERVER_VERSION` in constants.ts.

**The `$` trap in commit messages:** the shell interprets `$'`, `$&`, and `` $` `` as
special sequences inside double-quoted strings. Either use single quotes for commit
messages, escape every `$` as `\$`, or just avoid `$` in the message body. We learned
this the hard way — a commit message about the `$`-sequence bug itself became garbled
because of the same bug.

---

## Using the tech lead review skill

After any significant feature work — new tool, template change, security-adjacent edit —
run `/tech-lead-review` or say "do a tech lead review." The skill reads all source files,
runs four phases (Security, Architecture, Token Optimization, Architecture Diagram), fixes
any P0 findings, and writes `TECH-LEAD-REVIEW.md` and `ARCH.md` to the project.

Things it specifically checks for this codebase:
- `$`-sequence corruption in `String.prototype.replace` (already fixed in v0.3.17,
  don't revert — always use a replacer function `() => replacement`)
- Prompt injection: user-supplied content embedded in instruction prose must be fenced
  in code blocks or sanitized
- Version constants in sync with actual changes
- Canonical/bundled template copies in sync
- Security headers on HTML responses

---

## Edit tool pitfalls — hard lessons from past sessions

**Unicode characters break exact matching.** Font metrics tables in the warmup template
contain curly quotes and em dashes (e.g., `'`:278, `"`:355) that look like ASCII but
aren't. If an Edit fails with "String to replace not found," you've probably hit a block
containing these characters. Workarounds:
- Break big edits into smaller targeted ones above and below the Unicode block
- Block-comment dead code instead of trying to delete it
- Never include curly quotes or em dashes in `old_string`

**File state mismatch.** If the Edit tool says "File has been modified since read," you
must Read the file again before editing. Always read the specific line range you need —
large files are slow to read in full.

**Large block edits fail even when they look right.** If editing more than ~50 lines at
once fails, break it into 3–5 smaller edits: CSS section, HTML section, JS section —
separately.

**Dead code with Unicode: use block comments.** If you need to disable a large JS
function that contains font metrics tables, wrap it in `/* ... */` rather than
deleting it. Note it as cleanup debt for when bash is available.

---

## How template injection works (and the $-sequence fix)

The warmup template has one placeholder:
```
window.WARMUP_DATA = null; // ← AGENT: Edit-replace this line with your WARMUP_DATA JSON object (see SKILL.md Path B)
```

The server replaces it in `warmup_get_template`:
```typescript
const safe = warmup_data.replace(/<\/script>/gi, '<\\/script>');
const filled = WARMUP_TEMPLATE_HTML.replace(PLACEHOLDER, () => `window.WARMUP_DATA = ${safe};`);
```

Two safety layers:
1. **`</script>` escape** — prevents article content from closing the script tag (XSS)
2. **Replacer function** — `() => replacement` bypasses `$`-sequence expansion in
   `String.prototype.replace`. Article content (prices, tickers, shell strings) can
   contain `$'`, `$&`, `` $` `` which would corrupt the output if a literal string
   were used. This was fixed in v0.3.17. Do not change it back to a literal string.

The spotter template uses the identical pattern with `SPOTTER_DATA`.

If the placeholder is missing from the template, the tool returns a clear error string.
This is intentional — surface it, don't suppress it.

---

## Adding a new skill to the Loadout

A "skill" in this project means a set of MCP tools registered in `index.ts`, bundled
content in `skill-content/`, and an HTML template. Here's the full checklist:

**1. Create the skill content directory:**
```
missionbuilt-mcp/src/skill-content/my-skill/
├── SKILL.md          ← the framework / instructions for the LLM
└── my-template.html  ← the artifact template (if needed)
```

**2. Bundle the content in `index.ts`:**
```typescript
import MY_SKILL_MD from "./skill-content/my-skill/SKILL.md";
import MY_TEMPLATE_HTML from "./skill-content/my-skill/my-template.html";
```

**3. Add a section extractor if SKILL.md is large (>20KB):**
Model it on `getSkillSection()` — a boundary map that slices named sections by heading.
Expose it via a `section` Zod enum param on the `get_skill` tool. Never return the full
document unconditionally if it's large.

**4. Register tools inside `async init()` in `MissionBuiltMCP`:**
```typescript
this.server.tool(
  "myskill_get_skill",
  "Description of what this tool returns and when to call it.",
  {
    intent: intentField,   // always first
    section: z.enum(["overview", "run", "full"]).optional()
              .describe("Which section to load. Defaults to 'full'."),
  },
  async ({ section }) => ({
    content: [{ type: "text" as const, text: getMySkillSection(MY_SKILL_MD, section ?? "full") }],
  })
);
```

`intentField` is already defined at the top of `index.ts` — always include it as the
first parameter in every tool. It powers the Cowork permission dialog.

**5. Add a template injection tool (if there's an artifact):**
Follow the `warmup_get_template` / `spotter_get_template` pattern exactly:
- Put a unique PLACEHOLDER comment in the template
- Use `</script>` escaping
- Use a replacer function (not a literal string)
- Check `filled !== TEMPLATE` to detect injection failure and return an error string

**6. Bump constants.ts:**
- Increment `TOOL_COUNT` by the number of tools added
- Set `SERVER_VERSION` to the next semver patch

**7. Register any MCP resources** (optional, for large reference content):
```typescript
this.server.resource("my-skill", "loadout://my-skill/skill", { ... }, async () => ({ ... }));
```

**8. Deploy and verify** at `https://mcp.missionbuilt.io/health`.

---

## Prompt injection rules (for tool handler content)

When user-supplied content is embedded in instruction text returned to the agent:

| Content | Required handling |
|---|---|
| Multi-line user text (epics, drafts, config files) | Fence in ` ```\n...\n``` ` code block |
| Short string (source names, feature descriptions) | Strip non-ASCII + control chars, add `.max()` Zod bound |
| Nothing user-supplied | No special handling needed |

Always add a `.max()` bound to Zod string params that accept substantial user content.

---

## Path A / Path B — what agents actually do on a daily warmup run

Understanding this is important when making template changes:

- **Path A** (engine version in artifact matches `WARMUP_ENGINE_VERSION`): agent does a
  targeted edit — Greps for `<script id="warmup-data">`, reads ~20 lines, Edits just
  the WARMUP_DATA block, calls `update_artifact`. Fast, cheap, no template download.
- **Path B** (first run or engine version mismatch): agent calls `warmup_get_template`,
  server returns filled 131KB HTML, agent Writes to disk, calls `create_artifact` or
  `update_artifact`. One heavier run, then back to Path A.

Bumping `WARMUP_ENGINE_VERSION` forces everyone to Path B on their next run, ensuring
they pick up the new template. After that one run, they're back on Path A.

---

## Reference

See `references/project-context.md` for:
- Full file map with paths
- Complete design token system (CSS variables)
- Tool inventory (all 17 tools, what each does)
- Security patterns and what not to break
- Known cleanup debt
- Current version state
