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
  DO NOT invoke for end-user requests to RUN the skills — "spot my epic," "run my
  warmup," "run the approach for [company]" are handled by the MCP tools directly,
  not by this development skill.
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

## Shell files — one canonical file per skill (NOT two)

**Each skill's renderer is a single `.rawjs` file. Edit it directly. There are no
separate template HTML files for these skills.**

| Skill | Canonical shell | Served by |
|-------|----------------|-----------|
| The Warmup | `missionbuilt-mcp/src/warmup-shell.rawjs` | `warmup_get_template` — assembles chunked HTML |
| The Spotter | `missionbuilt-mcp/src/spotter-shell.rawjs` | `spotter_get_template` — returns full HTML in one call |

`warmup_get_template` injects the `<!-- warmup-engine: vX.X.X -->` marker and wraps
`WARMUP_SHELL_JS` in a complete HTML document, chunked into 900-line segments.

`spotter_get_template` inlines `SPOTTER_SHELL_JS` into a complete HTML document and
returns it in a single response (~200KB). Cowork may auto-persist large responses to
disk — agents are instructed to handle both the inline-HTML and file-path response cases.

**There is no `warmup-template.html` or `spotter-template.html`.** Earlier versions of
this skill referred to files that no longer exist. The file
`skill-content/spotter/spotter-template.html` is an orphaned older copy — its import was
removed from `index.ts` in v1.1.2. Ignore any reference to it.

After any edit to a shell file, always verify your change landed:
```bash
grep -n "YOUR_NEW_STRING" missionbuilt-mcp/src/warmup-shell.rawjs
# or for spotter:
grep -n "YOUR_NEW_STRING" missionbuilt-mcp/src/spotter-shell.rawjs
```

---

## Version bump rules

All version constants live in one file: `missionbuilt-mcp/src/constants.ts`

```typescript
export const SERVER_VERSION        = "1.1.2";   // Worker deploy version (semver)
export const WARMUP_VERSION        = "0.8.2";   // bump when SKILL.md or template changes
export const WARMUP_ENGINE_VERSION = "v0.8.2";  // bump when warmup-shell.rawjs changes
export const SPOTTER_VERSION       = "0.7.19";  // bump when Spotter SKILL.md/shell changes
export const THE_APPROACH_VERSION  = "0.1.4";   // bump when Approach SKILL.md/template changes
export const TOOL_COUNT            = 23;        // update when adding or removing tools
```

**What to bump for what:**

| What changed | Bump |
|---|---|
| `warmup-shell.rawjs` (any change) | `WARMUP_VERSION` + `WARMUP_ENGINE_VERSION` |
| Warmup `SKILL.md` only | `WARMUP_VERSION` |
| `spotter-shell.rawjs` (any change) | `SPOTTER_VERSION` |
| Spotter `SKILL.md` or area changes | `SPOTTER_VERSION` |
| New tool added or removed | `TOOL_COUNT` |
| `index.ts` infrastructure change | `SERVER_VERSION` |
| Worker infrastructure change | `SERVER_VERSION` |

**Why `WARMUP_ENGINE_VERSION` is critical:** agents use it to decide whether to reload
the full template (Path B) or just swap out the WARMUP_DATA block (Path A). If you
change the template but don't bump the engine version, every agent with an existing
artifact takes Path A — targeted data update only — and never picks up your new HTML.
The old toolbar/layout stays frozen in their artifact forever.

---

## Commit and deploy workflow

```bash
cd /Users/mike/Projects/loadout/missionbuilt-mcp
git add src/warmup-shell.rawjs src/constants.ts   # or git add -A for everything
git commit -m 'warmup v0.8.2 — short description of what changed'
npm run deploy
```

**Verify after deploy:** `https://mcp.missionbuilt.io/health` — `server_version` must match
`SERVER_VERSION` in constants.ts. The health response also includes `warmupEngineVersion`
which must match `WARMUP_ENGINE_VERSION`.

**The `$` trap in commit messages:** the shell interprets `$'`, `$&`, and backtick-$ as
special sequences inside double-quoted strings. Use single quotes for commit messages
or avoid `$` in the message body. We learned this the hard way — a commit message about
the `$`-sequence bug itself became garbled because of the same bug.

