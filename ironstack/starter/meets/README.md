# meets/

One file per competition, named by date (`2026-11-14.json`), validated against `schema/meet.schema.json`.

Kilograms are the source of truth; `ingest/index_meets.py` derives pounds and marks the best made attempt per lift. Every attempt becomes one `workout-meets` document carrying the meet-level fields, so one index answers both "best squat ever" and "total per meet".

## The example

`example-meet.json.example` is sample data. Nobody lifted it. It keeps the `.example`
extension on purpose: the indexer globs `meets/*.json`, so nothing under this folder is
read until you rename a file to end in `.json`. An example that indexes itself would put
someone else's total on your Meets dashboard and someone else's DOTS on your projection,
which is exactly what this template used to do.

To start from it:

```bash
cp meets/example-meet.json.example meets/2026-11-14.json   # use your own date
python ingest/index_meets.py --validate                     # check it against the schema
```

Then edit it into your own meet, or delete it.

## Fields

`meet_id` and `date` and at least one attempt are required. `total_kg` is your official
total; leave it out and the indexer adds up the best made attempt per lift. `dots` is the
score as the federation calculated it, so what the dashboard shows is what was on the
scoresheet. Missed attempts belong in the file: `attempts_made` counts them, and the
Meets dashboard shows what you went nine for.

`lift_names` maps each competition lift to how you name it in your logs (defaults:
Competition Squat, Competition Bench Press, Competition Deadlift), which is what lets a
meet's best lift drill into its own training history.
