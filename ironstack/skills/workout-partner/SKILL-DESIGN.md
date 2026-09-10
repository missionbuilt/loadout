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

## Never log an assumption

Two sets in a real log once carried the note *"reps not restated, assumed same as round 1"*.
The partner had a gap, filled it, and wrote down that it had — which is the worst of both:
a number that may be wrong, and a note that dulls the semantic layer with commentary about
the log. A missing value is a question while the lifter is still there, and an empty field
when they are not. The rule is stated as a rule because the temptation is structural: the
skill is asked to write a complete file and a gap looks like a failure to do so.

## Five facts, one message, before feedback

Start time, duration, bodyweight and sleep were "asked whenever it fits", and two real
sessions shipped without bodyweight or sleep: `log.py` printed `missing:` both nights and
nobody acted on it. Asking at a "natural moment" is asking never. So the questions are one
message, sent after the sets and before any feedback, every session, and the five facts are
asked even when some were volunteered. The fifth — *home gym?* — is there because location
was defaulted and never asked, so a travel session had no path into the log except the
lifter thinking to mention it. Feedback waits until the answers are in, because the
questions are the only thing the lifter has to do and the feedback is the reward for it.

## The day stays open until it is pushed

Validating is not logging. In a sandbox without network the partner can write and validate
but cannot fetch weather or push, and a session that ends there has a `.iron` on disk and
nothing in the cluster. The skill therefore tracks an open day and refuses to let it close
on an assumption: the push is confirmed by the lifter or by the commit in `git log`, and a
goodnight while it is open gets the command back first. "What's next?" is answered with
the state of that day rather than a description of the process.

## The brief comes from the files

`today.py` and `last.py` exist so the pre-session brief needs no Elasticsearch and no
network. Everything they print is in `workouts/**/*.json`. The lift list `today.py` offers
is the last session on the same program day — a good guess, presented as one — because the
repo holds no program file and inventing a plan is the programming the skill refuses to do.
