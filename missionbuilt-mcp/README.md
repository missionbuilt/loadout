# missionbuilt-mcp

The unified MCP server for The Loadout — exposes The Warmup, The Spotter, and The Approach through a single OAuth-protected endpoint at `mcp.missionbuilt.io`.

**18 tools. 3 skills. 1 connection.**

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
| `warmup_list_modes` | Returns the three modes with section descriptions |
| `warmup_get_template` | Injects your WARMUP_DATA into the self-contained brief and returns it in paginated chunks (fonts baked in) |
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
| `spotter_get_template` | Injects your SPOTTER_DATA into the self-contained worksheet and returns it in paginated chunks (fonts baked in) |
| `spotter_run` | Primes the agent to review an epic and render the worksheet |

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

The MCP server serves its skill content from `src/skill-content/{warmup,spotter,the-approach}/`, bundled at build time via Wrangler text imports. **Edit those files directly** — they are the source of truth for what the server ships to agents.

This repo also carries a second, *standalone* edition of each skill in the editorial directories at the loadout repo root (`warmup/`, `spotter/`, `the-approach/`). Those are the self-contained, downloadable skills — they render locally via `scripts/inject.py` with no MCP server. The two editions are **intentionally not identical**: a standalone `SKILL.md` references local rendering and on-disk files, while the bundled `SKILL.md` references MCP tools. Do **not** blindly `cp` between them — port changes by hand, and keep only the genuinely shared content (the worked examples in `area-examples.md`, the HTML templates) in step.

**Warmup:** The runtime is the self-contained `src/skill-content/warmup/warmup-template.html` (fonts baked, `__WARMUP_DATA__` placeholder). `warmup_get_template` injects your data at request time and chunks the result — no KV, no font tool, and no runtime calls from the rendered brief. Bump `WARMUP_ENGINE_VERSION` in `constants.ts` after any template change.

**Spotter:** As of v1.0, The Spotter produces a fully interactive worksheet artifact rather than text output. The template lives at `src/skill-content/spotter/spotter-template.html` — edit it directly (no canonical/bundled split). Worked examples live in `src/skill-content/spotter/area-examples.md`. Bump `SPOTTER_VERSION` in `constants.ts` after any template or SKILL.md change.

**The Approach:** Template lives at `src/skill-content/the-approach/approach-template.html`. Bump `THE_APPROACH_VERSION` in `constants.ts` after any template or SKILL.md change.

---

## License

MIT — see [LICENSE](../LICENSE).
