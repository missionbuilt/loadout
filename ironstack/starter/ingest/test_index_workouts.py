#!/usr/bin/env python3
"""Unit tests for ingest/index_workouts.py. No Elasticsearch, no network.

    python ingest/test_index_workouts.py

What this file is for is the document `_id`.

On 2026-09-05 an exercise was renamed in one log and 429 documents were orphaned in
Elasticsearch. The id had been `{session_id}-{slug}-{set_type}-{set_number}`, so
renaming the lift changed the id, the reindex stopped being an upsert, and the old
documents simply stayed - every one with correct types, correct fields, and a green
index step. The scheme was changed to `{session_id}-{seq}`, and nothing tested it:
reverting that single line passed all five test files. So the invariant is written
down here, in the terms the outage was in - rename a lift, the ids do not move.
"""

import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index_workouts as iw

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


# --------------------------------------------------------------------- fixture
#
# Two exercises, one of them logged twice under the same name in the same session -
# the shape the old name-based id collided on silently. Names are real taxonomy
# entries because explode() classifies them through derive.


def log(first="Comp Bench", second="Comp Squat", third="Comp Bench"):
    """One session: 2 + 1 + 2 sets, two notes, one watch item."""
    def sets(*specs):
        return [{"set_number": n, "reps": r, "weight_lb": w, "rpe": 8,
                 "set_type": t} for n, (r, w, t) in enumerate(specs, start=1)]

    return {
        "session": {"date": "2026-03-02", "session_id": "2026-03-02",
                    "start_time": "18:00", "watch_items": ["left shoulder"]},
        "exercises": [
            {"name": first, "category": "main",
             "sets": sets((5, 225.0, "working"), (5, 235.0, "working"))},
            {"name": second, "category": "main",
             "sets": sets((3, 315.0, "working"))},
            # Same name as the first exercise, later in the session. Under the old
            # scheme this produced ids that had already been used.
            {"name": third, "category": "accessory",
             "sets": sets((8, 185.0, "working"), (8, 185.0, "working"))},
        ],
        "notes": [{"phase": "during", "text": "bar path honest"},
                  {"phase": "after", "text": "good day"}],
    }


def ids(doc, index=None):
    return [i for ix, i, _d in iw.explode(doc) if index is None or ix == index]


# ------------------------------------------------------------------- the shape

print("The set _id is {session_id}-{seq}, and nothing else")
set_ids = ids(log(), "workout-sets")
check("one id per set, in session order", set_ids,
      ["2026-03-02-1", "2026-03-02-2", "2026-03-02-3", "2026-03-02-4", "2026-03-02-5"])
check("seq counts across exercises, not within one", len(set(set_ids)), 5)
check("the session document is keyed by the session alone",
      ids(log(), "workout-sessions"), ["2026-03-02"])
check("notes and watch items keep their own suffixes", ids(log(), "workout-notes"),
      ["2026-03-02-note-1", "2026-03-02-note-2", "2026-03-02-watch-1"])

# The regression, stated as the property that failed: whatever the id is built from, it
# must not be built from anything the lifter can retype. `{session_id}-{integer}` is the
# whole grammar, so anything else in there is a name or a set_type that has crept back.
check("every id is the session id and one integer, nothing else",
      sorted({i[len("2026-03-02-"):].isdigit() for i in set_ids}), [True])
check("no set id carries an exercise slug",
      any(s in i for i in set_ids for s in ("comp-bench", "comp-squat", "feet-up")), False)
check("no set id carries a set_type",
      any(s in i for i in set_ids for s in ("working", "accessory", "prep")), False)


# ------------------------------------------------------------------- the rename

print("\nRenaming an exercise does not move a single id")
# Same session, every exercise renamed - to a different lift, and to an ALIAS of the
# same lift, which is the rename that actually happened.
renamed = ids(log(first="Competition Bench Press", second="Comp Deadlift",
                  third="Feet Up Bench"))
