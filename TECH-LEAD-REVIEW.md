# Tech Lead Review — The Loadout · Warmup PATH B, Blank Artifact, Performance
**Stack:** TypeScript · Cloudflare Workers (Durable Objects) · MCP SDK · Zod · Wrangler
**Files reviewed:** `missionbuilt-mcp/src/index.ts`, `warmup-shell.rawjs` (lines 770–940), `skill-content/warmup/SKILL.md` (Path B + schema sections), `constants.ts`, session transcript `local_a95c12d9`
**Date:** 2026-05-18

---

## 🔴 Critical  (3 findings)

### 1. SKILL.md Path B describes the old single-call API — directly contradicts the live server
**Location:** `missionbuilt-mcp/src/skill-content/warmup/SKILL.md` lines ~612–622

**Issue:** The SKILL.md "Step 4 — Render phase, Path B" section still says:
> *"Call `warmup_get_template({ warmup_data: JSON.stringify(WARMUP_DATA) })`...the response is complete, filled HTML — no editing needed...Write the filled HTML to `warmup-artifact.html`."*

The server no longer does this. `warmup_get_template` now returns paginated 600-line chunks. Any agent that calls `warmup_get_skill({ section: "run" })` or `warmup_get_skill({ section: "full" })` receives instructions that will produce a 600-line, sentinel-terminated file instead of complete HTML. The agent will write a fragment and call `create_artifact` on it — producing a blank, broken artifact.

There's also a filename conflict: SKILL.md says `warmup-artifact.html`; `warmup_run` instructions say `warmup.html`. An agent exposed to both gets a coin-flip on which name to use. On the next PATH A run, `list_artifacts` returns the html_path from the previous registration — if that used `warmup-artifact.html`, the agent Greps the wrong file and either fails or writes stale data.

**Fix:**
Update SKILL.md Path B to match the current chunked assembly protocol:
```
1. Call warmup_get_template({ warmup_data: JSON.stringify(WARMUP_DATA), chunk: 0 })
2. Read WARMUP_TOTAL_CHUNKS: N from the response.
3. Write chunk 0 to [workspace-root]/warmup.html.
4. For i = 1 to N-1 (SEQUENTIAL — never parallel):
   a. Call warmup_get_template({ chunk: i })
   b. Edit warmup.html: old='<!-- __WARMUP_SENTINEL__ -->' → new=[chunk text]
5. Grep warmup.html for '<!-- __WARMUP_SENTINEL__ -->'. If found, stop and report.
6. Call create_artifact / update_artifact.
```
Replace every reference to `warmup-artifact.html` with `warmup.html`.
Also: update the SKILL.md frontmatter version from `0.3.16` to match `WARMUP_VERSION` in `constants.ts` (`0.7.1`).

---

### 2. Renderer failures are completely silent — blank white page is the only signal
**Location:** `missionbuilt-mcp/src/warmup-shell.rawjs` lines 779–940

**Issue:** The entire renderer is wrapped in a bare try-catch:
```javascript
try { (function() {
  const D = window.WARMUP_DATA;
  if (!D) return;
  // ... 160+ lines accessing D.sections[i].items, item.dot, item.src, item.url, item.hl, item.body
})(); } catch(e) { console.error('[Warmup:Export]', e); }
```
If `D` exists but is structurally wrong — `sections[i].items` is undefined, `item.dot` is null, `sections[i].id` doesn't match a DOM element — the catch fires and the page stays white. The user sees nothing. There is no error banner, no console message visible in the artifact panel, no feedback whatsoever.

This catch is too wide. It hides every schema mismatch between what agents build and what the renderer expects. The validation added to `warmup_get_template` (chunk 0, lines ~390–402) only guards the top level — it checks `sections` is a non-empty array and `config` is an object. It doesn't validate:
- `sections[i].id` exists (required by `document.getElementById(sec.id)` at line 887)
- `sections[i].label` exists (required by `sec.label` at line 934)
- `sections[i].items` is an array (required by `sec.items.length` at line 926 — throws TypeError if undefined)
- Each item has `dot`, `src`, `url`, `hl`, `body` (all accessed without null checks)

Any one of these missing = silent blank.

