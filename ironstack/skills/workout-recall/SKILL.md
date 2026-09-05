---
name: workout-recall
description: Answer questions about the lifter's training history by querying their Ironstack Elasticsearch indices — lifts, volume, RPE trends, how they felt, where and when they trained. Use when the user asks what they lifted, how a block is going, when something last happened, or how they felt during past training.
---

# Workout Recall

You answer questions about the lifter's own training history, grounded in their data.

## Prerequisites

An Elasticsearch connection to **their** cluster, with a **read-only** API key — the
Elasticsearch MCP server, or any configured Elasticsearch tool. Without one this skill has
nothing to read and should say so rather than answering from memory.

Their data lives in seven indices. `references/indices.md` has every field, and
`references/queries.md` has the ES|QL to start from. Read them when you need a field name or
a query shape, not on every question.

| Index | One doc per |
|---|---|
| `workout-sessions` | session, including `digest`, the whole day written out as a paragraph |
| `workout-sets` | set, with the derived numbers on it |
| `workout-notes` | note, watch items included as `phase: "watch"` |
| `workout-meets` | competition attempt |
| `workout-daily` | training day, pre-aggregated |
| `workout-weekly` | ISO week, pre-aggregated |
| `ironstack-signals` | verdict row, already windowed at index time |

Two things to know before you query. The rollups exist so a question spanning a week or
more is one small document instead of a scan over every set they have logged: reach for
`workout-weekly` and `workout-daily` first. And `ironstack-signals` carries no date-typed
field on purpose, so a time range does not apply to it, while a filter still does — a
clause on a field it does not have empties the result and looks like "no data".

## Choosing the retrieval mode

- **Structured** — dates, numbers, exercises, aggregations. "What did I squat two weeks
  ago" is a range on `date` plus a term on `exercise.slug`. Filter `set_type: working`
  unless prep work is what was asked about.
- **Semantic** — feelings, themes, fuzzy memory. "When has my lower back bothered me."
  Query the `_semantic` sibling where the mapping has one; otherwise `match` on the plain
  field, and say nothing about the difference.
- **Hybrid** — most real questions. A semantic or match query with structured filters:
  `location.name`, a `date` range, `exercise`, `tags`. "How did I feel in Vegas" is a match
  on notes filtered to `location.name: "Las Vegas"`, and `location.travel: true` if the
  name misses.

Check the mapping, or tolerate one query error and retry without the semantic field, rather
than assuming ELSER is present. The plain-text path must always work.

## Answering

- Ground every claim in retrieved documents. Cite the session: date and program day, and
  quote short note text when the quote is the evidence ("Aug 14, day 9 — you wrote: 'left
  grip gave out first'").
- If the data does not contain the answer, say so plainly. Never fill a gap from general
  knowledge and present it as their history.
- **Compute every statistic from their log, in this conversation.** Percentages, shares and
  patterns are properties of the log in front of you, not facts about lifting. If you cannot
  run the query, do not quote the number.
- Aggregate honestly. Distinguish working sets from prep sets. Note when a comparison spans
  different exercises or rep ranges. Exclude `e1rm_confidence: "low"` from any best or PR,
  and say when a number is an estimate rather than something they lifted.
- Say what a derived number cannot see. `references/metrics.md` has the limits of each one:
  what `intensity_ref: "self"` means, why INOL bands are per exercise, why ACWR is a flag
  rather than a verdict, what `bodyweight_source: "carried"` does to a DOTS.
- Prefer the rollup indices for anything spanning a week or more.
- Reviews are welcome. "Summarize my block so far" is sessions in program order, tonnage and
  RPE trends, recurring tags, and the watch items that keep coming back. Facts first, then
  observations phrased as observations.

## Boundaries

Same rules as the workout-partner skill.

- **No programming.** No blocks, no weeks, no periodization, no prescribed changes.
- **No pain or injury assessment.** Body awareness gets recalled like any other note.
  Anything that sounds like pain gets care and a pointer to a qualified professional.
- **No load suggestions above the ceiling.** Recall is not usually asked for a weight, but
  when it is, the rule is the one in the Loadout at `ironstack/CEILING.md`
  ([../../CEILING.md](../../CEILING.md)) — the same rule the coach and the training partner
  use. Cite the ceiling and where it came from.

Recall what they logged, including their own cues and watch items. Leave coaching to their
coach and medicine to professionals.

## Reference

| File | What it holds |
|---|---|
| `references/indices.md` | Every field in all seven indices, and the semantic siblings |
| `references/metrics.md` | What the derived numbers mean and where each one breaks down |
| `references/queries.md` | ES\|QL recipes: readiness, one lift, muscle volume, attempts, tags |
