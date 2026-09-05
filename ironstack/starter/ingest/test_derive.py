#!/usr/bin/env python3
"""Unit tests for ingest/derive.py. No Elasticsearch, no repo data, no network.

    python ingest/test_derive.py

Every case is built on a small synthetic corpus rather than on workouts/: the
verdicts these rows drive are all about WHEN a number is honest, and a fixture
whose weeks and meets are chosen by hand is the only way to pin "the week is in
progress", "this block is one session old" or "there are only two past meets"
without them drifting the next time a log is added.

`derive` reads meets/ and config/defaults.json at module scope, so the cases that
exercise a meet cycle repoint MEETS_DIR and DEFAULTS_PATH at a temp directory
they wrote themselves.
"""

import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import derive as d
import metrics as m

failures = []


def check(label, got, want, tol=None):
    ok = abs(got - want) <= tol if (tol is not None and got is not None) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


# --------------------------------------------------------------------- fixtures

ZONES = ("lt70", "z70_79", "z80_89", "z90plus")


def strip_nones(value):
    """index_workouts.strip_nones, copied rather than imported: importing the indexer
    pulls in jsonschema, and these tests are meant to run with nothing installed."""
    if isinstance(value, dict):
        return {k: strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_nones(v) for v in value]
    return value


def session(day, sid, tonnage=10000.0, block=None, rpe=7.0, **zones):
    doc = {
        "date": day,
        "session_id": sid,
        "totals": {"tonnage_lb": tonnage, "working_sets": 10, "reps": 50},
        "prilepin_reps": {z: zones.get(z, 0) for z in ZONES},
        "avg_working_rpe": rpe,
        "program": {"block": block} if block else {},
    }
    return ("workout-sessions", sid, doc)


def working_set(day, sid, n=0, muscles=(), family=None, pct=None):
    return ("workout-sets", f"{sid}:{n}", {
        "date": day,
        "session_id": sid,
        "set_type": "working",
        "rep_unit": "reps",
        "reps": 5,
        "muscles_primary": list(muscles),
        "lift_family": family,
        "intensity_pct": pct,
        "exercise": {"name": "Comp Squat", "category": "main"},
    })


def meet(day, total_kg):
    return {"date": day, "total_kg": total_kg,
            "attempts": [{"lift": "squat", "weight_kg": 180.0, "made": True}]}


def signals_by_id(docs, rollups, today):
    return {sid: doc for _index, sid, doc in d.signal_docs(docs, rollups, today=today)}


def weekly_by_week(rollups):
    return {sid: doc for index, sid, doc in rollups if index == "workout-weekly"}


class fake_meets:
    """Repoint derive at a meets/ and a defaults.json written for one test."""

    def __init__(self, meets, planned=None):
        self.meets, self.planned = meets, planned

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        # defaults.json lives OUTSIDE the meets directory, because _meet_cycles globs
        # every *.json in it and would otherwise read the config file as a meet.
        meets_dir = self.tmp / "meets"
        meets_dir.mkdir()
        for meet in self.meets:
            (meets_dir / f"{meet['date']}.json").write_text(json.dumps(meet))
        defaults = self.tmp / "defaults.json"
        defaults.write_text(json.dumps(
            {"program": {"meet_date": self.planned}} if self.planned else {"program": {}}))
        self.saved = (d.MEETS_DIR, d.DEFAULTS_PATH)
        d.MEETS_DIR, d.DEFAULTS_PATH = meets_dir, defaults
        return self

    def __exit__(self, *exc):
        d.MEETS_DIR, d.DEFAULTS_PATH = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False


# A three-week corpus. 2026-08-31 is a Monday, so 2026-09-02 is the Wednesday of
# 2026-W36 and W34/W35 are closed behind it.
WEDNESDAY = date(2026, 9, 2)
THREE_WEEKS = [
    session("2026-08-17", "s1", 10000.0, block="strength", lt70=20),
    session("2026-08-19", "s2", 12000.0, block="strength", lt70=20),
    session("2026-08-21", "s3", 8000.0, block="strength", lt70=20),
    session("2026-08-24", "s4", 11000.0, block="strength", lt70=20),
    session("2026-08-26", "s5", 9000.0, block="strength", lt70=20),
    session("2026-08-28", "s6", 13000.0, block="strength", lt70=20),
    session("2026-08-31", "s7", 10000.0, block="strength", lt70=20, z80_89=4),
    session("2026-09-01", "s8", 12000.0, block="strength", lt70=20, z80_89=2),
]