check("every id is unchanged after the rename", renamed, ids(log()))
check("the documents themselves did change, so the test is not vacuous",
      [d["exercise"]["name"] for ix, _i, d in iw.explode(log(first="Competition Bench Press"))
       if ix == "workout-sets"][0],
      "Competition Bench Press")


# --------------------------------------------------------------- the collision

print("\ncheck_unique_ids refuses a collision rather than letting it overwrite")


def collides(docs):
    """True when check_unique_ids exits non-zero. It reports by sys.exit(str)."""
    try:
        iw.check_unique_ids(docs)
    except SystemExit as exc:
        return bool(exc.code)
    return False


clean = iw.explode(log())
check("the real documents do not collide", collides(clean), False)

dup = clean + [(clean[0][0], clean[0][1], {**clean[0][2], "session_id": "2026-03-03"})]
check("two documents sharing an id in one index is fatal", collides(dup), True)
check("the same id in a DIFFERENT index is not a collision",
      collides(clean + [("workout-notes", clean[0][1], clean[0][2])]), False)

# And that it would have caught the 2026-09-05 outage's other half: two same-named
# exercises in one session, which the old name-based id merged into one document.
old_style = []
for index, _id, doc in clean:
    if index != "workout-sets":
        continue
    old_style.append((index, f"{doc['session_id']}-{doc['exercise']['slug']}-"
                             f"{doc['set_type']}-{doc['set_number']}", doc))
check("the old name-based id collides on this very session",
      collides(old_style), True)
check("...and the current one does not",
      collides([d for d in clean if d[0] == "workout-sets"]), False)


# ------------------------------------------------------------------ the totals
#
# The session totals are what every rollup, every card and every "lb moved" line is
# built from, and two of them were computed by a condition nothing tested.

print("\nTotals count what they say they count")


def timed(rep_unit="seconds"):
    """One barbell set and one 60-second plank, in one session."""
    return {
        "session": {"date": "2026-03-02", "session_id": "2026-03-02"},
        "exercises": [
            {"name": "Comp Squat", "category": "main",
             "sets": [{"set_number": 1, "reps": 5, "weight_lb": 300.0, "rpe": 8,
                       "set_type": "working"}]},
            {"name": "Plank", "category": "accessory",
             "sets": [{"set_number": 1, "reps": 60, "weight_lb": 45.0,
                       "rep_unit": rep_unit, "set_type": "working"}]},
        ],
    }


def session_doc(log):
    return [d for ix, _i, d in iw.explode(log) if ix == "workout-sessions"][0]


# 45 lb held for 60 seconds is not 2,700 lb moved. Tonnage is weight x REPS, and a
# seconds-based set has no reps to multiply - counting it added 2,700 lb to the day,
# the week, load_7d, the ACWR base and every tonnage_per_session in the block card.
check("a seconds-based set contributes no tonnage",
      session_doc(timed())["totals"]["tonnage_lb"], 1500.0)
check("the same set logged in reps does",
      session_doc(timed(rep_unit="reps"))["totals"]["tonnage_lb"], 4200.0)
check("and it is not silently dropped from the set count either",
      session_doc(timed())["totals"]["sets"], 2)
check("reps counts only what was logged in reps",
      session_doc(timed())["totals"]["reps"], 5)


def mixed():
    """A working set at RPE 9 and a warm-up at RPE 5, in that order."""
    return {
        "session": {"date": "2026-03-02", "session_id": "2026-03-02"},
        "exercises": [{"name": "Comp Squat", "category": "main", "sets": [
            {"set_number": 1, "reps": 5, "weight_lb": 135.0, "rpe": 5,
             "set_type": "warmup"},
            {"set_number": 2, "reps": 5, "weight_lb": 300.0, "rpe": 9,
             "set_type": "working"},
        ]}]}


