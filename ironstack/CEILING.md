# The ceiling

Two surfaces suggest loads: the **workout-partner** skill, when it names a starting weight
or builds a warm-up ladder, and the **Ironstack Coach**, when it answers "what should I
open with today". A lifter must not be able to get two different answers out of the same
product, so the rule lives here, once. Both surfaces cite this file. Neither restates it.

## The rule

For one lift, the **ceiling** is the largest load either surface may suggest.

1. The best `est_e1rm` on a **working set** of that lift in the trailing **90 days**,
   ignoring any set whose `e1rm_confidence` is `low`.
2. If nothing in that window qualifies, the best qualifying `est_e1rm` at any time — and
   the answer says the number is stale and how old it is.
3. If the lift has no qualifying estimate at all, the ceiling is the heaviest `weight_lb`
   ever logged on a working set of that lift.
4. If there is not even that, there is no ceiling. Do not suggest a number. Ask what they
   have done on it.

Never suggest above the ceiling. Round down, not up.

Two things are always said out loud with the suggestion: **the ceiling number and where it
came from** (the date and the set it was estimated from), and, when the suggested load is
above the heaviest weight ever actually moved on that lift, **that it is**. An estimate is
not a lift.

The ceiling is an upper bound, not a recommendation. Nothing here says a lifter should
work anywhere near it.

## Why these thresholds

They are not new policy. They are the thresholds already in the code, named in one place
so a sentence in a skill cannot drift from them:

- **90 days** is `REFERENCE_WINDOW_DAYS` in `starter/ingest/derive.py` — the same window
  every set's `intensity_pct` is measured against, with the same fall back to an all-time
  best when the window is empty (`intensity_ref` records which was used: `recent`,
  `all-time`, or `self`).
- **Excluding `low`** is what `derive._best_working_e1rm()` already does when it builds
  that reference. `starter/ingest/metrics.py` sets the tiers: `high` at 6 reps or fewer,
  `medium` at 7 to 9, `low` at 10 to 12, and no estimate at all above 12. A ten-rep set at
  RPE 6 is an extrapolation across nine reps of accumulating fatigue; it is worth showing
  and not worth setting a bar by.
- **Working sets only** — `set_type == "working"`. A warm-up single tells you nothing about
  a ceiling.

## Checking it from Elasticsearch

The coach has a tool for exactly this: `lift_ceiling` in [coach/tools.md](coach/tools.md),
with `ceiling_evidence` beside it for the sets behind the number. The coach runs both
before it names a load.

## Checking it from the repo, with no cluster

The skills that write logs have no Elasticsearch connection, and `est_e1rm` is computed at
index time — it appears in no session JSON file. So the rule has to be checkable from the
instance repo alone. That is one command:

```bash
python ingest/ceiling.py "Comp Bench"
```

`ingest/ceiling.py` reads the local `workouts/` corpus, applies the same estimation the
indexer applies, and prints the ceiling and the session it came from. No network, no
Elasticsearch, no credentials.

The lift is named as it is written in a log, or by any alias in `config/exercises.json`.
`Comp Bench` is the canonical name of the competition bench press in that file; there is
no `Competition Bench Press` entry, and asking for one fails the way a typo fails, with
the close matches printed:

```
$ python ingest/ceiling.py "Competition Bench Press"
exercise 'Competition Bench Press' is not in config/exercises.json. Did you mean:
  1. Comp Bench   (0.76)
```

### A worked example you can run

Two sessions are enough to show all four rules. From a fresh copy of `ironstack/starter`:

```bash
mkdir -p workouts/2026
cat > workouts/2026/2026-08-24.json <<'JSON'
{
  "session": { "session_id": "2026-08-24", "date": "2026-08-24" },
  "exercises": [
    { "name": "Comp Bench", "category": "main", "sets": [
      { "set_type": "prep", "weight_lb": 135, "reps": 5 },
      { "weight_lb": 185, "reps": 5, "rpe": 8 },
      { "weight_lb": 205, "reps": 2, "rpe": 9 },
      { "weight_lb": 155, "reps": 11, "rpe": 8 }
    ] }
  ]
}
JSON
python ingest/ceiling.py "Comp Bench" --as-of 2026-09-05
```

prints, exactly:

```
Comp Bench  ->  comp-bench
  ceiling        228.1 lb   est_e1rm  rpe/high      2026-08-24  185 x 5 @ 8
  window         90 days ending 2026-09-05  (recent)
  heaviest set   205.0 lb                           2026-08-24  205 x 2 @ 9
  qualifying     2 working sets across 1 sessions
```

Every number in that block comes from `ingest/metrics.py`, and every one of them is worth
reading:

- **228.1** is rule 1. The RTS table puts 5 reps at RPE 8 at **81.1%**, so `185 / 0.811`
  is 228.1 lb, at `rpe/high` because five reps is six or fewer.
- The 205 x 2 @ 9 set is heavier on the bar and **lower** as an estimate: 2 reps at RPE 9
  is 92.2%, so `205 / 0.922` is 222.3 lb. The ceiling is the best estimate, not the best
  set.
- The 155 x 11 @ 8 set estimates **237.4 lb**, which is higher than the answer, and it is
  thrown away — eleven reps is `low` confidence. Excluding `low` is not a rounding
  detail. Here it lowers the ceiling by nine pounds.
