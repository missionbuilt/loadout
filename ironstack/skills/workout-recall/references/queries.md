# Query recipes

ES|QL, against the indices in [indices.md](indices.md). Each of these is a starting point:
change the lift, the window, the block.

Where a recipe would otherwise quote a number, it computes it. Nothing here should tell a
lifter what *someone else's* log says.

## Readiness, the last four weeks

```esql
FROM workout-weekly
| SORT week_end DESC
| LIMIT 4
| KEEP iso_week, training_days, tonnage_lb, acwr, acwr_band, monotony, strain,
       inol_hardest_lift, inol_hardest, inol_hardest_band, avg_working_rpe
```

## Where one lift stands

```esql
FROM workout-sets
| WHERE set_type == "working" AND lift_slug == "comp-deadlift"
    AND e1rm_confidence != "low"
| STATS best = MAX(est_e1rm), top = MAX(weight_lb), last = MAX(date), sets = COUNT(*)
```

## What a lift has been doing lately

```esql
FROM workout-sets
| WHERE set_type == "working" AND lift_slug == "comp-bench-press"
| SORT date DESC
| LIMIT 40
| KEEP date, session_id, weight_lb, reps, rpe, est_e1rm, e1rm_confidence,
       intensity_pct, intensity_ref, notes
```

## Volume by muscle over a block

```esql
FROM workout-sets
| WHERE set_type == "working" AND program.block == "strength"
| MV_EXPAND muscles_primary
| STATS sets = COUNT(*) BY muscles_primary
| SORT sets DESC
```

## What the reference actually is

`intensity_pct` is only relative intensity when there was a real reference behind it.
Compute the split for **this** log before leaning on the field:

```esql
FROM workout-sets
| WHERE set_type == "working" AND intensity_ref IS NOT NULL
| STATS sets = COUNT(*) BY intensity_ref
| SORT sets DESC
```

## Attempt history, and what actually gets made

```esql
FROM workout-meets
| WHERE made == true
| STATS best_kg = MAX(weight_kg) BY meet_id, date, lift
| SORT date DESC
```

For attempt selection, pair a made or missed attempt with the lift's `est_e1rm` around that
meet date and work out **their** percentages, from their own record:

```esql
FROM workout-meets
| SORT date DESC, lift ASC, attempt_no ASC
| LIMIT 200
| KEEP date, meet_id, lift, attempt_no, weight_lb, made, best
```

```esql
FROM workout-sets
| WHERE set_type == "working" AND e1rm_confidence != "low"
    AND date >= "2024-09-16" AND date <= "2024-11-16"
| STATS best = MAX(est_e1rm) BY lift_slug
```

Then state the percentage you calculated and the attempts it came from. If there are only
one or two meets in the log, say that the pattern rests on one or two meets. Do not carry a
figure from a previous conversation, from this file, or from lifting in general and present
it as their history.

## Watch items over time

```esql
FROM workout-notes
| WHERE phase == "watch"
| SORT date DESC
| LIMIT 40
| KEEP date, session_id, exercise.name, text, tags
```

## What they keep writing down

```esql
FROM workout-notes
| MV_EXPAND tags
| STATS notes = COUNT(*), last = MAX(date) BY tags
| SORT notes DESC
| LIMIT 25
```

## How a session felt, without a join

Search `digest` on `workout-sessions` (or `digest_semantic` where ELSER is on). The digest
already contains the date, place, weather, lifts, totals, notes and wrap-up, so "how did I
feel training in Las Vegas" is one hop rather than a scan over notes plus a join back to
sessions.

## A day, start to finish

```esql
FROM workout-sets
| WHERE session_id == "2026-09-01"
| SORT seq ASC
| KEEP seq, exercise.name, exercise.category, set_type, weight_lb, reps, rep_unit,
       rpe, est_e1rm, notes, tags
```

```esql
FROM workout-notes
| WHERE session_id == "2026-09-01"
| SORT order ASC
| KEEP order, phase, exercise.name, text, tags
```
