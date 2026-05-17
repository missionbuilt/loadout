# Loadout — Project Context Reference

## File map

```
/Users/mike/Projects/loadout/              ← git repo root / workspace root
│
├── warmup/
│   └── warmup-template.html              ← CANONICAL warmup template (always edit this first)
│
├── skills/
│   └── loadout-dev/                      ← this skill
│
├── SKILL-BUILDING-CONTEXT.md             ← human-readable extended reference
│
└── missionbuilt-mcp/                     ← Cloudflare Worker (deploy from here)
    ├── src/
    │   ├── index.ts                      ← all 17 MCP tools + McpAgent class
    │   ├── auth.ts                       ← Google OAuth 2.1 flow
    │   ├── constants.ts                  ← ALL version numbers (single source of truth)
    │   ├── design.ts                     ← brandCss() design token system
    │   ├── landing.ts                    ← / route (public landing page)
    │   └── preview.ts                    ← /preview route (Warmup walkthrough)
    │
    ├── src/skill-content/
    │   ├── warmup/
    │   │   ├── SKILL.md                  ← Warmup framework (~90KB, section-loadable)
    │   │   └── warmup-template.html      ← BUNDLED COPY (must match canonical)
    │   └── spotter/
    │       ├── SKILL.md                  ← Spotter framework (~29KB, section-loadable)
    │       ├── area-examples.md          ← 64 worked examples (~64KB)
    │       ├── synthetic-epic.md         ← Calibration epic 1 (gap-heavy)
    │       ├── synthetic-epic-2.md       ← Calibration epic 2 (well-formed)
    │       ├── synthetic-epic-3.md       ← Calibration epic 3 (well-formed)
    │       └── spotter-template.html     ← Spotter artifact template
    │
    ├── ARCH.md                           ← Architecture diagram (Mermaid)
    └── TECH-LEAD-REVIEW.md              ← Last tech lead review report
```

---

## Version constants — `missionbuilt-mcp/src/constants.ts`

```typescript
export const SERVER_VERSION        = "1.0.1";
export const WARMUP_VERSION        = "0.3.17";
export const WARMUP_ENGINE_VERSION = "v0.3.17";
export const SPOTTER_VERSION       = "0.6.0";
export const TOOL_COUNT            = 17;
```

---

## Tool inventory (17 tools total)

### Shared
| Tool | What it does |
|------|-------------|
| `loadout_whoami` | Returns authenticated user's email + name |
| `loadout_get_brand_css` | Returns the Mission Built design CSS (~8KB) |

### The Warmup (6 tools)
| Tool | What it does | Token cost |
|------|-------------|------------|
| `warmup_get_skill` | Returns a SKILL.md section (or full ~90KB) | 5–90KB |
| `warmup_list_modes` | Returns 3 modes with descriptions | ~1KB |
| `warmup_get_template` | Injects WARMUP_DATA, returns filled 131KB HTML | **~131KB** |
| `warmup_setup` | Returns setup flow instructions | ~2KB |
| `warmup_run` | Returns run instructions + Path A/B logic | ~2KB |
| `warmup_config` | Returns source management instructions | ~1KB |

### The Spotter (9 tools)
| Tool | What it does | Token cost |
|------|-------------|------------|
| `spotter_get_skill` | Returns a SKILL.md section (or full ~29KB) | 3–29KB |
| `spotter_list_areas` | Returns 9 areas with weight notes | ~1KB |
| `spotter_get_examples` | Returns worked examples per area | 7–64KB |
| `spotter_get_calibration_epic` | Returns calibration epic #1 | ~3KB |
| `spotter_get_calibration_epics` | Returns all 3 calibration epics | ~9KB |
| `spotter_get_template` | Injects SPOTTER_DATA, returns filled HTML | large |
| `spotter_review` | Returns review instructions + fenced epic | ~2KB |
| `spotter_build` | Returns build mode instructions | ~1KB |
| `spotter_iterate` | Returns iterate instructions + fenced draft | ~2KB |

---

## Design tokens (CSS custom properties)

Both templates use these tokens from the Iron Log design system:

```css
/* Backgrounds */
--paper:      #171513   /* base background */
--paper-tint: #1f1c19   /* panel / card background */

/* Borders */
--rule:       #2a2622   /* primary border */
--rule-soft:  #221f1c   /* subtle border */

/* Text */
--ink:        #ebe5d8   /* primary text (chalk) */
--ink-dim:    #a8a094   /* secondary text */
--ink-faint:  #5a564f   /* tertiary / placeholder */

/* Accent */
--blood:      #a8211a   /* oxblood red — primary CTA, active states */
--army:       #7a8b3a   /* green — safe/live indicators only */

/* Typography */
--font-display: 'Oswald', 'Archivo Narrow', sans-serif
--font-serif:   'Merriweather', Georgia, serif
--font-mono:    'JetBrains Mono', ui-monospace, monospace
```

Never hardcode hex values that duplicate these tokens.

---

