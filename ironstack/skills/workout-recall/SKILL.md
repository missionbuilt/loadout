---
name: workout-recall
description: Answer questions about the lifter's training history by querying their Ironstack Elasticsearch indices — lifts, volume, RPE trends, how they felt, where and when they trained. Use when the user asks what they lifted, how a block is going, when something last happened, or how they felt during past training.
---

# Workout Recall

You answer questions about the lifter's own training history, grounded in their data. The data lives in three Elasticsearch indices, reachable through the configured Elasticsearch connection (MCP server or API) with a **read-only** key.

## The indices

Six indices. The first four are the log; the last two are pre-aggregated rollups that exist so
a question about a week or a month is one small document instead of a scan over 12,922 sets.

- `workout-sessions` — one doc per session: `date`, `timestamp`, `weekday`, `start_time`,
  `time_of_day`, `duration_min`, `location.name` (+ optional `location.geo`, `location.travel`),
  `environment` (temp_f, humidity_pct, conditions), `program` (name, block, phase
  hypertrophy|strength|peaking, week, day, total_days, meet_date), `days_to_meet`,
  `prev_session_id` / `next_session_id` / `streak_day`, optional `metrics` (bodyweight_lb,
  sleep_hrs), `totals` (tonnage_lb, sets, working_sets, reps, exercises), `avg_working_rpe`,
  `wrap_up`, `watch_items`, `gear_notes`, and **`digest`** — the whole session written out as one
  paragraph at index time. Semantic siblings where ELSER is on: `digest_semantic`,
  `wrap_up_semantic`, `watch_semantic`, `gear_notes_semantic`.
  Derived: `inol_total`, `inol_by_lift` (exercise, inol, band), `prilepin_reps`
  (lt70/z70_79/z80_89/z90plus), `fatigue_index`, `density_lb_per_min`, `load_au`,
  `load_estimated`.
- `workout-sets` — one doc per set: exercise (name, slug, category prep|main|accessory,
  equipment, equipment_ids/names/kinds, bar_weight_lb), `set_number`, `set_type`, `weight_lb`,
  `weight_each_lb`, `each_side`, `scheme`, `reps`, `rep_unit`, `distance_ft`, `load_type`, `rpe`,
  `volume_lb`, `cardio.*`, `seq`, `gear`, `notes` (+ `notes_semantic`), `tags` — plus
  denormalized `session_id`, `date`, `weekday`, `time_of_day`, `location.name`, `program`.
  Derived: `est_e1rm`, `e1rm_method`, `e1rm_confidence`, `intensity_pct`, `intensity_ref`,
  `pct_meet_max`, `inol`, `prilepin_zone`, `lift_slug`, `pattern`, `muscles_primary`,
  `muscles_secondary`, `lift_family`, `is_competition_lift`, `is_unilateral`, `work_ftlb`,
  `tut_sec`.
- `workout-notes` — one doc per note: `phase` (pre|prep|exercise|wrap-up|**watch**), `exercise`,
  `order`, `text` (+ `text_semantic`), `tags`, with the same denormalized session context. Watch
  items are indexed here too, with `phase: "watch"`, so "when was my grip last a problem" is one
  query.
- `workout-meets` — one doc per competition attempt: `meet_id`, `date`, `lift`, `exercise`,
  `attempt_no`, `weight_kg` / `weight_lb`, `made`, `best`, plus meet-level `total_kg` / `total_lb`,
  `dots`, `bodyweight_kg` / `bodyweight_lb`, `attempts_made`.
- `workout-daily` — one doc per training day, id = the date: `sessions`, `tonnage_lb`,
  `working_sets`, `reps`, `duration_min`, `inol_total`, `load_au`, `avg_working_rpe`,
  `bodyweight_lb`, `sleep_hrs`, `prilepin_reps`, `best_e1rm` (lift_slug, value),
  `sets_by_muscle` (muscle, sets).
- `workout-weekly` — one doc per ISO week, id like `2026-W36`: `week_start`, `week_end`,
  `training_days`, `sessions`, `tonnage_lb`, `working_sets`, `reps`, `avg_working_rpe`,
  `inol_total`, `inol_hardest_lift` / `inol_hardest` / `inol_hardest_band`, `inol_by_lift`,
  `prilepin_reps`, `load_7d`, `load_28d`, `acwr`, `acwr_band`, `monotony`, `strain`,
  `bodyweight_lb`, `bodyweight_source`, `projected_total_lb`, `dots`, `best_e1rm`,
  `sets_by_muscle`.

## What the derived numbers mean, and their limits

Say these out loud when you use them; they are estimates with known edges.

- **`est_e1rm`** comes from Tuchscherer's RPE table where an RPE was logged (`e1rm_method: "rpe"`)
  and from Epley where one was not. `e1rm_confidence` is `high` at 6 reps or fewer, `medium` at
  7 to 9, `low` at 10 to 12; nothing above 12 gets an estimate at all. **Ignore `low` when you
  are quoting a best or a personal record** — a ten-rep set at RPE 6 is an extrapolation.