---

## Using the tech lead review skill

After any significant feature work — new tool, template change, security-adjacent edit —
run `/tech-lead-review` or say "do a tech lead review." The skill reads all source files,
runs four phases (Security, Architecture, Token Optimization, Architecture Diagram), fixes
any P0 findings, and writes `TECH-LEAD-REVIEW.md` and `ARCH.md` to the Downloads folder.

Things it specifically checks for this codebase:
- **Indirect prompt injection -> XSS:** agent-sourced content from web articles inserted
  into innerHTML without escaping (see "Warmup security patterns" below — fully fixed in v0.8.2)
- `$`-sequence corruption in `String.prototype.replace` (fixed in v0.3.17 — always use
  a replacer function `() => replacement`, never revert to a literal string)
- Prompt injection: user-supplied content embedded in instruction prose must be fenced
  in code blocks or sanitized
- Version constants in sync with actual changes
- `warmup-shell.rawjs` as the single canonical template (no two-copy sync needed)
- Security headers on HTML responses
- Auto-refresh fetching full payload just to compare a timestamp (L3 — see backlog)

---

## Warmup security patterns — established in v0.8.2

The warmup renders agent-sourced content (from live web articles) into innerHTML. This
is a real XSS attack vector: an adversarial article can contain a payload in its title
or body that survives Claude's summarization via indirect prompt injection and executes
in the artifact iframe.

**The two helpers — always present near the top of the renderer block:**
```javascript
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function safeUrl(url) {
  var u = String(url == null ? '' : url).trim();
  return /^javascript:/i.test(u) ? '#' : u;
}
```

**Fields that MUST be escaped — every one, no exceptions:**

| Field | Helper | Location |
|-------|---------|----------|
| `item.src` | `escapeHtml` | item renderer `.src` span |
| `item.hl` | `escapeHtml` | item headline `<h3>` |
| `item.body` | `escapeHtml` | item summary `<p>` |
| `item.deck` | `escapeHtml` | lead item deck paragraph |
| `item.url` | `safeUrl` | all `href="..."` attributes |
| tag `t.text` / `t.cls` | `escapeHtml` | tag spans |
| `sec.label` | `escapeHtml` | both nav link AND section `<h2>` |
| `sec.sub` | `escapeHtml` | section sub-headline span |
| `sec.note` | `escapeHtml` | section note paragraph |
| `s.nm` / `s.dom` | `escapeHtml` | source rows in sources panel |
| `d.domain` | `escapeHtml` | safety panel domain rows |
| `sf.scannedAt` | `escapeHtml` | safety panel meta line |
| WARMUP_CONFIG fields | `escapeHtml` | profile card `k`/`v` in fields array |
| `source` in Deep Dive header | `escapeHtml` | `srcHeader.innerHTML` |

**Important subtlety — Deep Dive source round-trip:** `source` is read back via
`srcEl.textContent.trim()` from the already-rendered `.src` span. Because the span was
populated with `escapeHtml(item.src)`, textContent decodes HTML entities back to raw
characters. Then `srcHeader.innerHTML = ...${source}...` would re-inject unescaped.
Fix: apply `escapeHtml(source || 'Source')` at the `srcHeader.innerHTML` assignment.

**What is safe without escaping:**
- `renderMd` output — it escapes the full input before applying markdown substitutions
- Deep Dive error messages — already escaped before going into `resultDiv.innerHTML`
- Static string literals baked into the template

---

## Export HTML — standalone offline file

When the user exports ("Save as HTML"), `exportHTML()` captures
`document.documentElement.outerHTML`. The problem: `window.WARMUP_DATA` is a JS variable,
not in the DOM — the exported file opens blank.

**The fix (established in v0.8.2):** inject WARMUP_DATA into the script block at export time:
```javascript
function exportHTML() {
  closeExport(); // always close the dropdown first
  // ... filename logic ...
  let html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
  if (window.WARMUP_DATA) {
    try {
      const dataStr = JSON.stringify(window.WARMUP_DATA).replace(/<\/script>/gi, '<\\/script>');
      html = html.replace(
        /<script id="warmup-tools">[\s\S]*?<\/script>/,
        () => '<script id="warmup-tools">\nwindow.WARMUP_TOOLS = { dataTool: \'\' };\nwindow.WARMUP_DATA = ' + dataStr + ';\n<' + '/script>'
      );
    } catch (exportErr) { console.warn('[Warmup:Export] data injection failed', exportErr); }
  }
  // ... blob/download logic ...
}
```

