# Contributing to The Loadout

Thanks for taking the time to improve the kit.

The Loadout is open source under MIT. Improvements to existing skills, new skill submissions, and adjustments to the framework are all welcome. This document captures the conventions that keep skills consistent across the kit so contributors can move fast without drift.

## Quick orientation

The Loadout lives at [github.com/missionbuilt/loadout](https://github.com/missionbuilt/loadout). Each skill is a self-contained subdirectory at the top level — `spotter/`, `warmup/`, and others to come. Each skill carries its own `SKILL.md`, `README.md`, `ATTRIBUTION.md`, and `examples/` or reference folder.

When a Claude Code or Cowork user installs a skill, they copy a single subdirectory into their `.claude/skills/`. The directory structure mirrors that contract.

## How to contribute

### Report something

- **Issues** — for typos, broken links, factual errors, or anything you think is wrong: [open an issue](../../issues).
- **Discussions** — for general feedback, questions, suggestions, design conversations: [start a discussion](../../discussions).

### Improve an existing skill

1. **Fork** this repository.
2. **Find the file.** Each skill's content lives in:
   - `<skill>/SKILL.md` — the skill itself (criteria, modes, output formats)
   - `<skill>/examples/area-examples.md` (or equivalent) — the worked examples that teach the criteria
   - `<skill>/README.md` — install and use documentation
   - `<skill>/ATTRIBUTION.md` — credits and inspiration sources
3. **Make your change.** Keep the diff minimal — don't reformat surrounding text.
4. **Submit a pull request** with a short description of what you changed and why. Reference any related issue.

### Submit a new skill

New skills are the highest-leverage contribution. Before drafting a full skill, open a Discussion to align on:

- **The problem the skill solves.** What's the leverage moment? Why does this earn a slot in the Loadout?
- **The name.** Strength-themed where natural, with military riffs as accents (see existing skills for the pattern). Names should be short, evocative, and earn their meaning.
- **The relationship to existing skills.** Does this overlap with anything already in the Loadout? Should it ship as a new skill or as a mode within an existing skill?

Once we've aligned on scope, the path looks like:

1. Fork this repository.
2. Create a new top-level directory with the skill's name.
3. Add `SKILL.md`, `README.md`, `ATTRIBUTION.md`, `LICENSE` (MIT), and an `examples/` folder following the conventions below.
4. Submit a PR.

## Conventions that keep skills consistent

### Skills stay domain-agnostic

Company-specific examples — your tier names, your competitor set, your product taxonomy, your moat candidates — belong in the *user's* `CLAUDE.md`, not in the skill itself. Skills in the Loadout are reusable across organizations. If a skill embeds organization-specific context, it stops being useful to anyone else.

If you fork a skill for your team, customize freely. If you contribute back to the Loadout, strip the customizations and use generic placeholders.

### Voice: critique, not criticism

This is the single most important convention. The Loadout's skills are designed to *lift the work and the person doing it*, not to gate or judge them.

In practice, this means:

- ✓ *"You could strengthen this by..."*
- ✓ *"Worth checking..."*
- ✓ *"Consider naming the user persona explicitly..."*
- ✗ *"You missed..."*
- ✗ *"This is wrong."*
- ✗ *"You failed to..."*

Every flag, every suggestion, every prompt back to the user should be in the lifting voice. If your draft slips into the catching voice, rewrite it.

### Examples beat instructions

The most effective teaching mechanism is contrast. Skills in the Loadout pair every criterion with worked examples at three levels: **✓ Strong**, **⚠️ Needs work**, and **✗ Missing**. Each example carries a *teaching note* explaining why it earns its grade.

When in doubt about whether an instruction is teaching the right thing, write the contrasting example. If the contrast is sharp, the instruction is right.

### Anti-patterns

Each skill carries an explicit *"Things this skill should NOT do"* section. This convention is borrowed from [aakashg/pm-claude-skills](https://github.com/aakashg/pm-claude-skills) (MIT). Anti-patterns are as important as positive criteria — they prevent the drift modes that creep in as skills mature.

### Attribution

Skills in the Loadout cite their sources of conceptual influence — both other open-source skills and published thinkers. See [`spotter/ATTRIBUTION.md`](spotter/ATTRIBUTION.md) for the model.

When you contribute, add attribution for any new structural ideas borrowed from elsewhere. Citation should reflect actual debt, not citation theater — if you didn't borrow from a source, don't cite it to look thorough.

## Code of conduct

Be respectful. Argue ideas, not people. The Loadout is opinionated, but the project welcomes disagreement that's curious rather than combative.

---

Thank you for helping make this kit stronger.
