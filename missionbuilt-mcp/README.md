# missionbuilt-mcp

The unified MCP server for The Loadout — exposes The Warmup, The Spotter, and The Approach through a single OAuth-protected endpoint at `mcp.missionbuilt.io`.

**23 tools. 3 skills. 1 connection.**

---

## Tools

### Shared

| Tool | Description |
|---|---|
| `loadout_whoami` | Returns the authenticated user's name and email |
| `loadout_get_brand_css` | Returns the Mission Built design CSS |

### The Warmup

| Tool | Description |
|---|---|
| `warmup_get_skill` | Returns a section of the Warmup SKILL.md (use `section` param to load only what you need) |
| `warmup_get_fonts` | Returns font CSS for the artifact sandbox (cached in localStorage after first load) |
| `warmup_list_modes` | Returns the three modes with section descriptions |
| `warmup_get_template` | Returns the warmup artifact HTML in paginated chunks |
| `warmup_save_data` | Stores the user's WARMUP_DATA brief in KV (artifact auto-refreshes on next open) |
| `warmup_get_data` | Returns the user's latest WARMUP_DATA brief from KV |
| `warmup_setup` | Primes the agent to run the first-time setup flow |
| `warmup_run` | Primes the agent to fetch intelligence and generate a brief |
| `warmup_config` | Primes the agent to manage sources in WARMUP.md |

### The Spotter

| Tool | Description |
|---|---|
| `spotter_get_skill` | Returns a section of the Spotter SKILL.md (use `section` param to load only what you need) |
| `spotter_list_areas` | Returns the nine review areas with names and weight notes |
| `spotter_get_examples` | Returns worked area examples (strong, needs-work, missing) with teaching notes |
| `spotter_get_calibration_epic` | Returns synthetic calibration epic #1 (gap-heavy — target verdict: Needs polish) |
| `spotter_get_calibration_epics` | Returns all three synthetic calibration epics for batch grading range tests |
| `spotter_get_template` | Returns the v1.0 worksheet HTML with SPOTTER_DATA injected — write to disk, pass to artifact |
| `spotter_review` | Primes the agent to review an epic and produce a worksheet |
| `spotter_build` | Primes the agent to build an epic from scratch |
| `spotter_iterate` | Primes the agent to push a partial draft forward |

### The Approach

| Tool | Description |
|---|---|
| `approach_get_skill` | Returns the Approach SKILL.md — run flow, schema, output format |
| `approach_get_template` | Returns the Approach artifact HTML with APPROACH_DATA injected |
| `approach_run` | Primes the agent to research an account and produce a pre-meeting brief |

---

## Connect

### Claude Code

```bash
claude mcp add loadout https://mcp.missionbuilt.io/sse
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "loadout": {
      "url": "https://mcp.missionbuilt.io/sse"
    }
  }
}
```

---

## Deploy your own instance

### Prerequisites

- Cloudflare account with `mcp.yourdomain.com` pointed to Cloudflare DNS
- Google Cloud project with an OAuth 2.1 client configured
- Node.js 18+ and `wrangler` CLI

### 1. Install dependencies

```bash
cd missionbuilt-mcp
npm install
```

### 2. Create the KV namespace

```bash
npx wrangler kv namespace create OAUTH_KV
```

Paste the returned `id` into `wrangler.toml` under `[[kv_namespaces]]`.

### 3. Configure Google OAuth

In [Google Cloud Console](https://console.cloud.google.com/):

1. Create an OAuth 2.0 Client ID (Web application)
2. Add authorized redirect URI: `https://mcp.yourdomain.com/google/callback`
3. Copy the client ID and secret

### 4. Set secrets

```bash
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put COOKIE_ENCRYPTION_KEY   # any random 32-char string
```

### 5. Update wrangler.toml

Set the `pattern` under `[[routes]]` to your domain:

```toml
[[routes]]
pattern = "mcp.yourdomain.com"
custom_domain = true
```

### 6. Deploy

```bash
npx wrangler deploy
```

---

## Development

```bash
npm run dev        # local dev server
npm run typecheck  # TypeScript check without build
npm run deploy     # deploy to Cloudflare
```

---

## Retiring old servers

If you previously ran `warmup-mcp` or `spotter-mcp` as separate Cloudflare Workers, retire them after deploying this unified server:

```bash
# In each old directory (before deleting them)
npx wrangler delete --name warmup-mcp
npx wrangler delete --name spotter-mcp
```

Remove the old DNS entries (`warmup-mcp.missionbuilt.io`, `spotter-mcp.missionbuilt.io`) from your Cloudflare dashboard. Delete the old Google OAuth clients (or remove their redirect URIs) from Google Cloud Console.

---

## Skill content

Skill content lives in `src/skill-content/` and is bundled at build time via Wrangler text imports. Canonical SKILL.md copies sit in the editorial directories — always edit there first, then sync:

```bash
# After editing warmup/SKILL.md:
cp warmup/SKILL.md missionbuilt-mcp/src/skill-content/warmup/SKILL.md

# After editing spotter/SKILL.md or spotter/examples/:
cp spotter/SKILL.md missionbuilt-mcp/src/skill-content/spotter/SKILL.md
cp spotter/examples/area-examples.md missionbuilt-mcp/src/skill-content/spotter/area-examples.md

# After editing the-approach/SKILL.md:
cp the-approach/SKILL.md missionbuilt-mcp/src/skill-content/approach/SKILL.md
```

**Warmup:** The runtime is `src/warmup-shell.rawjs` (no canonical/bundled split). Edit and bump `WARMUP_ENGINE_VERSION` in `constants.ts` so users pick up the new shell on their next run. Warmup data flows through `warmup_save_data` → KV → `warmup_get_data`; the artifact is a pure renderer with no inline data.

**Spotter:** As of v1.0, The Spotter produces a fully interactive worksheet artifact rather than text output. The template lives at `src/skill-content/spotter/spotter-template.html` — edit it directly (no canonical/bundled split). Bump `SPOTTER_VERSION` in `constants.ts` after any template or SKILL.md change.

**The Approach:** Template lives at `src/skill-content/approach/approach-template.html`. Bump `THE_APPROACH_VERSION` in `constants.ts` after any template or SKILL.md change.

---

## License

MIT — see [LICENSE](../LICENSE).
