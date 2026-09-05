# Ironstack shorthand (`.iron`)

One session, written once. `ingest/log.py` expands it into the session JSON the
indexer eats and the markdown log you reread, so the two can never drift.

```bash
python ingest/log.py workouts/2026/2026-09-04.iron          # expand + validate + write
python ingest/log.py workouts/2026/2026-09-04.iron --push   # ... commit and push; CI indexes
```

## A whole session

```
start: 18:15
program: next
bw: 205.4
sleep: 7
env: 78F 61% "muggy, doors open" wind="light SW" setting="garage gym"
prep: pap
pre: shoulders felt cold walking in #fatigue

# Competition Bench | main | Rogue rack + Ohio power bar | emphasis: leg drive
w: 45x10 "bar only", 95x5, 135x3, 165x1
185x5 @7 +lever belt, wrist wraps "bar path honest"
195x5 @8 "grinder on the last rep" #felt-strong
- left shoulder tight on the second set #asymmetry:left

# Incline DB Press | accessory | dumbbells
70x10 @7 *3

# Face Pull | accessory
bw x20 *3

wrapup: Bench day felt good after a rough deadlift session.
watch: left shoulder tightness
wrap: Ended strong. #motivation
```

## Header keys

| Key | Becomes | Notes |
|---|---|---|
| `date:` | `session.date` | Defaults to the filename |
| `id:` | `session.session_id` | Only for a second session in one day (`2026-09-04-2`) |
| `start:` | `start_time` | `time_of_day` is derived: <11 morning, <15 midday, <21 evening, else night |
| `duration:` | `duration_min` | Minutes |
| `program:` | `session.program` | `block/phase w21 d4/4 meet=2026-10-24`, or just `next` |
| `place:` / `geo:` / `travel:` | `location` | `travel` flips to true automatically away from home. How precise you name a place is `location_detail` in `config/defaults.json` — `coarse` (town or city) or `exact` (street level, for a private log) |
| `env:` | `environment` | `78F 61% "conditions" wind="..." setting="..."` |
| `bw:` `sleep:` | `metrics` | Bodyweight lb, sleep hours |
| `gear:` | `gear_notes` | Session-wide |
| `prep:` | prep exercises | Expands a block from `templates/prep/` |
| `pre:` `prepnote:` `wrap:` | a note | Phase `pre` / `prep` / `wrap-up`; `#tags` allowed |
| `wrapup:` | `wrap_up` | The paragraph in the log |
| `watch:` | `watch_items` | Repeat the key for each item |

Anything omitted falls back to `config/defaults.json` (timezone, home gym,
program name, meet date), so a normal session never types them.

## Exercises

```
# Name | category | @equipment-ids | emphasis: ... | gear: a, b
```

`category` is `main`, `accessory` (default) or `prep`. Everything after the name
is optional and order doesn't matter.

### Equipment

Name the bar, the rack, the machine — `config/equipment.json` holds the gym once and the
log references it by id:

```
# Competition Deadlift | main | @ohio-power
275x4 @7 +@lever-belt, @chalk
```

That stores the readable line (`Titan deadlift platform + Texas Deadlift Bar (45 lb)`)
**and** the structure behind it — `equipment_ids`, `equipment_names`, `equipment_kinds`
and `bar_weight_lb` on every set document. So "everything I pulled with the Texas bar" or
"squat volume by bar" is a filter in Kibana, not a text search, and the bar's empty weight
is a number instead of a phrase in parentheses.

- An id that isn't in the registry still logs, using the id as the name — add it to
  `config/equipment.json` afterwards. Ids must not start with a digit.
- Free text still works and can sit alongside ids when the detail matters:
  `| @lat-pulldown | equipment: lat pulldown machine, wide neutral grip`.
- `+@lever-belt` in a set line and `gear: @knee-sleeves` in a header resolve to the
  registry's spelling, so the same strap is written one way forever.

## Set lines

```
[w] WEIGHT[ea]xREPS[s|w][/s] [@RPE] [+gear] ["notes"] [#tags] [key=value] [*N]
```

