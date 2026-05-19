# Skill Building Context — The Loadout (Mission Built MCP)

*For any Claude session doing skill work on this project. Read this before touching any file.*

---

## What this project is

**The Loadout** is an open-source MCP server at `mcp.missionbuilt.io` that exposes two AI skills to Claude:

- **The Warmup** — daily intelligence brief, rendered as a live HTML artifact
- **The Spotter** — B2B product epic review framework, rendered as a scored HTML artifact

The server is a Cloudflare Worker + Durable Objects, using Google OAuth 2.1 for auth. All skill content (SKILL.md, HTML templates, examples) is bundled at build time via Wrangler text imports — no runtime file reads.

**Repo:** `https://github.com/missionbuilt/loadout`
**Deploy command:** `npx wrangler deploy` (run from `missionbuilt-mcp/`)

---

## File map — where everything lives

```
/Users/mike/Projects/loadout/              ← workspace root (git repo root is here)
│
├── warmup/
│   └── SKILL.md                          ← CANONICAL warmup SKILL.md (human-readable copy)
│
├── missionbuilt-mcp/                     ← Cloudflare Worker source
│   ├── src/
│   │   ├── index.ts                      ← All MCP tools, tool handlers, warmup_run text
│   │   ├── auth.ts                       ← Google OAuth flow
│   │   ├── constants.ts                  ← ALL version numbers live here
│   │   ├── design.ts                     ← brandCss() design token system
│   │   ├── landing.ts                    ← / route (landing page)
│   │   ├── preview.ts                    ← /preview route (walkthrough page)
│   │   ├── warmup-shell.rawjs            ← WARMUP RUNTIME — CSS + HTML + renderer JS
│   │   ├── spotter-shell.rawjs           ← Spotter runtime
│   │   └── approach-shell.rawjs          ← The Approach runtime
│   │
│   └── src/skill-content/
│       ├── warmup/
│       │   ├── SKILL.md                  ← BUNDLED warmup SKILL.md (imported by worker)
│       │   ├── SKILL-DESIGN.md           ← Design spec for the Morning Edition layout
│       │   └── fonts.css                 ← Oswald / Merriweather / Permanent Marker / JetBrains Mono
│       ├── spotter/
│       │   ├── SKILL.md
│       │   ├── area-examples.md
│       │   ├── synthetic-epic.md / -2 / -3
│       │   └── spotter-template.html     ← Spotter still uses an HTML template
│       └── the-approach/
│           ├── SKILL.md
│           └── approach-template.html
│
├── SKILL-BUILDING-CONTEXT.md            ← this file
├── ARCH.md                               ← (inside missionbuilt-mcp/, auto-generated)
└── TECH-LEAD-REVIEW.md                   ← (inside missionbuilt-mcp/, auto-generated)
```

**Wrangler bindings** (in `missionbuilt-mcp/wrangler.toml`): `MCP_OBJECT` (Durable Object for SSE state), `OAUTH_KV` (OAuth client registrations + tokens), `WARMUP_KV` (per-user warmup briefs, v0.8+).

---

## The canonical / bundled rule — applies to SKILL.md only

The warmup **SKILL.md** exists in two places:

1. **Canonical:** `/Users/mike/Projects/loadout/warmup/SKILL.md` (human-readable copy in the repo root area)
2. **Bundled:** `/Users/mike/Projects/loadout/missionbuilt-mcp/src/skill-content/warmup/SKILL.md` (imported by the worker via Wrangler text rule)

**Always edit the canonical copy first. Then apply the identical changes to the bundled copy.** The worker only sees the bundled version, so if they diverge, agents calling `warmup_get_skill` will work against the bundled (live) text while the canonical drifts and misleads future readers.

**Verification after a SKILL.md edit:**
```
grep -c "warmup_save_data" warmup/SKILL.md
grep -c "warmup_save_data" missionbuilt-mcp/src/skill-content/warmup/SKILL.md
```
Both counts must match.