**Fix (two-part):**
Part 1 — Add an error banner in the renderer:
```javascript
try { (function() {
  const D = window.WARMUP_DATA;
  if (!D) return;
  // ... renderer ...
})(); } catch(e) {
  console.error('[Warmup] Render error:', e);
  var errDiv = document.createElement('div');
  errDiv.style.cssText = 'margin:60px auto;max-width:600px;font-family:sans-serif;color:#c00;';
  errDiv.innerHTML = '<h2>Warmup render error</h2><pre style="white-space:pre-wrap;font-size:12px;">' 
    + String(e) + '</pre><p>Check WARMUP_DATA structure in the warmup-data script block.</p>';
  document.body.appendChild(errDiv);
}
```
Part 2 — Expand server-side validation in `warmup_get_template` chunk 0 (index.ts ~line 394):
```typescript
for (const sec of (parsed as any).sections) {
  if (!sec.id || typeof sec.id !== 'string')
    return { content: [{ type: "text" as const, text: `[warmup_get_template ERROR: sections[].id is missing or not a string. Every section needs an id field.]` }] };
  if (!sec.label || typeof sec.label !== 'string')
    return { content: [{ type: "text" as const, text: `[warmup_get_template ERROR: sections[].label is missing. Every section needs a label.]` }] };
  if (!Array.isArray(sec.items))
    return { content: [{ type: "text" as const, text: `[warmup_get_template ERROR: sections[${sec.id}].items is not an array. Every section needs an items array (can be empty).]` }] };
}
```

---

### 3. warmup_setup Step 6 runs the brief inline — bypasses warmup_run's schema guidance
**Location:** `missionbuilt-mcp/src/index.ts` lines 497–526 (warmup_setup tool), `skill-content/warmup/SKILL.md` lines ~352–358

**Issue:** After writing WARMUP.md, both the warmup_setup MCP instructions and the SKILL.md Step 6 say:
> *"Run a test brief using the saved config. Deliver it as a Cowork artifact."*

The agent interprets this as running the warmup RUN flow inline in the same session, without explicitly calling `warmup_run`. This means the agent builds WARMUP_DATA based on whatever it loaded for setup — typically `warmup_get_skill({ section: "sources" })` and `warmup_get_skill({ section: "warmupmd" })`. It does NOT load `warmup_get_skill({ section: "schema" })`, which is the section that defines the exact WARMUP_DATA JSON structure the renderer needs.

In the "Run warmup routine" session transcript (`local_a95c12d9`), the agent called `warmup_get_skill` 3 times but the schema section was not confirmed as loaded. The agent built WARMUP_DATA from its training memory of what the structure "should" look like — which may or may not match the 80-field schema the renderer requires.

**Fix:** Replace Step 6 in warmup_setup instructions (index.ts line ~497) with:
```
6. Call warmup_run with config_summary set to the WARMUP.md content you just wrote.
   The warmup_run tool handles all schema guidance and template assembly.
   Do not attempt to build WARMUP_DATA or call warmup_get_template manually from setup.
```
Add `config_summary` to the `warmup_setup` return text. This also eliminates the redundant WARMUP.md Read on first run.

---

## 🟠 High  (2 findings)

### 4. warmup_get_template tool description says "400-line chunks" — actual CHUNK_LINES is 600
**Location:** `missionbuilt-mcp/src/index.ts` line 322

**Issue:** The tool's schema description reads:
> *"Returns the warmup artifact HTML in paginated 400-line chunks."*
> *"Read <!-- WARMUP_TOTAL_CHUNKS: N --> ...Which 400-line chunk to return"*

`CHUNK_LINES` is 600 (line 366). With 1757 total lines, totalChunks = 3. Agents reading the description expect ~4+ chunks (1757 / 400 ≈ 4.4) and get 3. The mismatch creates uncertainty about when assembly is complete — agents may loop extra chunk calls looking for a chunk that doesn't exist.

**Fix:** Update both description references from "400" to "600":
```typescript
"Returns the warmup artifact HTML in paginated 600-line chunks...Which 600-line chunk to return"
```

---

### 5. Premature try-catch in renderer wraps DOM setup code, not just item rendering
**Location:** `warmup-shell.rawjs` lines 779–940

