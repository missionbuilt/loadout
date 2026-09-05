# Ironstack Coach — tools

The tools the agent is given, each with the query it runs and the question it answers.

Every field named here comes from the mappings in
[../starter/schema/mappings/](../starter/schema/mappings/). Nothing is invented: a tool
that could not be written without a field that does not exist is not here, and the ones
that were dropped for that reason are listed at the bottom.

The ES|QL tools use named parameters, written `?name`. In Agent Builder these are declared
on the tool and filled from the conversation. Types: `?lift` and `?pattern` are keywords,
`?session_id` is a keyword, and `?from` and `?to` are dates.

## The ceiling

### `lift_ceiling`

*What is the most I may suggest for this lift?* The number the load rule in
[../CEILING.md](../CEILING.md) is defined by. Run it before naming any weight.

```esql
FROM workout-sets
| WHERE lift_slug == ?lift AND set_type == "working"
    AND e1rm_confidence != "low" AND date > NOW() - 90 days
| STATS ceiling_lb = MAX(est_e1rm), heaviest_lb = MAX(weight_lb),
        last = MAX(date), sets = COUNT(*)
```

Zero rows means nothing qualifies in the window. Widen to the all-time best by dropping the
`date` clause and say the number is stale; if that is empty too, there is no ceiling and no
suggestion.

### `ceiling_evidence`

*Where did that ceiling come from?* The sets behind the number, so the suggestion can cite
one.

```esql
FROM workout-sets
| WHERE lift_slug == ?lift AND set_type == "working"
    AND e1rm_confidence != "low" AND date > NOW() - 90 days
| SORT est_e1rm DESC
| LIMIT 3
| KEEP date, session_id, exercise.name, weight_lb, reps, rpe,
       est_e1rm, e1rm_method, e1rm_confidence, notes
```

## Recall

### `recent_sessions`

*What have they been doing?* The last ten sessions as headers, with the wrap-up in their
own words.

```esql
FROM workout-sessions
| SORT date DESC
| LIMIT 10
| KEEP date, session_id, weekday, time_of_day, location.name, location.travel,
       program.block, program.phase, program.week, program.day, program.total_days,
       days_to_meet, totals.tonnage_lb, totals.working_sets, avg_working_rpe,
       metrics.bodyweight_lb, metrics.sleep_hrs, wrap_up, watch_items
```

### `session_sets`

*What happened in that session?* Every set in the order performed.

```esql
FROM workout-sets
| WHERE session_id == ?session_id
| SORT seq ASC
| LIMIT 300
| KEEP seq, exercise.name, exercise.category, exercise.equipment_names, set_type,
       weight_lb, weight_each_lb, reps, rep_unit, distance_ft, scheme, rpe,
       est_e1rm, e1rm_confidence, intensity_pct, intensity_ref, gear, notes, tags
```

### `session_notes`

*What did they write that day?* Notes in session order, watch items included.

```esql
FROM workout-notes
| WHERE session_id == ?session_id
| SORT order ASC
| LIMIT 100
| KEEP order, phase, exercise.name, set_number, text, tags
```

### `lift_history`

*Where does this lift stand?* Working sets on one lift, newest first, with the estimate and
the reference each was measured against.

```esql
FROM workout-sets
| WHERE lift_slug == ?lift AND set_type == "working"
| SORT date DESC
| LIMIT 60
| KEEP date, session_id, program.block, program.phase, weight_lb, reps, rpe,
       est_e1rm, e1rm_method, e1rm_confidence, intensity_pct, intensity_ref,
       pct_meet_max, inol, prilepin_zone, gear, notes, tags
```

### `sessions_in_range`

*This time last week. The week before the last meet.* Sessions between two dates.

```esql
FROM workout-sessions
| WHERE date >= ?from AND date <= ?to
| SORT date ASC
| LIMIT 60
| KEEP date, session_id, weekday, location.name, program.block, program.phase,
       program.week, program.day, totals.tonnage_lb, totals.working_sets,
       avg_working_rpe, inol_total, wrap_up
```

## Trend

### `week_review`

*How is the block loading?* One document per ISO week rather than thousands of sets. Reach
for this before `workout-sets` on any question spanning a week or more.

```esql
FROM workout-weekly
| SORT week_end DESC
| LIMIT 8
| KEEP iso_week, week_start, week_end, training_days, sessions, tonnage_lb,
       working_sets, reps, avg_working_rpe, inol_total, inol_hardest_lift,
       inol_hardest, inol_hardest_band, load_7d, load_28d, acwr, acwr_band,
       monotony, strain, projected_total_lb, dots, bodyweight_lb, bodyweight_source
```

`acwr` is a trend flag, not a prediction, and its load unit is tonnage because duration is
logged on almost no session. `bodyweight_source: "carried"` means the weight was carried
forward from an earlier weigh-in, so any DOTS built on it is approximate.

### `day_context`

*Bodyweight, sleep, and how much work a day carried.*

```esql
FROM workout-daily
| SORT date DESC
| LIMIT 30
| KEEP date, weekday, iso_week, sessions, tonnage_lb, working_sets, reps,
       duration_min, inol_total, load_au, avg_working_rpe, bodyweight_lb, sleep_hrs
```

### `muscle_drift`

