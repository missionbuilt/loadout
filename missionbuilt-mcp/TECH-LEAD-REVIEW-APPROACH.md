# Tech Lead Review — The Approach (v0.2.3)
**Stack:** TypeScript · Cloudflare Workers · Zod · Vanilla JS (client renderer)
**Files reviewed:** 5 — `approach-template.html`, `SKILL.md`, `APPROACH.example.md`, `index.ts` (approach tools), `constants.ts`
**Date:** 2026-05-20

---

## Phase 0 — Recon

```
Stack:       TypeScript · Cloudflare Workers (no DO for Approach) · Zod validation ·
             Vanilla JS renderer (no framework) · Google Fonts CDN fallback
AI-adjacent: Yes — MCP server serving skill frameworks, HTML templates, and workflow
             orchestration instructions to Claude agents.
Entry points: approach_run (primes agent), approach_get_skill (section-gated SKILL.md),
              approach_get_template (data injection → filled HTML), MCP resource loadout://approach/skill
Data flow:   Agent calls approach_run → reads SKILL.md sections on demand via approach_get_skill
             → runs web research → assembles APPROACH_DATA JSON → calls approach_get_template
             (server escapes + injects into template, returns ~150KB filled HTML) → agent writes
             to disk → create_artifact renders in Cowork → artifact calls warmup_get_fonts via
             Cowork MCP bridge → font CSS cached in localStorage. All data is ephemeral;
             nothing is persisted server-side.
```

---

## 🔴 Critical  (0 findings)

None. No exposed secrets, no exploitable XSS vectors, no data breach risk.

---

## 🟠 High  (5 findings)

These all have the same root cause: **renderer field names were updated in a prior session but the SKILL.md documentation and APPROACH.example.md were not updated to match.** An agent following the documented schema generates data that silently produces blank output.

### H1 — `pull` items: schema says `quote` / `cite`, renderer reads `text`; `cite` not rendered at all
**Location:** `approach-template.html` ~line 1000 (`renderProseItem case 'pull'`); `SKILL.md` prose item reference table; `APPROACH.example.md` lines 4–9
**Issue:** SKILL.md documents `pull` as requiring `quote` and `cite`. The example uses these field names. The renderer reads `item.text` for the quote text and does not render `cite` at all — there is no `<cite>` element in the pull HTML. Any agent following the spec generates `{ type: "pull", quote: "...", cite: "..." }` and the pull renders blank. Attribution is always dropped.
**Fix:**
- In `SKILL.md` prose item reference table: change `pull | quote, cite` → `pull | text, cite`
- In `APPROACH.example.md`: rename `"quote"` → `"text"` in all pull items
- In `approach-template.html` renderer `case 'pull'`: add cite rendering:
  ```javascript
  case 'pull': {
    var h = '<div class="pull">'
      + '<q>' + rich(item.text || '') + '</q>';
    if (item.cite) h += '<cite>' + esc(item.cite) + '</cite>';
    return h + '</div>';
  }
  ```

### H2 — `facts` items: schema says `label` / `value`, renderer reads `k` / `v`
**Location:** `approach-template.html` ~line 1010 (`case 'facts'`); `SKILL.md` prose item reference table; `APPROACH.example.md` facts items
**Issue:** SKILL.md documents `facts.items[]` as requiring `label` and `value`. Example uses `{ "label": "Revenue", "value": "$700M+" }`. Renderer reads `f.k` and `f.v`. Agent-generated data produces blank fact strips — every `<span class="k">` and `<span class="v">` renders empty.
**Fix:**
- In `SKILL.md` prose item reference table: change `facts | items[] → label, value` → `items[] → k, v`
- In `APPROACH.example.md`: rename all `"label"` → `"k"` and `"value"` → `"v"` in facts items
- (Renderer is already correct — no template change needed)

### H3 — `opener` items: schema says `text` / `beat` (string), renderer reads `script` / `beats` (array)
**Location:** `approach-template.html` ~line 1025 (`case 'opener'`); `SKILL.md` prose item reference table; `APPROACH.example.md` opener item
**Issue:** SKILL.md documents opener as `text` (required) and `beat` (optional string). Example uses `{ "type": "opener", "text": "...", "beat": "..." }`. Renderer reads `item.script` for the quote and `item.beats` (array) for the beat callouts. Agent-generated data produces a blank opener — the scripted text is invisible, and the beat instruction is silently dropped.
**Fix:**
- In `SKILL.md` prose item reference: change `opener | text | beat` → `opener | script | beats[] (array of strings)`
- In `APPROACH.example.md`: rename `"text"` → `"script"` and `"beat"` → `"beats": ["..."]`
- (Renderer is already correct — no template change needed)