## Toolbar pattern — both templates share this exactly

Both warmup and spotter use the same `.tb-btn` CSS class and the same fullscreen implementation.

**CSS:**
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

**Fullscreen button (match exactly):**
```html
<button class="tb-btn" id="fs-btn" onclick="toggleFullscreen()">⛶ Fullscreen</button>
```

**Fullscreen JS:**
```javascript
function toggleFullscreen() {
  const el = document.documentElement;
  if (document.fullscreenElement || document.webkitFullscreenElement) {
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  } else {
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) req.call(el).catch(function(err) {
      console.warn('[SkillName:Fullscreen] blocked —', err && err.message ? err.message : err);
    });
  }
}
document.addEventListener('fullscreenchange', function() {
  var btn = document.getElementById('fs-btn');
  if (btn) btn.textContent = document.fullscreenElement ? '← Exit' : '⛶ Fullscreen';
});
document.addEventListener('webkitfullscreenchange', function() {
  var btn = document.getElementById('fs-btn');
  if (btn) btn.textContent = document.webkitFullscreenElement ? '← Exit' : '⛶ Fullscreen';
});
```

**Export dropdown (warmup pattern):**
```html
<div class="tb-export">
  <button class="tb-btn save" onclick="toggleExport(event)">Export ▾</button>
  <div class="tb-dropdown" id="export-dd">
    <button class="dd-primary" onclick="exportHTML();closeExport()">Export HTML</button>
    <button onclick="window.print();closeExport()">Print / PDF</button>
  </div>
</div>
```

Export philosophy: **print/save what is on screen.** If deep dives are open, they export. The `@media print` CSS handles visibility — no JS logic for choosing what to include.

---

## Security patterns — do not break these

| Pattern | Location | Why |
|---------|----------|-----|
| `</script>` escape before injection | `index.ts` template tools | Prevents article content from closing the script tag |
| Replacer function in `.replace()` | Same | Prevents `$'`/`$&`/`` $` `` corruption (fixed v0.3.17) |
| `escapeHtml()` in error pages | `auth.ts:errorPage()` | Prevents XSS in OAuth error messages |
| Fenced code blocks for user content | `warmup_run`, `spotter_review`, `spotter_iterate` | Prevents prompt injection into agent instructions |
| `source` sanitization | `warmup_config` | Strips non-ASCII + control chars before embedding |
| Zod `.max()` on long params | `epic`, `draft` | Bounds user-supplied content |
| OAuth state UUID + 300s TTL + delete-after-use | `auth.ts` | Prevents OAuth state replay |

---

## `getSkillSection` / `getSpotterSkillSection` — lazy-loading pattern

Both functions take the full SKILL.md string and a section name, and return only the
requested slice (by heading boundary). The boundary map lives at the top of each function.

When adding new sections to a SKILL.md, add the corresponding boundary entry:
```typescript
const boundaries: Record<string, [string, string | null]> = {
  existing: ["## Existing Section", "## Next Section"],
  new_section: ["## My New Section", "## Whatever Follows It"],
};
```

Section names must match the Zod enum on the tool's `section` parameter. Keep them in
sync — a section in the boundary map that isn't in the enum is unreachable from agents.

---

## The `intentField` — always include it

Every tool must have this as its first parameter:
```typescript
const intentField = z.string().describe(
  "Permission dialog text — one sentence, ≤100 chars. E.g. 'Loading Warmup skill framework'."
);
```
It's defined once at the top of `index.ts` and re-used across all tools. It powers the
Cowork permission dialog. Omitting it breaks the Cowork UX.

---

## Known cleanup debt

- `buildBriefPDF` function is block-commented in both warmup template copies. Contains
  Unicode font metrics tables that prevent clean Edit tool deletion. Delete when bash
  is available (`git diff` first to confirm scope).
- `print-no-dives` CSS class in `@media print` — set by the old PDF flow, never set
  now. Inert. Safe to remove.
- `spotter_build` `feature` param has no `.max()` Zod bound (all other long params do).
- OAuth flow missing state-cookie binding (login-CSRF mitigation). See TECH-LEAD-REVIEW.md.
- `oauthReqInfo` in `auth.ts` is typed `any` after `JSON.parse`. Should be Zod-validated.

---

## Architecture at a glance

```
Claude (MCP client)
  ↓  OAuth Bearer token
Cloudflare Worker (index.ts + auth.ts)
  ├── /authorize, /google/callback → Google OAuth
  ├── /sse → MissionBuiltMCP Durable Object (17 tools)
  └── / /preview /health /brand.css → public routes

All skill content bundled at deploy time (Wrangler text imports):
  SKILL.md files · HTML templates · calibration epics · examples

Agent filesystem (user's machine):
  WARMUP.md → agent reads config from here
  warmup.html / spotter.html → agent writes artifacts here
```

Config (`WARMUP.md`) never leaves the user's machine. The server holds no user data
beyond OAuth session state (Cloudflare KV, 5-minute TTL).
