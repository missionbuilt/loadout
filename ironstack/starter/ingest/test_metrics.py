#!/usr/bin/env python3
"""Unit tests for ingest/metrics.py. No Elasticsearch, no repo data.

    python ingest/test_metrics.py

The DOTS cases are golden tests against hand-checked values: if the
coefficients are ever mistyped, these fail loudly rather than quietly shifting
every score on the Meets dashboard.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import metrics as m

failures = []


def check(label, got, want):
    # There was a `tol` parameter here that no call site has ever passed, so every
    # comparison below was exact equality wearing a tolerance's clothes. The values
    # metrics.py returns are rounded at the source, so exact is the right test - the
    # parameter is gone rather than left to imply a looseness that was never applied.
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


print("DOTS — golden tests against the published coefficients")
check("100.0 kg bw, 500.0 kg total", m.dots(100.0, 500.0, "male"), 307.76)
check("75.0 kg bw, 400.0 kg total", m.dots(75.0, 400.0, "male"), 286.97)
check("female coefficients still produce a score", m.dots(60.0, 300.0, "female") > 0, True)
# The two sets are 20-40% apart, which is why `sex` has no default and an unset one
# yields no score at all. Guessing here was wrong by more than any lift ever moves.
check("and they are nowhere near the male ones",
      round((m.dots(60.0, 300.0, "female") - m.dots(60.0, 300.0, "male"))
            * 100 / m.dots(60.0, 300.0, "male")) >= 20, True)
# Deliberately round numbers, not one of the meets above: sync-manifest.json redacts
# the two lines carrying real meet totals on the way to the public template, and a
# third one would be a third rule to keep in step.
check("no sex -> no score, rather than a male one", m.dots(100.0, 500.0, None), None)
check("an unrecognised sex -> no score either", m.dots(100.0, 500.0, "Male"), None)
check("no bodyweight -> no score", m.dots(0, 500.0, "male"), None)

print("\nRPE table — anchors from the published RTS chart")
check("1 rep @ RPE 10", m.pct_from_rpe(1, 10), 100.0)
check("1 rep @ RPE 9", m.pct_from_rpe(1, 9), 95.5)
check("3 reps @ RPE 8", m.pct_from_rpe(3, 8), 86.3)
check("5 reps @ RPE 8", m.pct_from_rpe(5, 8), 81.1)
check("8 reps @ RPE 8", m.pct_from_rpe(8, 8), 73.9)
check("10 reps @ RPE 8", m.pct_from_rpe(10, 8), 68.0)
check("12 reps @ RPE 6 (table floor)", m.pct_from_rpe(12, 6), 57.2)
check("half-point RPE lands on a row", m.pct_from_rpe(5, 7.5), 79.9)
check("equivalence: 5 @ 8 == 6 @ 9", m.pct_from_rpe(5, 8), m.pct_from_rpe(6, 9))
check("past the table it extrapolates", m.pct_from_rpe(12, 4), 51.6)
check("far past the table it declines to guess", m.pct_from_rpe(12, 1), None)

print("\ne1RM — model, value and confidence")
top = m.e1rm(275, 5, 8)
check("275x5 @8 uses the RPE model", top["method"], "rpe")
check("275x5 @8 value", top["value"], 339.1)
check("275x5 @8 is high confidence", top["confidence"], m.CONF_HIGH)
check("7 reps is medium confidence", m.e1rm(225, 7, 8)["confidence"], m.CONF_MEDIUM)
check("10 reps is low confidence", m.e1rm(80, 10, 6)["confidence"], m.CONF_LOW)
check("13 reps gets no estimate at all", m.e1rm(80, 13, 6), None)
# The cap is `reps > REPS_MAX`, and the case that pins the comparison is REPS_MAX
# itself. "13 gets nothing" is equally true of `>=`, so on its own it left the
# boundary free to move a rep inward and silently drop every 12-rep set's estimate -
# and with it the e1RM that a 12-rep back-off set contributes to the daily best.
check("exactly REPS_MAX still gets one", m.e1rm(80, m.REPS_MAX, 6) is not None, True)
check("one rep past REPS_MAX does not", m.e1rm(80, m.REPS_MAX + 1, 6), None)
check("no RPE falls back to Epley", m.e1rm(225, 5, None)["method"], "epley")
check("no RPE is never high confidence", m.e1rm(225, 5, None)["confidence"], m.CONF_MEDIUM)
check("bodyweight set (no load) gets nothing", m.e1rm(0, 10, 7), None)

print("\ne1RM — how the new model differs from the old est_e1rm()")
# The old index_workouts.est_e1rm was Epley with reps-in-reserve folded into the
# rep count. At low reps the two agree closely; at high reps Epley's linear curve
# reads *lower* than the RTS table, and neither deserves much trust — which is
# what e1rm_confidence exists to say.
old = lambda w, r, rpe: w * (1 + (r + (10 - rpe)) / 30.0)
check("5 reps: old and new within 1 lb", abs(m.e1rm(275, 5, 8)["value"] - old(275, 5, 8)) < 1.0, True)
check("10 reps: they diverge by more than 8%",
      abs(m.e1rm(80, 10, 6)["value"] - old(80, 10, 6)) / old(80, 10, 6) > 0.08, True)

print("\nINOL")
check("5 reps at 85%", m.inol(5, 85.0), 0.3333)
# INOL is undefined at a true 100%; the denominator is clamped at 1, so a single
# at 100% scores the same as a single at 99% rather than blowing up.
check("a true max does not divide by zero", m.inol(1, 100.0), 1.0)
check("and matches a single at 99%", m.inol(1, 100.0), m.inol(1, 99.0))
check("no intensity -> no INOL", m.inol(5, None), None)
check("0.3 is below the useful band", m.inol_session_band(0.3), "low")
check("0.8 is optimal", m.inol_session_band(0.8), "optimal")
check("1.5 is loading", m.inol_session_band(1.5), "loading")
check("2.5 is brutal", m.inol_session_band(2.5), "brutal")
check("weekly 3.5 is brutal", m.inol_week_band(3.5), "brutal")
check("weekly 4.5 is above the ceiling", m.inol_week_band(4.5), "excessive")

print("\nPrilepin")
check("69.9% is the light zone", m.prilepin_zone(69.9), "0-69")
check("70.0% crosses into 70-79", m.prilepin_zone(70.0), "70-79")
check("79.9% is still 70-79", m.prilepin_zone(79.9), "70-79")
check("80.0% crosses into 80-89", m.prilepin_zone(80.0), "80-89")
check("89.9% is still 80-89", m.prilepin_zone(89.9), "80-89")
check("90.0% is the top zone", m.prilepin_zone(90.0), "90+")
# The zone floors are 70 / 80 / 90 and every one of them needs a case on BOTH sides,
# or the boundary can move into the gap the tests leave. 80-89 had a case at 80.0 and
# the next at 90.0, so the 90+ floor could drop to 85 with every assertion still
# green - and a whole band of 85-89% work, which is heavy back-off and top-set
# territory, would have been reported in the singles-and-doubles zone. Prilepin's
# rep prescriptions differ by a factor of three across that line, and heavy_reps,
# INOL, the intensity card and the block card all read the zone.
check("85.0% is squarely inside 80-89, not the top zone", m.prilepin_zone(85.0), "80-89")
check("87.5% too", m.prilepin_zone(87.5), "80-89")
check("nothing below 90 is ever 90+",
      {m.prilepin_zone(p) for p in (80.0, 82.5, 85.0, 87.5, 89.9)}, {"80-89"})
check("no intensity, no zone", m.prilepin_zone(None), None)
check("15 reps at 80-89 is in range", m.prilepin_verdict("80-89", 15), "in-range")
check("24 reps at 80-89 is over", m.prilepin_verdict("80-89", 24), "over")
check("3 reps at 90+ is under", m.prilepin_verdict("90+", 3), "under")

print("\nLoad monitoring")
check("AU is sRPE x duration", m.session_au(7.0, 74), 518.0)
check("AU needs a duration", m.session_au(7.0, None), None)
check("flat 7 and 28 day load -> 1.0", m.acwr(7000, 28000), 1.0)
check("acute at double the base", m.acwr(14000, 28000), 2.0)
check("no chronic base -> no ratio", m.acwr(7000, 0), None)
check("1.0 is steady", m.acwr_band(1.0), "steady")
check("1.4 is rising", m.acwr_band(1.4), "rising")
check("1.8 is a spike", m.acwr_band(1.8), "spike")
check("0.5 is undertrained", m.acwr_band(0.5), "undertrained")
check("identical days -> no monotony value", m.monotony([100] * 7), None)
check("four days on, three off", m.monotony([100, 100, 100, 100, 0, 0, 0]), 1.15)
# Foster's monotony describes how a week's work is spread, so there has to be a spread.
# One training day used to return 0.41 - a number on the same scale as a real week, in
# the same column, meaning only "you trained once".
check("one training day is not a distribution", m.monotony([700, 0, 0, 0, 0, 0, 0]), None)
check("nor are two", m.monotony([400, 0, 300, 0, 0, 0, 0]), None)
check("three is the fewest that can be even or uneven",
      m.monotony([400, 0, 300, 0, 200, 0, 0]), 0.81)
check("no monotony, no strain", m.strain(4000, m.monotony([700, 0, 0, 0, 0, 0, 0])), None)
# The minimum-days guard counts non-zero loads only because this module has nothing
# else to count. A bodyweight-only session is a training day carrying no tonnage, so
# a caller that knows which days had a session says so and the guard uses that. Two
# lifting days plus a bodyweight day is three training days, and it used to be two.
check("a bodyweight day is a training day when the caller says so",
      m.monotony([400, 0, 300, 0, 0, 0, 0], training_days=3), 0.62)
check("...and without that it is still counted as a rest day, as before",
      m.monotony([400, 0, 300, 0, 0, 0, 0]), None)
check("the count the caller passes is the one that decides, downwards too",
      m.monotony([400, 0, 300, 0, 200, 0, 0], training_days=2), None)
check("and the load series is untouched by it - only the guard moves",
      m.monotony([400, 0, 300, 0, 200, 0, 0], training_days=3),
      m.monotony([400, 0, 300, 0, 200, 0, 0]))
check("strain is load x monotony", m.strain(4000, 1.15), 4600.0)

print("\nSession shape")
check("drop-off from 340 to 320", m.fatigue_index(340, 320), 5.9)
check("no drop-off when nothing fell", m.fatigue_index(340, 340), 0.0)
check("relative intensity vs a meet max", m.relative_intensity(225, 402.3), 55.9)
check("density", m.density(12100, 74), 163.5)
check("carry work in ft-lb", m.work_ftlb(200, 50), 10000.0)
check("a carry with no distance is not work", m.work_ftlb(200, None), None)

print()
if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all metrics tests passed")
