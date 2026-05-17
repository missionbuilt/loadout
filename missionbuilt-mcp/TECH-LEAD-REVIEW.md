# Tech Lead Review — Mission Built MCP Server (The Loadout)
**Stack:** TypeScript · Cloudflare Workers + Durable Objects · MCP SDK · Zod · workers-oauth-provider
**Files reviewed:** 7 files — `index.ts` (853 lines), `auth.ts`, `constants.ts`, `landing.ts`, `preview.ts`, `design.ts`, `ARCH.md`
**Date:** 2026-05-16

---

## Recon Summary

```
Stack:        TypeScript · Cloudflare Workers + Durable Objects (McpAgent)
              MCP SDK · Zod · @cloudflare/workers-oauth-provider · Google OAuth 2.1
AI-adjacent:  YES — MCP server exposing 17 skill tools, prompt construction in tool
              handlers, server-side HTML injection of agent-supplied JSON into live
              artifact templates
Entry points: /sse (MCP, Bearer token) · /authorize · /google/callback (OAuth)
              / · /preview · /health · /brand.css (public, no auth)
Data flow:    Claude authenticates via Google OAuth → MCP Bearer token issued →
              agent calls skill tools → tools return instruction text, bundled skill
              content, or filled HTML templates → agent writes artifacts to disk →
              WARMUP_DATA/SPOTTER_DATA injected server-side before HTML is returned
```

---

## 🔴 Critical  (0 findings)

None found.

---

## 🟠 High  (1 finding)

### `$`-sequence corruption in template injection — both `warmup_get_template` and `spotter_get_template`
**Location:** `index.ts:306–309` (warmup), `index.ts:648–651` (spotter)
**Issue:** `String.prototype.replace(literal, replacementString)` interprets `$'`, `$&`, and `` $` `` as special sequences that insert portions of the surrounding string. The replacement strings are `window.WARMUP_DATA = ${safe};` and `window.SPOTTER_DATA = ${safe};`, where `safe` is agent-supplied JSON. Any article title, body, or epic text containing `$'` (common in price strings: `"it's worth $'s in savings"`), `$&` (referencing the matched text), or `` $` `` would cause the replacement to splice in a large chunk of the template HTML instead of the intended characters — silently corrupting the output artifact.

This is a data integrity bug that would manifest unpredictably in real briefs: any brief covering financial topics, cryptocurrency, shell commands, or technical content has a meaningful chance of triggering it. The agent would receive corrupted HTML with no indication anything went wrong.

**Fix (applied):** Use a replacer function, which bypasses all `$`-sequence interpretation:
```typescript
// Before (buggy):
const filled = WARMUP_TEMPLATE_HTML.replace(PLACEHOLDER, `window.WARMUP_DATA = ${safe};`);

// After (fixed):
const filled = WARMUP_TEMPLATE_HTML.replace(PLACEHOLDER, () => `window.WARMUP_DATA = ${safe};`);
```
Applied to both `warmup_get_template` and `spotter_get_template`. **✅ Fixed in this review.**

---

## 🟡 Medium  (3 findings)

### 1. No state-cookie binding in OAuth flow — login-CSRF surface
**Location:** `auth.ts:148–179` (handleAuthorize), `auth.ts:182–263` (handleGoogleCallback)
**Issue:** The state UUID is generated, stored in KV with a 300s TTL, and sent to Google. But no cookie ties this UUID to the initiating browser session. The standard login-CSRF attack: an attacker initiates their own OAuth flow, pauses before the Google redirect, then tricks a victim's browser into hitting `/google/callback?code=ATTACKER_CODE&state=ATTACKER_STATE`. If the victim completes the flow, their Claude session gets bound to the attacker's Google account instead of their own. The attacker can then read anything returned by `loadout_whoami` or any tool that uses `this.props.email`.

The fix is one cookie: set `oauth_state=UUID; SameSite=Lax; Secure; HttpOnly; Max-Age=300` in the `/authorize` response and verify it matches the `state` query param in `/google/callback`.

**Fix:**
```typescript
// In handleAuthorize — add to redirect response:
const response = Response.redirect(googleUrl, 302);
// Set a signed state cookie matching the stateKey UUID
response.headers.set('Set-Cookie',
  `oauth_state=${stateKey}; Path=/google/callback; SameSite=Lax; Secure; HttpOnly; Max-Age=300`
);
return response;

// In handleGoogleCallback — verify before KV lookup:
const cookieHeader = request.headers.get('Cookie') ?? '';
const stateCookie = cookieHeader.split(';')
  .map(c => c.trim()).find(c => c.startsWith('oauth_state='))?.split('=')[1];
if (stateCookie !== stateKey) {
  return errorPage("State mismatch. Please try connecting again.");
}
```

