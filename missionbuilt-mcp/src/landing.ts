/**
 * Landing page for the Mission Built MCP server.
 *
 * Status / connection page for users who hit the root URL directly while
 * configuring an MCP client. Not marketing — the marketing surface is
 * missionbuilt.io. This page tells you what this server is, how to connect,
 * and what tools it exposes.
 */

import { brandCss, STENCIL } from "./design";

interface LandingArgs {
  origin: string;
  githubUrl: string;
  serverVersion: string;
  stencil: string;
}

export function renderLanding(args: LandingArgs): string {
  const { origin, githubUrl, serverVersion } = args;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#171513">
  <title>Mission Built · MCP Server</title>
  <meta name="description" content="The Mission Built MCP server — The Warmup and The Spotter. Daily intelligence briefs and product epic reviews for operators who do the work.">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="manifest" href="/site.webmanifest">
  <style>${brandCss()}</style>
</head>
<body>
  <div class="mb-container">

    <p class="mb-stencil"><span class="mb-stencil-bars">${STENCIL}</span> An open-source skill suite from Mission Built <span class="mb-stencil-bars">${STENCIL}</span></p>

    <h1 class="mb-hero">The Loadout<span class="mb-hero-period">.</span></h1>

    <p class="mb-tagline">Two skills. One server. Know what moved before you open your inbox. Know if your epic is ready before you commit the team.</p>

    <div class="mb-meta-row">
      <div>Server <strong>v${serverVersion}</strong></div>
      <div>Skills <strong>2</strong></div>
      <div>Tools <strong>14</strong></div>
      <div>License <strong>MIT</strong></div>
      <div>Status <strong style="color: #92a844;">Online</strong></div>
    </div>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Connect</p>
      <h2 class="mb-h2">One endpoint. Both skills.</h2>

      <h3 class="mb-h3">Claude Code</h3>
      <pre class="mb-pre"><code>claude mcp add loadout ${origin}/sse</code></pre>

      <h3 class="mb-h3">Claude Desktop</h3>
      <p class="mb-p">Add to <code class="mb-code">claude_desktop_config.json</code>:</p>
      <pre class="mb-pre"><code>{
  "mcpServers": {
    "loadout": {
      "url": "${origin}/sse"
    }
  }
}</code></pre>

      <h3 class="mb-h3">Transports</h3>
      <ul class="mb-tool-list" style="margin-top: 0.5rem;">
        <li><code>${origin}/sse</code><span>Server-Sent Events (most common)</span></li>
        <li><code>${origin}/mcp</code><span>Streamable HTTP (newer clients)</span></li>
      </ul>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">The Warmup</p>
      <h2 class="mb-h2">Know what moved. Then go move things.</h2>
      <p class="mb-p">A daily intelligence brief for the first coffee. Three modes — CISO, Product Leader, Custom — each pulling from a curated source suite, running link safety verification, and rendering into a live artifact. One summary line in chat. The brief is the artifact.</p>
      <p class="mb-p">First time? Say <em>warmup setup</em>. Every day after that, say <em>run warmup</em>.</p>

      <ul class="mb-tool-list">
        <li><code>warmup_get_skill</code><span>Returns the full SKILL.md framework</span></li>
        <li><code>warmup_list_modes</code><span>Returns the three modes with section descriptions</span></li>
        <li><code>warmup_get_template</code><span>Returns the canonical Iron Log HTML engine for brief rendering</span></li>
        <li><code>warmup_setup</code><span>Primes the agent to run the setup flow</span></li>
        <li><code>warmup_run</code><span>Primes the agent to generate the brief</span></li>
        <li><code>warmup_config</code><span>Primes the agent to manage sources (add / remove / exclude)</span></li>
      </ul>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">The Spotter</p>
      <h2 class="mb-h2">Nine lenses. One verdict. No hiding.</h2>
      <p class="mb-p">A structured review framework for B2B product epics. Nine lenses — from user empathy to trust and governance — each graded ✓ / ⚠️ / ✗. Lens 1 is the foundation. Lens 9 is the gate. The output is a verdict, a set of targeted flags, and an offer to work through every gap.</p>
      <p class="mb-p">Paste an epic and say <em>run the spotter</em>. Or start from scratch with <em>help me build an epic for [feature]</em>.</p>

      <ul class="mb-tool-list">
        <li><code>spotter_get_skill</code><span>Returns the full SKILL.md framework</span></li>
        <li><code>spotter_list_lenses</code><span>Returns the nine lenses with weight notes</span></li>
        <li><code>spotter_get_examples</code><span>Returns 64 worked examples with teaching notes</span></li>
        <li><code>spotter_get_calibration_epic</code><span>Returns the synthetic calibration epic</span></li>
        <li><code>spotter_review</code><span>Primes the agent to review an epic</span></li>
        <li><code>spotter_build</code><span>Primes the agent to build an epic from scratch</span></li>
        <li><code>spotter_iterate</code><span>Primes the agent to push a draft forward</span></li>
      </ul>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Shared tools</p>
      <h2 class="mb-h2">One identity. One design system.</h2>
      <ul class="mb-tool-list">
        <li><code>loadout_whoami</code><span>Returns the authenticated user's name and email</span></li>
        <li><code>loadout_get_brand_css</code><span>Returns the Mission Built design CSS</span></li>
      </ul>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Your config</p>
      <h2 class="mb-h2">Config stays on your machine.</h2>
      <p class="mb-p">The Warmup reads your profile, sources, and interests from <code class="mb-code">WARMUP.md</code> at your project root — gitignored, never leaves your machine. Copy <code class="mb-code">WARMUP.example.md</code> from the repo to see the schema, or say <em>warmup setup</em> and the skill writes it for you.</p>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Open source</p>
      <h2 class="mb-h2">Take it. Fork it. Lift others with it.</h2>
      <p class="mb-p">The Loadout ships under MIT. Use it commercially, adapt it for your team, embed it in your own product. Source lives in <a class="mb-link" href="${githubUrl}">The Loadout repo on GitHub</a>.</p>
    </section>

    <div class="mb-footer">
      <p class="mb-footer-line">Real strength is lifting others.</p>
      <p>Part of <a href="https://missionbuilt.io">Mission Built</a> · Source on <a href="${githubUrl}">GitHub</a> · MIT licensed</p>
    </div>

  </div>
</body>
</html>`;
}
