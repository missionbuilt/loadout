# The Loadout

A growing kit of open-source product leadership skills from the [*Mission Built*](https://missionbuilt.io) ecosystem.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

By [Mike Nichols](https://www.linkedin.com/in/hmikenichols) · Read the book at [missionbuilt.io](https://missionbuilt.io)

---

## What this is

The Loadout is a collection of Claude Code / Cowork / agent-compatible skills that help product leaders do the work that matters — reviewing epics, prepping for customer meetings, curating signal, running retros — with the same orientation as *Mission Built*: empathy first, problem before solution, lift the work and the people doing it.

Each skill is self-contained. Drop one into your `.claude/skills/` folder and it works. Take only what's useful to your team. The book teaches the principles; the Loadout puts the principles into operation.

## Available now

### [The Spotter](spotter/)

A skill for reviewing, building, and iterating on B2B product epics across nine product-leadership lenses — empathy, competitive landscape, strategic differentiation, solution approach, holistic impact, packaging, launch readiness, post-launch ownership, and trust/governance/auditability. Produces structured *critique-not-criticism* feedback in three modes (review, build, iterate).

A spotter in powerlifting watches your form, catches the bar if something breaks down, and gives you the confidence to attempt a lift you couldn't safely attempt alone. They lift *you*, not the bar. This skill does the same for an epic.

→ [Read The Spotter's documentation](spotter/README.md)

### [The Warmup](warmup/)

A daily intelligence brief for the first coffee. Know what moved before you open your inbox.

Three modes: **CISO Mode** loads a curated source suite — CISA advisories, the KEV catalog, MITRE ATT&CK, Tier 1 threat intel vendors, and sector-specific sources for Healthcare, Financial Services, Energy, Government, and Manufacturing/OT. **Product Leader Mode** covers competitor moves, AI model releases, market funding, key voices to track, and the analyst and news sources that matter for your vertical. **Custom Mode** lets you describe your interests in plain language and builds a source suite from scratch.

Every brief renders as a live HTML artifact — charcoal background, oxblood accents, instrument-panel typography. It reads like a field document, not a dashboard. Every URL cited in the brief is scanned before it renders; a Link Safety Verification panel shows the scan verdict for each source domain, flags anything suspicious, and excludes flagged sources from the brief body. Your config lives in a plain `WARMUP.md` at your project root — readable, editable, yours. See `WARMUP.example.md` at the repo root for the full schema.

→ [Read The Warmup's documentation](warmup/README.md)

## Planned

Future skills in the kit. Names tentative, scope under exploration:

- **The Walkthrough** — customer meeting prep that pulls recent activity and predicts where the conversation may head
- **The Sitrep** — status updates that respect the reader's time
- **Form Check** — code or design review with the same lift-not-gate orientation
- **The Cooldown** — retros and post-mortems that learn forward, not blame backward
- **The Programming** — strategy and roadmap planning, structured like a training cycle

## How skills work

Each skill in The Loadout is a markdown-based skill compatible with Claude Code, Cowork, and other agents that support the SKILL.md convention. They're plain text — no installer, no runtime, no API key required. You can fork them, adapt them for your team, and ship your own derivatives under the same MIT license.

## Install

Clone the Loadout and pull the skills you want into your project:

```bash
git clone https://github.com/missionbuilt/loadout.git /tmp/loadout
mkdir -p .claude/skills
cp -r /tmp/loadout/spotter .claude/skills/
cp -r /tmp/loadout/warmup .claude/skills/
```

Verify installation:

```bash
ls .claude/skills/
# spotter  warmup
```

Then in Claude Code or Cowork, trigger the skill with a phrase from its README — for example, *"run the spotter on this epic"* or *"run warmup"* / *"start my warmup."*

## Customizing for your team

Each skill is designed to stay generic. Company-specific context — your tier names, your competitor set, your product taxonomy, your moat candidates — belongs in a `CLAUDE.md` at your project root, *not* in the skill itself. This keeps the open-source skill clean and makes it easy to pull in updates without merge conflicts.

The skills read your `CLAUDE.md` automatically. Tune your local context once and every skill in the Loadout uses it.

For The Warmup specifically, your personal config (sector, vendors, sources) lives in `WARMUP.md` at your project root. See `WARMUP.example.md` for the full schema. `WARMUP.md` is gitignored and never committed — it stays on your machine.

## License

MIT. See [LICENSE](LICENSE). Use it commercially, fork it, modify it, embed it. Attribution preserved per the MIT terms is appreciated.

## Contributing

Improvements and new skill submissions welcome. Open an issue to start a conversation before sending a large PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for the conventions that keep skills consistent across the kit.

Two things to know up front:

1. **Skills stay domain-agnostic.** Company-specific examples belong in CLAUDE.md, not in the skill.
2. **Voice and orientation matter.** *Critique not criticism.* *"You could strengthen this by..."* — never *"you missed..."* See any existing skill's README and SKILL.md for the voice.

## Spirit

The Loadout is offered freely. If a skill makes your work better, pay it forward by contributing back, by sharing what you learn, by lifting the PMs around you.

*Real strength is lifting others.*

— Mike

---

*Part of the [Mission Built](https://missionbuilt.io) ecosystem. The book teaches the principles. The Loadout puts the principles into operation.*
