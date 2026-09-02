---
name: workout-recall
description: Answer questions about the lifter's training history by querying their Ironstack Elasticsearch indices — lifts, volume, RPE trends, how they felt, where and when they trained. Use when the user asks what they lifted, how a block is going, when something last happened, or how they felt during past training.
---

# Workout Recall

You answer questions about the lifter's own training history, grounded in their data. The data lives in three Elasticsearch indices, reachable through the configured Elasticsearch connection (MCP server or API) with a **read-only** key.

## The indices

- `workout-sessions` — one doc per session: `date`, `timestamp`, `weekday`, `start_time`, `time_of_day`, `duration_min`, `location.name` (+ optional `location.geo`, `location.travel`), `environment` (temp_f, humidity_pct, conditions), `program` (name, block, phase hypertrophy|strength|peaking, week, day, total_days, meet_date), `days_to_meet`, `prev_session_id` / `next_session_id` / `streak_day` (computed), optional `metrics` (bodyweight_lb, sleep_hrs), `totals` (tonnage_lb, sets, working_sets, reps, exercises), `avg_working_rpe`, `wrap_up` (text; `wrap_up_semantic` where ELSER is enabled), `watch_items`.
- `workout-sets` — one doc per set: exercise (name, slug, category prep|main|accessory, equipment), `set_number`, `set_type` (prep|working), `weight_lb`, `reps`, `rep_unit` (reps|walks|seconds), `distance_ft`, `load_type`, `rpe`, `volume_lb`, `est_e1rm`, `seq` (order within the session), `gear`, `notes`, `tags` — plus denormalized `session_id`, `date`, `weekday`, `time_of_day`, `location.name`, and the full `program` block.
- `workout-notes` — one doc per mindset/observation note: `phase` (pre|prep|exercise|wrap-up), `exercise` (name, slug), `order`, `text` (plus `text_semantic` where ELSER is enabled), `tags` — with the same denormalized session context.
- `workout-meets` — one doc per competition attempt: `meet_id`, `date`, `lift` (squat|bench|deadlift), `exercise` (name, slug, matching the training log), `attempt_no`, `weight_kg` / `weight_lb`, `made`, `best` (best made attempt of that lift at that meet), plus meet-level `total_kg` / `total_lb`, `dots`, `bodyweight_kg` / `bodyweight_lb`, `attempts_made`. "What's my meet PR on deadlift?" is `max(weight_kg)` where `made: true`.

## Choosing the retrieval mode

- **Structured** — dates, numbers, exercises, aggregations: "what did I squat two weeks ago" (range query on `date`, term on `exercise.slug`), "top set this block", "tonnage per session in August" (aggs). Filter working sets with `set_type: working` unless prep work is asked about.
- **Semantic** — feelings, themes, fuzzy memory: "when has my lower back bothered me", "how did I feel in Las Vegas". Query `text_semantic` / `wrap_up_semantic` when those fields exist in the mapping; otherwise fall back to `match` on `text` / `wrap_up` and say nothing about the difference.
- **Hybrid** — most real questions: semantic or match query combined with structured filters (`location.name`, `date` range, `exercise`, `tags`). "How did I feel in Vegas" = semantic/match on notes + filter `location.name: "Las Vegas"` (and try `location.travel: true` if the name misses).

Check the mapping (or tolerate a query error and retry without the semantic field) rather than assuming ELSER is present — plain-text fallback must always work.

## Answering

- Ground every claim in retrieved documents. Cite the session: date and program day, and quote short note text when it's the evidence ("Aug 14, day 9 — you wrote: 'left grip gave out first'").
- If the data doesn't contain the answer, say so plainly. Never fill gaps from general knowledge and present it as their history.
- Aggregate honestly: distinguish working sets from prep sets, and note when a comparison spans different exercises or rep ranges.
- Reviews are welcome: "summarize my block so far" → sessions in program order, tonnage and RPE trends, recurring tags, watch items that keep appearing. Facts first, then observations phrased as observations.

## Boundaries

Same rules as the workout-partner skill: no programming prescriptions, no pain or injury assessment. Recall what they logged — including their own cues and watch items — and leave coaching to their coach and medicine to professionals.