**Two `</script>` traps in this function — both must be correct:**
1. **Data content:** `dataStr` uses `.replace(/<\/script>/gi, '<\\/script>')` to escape
   any `</script>` that might appear inside article content.
2. **The replacement string itself:** the JS string literal `'<' + '/script>'` splits the
   closing tag so the HTML parser does not see `</script>` and close the `<script>` block
   early. If you write `'</script>'` as a literal inside the replacer, the HTML parser
   closes the outer script tag and all remaining JS renders as visible page text —
   you will see "Warmup render error" with raw code on screen.

**The replacer function:** always `() => replacement`, never a literal string — same
`$`-sequence reason as everywhere else.

**Font guard for exported files:** the font loader polls for `window.cowork` (the Cowork
bridge), which does not exist in a standalone exported file. Add this guard at the top of
the font loader, right after the `if (!toolName)` check:
```javascript
if (document.getElementById('warmup-fonts')) return; // fonts already in DOM (exported file)
```
This detects that fonts were already captured in the outerHTML snapshot and skips the
dead Cowork poll entirely.

---

## Clipboard API in sandboxed iframes

The Cowork artifact iframe runs under a permissions policy that frequently blocks
`navigator.clipboard`. **Never assume clipboard success** — always use the
`.then(onSuccess).catch(onFailed)` pattern:

```javascript
function onCopied() { label.textContent = 'Copied'; /* ... */ }
function onFailed() { label.textContent = 'Paste into chat'; /* show prompt inline */ }
try {
  navigator.clipboard.writeText(prompt).then(onCopied).catch(onFailed);
} catch(e) { onFailed(); }
```

For smaller chips/buttons where there is no room to show the prompt inline, show
`'Copy blocked'` on failure so the UI never claims success it did not achieve.

The old pattern was `try { navigator.clipboard.writeText(prompt).catch(() => {}); } catch(e) {}`
followed by immediately setting the label to a success state. This was a lie —
fixed in v0.8.2.

---

## Variable naming — FONT_CACHE_KEY vs CACHE_KEY

The warmup shell has two separate localStorage keys managed in two different scopes:
- `CACHE_KEY` (outer scope) — keyed `'warmup-data-cache-v1'`, for WARMUP_DATA
- `FONT_CACHE_KEY` (font loader scope) — keyed `'warmup-fonts-v2'`, for font CSS

In earlier versions both were declared as `var CACHE_KEY`, which was confusing and
a latent bug. As of v0.8.2 the font cache key is `FONT_CACHE_KEY` everywhere.
If you add a third cache, give it a distinct name — do not reuse `CACHE_KEY`.

---

## Font loading — MCP-served base64 CSS

**Problem:** Cowork's Content Security Policy blocks Google Fonts CDN and jsDelivr entirely.
Any `<link rel="stylesheet" href="https://fonts.googleapis.com/...">` silently fails.
The artifact renders in browser fallback fonts (system sans-serif) and looks wrong.

**Solution:** Fonts are served by the `warmup_get_fonts` MCP tool as a base64-encoded
`@font-face` CSS blob. The artifact's font loader IIFE calls that tool at open time via
the Cowork bridge, then injects the CSS into the `<head>`. After the first load, the CSS
is cached in `localStorage` under the key `warmup-fonts-v2`.

**Both skills share the same cache key and the same element ID.** This means:
- If the user opens a Warmup artifact first, the Spotter gets fonts for free from cache
- Same in reverse — one MCP call covers both skills in the same browser session
- The `<style>` element injected is `id="warmup-fonts"` in both skills

### The font loader pattern

Every shell file (warmup-shell.rawjs, spotter-shell.rawjs) must include this IIFE
immediately after `document.head.appendChild(_style)`:

```javascript
(function loadFonts() {
  var FONT_CACHE_KEY = 'warmup-fonts-v2'; // shared with both skills — do not rename
  // Read fontToolName from the data object (WARMUP_DATA or SPOTTER_DATA)
  var cfg      = (window.WARMUP_DATA && window.WARMUP_DATA.config) || {};
  var toolName = cfg.fontToolName || '';

  function showFontError(stage, detail) { /* visible error div in corner */ }

  // Guard 1: fontToolName must be set by the agent. Without it there is nothing to call.
  if (!toolName) { showFontError('no fontToolName in config', '...'); return; }

  // Guard 2: fonts already present in DOM — exported/standalone file or other skill loaded first.
  if (document.getElementById('warmup-fonts')) return;

  function injectCSS(css) {
    if (document.getElementById('warmup-fonts')) return; // race guard
    var s = document.createElement('style');
    s.id = 'warmup-fonts';         // shared ID — intentional
    s.textContent = css;
    document.head.insertBefore(s, document.head.firstChild); // fonts load before other styles
  }

  // Try cache — only trust entries that look like real @font-face CSS
  try {
    var cached = localStorage.getItem(FONT_CACHE_KEY);
    if (cached && cached.length > 100 && cached.indexOf('@font-face') > -1) { injectCSS(cached); return; }
    if (cached) { try { localStorage.removeItem(FONT_CACHE_KEY); } catch(e){} } // stale — evict
  } catch(e) { /* storage unavailable — continue to MCP fetch */ }

  // Poll for window.cowork (it may not exist yet at script execution time)
  var _fontAttempts = 0;
  function tryFetchFonts() {
    if (!window.cowork || typeof window.cowork.callMcpTool !== 'function') {
      if (++_fontAttempts < 25) { setTimeout(tryFetchFonts, 200); return; }
      showFontError('window.cowork never appeared', 'sandbox bridge unavailable'); return;
    }
    window.cowork.callMcpTool(toolName, { intent: 'Loading fonts' })
      .then(function(raw) {
        // 4-shape response normalizer — Cowork wraps MCP responses inconsistently:
        var css = null;
        function tryParseCss(val) {
          if (!val) return null;
          if (typeof val === 'string') {
            if (val.trim().charAt(0) === '{') {
              try { var p = JSON.parse(val); return (p && p.css) ? p.css : val; } catch(e) {}
            }
            return val;
          }
          if (val && val.css) return val.css;
          return null;
        }
        if (typeof raw === 'string')                               { css = tryParseCss(raw); }
        else if (raw && raw.css)                                   { css = raw.css; }
        else if (Array.isArray(raw) && raw[0] && raw[0].text)     { css = tryParseCss(raw[0].text); }
        else if (raw && raw.content && Array.isArray(raw.content)) { css = tryParseCss(raw.content[0]?.text); }

        if (!css || css.length < 100 || css.indexOf('@font-face') === -1) {
          showFontError('unexpected font response', JSON.stringify(raw).slice(0, 200)); return;
        }
        injectCSS(css);
        try { localStorage.setItem(FONT_CACHE_KEY, css); } catch(e) { /* quota full — ok */ }
      })
      .catch(function(err) { showFontError('MCP call rejected', String(err && err.message || err)); });
  }
  tryFetchFonts();
})();
```

### What the agent must do

**Every review run (spotter_review) and warmup run (warmup_run):** the agent must include
`fontToolName` in the data config object, and must pass `warmup_get_fonts` in `mcp_tools`
when calling `create_artifact` or `update_artifact`.

For the Warmup (`WARMUP_DATA.config`):
```json
"config": {
  "fontToolName": "mcp__3096d634-4b43-4ea7-9121-ad04763776a6__warmup_get_fonts",
  ...other config fields...
}
```

For the Spotter (`SPOTTER_DATA.config`):
```json
"config": {
  "fontToolName": "mcp__3096d634-4b43-4ea7-9121-ad04763776a6__warmup_get_fonts"
}
```

`create_artifact` / `update_artifact` call:
```
mcp_tools: ["mcp__<uuid>__warmup_get_data", "mcp__<uuid>__warmup_get_fonts"]
                                              ^--- required or Cowork blocks the font call
```

