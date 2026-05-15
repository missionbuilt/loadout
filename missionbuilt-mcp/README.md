# missionbuilt-mcp

The unified MCP server for The Loadout — exposes The Warmup and The Spotter through a single OAuth-protected endpoint at `mcp.missionbuilt.io`.

**14 tools. 2 skills. 1 connection.**

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
| `warmup_get_skill` | Returns the full Warmup SKILL.md framework |
| `warmup_list_modes` | Returns the three modes with section descriptions |
| `warmup_get_template` | Returns the canonical Iron Log HTML engine |
| `warmup_setup` | Primes the agent to run the setup flow |
| `warmup_run` | Primes the agent to generate a brief |
| `warmup_config` | Primes the agent to manage sources |

### The Spotter

| Tool | Description |
|---|---|
| `spotter_get_skill` | Returns the full Spotter SKILL.md framework |
| `spotter_list_lenses` | Returns the nine lenses with weight notes |
| `spotter_get_examples` | Returns 64 worked lens examples with teaching notes |
| `spotter_get_calibration_epic` | Returns the synthetic calibration epic |
| `spotter_review` | Primes the agent to review an epic |
| `spotter_build` | Primes the agent to build an epic from scratch |
| `spotter_iterate` | Primes the agent to push a partial draft forward |

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

Skill content lives in `src/skill-content/` and is bundled at build time via Wrangler text imports. Canonical sources are the editorial directories — always edit there, then sync:

```bash
# After editing warmup/SKILL.md or warmup/warmup-template.html:
cp warmup/SKILL.md missionbuilt-mcp/src/skill-content/warmup/SKILL.md
cp warmup/warmup-template.html missionbuilt-mcp/src/skill-content/warmup/warmup-template.html

# After editing spotter/SKILL.md or spotter/examples/:
cp spotter/SKILL.md missionbuilt-mcp/src/skill-content/spotter/SKILL.md
cp spotter/examples/lens-examples.md missionbuilt-mcp/src/skill-content/spotter/lens-examples.md
```

---

## License

MIT — see [LICENSE](../LICENSE).