# avg_working_rpe is the session's effort, and it feeds load_au, the daily and weekly
# averages and the block card's avg_working_rpe. Warm-ups are logged with an RPE too,
# and averaging them in drags every session toward the middle: 9.0 becomes 7.0 here.
check("avg_working_rpe averages working sets only",
      session_doc(mixed())["avg_working_rpe"], 9.0)
check("the warm-up is still in the session, so the test is not vacuous",
      session_doc(mixed())["totals"]["sets"], 2)
check("and is not counted as a working set", session_doc(mixed())["totals"]["working_sets"], 1)


# --------------------------------------------------------------------- streaks

print("\nstreak_day counts CONSECUTIVE days, and only consecutive days")

# Sat, Sun, Mon: three in a row. Then a day off, then Wed and Thu.
STREAK = [("2026-03-07", "a"), ("2026-03-08", "b"), ("2026-03-09", "c"),
          ("2026-03-11", "d"), ("2026-03-12", "e")]
links = iw.session_links(STREAK)
check("day one of a streak", links["a"]["streak_day"], 1)
check("day two", links["b"]["streak_day"], 2)
check("day three", links["c"]["streak_day"], 3)
# The case the `== timedelta(days=1)` comparison exists for. A two-day gap is a break;
# read as consecutive it produced a streak_day of 4 across a rest day, and the number
# on the card stopped meaning "days in a row".
check("a two-day gap restarts the count, it does not continue it",
      links["d"]["streak_day"], 1)
check("and the day after the restart is day two", links["e"]["streak_day"], 2)
# Two sessions on one day are one day of a streak.
same_day = iw.session_links([("2026-03-07", "a"), ("2026-03-07", "b"),
                             ("2026-03-08", "c")])
check("two sessions in a day do not advance the streak",
      [same_day[s]["streak_day"] for s in ("a", "b", "c")], [1, 1, 2])
check("prev/next still thread through them",
      (same_day["b"]["prev_session_id"], same_day["b"]["next_session_id"]), ("a", "c"))


# ------------------------------------------------------------------- the corpus

print("\ncatalog_logs refuses an incomplete corpus rather than analysing part of one")


class corpus:
    """A temp workouts/ directory, with derive's clock left alone."""

    def __init__(self, logs):
        self.logs = logs

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name, log in self.logs.items():
            (self.tmp / f"{name}.json").write_text(json.dumps(log))
        self.saved = iw.WORKOUTS_DIR
        iw.WORKOUTS_DIR = self.tmp
        return self

    def __exit__(self, *exc):
        iw.WORKOUTS_DIR = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False


def a_log(day, sid=None):
    return {"session": {"date": day, **({"session_id": sid} if sid else {})},
            "exercises": [{"name": "Comp Squat", "category": "main", "sets": [
                {"set_number": 1, "reps": 5, "weight_lb": 300.0, "rpe": 8,
                 "set_type": "working"}]}]}


def catalogued(logs, today=date(2026, 3, 2)):
    """The session ids catalog_logs returns, or the message it exited with."""
    with corpus(logs):
        try:
            return sorted(sid for _day, sid, _log in iw.catalog_logs(today=today))
        except SystemExit as exc:
            return str(exc.code)


check("an ordinary corpus catalogues",
      catalogued({"a": a_log("2026-03-01"), "b": a_log("2026-03-02")}),
      ["2026-03-01", "2026-03-02"])
# FUTURE_TOLERANCE_DAYS is one day, for the lifter at UTC+13 whose local date is ahead
# of the runner's. Everything past that is a mistyped year or month, and it does not
# arrive as a stray row - it becomes the NEWEST row, and every "most recent" in the
# pipeline is defined by sort order rather than by the clock.
tomorrow = catalogued({"a": a_log("2026-03-01"), "b": a_log("2026-03-03")})
check("one day ahead of the runner is a real session at UTC+13",
      tomorrow, ["2026-03-01", "2026-03-03"])