> **Historical note (v0.3.x–v0.7.x):** the project also kept canonical + bundled copies of `warmup-template.html`. That template was retired in v0.8.0 — the warmup runtime now lives entirely in `warmup-shell.rawjs`, and the data flow goes through `warmup_save_data` → KV → `warmup_get_data` instead of an inline `<script>` injection. The two `.html` template files were deleted in the v0.8 cleanup. The spotter and the-approach skills still use their HTML templates.

---

## Version constants — always in `constants.ts`

**File:** `missionbuilt-mcp/src/constants.ts`

```typescript
export const SERVER_VERSION        = "1.1.0";   // Worker deploy version
export const WARMUP_VERSION        = "0.8.0";   // bump when warmup SKILL.md or shell changes
export const WARMUP_ENGINE_VERSION = "v0.8.0";  // bump when warmup-shell.rawjs changes
export const SPOTTER_VERSION       = "0.7.17";  // bump when Spotter SKILL.md changes
export const THE_APPROACH_VERSION  = "0.1.4";   // bump when Approach SKILL.md changes
export const TOOL_COUNT            = 23;        // update when adding/removing tools
```

**Bump rules:**
- Change to `warmup-shell.rawjs` → bump `WARMUP_VERSION` AND `WARMUP_ENGINE_VERSION`
- Change to warmup `SKILL.md` → bump `WARMUP_VERSION`
- Change to spotter `SKILL.md` or areas → bump `SPOTTER_VERSION`
- New tool added or removed → update `TOOL_COUNT`

**Why `WARMUP_ENGINE_VERSION` matters critically:**
The `warmup_run` tool reads the first 10 lines of the user's existing `warmup.html` artifact and matches the `<!-- warmup-engine: vX.Y.Z -->` marker against this constant. On a match, the agent skips rewriting the file (the artifact is already current; just call `warmup_save_data`). On a mismatch (or no file at all), the agent re-fetches the shell from `warmup_get_template` and rewrites the file with the new engine. Without the bump, agents with stale files keep running on the old engine forever.

---

## How warmup data flows in v0.8

There is no longer an inline placeholder in the warmup HTML. The artifact is a pure renderer.

1. **Agent run:** synthesize WARMUP_DATA, then call `warmup_save_data({ warmup_data: JSON.stringify(WARMUP_DATA) })`. The server validates it parses to an object with a `config` field, then stores `{ data, savedAt }` in KV at `warmup:{email}:current`.
2. **Artifact boot:** shell reads `window.WARMUP_TOOLS.dataTool` (baked in once at create-artifact time via `warmup_get_template({ dataToolName: "mcp__<uuid>__warmup_get_data" })`), then calls `warmup_get_data` via the Cowork MCP bridge.
3. **Auto-refresh:** on every `visibilitychange` and `focus` event, the shell re-fetches and compares `savedAt`. Newer payload → save in-flight UI state to `sessionStorage`, `location.reload()`. The reload restores scroll position and section-done toggles from `sessionStorage`.

The legacy `</script>` XSS escape and `$`-sequence replacer-function rule for warmup are obsolete since v0.8 — data never touches inline script context. **Both rules still apply to the spotter and the-approach templates**, which inject SPOTTER_DATA / APPROACH_DATA server-side via the same `replace(/<\/script>/gi, '<\\/script>')` + `() => replacement` pattern. Don't revert those.

If the placeholder is missing from the template, `warmup_get_template` returns:
```
[warmup_get_template ERROR: WARMUP_DATA placeholder not found in template — injection failed. ...]
```
This is intentional — don't suppress it.

---

## How the toolbar pattern works (warmup + spotter share this)

Both templates use the same toolbar CSS and button pattern:

**CSS (`.tb-btn` class):**
```css
.tb-btn {
  font-family: var(--font-mono); font-size: 10px; font-weight: 500;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--ink-dim); background: transparent;
  border: 1px solid var(--rule); padding: 4px 11px; cursor: pointer;
  transition: color 0.1s, border-color 0.1s, background 0.1s; white-space: nowrap;
}
.tb-btn:hover { color: var(--ink); background: var(--paper-tint); }
.tb-btn.save { color: var(--blood); }
.tb-btn.save:hover { color: var(--paper); background: var(--blood); border-color: var(--blood); }
```