- **`intensity_pct`** is the set's weight against that lift's best estimate *at the time*, taken
  from a trailing 90 days. `intensity_ref` says which reference was used: `recent`, `all-time`
  (nothing in the window), or `self` (no history, measured against its own estimate). Roughly
  44% of working sets are `self` — accessories. Do not read those as true relative intensity.
- **`inol` and `prilepin_zone`** are main-lift metrics. `inol` is only written on
  `exercise.category: "main"` sets. INOL bands are **per exercise**: per session 0.4–1 optimal,
  1–2 loading, above 2 brutal; per week under 2 easy, 2–3 loading, 3–4 brutal, above 4 excessive.
  Never band a session or week total.
- **`projected_total_lb` and `dots`** count the competition lifts only. A high-bar squat or a
  wide-grip bench belongs to the same `lift_family` but does not transfer to the platform.
- **`acwr`** is a trend flag, not a prediction, and the load unit is tonnage rather than session
  RPE times duration, because duration is logged on almost no historical session. Treat a spike
  as a prompt to look, never as a verdict.
- **`bodyweight_source: "carried"`** means the figure was carried forward from the last known
  weigh-in, possibly months earlier. Any DOTS built on it is approximate.

## Query recipes

**Readiness, the last four weeks.**
```
FROM workout-weekly | SORT @timestamp DESC | LIMIT 4
| KEEP iso_week, training_days, tonnage_lb, acwr, acwr_band, monotony, strain,
       inol_hardest_lift, inol_hardest, inol_hardest_band, avg_working_rpe
```

**Where one lift stands.**
```
FROM workout-sets
| WHERE set_type == "working" AND lift_slug == "comp-deadlift" AND e1rm_confidence != "low"
| STATS best = MAX(est_e1rm), top = MAX(weight_lb), last = MAX(date), sets = COUNT(*)
```

**Attempt history, and what percentage actually gets made.**
```
FROM workout-meets | WHERE made == true
| STATS best = MAX(weight_kg) BY lift, meet_id | SORT meet_id DESC
```
For attempt selection, pair this with the lift's `est_e1rm` around that meet date. The pattern
in this lifter's own record: openers made at about 87% of estimate, missed at about 90%.

**Volume by muscle over a block.**
```
FROM workout-sets | WHERE set_type == "working" AND program.block == "strength"
| MV_EXPAND muscles_primary | STATS sets = COUNT(*) BY muscles_primary | SORT sets DESC
```

**How a session felt, without a join.** Search `digest_semantic` on `workout-sessions` — the
digest already contains the date, place, weather, lifts, totals, notes and wrap-up, so
"how did I feel training in Las Vegas" is one hop rather than a scan over notes.

## Choosing the retrieval mode

- **Structured** — dates, numbers, exercises, aggregations: "what did I squat two weeks ago" (range query on `date`, term on `exercise.slug`), "top set this block", "tonnage per session in August" (aggs). Filter working sets with `set_type: working` unless prep work is asked about.
- **Semantic** — feelings, themes, fuzzy memory: "when has my lower back bothered me", "how did I feel in Las Vegas". Query `text_semantic` / `wrap_up_semantic` when those fields exist in the mapping; otherwise fall back to `match` on `text` / `wrap_up` and say nothing about the difference.
- **Hybrid** — most real questions: semantic or match query combined with structured filters (`location.name`, `date` range, `exercise`, `tags`). "How did I feel in Vegas" = semantic/match on notes + filter `location.name: "Las Vegas"` (and try `location.travel: true` if the name misses).

Check the mapping (or tolerate a query error and retry without the semantic field) rather than assuming ELSER is present — plain-text fallback must always work.

## Answering

- Ground every claim in retrieved documents. Cite the session: date and program day, and quote short note text when it's the evidence ("Aug 14, day 9 — you wrote: 'left grip gave out first'").
- If the data doesn't contain the answer, say so plainly. Never fill gaps from general knowledge and present it as their history.
- Aggregate honestly: distinguish working sets from prep sets, and note when a comparison spans different exercises or rep ranges. Exclude `e1rm_confidence: "low"` from any best or PR.
- Prefer the rollup indices for anything spanning a week or more. They are one document per week rather than thousands of sets, and they already carry ACWR, monotony, INOL and DOTS.
- Reviews are welcome: "summarize my block so far" → sessions in program order, tonnage and RPE trends, recurring tags, watch items that keep appearing. Facts first, then observations phrased as observations.

## Boundaries

Same rules as the workout-partner skill: no programming prescriptions, no pain or injury assessment. Recall what they logged — including their own cues and watch items — and leave coaching to their coach and medicine to professionals.
