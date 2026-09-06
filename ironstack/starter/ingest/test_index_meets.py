#!/usr/bin/env python3
"""Unit tests for ingest/index_meets.py. No Elasticsearch, no network.

    python ingest/test_index_meets.py

What this file is for is the legacy meet.

On 2026-09-06 a meet stopped being three named lifts and became a list of events with
units, so that a strongman show - a log press in kg, a yoke in seconds, a sandbag in
reps - could be recorded at all. Every meet file that already existed was written in
the old shape. The migration is only acceptable if those files index exactly the way
they did before: same document `_id`, same fields, same values. Anything else asks a
lifter to rewrite their own history to keep their dashboards.

So the first section here is a legacy file, asserted field by field, and the ids it
produces are written out in full. The rest is the new shape - and mostly the places
where the new shape must REFUSE to produce a number: a total across a log press and a
yoke run is not a total, and DOTS without a total is not a score.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index_meets as im

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


def by_id(docs):
    return {i: d for _index, i, d in docs}


# ------------------------------------------------------------------ legacy shape
#
# The file every existing user has. Three lifts, three attempts, kg, no `events` key
# and no `scoring` key anywhere in it.

LEGACY = {
    "meet_id": "2024-11-16",
    "date": "2024-11-16",
    "name": "Fall Open",
    "federation": "USAPL",
    "bodyweight_kg": 82.0,
    "dots": 266.7,
    "attempts": [
        {"lift": "squat", "attempt_no": 1, "weight_kg": 112.5, "made": True},
        {"lift": "squat", "attempt_no": 2, "weight_kg": 125.0, "made": True},
        {"lift": "squat", "attempt_no": 3, "weight_kg": 132.5, "made": False},
        {"lift": "bench", "attempt_no": 1, "weight_kg": 80.0, "made": True},
        {"lift": "bench", "attempt_no": 2, "weight_kg": 85.0, "made": False},
        {"lift": "bench", "attempt_no": 3, "weight_kg": 85.0, "made": True},
        {"lift": "deadlift", "attempt_no": 1, "weight_kg": 150.0, "made": True},
        {"lift": "deadlift", "attempt_no": 2, "weight_kg": 160.0, "made": True},
        {"lift": "deadlift", "attempt_no": 3, "weight_kg": 170.0, "made": False},
    ],
}

print("legacy meet: ids do not move")
legacy = im.explode(LEGACY)
check("nine attempts, nine documents", len(legacy), 9)
check("every id", [i for _x, i, _d in legacy], [
    "2024-11-16-squat-1", "2024-11-16-squat-2", "2024-11-16-squat-3",
    "2024-11-16-bench-1", "2024-11-16-bench-2", "2024-11-16-bench-3",
    "2024-11-16-deadlift-1", "2024-11-16-deadlift-2", "2024-11-16-deadlift-3"])
check("every document goes to workout-meets",
      sorted({ix for ix, _i, _d in legacy}), ["workout-meets"])

docs = by_id(legacy)
squat3 = docs["2024-11-16-squat-3"]
# The `lift` column is the id's middle segment and the value every existing saved
# query filters on. It stays the bare lift, not the log's name for it.
check("lift is still the bare lift", squat3["lift"], "squat")
check("weight_kg still carries the attempt", squat3["weight_kg"], 132.5)
check("weight_lb still derived", squat3["weight_lb"], im.lb(132.5))
check("a missed attempt is not best", squat3["best"], False)
check("the made 125 is best", docs["2024-11-16-squat-2"]["best"], True)
check("the made 85 is best even though 85 was also missed",
      docs["2024-11-16-bench-3"]["best"], True)
# Attempt 2 and attempt 3 are the same weight, one missed and one made. `best` is
# computed from the RESULT, not from the maximum attempted, so the missed one is not
# retroactively promoted by the made one having the same number on the bar.
check("the missed 85 is not best", docs["2024-11-16-bench-2"]["best"], False)
# And a MADE attempt that is not the best one. Without this line `best` could
# be `made` and nothing here would notice: every other not-best attempt in the
# fixture is also a missed one.
check("an opener that was made is not best", docs["2024-11-16-squat-1"]["best"], False)

# 125 + 85 + 160
check("total summed from the best made attempts", squat3["total_kg"], 370.0)
check("total in lb", squat3["total_lb"], im.lb(370.0))
check("dots survives a total meet", squat3["dots"], 266.7)
check("attempts made", squat3["attempts_made"], 6)
check("a legacy meet is powerlifting by default", squat3["discipline"], "powerlifting")
check("a legacy meet is scored on a total by default", squat3["scoring"], "total")
check("legacy events are kg", squat3["unit"], "kg")
# The competition announces the squat; the log calls it Comp Squat. Both are kept and
# they are not the same field.
check("event name is the platform's word", squat3["event_name"], "Squat")
check("exercise is the log's word", squat3["exercise"]["name"], "Comp Squat")
check("lift_slug reaches the training history", squat3["lift_slug"], "comp-squat")
check("running order: squat is first", squat3["event_no"], 1)
check("bench second", docs["2024-11-16-bench-1"]["event_no"], 2)
check("deadlift third", docs["2024-11-16-deadlift-1"]["event_no"], 3)

# lift_names still overrides, and still resolves through the taxonomy.
named = by_id(im.explode({**LEGACY, "lift_names": {"squat": "Competition Squat"}}))
check("lift_names still overrides",
      named["2024-11-16-squat-1"]["exercise"]["name"], "Comp Squat")

# An official total on the record wins over the computed one - a meet where an
# attempt was later overturned is the reason the field exists.
official = by_id(im.explode({**LEGACY, "total_kg": 999.0}))
check("an official total is not recomputed",
      official["2024-11-16-squat-1"]["total_kg"], 999.0)


# ------------------------------------------------------------------- events shape

STRONGMAN = {
    "meet_id": "2026-06-13-strongman",
    "date": "2026-06-13",
    "name": "Summer Strongman",
    "discipline": "strongman",
    "scoring": "points",
    "bodyweight_kg": 100.0,
    "dots": 300.0,
    "points": 41.5,
    "placing": 3,
    "events": [
        {"name": "Log Press", "unit": "kg", "lift_name": "Comp Bench",
         "points": 9.5, "placing": 4,
         "attempts": [{"attempt_no": 1, "value": 100.0, "made": True},
                      {"attempt_no": 2, "value": 110.0, "made": False}]},
        {"name": "Yoke Carry", "unit": "seconds", "placing": 1, "points": 12.0,
         "attempts": [{"attempt_no": 1, "value": 14.2, "made": True},
                      {"attempt_no": 2, "value": 11.8, "made": False},
                      {"attempt_no": 3, "value": 12.9, "made": True}]},
        {"name": "Sandbag over Bar", "unit": "reps",
         "attempts": [{"attempt_no": 1, "value": 5, "made": True}]},
    ],
}

print("\nevents: a competition that is not three barbell lifts")
show = im.explode(STRONGMAN)
check("six attempts across three events", len(show), 6)
check("ids are slugged event names", [i for _x, i, _d in show], [
    "2026-06-13-strongman-log-press-1", "2026-06-13-strongman-log-press-2",
    "2026-06-13-strongman-yoke-carry-1", "2026-06-13-strongman-yoke-carry-2",
    "2026-06-13-strongman-yoke-carry-3",
    "2026-06-13-strongman-sandbag-over-bar-1"])

s = by_id(show)
yoke = s["2026-06-13-strongman-yoke-carry-1"]
bag = s["2026-06-13-strongman-sandbag-over-bar-1"]
log = s["2026-06-13-strongman-log-press-1"]

# Faster is better, and only a completed run counts. 11.8 is the fastest number on the
# event and it was a failed run: the result is 12.9, the fastest one he finished.
check("seconds: lower is better", yoke["event_result"], 12.9)
check("the fastest FAILED run is not the result",
      s["2026-06-13-strongman-yoke-carry-2"]["best"], False)
check("the fastest finished run is best",
      s["2026-06-13-strongman-yoke-carry-3"]["best"], True)
# The same trap in the direction that runs backwards: 14.2 was completed and is
# still not the result, because 12.9 was completed and is faster.
check("a slower finished run is not best", yoke["best"], False)
check("reps: more is better", bag["event_result"], 5)
check("kg: more is better", log["event_result"], 100.0)

# The unit column is what keeps a 14.2-second yoke run out of a weight ranking.
check("a timed event carries no weight_kg", yoke["weight_kg"], None)
check("a timed event carries no weight_lb", yoke["weight_lb"], None)
check("a timed event still carries its value", yoke["value"], 14.2)
check("unit is on the document", yoke["unit"], "seconds")
# The events come out in the order the file lists them, which is the order the
# show ran. Nothing about them is alphabetical or weight-ranked.
check("the log press ran first", log["event_no"], 1)
check("the yoke second", yoke["event_no"], 2)
check("the sandbag third", bag["event_no"], 3)
check("a kg event still fills weight_kg", log["weight_kg"], 100.0)

# The refusals. This is the whole reason `scoring` exists.
check("points scoring invents no total", yoke["total_kg"], None)
# Not just uncomputed - refused. A points meet carrying a hand-added kilogram
# total would sort into a ranking of powerlifting totals as though it belonged.
stated_total = by_id(im.explode({**STRONGMAN, "total_kg": 500.0}))
check("points scoring drops a STATED total too",
      stated_total["2026-06-13-strongman-log-press-1"]["total_kg"], None)
check("points scoring invents no total in lb", yoke["total_lb"], None)
check("DOTS without a total is dropped even when the file carries one",
      yoke["dots"], None)
check("competition points are kept", yoke["points"], 41.5)
check("placing is kept", yoke["placing"], 3)
check("per-event points are kept", log["event_points"], 9.5)
check("per-event placing is kept", yoke["event_placing"], 1)
check("an event with no points says so", bag["event_points"], None)

# An event with a lift_name reaches its training history; one without is filed under
# its own name rather than given a fake analogue.
check("a claimed lift_name resolves through the taxonomy",
      log["exercise"]["name"], "Comp Bench")
check("an unclaimed event keeps its own name", yoke["exercise"]["name"], "Yoke Carry")
check("an unclaimed event still gets a slug", yoke["lift_slug"], "yoke-carry")


print("\nevents scored on a total")
WEIGHTLIFTING = {
    "meet_id": "2026-03-01-wl", "date": "2026-03-01", "discipline": "weightlifting",
    "scoring": "total", "bodyweight_kg": 90.0,
    "events": [
        {"name": "Snatch", "unit": "kg",
         "attempts": [{"attempt_no": 1, "value": 90.0, "made": True},
                      {"attempt_no": 2, "value": 95.0, "made": False}]},
        {"name": "Clean and Jerk", "unit": "kg",
         "attempts": [{"attempt_no": 1, "value": 115.0, "made": True}]},
    ],
}
wl = by_id(im.explode(WEIGHTLIFTING))["2026-03-01-wl-snatch-1"]
check("two kg events sum to a total", wl["total_kg"], 205.0)
check("and the total converts", wl["total_lb"], im.lb(205.0))

# A total meet with a non-kg event in it sums the kg ones and leaves the other alone,
# rather than adding seconds to kilograms or refusing the total outright.
MIXED = {**WEIGHTLIFTING, "meet_id": "2026-03-01-mixed",
         "events": WEIGHTLIFTING["events"] + [
             {"name": "Farmers Walk", "unit": "seconds",
              "attempts": [{"attempt_no": 1, "value": 20.0, "made": True}]}]}
mixed = by_id(im.explode(MIXED))
check("a total sums the kg events and only those",
      mixed["2026-03-01-mixed-snatch-1"]["total_kg"], 205.0)
check("the non-kg event is still indexed",
      mixed["2026-03-01-mixed-farmers-walk-1"]["value"], 20.0)

# Nothing made means no result, and no result means no total rather than a zero.
BOMBED = {"meet_id": "2026-05-01", "date": "2026-05-01",
          "events": [{"name": "Squat", "unit": "kg",
                      "attempts": [{"attempt_no": 1, "value": 200.0, "made": False}]}]}
bombed = by_id(im.explode(BOMBED))["2026-05-01-squat-1"]
check("a bombed event has no result", bombed["event_result"], None)
check("a bombed meet has no total, not a zero", bombed["total_kg"], None)
check("and nothing is marked best", bombed["best"], False)
check("attempts_made counts nothing", bombed["attempts_made"], 0)

# An explicit result on the record wins - a judged event where the recorded attempts
# do not tell the whole story.
STATED = {"meet_id": "2026-05-02", "date": "2026-05-02",
          "events": [{"name": "Medley", "unit": "seconds", "result": 61.0,
                      "attempts": [{"attempt_no": 1, "value": 65.0, "made": True}]}]}
stated = by_id(im.explode(STATED))["2026-05-02-medley-1"]
check("a stated result is not recomputed", stated["event_result"], 61.0)


print("\na claimed link that goes nowhere is a hard error")
BAD_LINK = {"meet_id": "2026-07-01", "date": "2026-07-01",
            "events": [{"name": "Log Press", "unit": "kg",
                        "lift_name": "Zercher Wheelbarrow Press",
                        "attempts": [{"attempt_no": 1, "value": 100.0, "made": True}]}]}
try:
    im.explode(BAD_LINK)
    check("unresolvable lift_name exits", "no exit", "SystemExit")
except SystemExit:
    check("unresolvable lift_name exits", "SystemExit", "SystemExit")


if failures:
    print(f"\n{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("\nall index_meets tests passed")