### H4 — `meta.generatedAt` in schema, `meta.generated` in renderer → Generated date always blank
**Location:** `approach-template.html` `renderMasthead()` line ~870; `SKILL.md` meta schema block line 178; `APPROACH.example.md` line 54
**Issue:** SKILL.md and example document `meta.generatedAt`. Renderer reads `M.generated`. When an agent generates `{ "meta": { "generatedAt": "20 May 2026" } }`, the Generated meta cell shows "—".
**Fix:**
- In `SKILL.md` meta schema block: rename `"generatedAt"` → `"generated"`
- In `APPROACH.example.md`: rename `"generatedAt"` → `"generated"`
- (Renderer is already correct)

### H5 — `meta.sourceCount` / `meta.sourceStatus` strings in schema; renderer reads `meta.sources` array
**Location:** `approach-template.html` `renderMasthead()` lines ~872–876; `SKILL.md` meta schema lines 176–177; `APPROACH.example.md` lines 52–53
**Issue:** SKILL.md and example document `sourceCount: "14"` and `sourceStatus: "all green"` as flat strings. Renderer reads `M.sources` as an array and computes count from `.length`. `sourceStatus` is never read by the renderer. Agent-generated data shows "—" for Sources in the masthead every time.
**Fix two options — pick one and make it consistent:**
- **Option A (simpler for agents):** Change renderer to read `M.sourceCount` as a display string:
  ```javascript
  $('h-meta-sources').textContent = M.sourceCount || '—';
  ```
  Remove `M.sourceStatus` from schema (renderer doesn't use it).
- **Option B (richer):** Change schema to use `meta.sources: []` (array of source objects or strings), update `SKILL.md` and example to match.
  
  Option A requires only a renderer change and a schema simplification. Option B requires agents to build an array. Recommend Option A.

---

## 🟡 Medium  (4 findings)

### M1 — `renderColophon` reads `C.seller` (undefined); seller is at `C.config.seller`
**Location:** `approach-template.html` `renderColophon()` lines ~1070–1077
**Issue:**
```javascript
function renderColophon() {
  var sub = [];
  if (C.seller)    sub.push(esc(C.seller));   // ← C.seller doesn't exist
  if (C.product)   sub.push(esc(C.product));
```
The schema puts `seller` in `C.config.seller`, not `C.seller`. `C.product` is correct (top-level). The colophon sub-row always renders as just the date, never the seller name.
**Fix:**
```javascript
function renderColophon() {
  var sub = [];
  var cfg = C.config || {};
  if (cfg.seller)  sub.push(esc(cfg.seller));
  if (cfg.se)      sub.push(esc(cfg.se));
  if (C.product)   sub.push(esc(C.product));
  if (M.generated) sub.push('Generated ' + esc(M.generated));
```

### M2 — `questions` item chips not rendered; chip in schema, dropped silently
**Location:** `approach-template.html` `case 'questions'` lines ~1040–1048; `SKILL.md` prose item reference table
**Issue:** SKILL.md documents `chip.text` and `chip.status` as optional per-item fields in questions. Example uses them. Renderer reads only `q.text` and ignores the chip entirely:
```javascript
return '<li>' + esc(typeof q === 'string' ? q : (q.text || '')) + '</li>';
```
The MEDDPICC chip visual cue (which tells the seller which discovery dimension a question targets) never renders.
**Fix:**
```javascript
return '<li>' + (q.chip
  ? '<span class="mp-chip ' + esc(q.chip.status||'') + '">' + esc(q.chip.text||'') + '</span>'
  : '')
  + esc(typeof q === 'string' ? q : (q.text || '')) + '</li>';
```

### M3 — SKILL.md version history stops at v0.2.0; three releases undocumented
**Location:** `SKILL.md` Version history table (last entry)
**Issue:** Current version is 0.2.3. The history table's last entry is `0.2.0 | Inline template architecture`. Versions 0.2.1, 0.2.2, and 0.2.3 are missing — anyone reading the changelog to understand recent changes gets an incomplete picture.
**Fix:** Add entries to the version history table for each release. Based on the commit history and session notes, the missing entries cover the C1 editorial redesign, MEDDPICC placement, renderer field name fixes, and footer changes.

### M4 — `approach_get_template` does not validate JSON before injection; malformed JSON → silent near-blank output
**Location:** `index.ts` lines 1238–1255
**Issue:** The tool receives `approach_data` as a string, escapes `</script>`, and injects. No JSON.parse validation occurs server-side. If an agent passes malformed JSON, the template's try/catch sets `APPROACH_DATA = null` and the renderer silently produces a "Brief." heading with all sections empty. This is hard to diagnose — no error surfaces in the artifact or to the calling agent.
**Fix:** Add a parse check server-side and return a clear error early:
```typescript
async ({ approach_data }) => {
  try { JSON.parse(approach_data); } catch (e) {
    return { content: [{ type: "text" as const,
      text: `[approach_get_template] ERROR: approach_data is not valid JSON — ${String(e)}. Fix the data object and retry.` }] };
  }
  const safe = approach_data.replace(/<\/script>/gi, '<\\/script>');
  // ... rest of injection
```

---

## 🟢 Low / Recommendations  (2)

### L1 — `meta.sourceStatus` field is documented but never consumed
**Location:** `SKILL.md` meta schema line 177; `APPROACH.example.md` line 53
**Issue:** `sourceStatus: "all green"` appears in the documented schema and example. No renderer code reads it. Agents spend tokens generating a field that has no effect.
**Fix:** Remove `sourceStatus` from the `meta` schema in SKILL.md and APPROACH.example.md, or implement a visual indicator in the masthead (e.g., a colored dot next to the Sources count).

### L2 — `approach_data` Zod limit is 300KB; typical brief is ~5–10KB
**Location:** `index.ts` line 1233
**Issue:** `z.string().max(300000)` allows 30× the typical payload. This isn't a bug, but it means a misconfigured agent could send a very large string and the server would accept and process it. Not a real attack surface since this is an authenticated MCP, but worth tightening.
**Fix:** Consider `max(50000)` — generous (5× a large brief) but bounded.

---

## ✅ Clean

- **`</script>` XSS escaping in `approach_get_template`:** Properly done server-side before injection. The client-side renderer cannot re-escape because the server already handled it.
- **Replacer function pattern:** `APPROACH_TEMPLATE_HTML.replace(PLACEHOLDER, () => safe)` correctly bypasses `$`-sequence expansion. Consistent with the Warmup and Spotter.
- **`esc()` coverage in renderer:** All user-controlled string fields in the renderer pass through `esc()` before insertion into innerHTML. No unescaped interpolation found.
- **`rich()` function XSS safety:** Calls `esc()` first, then applies pattern substitutions — the correct order. The chip status is constrained by regex to `confirmed|partial|unknown`; no injection path.
- **Export function `</script>` + replacer:** Client-side export uses `replace(/<\/script>/gi, '<\\/script>')` + replacer function — both guards present, consistent with server-side pattern.
- **Font loader `safeToolName` sanitization:** `toolName.replace(/[^A-Za-z0-9_\-:]/g, '').slice(0, 200)` — clean before use as an MCP call argument.
- **`approach_md_path` sanitization:** Non-ASCII and special chars stripped before inclusion in the returned hint string. Prevents prompt injection via a crafted path value.
- **Injection failure detection:** `const injected = filled !== APPROACH_TEMPLATE_HTML` — catches missing placeholder and returns a clear error rather than silently serving an empty template.
- **Section-gated SKILL.md loading:** Per-section `approach_get_skill` with enumerated sections is excellent token design. Normal run loads ~200–300 lines instead of all 457.
- **Font caching via localStorage:** `warmup-fonts-v2` cache key means repeat artifact opens skip the MCP font call entirely.
- **No secrets in template or SKILL.md:** Confirmed. `config.fontToolName` is a session-scoped tool name, not a credential.
- **Single-path render (no Path A/B):** Simpler and cheaper than the Warmup's dual-path system. Correct choice for a brief that is generated once per prospect.
- **`approach_run` primes the full workflow in one tool call:** No repeated calls to understand phase sequencing.

---

## Architecture Diagram
Saved to `ARCH-APPROACH.md`. Shows the full data and token flow from agent invocation through to Cowork artifact rendering, with per-call cost annotations.

---

## Fix Plan

**P0 — Before shipping (schema mismatches cause blank output on every real run):**
1. `SKILL.md` + `APPROACH.example.md` — rename `pull.quote` → `pull.text` (H1)
2. `approach-template.html case 'pull'` — add `<cite>` rendering (H1)
3. `SKILL.md` + `APPROACH.example.md` — rename `facts.label`/`facts.value` → `facts.k`/`facts.v` (H2)
4. `SKILL.md` + `APPROACH.example.md` — rename `opener.text`/`opener.beat` → `opener.script`/`opener.beats[]` (H3)
5. `SKILL.md` + `APPROACH.example.md` — rename `meta.generatedAt` → `meta.generated` (H4)
6. `SKILL.md` + `APPROACH.example.md` — replace `meta.sourceCount`/`meta.sourceStatus` with Option A (renderer reads `M.sourceCount`) or Option B (`meta.sources` array) (H5)
7. `approach-template.html renderColophon` — fix `C.seller` → `C.config.seller` (M1)

**P1 — This sprint:**
8. `approach-template.html case 'questions'` — render chip per question item (M2)
9. `index.ts approach_get_template` — add JSON.parse validation before injection (M4)
10. `SKILL.md` version history — add entries for 0.2.1, 0.2.2, 0.2.3 (M3)

**P2 — Schedule:**
11. `SKILL.md` + `APPROACH.example.md` — remove `meta.sourceStatus` (L1)
12. `index.ts` — tighten `approach_data` Zod max to 50000 (L2)

---

## Seal of Approval

This codebase is not ready to ship. The five P0 schema mismatches mean every agent-generated brief will have blank pull quotes, blank facts strips, a blank opener, a blank Generated date, and a blank Sources count — silently, with no error. The underlying infrastructure (injection pattern, escaping, font loading, section routing) is solid. Fix the docs, fix the two renderer gaps (cite, colophon seller), and this is ready.