**Fullscreen button (match this exactly in both templates):**
```html
<button class="tb-btn" id="fs-btn" onclick="toggleFullscreen()">⛶ Fullscreen</button>
```
```javascript
function toggleFullscreen() {
  const el = document.documentElement;
  if (document.fullscreenElement || document.webkitFullscreenElement) {
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  } else {
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) req.call(el).catch(function(err) {
      console.warn('[Warmup:Fullscreen] blocked —', err && err.message ? err.message : err);
    });
  }
}
document.addEventListener('fullscreenchange', function() {
  const btn = document.getElementById('fs-btn');
  if (btn) btn.textContent = document.fullscreenElement ? '← Exit' : '⛶ Fullscreen';
});
document.addEventListener('webkitfullscreenchange', function() {
  const btn = document.getElementById('fs-btn');
  if (btn) btn.textContent = document.webkitFullscreenElement ? '← Exit' : '⛶ Fullscreen';
});
```

**Export dropdown (warmup):**
```html
<div class="tb-export">
  <button class="tb-btn save" onclick="toggleExport(event)">Export ▾</button>
  <div class="tb-dropdown" id="export-dd">
    <button class="dd-primary" onclick="exportHTML();closeExport()">Export HTML</button>
    <button onclick="window.print();closeExport()">Print / PDF</button>
  </div>
</div>
```

The export design philosophy: **print/save what is on screen**. If deep dives are open, they export. If not, they don't. The `@media print` CSS handles this: `.deep-result { display: none !important; }` + `.deep-result.visible { display: block !important; }`. No modal, no choice.

---

## Edit tool limitations — hard lessons

### Problem: Unicode characters break exact matching
The Edit tool requires an exact string match. Font metrics tables in the warmup template contain curly quotes and em dashes (e.g., `' ':278`, `'"':355`) that look like ASCII but aren't. If you try to edit a block containing these, the Edit tool will return "String to replace not found" even if the text looks right visually.

**Workarounds:**
1. **Break big edits into small, targeted ones.** Target lines above or below the Unicode block.
2. **Use block comments for dead code** instead of deleting it. `/* dead code */` is safer than trying to delete 500 lines containing font metrics tables.
3. **Never try to match curly quotes or em dashes** in old_string — they won't match.

### Problem: File state mismatch after edits
If the Edit tool says "File has been modified since read," you must Read the file again before attempting a new edit. Always read the specific line range you need, not the full file (large files are slow).

### Problem: Large file edits fail even when they look right
If an edit fails on a large block, break it into 3–5 smaller targeted edits. Edit the CSS section, then the HTML section, then the JS section — separately.

### Problem: Bash sandbox unavailability
When bash returns "no disk space" or similar errors, all file operations must use the Read/Edit/Write tools only. You cannot `grep`, `diff`, or `cp` via bash. Workarounds:
- Use the `Grep` tool for searching file contents
- Use the `Glob` tool for finding files
- Verify changes by reading specific line ranges after editing

---

## Prompt injection — how it's handled in tool handlers

When user-supplied content is embedded in instruction text returned to the agent, it must be fenced or sanitized:

| Parameter | Tool | Handling |
|-----------|------|----------|
| `config_summary` | `warmup_run` | Fenced in ` ```\n...\n``` `, sliced to 8000 chars |
| `source` | `warmup_config` | Sanitized: strip `\r\n`, non-ASCII, slice to 120 chars |
| `epic` | `spotter_review` | Fenced in ` ```\n...\n``` `, `.max(20000)` Zod |
| `draft` | `spotter_iterate` | Fenced in ` ```\n...\n``` `, `.max(20000)` Zod |
| `feature` | `spotter_build` | Inline bold only — low risk, short string |

If you add a new tool that embeds user content in instruction prose, wrap it in a fenced block.

---

## Adding a new tool to `index.ts`

Tools are registered inside `async init()` in the `MissionBuiltMCP` class:

```typescript
this.server.tool(
  "tool_name",
  "Description — what the agent should call this for.",
  {
    intent: intentField,               // always include this
    my_param: z.string().describe("What this is."),
  },
  async ({ my_param }) => ({
    content: [{ type: "text" as const, text: "your response" }],
  })
);
```

**`intentField`** is a re-used Zod field that produces the Cowork permission dialog:
```typescript
const intentField = z.string().describe(
  "Permission dialog text — one sentence, ≤100 chars. E.g. 'Loading Warmup skill framework'."
);
```
Always include it as the first parameter in every tool.

**After adding a tool:** increment `TOOL_COUNT` in `constants.ts`.

---

## Adding new bundled content

To bundle a new file in the Worker, add a Wrangler text import at the top of `index.ts`:
```typescript
import MY_NEW_FILE from "./skill-content/warmup/my-new-file.md";
```
Then use `MY_NEW_FILE` in tool handlers. No runtime fetch, no external storage — the content is baked into the Worker bundle at deploy time.

---

## Skill section lazy-loading pattern

Both SKILL.md files are large (Warmup ~90KB, Spotter ~29KB). Tools that return skill content use section-extraction functions to avoid returning the full document on every call:

```typescript
function getSkillSection(md: string, section: string): string {
  const boundaries: Record<string, [string, string | null]> = {
    setup:  ["## SETUP Mode", "## RUN Mode"],
    run:    ["## RUN Mode",   "## CONFIGURE Mode"],
    // ...
  };
  if (section === "full" || !boundaries[section]) return md;
  const [startMark, endMark] = boundaries[section];
  const si = md.indexOf(startMark);
  if (si === -1) return `[Section "${section}" not found in SKILL.md — use section:"full"]`;
  const ei = endMark ? md.indexOf(endMark, si) : md.length;
  return md.slice(si, ei === -1 ? md.length : ei).trim();
}
```

When adding new sections to SKILL.md, add the corresponding entry to the `boundaries` map. When adding a new tool that returns skill content, expose a `section` Zod enum parameter — never return the full document unconditionally.

---

## Design token system

Both templates use CSS custom properties from the Iron Log design system. Key tokens:

```css
--paper:     #171513   /* base background */
--paper-tint:#1f1c19   /* panel / card background */
--rule:      #2a2622   /* borders, dividers */
--ink:       #ebe5d8   /* primary text (chalk) */
--ink-dim:   #a8a094   /* secondary text */
--ink-faint: #5a564f   /* tertiary / placeholder text */
--blood:     #a8211a   /* primary accent (oxblood red) */
--army:      #7a8b3a   /* success / "live" / safe indicators */
--font-display: 'Oswald', 'Archivo Narrow', sans-serif
--font-serif:   'Merriweather', Georgia, serif
--font-mono:    'JetBrains Mono', ui-monospace, monospace
```

Use these tokens in any new template UI. Never hardcode hex values that duplicate these. The full design system is in `design.ts` and accessible via the `loadout_get_brand_css` tool.

---

## Commit and deploy workflow

```bash
# From /Users/mike/Projects/loadout/ (repo root) or missionbuilt-mcp/
git add -A
git commit -m "skill name vX.X.X — summary of what changed"
npx wrangler deploy   # run from missionbuilt-mcp/
```

**Commit message format:** `warmup v0.3.17 — Export dropdown, spotter-matched fullscreen`

**Watch out for `$` in commit messages.** The shell interprets `$'`, `$&`, `$\`` as special sequences in double-quoted strings. Use single quotes for the commit message, or escape every `$` as `\$`. Or just avoid `$` in the message entirely.

**After deploy:** verify at `https://mcp.missionbuilt.io/health` that `server_version` matches.

---

## Security patterns — don't break these

