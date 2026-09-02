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

Use the **workout-partner** skill (in the Loadout at `ironstack/skills/`) — tell Claude about your session and it writes the pair of files:

```
workouts/2026/2026-09-01.md     # for you to reread
workouts/2026/2026-09-01.json   # for the pipeline (validated against schema/workout.schema.json)
```

Commit both. A complete example pair lives in the Loadout at `ironstack/examples/`.

The `program` block is what ties sessions into the dashboards: `block`, `phase` (hypertrophy, strength, peaking), `week`, `day` of `total_days`, and `meet_date`. The indexer adds `prev_session_id`, `next_session_id`, and `streak_day` to every session from the set of logs it can see, so never write those by hand. Optional `metrics` (`bodyweight_lb`, `sleep_hrs`) feed the companion tiles when present.

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
workflows/index.yml             the GitHub Action, move to .github/workflows/index.yml
workouts/                       your logs live here
meets/                          your meet records live here
```