mistyped = catalogued({"a": a_log("2026-03-01"), "b": a_log("2062-03-01")})
check("a mistyped year is fatal, not the newest row", isinstance(mistyped, str), True)
check("and the message names the file and the date",
      "2062-03-01" in mistyped and "future" in mistyped, True)
check("two days ahead is already past the tolerance",
      isinstance(catalogued({"a": a_log("2026-03-04")}), str), True)

# Two files, one session_id. The bulk write is keyed by id, so the second simply
# replaces the first in Elasticsearch: no error, a correct-looking index, and one
# session's worth of work gone.
dup = catalogued({"a": a_log("2026-03-01", "same"), "b": a_log("2026-03-02", "same")})
check("two logs sharing a session_id is fatal", isinstance(dup, str), True)
check("and the message says what would have happened",
      "already used by" in dup and "overwrite" in dup, True)
check("...while two logs with distinct ids are fine",
      catalogued({"a": a_log("2026-03-01", "one"), "b": a_log("2026-03-02", "two")}),
      ["one", "two"])


# -------------------------------------------------------------------- the schema

print("\nload_schema() checks formats, not just types")

# Draft 2020-12 treats `format` as an annotation unless a checker is supplied. Without
# one, every "format": "date" in workout.schema.json is decoration: the log validates
# clean and then dies several stages later in session_links() as a bare ValueError with
# no filename in it.
validator = iw.load_schema()


def date_errors(day):
    """Only the errors about session.date, so a fixture missing some other required
    key cannot make this look like a format check that works."""
    return [e.message for e in validator.iter_errors(a_log(day, "sid"))
            if e.json_path.endswith("date")]


check("a date-shaped field holding 'banana' is a validation error",
      bool(date_errors("banana")), True)
check("and the error names the format it broke",
      any("date" in e for e in date_errors("banana")), True)
check("a real date raises nothing about the date", date_errors("2026-03-01"), [])


# --------------------------------------------------------------------- the sweeps

print("\nThe orphan sweep is scoped to what the run can actually know")


class recording:
    """Capture the queries the sweeps would have issued, instead of issuing them."""

    def __enter__(self):
        self.queries = []
        self.saved = (iw.refresh_indices, iw.delete_by_query)
        iw.refresh_indices = lambda *a, **k: None
        iw.delete_by_query = lambda index, query, what, consequence: (
            self.queries.append((index, what, query)) or {"deleted": 0, "total": 0})
        return self

    def __exit__(self, *exc):
        iw.refresh_indices, iw.delete_by_query = self.saved
        return False


SWEPT = iw.explode(a_log("2026-03-01", "one"))


def sweep(whole_corpus):
    with recording() as r:
        iw.sweep_sessions(SWEPT, {"one"}, whole_corpus=whole_corpus)
        return [what for _index, what, _q in r.queries]


# A run given explicit paths knows nothing about the 640 sessions it was not given, so
# "every document whose session_id is not in this run" is every document of every other
# session in the repo. Running the orphan sweep on a partial run deletes the corpus.
check("a whole-corpus run sweeps stale documents AND orphans",
      sorted(set(sweep(True))),
      ["orphaned workout-notes documents", "orphaned workout-sessions documents",
       "orphaned workout-sets documents", "stale workout-notes documents",
       "stale workout-sessions documents", "stale workout-sets documents"])
check("a partial run sweeps only the sessions it was given",
      sorted(set(sweep(False))),
      ["stale workout-notes documents", "stale workout-sessions documents",
       "stale workout-sets documents"])
check("no orphan query on a partial run, in any index",
      any("orphaned" in what for what in sweep(False)), False)

# The rollups are the other way round: rollup_docs() is always handed the whole corpus,
# so every run rewrites every daily and weekly row and the sweep is safe on all of them.
with recording() as r:
    iw.sweep_rollups([("workout-daily", "2026-03-01", {}),
                      ("workout-weekly", "2026-W09", {})])
    rollup_queries = r.queries
