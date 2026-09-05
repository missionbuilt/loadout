# Workout Recall — Design Spec

Why the skill is shaped this way. Read this before editing `SKILL.md` or the references.
For *using* the skill, see `SKILL.md`.

## Thesis

The lifter already owns the data. The skill's whole job is to answer from it and to be
visibly honest about the edges: which number is an estimate, which reference it was measured
against, and what the log simply does not contain.

## The body is judgement; the references are lookup

`SKILL.md` loads on every trigger, including "what did I squat last week". A field catalogue
in the body costs that question the whole catalogue. So the split is:

- **Body** — prerequisites, how to choose a retrieval mode, how to answer, the boundaries.
  Everything that changes what Claude *does*.
- **`references/indices.md`** — the field catalogue, read when a field name is needed.
- **`references/metrics.md`** — what each derived number means and where it breaks down.
- **`references/queries.md`** — ES|QL recipes, read when a query shape is needed.

Adding a field goes in the reference. Adding a rule goes in the body. If the body grows a
list of field names again, it has drifted.

## No borrowed statistics

An early version of this skill quoted the author's own corpus: a set count, the share of
sets measured against themselves, the percentage of meet openers that got made. Every one of
those reads to a stranger as a claim about *their* log, and it was wrong for them by
construction.

The rule now: any figure the skill states is computed in the conversation, from the log in
front of it. `references/queries.md` carries the query instead of the answer. This is the
same principle the dashboards follow when they refuse to hardcode a personal record into a
panel title.

## Retrieval modes

Structured, semantic, hybrid — chosen by the question, not by preference. Semantic fields
are optional infrastructure (`ES_SEMANTIC=auto|on|off`), so every semantic path has a
plain-text fallback and the skill never tells the lifter which one it used.

## Rollups first

`workout-daily` and `workout-weekly` exist so a question about a week is one document rather
than thousands of sets. The skill is told to reach for them before `workout-sets` on
anything spanning a week or more.

## `ironstack-signals` is documented, not queried

The seventh index carries the dashboards' verdict rows, and it has no date-typed field so a
time picker cannot re-scope a verdict. The skill needs to know that — a KQL filter on an
absent field silently empties a result, which looks like "no data" — but its field list is
not in `starter/schema/mappings/` yet, so the reference points at the dashboard build rather
than inventing names. Add the fields to the reference when the mapping lands.

## The ceiling lives in one file

Load suggestions are governed by `ironstack/CEILING.md`, which the training partner and the
coach also cite. The rule is not restated here. A second copy is a second rule.

## Boundaries

No programming, no injury assessment. Identical wording in spirit to the workout-partner
skill, because a lifter should not be able to route around a boundary by asking the other
half of the product.