- `275x4 @7` — 275 lb for 4, RPE 7. Report RIR and it converts: RPE = 10 − RIR.
- `w 135x5` or `w: 45x10, 135x5, 225x3` — warmup / prep sets.
- `bw x60s` — bodyweight, 60 seconds. `bw45x8` is bodyweight plus 45 lb.
- `55ea x10` — 55 lb **in each hand**; `weight_lb` becomes the 110 lb total and
  `weight_each_lb` keeps the 55. Don't write "55 lb each hand" in the notes.
- `x12/s` — 12 reps **per side**. Don't write "each side" in the notes.
- `141x1w ft=50` — a carry: one walk, 50 feet.
- `*3` repeats an identical set. `- text #tag` on its own line notes the exercise above.
- `0x12` is loaded-but-weightless (bands); `bw` is the one that marks `load_type: bodyweight`.

### Keep the notes for meaning

A note should say something no field can. These all have fields now, and writing them
twice costs bytes and dulls semantic search — every set that says "3 in the tank" makes
that phrase meaningless to search:

| Don't write | Write |
|---|---|
| `"3 in the tank"` | `@7` — the log renders "3 in reserve" from the RPE |
| `"55 lb each hand"` | `55ea` |
| `"12 reps each leg"` | `x12/s` |
| `"ladder: 6,5,4,3,2 + hold"` | `scheme="6,5,4,3,2 + hold"` |
| `"4.46 mi, 92 cal, 62 rpm"` | `dist=4.46 cal=92 rpm=62` |

Conditioning keys: `dist=` miles, `cal=`, `watts=` average, `peakw=`, `rpm=`, `mph=`,
`hr=` average, `maxhr=`. An unknown `key=` is an error, so a typo can't sneak through.
"lower back aware", "bar path honest", "left arm tired before the right" — that's what
notes are for.

There is no comment syntax — a leading `#` opens an exercise, and `#tag` is a tag.

## What every session should carry

`config/defaults.json` holds a `require` list — the session metadata a log is supposed to
have. `ingest/log.py` names anything missing:

```
2026-09-04: 6 exercises · 13 working sets · 12,100 lb moved · avg RPE 7.0
  weather: 78F, 61%, partly cloudy, SW 7 mph
  missing: duration, sleep — ask before the memory fades
```

- **Location, timezone, program** come from `config/defaults.json`, so they're always there.
- **Weather** is looked up automatically from the coordinates and the hour trained
  (Open-Meteo, no key). It never blocks a log: if the lookup fails you get a note and an
  empty `environment`. `--no-weather` skips it; an `env:` line you wrote always wins.
- **Start time, duration, bodyweight, sleep** can only come from the lifter. The training
  partner asks for them; `--strict` refuses to write the log without them.

Change the `require` list to match what you actually want tracked.

## What Elasticsearch gets

The log stays terse; `ingest/index_workouts.py` builds the AI-facing view on every run:

- **`digest`** on each session document — the whole session written out as a paragraph
  (date, place, weather, program day, top sets, equipment, totals, every note, the wrap-up,
  the watch list). This is the field to search when the question is about a session rather
  than a sentence: *"how did I feel training in Las Vegas?"*
- **Watch items become documents** in `workout-notes` with `phase: "watch"`, so *"when was
  my grip last a problem?"* finds them the same way it finds notes.
- **Semantic (ELSER) fields** — `notes.text`, set `notes`, session `wrap_up`, `gear_notes`,
  `watch_items` and `digest`, plus meet `notes`. `setup_indices.py` adds each as a
  `semantic_text` sibling via `copy_to`, and falls back to plain mappings where semantic
  search isn't available (`ES_SEMANTIC=auto|on|off`).
- **Equipment, effort and conditioning as fields** — `equipment_ids`, `bar_weight_lb`,
  `each_side`, `weight_each_lb`, `scheme`, `cardio.*` — so they can be filtered and
  aggregated instead of read.

Re-run `python ingest/setup_indices.py` after pulling mapping changes, then
`python ingest/index_workouts.py` to rebuild. Ids are deterministic, so nothing duplicates.

## Checks

```bash
python ingest/test_shorthand.py    # round-trips every log in the repo through the format
python ingest/weather.py 39.8 -89.65 2026-09-04 18 America/Chicago   # the weather lookup alone
python ingest/shorthand.py --encode workouts/2026/2026-09-03.json   # JSON -> shorthand
python ingest/render_md.py workouts/2026/2026-09-03.json --write    # regenerate one markdown log
```
