# Ironstack starter — your private instance

This folder is the plumbing for your own workout log: the schema, the indexing scripts, the analytics layer, and the GitHub Action. Copy it into a new **private** repo — that repo becomes the source of truth for your training data. It never goes back into the Loadout.

## Set it up

```bash
# from the loadout repo root
NEW=~/Projects/my-workout-log        # name it whatever you like
mkdir -p "$NEW"
cp -R ironstack/starter/. "$NEW"/
cd "$NEW"
mkdir -p .github/workflows
mv workflows/index.yml .github/workflows/index.yml && rmdir workflows

git init -b main
git add -A
git commit -m "Ironstack instance"
gh repo create <you>/my-workout-log --private --source=. --push
```

Then in the new repo on GitHub: **Settings → Secrets and variables → Actions** →

| Secret | Value |
|---|---|
| `ES_ENDPOINT` | your Elasticsearch URL |
| `ES_API_KEY` | an API key with write access |

Optional repo **variable**: `ES_SEMANTIC` — `auto` (default), `on`, or `off` — controls the ELSER semantic layer.

Then edit `config/defaults.json`. Everything in it is a placeholder, and one field is missing on purpose: there is no `location.geo`. `ingest/weather.py` sends those coordinates to Open-Meteo on your first log, so shipping a working pair here would have sent one person's weather to everyone who cloned this. Until you add yours, every log says `no weather: the session has no coordinates` and `weather` stays on the missing-metadata list. Add it as `"geo": {"lat": 39.8, "lon": -89.65}` inside `"location"`. Town level is enough; it is the only thing in this repo that leaves your machine.

From then on, every push that touches `workouts/**`, `meets/*.json`, `schema/**`, `ingest/**` or `config/**` runs the unit tests, validates your files against the schemas, indexes them, and verifies the cluster matches the repo. Running by hand works too, and every script is idempotent:

```bash
pip install -r ingest/requirements.txt
export ES_ENDPOINT=... ES_API_KEY=...
python ingest/setup_indices.py      # creates or updates the seven indices
python ingest/index_meets.py        # meets/*.json  -> workout-meets
python ingest/index_workouts.py     # workouts/**   -> the other six
```

If a mapping change alters a field's type, Elasticsearch won't apply it to a live index —
`setup_indices.py` says which index needs a rebuild and stops. Every document is rebuilt from
this repo, so recreating loses nothing:

```bash
python ingest/setup_indices.py --recreate workout-sessions
python ingest/index_workouts.py
```

To check that Elasticsearch matches this repo — mappings, counts, and the documents
themselves — run:

```bash
python ingest/verify_index.py
```

Pass file paths to either indexer to index a subset. `--validate` checks files against the schema, computes every derived field, and touches no cluster.

## Log a workout

Use the **workout-partner** skill (in the Loadout at `ironstack/skills/`) — tell Claude
about your session and it writes one shorthand file:

```
workouts/2026/2026-09-04.iron
```

Then one command expands it, validates it, and writes the rest:

```bash
python ingest/log.py workouts/2026/2026-09-04.iron --push
# -> workouts/2026/2026-09-04.json   the machine log (schema-validated, what the indexer explodes)
# -> workouts/2026/2026-09-04.md     the human log (generated, never hand-edited)
# -> commit + push; the Action indexes it
```

The shorthand is the only thing written by hand, so the JSON and the markdown cannot
drift apart. The command also looks up the weather you trained in, checks every exercise
name against the taxonomy before it writes anything, and names any session metadata
that's missing (`--strict` refuses to write without it).

`docs/shorthand.md` is the format reference. `config/defaults.json` holds the things that
never change (timezone, home gym, program name, meet date), `templates/prep/*.json` holds
the prep blocks, and `config/equipment.json` holds the gym — name a bar as `@ohio-power`
and the log stores its id, name and empty weight — so a normal session is a dozen lines.
`program: next` counts the block forward from the previous session.

A complete example lives in the Loadout at `ironstack/examples/`.

The `program` block is what ties sessions into the dashboards: `block`, `phase`
(hypertrophy, strength, peaking), `week`, `day` of `total_days`, and `meet_date`. The
indexer adds `prev_session_id`, `next_session_id`, and `streak_day` to every session from
the set of logs it can see, so never write those by hand. Optional `metrics`
(`bodyweight_lb`, `sleep_hrs`) feed the companion tiles when present.

## Exercise names

`config/exercises.json` is the taxonomy: every exercise name the pipeline will accept,
its movement pattern, the muscles it works, and whether it is a competition lift. Aliases
point at a canonical name (`Competition Squat` -> `Comp Squat`), and a name that is in no
entry is a hard error, not a warning — a renamed lift silently dropping out of the
muscle-group and ratio metrics is the failure this prevents.

When you log a name it does not know, `ingest/suggest.py` ranks the closest canonical
names and offers them. Accepting one writes an alias into `config/exercises.json`;
nothing is ever guessed for you. `ingest/build_exercise_taxonomy.py --check` fails if any
name in your corpus is unclassified.

## Record a meet

One JSON file per competition in `meets/`, named by date, validated against
`schema/meet.schema.json`. Kilograms are the source of truth; the indexer derives pounds.
Each attempt becomes one document in `workout-meets`, carrying the meet total, DOTS, and
weigh-in so the Meets dashboard and the meet-max reference lines read from one place.

`meets/example-meet.json.example` is sample data and keeps that extension on purpose: the
indexer globs `meets/*.json`, so nothing here is read until you rename a file to end in
`.json`. See `meets/README.md`.

## How heavy is too heavy

`ironstack/CEILING.md` in the Loadout is the one rule for the largest load either
suggesting surface may name for a lift. `ingest/ceiling.py` is that rule, runnable here
with no cluster and no credentials:

