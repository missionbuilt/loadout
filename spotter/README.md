# The Spotter

A Claude Code / Cowork / agent-compatible skill for reviewing, building, and iterating on B2B product epics.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

By [H. Michael Nichols](https://www.linkedin.com/in/hmichaelnichols) · Part of [The Loadout](https://missionbuilt.io) — open-source product leadership skills from the [*Mission Built*](https://missionbuilt.io) ecosystem.

---

## What this is

The Spotter walks an epic through nine product-leadership areas — user and problem, competitive landscape, strategic differentiation, solution approach (with explicit AI decisions), holistic impact, packaging and pricing, launch readiness, post-launch ownership, and trust, governance, and auditability — and produces a structured, interactive worksheet in the *critique-not-criticism* tradition.

The output is a live HTML artifact. Each area shows the relevant excerpt from your epic alongside per-note feedback — typed as *missing*, *suggest*, *recommend*, or *observation*. You accept or skip individual notes, carry accepted ones as context into a refine pass, and watch the worksheet close area by area as you work through it. When all areas are closed, the export unlocks.

Three modes for different entry points:

- **Review mode** — paste your epic, get a fully populated worksheet with per-area critiques, one click away from iterating on any area.
- **Build mode** — guided creation from scratch, area by area. Output is a polished draft epic.
- **Iterate mode** — push a partial draft further, one area at a time, with coaching questions to surface gaps you haven't hit yet.

The orientation throughout: every gap is framed as *"you could strengthen this by..."* — never *"you missed."*

## Why "The Spotter"

In powerlifting, a spotter stands behind you when you go for a heavy set. Their job isn't to lift the weight. It's to watch your form, catch the bar if something breaks down, and give you the confidence to attempt a lift you couldn't safely attempt alone. They lift *you*, not the bar.

This skill does the same for an epic. It doesn't write the epic for the PM. It watches the work, catches the failure modes, and gives the PM the confidence to push the draft further than they'd push alone. The PM still owns the lift.

The name comes from *Mission Built*, where the closing principle is *real strength is lifting others.* The Spotter is that principle in operation.

## Why this exists

Most PM-skill libraries focus on PM outputs: competitive teardowns, customer interview synthesis, NPS analyses, status updates. None of them — including the strongest ones from Aakash Gupta, Sachin Rekhi, and the product-on-purpose collection — have a leadership-grade epic review framework.

Epic review is a leverage moment. Every epic that gets reviewed touches a roadmap, a team, customers, dollars. Systematizing the criteria does three things:

1. **Raises the floor** for every PM on the team.
2. **Teaches the criteria** by example — over time, PMs internalize the framework and stop submitting weaker drafts.
3. **Scales coaching**, not just gatekeeping. The Spotter is doing the first-pass review while leaders focus on harder judgment calls.

It's also a coaching tool. When a PM disagrees with The Spotter's verdict, that conversation — about *why,* about *what nuance the skill missed* — is exactly the kind of dialogue that builds product judgment.

## Install

The Spotter runs via the Mission Built MCP server — no local file copy needed.

**Add to Claude Code** (`~/.claude/claude.json` or your project's `.mcp.json`):

```json
{
  "mcpServers": {
    "missionbuilt": {
      "type": "sse",
      "url": "https://mcp.missionbuilt.io/sse"
    }
  }
}
```

**Cowork:** install the Mission Built plugin from the Cowork plugin directory.

Then say *"run the spotter on this epic"* (after pasting one) or *"build an epic for [feature]"* — the skill triggers automatically.

## How to use

### Review an existing epic

Paste your epic into Claude Code or Cowork and say *"run the spotter"* (or *"review this epic"*). The Spotter evaluates the epic across all nine areas, builds a SPOTTER_DATA payload, and calls `spotter_get_template` to produce a worksheet artifact. Each area shows the relevant excerpt from your epic, a verdict pip trio, and typed critique notes. Accept notes you've addressed, skip ones you're setting aside, then hit **Send to Spotter** to refine a given area. When every area is closed, the export button unlocks.

### Build a new epic

Say *"help me build an epic for [feature]."* The Spotter walks you through the nine areas with guiding questions, lingering on Area 1 (user and problem) before moving on. Output is a polished draft epic.

### Iterate on a draft

Say *"iterate on this epic"* with a partial draft. The Spotter uses coaching questions to surface gaps in whichever areas are weakest, then pushes the draft forward with you.

## Customizing for your team

The Spotter is designed to be adapted. Two layers:

1. **The skill stays generic.** SKILL.md captures the universal lens framework and voice. Don't fork that for company-specific things.
2. **Your `CLAUDE.md` carries the specifics.** Put your tier names, your competitor set, your product taxonomy, your moat candidates in `.claude/CLAUDE.md` at the project root. The Spotter will pull from it automatically.

This keeps the open-source skill clean while letting your team's instance carry organizational truth.

## Calibration

The server includes three synthetic calibration epics, accessible via `spotter_get_calibration_epic` (epic 1) or `spotter_get_calibration_epics` (all three). Epic 1 is a deliberately gap-heavy "thoughtful PM, but with real failure modes" B2B security draft — running The Spotter against it should produce a worksheet with flags on Areas 1, 4, 5, 6, 8, and 9.

Epics 2 and 3 are well-formed security platform epics for grading range calibration.

If your install produces a wildly different result on Epic 1, the skill has drifted — recheck your CLAUDE.md and any local edits to SKILL.md.

## Contributing

Improvements welcome. Pull requests should:

1. Keep the skill domain-agnostic. Company-specific examples belong in your CLAUDE.md, not in the skill.
2. Preserve the *critique-not-criticism* voice. *"You could strengthen this by..."* — never *"you missed..."*
3. Add citations for any new structural ideas borrowed from other open-source skills or PM writers. See `ATTRIBUTION.md`.

## License

MIT. See [LICENSE](LICENSE). Use it commercially, fork it, modify it, embed it. Attribution preserved per the MIT terms is appreciated.

## Spirit

The Spotter is offered freely. If it makes your work better — pay it forward by contributing back, by sharing what you learn, by lifting the PMs around you.

*Real strength is lifting others.*

— Mike

---

## Attribution

See [ATTRIBUTION.md](ATTRIBUTION.md) for full credits to the open-source skills and product writers whose thinking informed this work.

## Part of The Loadout

The Spotter is part of **The Loadout** — a growing kit of open-source product leadership skills from the *Mission Built* ecosystem. The book teaches the principles; The Loadout puts the principles into operation. Current skills in the kit:

- **The Spotter** — epic review and guided build, nine-area framework, interactive worksheet artifact
- **The Warmup** — morning intelligence brief for the first coffee, three modes, live HTML artifact
- **The Approach** — pre-meeting intelligence brief for enterprise sales calls, QBRs, and executive meetings

Future skills may include:

- **The Sitrep** — status updates that respect the reader's time
- **Form Check** — code or design review with the same lift-not-gate orientation
- **The Cooldown** — retros and post-mortems that learn forward, not blame backward

Each skill stands alone. Together they form a kit.