If `warmup_get_fonts` is missing from `mcp_tools`, the `callMcpTool(fontToolName, ...)` call
is blocked by Cowork and the artifact renders in fallback fonts. The error div appears but
the report is otherwise functional — still annoying to diagnose.

### The `fontToolName` UUID problem

The MCP tool name prefix (`mcp__<uuid>__`) changes per user session. The agent cannot
hard-code it — it must use the actual tool name from its loaded tool list:

- For warmup: inspect the loaded `warmup_get_fonts` tool name in context
- For spotter: same — it is always `warmup_get_fonts`, just a different UUID prefix

The `spotter_review` instructions tell the agent: `config: { fontToolName: the full
prefixed name of warmup_get_fonts, e.g. "mcp__3096d634-....__warmup_get_fonts" }`.

### The export guard — critical for standalone files

When the user exports the artifact as an HTML file, `outerHTML` captures the entire DOM
including the injected `<style id="warmup-fonts">`. In the standalone exported file,
`window.cowork` does not exist, and the Cowork poll loop would spin 25 times and then
show a noisy error div.

The guard at the top of the font loader (after the `!toolName` check) prevents this:
```javascript
if (document.getElementById('warmup-fonts')) return;
```
Because `outerHTML` already captured the `<style id="warmup-fonts">` tag, the element
exists in the DOM on load — the guard fires immediately and the poll never starts.

---

## How template injection works (and the $-sequence fix)

The warmup shell (`warmup-shell.rawjs`) has one placeholder that the server fills at
request time. The server assembles the full HTML in `warmup_get_template` in `index.ts`:

```typescript
const safe = warmup_data.replace(/<\/script>/gi, '<\\/script>');
const filled = WARMUP_SHELL_JS.replace(PLACEHOLDER, () => `window.WARMUP_DATA = ${safe};`);
```

Two safety layers:
1. **`</script>` escape** — prevents article content from closing the script tag (XSS)
2. **Replacer function** — `() => replacement` bypasses `$`-sequence expansion in
   `String.prototype.replace`. Article content (prices, tickers, shell strings) can
   contain `$'`, `$&`, and backtick-$ which would corrupt the output if a literal string
   were used. This was fixed in v0.3.17. Do not change it back to a literal string.

The spotter template uses the identical pattern with `SPOTTER_DATA`.

If the placeholder is missing from the template, the tool returns a clear error string.
This is intentional — surface it, do not suppress it.

---

## Edit tool pitfalls — hard lessons from past sessions

**Unicode characters break exact matching.** Font metrics tables in the warmup template
contain curly quotes and em dashes (e.g., `'`:278, `"`:355) that look like ASCII but
are not. If an Edit fails with "String to replace not found," you have probably hit a block
containing these characters. Workarounds:
- Break big edits into smaller targeted ones above and below the Unicode block
- Block-comment dead code instead of trying to delete it
- Never include curly quotes or em dashes in `old_string`

**File state mismatch.** If the Edit tool says "File has been modified since read," you
must Read the file again before editing. Always read the specific line range you need —
large files are slow to read in full.

**Large block edits fail even when they look right.** If editing more than ~50 lines at
once fails, break it into 3-5 smaller edits: CSS section, HTML section, JS section —
separately.

**Dead code with Unicode: use block comments.** If you need to disable a large JS
function that contains font metrics tables, wrap it in `/* ... */` rather than
deleting it. Note it as cleanup debt for when bash is available.

---

## Path A / Path B — what agents actually do on a daily warmup run

Understanding this is important when making template changes:

- **Path A** (engine version in artifact matches `WARMUP_ENGINE_VERSION`): agent does a
  targeted edit — Greps for `<script id="warmup-data">`, reads ~20 lines, Edits just
  the WARMUP_DATA block, calls `update_artifact`. Fast, cheap, no template download.
- **Path B** (first run or engine version mismatch): agent calls `warmup_get_template`,
  server returns the full assembled HTML, agent Writes to disk, calls `create_artifact` or
  `update_artifact`. One heavier run, then back to Path A.

Bumping `WARMUP_ENGINE_VERSION` forces everyone to Path B on their next run, ensuring
they pick up the new template. After that one run, they are back on Path A.

---

## Adding a new skill to the Loadout

