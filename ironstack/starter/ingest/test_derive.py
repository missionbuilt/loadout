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
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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


def session(day, sid, tonnage=10000.0, block=None, rpe=7.0, bodyweight=None, **zones):
    doc = {
        "date": day,
        "session_id": sid,
        "totals": {"tonnage_lb": tonnage, "working_sets": 10, "reps": 50},
        "prilepin_reps": {z: zones.get(z, 0) for z in ZONES},
        "avg_working_rpe": rpe,
        "program": {"block": block} if block else {},
    }
    if bodyweight is not None:
        doc["metrics"] = {"bodyweight_lb": bodyweight}
    return ("workout-sessions", sid, doc)


def e1rm_set(day, sid, slug, value):
    """A working set carrying an estimate, which is all rollup_docs reads them for."""
    return ("workout-sets", f"{sid}:{slug}", {
        "date": day, "session_id": sid, "set_type": "working", "rep_unit": "reps",
        "reps": 1, "est_e1rm": value, "e1rm_confidence": m.CONF_HIGH,
        "lift_slug": slug, "muscles_primary": [],
        "exercise": {"name": "Comp Squat", "category": "main"},
    })


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
            # attempt_no is schema-required and was omitted here for years, because
            # nothing that read this fixture needed it. derive now reads a meet through
            # the indexer's normaliser, so the fixture has to be a meet the indexer
            # would accept - which is the right constraint on a fixture standing in for
            # a real file.
            "attempts": [{"lift": "squat", "attempt_no": 1, "weight_kg": 180.0,
                          "made": True}]}


def signals_by_id(docs, rollups, today):
    return {sid: doc for _index, sid, doc in d.signal_docs(docs, rollups, today=today)}


def weekly_by_week(rollups):
    return {sid: doc for index, sid, doc in rollups if index == "workout-weekly"}


class fake_meets:
    """Repoint derive at a meets/ and a defaults.json written for one test."""

    def __init__(self, meets, planned=None, lifter=None, timezone=None):
        self.meets, self.planned = meets, planned
        self.lifter, self.timezone = lifter, timezone

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        # defaults.json lives OUTSIDE the meets directory, because _meet_cycles globs
        # every *.json in it and would otherwise read the config file as a meet.
        meets_dir = self.tmp / "meets"
        meets_dir.mkdir()
        for meet in self.meets:
            (meets_dir / f"{meet['date']}.json").write_text(json.dumps(meet))
        defaults = self.tmp / "defaults.json"
        config = {"program": {"meet_date": self.planned} if self.planned else {}}
        if self.lifter is not None:
            config["lifter"] = self.lifter
        if self.timezone is not None:
            config["session"] = {"timezone": self.timezone}
        defaults.write_text(json.dumps(config))
        self.saved = (d.MEETS_DIR, d.DEFAULTS_PATH, d._lifter)
        d.MEETS_DIR, d.DEFAULTS_PATH = meets_dir, defaults
        # lifter() caches, and these cases are the only thing that ever repoints
        # DEFAULTS_PATH. Clearing it on the way in and restoring on the way out keeps
        # the fixture's config from leaking into the next case, in either direction.
        d._lifter = None
        return self

    def __exit__(self, *exc):
        d.MEETS_DIR, d.DEFAULTS_PATH, d._lifter = self.saved
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
# Two training days is below metrics.MONOTONY_MIN_TRAINING_DAYS, so this week gets no
# monotony at all - Foster's number is a statement about a distribution and two points
# are not one. It used to report 0.63 here, in the same column and on the same scale as
# a real week.
check("two training days is not a week to describe", w36["monotony"], None)
check("and with no monotony there is no strain either", w36["strain"], None)

# The elapsed-days clamp itself, on a week that does clear that floor: Mon/Tue/Wed
# trained, Thursday not yet happened.
elapsed = m.monotony([10000.0, 12000.0, 8000.0, 0.0])
padded = m.monotony([10000.0, 12000.0, 8000.0, 0.0, 0.0, 0.0, 0.0])
check("padding the unfinished week to seven is a different number", elapsed == padded, False)
check("and the padded one always reads calmer than the week really was",
      padded < elapsed, True)

# ...and the clamp reaches the rollup, not just the formula. A four-day corpus whose
# in-progress week has three training days in it.
FOUR_DAYS = [session("2026-08-31", "t1", 10000.0, lt70=20),
             session("2026-09-01", "t2", 12000.0, lt70=20),
             session("2026-09-02", "t3", 8000.0, lt70=20)]
with fake_meets([]):
    thursday = weekly_by_week(d.rollup_docs(FOUR_DAYS, today=date(2026, 9, 3)))
check("the in-progress week is measured over its elapsed days only",
      thursday["2026-W36"]["monotony"], elapsed)
