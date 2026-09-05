# Logging detail

The parts of the write path you need occasionally. The rules that change what you *do* are
in `SKILL.md`; this is the lookup.

## What `ingest/log.py` does, in order

1. Expands the shorthand: `config/defaults.json` for timezone, home gym, program name and
   meet date; `templates/prep/*.json` for a `prep:` block; `program: next` counted forward
   from the previous session.
2. Looks up the weather from the coordinates and the hour trained (Open-Meteo, no key). An
   `env:` line you wrote always wins. `--no-weather` skips it. A failed lookup is a note,
   never a blocked log.
3. Checks the session metadata in `config/defaults.json`'s `require` list and names what is
   missing.
4. Validates against `schema/workout.schema.json`.
5. Writes `workouts/YYYY/YYYY-MM-DD.json` and `.md` beside the `.iron`.
6. Prints the summary. With `--commit` or `--push`, commits the three files and pushes; CI
   indexes from there.

## Exit codes

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Written. | Read the summary and the `missing:` line. |
| 1 | No file named. | Pass the `.iron` path. |
| 2 | Schema validation failed. | The message names the field. Fix the shorthand and re-run. Never patch the JSON. |
| 3 | Push failed. | The commit is local. Tell them to push from a terminal with credentials. |
| 4 | `--strict` and session metadata missing. | Ask for what it named, add it, re-run. |
| 5 | An exercise name is not in `config/exercises.json`. | The lifter picks from the printed suggestions. See `SKILL.md`; never invent an alias. |

## Flags

| Flag | Effect |
|---|---|
| `--push` | Commit and push. The repo's Action indexes it. |
| `--commit` | Commit only. |
| `--strict` | Refuse to write while session metadata is missing. |
| `--no-weather` | Skip the weather lookup. |
| `--message "..."` | Set the commit message. |
| `--stdin --date YYYY-MM-DD` | Read shorthand on stdin instead of a file. |

## Equipment

`config/equipment.json` holds the gym once, and the log references it by id, so the bar,
its brand and its empty weight are stored as fields rather than buried in a sentence:

```
# Competition Deadlift | main | @titan-platform @texas-db
275x4 @7 +@lever-belt, @chalk
```

That writes `equipment_ids`, `equipment_names`, `equipment_kinds` and `bar_weight_lb` onto
every set document, so "everything I pulled with the Texas bar" is a filter rather than a
text search.

An id that is not in the registry still logs, using the id as its own name. Add it to
`config/equipment.json` in the same commit, with a sensible id that does not start with a
digit. That is the one registry the partner may extend on its own, because the alternative
is the gym being retyped every session. `config/exercises.json` is not: see the exit 5 rule
in `SKILL.md`.

## Odd units

Not everything is weight for reps, and each shape has fields rather than a sentence:

| Shape | Fields |
|---|---|
| Loaded carry | `rep_unit: "walks"` with `distance_ft` per walk (`141x1w ft=50`) |
| Timed hold | `rep_unit: "seconds"` (`bw x45s`) |
| Bodyweight work | `weight_lb: 0` with `load_type: "bodyweight"` (`bw x15`) |
| Bodyweight plus load | `bw45x8` — bodyweight plus 45 lb |
| Each hand | `55ea x10` — `weight_lb` is the 110 lb total, `weight_each_lb` keeps the 55 |
| Per side | `x12/s` sets `each_side` |
| Conditioning | the `cardio` fields, from the `key=` list below |

## Notes that repeat a field

Every one of these has a field, and writing it twice costs bytes and dulls semantic search.
When every set says "3 in the tank", the phrase stops meaning anything.

| Don't write | Write |
|---|---|
| `"3 in the tank"` | `@7` |
| `"55 lb each hand"` | `55ea` |
| `"12 reps each leg"` | `x12/s` |
| `"ladder: 6,5,4,3,2"` | `scheme="6,5,4,3,2"` |
| `"4.46 mi, 92 cal, 62 rpm"` | `dist=4.46 cal=92 rpm=62` |

Conditioning keys: `dist=` miles, `cal=`, `watts=` average, `peakw=`, `rpm=`, `mph=`, `hr=`
average, `maxhr=`. An unknown `key=` is an error, so a typo cannot sneak through.

Notes are for what no field can hold: "lower back aware", "bar path honest", "left arm tired
before the right".

## Working economically

The lifter is between sets. The log should cost them nothing and the session little.

- Keep a running `.iron` file and append to it. Do not restate the whole log in chat; a set
  they just called out does not need reading back in full.
- Never paste the generated JSON or markdown into the conversation. To check something, run
  the command and read its summary.
- A normal session is a `prep:` line, a `program: next` line, and one line per set.
  `config/defaults.json` and `templates/prep/` already cover the rest.
