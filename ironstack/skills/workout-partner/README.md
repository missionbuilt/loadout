# Workout Partner

The writing half of [Ironstack](../../README.md). Tell Claude about your session — during it
or after — and it asks the questions a good partner asks, keeps you honest, and writes the
log. One shorthand file per session; one command turns that into the JSON the indexer eats
and the markdown you reread.

It is a partner, not a programmer and not a doctor. It logs and it encourages. It does not
write blocks, and anything that sounds like pain gets a note in your journal and a pointer
to a professional.

## Prerequisites

- An **Ironstack instance repo**, made from [starter/](../../starter/README.md), as the
  working directory. That is where `workouts/`, `config/` and `ingest/log.py` live.
- **Python**, with `pip install -r ingest/requirements.txt` done.

Without the repo the skill has nowhere to write, and it will say so rather than logging a
session into the conversation.

## Install

Claude Code / Cowork:

    cp -r workout-partner .claude/skills/

Claude.ai: upload this folder as a user skill.

## Run

Start talking about your session: "warming up for bench", "just hit 315 for 3", "logging
yesterday's squat day". The skill keeps a running `.iron` file, asks for the four things
only you can supply (start time, duration, bodyweight, sleep), and finishes with:

```bash
python ingest/log.py workouts/2026/2026-09-04.iron --push
```

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The skill: prerequisites, the conversation, encouragement, boundaries, the write path and its exit codes |
| `references/example-session.iron` | A complete session in the shorthand format |
| `references/logging.md` | What `log.py` does, its flags, equipment ids, and the fields that make a note redundant |
| `SKILL-DESIGN.md` | Why the skill is shaped this way (maintenance only) |
| `LICENSE` | MIT |

## The load ceiling

Any weight the skill suggests is bounded by the rule in [CEILING.md](../../CEILING.md),
which the Ironstack Coach obeys too. The skill cannot read `est_e1rm` — that is computed at
index time and lives in Elasticsearch — so the check that works from the repo is
`python ingest/ceiling.py "<lift>"`. **That script is specified in `CEILING.md` and not yet
implemented**; until it is, the skill says it could not check rather than implying it did.

## Caveat

Not medical advice, not programming. Ironstack logs your training and encourages you
honestly. Programs belong to your coach or an established program; pain and injury belong to
a qualified professional.

MIT. Part of The Loadout · missionbuilt.io
