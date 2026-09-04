# Ironstack starter — your private instance

This folder is the plumbing for your own workout log: the schema, the indexing scripts, and the GitHub Action. Copy it into a new **private** repo — that repo becomes the source of truth for your training data. It never goes back into the Loadout.

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

From now on, every push that touches `workouts/**` or `meets/*.json` validates your files against the schemas and indexes them. Running by hand works too, and every script is idempotent:

```bash
pip install -r ingest/requirements.txt
export ES_ENDPOINT=... ES_API_KEY=...
python ingest/setup_indices.py      # creates or updates the four indices
python ingest/index_meets.py        # meets/*.json  -> workout-meets
python ingest/index_workouts.py     # workouts/**   -> workout-sessions / -sets / -notes
```

Pass file paths to either indexer to index a subset. `--validate` checks files against the schema without touching Elasticsearch.

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
drift apart. The command also looks up the weather you trained in and names any session
metadata that's missing (`--strict` refuses to write without it). `docs/shorthand.md` is the format reference; `config/defaults.json` holds the
things that never change (timezone, home gym, program name, meet date) and
`templates/prep/*.json` holds the prep blocks, and `config/equipment.json` holds the gym —
name a bar as `@texas-db` and the log stores its id, name and empty weight — so a normal
session is a dozen lines.
`program: next` counts the block forward from the previous session.

A complete example lives in the Loadout at `ironstack/examples/`.

The `program` block is what ties sessions into the dashboards: `block`, `phase`
(hypertrophy, strength, peaking), `week`, `day` of `total_days`, and `meet_date`. The
indexer adds `prev_session_id`, `next_session_id`, and `streak_day` to every session from
the set of logs it can see, so never write those by hand. Optional `metrics`
(`bodyweight_lb`, `sleep_hrs`) feed the companion tiles when present.

## Record a meet

One JSON file per competition in `meets/`, named by date, validated against `schema/meet.schema.json`. Kilograms are the source of truth; the indexer derives pounds. Each attempt becomes one document in `workout-meets`, carrying the meet total, DOTS, and weigh-in so the Meets dashboard and the meet-max reference lines read from one place. Two real (already public) meets ship as examples; replace them with yours.

## What's here

```
schema/workout.schema.json      every log must validate against this
schema/meet.schema.json         every meet record must validate against this
schema/mappings/                Elasticsearch mappings for the four indices
ingest/setup_indices.py         creates/updates indices (semantic layer auto-detected)
ingest/index_workouts.py        validates + bulk-indexes logs (deterministic _ids, safe re-runs)
ingest/index_meets.py           validates + bulk-indexes meet records (same guarantees)
ingest/log.py                   shorthand -> JSON + markdown + commit (the one command)
ingest/weather.py               fills environment from the coordinates and hour trained
ingest/shorthand.py             the .iron format, both directions
ingest/render_md.py             session JSON -> the human markdown log
ingest/test_shorthand.py        round-trips every log through the format
config/defaults.json            what every session assumes unless it says otherwise
config/equipment.json           the gym: bars, racks, machines, belts — referenced as @id
templates/prep/                 named prep blocks, referenced as `prep: <name>`
docs/shorthand.md               the format reference
workflows/index.yml             the GitHub Action, move to .github/workflows/index.yml
workouts/                       your logs live here
meets/                          your meet records live here
```