**Issue:** The try-catch at line 779 encloses the full DOM-building phase: section element creation (line 787), nav generation (line 802), signal bar stat population (line 845), AND per-item rendering (line 886). If the section creation loop throws (e.g., `D.sections` has items with undefined `id`), the DOM is left in a half-built state — some `<section>` elements may exist but be empty. The catch fires and the user sees a partially-built blank page or an entirely white page depending on where the error occurred.

**Fix:** Narrow the try-catch to the item rendering phase only. DOM scaffolding (sections, nav, pills) should fail loudly into the error banner added in finding #2. Item rendering can be individually wrapped so a bad item silently skips rather than aborting all sections:
```javascript
sec.items.forEach(function(item) {
  try { el.innerHTML += renderItem(item); }
  catch(e) { console.warn('[Warmup] Item render error:', e, item); }
});
```

---

## 🟡 Medium  (3 findings)

### 6. Three sequential warmup_get_skill calls before the first WebSearch fires
**Location:** Session transcript `local_a95c12d9`, confirmed by warmup_run instructions lines ~613–618

**Issue:** The warmup_run instructions tell the agent to call `warmup_get_skill` for `"sources"`, `"sections"`, and `"schema"` during the fetch and synthesis phases. Each call is a sequential MCP roundtrip to the Cloudflare Worker. In the observed session, the agent issued 3 skill calls before firing the 9 WebSearch batches. That's ~15–30 seconds of blocking MCP roundtrips (network + Durable Object wake) before any search result comes back.

The schema section (~6KB) and the sources section (~8KB) are stable reference content that changes only on version bumps. They don't need to be fetched at runtime.