| Pattern | Where | Why |
|---------|-------|-----|
| `</script>` escape before template injection | `index.ts:warmup_get_template, spotter_get_template` | Prevents XSS via article content closing the script tag |
| Replacer function in `.replace()` | Same | Prevents `$`-sequence corruption (v0.3.17 fix) |
| `escapeHtml()` in error pages | `auth.ts:errorPage()` | Prevents XSS in OAuth error messages |
| Fenced code blocks for user content in prompts | `warmup_run`, `spotter_review`, `spotter_iterate` | Prevents prompt injection overriding agent instructions |
| `source` sanitization | `warmup_config` | Strip non-ASCII + control chars before embedding in instruction text |
| Zod `.max()` on long string params | `epic`, `draft` | Bounds user-supplied content |
| OAuth state UUID + 300s KV TTL + delete-after-use | `auth.ts` | Prevents OAuth state replay |

---

## Known cleanup debt

- `buildBriefPDF` is no longer carried — the v0.8 shell drops PDF generation entirely in favour of browser-native `window.print()` from the Export dropdown.
- `print-no-dives` CSS class exists in `@media print` in `warmup-shell.rawjs` but is never set by any JS since the Export dropdown change. Inert — safe to remove.
- `spotter_build` `feature` param has no `.max()` bound. Low risk but inconsistent.
- OAuth flow missing state-cookie binding (login-CSRF protection). Medium priority — see TECH-LEAD-REVIEW.md.

---

## What agents actually do with these tools (the flow)

**Daily warmup run:**
1. Agent calls `warmup_run` → gets instruction text
2. Agent reads `WARMUP.md` from user's disk → gets their config
3. Agent calls `list_artifacts` → checks if "the-warmup" exists and what engine version it has
4. **Path A** (engine version matches): agent Greps for `<script id="warmup-data">` in the artifact file, reads ~20 lines, Edits just the WARMUP_DATA block, calls `update_artifact`
5. **Path B** (first run or stale engine): agent calls `warmup_get_template({ warmup_data: JSON.stringify(data) })`, server returns filled 131KB HTML, agent Writes to disk, calls `create_artifact`

**Spotter review:**
1. Agent calls `spotter_review({ epic: "..." })` → gets instruction text + fenced epic
2. Agent calls `spotter_get_skill({ section: "areas" })` → loads area framework
3. Agent grades all 9 areas
4. Agent calls `spotter_get_template({ spotter_data: JSON.stringify(data) })` → gets filled artifact HTML
5. Agent Writes to disk, calls `create_artifact` or `update_artifact`

**The "NEVER write your own HTML" rule** — both `warmup_run` and `spotter_review` contain explicit non-negotiable rules: the artifact HTML comes ONLY from the server-side template tool, never reconstructed from the agent's training memory. Every time an agent generates HTML from memory, the design is wrong. Reinforce this rule if editing those instruction strings.

---

## Token budget awareness

When adding or editing tools, keep this in mind:

| Response size | Tools | Action |
|--------------|-------|--------|
| < 2KB | `list_modes`, `list_areas`, `whoami` | Fine to call freely |
| ~2KB | `warmup_run`, `warmup_setup`, spotter primers | OK — instruction text only |
| 5–15KB | `get_skill(section)` | Always use section params |
| ~8KB | `loadout_get_brand_css` | Once per session |
| **~90KB** | **`warmup_get_skill(full)`** | **Avoid — section params exist** |
| **~131KB** | **`warmup_get_template`** | **Path B / first-run only** |
| **~64KB** | **`spotter_get_examples(area:0)`** | **Avoid mid-review** |

If you add a new tool that returns large content, add a section/area parameter so callers can load only what they need.

---

## Current versions (as of v0.3.17)

- `SERVER_VERSION = "1.0.1"`
- `WARMUP_VERSION = "0.3.17"`
- `WARMUP_ENGINE_VERSION = "v0.3.17"`
- `SPOTTER_VERSION = "0.6.0"`
- `TOOL_COUNT = 17`

Tools: `loadout_whoami`, `loadout_get_brand_css`, `warmup_get_skill`, `warmup_list_modes`, `warmup_get_template`, `warmup_setup`, `warmup_run`, `warmup_config`, `spotter_get_skill`, `spotter_list_areas`, `spotter_get_examples`, `spotter_get_calibration_epic`, `spotter_get_calibration_epics`, `spotter_get_template`, `spotter_review`, `spotter_build`, `spotter_iterate`
