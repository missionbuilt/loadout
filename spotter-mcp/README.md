# The Spotter — MCP Server

A hosted Model Context Protocol (MCP) server that exposes **[The Spotter](https://github.com/missionbuilt/loadout/tree/main/spotter)** — an open-source skill for reviewing, building, and iterating on B2B product epics — to any MCP-compatible agent.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Part of [The Loadout](https://github.com/missionbuilt/loadout) · From the [*Mission Built*](https://missionbuilt.io) ecosystem.

---

## What this is

The Spotter ships as a markdown skill in [The Loadout](https://github.com/missionbuilt/loadout/tree/main/spotter). That works great when users have local file access (Claude Code, Cowork, Cursor). For other agents — Claude Desktop, ChatGPT MCP, custom clients — a hosted MCP server is the cleanest distribution path.

This server:

- Hosts on **Cloudflare Workers** (free tier, no payment method required)
- Exposes The Spotter's framework, examples, and calibration content via standard MCP tools and resources
- Supports both **SSE** and **Streamable HTTP** transports
- Bundles `SKILL.md`, `lens-examples.md`, and the synthetic test epic at build time so the server is fully self-contained

The server doesn't *do* the review — the agent does the reasoning. The server's job is to deliver the framework with high fidelity so any MCP client can apply The Spotter's lenses without installing the markdown skill locally.

## Connect to the hosted server

If you're connecting to the canonical instance hosted by Mission Built:

**Claude Code:**

```bash
claude mcp add spotter https://spotter-mcp.missionbuilt.io/sse
```

(Replace with your custom domain if you've bound one — e.g., `https://spotter-mcp.missionbuilt.io/sse`.)

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spotter": {
      "url": "https://spotter-mcp.missionbuilt.io/sse"
    }
  }
}
```

**Other MCP clients:** point them at the SSE endpoint or the Streamable HTTP endpoint:

- SSE: `https://spotter-mcp.missionbuilt.io/sse`
- Streamable HTTP: `https://spotter-mcp.missionbuilt.io/mcp`

Once connected, ask your agent to *"run the spotter on this epic"* (after pasting an epic) and the server will provide the framework.

## What the server exposes

### Tools

| Tool | What it does |
|---|---|
| `spotter_get_skill` | Returns the full SKILL.md content — framework, modes, nine lenses, sub-checks, output formats |
| `spotter_get_examples` | Returns 64 worked examples across the nine lenses with teaching notes |
| `spotter_get_calibration_epic` | Returns a synthetic B2B security epic for verifying the skill is calibrated correctly |
| `spotter_list_lenses` | Lightweight list of the nine lenses (good for clients that render lens cards) |
| `spotter_review` | Primes the agent to review a pasted epic in review mode |
| `spotter_build` | Primes the agent to walk a PM through building a new epic |
| `spotter_iterate` | Primes the agent to push a partial draft forward |

### Resources

- `spotter://skill` — full SKILL.md
- `spotter://examples` — full lens-examples.md
- `spotter://calibration-epic` — synthetic test epic

## Deploy your own instance

The whole thing runs on Cloudflare Workers' free tier. You don't need to add a payment method — without one, the platform structurally cannot bill you. If you exceed the free tier (100,000 requests/day), the server returns errors instead of incurring charges.

### Prerequisites

- A Cloudflare account ([dash.cloudflare.com](https://dash.cloudflare.com) — free)
- Node.js 18 or later installed locally
- The Wrangler CLI (Cloudflare's deploy tool)

### One-time setup

```bash
# Clone the Loadout repo and navigate to this server
git clone https://github.com/missionbuilt/loadout.git
cd loadout/spotter-mcp

# Install dependencies
npm install

# Authenticate Wrangler with your Cloudflare account
npx wrangler login
```

### Deploy

```bash
npx wrangler deploy
```

That's it. Wrangler will print the deployment URL — usually `https://spotter-mcp.<your-subdomain>.workers.dev`. The server is now live.

### Verify

Visit the deployment URL in a browser. You should see a landing page with connection instructions and the list of tools/resources the server exposes.

The `/health` endpoint returns JSON status:

```bash
curl https://your-deployment.workers.dev/health
```

### Connect a custom domain (optional)

If you own a domain (e.g., `missionbuilt.io`), you can bind a custom subdomain like `spotter.mcp.missionbuilt.io`:

1. Add your domain to Cloudflare (if not already managed there)
2. Uncomment the `[[routes]]` block in `wrangler.toml` and adjust the `pattern`
3. Run `npx wrangler deploy` again

Cloudflare will provision SSL automatically.

### Updating the skill content

When the canonical Spotter skill in `loadout/spotter/` is updated:

```bash
cd loadout/spotter-mcp/src/skill-content
cp ../../../spotter/SKILL.md SKILL.md
cp ../../../spotter/examples/lens-examples.md lens-examples.md
cp ../../../spotter/examples/synthetic-epic.md synthetic-epic.md
cd ..
npx wrangler deploy
```

The bundled markdown is embedded at build time, so a redeploy is required to pick up updates.

## Local development

To run the server locally for development:

```bash
npx wrangler dev
```

The dev server will start on `http://localhost:8787`. You can connect a local MCP client to `http://localhost:8787/sse`.

To tail production logs:

```bash
npx wrangler tail
```

## Costs

Free, with a structural guarantee:

- **Cloudflare Workers Free tier**: 100,000 requests/day, no cold starts, no sleep
- **No payment method required** — the platform cannot bill an account without billing info on file
- **No Anthropic API costs** — the server doesn't call Claude. The agent connecting to the server makes its own Claude calls and pays for those itself

For a personal or community-scale project, you'll never approach the free-tier limits. The server returns mostly-static markdown content; compute is minimal.

## License

MIT. See [LICENSE](LICENSE) at the repo root. Use it commercially, fork it, modify it, embed it. Attribution preserved per the MIT terms is appreciated.

## Spirit

The Spotter is offered freely. If a hosted instance makes your work better, pay it forward by contributing back, by sharing what you learn, by lifting the PMs around you.

*Real strength is lifting others.*

— Mike