# ------------------------------------------------------- the week in progress

print("A week in progress is marked as one, everywhere it is read")
with fake_meets([]):
    rollups = d.rollup_docs(THREE_WEEKS, today=WEDNESDAY)
    weekly = weekly_by_week(rollups)
    rows = signals_by_id(THREE_WEEKS, rollups, WEDNESDAY)

check("weekly rollup: the current week", weekly["2026-W36"]["week_state"], "in-progress")
check("weekly rollup: last week", weekly["2026-W35"]["week_state"], "closed")
check("intensity row: the current week", rows["intensity:2026-W36"]["week_state"], "in-progress")
check("intensity row: last week", rows["intensity:2026-W35"]["week_state"], "closed")
check("load row: the current week", rows["load:2026-W36"]["week_state"], "in-progress")
check("load row: last week", rows["load:2026-W35"]["week_state"], "closed")

print("\nIntensity rows carry what the card needs to refuse")
check("training days come off the rollup", rows["intensity:2026-W36"]["training_days"], 2)
check("the rate is heavy / training days",
      rows["intensity:2026-W36"]["heavy_per_training_day"], 3.0)
check("a raw count is still a raw count", rows["intensity:2026-W36"]["heavy"], 6)
# Two closed weeks with main-lift work; the week in progress is not one of them.
check("weeks_available counts CLOSED weeks only",
      rows["intensity:2026-W36"]["weeks_available"], 2)
check("and is the same on every row so one query sees it",
      rows["intensity:2026-W34"]["weeks_available"], 2)
# A rollup built by rollup_docs always has at least one training day, so the guard is
# reached only by a hand-made row - which is exactly the shape a future caller could
# hand it. Checked here so the divide can never come back.
_empty_week = [("workout-weekly", "2026-W36", {
    "iso_week": "2026-W36", "week_start": "2026-08-31", "week_end": "2026-09-04",
    "training_days": 0, "prilepin_reps": {z: 0 for z in ZONES}})]
with fake_meets([]):
    _guard = [doc for _i, sid, doc in d.signal_docs([], _empty_week, today=WEDNESDAY)
              if sid == "intensity:2026-W36"][0]
check("no training days -> no rate rather than a divide by zero",
      _guard["heavy_per_training_day"], None)


# ------------------------------------------- monotony over elapsed days only