- The prep single is not counted at all.
- **heaviest set 205.0** is below the ceiling, which is the case the rule requires you to
  say out loud: 228.1 lb has never been on this bar.

Add a second session and the fallbacks show up:

```bash
cat > workouts/2026/2026-08-26.json <<'JSON'
{
  "session": { "session_id": "2026-08-26", "date": "2026-08-26" },
  "exercises": [
    { "name": "Lat Pulldown", "category": "accessory", "sets": [
      { "weight_lb": 120, "reps": 15, "rpe": 7 },
      { "weight_lb": 130, "reps": 15, "rpe": 8 }
    ] }
  ]
}
JSON
python ingest/ceiling.py "Lat Pulldown" --as-of 2026-09-05
```

```
Lat Pulldowns  ->  lat-pulldowns
  ceiling        130.0 lb   heaviest working set    2026-08-26  130 x 15 @ 8
  window         90 days ending 2026-09-05  (all-time)
  heaviest set   130.0 lb                           2026-08-26  130 x 15 @ 8
  qualifying     2 working sets across 1 sessions
```

That is rule 3. Above twelve reps there is no estimate at all, so there is nothing to
apply rules 1 and 2 to, and the only honest number left is a weight that was actually
moved. `Lat Pulldown` is an alias; the canonical name and the slug are what the block
prints. A lift with no loaded working sets at all — a plank, a bodyweight movement —
is rule 4:

```
$ python ingest/ceiling.py "Plank"
no qualifying sets — nothing to ceiling from
```

and exits 4.

### Qualifying sets

The last line of the block counts the evidence the ceiling rests on, and what counts
depends on which rule answered.

A **working rep-set** is the common part: `set_type` is `working` (absent means working;
prep and backoff-typed sets are out) and `rep_unit` is `reps` (a timed hold or a carry
has no reps to estimate from). Those are the same two filters
`derive.best_working_e1rm()` applies, which is why the number printed here and the number
the indexer writes cannot disagree.

On top of that:

| Rule | A set qualifies when | Over |
|---|---|---|
| 1 (best estimate in the window) | it is a working rep-set **and** `metrics.e1rm()` returns an estimate that is not `low` confidence | the trailing window only |
| 2 (stale best) | the same test | all time |
| 3 (heaviest working set) | it is a working rep-set carrying a load above zero — there is no estimate to qualify, so none is required | all time |
| 4 | nothing qualifies; the count is not printed | — |

`sessions` is the number of distinct sessions those sets came from. Under rule 1 the
count answers "how much recent evidence is behind this number"; under rule 3 it answers
"how often has this lift been loaded at all", which is a different question with the same
shape, and the `basis` on the ceiling line is what tells you which one you are reading.

### `window_ref` under the heaviest-weight fallback

`window_ref` is `recent` under rule 1 and `all-time` under rule 2, matching the two words
`intensity_ref` uses. Under **rule 3 it is `all-time`**, and under rule 4 it is null.

Rule 3 searches the whole history by construction: it is looking for the heaviest weight
ever moved, and a 90-day window would turn "the most this lifter has done" into "the most
they did this quarter", which is a different and much weaker claim. So the window line
still prints the window it was asked for, and `all-time` beside it says the answer did
not come from inside it.

Rule 3 is **not** marked stale. Staleness is rule 2's marker: an estimate that has aged
out of the window and may no longer be true. A weight that was on the bar does not expire
— it is a fact about what happened, not a projection — so `stale_days` stays null and the
window line carries no "stale" clause. If the fallback needs age context, `from_date` on
the ceiling line already carries it.

### Arguments and exit codes

| Argument | Meaning |
|---|---|
| `LIFT` (positional, required) | An exercise name as written in a log, or any alias in `config/exercises.json`. Resolved to a canonical lift the same way a set document's `lift_slug` is. |
| `--as-of YYYY-MM-DD` | Compute the ceiling as it stood on that date. Defaults to today. |
| `--window N` | Trailing window in days. Defaults to `derive.REFERENCE_WINDOW_DAYS` (90). |
| `--json` | Emit one JSON object instead of the text block, for a caller that wants to parse it. |

`--json` emits `{lift, slug, ceiling_lb, basis, method, confidence, from_date,
from_session_id, from_set, window_days, window_ref, heaviest_set_lb, heaviest_set_date,
qualifying_sets, sessions}`, with nulls where a fact is absent.

| Code | Meaning |
|---|---|
| 0 | A ceiling was printed. |
| 1 | Usage error (no lift named, or a bad `--as-of` / `--window`). |
| 4 | The lift is known but has no qualifying sets — rule 4. Nothing to suggest from. |
| 5 | The name is not in `config/exercises.json`. The closest canonical names are printed and nothing else happens, the same way `ingest/log.py` fails on the same typo. |

**What it reuses** — it implements no formula of its own:

| From | What |
|---|---|
| `ingest/metrics.py` | `e1rm()` for the estimate, method and confidence; `CONF_LOW` for the exclusion. |
| `ingest/derive.py` | `load_taxonomy()` and `classify()` to resolve the name and raise `UnknownExercise`; `lift_slug()` for the canonical slug; `REFERENCE_WINDOW_DAYS` for the window; `best_working_e1rm()` for the per-session best. |
| `ingest/index_workouts.py` | `catalog_logs()` to read every session JSON in `workouts/`, so one corpus walk is shared with the indexer. |
