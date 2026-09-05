# Workout Partner — Design Spec

Why the skill is shaped this way. Read this before editing `SKILL.md`. For *using* the
skill, see `SKILL.md`.

## Thesis

A training partner with a notebook. Logging has to cost the lifter almost nothing while
they are between sets, and encouragement has to be earned or it is noise. Everything else
follows from those two.

## Written once, generated twice

The lifter writes shorthand and nothing else. `ingest/log.py` expands it into the session
JSON and the markdown log, so the two cannot drift and neither is ever hand-edited. The
skill is told this as a rule, because the failure mode is Claude "fixing" a generated JSON
file and putting it out of sync with the `.iron` that produced it.

A gap in the format is a reason to fix the format, not a reason to write JSON by hand.

## Ask for the four things nobody else can supply

Start time, duration, bodyweight, sleep. Everything else is defaulted (`config/defaults.json`)
or looked up (weather from the coordinates). `log.py` prints a `missing:` line, so the skill
reads the command's output rather than interrogating the lifter up front, and asks for a gap
while the session is still fresh.

## Notes carry what no field can

Every field that exists is a note that should not be written. When every set says "3 in the
tank", the phrase stops meaning anything to search, and the semantic layer over notes is one
of the reasons this project exists. The redundancy table lives in `references/logging.md`.

## The ceiling is checkable, or it is admitted

An earlier version of this skill claimed the load ceiling was "checkable rather than a matter
of judgement" because the indices carry `est_e1rm`. They do — but this skill has no
Elasticsearch connection, and `est_e1rm` appears in no file in the instance repo, so in the
skill's actual context the claim was false.

Two changes fixed that. The rule moved to one file, `ironstack/CEILING.md`, which the coach
cites too, so the two surfaces cannot state different ceilings. And the check became a
command that runs against the repo — `ingest/ceiling.py`, specified in that file. Until the
script exists the skill is instructed to say it could not check. An honest "I could not
verify this" is worth more than a confident number.

## Two registries, two different rules

`config/equipment.json` may be extended by the skill in the same commit, because the
alternative is the gym being retyped every session and the equipment fields never getting
populated.

`config/exercises.json` may not. An unknown exercise name is `log.py` exit 5: the command
refuses to write and prints the closest canonical names. A silently invented alias splits a
lift's history in two, which is exactly what the taxonomy exists to prevent, so the lifter
picks and the skill surfaces.

## The house layout

`SKILL.md` is the judgement and the boundaries. `references/` is the lookup: the write
path's mechanics, the equipment syntax, the redundancy table, a complete example session.
The example lives here rather than in the Loadout's `examples/` folder because the skill's
working directory is the instance repo, where a Loadout path does not resolve.
