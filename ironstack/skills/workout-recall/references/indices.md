# The indices

Seven. The first four are the log itself, written by `ingest/index_workouts.py` and
`ingest/index_meets.py` from the lifter's private repo. The next two are pre-aggregated
rollups that exist so a question about a week or a month is one small document instead of a
scan over every set they have ever logged. The seventh holds the verdicts the dashboards
show.

## `workout-sessions` — one doc per session

`session_id`, `date`, `timestamp`, `weekday`, `start_time`, `time_of_day`, `duration_min`,
`location.name` (+ optional `location.geo`, `location.travel`), `environment` (`temp_f`,
`humidity_pct`, `conditions`, `wind`, `setting`), `program` (`name`, `block`, `phase`
hypertrophy|strength|peaking, `week`, `day`, `total_days`, `meet_date`), `days_to_meet`,
`prev_session_id` / `next_session_id` / `streak_day`, optional `metrics`
(`bodyweight_lb`, `sleep_hrs`), `totals` (`tonnage_lb`, `sets`, `working_sets`, `reps`,
`exercises`), `avg_working_rpe`, `wrap_up`, `watch_items`, `gear_notes`, `source`, and
**`digest`** — the whole session written out as one paragraph at index time.

Derived: `inol_total`, `inol_by_lift` (`exercise`, `inol`, `band`), `prilepin_reps`
(`lt70`, `z70_79`, `z80_89`, `z90plus`), `fatigue_index`, `density_lb_per_min`, `load_au`,
`load_estimated`.

## `workout-sets` — one doc per set

`exercise` (`name`, `slug`, `category` prep|main|accessory, `equipment`, `emphasis`,
`equipment_ids`, `equipment_names`, `equipment_kinds`, `bar_weight_lb`), `seq`,
`set_number`, `set_type`, `weight_lb`, `weight_each_lb`, `each_side`, `scheme`, `reps`,
`rep_unit`, `distance_ft`, `load_type`, `rpe`, `volume_lb`, `cardio.*` (`distance_mi`,
`calories`, `avg_watts`, `peak_watts`, `cadence_rpm`, `peak_mph`, `avg_hr`, `max_hr`),
`gear`, `notes`, `tags` — plus denormalized `session_id`, `date`, `weekday`, `time_of_day`,
`location.name`, `location.travel`, `program.*`, `environment.*`.

Derived: `est_e1rm`, `e1rm_method`, `e1rm_confidence`, `intensity_pct`, `intensity_ref`,
`pct_meet_max`, `inol`, `prilepin_zone`, `lift_slug`, `pattern`, `muscles_primary`,
`muscles_secondary`, `lift_family`, `is_competition_lift`, `is_unilateral`, `work_ftlb`,
`tut_sec`.

## `workout-notes` — one doc per note

`phase` (`pre` | `prep` | `exercise` | `wrap-up` | **`watch`**), `exercise.name` /
`exercise.slug`, `set_number`, `order`, `text`, `tags`, with the same denormalized session
context. Watch items are indexed here too, with `phase: "watch"`, so "when was my grip last
a problem" is one query rather than a scan of session documents.

## `workout-meets` — one doc per competition attempt

`meet_id`, `date`, `name`, `federation`, `lift`, `exercise.name` / `exercise.slug`,
`attempt_no`, `weight_kg` / `weight_lb`, `made`, `best`, `notes`, plus meet-level
`total_kg` / `total_lb`, `dots`, `bodyweight_kg` / `bodyweight_lb`, `attempts_made`.

Kilograms are what the platform recorded. The pounds beside them are derived.

## `workout-daily` — one doc per training day, id = the date

`date`, `weekday`, `iso_week`, `sessions`, `tonnage_lb`, `working_sets`, `reps`,
`duration_min`, `inol_total`, `load_au`, `avg_working_rpe`, `bodyweight_lb`, `sleep_hrs`,
`prilepin_reps.*`, `best_e1rm` (`lift_slug`, `value`), `sets_by_muscle` (`muscle`, `sets`).

## `workout-weekly` — one doc per ISO week, id like `2026-W36`

`iso_week`, `week_start`, `week_end`, `training_days`, `sessions`, `tonnage_lb`,
`working_sets`, `reps`, `avg_working_rpe`, `inol_total`, `inol_hardest_lift` /
`inol_hardest` / `inol_hardest_band`, `inol_by_lift`, `prilepin_reps.*`, `load_7d`,
`load_28d`, `acwr`, `acwr_band`, `monotony`, `strain`, `bodyweight_lb`,
`bodyweight_source`, `projected_total_lb`, `dots`, `best_e1rm`, `sets_by_muscle`.

## `ironstack-signals` — one doc per verdict row

The rows behind the Signal cards on the dashboards: intensity, load, drift, block, taper,
projection, tags, weekly loading. Each row is already windowed at index time, which is why
it has one property no other index here has:

**It carries no date-typed field, on purpose.** Kibana scopes a panel to the dashboard's
time range by filtering on the index's date field, and with none there is nothing to filter
on, so a time picker cannot silently re-scope a verdict that was computed over a fixed
window. Two consequences when you query it:

- A **time range** does not apply. Do not try to narrow a signal row by date; narrow it by
  the window the row itself names.
- A **filter still does**, including a filter on a field this index does not have. A KQL
  clause on an absent field matches nothing and empties the result, which looks exactly
  like "no data" and is not.

The field list is not in `starter/schema/mappings/` yet. Until it is, the ES|QL in
`kibana/build_dashboards.py` is the reference for what each row carries, and the dashboards
are the surface for these verdicts. Prefer answering from the log and the rollups.

## Semantic siblings

Where ELSER is switched on, `ingest/setup_indices.py` adds a `semantic_text` sibling beside
each text field and populates it with `copy_to`:

| Index | Field | Sibling |
|---|---|---|
| `workout-notes` | `text` | `text_semantic` |
| `workout-sets` | `notes` | `notes_semantic` |
| `workout-meets` | `notes` | `notes_semantic` |
| `workout-sessions` | `wrap_up` | `wrap_up_semantic` |
| `workout-sessions` | `gear_notes` | `gear_notes_semantic` |
| `workout-sessions` | `watch_items` | `watch_semantic` |
| `workout-sessions` | `digest` | `digest_semantic` |

Where it is not switched on, those fields do not exist and the plain text fields do. Check
the mapping, or tolerate one query error and retry without the semantic field. The
plain-text path must always work.