check("the rollup sweep covers both rollup indices",
      sorted(index for index, _w, _q in rollup_queries),
      ["workout-daily", "workout-weekly"])
check("and scopes by must_not ids, the exact complement of what it wrote",
      rollup_queries[0][2]["bool"]["must_not"][0]["ids"]["values"], ["2026-03-01"])


# ---------------------------------------------------------------------- the bulk

print("\nThe bulk write is chunked, by documents and by bytes")

many = [("workout-sets", f"s-{i}", {"n": i}) for i in range(2500)]
chunks = list(iw.bulk_chunks(many))
check("2,500 documents do not go out as one request", len(chunks) > 1, True)
check("no chunk exceeds the document cap",
      max(len(batch) for batch, _p in chunks) <= iw.BULK_MAX_DOCS, True)
chunked_ids = [i for batch, _p in chunks for _ix, i in batch]
check("every document is in exactly one chunk, in order",
      chunked_ids == [i for _ix, i, _d in many], True)
check("and none is dropped or repeated",
      (len(chunked_ids), len(set(chunked_ids))), (2500, 2500))
check("and each chunk is well-formed ndjson: two lines per document",
      {len(p.strip().split(chr(10))) == 2 * len(b) for b, p in chunks}, {True})

# The byte cap, not the document cap: one fat document is a different constraint from
# a thousand thin ones, and 18.4 MB in one request is what the corpus produced.
fat = [("workout-sets", f"f-{i}", {"digest": "x" * 200_000}) for i in range(60)]
fat_chunks = list(iw.bulk_chunks(fat))
check("a handful of large documents still chunks", len(fat_chunks) > 1, True)
check("no chunk exceeds the byte cap by more than one document",
      max(len(p) for _b, p in fat_chunks) < iw.BULK_MAX_BYTES + 250_000, True)
check("a single document larger than the cap still goes, alone",
      len(list(iw.bulk_chunks([("workout-sets", "huge",
                                {"d": "x" * (iw.BULK_MAX_BYTES + 10)})]))), 1)
check("nothing to write is no requests at all", list(iw.bulk_chunks([])), [])


# ------------------------------------------------------------- main()'s wiring

print("\nmain() sweeps what a run is entitled to sweep, and no more")

# The three sweeps are decided in main(), and which of them a run performs is the whole
# safety argument: the session sweep is scoped to what the run was given, the rollup
# sweep is safe on every run because rollup_docs is always given the whole corpus, and
# the signal sweep has always run unconditionally. Nothing tested that wiring, so the
# rollup sweep could be put back behind `if not opts.paths` - leaving a deleted date's
# daily row in the cluster until somebody happened to run the indexer with no arguments
# - with every test still green.


class wired:
    """Run main() against a temp corpus with the cluster calls recorded, not made."""

    def __init__(self, logs):
        self.logs = logs

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.paths = {}
        for name, log in self.logs.items():
            path = self.tmp / f"{name}.json"
            path.write_text(json.dumps(log))
            self.paths[name] = path
        self.calls = []
        self.saved = (iw.WORKOUTS_DIR, iw.bulk_index, iw.sweep_sessions,
                      iw.sweep_rollups, iw.sweep_signals)
        iw.WORKOUTS_DIR = self.tmp
        iw.bulk_index = lambda docs: self.calls.append(("bulk", len(docs)))
        iw.sweep_sessions = lambda docs, requested, whole_corpus: self.calls.append(
            ("sweep_sessions", whole_corpus))
        iw.sweep_rollups = lambda docs: self.calls.append(("sweep_rollups", None))
        iw.sweep_signals = lambda stamp: self.calls.append(("sweep_signals", None))
        return self

    def __exit__(self, *exc):
        (iw.WORKOUTS_DIR, iw.bulk_index, iw.sweep_sessions,
         iw.sweep_rollups, iw.sweep_signals) = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False