A "skill" in this project means a set of MCP tools registered in `index.ts`, bundled
content in `skill-content/`, and an HTML template. Here is the full checklist:

**1. Create the skill content directory:**
```
missionbuilt-mcp/src/skill-content/my-skill/
├── SKILL.md          <- the framework / instructions for the LLM
└── my-template.html  <- the artifact template (if needed)
```

**2. Bundle the content in `index.ts`:**
```typescript
import MY_SKILL_MD from "./skill-content/my-skill/SKILL.md";
import MY_TEMPLATE_HTML from "./skill-content/my-skill/my-template.html";
```

**3. Add a section extractor if SKILL.md is large (>20KB):**
Model it on `getSkillSection()` — a boundary map that slices named sections by heading.
Expose it via a `section` Zod enum param on the `get_skill` tool. Never return the full
document unconditionally if it is large.

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

**5. Add a template injection tool (if there is an artifact):**
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
| Multi-line user text (epics, drafts, config files) | Fence in code block |
| Short string (source names, feature descriptions) | Strip non-ASCII + control chars, add `.max()` Zod bound |
| Nothing user-supplied | No special handling needed |

Always add a `.max()` bound to Zod string params that accept substantial user content.

---

## Backlog / known improvement items

These are real improvements but not blockers — document them here so they do not get lost:

**`spotter_get_template` — add size limit (P1):** `spotter_data` accepts an unbounded
string. Add `.max(300_000, "SPOTTER_DATA exceeds 300KB")` to the Zod schema in `index.ts`.

**`spotter_get_examples` — fix default (P1):** The `area ?? 0` default loads all 64KB of
examples. Change to require an explicit area param, or flip the default to `1`, so agents
can't accidentally burn 16K tokens per call. Also update the tool description to document
that `area:0` returns 64KB.

**Spotter font loader — sanitize `fontToolName` client-side (P1):** The warmup sanitizes
`dataToolName` server-side before embedding it in HTML. The Spotter font loader passes
`cfg.fontToolName` directly to `callMcpTool` without client-side sanitization. Add:
```javascript
var safeToolName = toolName.replace(/[^A-Za-z0-9_\-:]/g, '').slice(0, 200);
if (!safeToolName) { showFontError('invalid fontToolName', toolName.slice(0, 40)); return; }
window.cowork.callMcpTool(safeToolName, ...)
```

**Spotter demo data — update area IDs/names (P1):** The fallback `window.SPOTTER_DATA`
in `spotter-shell.rawjs` uses legacy area IDs (`problem-clarity`, `customer-truth`, etc.)
that don't match the official schema (`user-and-problem`, `competitive-landscape`, etc.).
Update all 9 demo area entries to match `spotter_get_template` docstring schema exactly.

**`spotter_build` `feature` — add `.max()` + fencing (P2):** The `feature` param is
embedded directly in instruction prose as `**${feature}**` with no length bound. Add
`.max(500)` and wrap in a fenced code block. Add a prompt injection isolation comment.

**Prompt injection comments (P2):** `spotter_iterate` (draft) and `spotter_build` (answers)
use fenced code blocks correctly but unlike `warmup_run`, have no explanatory comment about
why. Add the same comment from `warmup_run` to both handlers so the intent is clear to
future editors.

**`warmup_check_freshness` tool (P2):** Auto-refresh calls `warmup_get_data` (~15KB) just
to compare `savedAt`. A dedicated tool returning only `{ savedAt, empty }` would reduce
this to ~200 bytes. Add to `index.ts`, wire into `checkForUpdate()` in `warmup-shell.rawjs`.
Needs a server deploy.

**localStorage size guard (P2):** Font CSS (~50-100KB as base64 data URIs) and WARMUP_DATA
(~15KB) are written to localStorage without a quota check. Wrap writes in a utility that
estimates size and skips the write if approaching a 4MB budget. Caught exceptions degrade
gracefully today, but a persistent cache miss is a silent perf regression.

---

## Reference

See `references/project-context.md` for:
- Full file map with paths
- Complete design token system (CSS variables)
- Tool inventory (all 23 tools, what each does)
- Security patterns and what not to break
- Known cleanup debt
- Current version state
