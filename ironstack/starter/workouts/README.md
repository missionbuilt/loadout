# workouts/

Your training logs live here, in your **private** instance repo.

One session = two files, organized by year:

```
workouts/2026/2026-09-01.md     # the human log
workouts/2026/2026-09-01.json   # the machine log (validated against schema/workout.schema.json)
```

Commit both and the GitHub Action indexes the JSON into your Elasticsearch. A complete reference pair lives in the Loadout repo at `ironstack/examples/`, and the **workout-partner** skill (`ironstack/skills/`) writes these files with you.
