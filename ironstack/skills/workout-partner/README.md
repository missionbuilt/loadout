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

Ask "what's today?" and it reads `ingest/today.py` and `ingest/last.py` — your program day,
the last time on each lift, the things you said to watch — before you touch a bar. Then
talk about the session: "warming up for bench", "just hit 315 for 3", the whole day in one
message afterward. The skill writes the `.iron` file, takes start time and duration off the
clock when you log live, asks the three things only you can supply in one message
(bodyweight, sleep, and whether you were home), never logs a guess, and finishes with:

```bash
python ingest/log.py workouts/2026/2026-09-04.iron --push
```

The day stays open until that command has run — say goodnight first and it reminds you.

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
`python ingest/ceiling.py "<lift>"`, which ships in the starter. Every suggested number
names the ceiling it sat under and the session it came from.

## Caveat

Not medical advice, not programming. Ironstack logs your training and encourages you
honestly. Programs belong to your coach or an established program; pain and injury belong to
a qualified professional.

MIT. Part of The Loadout · missionbuilt.io