def full_log(day, sid):
    return {"session": {"date": day, "session_id": sid, "start_time": "18:00"},
            "exercises": [{"name": "Comp Squat", "category": "main", "sets": [
                {"set_number": 1, "reps": 5, "weight_lb": 300.0, "rpe": 8,
                 "set_type": "working"}]}]}


LOGS = {"a": full_log("2026-03-01", "2026-03-01"),
        "b": full_log("2026-03-02", "2026-03-02")}


def wiring(argv_paths):
    with wired(LOGS) as w:
        iw.main([str(w.paths[n]) for n in argv_paths])
        return dict(w.calls)


whole = wiring([])
partial = wiring(["a"])
check("a whole-corpus run writes", "bulk" in whole, True)
check("a whole-corpus run sweeps sessions as a whole corpus",
      whole["sweep_sessions"], True)
check("a partial run does not", partial["sweep_sessions"], False)
# The rollups are rewritten from the WHOLE corpus on both runs, so both sweep them.
check("a whole-corpus run sweeps the rollups", "sweep_rollups" in whole, True)
check("and so does a partial run - it rewrote every rollup row too",
      "sweep_rollups" in partial, True)
check("the signal sweep runs on both, as it always has",
      ("sweep_signals" in whole, "sweep_signals" in partial), (True, True))
# ...and the reason the rollup sweep is safe on a partial run, stated as a fact about
# the documents rather than as a claim in a comment.
check("a partial run writes every daily row the whole corpus has",
      partial["bulk"] >= whole["bulk"] - 2, True)


print()

# --------------------------------------------------------------- the phase vocabulary

print("\nprogram.phase is the program's word, not this author's")
# It was an enum of hypertrophy / strength / peaking, which is the arc this author's
# programs happen to use. Nothing in the pipeline branches on the value - a block is only
# ever compared against earlier blocks of the same name - so the enum bought nothing and
# cost a lifter running base / accumulation / realization every session they tried to log.
# Caught by writing eight weeks of a stranger's training and watching all 24 files refuse.
_phase_schema = iw.load_schema()


def _phase_ok(word):
    log = {
        "session": {
            "session_id": "2026-01-05", "date": "2026-01-05",
            "timezone": "America/New_York",
            "program": {"name": "P", "block": "b", "phase": word, "day": 1, "total_days": 3},
        },
        "exercises": [{"name": "Comp Bench", "category": "main",
                       "sets": [{"set_type": "working", "weight_lb": 100, "reps": 5}]}],
    }
    return not list(_phase_schema.iter_errors(log))


for word in ("hypertrophy", "strength", "peaking", "base", "accumulation", "realization",
             "GPP", "off-season"):
    check(f"phase {word!r} validates", _phase_ok(word), True)
check("an empty phase does not", _phase_ok(""), False)


# --- program.phase is never absent ------------------------------------------------
#
# 639 of 643 sessions predate program tracking. Left absent, the block timeline drew
# them as a series named "(null)" - the literal string, the largest series in the
# legend, and the one label a Lens panel cannot rename. The value is written here so
# the chart has a word to print and History's PHASE control has an option for them.
check("a session with no program phase gets one",
      iw.program_block({"name": "P", "block": "b"})["phase"], iw.UNTRACKED_PHASE)
check("a session with a phase keeps its own",
      iw.program_block({"name": "P", "block": "b", "phase": "peaking"})["phase"], "peaking")
check("a session with no program at all still gets one",
      iw.program_block({})["phase"], iw.UNTRACKED_PHASE)
# The other absent fields stay absent: a week the lifter did not record is a gap and
# has to read as one. Only `phase` is drawn as a series, and only `phase` is filled.
check("week is not invented", "week" in iw.program_block({"name": "P"}), False)
check("day is not invented", "day" in iw.program_block({"name": "P"}), False)
check("block is not invented", "block" in iw.program_block({"name": "P"}), False)


if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all index_workouts tests passed")