```bash
python ingest/ceiling.py "Comp Bench"
python ingest/ceiling.py "Comp Squat" --as-of 2026-06-01 --window 60 --json
```

It prints the ceiling, the session and set it came from, the heaviest weight actually
moved, and how much evidence is behind the number. `est_e1rm` is computed at index time
and appears in no file under `workouts/`, so without this there was no way to check the
ceiling from the repo alone.

## The seven indices

`ingest/index_workouts.py` explodes one session JSON into six of them; `index_meets.py`
writes the seventh.

| Index | One document is | Date-typed fields |
|---|---|---|
| `workout-sessions` | one session, with its program, environment, load and session-shape metrics | `@timestamp`, `date`, `timestamp` |
| `workout-sets` | one set, with its estimated 1RM, relative intensity, INOL and Prilepin zone | `@timestamp`, `date` |
| `workout-notes` | one note, wrap-up or watch item, for the semantic layer | `@timestamp`, `date` |
| `workout-meets` | one competition attempt, carrying the meet total, DOTS and weigh-in | `@timestamp`, `date` |
| `workout-daily` | one training day, rolled up | `@timestamp` |
| `workout-weekly` | one ISO week, rolled up, with ACWR, monotony, strain and the projection | `@timestamp` |
| `ironstack-signals` | one verdict, precomputed | **none, deliberately** |

### `ironstack-signals` carries no date field, and must not

The Overview verdict cards ("training drifted on calves", "this week is a loading week")
are ES|QL panels that state a conclusion about a window the card itself chose. Kibana
scopes an ES|QL card to the dashboard time picker by filtering on the index's date field.
With no date field there is nothing to filter on, so the picker cannot reach these rows,
and a card that says "the last 90 days" keeps saying it when the reader switches to Last
15 minutes.

That is the whole mechanism. **Adding any date-typed field to this index silently reverts
it**, with no error and no visible symptom: the cards keep rendering and start reporting
whatever slice of their own window the picker happens to allow. Every date in these rows
is stored as a `keyword` for that reason — `computed_through`, `week_end`, `last_trained`,
`meet_date` are all strings.

Three things defend it, and all three are load-bearing:

- `schema/mappings/ironstack-signals.json` sets `dynamic: strict` and `date_detection: false`, so Elasticsearch cannot invent a date mapping for a field it was not told about.
- `index_workouts.check_signal_fields()` refuses to send a row carrying a field the mapping does not declare, naming the field and the file, before anything is written.
- `derive.signal_docs()` writes every row with today's `computed_through`, and `index_workouts.sweep_signals()` deletes any row that this run did not write — signal ids carry meaning (`drift:calves`, `intensity:2026-W36`), so a row whose subject leaves the window would otherwise survive forever and could become the headline verdict.

If you add a signal, add its fields to the mapping as `keyword` whatever they hold, and
run `setup_indices.py`.

## Staying in step with the Loadout

The files in this template that are copies of a working instance's pipeline are listed
once, in `sync-manifest.json`, with the reason for every file that is deliberately not
shared. `sync_check.py` reads that list and compares two checkouts:

```bash
python sync_check.py --instance .          # from inside a copy of the template
```

The Loadout's own instance runs this in CI, so a fix that lands there and never reaches
here fails while someone is still holding the change. If you have customized the
pipeline, expect it to report your changes — that is what it is for.

## What's here

```
schema/workout.schema.json      every log must validate against this
schema/meet.schema.json         every meet record must validate against this
schema/mappings/                Elasticsearch mappings for the seven indices

ingest/setup_indices.py         creates/updates indices (semantic layer auto-detected)
ingest/index_workouts.py        validates + bulk-indexes logs, rollups and signals
ingest/index_meets.py           validates + bulk-indexes meet records
ingest/verify_index.py          checks Elasticsearch against this repo (mappings, counts, documents)
ingest/log.py                   shorthand -> JSON + markdown + commit (the one command)
ingest/shorthand.py             the .iron format, both directions
ingest/render_md.py             session JSON -> the human markdown log
ingest/weather.py               fills environment from the coordinates and hour trained
ingest/metrics.py               the formulas: DOTS, e1RM, INOL, Prilepin, ACWR, monotony
ingest/derive.py                what the formulas are applied to: the taxonomy, the
                                reference maxes, the rollups and the signal rows
ingest/ceiling.py               the largest load that may be suggested for one lift
ingest/suggest.py               ranked guesses at an unknown exercise name
ingest/build_exercise_taxonomy.py  one-shot seed for config/exercises.json, and --check
ingest/envconf.py               one reading of ES_ENDPOINT and ES_API_KEY
ingest/test_metrics.py          the formulas, against hand-checked values
ingest/test_shorthand.py        round-trips every log through the format
ingest/test_derive.py           the analytics layer, on a synthetic corpus
ingest/test_ceiling.py          the ceiling rule, and that it agrees with the indexer
ingest/test_suggest.py          the name suggester, against the whole taxonomy

config/defaults.json            what every session assumes unless it says otherwise
config/equipment.json           the gym: bars, racks, machines, belts — referenced as @id
config/exercises.json           the exercise taxonomy: patterns, muscles, aliases
templates/prep/                 named prep blocks, referenced as `prep: <name>`
docs/shorthand.md               the format reference

sync-manifest.json              which files here are copies of the Loadout's instance
sync_check.py                   compares this template against an instance
workflows/index.yml             the GitHub Action, move to .github/workflows/index.yml
workouts/                       your logs live here
meets/                          your meet records live here
```

Everything runs on Python 3.12 with `jsonschema` and `requests`. Nothing else.
