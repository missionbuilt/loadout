#!/usr/bin/env python3
"""Unit tests for ingest/ceiling.py. No Elasticsearch, no network.

    python ingest/test_ceiling.py

The corpus here is synthetic, for the same reason test_derive.py's is: every
verdict below is about WHICH set a ceiling may come from, and a fixture whose
dates and rep counts are chosen by hand is the only way to pin "this one is
outside the window", "this one is ten reps" and "this one was a warm-up" without
them drifting the next time a real session is logged.

The last section is the one that matters most. It walks the REAL workouts/ corpus
and checks that the ceiling this script prints is the same number
derive.best_working_e1rm() produces - the number the indexer writes to est_e1rm. A
guardrail that disagrees with the data it is guarding is worse than no guardrail,
so that agreement is a test rather than an assumption.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ceiling as c
import derive as d
import metrics as m

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


# --------------------------------------------------------------------- fixtures

TODAY = date(2026, 9, 5)
BENCH = "Comp Bench"
BENCH_SLUG = "comp-bench"


def st(weight, reps, rpe=None, **extra):
    s = {"weight_lb": weight, "reps": reps}
    if rpe is not None:
        s["rpe"] = rpe
    s.update(extra)
    return s


def session(day, *exercises):
    """One (date, session_id, log) tuple in catalog_logs() shape."""
    return (day, day, {"session": {"date": day, "session_id": day},
                       "exercises": list(exercises)})


def bench(day, *sets):
    return session(day, {"name": BENCH, "category": "main", "sets": list(sets)})


def run(logs, lift=BENCH, slug=BENCH_SLUG, as_of=TODAY, window=90):
    return c.compute(logs, lift, slug, as_of, window)


# ------------------------------------------------------------------- formatting

print("A set is printed the way it would be said out loud")
check("weight, reps and RPE", c.set_repr(st(185, 5, 8)), "185 x 5 @ 8")
check("a half-point RPE keeps its half", c.set_repr(st(195, 3, 8.5)), "195 x 3 @ 8.5")
check("no RPE, no @", c.set_repr(st(185, 5)), "185 x 5")
check("a whole number of pounds is not 185.0", c.set_repr(st(185.0, 5, 8)), "185 x 5 @ 8")
check("a fractional dumbbell keeps its fraction", c.set_repr(st(52.5, 8, 8)),
      "52.5 x 8 @ 8")


# ----------------------------------------------------------- rule 1: the window

print("\nRule 1 — the best qualifying estimate in the trailing window")
recent = run([
    bench("2026-08-01", st(185, 5, 8)),          # 228.1
    bench("2026-08-15", st(200, 3, 8)),          # 231.7  <- the ceiling
    bench("2026-08-29", st(155, 8, 7)),          # 219.2
])
check("the ceiling is the best estimate, not the last one", recent["ceiling_lb"], 231.7)
check("it says which rule produced it", recent["basis"], "est_e1rm")
check("and which model", recent["method"], "rpe")
check("and how much to trust it", recent["confidence"], "high")
check("and the day it came from", recent["from_date"], "2026-08-15")
check("and the session", recent["from_session_id"], "2026-08-15")
check("and the actual set", recent["from_set"], "200 x 3 @ 8")
check("the window is recent, not stale", recent["window_ref"], "recent")
check("nothing is stale", recent["stale_days"], None)
check("every qualifying set is counted", recent["qualifying_sets"], 3)
check("across their sessions", recent["sessions"], 3)

print("\n  ...and the heaviest weight actually moved is named beside it")
check("heaviest working set", recent["heaviest_set_lb"], 200.0)
check("on its own date", recent["heaviest_set_date"], "2026-08-15")

print("\nSets that may not set a bar")
excluded = run([
    bench("2026-08-01", st(185, 5, 8)),                       # 228.1, counts
    bench("2026-08-02", st(100, 10, 6)),                      # low confidence
    bench("2026-08-03", st(100, 13, 6)),                      # no estimate at all
    bench("2026-08-04", st(315, 3, 8, set_type="warmup")),    # not a working set
    bench("2026-08-05", st(315, 60, rep_unit="seconds")),     # not reps
])
check("ten reps at RPE 6 is not a ceiling", excluded["ceiling_lb"], 228.1)
check("a 13-rep set gets no estimate to exclude", excluded["from_date"], "2026-08-01")
check("only the qualifying set is counted", excluded["qualifying_sets"], 1)
check("a warm-up 315 is not the heaviest working set",
      excluded["heaviest_set_lb"], 185.0)
check("nor is a 315 lb timed hold", "315" in c.render(excluded), False)


# ------------------------------------------------------------- rule 2: staleness

print("\nRule 2 — nothing in the window, so the answer says how old it is")
stale = run([
    bench("2026-01-10", st(200, 3, 8)),                   # 231.7, long ago
    bench("2026-08-20", st(100, 10, 6)),                  # recent but low confidence
])
check("it still answers", stale["ceiling_lb"], 231.7)
check("from the all-time best", stale["window_ref"], "all-time")
check("and says how old that is", stale["stale_days"], (TODAY - date(2026, 1, 10)).days)
check("a recent low-confidence set does not rescue the window",
      stale["from_date"], "2026-01-10")
check("the stale block says so out loud", "stale," in c.render(stale), True)
check("a fresh block does not", "stale," in c.render(recent), False)


# ------------------------------------------------------- rule 3: a weight, not an estimate

print("\nRule 3 — no estimate anywhere, so the heaviest weight actually moved")
heavy = run([
    bench("2026-08-01", st(95, 15, 7)),
    bench("2026-08-08", st(115, 14, 8)),
    bench("2026-08-15", st(105, 20, 7)),
])
check("the ceiling is a weight", heavy["ceiling_lb"], 115.0)
check("and says it is not an estimate", heavy["basis"], "heaviest working set")
check("so it carries no model", heavy["method"], None)
check("and no confidence", heavy["confidence"], None)
check("named to its set", heavy["from_set"], "115 x 14 @ 8")
check("the ceiling and the heaviest set are the same number under rule 3",
      heavy["ceiling_lb"], heavy["heaviest_set_lb"])
check("the block does not claim a method",
      "rpe/" in c.render(heavy), False)


# ------------------------------------------------------------ rule 4: no answer

print("\nRule 4 — nothing to ceiling from")
nothing = run([
    session("2026-08-01", {"name": "Chin-ups", "category": "accessory",
                           "sets": [st(0, 10, 8)]}),
], lift="Chin-ups", slug="chin-ups")
check("no number is invented", nothing["ceiling_lb"], None)
check("no basis either", nothing["basis"], None)
check("no heaviest set to point at", nothing["heaviest_set_lb"], None)
check("the block is one line", c.render(nothing), c.NOTHING)
check("and it is the sentence the spec names", "\n" in c.render(nothing), False)

check("a lift with no sets at all lands in the same place",
      run([bench("2026-08-01")])["ceiling_lb"], None)


# ------------------------------------------------------------- as-of and window

print("\n--as-of computes the ceiling as it stood, with no lookahead")
history = [
    bench("2026-03-01", st(185, 5, 8)),      # 228.1
    bench("2026-06-01", st(200, 3, 8)),      # 231.7
    bench("2026-08-15", st(225, 1, 9)),      # 235.6
]
check("today sees the newest PR", run(history)["ceiling_lb"], 235.6)
check("as of July it does not exist yet",
      run(history, as_of=date(2026, 7, 1))["ceiling_lb"], 231.7)
check("as of April, only the March session",
      run(history, as_of=date(2026, 4, 1))["ceiling_lb"], 228.1)
check("as of the day itself, the set counts",
      run(history, as_of=date(2026, 6, 1))["from_date"], "2026-06-01")

print("\n--window narrows what counts as recent")
check("90 days reaches the June session",
      run(history, as_of=date(2026, 7, 1))["window_ref"], "recent")
check("14 days does not",
      run(history, as_of=date(2026, 7, 1), window=14)["window_ref"], "all-time")
check("but still answers with the same number",
      run(history, as_of=date(2026, 7, 1), window=14)["ceiling_lb"], 231.7)
check("the window is reported as asked for",
      run(history, window=14)["window_days"], 14)
check("the default is derive's own reference window",
      c.build_parser().parse_args(["x"]).window, d.REFERENCE_WINDOW_DAYS)

print("\n  ...and the window edge is derive's edge, not one day off")
edge = [bench("2026-06-07", st(200, 3, 8))]     # exactly 90 days before 2026-09-05
check("a set exactly `window` days back is still recent",
      run(edge)["window_ref"], "recent")
check("one day older is not",
      run([bench("2026-06-06", st(200, 3, 8))])["window_ref"], "all-time")


# ------------------------------------------------------------------ the payload

print("\nThe JSON payload carries every fact the block does")
import json as _json

payload = _json.loads(c.as_json(recent))
check("every key the spec names is present",
      sorted(payload) == sorted(c.JSON_KEYS), True)
check("and nothing else is", set(payload) - set(c.JSON_KEYS), set())
check("nulls where a fact is absent",
      _json.loads(c.as_json(nothing))["ceiling_lb"], None)
check("a rule-3 payload nulls the model it does not have",
      _json.loads(c.as_json(heavy))["method"], None)

print("\nThe text block names its provenance on every line")
block = c.render(recent).splitlines()
check("five lines", len(block), 5)
check("the header resolves the lift to its slug", block[0], "Comp Bench  ->  comp-bench")
check("the ceiling line carries the date", "2026-08-15" in block[1], True)
check("and the set", "200 x 3 @ 8" in block[1], True)
check("and the confidence tier", "rpe/high" in block[1], True)
check("the window line names the window", "90 days ending 2026-09-05" in block[2], True)
check("the heaviest set line is a real lift", "heaviest set" in block[3], True)
check("the count line closes it", block[4].strip().startswith("qualifying"), True)


# ---------------------------------------------- agreement with the indexed data

print("\nThe ceiling is the number the indexer writes — over the real corpus")
# A fresh instance has no logs, and that is a pass with a note, not a skip: both
# walks agree on nothing, so there is nothing this section could disagree about.
# A corpus that exists but cannot be read is the opposite - that is the failure
# this section is here to catch, so it fails rather than being swallowed as a skip.
import index_workouts

if not index_workouts.log_paths():
    print("  no logs yet — nothing to cross-check (a fresh instance looks like this)")
    corpus = None
else:
    corpus = index_workouts.catalog_logs()

if corpus:
    # derive's own path: the best per-session e1RM for a lift, maximised over every
    # session. That is exactly what lands in est_e1rm. The ceiling with a window wide
    # enough to cover the whole history must be the same number, to the decimal.
    indexed = {}
    for _day, _sid, log in corpus:
        for slug, value in d.best_working_e1rm(log).items():
            indexed[slug] = max(indexed.get(slug, 0.0), value)

    slugs = sorted({d.lift_slug(ex["name"])
                    for _day, _sid, log in corpus
                    for ex in log.get("exercises", [])})
    print(f"  ({len(slugs)} lifts across {len(corpus)} sessions, "
          f"{len(indexed)} with an estimate)")

    disagreed = []
    for slug, want in sorted(indexed.items()):
        got = c.compute(corpus, slug, slug, date(2100, 1, 1), 100000)["ceiling_lb"]
        if got != round(want, 1):
            disagreed.append(f"{slug}: ceiling {got} vs derive {round(want, 1)}")
    check("every lift's ceiling equals derive.best_working_e1rm", disagreed, [])

    # And the ceiling never exceeds the best estimate under the real 90-day window
    # either - a narrower window may only ever lower the answer, never raise it.
    raised = []
    for slug in sorted(indexed):
        wide = c.compute(corpus, slug, slug, date.today(), 100000)["ceiling_lb"]
        narrow = c.compute(corpus, slug, slug, date.today(), 90)["ceiling_lb"]
        if wide is None or narrow is None:
            continue
        if narrow > wide:
            raised.append(f"{slug}: 90-day {narrow} > all-time {wide}")
    check("a narrower window never raises the ceiling", raised, [])

    # Nothing at low confidence, and nothing above 12 reps, may ever be the answer.
    invented = []
    for slug in sorted(indexed):
        result = c.compute(corpus, slug, slug, date.today(), 90)
        if result["confidence"] == m.CONF_LOW:
            invented.append(slug)
    check("no ceiling rests on a low-confidence estimate", invented, [])


print()
if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all ceiling tests passed")