### 2. Missing security headers on all HTML responses
**Location:** `auth.ts:72–84` (public routes), `auth.ts:267–289` (errorPage), `landing.ts:23–151`, `preview.ts:232+`
**Issue:** No `X-Content-Type-Options`, `X-Frame-Options`, or minimal `Content-Security-Policy` on any HTML response. If a stored XSS were introduced in the future, the absence of these headers means the browser provides no additional containment. `X-Frame-Options: DENY` specifically prevents the OAuth flow pages from being embedded in iframes (a classic clickjacking vector for login flows).
**Fix:** Add a shared headers helper and apply it to all HTML responses:
```typescript
const SECURE_HTML_HEADERS = {
  'Content-Type': 'text/html; charset=utf-8',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'same-origin',
};
```
Can also be applied globally via a Cloudflare Transform Rule without touching the Worker code.

### 3. `WARMUP_ENGINE_VERSION` not bumped for v0.3.17 template changes
**Location:** `constants.ts:15`
**Issue:** `WARMUP_ENGINE_VERSION = "v0.3.12"` but the warmup template's toolbar was significantly restructured in v0.3.17 (old `btn-save-pdf` + save modal removed; new Export ▾ dropdown + matched fullscreen button added). Agents with an existing artifact that shows `<!-- warmup-engine: v0.3.12 -->` will take Path A — targeted WARMUP_DATA block update, no template reload — meaning they'll keep using the old toolbar indefinitely. The new Export HTML / Print buttons will never reach their artifact until the engine version is bumped.
**Fix:** In `constants.ts`, bump both:
```typescript
export const WARMUP_VERSION        = "0.3.17";
export const WARMUP_ENGINE_VERSION = "v0.3.17";
```
This forces all agents to Path B on the next run, picking up the new template. Note: this will cause one slightly heavier run per user (full 131KB template download) then return to cheap Path A updates.

---

## 🟢 Low / Recommendations  (4)

### 1. `WARMUP_VERSION` constant not bumped
**Location:** `constants.ts:14`
`WARMUP_VERSION = "0.3.16"` but the Export + fullscreen changes shipped in this session are v0.3.17. Bump alongside `WARMUP_ENGINE_VERSION`. Also update the version comment in `warmup-template.html` and `SKILL.md` frontmatter if applicable.

### 2. `oauthReqInfo` parsed as `any`, not Zod-validated
**Location:** `auth.ts:198–203`
```typescript
let oauthReqInfo: any;
try {
  oauthReqInfo = JSON.parse(stored);
} catch {
  return errorPage("Corrupted auth state. Please try connecting again.");
}
```
The KV value is parsed and immediately passed to `completeAuthorization` without shape validation. KV is managed Cloudflare infrastructure so corruption is unlikely, but a Zod schema on the stored auth request would be cleaner defense and catch bugs if the serialization shape ever changes.

### 3. `spotter_build` `feature` param embedded inline without a length guard
**Location:** `index.ts:721`
`**${feature}**` is spliced directly into instruction prose. The risk is much lower than `epic`/`draft` (both already fenced and `.max(20000)` bounded) — `feature` is described as a "brief description," making multi-line injection attempts unlikely. Add `.max(200)` to the Zod schema to enforce the intent.

### 4. `print-no-dives` CSS class is inert dead code
**Location:** `warmup-template.html`, `@media print` block
The class was set by the old `buildBriefPDF` JS before the Export dropdown change. Now that `buildBriefPDF` is block-commented and the Export dropdown doesn't set this class, the `@media print` rule for `.print-no-dives` is dead. Minor cleanup — remove both the class rule and the block-commented `buildBriefPDF` function when the next bash-available session lands.

---

## ✅ Clean

Areas checked and found to be in good shape.

- **`</script>` XSS escaping:** The `.replace(/<\/script>/gi, '<\\/script>')` pattern before template injection is correct and complete. JSON.stringify output's only structural HTML injection vector inside a `<script>` tag is the literal string `</script>`. Correct.

- **Google API response validation:** Both `GoogleTokenSchema` and `GoogleUserInfoSchema` are Zod-parsed with `.safeParse()`. Failures return user-facing error pages, not panics. The access token is used transiently and discarded — not stored in KV or any persistent layer.

