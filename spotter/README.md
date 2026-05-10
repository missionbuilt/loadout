# The Spotter

A Claude Code / Cowork / agent-compatible skill for reviewing, building, and iterating on B2B product epics.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

By [H. Michael Nichols](https://www.linkedin.com/in/hmichaelnichols) · Part of [The Loadout](https://missionbuilt.io) — open-source product leadership skills from the [*Mission Built*](https://missionbuilt.io) ecosystem.

---

## What this is

The Spotter walks an epic through nine product-leadership lenses — empathy, competitive landscape, strategic differentiation, solution approach (with explicit AI decisions), holistic impact, packaging, launch readiness, post-launch ownership, and trust/governance/auditability — and produces structured, voice-aligned feedback in the *critique-not-criticism* tradition.

It works in three modes:

- **Build mode** — guided creation from scratch, lens by lens.
- **Iterate mode** — push a partial draft forward with targeted questions.
- **Review mode** — verdict the epic with structured per-lens feedback, then offer to work through gaps together.

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

**Drop-in install (Claude Code):**

```bash
git clone https://github.com/missionbuilt/loadout.git /tmp/loadout
mkdir -p .claude/skills
cp -r /tmp/loadout/spotter .claude/skills/
```

**Verify it loaded:**

```bash
ls .claude/skills/
# spotter
```

Then in Claude Code, say *"run the spotter on this epic"* (after pasting one) or *"build an epic for [feature]"* — the skill triggers automatically.

**Cowork:** drop the `spotter/` folder into your Cowork plugin's skills directory.

## How to use

### Review an existing epic

Paste your epic into Claude Code or Cowork and say *"run the spotter"* (or *"review this epic"*). The Spotter will produce a verdict (Ready / Needs polish / Not ready), walk all nine lenses with structured feedback, end with a *Questions to ask the PM* section, and — if the verdict is *Needs polish* or *Not ready* — offer to work through specific gaps with you. Pick a lens, work through it together, repeat for as many as you want. The review is the start of a conversation, not the end of one.

### Build a new epic

Say *"help me build an epic for [feature]."* The Spotter walks you through the nine lenses with guiding questions, lingering on Lens 1 (empathy + current state) before moving on. Output is a polished draft epic at the end.

### Iterate on a draft

Say *"push this epic forward"* or *"what's missing from my epic?"* with a partial draft pasted. The Spotter engages only the lenses that have content, asks targeted questions, and offers structure where you're stuck.

## Customizing for your team

The Spotter is designed to be adapted. Two layers:

1. **The skill stays generic.** SKILL.md captures the universal lens framework and voice. Don't fork that for company-specific things.
2. **Your `CLAUDE.md` carries the specifics.** Put your tier names, your competitor set, your product taxonomy, your moat candidates in `.claude/CLAUDE.md` at the project root. The Spotter will pull from it automatically.

This keeps the open-source skill clean while letting your team's instance carry organizational truth.

## Calibration

The repo includes a synthetic B2B security epic at `examples/synthetic-epic.md` — a deliberately gap-heavy "thoughtful PM, but with real failure modes" draft. Running The Spotter against this synthetic epic should produce a verdict of **Needs polish** with specific gaps flagged on Lenses 1, 4, 5, 6, 8, and 9.

If your install produces a wildly different verdict, the skill has drifted — recheck your CLAUDE.md and any local edits to SKILL.md.

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

The Spotter is the first skill in **The Loadout** — a growing kit of open-source product leadership skills from the *Mission Built* ecosystem. The book teaches the principles; The Loadout puts the principles into operation. Future skills in the kit may include:

- **The Walkthrough** — customer meeting prep that pulls recent activity and predicts conversation direction
- **The Warmup** — morning curation of the news and signals worth your first coffee
- **The Sitrep** — status updates that respect the reader's time
- **Form Check** — code or design review with the same lift-not-gate orientation
- **The Cooldown** — retros and post-mortems that learn forward, not blame backward

Each skill stands alone. Together they form a kit.