**Fix:** Inline the WARMUP_DATA schema spec directly into the `warmup_run` instruction text (index.ts lines 575–617). Append it after the current reference list, fenced in a code block. This eliminates the `schema` roundtrip entirely. For `sources`, embed the CISO and Product Leader batch query tables in the instruction text (they're already short — the SKILL.md tables fit in ~40 lines). Agents still call `warmup_get_skill({ section: "sources" })` for custom mode, but CISO and Product Leader modes skip it.

Estimated time savings: 10–20 seconds per first run.

---

### 7. Deferred create_artifact forces ToolSearch in the hot path
**Location:** Session transcript `local_a95c12d9` — agent called ToolSearch to load create_artifact schema immediately before calling it

**Issue:** Cowork defers tool schemas until explicitly fetched. In the observed session, the agent completed Grep verification and then issued a ToolSearch call to load `create_artifact` before it could proceed. This is an extra roundtrip at the most expensive point in the flow — after the template is assembled and the user is waiting for the artifact to appear.

`warmup_run` doesn't tell agents to ensure artifact tools are loaded early.

**Fix:** Add to the warmup_run instruction preamble (index.ts before the "How to generate the brief" section):
```
## Before starting
If list_artifacts, create_artifact, or update_artifact are not yet loaded, load them now
via ToolSearch before proceeding. These tools are needed at the end of the flow —
loading them late adds a roundtrip after template assembly while the user is waiting.
```

---

### 8. CHUNK_LINES at 600 produces 3 chunks — reducible to 2 without hitting Cowork's size limit
**Location:** `missionbuilt-mcp/src/index.ts` line 366

**Issue:** With `CHUNK_LINES = 600`, a 1757-line template produces 3 chunks (600 + 600 + 557). The assembly sequence for PATH B is: Write(chunk 0) → warmup_get_template(chunk 1) → Edit → warmup_get_template(chunk 2) → Edit. That's 5 sequential file ops after the initial chunk call.

With `CHUNK_LINES = 900`, the template produces 2 chunks (900 + 857). Each chunk is ~22KB — well under Cowork's 67KB persistence threshold. Assembly becomes: Write(chunk 0) → warmup_get_template(chunk 1) → Edit. That's 3 sequential file ops, saving 2 roundtrips.

At ~5–10 seconds per MCP roundtrip + file op, this saves 10–20 seconds per PATH B run.

**Fix:**
```typescript
const CHUNK_LINES = 900;
```
Update the tool description from "600-line chunks" to "900-line chunks". Update the test mock `MOCK_WARMUP_HTML` to include the correct chunk count comment.

---

## ✅ Clean

- **OAuth implementation:** Cloudflare workers-oauth-provider integration is correctly structured. Tokens are not logged, not passed to clients, and not serialized into tool responses. `props.email` and `props.name` are the only user-supplied values, and they're only returned by `loadout_whoami` on explicit request.
- **XSS protection in template injection:** Both `warmup_get_template` and `spotter_get_template` correctly escape `</script>` sequences before injection (`replace(/<\/script>/gi, '<\\/script>')`). Both use replacer-function syntax (`() => replacement`) to prevent `$`-sequence expansion in article content — the v0.3.17 fix is intact and correct.
- **Prompt injection on warmup_config:** The `safeSource` sanitizer (index.ts lines 641–644) strips newlines and non-ASCII before embedding source names in instruction prose. Zod `.max(120)` bound is set. This is the right pattern.
- **Placeholder injection detection:** Both template tools detect and return an error if the placeholder wasn't found in the fill result (`filled !== shellInlined` check). No silently-wrong HTML is returned.
- **Test suite structure:** The three-scenario test design (PATH B new, PATH B stale, PATH A match) covers the important branching logic. The `saveRunReport` call after PATH B captures a full agent trace for quality review.
- **Chunk math and seam alignment:** The PREAMBLE_LINES=13 constant correctly accounts for the TOTAL_CHUNKS comment splice. Chunks 1+ start at `shellIdx = pos - 13` which is exactly where chunk 0 ends. The seam is clean — no lines are skipped or duplicated.
- **$-sequence fix is intact:** `warmup_get_template` uses `() => \`window.WARMUP_DATA = ${safe};\`` (replacer function). This is correct. Do not change to a literal string.
- **Chunk out-of-range protection:** `warmup_get_template` returns a clear error string for `chunk > totalChunks - 1`. Agents that miscounted won't get a silent empty response.

---

## Architecture Diagram
Saved to `ARCH.md`. Shows full agent ↔ MCP server ↔ Cowork data flow with token cost annotations for each path.

---

## Fix Plan

**P0 — Before next user-facing run (these directly cause blank artifacts):**

1. `skill-content/warmup/SKILL.md` ~line 612 — Update Path B description to match chunked assembly. Replace `warmup-artifact.html` → `warmup.html`. Update frontmatter version from `0.3.16` to `0.7.1`.

2. `warmup-shell.rawjs` ~line 779 — Add error banner to the catch block so users see a message instead of a blank white page (see Critical finding #2 above for exact code).

3. `index.ts` warmup_get_template chunk 0 validation (~line 394) — Add per-section validation: `sections[i].id` is a non-empty string, `sections[i].label` is a string, `sections[i].items` is an array.

4. `index.ts` warmup_setup instructions (~line 497) — Replace inline "run a test brief" instruction with "Call warmup_run with config_summary populated from the WARMUP.md you just wrote."

**P1 — This sprint (performance + correctness):**

5. `index.ts` line 322 — Update warmup_get_template description: "400-line chunks" → "600-line chunks" (or 900 if P2 fix is applied).

6. `index.ts` warmup_run instructions (~line 613) — Add early ToolSearch guidance: "Load list_artifacts, create_artifact, update_artifact before starting."

7. `index.ts` warmup_run instructions — Inline WARMUP_DATA schema and CISO/Product Leader batch query tables to eliminate 2 of the 3 warmup_get_skill roundtrips before fetch.

**P2 — Schedule:**

8. `index.ts` line 366 — Bump `CHUNK_LINES` to 900. Update tool description. Update `MOCK_WARMUP_HTML` in `tests/mocks.mjs`.

9. `warmup-shell.rawjs` ~line 886 — Narrow the try-catch; wrap per-item rendering individually so a bad item skips rather than aborting all sections.

---

## Seal of Approval

**This codebase is not ready to ship. Blockers:**
1. SKILL.md Path B describes a dead API — any agent reading that section produces a broken artifact.
2. Renderer failures are invisible — users see a blank page with no diagnosis path.
3. warmup_setup → inline run bypasses schema guidance — WARMUP_DATA structure is built on training memory, not the schema reference.

P0 items are all small, targeted changes (no architectural rework). Fix those three and the blank artifact problem is solved. P1 items close the remaining performance gap.
