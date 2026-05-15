/**
 * Landing page renderer for the MCP server.
 *
 * Visitors who hit the server's root URL see this page. Designed to match
 * missionbuilt.io's aesthetic — warm dark base, editorial serif hero,
 * stencil decoration, restrained field-guide voice.
 */

import { brandCss, STENCIL } from "./design";

interface LandingArgs {
  origin: string;
  githubUrl: string;
  spotterVersion: string;
  serverVersion: string;
  stencil: string;
}

export function renderLanding(args: LandingArgs): string {
  const { origin, githubUrl, spotterVersion, serverVersion } = args;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#171513">
  <title>The Spotter · MCP Server</title>
  <meta name="description" content="Hosted MCP server for The Spotter — an open-source skill for B2B product epic review. Part of The Loadout, from the Mission Built ecosystem.">
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

    <h1 class="mb-hero">The Spotter<span class="mb-hero-period">.</span></h1>

    <p class="mb-tagline">A skill for reviewing, building, and iterating on B2B product epics. Hosted as an MCP server for any agent that wants the framework.</p>

    <div class="mb-meta-row">
      <div>The Spotter <strong>v${spotterVersion}</strong></div>
      <div>Server <strong>v${serverVersion}</strong></div>
      <div>Lenses <strong>9</strong></div>
      <div>Examples <strong>64</strong></div>
      <div>License <strong>MIT</strong></div>
    </div>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">What this is</p>
      <h2 class="mb-h2">A second pair of eyes that lifts the work.</h2>
      <p class="mb-p">A spotter in powerlifting watches your form, catches the bar if something breaks down, and gives you the confidence to attempt a lift you couldn't safely attempt alone. They lift <em>you</em>, not the bar.</p>
      <p class="mb-p">This skill does the same for an epic. It walks the work through nine product-leadership lenses — empathy, competitive landscape, strategic differentiation, solution approach, holistic impact, packaging, launch readiness, post-launch ownership, and trust/governance/auditability — and produces structured feedback in the <em>critique-not-criticism</em> tradition. Every flag is "you could strengthen this by..." Never "you missed."</p>
      <p class="mb-p">The PM still owns the lift. The Spotter is just there to lift them.</p>
      <p class="mb-p"><a class="mb-link" href="${origin}/preview">See what a Spotter review looks like →</a></p>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Connect</p>
      <h2 class="mb-h2">Plug The Spotter into your agent.</h2>

      <h3 class="mb-h3">Claude Code</h3>
      <pre class="mb-pre"><code>claude mcp add spotter ${origin}/sse</code></pre>

      <h3 class="mb-h3">Claude Desktop</h3>
      <p class="mb-p">Add to <code class="mb-code">claude_desktop_config.json</code>:</p>
      <pre class="mb-pre"><code>{
  "mcpServers": {
    "spotter": {
      "url": "${origin}/sse"
    }
  }
}</code></pre>

      <h3 class="mb-h3">Other MCP clients</h3>
      <ul class="mb-tool-list" style="margin-top: 0.5rem;">
        <li><code>${origin}/sse</code><span>Server-Sent Events transport (most common)</span></li>
        <li><code>${origin}/mcp</code><span>Streamable HTTP transport (newer)</span></li>
      </ul>
      <p class="mb-p" style="margin-top: 1rem;">Once connected, ask your agent: <em>"run the spotter on this epic"</em> and paste an epic. The framework loads from this server; your agent does the reasoning.</p>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Tools exposed</p>
      <h2 class="mb-h2">Seven tools, three resources.</h2>
      <ul class="mb-tool-list">
        <li><code>spotter_get_skill</code><span>Returns the full SKILL.md framework</span></li>
        <li><code>spotter_get_examples</code><span>Returns 64 worked lens examples</span></li>
        <li><code>spotter_get_calibration_epic</code><span>Returns the synthetic test epic</span></li>
        <li><code>spotter_list_lenses</code><span>Returns the nine lenses with weights</span></li>
        <li><code>spotter_get_brand_css</code><span>Returns the Mission Built design CSS</span></li>
        <li><code>spotter_review</code><span>Primes review mode on a pasted epic</span></li>
        <li><code>spotter_build</code><span>Primes build mode for a new epic</span></li>
        <li><code>spotter_iterate</code><span>Primes iterate mode on a draft</span></li>
      </ul>
    </section>

    <hr class="mb-divider">

    <section class="mb-section">
      <p class="mb-section-label">Open source</p>
      <h2 class="mb-h2">Take it. Fork it. Lift others with it.</h2>
      <p class="mb-p">The Spotter ships under MIT. Use it commercially, adapt it for your team, embed it in your own product. The skill markdown is in <a class="mb-link" href="${githubUrl}">The Loadout repo on GitHub</a> alongside the source for this MCP server. Full attribution to the open-source skills and product writers whose thinking informed it lives in <code class="mb-code">spotter/ATTRIBUTION.md</code>.</p>
      <p class="mb-p">Customize for your team by adding a <code class="mb-code">CLAUDE.md</code> at your project root with your tier names, competitor set, and product taxonomy. The skill stays generic; your context stays local.</p>
    </section>

    <div class="mb-footer">
      <p class="mb-footer-line">Real strength is lifting others.</p>
      <p>Part of <a href="https://missionbuilt.io">Mission Built</a> · Source on <a href="${githubUrl}">GitHub</a> · MIT licensed · The book teaches the principles. The Loadout puts them into operation.</p>
    </div>

  </div>
</body>
</html>`;
}
