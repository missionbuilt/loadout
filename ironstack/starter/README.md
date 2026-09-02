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

From now on, every push that touches `workouts/**` validates your logs against the schema and indexes them. Running by hand works too, and both scripts are idempotent:

```bash
pip install -r ingest/requirements.txt
export ES_ENDPOINT=... ES_API_KEY=...
python ingest/setup_indices.py
python ingest/index_workouts.py
```

## Log a workout

Use the **workout-partner** skill (in the Loadout at `ironstack/skills/`) — tell Claude about your session and it writes the pair of files:

```
workouts/2026/2026-09-01.md     # for you to reread
workouts/2026/2026-09-01.json   # for the pipeline (validated against schema/workout.schema.json)
```

Commit both. A complete example pair lives in the Loadout at `ironstack/examples/`.

## What's here

```
schema/workout.schema.json      every log must validate against this
schema/mappings/                Elasticsearch mappings for the three indices
ingest/setup_indices.py         creates/updates indices (semantic layer auto-detected)
ingest/index_workouts.py        validates + bulk-indexes logs (deterministic _ids, safe re-runs)
workflows/index.yml             the GitHub Action — move to .github/workflows/index.yml
workouts/                       your logs live here
```