print("\nMonotony and strain: un-elapsed days are not rest days")
w36 = weekly["2026-W36"]
elapsed = m.monotony([10000.0, 12000.0, 0.0])                     # Mon, Tue, today
padded = m.monotony([10000.0, 12000.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # the old window
check("the in-progress week is measured over the 3 elapsed days", w36["monotony"], elapsed)
check("which is not what padding it to seven said", w36["monotony"] == padded, False)
check("strain follows the clamped monotony", w36["strain"], m.strain(w36["tonnage_lb"], elapsed))

# The whole point of the clamp is that it is a no-op on a week that has ended.
with fake_meets([]):
    later = weekly_by_week(d.rollup_docs(THREE_WEEKS, today=date(2027, 1, 1)))
for week in ("2026-W34", "2026-W35"):
    check(f"{week} monotony is unchanged by the clamp",
          weekly[week]["monotony"], later[week]["monotony"])
    check(f"{week} strain is unchanged by the clamp",
          weekly[week]["strain"], later[week]["strain"])
check("2026-W34 is still the full seven days: Mon/Wed/Fri and four zeros",
      weekly["2026-W34"]["monotony"],
      m.monotony([10000.0, 0.0, 12000.0, 0.0, 8000.0, 0.0, 0.0]))


# ------------------------------------------------------------ the taper rows

print("\nTaper: a cycle with no closed week ships no cumulative at all")
# The log begins in the week in progress, so every earlier week of the run-in is
# before the corpus and every later one is in the future: one row, still open.
one_week = [session("2026-08-31", "t1", 10000.0, lt70=20),
            session("2026-09-01", "t2", 12000.0, lt70=20)]
with fake_meets([], planned="2026-10-24"):
    taper = [(sid, doc) for _i, sid, doc in
             d.signal_docs(one_week, d.rollup_docs(one_week, today=WEDNESDAY),
                           today=WEDNESDAY)
             if doc["signal"] == "taper"]
check("exactly one taper row", len(taper), 1)
row = strip_nones(taper[0][1])
check("and it is the week in progress", row["week_state"], "in-progress")
check("cum_weeks is dropped, not zero", "cum_weeks" in row, False)
check("cum_tonnage_lb is dropped, not zero", "cum_tonnage_lb" in row, False)
check("cum_heavy is dropped, not zero", "cum_heavy" in row, False)
check("the row itself still ships, with its own week", row["iso_week"], "2026-W36")
check("cycle_role is untouched", row["cycle_role"], "current")

print("\nTaper: with closed weeks behind it, the current cycle accumulates")
with fake_meets([], planned="2026-10-24"):
    taper = {sid: doc for _i, sid, doc in
             d.signal_docs(THREE_WEEKS, rollups, today=WEDNESDAY)
             if doc["signal"] == "taper"}
open_row = taper["taper:2026-10-24:8"]
check("the in-progress row now has closed weeks to count", open_row["cum_weeks"], 2)
check("cum_tonnage_lb over W34 and W35", open_row["cum_tonnage_lb"], 63000.0)
check("the week in progress is still excluded from them",
      open_row["cum_tonnage_lb"] == 63000.0 + open_row["tonnage_lb"], False)
check("weeks_out is still measured from the meet, not from today",
      open_row["weeks_out"], 8)


print("\nTaper: the cumulative is the same measurement on every cycle")
# Twenty-two identical training weeks - Mon/Wed/Fri, 30,000 lb a week - and three meets
# laid over them. Identical weeks are the point: if the window is symmetric, two rows at
# the same weeks_out with the same amount of log behind them must agree to the pound.
def weekly_training(first_monday, weeks, offsets=(0, 2, 4), tonnage=10000.0):
    start = date.fromisoformat(first_monday)
    return [session((start + timedelta(days=7 * w + off)).isoformat(),
                    f"w{w:02d}d{off}", tonnage, lt70=10)
            for w in range(weeks) for off in offsets]


SYMMETRY = weekly_training("2026-01-05", 22)          # 2026-W02 .. 2026-W23
SYM_TODAY = date(2026, 6, 10)
# early:  weeks_out 8 lands on 2026-W03, only one logged week behind it
# middle: weeks_out 8 lands on 2026-W12, a full eight behind it
# late:   weeks_out 8 lands on 2026-W16, a full eight behind it
with fake_meets([meet("2026-03-07", 400.0), meet("2026-05-09", 400.0),
                 meet("2026-06-06", 400.0)]):
    sym = {sid: doc for _i, sid, doc in
           d.signal_docs(SYMMETRY, d.rollup_docs(SYMMETRY, today=SYM_TODAY),
                         today=SYM_TODAY)
           if doc["signal"] == "taper"}

early, middle, late = "2026-03-07", "2026-05-09", "2026-06-06"
check("two cycles with a full window behind weeks_out 8 agree on cum_weeks",
      sym[f"taper:{middle}:8"]["cum_weeks"], sym[f"taper:{late}:8"]["cum_weeks"])
check("and on the tonnage that window spans",
      sym[f"taper:{middle}:8"]["cum_tonnage_lb"], sym[f"taper:{late}:8"]["cum_tonnage_lb"])
check("which is the full eight weeks", sym[f"taper:{late}:8"]["cum_weeks"], 8)
check("at 30,000 lb a week", sym[f"taper:{late}:8"]["cum_tonnage_lb"], 240000.0)
# The early cycle reports what it actually has rather than reaching for a peer's span.
check("a cycle with one week of history behind weeks_out 8 says one",
      sym[f"taper:{early}:8"]["cum_weeks"], 1)
check("and does not borrow the other cycles' tonnage",
      sym[f"taper:{early}:8"]["cum_tonnage_lb"], 30000.0)
check("it is smaller, which is the signal the card declines on",
      sym[f"taper:{early}:8"]["cum_weeks"] < sym[f"taper:{late}:8"]["cum_weeks"], True)
# By weeks_out 1 the early cycle has caught up, and all three agree again.
check("all three cycles agree at weeks_out 1",
      len({sym[f"taper:{c}:1"]["cum_weeks"] for c in (early, middle, late)}), 1)
check("on the same span, to the pound",
      len({sym[f"taper:{c}:1"]["cum_tonnage_lb"] for c in (early, middle, late)}), 1)
check("every cycle still emits its own eight rows",
      len([k for k in sym if k.startswith(f"taper:{late}:")]), 8)


# ------------------------------------------------------------- the block card

print("\nBlocks: a fragment gets no peer comparison")
# strength(5), hypertrophy(5), strength(5), hypertrophy(5), then one strength session.
def run(block, days, **zones):
    return [session(day, f"{block}-{day}", 10000.0, block=block, **zones)
            for day in days]


def span(first, n, step=1):
    start = date.fromisoformat(first)
    return [(start + timedelta(days=step * i)).isoformat() for i in range(n)]


fragment_corpus = (
    run("strength", span("2026-01-05", 5), z80_89=10)
    + run("hypertrophy", span("2026-02-02", 5), lt70=50)
    + run("strength", span("2026-03-02", 5), z80_89=10)
    + run("hypertrophy", span("2026-04-06", 5), lt70=50)
    + run("strength", span("2026-05-04", 1), z80_89=10)
)
with fake_meets([]):
    blocks = signals_by_id(fragment_corpus,
                           d.rollup_docs(fragment_corpus, today=date(2026, 5, 6)),
                           date(2026, 5, 6))
current = blocks["block:0"]
check("the current run is one session", current["sessions"], 1)
check("so it is not rankable", current["rankable"], False)
check("no peers count is attached", "peers" in current, False)
check("no peer_heavy_per_session", "peer_heavy_per_session" in current, False)
check("no peer_window_sessions", "peer_window_sessions" in current, False)

print("\nBlocks: peers are truncated to the same number of sessions")
# Two ten-session strength peers with every heavy rep in their last four sessions,
# and a current strength block six sessions in. Full-block rate 4.0/session; through
# their own first six sessions, 0.0. Comparing 1.0 against 4.0 measures the calendar.
def back_loaded(block, first):
    days = span(first, 10)
    return ([session(day, f"{block}-{day}", 10000.0, block=block, lt70=10)
             for day in days[:6]]
            + [session(day, f"{block}-{day}", 10000.0, block=block, z80_89=10)
               for day in days[6:]])


loaded_corpus = (
    back_loaded("strength", "2026-01-05")
    + run("deload", span("2026-02-02", 5), lt70=10)
    + back_loaded("strength", "2026-03-02")
    + run("deload", span("2026-04-06", 5), lt70=10)
    + [session(day, f"cur-{day}", 10000.0, block="strength", z80_89=1)
       for day in span("2026-05-04", 6)]
)
with fake_meets([]):
    blocks = signals_by_id(loaded_corpus,
                           d.rollup_docs(loaded_corpus, today=date(2026, 5, 12)),
                           date(2026, 5, 12))
current = blocks["block:0"]
check("the current block is six sessions in", current["sessions"], 6)
check("its own rate", current["heavy_per_session"], 1.0)
check("the peer window is that same length", current["peer_window_sessions"], 6)
check("peers measured through their first six sessions", current["peer_heavy_per_session"], 0.0)
check("the full-block median survives under its own name",
      current["peer_heavy_per_session_full"], 4.0)
check("both peers were counted", current["peers"], 2)


# ------------------------------------------------------------------- drift

print("\nDrift: cadence is the muscle's own span, not a fixed 365")
TODAY = date(2026, 9, 5)
first = TODAY - timedelta(days=60)
drift_corpus = []
for i, offset in enumerate((60, 40, 20)):
    day = (TODAY - timedelta(days=offset)).isoformat()
    drift_corpus.append(session(day, f"lb{i}", 10000.0, lt70=10))
    drift_corpus.append(working_set(day, f"lb{i}", i, muscles=("lower-back",)))
with fake_meets([]):
    rows = signals_by_id(drift_corpus, d.rollup_docs(drift_corpus, today=TODAY), TODAY)
lower = rows["drift:lower-back"]
check("three sessions in the window", lower["sessions"], 3)
check("first_trained is on the row", lower["first_trained"], first.isoformat())
# 61 days of span (inclusive) over 3 sessions.
check("cadence is ~20 days", lower["cadence_days"], 20.33)
check("not 365/3", lower["cadence_days"] == round(d.DRIFT_WINDOW_DAYS / 3, 2), False)
check("window_days is kept so the card can still say 'the last year'",
      lower["window_days"], 365)


# -------------------------------------------------------------- projection

print("\nProjection: it refuses below PROJECTION_MIN_PEERS, and dates its evidence")
check("the threshold is three", d.PROJECTION_MIN_PEERS, 3)


# One closed week ending on or before each meet - that is the projection the lifter
# would have been shown walking in - and one for the week the corpus ends on.
PROJ_WEEKS = [("workout-weekly", week, {
    "iso_week": week, "week_end": end, "projected_total_lb": projected})
    for week, end, projected in (
        ("2024-W13", "2024-03-31", 800.0),
        ("2024-W45", "2024-11-10", 850.0),
        ("2025-W45", "2025-11-09", 875.0),
        ("2026-W36", "2026-09-04", 900.0),
    )]

with fake_meets([meet("2024-04-06", 380.0), meet("2024-11-16", 410.0)]):
    now = strip_nones([doc for _i, sid, doc in
                       d._projection_rows(PROJ_WEEKS, TODAY, TODAY.isoformat())
                       if sid == "projection:now"][0])
check("two meets is below the threshold", now["peers"], 2)
check("so no expected_lb ships", "expected_lb" in now, False)
check("and no peer_pct either", "peer_pct" in now, False)
check("the row still ships, so the card can explain itself",
      now["projected_total_lb"], 900.0)
check("with the oldest meet it is reasoning from", now["peer_from"], "2024-04-06")
check("and the newest", now["peer_to"], "2024-11-16")
check("peer_from is a plain string, never a date object", isinstance(now["peer_from"], str), True)

with fake_meets([meet("2024-04-06", 380.0), meet("2024-11-16", 410.0),
                 meet("2025-11-15", 400.0)]):
    now = strip_nones([doc for _i, sid, doc in
                       d._projection_rows(PROJ_WEEKS, TODAY, TODAY.isoformat())
                       if sid == "projection:now"][0])
check("three meets clears it", now["peers"], 3)
check("and a figure ships", "expected_lb" in now, True)
check("spanning both ends of the evidence", (now["peer_from"], now["peer_to"]),
      ("2024-04-06", "2025-11-15"))


# ----------------------------------------------------------------- _median

print("\n_median")
check("odd length takes the middle", d._median([1.0, 5.0, 100.0]), 5.0)
check("even length takes the mean of the middle two", d._median([1.0, 3.0, 5.0, 9.0]), 4.0)
check("a single element is itself", d._median([7.25]), 7.25)
check("it sorts first", d._median([100.0, 1.0, 5.0]), 5.0)
check("nothing to take a median of", d._median([]), None)
check("and it is a median, not a mean, so one outlier does not move it",
      d._median([1.0, 1.0, 1.0, 1.0, 400.0]), 1.0)


# --------------------------------------------------------------- the glosses

print("\nBand glosses reach the row")
check("the weekly rollup carries the INOL sentence",
      weekly["2026-W36"]["inol_hardest_gloss"] is None
      or isinstance(weekly["2026-W36"]["inol_hardest_gloss"], str), True)
check("a known INOL band's sentence", m.inol_week_gloss(2.5), "tough but repeatable")
check("a known ACWR band's sentence", m.acwr_gloss(1.37),
      "loading faster than the 28-day base")
check("no value, no sentence", m.acwr_gloss(None), None)

print()
if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all derive tests passed")