*What has not been trained lately?* Working sets by primary muscle since a date, oldest
last-trained first.

```esql
FROM workout-sets
| WHERE set_type == "working" AND date > ?from
| MV_EXPAND muscles_primary
| STATS sets = COUNT(*), last = MAX(date) BY muscles_primary
| SORT last ASC
```

## Prep, cues and alternatives

### `warmup_history`

*How do they normally get to the working weight?* The prep sets they actually used on this
lift, newest sessions first.

```esql
FROM workout-sets
| WHERE lift_slug == ?lift AND set_type == "prep"
| SORT date DESC, seq ASC
| LIMIT 60
| KEEP date, session_id, seq, weight_lb, reps, rep_unit, rpe, gear, notes
```

### `cues_for_lift`

*What has fixed this before, in their words?* Their own cue, technique and gear notes on one
exercise. Offer these before offering a new cue.

```esql
FROM workout-notes
| WHERE exercise.slug == ?lift
| MV_EXPAND tags
| WHERE tags IN ("cue", "technique", "gear-note")
| SORT date DESC
| LIMIT 25
| KEEP date, session_id, phase, exercise.name, text, tags
```

### `open_watch_items`

*What are they keeping an eye on?* Watch items are indexed as notes with `phase: "watch"`.

```esql
FROM workout-notes
| WHERE phase == "watch"
| SORT date DESC
| LIMIT 25
| KEEP date, session_id, exercise.name, text, tags
```

### `alternatives_by_pattern`

*The rack is taken. What else have they trained this pattern with?* Substitutes drawn from
their own history rather than from a catalogue, so the suggestion is something they have
done.

```esql
FROM workout-sets
| WHERE set_type == "working" AND pattern == ?pattern AND date > NOW() - 180 days
| STATS sets = COUNT(*), best_e1rm = MAX(est_e1rm), top_lb = MAX(weight_lb),
        last = MAX(date) BY exercise.name, lift_slug
| SORT last DESC
| LIMIT 20
```

Get `?pattern` from `lift_history` on the lift being replaced: every set carries the
`pattern` of its exercise.

## The platform

### `meet_record`

*What has been done in competition?* Best made attempt per lift, per meet. Kilograms are
what the platform recorded; pounds beside them are derived.

```esql
FROM workout-meets
| WHERE made == true
| STATS best_kg = MAX(weight_kg), best_lb = MAX(weight_lb) BY meet_id, date, lift
| SORT date DESC, lift ASC
| LIMIT 60
```

### `meet_totals`

*Totals, DOTS, and how many attempts stuck.*

```esql
FROM workout-meets
| STATS total_lb = MAX(total_lb), total_kg = MAX(total_kg), dots = MAX(dots),
        bodyweight_lb = MAX(bodyweight_lb), attempts_made = MAX(attempts_made),
        attempts = COUNT(*) BY meet_id, date, name, federation
| SORT date DESC
```

### `attempt_history`

*Every attempt, made and missed.* Attempt selection is a conversation about these numbers
against the lift's estimate around that date, not a formula.

```esql
FROM workout-meets
| SORT date DESC, lift ASC, attempt_no ASC
| LIMIT 200
| KEEP date, meet_id, name, lift, attempt_no, weight_kg, weight_lb, made, best, notes
```

## Search

Two search tools, not ES|QL, because the question is about words rather than numbers. Each
queries one index and returns the matching documents.

### `note_search`

Index `workout-notes`, matched on `text`. Filters worth passing through: `date` range,
`tags`, `phase`, `exercise.slug`, `location.name`.

### `session_search`

Index `workout-sessions`, matched on `digest` — the whole session written out as a paragraph
at index time, carrying the date, place, weather, program day, top sets, equipment, every
note and the wrap-up. "How did I feel training in Las Vegas" is one hop against this rather
than a scan across notes.

Where ELSER is switched on, `ingest/setup_indices.py` adds a `semantic_text` sibling beside
each of these text fields (`text_semantic` on notes, `digest_semantic` and
`wrap_up_semantic` on sessions, `notes_semantic` on sets and meets, `watch_semantic` and
`gear_notes_semantic`), populated by `copy_to`. Where it is not, those fields do not exist.
Configure the search tools against the plain fields, which always exist, and add the
semantic sibling only on a deployment where the mapping actually has it.

## Tools that were dropped

Each of these needs a field nothing writes, so the tool would have to invent one:

- **Prescribed load or planned session.** The log records what was done, not what was
  planned. There is no target field to read, which is consistent with the coach not doing
  programming.
- **Rest between sets, bar speed, tempo.** Not logged. `tut_sec` is an estimate of time
  under tension, not a measured rest interval.
- **Pain, severity, or anything clinical.** Deliberately absent. Body awareness lives in
  `tags` as `body-awareness:<area>` and in note text, and it is not a severity scale.
- **Sleep quality, stress, HRV, nutrition.** `metrics.sleep_hrs` is hours, and nothing else
  in that family is captured.
- **A tool over `ironstack-signals`.** The verdict rows exist and the dashboards read them,
  but there is no mapping for that index in `starter/schema/mappings/` yet. Add the tool
  when the mapping lands, and write its `KEEP` against that file rather than against a
  dashboard query.
