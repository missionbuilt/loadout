---
name: missionbuilt-mcp-dev
description: >
  Working context for missionbuilt-mcp development sessions. Load this skill at the start of any
  session involving the Cloudflare Workers MCP server (missionbuilt-mcp), its TypeScript source,
  Wrangler deploys, or the Warmup / Spotter / The Approach skill infrastructure. Covers how Mike
  and Claude divide work, the deploy sequence, artifact patterns, engine-version check patterns,
  and file path rules. Trigger when the user says "continue where we left off," "let's work on the
  MCP server," "here's the context for this session," or starts a session involving any of:
  missionbuilt-mcp, mcp.missionbuilt.io, warmup, spotter, the-approach, wrangler deploy.
---

# missionbuilt-mcp — Dev Session Context

Workspace: `/Users/mike/Projects/loadout/missionbuilt-mcp`

---

## How we divide work

Claude writes all code using **Read / Write / Edit file tools directly** — no bash for file
operations. The bash sandbox runs in a Linux VM where macOS paths are remapped and disk space
is frequently exhausted.

Mike runs all **git and deploy commands** from his own terminal. Claude never attempts `git` or
`npx wrangler deploy` — it writes the commands for Mike to run.

**Standard deploy sequence:**
```
cd /Users/mike/Projects/loadout/missionbuilt-mcp
git add -A && git commit -m "..." && git push && npx wrangler deploy
```

**Verify deploys:** `https://mcp.missionbuilt.io/health` — returns `server_version` confirming new code is live.

---

## Stack

- **Cloudflare Workers** (Durable Objects) + TypeScript + Wrangler
- Text imports bundled at build time via `wrangler.toml` `[[rules]]` globs (`**/*.md`, `**/*.html`)
- Zod for tool param schemas; `intentField` shared param required on every tool
- `constants.ts` is the single source of truth for all version constants and `TOOL_COUNT`

---

## Artifact pattern — Warmup and Spotter

Both skills use **server-side template injection**: the MCP tool (`warmup_get_template` /
`spotter_get_template`) receives a JSON data object, injects it into a bundled HTML template
server-side, and returns complete artifact-ready HTML. The agent writes that HTML to a file in
the user's workspace folder, then registers it with `create_artifact` / `update_artifact` using
the `html_path`. The artifact viewer serves the file from disk — clicking refresh reloads from disk.

---

## Engine version check pattern

The problem: when a user re-runs a review after a template update, the agent may shortcut and
reuse existing artifact HTML rather than calling `*_get_template` again. This produces stale
artifacts.

**The fix (implemented in both Warmup and Spotter):**

1. **Version marker in the template.** Line 2 of every generated HTML file contains:
   `<!-- spotter-engine: vX.Y.Z -->` (or `warmup-engine: vX.Y.Z`). The server replaces the
   marker string with the actual version during injection. Every artifact written to disk carries
   the engine version it was built with.

2. **Server-side injection chain in `*_get_template`:**
   ```typescript
   const withVersion = TEMPLATE_HTML.replace('VERSION_MARKER', `v${VERSION}`);
   const filled = withVersion.replace(PLACEHOLDER, () => `window.DATA = ${safe};`);
   const injected = filled !== withVersion;
   ```
   The replacer function `() => safe` prevents `$`-sequence corruption in `String.replace`.

3. **Step 0 in the primed prompt** — mandatory engine check before grading:
   - Call `list_artifacts`, find existing artifact, read first 3 lines, check version comment
   - If version doesn't match, call `*_get_template` fresh regardless

4. **Hard-stop language:** `ABSOLUTE RULE — NO EXCEPTIONS: If you reach step N without having
   called *_get_template, STOP and call it now.`

**Warmup's two-path system (Spotter skips this):**
- Path A (version match, daily run): patches only the `<script id="warmup-data">` block in the
  existing file — no re-fetch of the 131 KB engine.
- Path B (first run or version mismatch): calls `warmup_get_template`, writes a fresh file.
- The Spotter skips Path A because `SPOTTER_DATA` always changes on every review.

---

## File path rules

| Purpose | Path |
|---|---|
| Workspace (persistent, user-visible) | `/Users/mike/Projects/loadout/` |
| Temp outputs (session-scoped, not for artifacts) | session outputs folder |
| Artifact HTML files | **Must** live in the workspace folder — temp outputs are cleared between sessions |

---

## XSS / injection protection in template tools

When injecting JSON into HTML templates:
```typescript
const safe = JSON.stringify(data).split("</script>").join("<\\/script>");
const html = TEMPLATE_HTML.replace("__DATA_PLACEHOLDER__", () => safe);
```
Always use an arrow function replacer (not a string literal) to avoid `$`-sequence corruption.

---

## TOOL_COUNT rule

`constants.ts` exports `TOOL_COUNT`. **Update it every time a tool is added or removed.** It
is surfaced in the `/health` endpoint and used to verify deploys. Current value should match
the actual number of registered tools in `index.ts`.