check("strain follows the clamped monotony",
      thursday["2026-W36"]["strain"], m.strain(thursday["2026-W36"]["tonnage_lb"], elapsed))

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
#
# Both projection fields, because the now row is gated on the per-lift one. That gate
# is deliberately the more permissive of the two: a total needs an estimate for EVERY
# competition lift, the per-lift list needs one for any of them, so a lifter two lifts
# into a three-lift sport keeps a card instead of losing it. And in a sport scored on
# points there is no total to gate on at all.
PROJ_WEEKS = [("workout-weekly", week, {
    "iso_week": week, "week_end": end, "projected_total_lb": projected,
    "projected_by_lift": [{"lift_family": "bench", "value": round(projected * 0.25, 1)},
                          {"lift_family": "deadlift", "value": round(projected * 0.4, 1)},
                          {"lift_family": "squat", "value": round(projected * 0.35, 1)}]})
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


# ------------------------------------------------- a sport that is not powerlifting
#
# Ironstack was three barbell lifts because a tuple in this file said so. The lifts a
# person competes in now come off their own taxonomy, and what their competition does
# with those lifts comes off the meet record. The two questions the card can ask are
# "what will you total" and "are you ready on each event", and the second one is the
# only one a strongman show has an answer to.

print("\nA discipline scored on points gets readiness, not a total")

check("the competition families come off the taxonomy, not a constant",
      d.comp_families(), ("bench", "deadlift", "squat"))


def show(day, scoring="points"):
    """A meet in the events shape: a kg press, a timed yoke, a rep sandbag."""
    return {"meet_id": day, "date": day, "discipline": "strongman", "scoring": scoring,
            "events": [
                {"name": "Log Press", "unit": "kg", "lift_name": "Comp Bench",
                 "attempts": [{"attempt_no": 1, "value": 100.0, "made": True}]},
                {"name": "Yoke Carry", "unit": "seconds",
                 "attempts": [{"attempt_no": 1, "value": 12.9, "made": True}]},
                {"name": "Sandbag over Bar", "unit": "reps",
                 "attempts": [{"attempt_no": 1, "value": 5, "made": True}]}]}


with fake_meets([show("2026-06-13")]):
    now = strip_nones([doc for _i, sid, doc in
                       d._projection_rows(PROJ_WEEKS, TODAY, TODAY.isoformat())
                       if sid == "projection:now"][0])
check("the row knows how the sport is scored", now["scoring"], "points")
check("and what the sport is", now["discipline"], "strongman")
check("no projected total, because there is no total to project",
      "projected_total_lb" in now, False)
check("nor an expectation built on one", "expected_lb" in now, False)
check("but readiness per lift still ships", len(now["projected_by_lift"]), 3)
check("a points meet is not a peer for a total", now["peers"], 0)

# The same weeks, the same lifter, a meet scored on a total: the card comes back.
with fake_meets([show("2026-06-13", scoring="total")]):
    now = strip_nones([doc for _i, sid, doc in
                       d._projection_rows(PROJ_WEEKS, TODAY, TODAY.isoformat())
                       if sid == "projection:now"][0])
check("a total discipline still projects a total", now["projected_total_lb"], 900.0)
check("and says so", now["scoring"], "total")

# The reference maxes: a weight event sets a meet max, a timed one cannot.
with fake_meets([show("2026-06-13")]):
    maxes = dict(d._meet_maxes())
check("an events meet still yields meet maxes", sorted(maxes["2026-06-13"]), ["bench"])
check("and the max is the log press, converted",
      maxes["2026-06-13"]["bench"], round(100.0 * d.metrics.LB_PER_KG, 1))

# A meet cycle reads the events shape for its attempt counts, which used to be None on
# anything that was not three named lifts.
with fake_meets([show("2026-06-13")]):
    cycle = [c for c in d._meet_cycles(TODAY) if c["cycle"] == "2026-06-13"][0]
check("three events, three attempts", cycle["attempts_total"], 3)
check("all three completed", cycle["attempts_made"], 3)
check("and the events are counted too", cycle["events_total"], 3)
check("a points meet contributes no platform total", cycle["meet_total_lb"], None)

# A malformed meet is named, not traced.
with fake_meets([{"meet_id": "2026-01-01", "date": "2026-01-01",
                  "attempts": [{"lift": "squat", "weight_kg": 100.0, "made": True}]}]):
    try:
        d._meet_maxes()
        check("a malformed meet names its file", "no exit", "SystemExit")
    except SystemExit as exc:
        check("a malformed meet names its file", "2026-01-01.json" in str(exc), True)


# ------------------------------------------------- no lookahead in the reference
#
# The invariant this whole module exists for, and until now the only one with no test.
# build_reference() snapshots the running best STRICTLY BEFORE each session. Fold the
# session in first instead - one line moved - and every set is measured against a max
# that includes its own session, and hoisting the snapshot out of the loop measures
# every set against a PR set months in the FUTURE. Either mutation changes 1,055 of the
# corpus's 12,949 sets and inverts a headline verdict, and all five test files passed.
#
# set_fields() reaches index_workouts.slugify through derive.lift_slug, so this section
# (unlike the rest of the file) needs the indexer importable. It reads config/exercises.json
# for the two real lift names below; nothing else here touches the repo.

print("\nNo lookahead: a later PR cannot reach back into an earlier session")


def lift_log(day, sid, name, sets):
    return (day, sid, {"session": {"date": day, "session_id": sid},
                       "exercises": [{"name": name, "category": "main",
                                      "sets": [{"set_number": n, "reps": r,
                                                "weight_lb": w, "rpe": rpe,
                                                "set_type": "working"}
                                               for n, (w, r, rpe) in enumerate(sets, 1)]}]})


LIFT = "Comp Squat"
SLUG = "comp-squat"
# Two sessions. The second is a PR by any measure: more weight, fewer reps, higher RPE.
# The first has two sets of its own, so a reference that folded the session into itself
# would be caught here too and not only by the later one.
EARLY = lift_log("2026-01-05", "early", LIFT, [(300.0, 5, 7.0), (315.0, 5, 8.0)])
LATE = lift_log("2026-01-12", "late", LIFT, [(405.0, 3, 9.0)])

alone = d.build_reference([EARLY])
both = d.build_reference([EARLY, LATE])

check("with no history, the early session has no reference at all",
      alone.best_before("early", SLUG), None)
check("...and adding a later PR does not give it one",
      both.best_before("early", SLUG), None)
check("the later session is measured against the earlier one's best",
      both.best_before("late", SLUG),
      (m.e1rm(315.0, 5, 8.0)["value"], "recent"))
check("not against its own, which is higher",
      both.best_before("late", SLUG)[0] < m.e1rm(405.0, 3, 9.0)["value"], True)


def early_fields(reference):
    exercise = EARLY[2]["exercises"][0]
    return [d.set_fields(exercise, s, "early", reference) for s in exercise["sets"]]


before, after = early_fields(alone), early_fields(both)
check("the early session's intensity_pct is unchanged by the later PR",
      [f.get("intensity_pct") for f in after], [f.get("intensity_pct") for f in before])
check("and so is its intensity_ref",
      [f.get("intensity_ref") for f in after], [f.get("intensity_ref") for f in before])
# Said absolutely, not only relatively: "self" is what "there was nothing before this"
# looks like on the row, and it is the value both mutations replace.
check("both early sets are measured against themselves",
      [f["intensity_ref"] for f in after], ["self", "self"])
check("the first early set is measured against its own estimate, not the session's best",
      after[0]["intensity_pct"],
      m.relative_intensity(300.0, m.e1rm(300.0, 5, 7.0)["value"]))
# The test is not vacuous: the later session IS measured, and against the earlier best.
late_exercise = LATE[2]["exercises"][0]
late_fields = d.set_fields(late_exercise, late_exercise["sets"][0], "late", both)
check("the later session does get a reference, and it is the earlier session's",
      (late_fields["intensity_ref"], late_fields["intensity_pct"]),
      ("recent", m.relative_intensity(405.0, m.e1rm(315.0, 5, 8.0)["value"])))


# ------------------------------------------- intensity needs something to measure

print("\nAn intensity with no RPE and no reference is not an intensity")

# The set is the FIRST of its lift in the corpus, so build_reference has nothing to
# measure it against, and it carries no RPE, so e1rm() falls back to Epley. Measuring
# such a set against its own Epley estimate is weight * 100 / (weight * (1 + reps/30)),
# in which the weight cancels: what comes out is a function of the rep count alone.
check("that arithmetic really is independent of the load",
      m.relative_intensity(225.0, m.e1rm(225.0, 5, None)["value"])
      == m.relative_intensity(315.0, m.e1rm(315.0, 5, None)["value"]), True)
check("and a warm-up triple scored the same as a top single",
      m.relative_intensity(135.0, m.e1rm(135.0, 3, None)["value"])
      == m.relative_intensity(315.0, m.e1rm(315.0, 3, None)["value"]), True)
check("which put both of them in Prilepin's 90+ zone",
      m.prilepin_zone(m.relative_intensity(315.0, m.e1rm(315.0, 3, None)["value"])), "90+")

NORPE = lift_log("2026-01-05", "norpe", LIFT,
                 [(225.0, 5, None), (315.0, 5, None), (315.0, 3, None)])
norpe_ref = d.build_reference([NORPE])
norpe_ex = NORPE[2]["exercises"][0]
norpe_fields = [d.set_fields(norpe_ex, s, "norpe", norpe_ref) for s in norpe_ex["sets"]]

check("the estimate itself still ships - Epley is rough, but it estimates something",
      [f.get("e1rm_method") for f in norpe_fields], ["epley"] * 3)
check("with a value that does depend on the weight",
      len({f["est_e1rm"] for f in norpe_fields}), 3)
check("no intensity_pct", [f.get("intensity_pct") for f in norpe_fields], [None] * 3)
check("no intensity_ref", [f.get("intensity_ref") for f in norpe_fields], [None] * 3)
check("no prilepin_zone", [f.get("prilepin_zone") for f in norpe_fields], [None] * 3)
check("no inol", [f.get("inol") for f in norpe_fields], [None] * 3)

# Both halves of the condition matter, so both are pinned. An RPE with no reference is
# still measured against itself - that is what the RPE said about the set - and a
# reference with no RPE is still measured, against the reference.
WITH_RPE = lift_log("2026-01-05", "rpe", LIFT, [(315.0, 3, 9.0)])
rpe_ex = WITH_RPE[2]["exercises"][0]
rpe_fields = d.set_fields(rpe_ex, rpe_ex["sets"][0], "rpe", d.build_reference([WITH_RPE]))
check("an RPE with no reference is still measured against itself",
      rpe_fields["intensity_ref"], "self")
# Self-referenced with an RPE, the percentage IS the RPE table's percentage for that
# rep count - which is a statement about the set, unlike the reps-only constant.
check("and the percentage is the one the RPE table gives", rpe_fields["intensity_pct"],
      m.pct_from_rpe(3, 9.0))
check("with the zone that follows from it", rpe_fields["prilepin_zone"], "80-89")

PRIOR = lift_log("2026-01-05", "prior", LIFT, [(405.0, 3, 9.0)])
NO_RPE_LATER = lift_log("2026-01-12", "later", LIFT, [(315.0, 5, None)])
later_ref = d.build_reference([PRIOR, NO_RPE_LATER])
later_ex = NO_RPE_LATER[2]["exercises"][0]
later_fields = d.set_fields(later_ex, later_ex["sets"][0], "later", later_ref)
check("a reference with no RPE is still measured, against the reference",
      later_fields["intensity_ref"], "recent")
check("and the number is the real one",
      later_fields["intensity_pct"],
      m.relative_intensity(315.0, m.e1rm(405.0, 3, 9.0)["value"]))
check("which is nothing like the rep-count constant it used to be",
      later_fields["intensity_pct"] == 85.7, False)

# The rows built from those sets carry the absence through rather than inventing a zone.
norpe_sets = [("workout-sets", f"norpe:{i}", {
    "date": "2026-01-05", "session_id": "norpe", "set_type": "working",
    "rep_unit": "reps", "reps": 5, "muscles_primary": [],
    "exercise": {"name": LIFT, "category": "main"}, **f})
    for i, f in enumerate(norpe_fields)]
zoned = d.session_fields([doc for _i, _id, doc in norpe_sets],
                         {"date": "2026-01-05"}, {"tonnage_lb": 1000.0}, None)
check("a session of them counts no Prilepin reps at all",
      set(zoned["prilepin_reps"].values()), {0})
check("and has no INOL total", zoned["inol_total"], None)


# --------------------------------------------- the layoff threshold, as a number

print("\nlayoff_min_training_days: half the lifter's own cadence")

check("half a four-a-week cadence is the 8 the old constant hardcoded",
      d.layoff_min_training_days([16] * 5), 8)
# The whole point of deriving it. A twice-a-week lifter has at most 8 training days in
# any 28-day window, so a constant 8 flagged every window they will ever log and the
# Load card's comeback branch was permanently taken.
check("a twice-a-week lifter gets 4, not 8", d.layoff_min_training_days([8] * 5), 4)
check("so their ordinary weeks are not comebacks", 8 < d.layoff_min_training_days([8] * 5), False)

# Median, not mean. One unusually dense window in a sparse history drags a mean up and
# starts flagging ordinary weeks; the median is what survives it, which is the point,
# because the windows being detected are exactly the outliers.
check("one huge window does not move the median",
      d.layoff_min_training_days([4, 4, 4, 4, 40]), 2)
check("...and the mean would have said 6",
      int(sum([4, 4, 4, 4, 40]) / 5 * d.LAYOFF_FRACTION + 0.5), 6)

# Half of an odd median is a .5, and round() is banker's rounding: 13 -> 6.5 -> 6 but
# 15 -> 7.5 -> 8, so the threshold moved in different directions for two neighbouring
# cadences depending only on which side of the float landed even.
check("a median of 13 gives 7, not 6", d.layoff_min_training_days([13]), 7)
check("a median of 15 gives 8", d.layoff_min_training_days([15]), 8)
check("and the two round the same way", d.layoff_min_training_days([13]) * 15,
      d.layoff_min_training_days([15]) * 13 + 1)

# The floor guards an UNKNOWN cadence.
check("no history at all falls back to the floor",
      d.layoff_min_training_days([]), d.LAYOFF_FLOOR)
check("and the floor is 2, so a single week back after a layoff can still fire",
      d.LAYOFF_FLOOR, 2)
check("a thin but real cadence gets the floor rather than 0 or 1",
      d.layoff_min_training_days([1, 1, 1]), 2)
# A measured zero is a measurement, and it was the one answer this could not hear.
# Read as "no data" it fell through to the floor, which every one of that lifter's
# windows is below, so every week was flagged and the card read "Coming back." forever.
check("a measured median of zero is not the absence of data",
      d.layoff_min_training_days([0, 0, 0, 0, 0]), 0)
check("so no window of that history is ever below it",
      0 < d.layoff_min_training_days([0, 0, 0, 0, 0]), False)
check("while an empty list still is an absence",
      d.layoff_min_training_days([]) == d.layoff_min_training_days([0, 0, 0]), False)
check("config can still override the whole derivation", d.CHRONIC_DAYS, 28)

print("\nThe 28-day window is 28 days, inclusive of its own end")
END = date(2026, 3, 2)
check("the end day itself counts", d._training_days_in_window({END}, END), 1)
check("27 days back is inside the window",
      d._training_days_in_window({END - timedelta(days=27)}, END), 1)
check("28 days back is outside it",
      d._training_days_in_window({END - timedelta(days=28)}, END), 0)
check("and so is tomorrow",
      d._training_days_in_window({END + timedelta(days=1)}, END), 0)
check("the whole window, counted",
      d._training_days_in_window({END - timedelta(days=n) for n in range(40)}, END), 28)


# --------------------------------------- one definition of a training day

print("\nA bodyweight-only session is a training day, not a rest day")

# Mon/Wed/Fri for nine weeks, with every Wednesday a bodyweight-only session: a real
# session, zero tonnage. It used to be a training day by `training_days` and a rest day
# by chronic_days_trained and by monotony's minimum-days guard, on the same document.
BW_MONDAY = date(2026, 7, 6)
BODYWEIGHT = []
for w in range(9):
    for off, tonnage in ((0, 10000.0), (2, 0.0), (4, 8000.0)):
        day = (BW_MONDAY + timedelta(days=7 * w + off)).isoformat()
        BODYWEIGHT.append(session(day, f"bw{w}-{off}", tonnage, lt70=10))
BW_TODAY = date(2026, 9, 6)
with fake_meets([]):
    bw_weekly = weekly_by_week(d.rollup_docs(BODYWEIGHT, today=BW_TODAY))
last_bw = bw_weekly["2026-W36"]
check("three sessions a week", last_bw["training_days"], 3)
check("the 28-day window counts twelve of them, not eight",
      last_bw["chronic_days_trained"], 12)
check("which is training_days x 4, the same definition on both fields",
      last_bw["chronic_days_trained"], last_bw["training_days"] * 4)
check("the bodyweight day is still honestly a zero in the LOAD series",
      last_bw["tonnage_lb"], 18000.0)
check("and the week has enough training days to describe a distribution",
      last_bw["monotony"] is not None, True)
check("which it did not when the zero-tonnage day was read as rest",
      m.monotony([10000.0, 0.0, 0.0, 0.0, 8000.0, 0.0, 0.0]), None)


# ------------------------------------------ the load window is the week's window

print("\nload_7d is the week's seven days, not seven days back from its last session")

# W35 trained Mon/Wed/Fri, W36 trained Monday only. Anchored on the last training day,
# W36's acute window is Aug 25 - Aug 31, which is mostly W35: it reported 27,000 lb of
# "7-day load" on a row whose own tonnage is 7,000, under an ISO-week label.
ANCHORED = [session("2026-08-24", "n1", 10000.0, lt70=10),
            session("2026-08-26", "n2", 10000.0, lt70=10),
            session("2026-08-28", "n3", 10000.0, lt70=10),
            session("2026-08-31", "n4", 7000.0, lt70=10)]
SUNDAY = date(2026, 9, 6)
with fake_meets([]):
    anchored = weekly_by_week(d.rollup_docs(ANCHORED, today=SUNDAY))
w36 = anchored["2026-W36"]
check("the window ends on the week's Sunday", w36["load_window_end"], "2026-09-06")
check("week_end is still the last day TRAINED, which is a different question",
      w36["week_end"], "2026-08-31")
check("load_7d is the week's own load", w36["load_7d"], 7000.0)
check("which is what the row says it moved", w36["load_7d"], w36["tonnage_lb"])
check("and not the previous week's, reached back into",
      w36["load_7d"] == 27000.0, False)
check("the closed week behind it is measured over its own seven days",
      anchored["2026-W35"]["load_7d"], 30000.0)
check("consecutive weeks' windows abut rather than overlap",
      (date.fromisoformat(w36["load_window_end"])
       - date.fromisoformat(anchored["2026-W35"]["load_window_end"])).days, 7)
# The week in progress has not reached its Sunday, and a window running into the future
# would be seven days of which three have not happened.
with fake_meets([]):
    midweek = weekly_by_week(d.rollup_docs(ANCHORED, today=date(2026, 9, 2)))
check("a week in progress is anchored on today instead",
      midweek["2026-W36"]["load_window_end"], "2026-09-02")
check("and never past it",
      midweek["2026-W36"]["load_window_end"] <= "2026-09-02", True)


# ------------------------------------- the threshold cannot see the future

print("\nThe layoff threshold is the history behind each week, not the whole corpus")

# Twelve sparse weeks (two sessions a week) followed by twelve dense ones (six). The
# whole-corpus median sits between the two cadences, so a single threshold computed
# once judges the sparse half against training the lifter had not done yet - and lets
# a 2024 week's flag change in 2026 because of a 2026 training block.
SPARSE_MONDAY = date(2026, 1, 5)
LOOKAHEAD = []
for w in range(24):
    offsets = (0, 3) if w < 12 else (0, 1, 2, 3, 4, 5)
    for off in offsets:
        day = (SPARSE_MONDAY + timedelta(days=7 * w + off)).isoformat()
        LOOKAHEAD.append(session(day, f"la{w}-{off}", 10000.0, lt70=10))

LOOK_TODAY = SPARSE_MONDAY + timedelta(days=7 * 24 - 1)
EARLY_WEEK = "2026-W11"          # inside the sparse half, past the 28-day warm-up
truncated = [s for s in LOOKAHEAD if s[2]["date"] <= "2026-03-15"]
with fake_meets([]):
    full = weekly_by_week(d.rollup_docs(LOOKAHEAD, today=LOOK_TODAY))
    part = weekly_by_week(d.rollup_docs(truncated, today=date(2026, 3, 15)))
check("an early week's threshold is on the row at all",
      full[EARLY_WEEK]["layoff_min_training_days"] is not None, True)
check("and it is the same whether or not the later weeks exist",
      full[EARLY_WEEK]["layoff_min_training_days"],
      part[EARLY_WEEK]["layoff_min_training_days"])
check("...which is not vacuous: the later weeks do move the threshold",
      full[EARLY_WEEK]["layoff_min_training_days"]
      == full["2026-W24"]["layoff_min_training_days"], False)
check("the sparse half is judged against the sparse cadence",
      full[EARLY_WEEK]["layoff_min_training_days"], 4)
check("and the dense half against the dense one",
      full["2026-W24"]["layoff_min_training_days"], 8)
check("the flag on an early week is not moved by later training",
      full[EARLY_WEEK]["acwr_off_layoff"], part[EARLY_WEEK]["acwr_off_layoff"])
check("every judged week carries the number it was judged against",
      all(w.get("layoff_min_training_days") is not None
          for w in full.values() if w["acwr"] is not None), True)
check("and weeks with no 28-day base carry neither",
      full["2026-W02"].get("layoff_min_training_days"), None)


print("\nThe layoff flag is strictly below the threshold, not at it")

# The threshold is pinned by config so the boundary case can be constructed at all.
# Three sessions a week gives a 28-day window of 12; four gives 16.
BOUNDARY = []
for w in range(10):
    for off in (0, 2, 4):
        BOUNDARY.append(session((date(2026, 1, 5) + timedelta(days=7 * w + off)).isoformat(),
                                f"b{w}-{off}", 10000.0, lt70=10))
with fake_meets([], lifter={"layoff_min_training_days": 12}):
    at = weekly_by_week(d.rollup_docs(BOUNDARY, today=date(2026, 3, 15)))
with fake_meets([], lifter={"layoff_min_training_days": 13}):
    below = weekly_by_week(d.rollup_docs(BOUNDARY, today=date(2026, 3, 15)))
LAST = "2026-W10"
check("the window carries exactly twelve training days",
      at[LAST]["chronic_days_trained"], 12)
check("at the threshold is not below it", at[LAST]["acwr_off_layoff"], False)
check("and the row says what it was judged against",
      at[LAST]["layoff_min_training_days"], 12)
check("one under the threshold is", below[LAST]["acwr_off_layoff"], True)


# --------------------------------------------------- heavy means 80% and above

print("\nHeavy is the 80-89 zone as well as 90+")

MAIN_ONLY = {"prilepin_reps": {"lt70": 100, "z70_79": 50, "z80_89": 10, "z90plus": 3},
             "totals": {"tonnage_lb": 10000.0}}
check("_heavy_reps counts both heavy zones", d._heavy_reps([MAIN_ONLY]), 13)
check("not the top zone alone", d._heavy_reps([MAIN_ONLY]) == 3, False)
check("_run_stats agrees, over the same slice",
      d._run_stats([MAIN_ONLY])["heavy_per_session"], 13.0)
check("and its share is over all main-lift reps", d._run_stats([MAIN_ONLY])["share_pct"], 8.0)

# ...and the two rows a card reads it off.
HEAVY_CORPUS = [session(day, f"h-{day}", 10000.0, block="strength", z80_89=10)
                for day in span("2026-05-04", 5)]
HEAVY_TODAY = date(2026, 5, 10)
with fake_meets([]):
    heavy_rows = signals_by_id(HEAVY_CORPUS,
                               d.rollup_docs(HEAVY_CORPUS, today=HEAVY_TODAY), HEAVY_TODAY)
check("the block row's heavy count is 80-89 work", heavy_rows["block:0"]["heavy"], 50)
check("and its rate", heavy_rows["block:0"]["heavy_per_session"], 10.0)
check("the intensity row's too", heavy_rows["intensity:2026-W19"]["heavy"], 50)
check("a week of nothing but 80-89 work is not a week with no heavy work",
      heavy_rows["intensity:2026-W19"]["heavy"] == 0, False)


print("\nPrilepin's zones are main-lift work only")
ZONED_SETS = [
    {"set_type": "working", "rep_unit": "reps", "reps": 3, "prilepin_zone": "90+",
     "exercise": {"name": "Comp Squat", "category": "main"}},
    {"set_type": "working", "rep_unit": "reps", "reps": 20, "prilepin_zone": "90+",
     "exercise": {"name": "Cable Curl", "category": "accessory"}},
    {"set_type": "working", "rep_unit": "seconds", "reps": 60, "prilepin_zone": "90+",
     "exercise": {"name": "Plank", "category": "main"}},
]
zoned = d.session_fields(ZONED_SETS, {"date": "2026-01-05"}, {"tonnage_lb": 1000.0}, None)
# An accessory is measured against its own reference, so a lateral raise at 100% of its
# own best would swamp the zone counts a squat's top single belongs in.
check("the accessory's 20 reps do not join the squat's 3",
      zoned["prilepin_reps"]["z90plus"], 3)
check("nor does a seconds-based hold", sum(zoned["prilepin_reps"].values()), 3)


print("\nISO weeks use the ISO year, not the calendar year")
# The two disagree for up to three days either side of New Year, and a row keyed
# "2027-W53" sorts after every real 2027 week and merges with nothing.
check("New Year's Day 2027 is the last ISO week of 2026",
      d._iso_week(date(2027, 1, 1)), "2026-W53")
check("and December 29 2025 is the first of 2026",
      d._iso_week(date(2025, 12, 29)), "2026-W01")
check("January 1 2026 is in that same week", d._iso_week(date(2026, 1, 1)), "2026-W01")
check("so the two dates land on one row",
      d._iso_week(date(2025, 12, 29)) == d._iso_week(date(2026, 1, 1)), True)


print("\nA block stops being current when it stops being trained")
RECENT_BLOCK = [session(day, f"cur-{day}", 10000.0, block="strength", z80_89=10)
                for day in span("2026-05-04", 5)]
with fake_meets([]):
    fresh = signals_by_id(RECENT_BLOCK,
                          d.rollup_docs(RECENT_BLOCK, today=date(2026, 5, 10)),
                          date(2026, 5, 10))
    stale = signals_by_id(RECENT_BLOCK,
                          d.rollup_docs(RECENT_BLOCK, today=date(2026, 9, 1)),
                          date(2026, 9, 1))
check("the window is 28 days", d.BLOCK_CURRENT_DAYS, 28)
check("a block trained this week is the block you are in",
      fresh["block:0"]["block_role"], "current")
check("one abandoned in the spring is not",
      stale["block:0"]["block_role"], "past")
check("even though it is still ordinal 0", stale["block:0"]["ordinal"], 0)
with fake_meets([]):
    edge = signals_by_id(RECENT_BLOCK,
                         d.rollup_docs(RECENT_BLOCK, today=date(2026, 5, 8) + timedelta(days=28)),
                         date(2026, 5, 8) + timedelta(days=28))
check("28 days after the last session is still current",
      edge["block:0"]["block_role"], "current")


print("\nWeekly DOTS uses the configured sex, and never a default")
DOTS_CORPUS = []
for i, day in enumerate(span("2026-05-04", 5)):
    DOTS_CORPUS.append(session(day, f"dt{i}", 10000.0, lt70=10, bodyweight=200.0))
    for slug, value in (("comp-squat", 500.0), ("comp-bench", 300.0),
                        ("comp-deadlift", 600.0)):
        DOTS_CORPUS.append(e1rm_set(day, f"dt{i}", slug, value))
DOTS_TODAY = date(2026, 5, 10)


def weekly_dots(sex):
    with fake_meets([], lifter=({"sex": sex} if sex else {})):
        return weekly_by_week(d.rollup_docs(DOTS_CORPUS, today=DOTS_TODAY))["2026-W19"]


male, female, unset = weekly_dots("male"), weekly_dots("female"), weekly_dots(None)
check("the projection is the three competition lifts",
      male["projected_total_lb"], 1400.0)
check("a male lifter gets the male score", male["dots"],
      m.dots(m.lb_to_kg(200.0), m.lb_to_kg(1400.0), "male"))
check("a female lifter gets the female one", female["dots"],
      m.dots(m.lb_to_kg(200.0), m.lb_to_kg(1400.0), "female"))
# The two coefficient sets are 20-30% apart, which is the size of the error a hardcoded
# "male" put on a female adopter's Meets card with nothing on the page to say so.
check("and they are not the same number", male["dots"] == female["dots"], False)
check("no sex configured means no score at all, not a male one",
      unset.get("dots"), None)
check("...while the projection it would have scored is still there",
      unset["projected_total_lb"], 1400.0)


print("\nA date-keyed rollup sits on the day it is about, in the lifter's own zone")
NZ = "Pacific/Auckland"
check("local noon, not UTC noon", d.rollup_timestamp(date(2026, 9, 4), NZ),
      "2026-09-04T12:00:00+12:00")
check("no zone configured falls back to the old UTC noon",
      d.rollup_timestamp(date(2026, 9, 4), None), "2026-09-04T12:00:00Z")
check("and so does an unreadable one, rather than raising a second time",
      d.rollup_timestamp(date(2026, 9, 4), "Mars/Olympus_Mons"),
      "2026-09-04T12:00:00Z")
# The failure, stated as what a reader at UTC+12 sees.
_utc_noon = datetime.fromisoformat("2026-09-04T12:00:00+00:00")
_local = datetime.fromisoformat(d.rollup_timestamp(date(2026, 9, 4), NZ))
check("UTC noon lands on the NEXT local day there",
      _utc_noon.astimezone(ZoneInfo(NZ)).date().isoformat(), "2026-09-05")
check("local noon lands on the day the row is about",
      _local.astimezone(ZoneInfo(NZ)).date().isoformat(), "2026-09-04")
check("and stays a day's width from either midnight, so no DST shift crosses it",
      _local.astimezone(ZoneInfo(NZ)).hour, 12)
with fake_meets([], timezone=NZ):
    stamped = d.rollup_docs(THREE_WEEKS, today=WEDNESDAY)
check("the daily rows are stamped with it",
      [doc["@timestamp"] for index, _id, doc in stamped
       if index == "workout-daily" and _id == "2026-08-17"],
      ["2026-08-17T12:00:00+12:00"])
check("and the weekly rows too",
      [doc["@timestamp"] for index, _id, doc in stamped
       if index == "workout-weekly" and _id == "2026-W34"],
      ["2026-08-21T12:00:00+12:00"])


print("\nAn unknown exercise name is fatal, and says which log it is in")
try:
    d.classify("Comp Squatt")
    unknown = None
except d.UnknownExercise as exc:
    unknown = str(exc)
check("a misspelt lift raises rather than classifying to nothing",
      unknown is not None, True)
check("and the message suggests what it probably was",
      "Comp Squat" in (unknown or ""), True)
check("with the fix as well as the guess",
      "config/exercises.json" in (unknown or ""), True)
check("a real name still classifies", d.classify(LIFT)["canonical"], LIFT)

BAD_LOG = lift_log("2026-01-05", "bad-session", "Comp Squatt", [(300.0, 5, 8.0)])
try:
    d.build_reference([BAD_LOG])
    raised_in = None
except d.UnknownExercise as exc:
    raised_in = exc.session_id
check("build_reference names the session holding it", raised_in, "bad-session")


print("\nDrift: a muscle trained once has no cadence to report")
ONCE_TODAY = date(2026, 9, 5)
once = [session("2026-08-01", "o1", 10000.0, lt70=10),
        working_set("2026-08-01", "o1", 0, muscles=("calves",)),
        session("2026-08-15", "o2", 10000.0, lt70=10),
        working_set("2026-08-15", "o2", 1, muscles=("hamstrings",)),
        session("2026-08-29", "o3", 10000.0, lt70=10),
        working_set("2026-08-29", "o3", 2, muscles=("hamstrings",))]
with fake_meets([]):
    once_rows = signals_by_id(once, d.rollup_docs(once, today=ONCE_TODAY), ONCE_TODAY)
calves, hams = once_rows["drift:calves"], once_rows["drift:hamstrings"]
check("one session is one session", calves["sessions"], 1)
# span / 1 is how long ago that session was, wearing a cadence's units. The card had
# this guard; the row did not, which is the split this index exists to remove.
check("and gets no cadence_days", calves["cadence_days"], None)
check("the row says so in a field, so a card that forgot to check still declines",
      calves["rankable"], False)
check("the row still ships, with its date", calves["last_trained"], "2026-08-01")
check("two sessions is one observed gap, which is a cadence", hams["sessions"], 2)
check("and it is reported", hams["cadence_days"], 11.0)
check("and marked rankable", hams["rankable"], True)


print("\nThe taper cumulative never counts the week in progress")
TAPER_TODAY = date(2026, 9, 2)
taper_corpus = weekly_training("2026-08-03", 5, offsets=(0, 2, 4))
with fake_meets([], planned="2026-09-05"):
    rows = {sid: doc for _i, sid, doc in
            d.signal_docs(taper_corpus, d.rollup_docs(taper_corpus, today=TAPER_TODAY),
                          today=TAPER_TODAY)
            if doc["signal"] == "taper"}
open_row = rows["taper:2026-09-05:1"]
check("the meet week is the week in progress", open_row["week_state"], "in-progress")
check("it has four closed weeks behind it", open_row["cum_weeks"], 4)
check("and the cumulative is those four, at 30,000 lb each",
      open_row["cum_tonnage_lb"], 120000.0)
check("its own partial week is not in the total",
      open_row["cum_tonnage_lb"] == 120000.0 + open_row["tonnage_lb"], False)
# The row a week earlier: its own week is closed, so it counts three behind it and not
# itself either.
check("nor is any row's own week in its own cumulative",
      rows["taper:2026-09-05:2"]["cum_weeks"], 3)

# _preceding_cumulative refuses the week in progress on its own, tested directly.
# _taper_rows never asks it to: it skips any Monday later than today, so the eight
# weeks behind a row are all strictly before the in-progress week and the guard cannot
# fire from there - removing it moves not one row of the 643-log corpus. That makes it
# untestable through the rows, and it is not untestable through the function, which is
# where the promise in its docstring ("the week in progress never contributes") lives
# and where a future caller with a meet-week Monday in hand will land.
PARTIAL = {"2026-W36": {"tonnage_lb": 99999.0,
                        "prilepin_reps": {"z80_89": 5, "z90plus": 5}},
           "2026-W35": {"tonnage_lb": 30000.0,
                        "prilepin_reps": {"z80_89": 2, "z90plus": 1}}}
future_monday = d._preceding_cumulative(date(2026, 10, 5), PARTIAL, "2026-01-05",
                                        "2026-W36", date(2026, 9, 2))
check("a window spanning the week in progress does not count it",
      future_monday, (30000.0, 3, 3))
check("...and it is that week's numbers that are missing, not a rounding",
      future_monday[0] == 99999.0 + 30000.0, False)
# The same call with that week closed instead: it counts, so the guard is what excluded
# it rather than the window's edges.
closed = d._preceding_cumulative(date(2026, 10, 5), PARTIAL, "2026-01-05",
                                 "2026-W01", date(2026, 9, 2))
check("a CLOSED week in the same window does count",
      closed, (129999.0, 13, 4))


print("\nThe intensity reference window is 90 days")
check("the constant", d.REFERENCE_WINDOW_DAYS, 90)
STALE = lift_log("2025-01-05", "stale", LIFT, [(405.0, 3, 9.0)])
FRESH = lift_log("2025-12-05", "fresh", LIFT, [(315.0, 5, 8.0)])
NOW = lift_log("2026-01-05", "now", LIFT, [(225.0, 5, 8.0)])
stale_only = d.build_reference([STALE, NOW])
check("a best a year old is carried, and marked stale",
      stale_only.best_before("now", SLUG)[1], "all-time")
with_fresh = d.build_reference([STALE, FRESH, NOW])
check("a best inside the window is preferred, and marked recent",
      with_fresh.best_before("now", SLUG)[1], "recent")
check("and it is the recent one even though the old one is heavier",
      with_fresh.best_before("now", SLUG)[0], m.e1rm(315.0, 5, 8.0)["value"])
check("the old best really is the bigger number",
      m.e1rm(405.0, 3, 9.0)["value"] > m.e1rm(315.0, 5, 8.0)["value"], True)
# The boundary, in days rather than by eye.
EDGE = lift_log((date(2026, 1, 5) - timedelta(days=d.REFERENCE_WINDOW_DAYS)).isoformat(),
                "edge", LIFT, [(405.0, 3, 9.0)])
check("a best exactly REFERENCE_WINDOW_DAYS old is still recent",
      d.build_reference([EDGE, NOW]).best_before("now", SLUG)[1], "recent")
OVER = lift_log((date(2026, 1, 5) - timedelta(days=d.REFERENCE_WINDOW_DAYS + 1)).isoformat(),
                "over", LIFT, [(405.0, 3, 9.0)])
check("one day older is not",
      d.build_reference([OVER, NOW]).best_before("now", SLUG)[1], "all-time")


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
