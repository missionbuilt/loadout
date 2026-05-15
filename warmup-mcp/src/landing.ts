/**
 * Landing page renderer for The Warmup MCP server.
 *
 * Status / connection page for users who hit the root URL directly while
 * configuring an MCP client. Not marketing — the marketing surface is
 * missionbuilt.io/loadout/warmup. This page tells you what this server is,
 * how to connect, and what tools it exposes.
 */

import { brandCss, STENCIL } from "./design";

interface LandingArgs {
  origin: string;
  githubUrl: string;
  warmupVersion: string;
  serverVersion: string;
  stencil: string;
}

export function renderLanding(args: LandingArgs): string {
  const { origin, githubUrl, warmupVersion, serverVersion } = args;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#171513">
  <title>The Warmup · MCP Server</title>
  <meta name="description" content="Hosted MCP server for The Warmup — a daily intelligence brief skill. Part of The Loadout, from the Mission Built ecosystem.">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <style>${brandCss()}</style>
</head>
<body>
  <div class="mb-container">

    <p class="mb-stencil"><span class="mb-stencil-bars">${STENCIL}</span> An open-source skill from Mission Built <span class="mb-stencil-bars">${STENCIL}</span></p>

    <h1 class="mb-hero">The Warmup<span class="mb-hero-period">.</span></h1>

    <p class="mb-tagline">A daily intelligence brief for the first coffee. Know what moved before you open your inbox.</p>

    <div class="mb-meta-row">
      <div>The Warmup <strong>v${warmupVersion}</strong></div>
      <div>Server <strong>v${serverVersion}</strong></div>
      <div>Modes <strong>3</strong></div>
      <div>Sections <strong>5</strong></div>
      <div>License <strong>MIT</strong></div>
      <div>Status <strong style="color: #7a8b3a;">Online</strong></div>
    </div>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">What this is</p>
      <h2 class="mb-h2">Know what moved. Then go move things.</h2>
      <p class="mb-p">You do not go under the bar cold. In the gym, the warmup is the ten minutes that makes the next ninety honest. It tells you what is tight, what needs adjustment, and whether today's plan needs to change before the work begins.</p>
      <p class="mb-p">This skill does the same thing for your workday. Before the first meeting, before the first decision — you know what threat actors are active, what vulnerabilities dropped overnight, what your competitors announced, what your vendors are doing. You start informed instead of catching up for the first hour.</p>
      <p class="mb-p">Three modes: <strong>CISO Mode</strong> for cybersecurity executives, <strong>Product Leader Mode</strong> for PMs and CPOs, <strong>Custom Mode</strong> for anyone with a specific set of sources they want to watch. Every brief includes link safety verification — each URL is scanned before the brief renders.</p>
      <p class="mb-p"><a class="mb-link" href="${origin}/preview">See what a Warmup brief looks like →</a></p>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Connect</p>
      <h2 class="mb-h2">Plug The Warmup into your agent.</h2>

      <h3 class="mb-h3">Claude Code</h3>
      <pre class="mb-pre"><code>claude mcp add warmup ${origin}/sse</code></pre>

      <h3 class="mb-h3">Claude Desktop</h3>
      <p class="mb-p">Add to <code class="mb-code">claude_desktop_config.json</code>:</p>
      <pre class="mb-pre"><code>{
  "mcpServers": {
    "warmup": {
      "url": "${origin}/sse"
    }
  }
}</code></pre>

      <h3 class="mb-h3">Other MCP clients</h3>
      <ul class="mb-tool-list" style="margin-top: 0.5rem;">
        <li><code>${origin}/sse</code><span>Server-Sent Events transport (most common)</span></li>
        <li><code>${origin}/mcp</code><span>Streamable HTTP transport (newer)</span></li>
      </ul>

      <p class="mb-p" style="margin-top: 1rem;">First time? Run <em>warmup setup</em> to configure your profile, build your source suite, and save your config. Then say <em>run warmup</em> or <em>start my warmup</em> each day.</p>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Tools exposed</p>
      <h2 class="mb-h2">Seven tools, two resources.</h2>
      <ul class="mb-tool-list">
        <li><code>warmup_get_skill</code><span>Returns the full SKILL.md framework</span></li>
        <li><code>warmup_list_modes</code><span>Returns the three modes with section descriptions</span></li>
        <li><code>warmup_get_brand_css</code><span>Returns the Mission Built design CSS</span></li>
        <li><code>warmup_get_template</code><span>Returns the canonical Iron Log HTML engine for brief rendering</span></li>
        <li><code>warmup_whoami</code><span>Returns the authenticated user's identity</span></li>
        <li><code>warmup_setup</code><span>Primes the agent to run the setup flow</span></li>
        <li><code>warmup_run</code><span>Primes the agent to generate the brief</span></li>
        <li><code>warmup_config</code><span>Primes the agent to manage sources (add / remove / exclude)</span></li>
      </ul>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Your config</p>
      <h2 class="mb-h2">WARMUP.md stays on your machine.</h2>
      <p class="mb-p">Your profile, sources, and interests live in a plain <code class="mb-code">WARMUP.md</code> at your project root. It's gitignored and never leaves your machine. The server provides the framework; your config is yours.</p>
      <p class="mb-p">Copy <code class="mb-code">WARMUP.example.md</code> from the repo root to see the full schema. Run <em>warmup setup</em> the first time and the skill writes the file for you.</p>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Open source</p>
      <h2 class="mb-h2">Take it. Fork it. Lift others with it.</h2>
      <p class="mb-p">The Warmup ships under MIT. Use it commercially, adapt it for your team, embed it in your own product. The skill markdown and the source for this MCP server live in <a class="mb-link" href="${githubUrl}">The Loadout repo on GitHub</a>.</p>
      <p class="mb-p">Customize for your team by adding a <code class="mb-code">CLAUDE.md</code> at your project root with your company, sector, and competitor context. The skill stays generic. Your context stays local.</p>
    </section>

    <div class="mb-footer">
      <p class="mb-footer-line">Know what moved. Then go move things.</p>
      <p>Part of <a href="https://missionbuilt.io">Mission Built</a> · Source on <a href="${githubUrl}">GitHub</a> · MIT licensed · The book teaches the principles. The Loadout puts them into operation.</p>
    </div>

  </div>
</body>
</html>`;
}