- **OAuth state integrity:** `crypto.randomUUID()` state key — not predictable. 300-second KV TTL — appropriate. `OAUTH_KV.delete` called immediately after retrieval — prevents replay. OAuth fields serialized explicitly (not relying on class getters) before KV storage — correct.

- **Error page HTML escaping:** `escapeHtml(message)` in `errorPage()` covers `&`, `<`, `>`, `"` — correct. Error messages are internal strings, not user-controlled. No stack traces or internal config exposed.

- **Prompt injection — spotter review/iterate:** `epic` and `draft` are fenced in code blocks (` ```\n${epic}\n``` `) and bounded with `.max(20000)` in the Zod schema. The code is ahead of what the session summary indicated.

- **`warmup_config` source sanitization:** `.replace(/[\r\n]+/g, ' ').replace(/[^\x20-\x7E]/g, '').slice(0, 120).trim()` — strips control characters, non-ASCII, and limits length before embedding in instruction prose. Correct.

- **`config_summary` in `warmup_run`:** Fenced in a code block (` ```\n${config_summary}\n``` `) and sliced to 8000 chars. Prevents adversarial WARMUP.md content from overriding agent instructions.

- **All tool parameters Zod-validated:** Every tool uses Zod schemas at the schema layer. No raw unvalidated input reaches handlers.

- **No hardcoded secrets:** All credentials (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, COOKIE_ENCRYPTION_KEY) come from Cloudflare Worker environment bindings — never in source.

- **No PII in logs:** No `console.log` with email, name, or user identity. The `loadout_whoami` tool intentionally returns identity to the authenticated agent — that's its contract.

- **`landing.ts` injection surface:** `origin` comes from `new URL(request.url).origin` — a URL-parsed value that cannot contain `<`, `>`, `"`, or other HTML special chars. `githubUrl` and `STENCIL` are compile-time constants. No user-controlled data touches the landing page HTML.

- **`preview.ts` escaping:** Custom `escape()` function applied to all variable content before HTML insertion. Static synthetic data — no user input at all.

- **Token optimization architecture:** `getSkillSection()` and `getSpotterSkillSection()` lazy-load named SKILL.md sections instead of always returning the full 90KB or 29KB document. Path A/B engine version check prevents the 131KB warmup template from being re-downloaded on every daily run. This is well-designed.

- **Injection detection:** Both `warmup_get_template` and `spotter_get_template` check `filled !== TEMPLATE` to detect placeholder-not-found and return a clear error instead of silently returning the unfilled template.

---

## Architecture Diagram
Saved to `ARCH.md`. Shows the full data flow from OAuth through MCP tool dispatch, the build-time bundle structure, the Path A/B template optimization loop, and a token/cost table by tool.

---

## Fix Plan

**P0 — Applied in this review:**
1. `index.ts:308` — Replacer function for `warmup_get_template` — prevents `$`-sequence corruption ✅
2. `index.ts:651` — Replacer function for `spotter_get_template` — same fix ✅

**P1 — Before next deploy:**
1. `constants.ts:14–15` — Bump `WARMUP_VERSION` to `"0.3.17"` and `WARMUP_ENGINE_VERSION` to `"v0.3.17"` — required for agents to pick up the new toolbar
2. `auth.ts:179, 188–190` — Add state-cookie binding to `/authorize` response and verification in `/google/callback`

**P2 — Next sprint:**
1. `auth.ts:198` — Zod-validate `oauthReqInfo` after `JSON.parse`
2. `index.ts:713` — Add `.max(200)` to `spotter_build` `feature` param
3. All HTML responses — Add `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` headers (or configure via Cloudflare Transform Rule)
4. `warmup-template.html` — Delete block-commented `buildBriefPDF` function when bash is available; remove inert `print-no-dives` CSS rule

---

## Seal of Approval

**This codebase is ready to ship once P1 items are addressed.** The P0 `$`-sequence fix is applied. The version bump (`WARMUP_VERSION` + `WARMUP_ENGINE_VERSION`) must go out before deploy to force agents onto the new toolbar. The state-cookie fix is the right thing to do before this server sees meaningful traffic. Everything else is maintenance.

The core architecture is solid — build-time bundling, server-side injection, section lazy-loading, Path A/B engine versioning, Zod validation throughout, clean OAuth state management. No secrets in source, no PII in logs, no XSS vectors found.
