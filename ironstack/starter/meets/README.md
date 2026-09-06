# meets/

One file per competition, named by date (`2026-11-14.json`), validated against `schema/meet.schema.json`.

A meet is a list of **events**. Each event has a unit and a list of attempts. Powerlifting's squat/bench/deadlift is one shape of that; a strongman show is another. Kilograms are the source of truth for weight events; `ingest/index_meets.py` derives pounds and marks the best made attempt on each event. Every attempt becomes one `workout-meets` document carrying the meet-level fields, so one index answers both "best log press ever" and "what did I place".

## The two questions that decide everything

**`unit`** — what the attempt measures, and which direction is better.

| unit | better | example |
|---|---|---|
| `kg` | more | squat, log press, clean and jerk |
| `reps` | more | sandbag over bar, max reps in 60s |
| `m` | more | Conan's wheel, a loaded carry for distance |
| `seconds` | **less**, and only a finished run counts | yoke, farmer's walk for time, a medley |

Only `kg` events fill `weight_kg` / `weight_lb`. That is deliberate: every query that ranks a best lift or sums a total reads those columns, and a yoke time in them would be ranked as a weight.

**`scoring`** — the only field that changes what the dashboards compute.

- `total` (the default) — the competition sums your best made weight attempt on every event. Powerlifting, weightlifting. A projected total is a meaningful thing to compute, and DOTS scores it against your bodyweight.
- `points` — each event is placed and the placings are added. Strongman. **There is no total, and Ironstack will not invent one** — not even from a `total_kg` written into the file by hand. A kilogram total on a points show would sort into a ranking of powerlifting totals as though it belonged there, and DOTS without a total is not a score. The Overview card switches from *projected total* to *event readiness*, and the Meets tiles rank on placing and points instead.

## The examples

Both keep the `.example` extension on purpose: the indexer globs `meets/*.json`, so nothing here is read until you rename a file to end in `.json`. An example that indexes itself would put someone else's total on your Meets dashboard.

- `example-meet.json.example` — a powerlifting meet in the legacy `attempts` shape, which is still fully supported.
- `example-strongman.json.example` — four events, four units, no total.

```bash
cp meets/example-strongman.json.example meets/2026-06-13.json   # use your own date
python ingest/index_meets.py --validate                          # check it against the schema
```

## Fields

`meet_id` and `date` are required, plus **either** `events` or the legacy `attempts` — not both.

`total_kg` is your official total; leave it out and the indexer adds up the best made weight attempt on each event, where the sport has a total at all. `dots` is the score as the federation calculated it, so what the dashboard shows is what was on the scoresheet. `points` and `placing` are the meet-level result for a points discipline, and each event can carry its own.

`result` is the official result for an event. Leave it out and the indexer computes it: the best made value, or the **lowest** for a `seconds` event. Set it when the recorded attempts do not tell the whole story — a judged event, an overturned lift.

Missed attempts belong in the file. `attempts_made` counts them, the Meets list strikes them through, and a fast run you did not finish is not your time.

`discipline` is free text — "powerlifting", "strongman", "highland games", whatever you call yours. It labels the record and picks nothing by itself; `scoring` is what changes behaviour.

## Reaching your training history

`lift_name` on an event is how that event is spelled in your workout logs, resolved through `config/exercises.json`. It is what lets a meet's best lift drill into its own training history, and what lets your platform best become the reference a training set is measured against.

Omit it when you do not train the event under a logged name. A yoke run and a medley have no training analogue and do not need a fake one — the event is filed under its own name instead, and nothing pretends it links anywhere.

Given and unresolvable is a **hard error**. A meet that says it links to a lift and lands on an empty dashboard is worse than a meet that says nothing.

The legacy `lift_names` object does the same job for the old three-lift shape, and still works.

## Upgrading an old meet file

You do not have to. A file written in the `attempts` shape produces byte-identical documents — same ids, same fields, same values — before and after events existed, and that is asserted in `ingest/test_index_meets.py` against a real meet.
