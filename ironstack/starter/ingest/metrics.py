#!/usr/bin/env python3
"""Strength-training metrics. Pure functions: numbers in, numbers out.

No I/O, no Elasticsearch, no repo knowledge — so every formula here is unit
testable on its own (`ingest/test_metrics.py`). `index_workouts.py` imports this
module and writes the results onto set, session, day and week documents.

Each formula names its source. Where a metric has a published interpretation
band (INOL, Prilepin, ACWR), the band is here too, so a dashboard panel and the
coach agent read the same thresholds.
"""

from __future__ import annotations

import statistics

KG_PER_LB = 0.45359237
LB_PER_KG = 1 / KG_PER_LB


# --------------------------------------------------------------- estimated 1RM

# Mike Tuchscherer's RPE / reps-in-reserve table (Reactive Training Systems).
#
# The table's construction is a single sequence: a set of R reps at RPE X sits at
# the same percentage as a set of R+1 reps at RPE X+1. So one axis is enough —
# "effective reps" = reps + (10 - RPE), i.e. reps performed plus reps left in the
# tank. Keys step by 0.5 so half-point RPEs land on a real row.
#
# e = 1.0 is a true single at RPE 10 = 100%. e = 16.0 is 12 reps at RPE 6.
RPE_TABLE = {
    1.0: 100.0, 1.5: 97.8, 2.0: 95.5, 2.5: 93.9, 3.0: 92.2, 3.5: 90.7,
    4.0: 89.2, 4.5: 87.8, 5.0: 86.3, 5.5: 85.0, 6.0: 83.7, 6.5: 82.4,
    7.0: 81.1, 7.5: 79.9, 8.0: 78.6, 8.5: 77.4, 9.0: 76.2, 9.5: 75.1,
    10.0: 73.9, 10.5: 72.3, 11.0: 70.7, 11.5: 69.4, 12.0: 68.0, 12.5: 66.7,
    13.0: 65.3, 13.5: 64.0, 14.0: 62.6, 14.5: 61.3, 15.0: 59.9, 15.5: 58.6,
    16.0: 57.2,
}
_TABLE_MAX = 16.0
_TABLE_STEP = -1.4          # percentage points per 0.5 effective reps at the tail
_EXTRAPOLATE_LIMIT = 20.0   # past this the estimate is not worth making

# Confidence in an e1RM, keyed off the reps actually performed. A single at RPE 9
# is a measurement; ten reps at RPE 6 is an extrapolation across nine reps of
# accumulating fatigue. Panels filter on this; they do not pretend the two are
# the same number.
CONF_HIGH, CONF_MEDIUM, CONF_LOW = "high", "medium", "low"
REPS_HIGH_MAX = 6
REPS_MEDIUM_MAX = 9
REPS_MAX = 12               # above this, no e1RM at all


def _round_half(value: float) -> float:
    return round(value * 2) / 2


def pct_from_rpe(reps: float, rpe: float) -> float | None:
    """Percentage of 1RM a set of `reps` at `rpe` represents (RTS table)."""
    if not reps or rpe is None:
        return None
    effective = _round_half(reps + (10 - rpe))
    if effective < 1.0:
        effective = 1.0
    if effective in RPE_TABLE:
        return RPE_TABLE[effective]
    if effective > _EXTRAPOLATE_LIMIT:
        return None
    # Past the published table, continue its tail slope rather than inventing a curve.
    steps = (effective - _TABLE_MAX) / 0.5
    return round(RPE_TABLE[_TABLE_MAX] + steps * _TABLE_STEP, 1)


def epley(weight: float, reps: float) -> float | None:
    """Epley (1985). Reasonable to ~5 reps, optimistic beyond."""
    if not weight or not reps:
        return None
    return weight * (1 + reps / 30.0)


def brzycki(weight: float, reps: float) -> float | None:
    """Brzycki (1993). Breaks down above 10 reps (denominator collapses)."""
    if not weight or not reps or reps >= 37:
        return None
    return weight * 36.0 / (37.0 - reps)


def e1rm(weight: float, reps: float, rpe: float | None) -> dict | None:
    """Estimated 1RM with the model used and how much to trust it.

    Returns {"value", "method", "confidence", "pct"} or None when the set does
    not support an estimate (no load, no reps, or too many reps to extrapolate).

    RPE is the primary model: 99.9% of logged working sets carry one, and a
    submaximal set with an RPE says far more than the same set without it.
    """
    if not weight or not reps or reps > REPS_MAX:
        return None

    if rpe is not None:
        pct = pct_from_rpe(reps, rpe)
        if pct is None:
            return None
        value, method = weight * 100.0 / pct, "rpe"
    else:
        value, method, pct = epley(weight, reps), "epley", None
        if value is None:
            return None

    if reps <= REPS_HIGH_MAX:
        confidence = CONF_HIGH
    elif reps <= REPS_MEDIUM_MAX:
        confidence = CONF_MEDIUM
    else:
        confidence = CONF_LOW
    if method == "epley" and confidence == CONF_HIGH:
        confidence = CONF_MEDIUM      # no RPE means no information about proximity to failure

    return {
        "value": round(value, 1),
        "method": method,
        "confidence": confidence,
        "pct": pct,
    }


def relative_intensity(weight: float, reference: float | None) -> float | None:
    """Working weight as a percentage of a reference max (best e1RM, or meet 1RM)."""
    if not weight or not reference:
        return None
    return round(weight * 100.0 / reference, 1)


# ------------------------------------------------------------------------ INOL

# Hristo Hristov's INOL. Reps divided by the distance from a true max, so both
# how heavy and how much are in one number.
INOL_SESSION_BANDS = [
    (0.4, "low", "not enough to drive an adaptation"),
    (1.0, "optimal", "productive without accumulating fatigue"),
    (2.0, "loading", "tough, appropriate inside a loading block"),
    (float("inf"), "brutal", "very high fatigue cost"),
]
INOL_WEEK_BANDS = [
    (2.0, "easy", "recovery, or a week after a hard one"),
    (3.0, "loading", "tough but repeatable"),
    (4.0, "brutal", "sustainable only briefly"),
    (float("inf"), "excessive", "above the recommended ceiling"),
]


def inol(reps: float, pct: float | None) -> float | None:
    """INOL for one set: reps / (100 - intensity%)."""
    if not reps or pct is None:
        return None
    denominator = max(100.0 - pct, 1.0)   # a true max would divide by zero
    return round(reps / denominator, 4)


def _band(value: float | None, bands) -> str | None:
    if value is None:
        return None
    for ceiling, label, _ in bands:
        if value < ceiling:
            return label
    return bands[-1][1]


def inol_session_band(value: float | None) -> str | None:
    return _band(value, INOL_SESSION_BANDS)


def inol_week_band(value: float | None) -> str | None:
    return _band(value, INOL_WEEK_BANDS)


# -------------------------------------------------------------------- Prilepin

# Prilepin's chart: reps per set, and total reps, that Soviet weightlifting data
# found productive in each intensity zone.
PRILEPIN = {
    "<70":   {"reps_per_set": (3, 6), "total": (18, 30), "optimal": 24},
    "70-79": {"reps_per_set": (3, 6), "total": (12, 24), "optimal": 18},
    "80-89": {"reps_per_set": (2, 4), "total": (10, 20), "optimal": 15},
    "90+":   {"reps_per_set": (1, 2), "total": (4, 10),  "optimal": 7},
}
PRILEPIN_ZONES = ("<70", "70-79", "80-89", "90+")


def prilepin_zone(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct < 70:
        return "<70"
    if pct < 80:
        return "70-79"
    if pct < 90:
        return "80-89"
    return "90+"


def prilepin_verdict(zone: str | None, total_reps: float) -> str | None:
    """Whether a zone's rep total for one exercise landed inside the chart."""
    if zone not in PRILEPIN:
        return None
    low, high = PRILEPIN[zone]["total"]
    if total_reps < low:
        return "under"
    if total_reps > high:
        return "over"
    return "in-range"


# ------------------------------------------------------------------------ DOTS

# DOTS: the IPF-era replacement for Wilks. Bodyweight and total in kilograms.
DOTS_COEFF = {
    "male":   (-307.75076, 24.0900756, -0.1918759221, 0.0007391293, -0.000001093),
    "female": (-57.96288, 13.6175032, -0.1126655495, 0.0005158568, -0.0000010706),
}


def dots(bodyweight_kg: float, total_kg: float, sex: str = "male") -> float | None:
    if not bodyweight_kg or not total_kg:
        return None
    a, b, c, d, e = DOTS_COEFF[sex]
    x = bodyweight_kg
    denominator = a + b * x + c * x**2 + d * x**3 + e * x**4
    if denominator <= 0:
        return None
    return round(500.0 / denominator * total_kg, 2)


def lb_to_kg(pounds: float | None) -> float | None:
    return None if pounds is None else pounds * KG_PER_LB


# ------------------------------------------------------------- load monitoring

# The coverage audit found duration_min on 1 of 642 sessions, so session RPE x
# duration cannot describe any history. Volume load (tonnage) is the load unit
# instead — an established alternative, and one that backfills to 2023. sRPE x
# duration is available here for when duration coverage is real.
ACWR_BANDS = [
    (0.8, "undertrained", "acute load well below the recent norm"),
    (1.3, "steady", "inside the commonly cited comfort band"),
    (1.5, "rising", "loading faster than the 28-day base"),
    (float("inf"), "spike", "sharp departure from the recent norm"),
]


def session_au(session_rpe: float | None, duration_min: float | None) -> float | None:
    """Foster's arbitrary units: session RPE x duration."""
    if session_rpe is None or not duration_min:
        return None
    return round(session_rpe * duration_min, 1)


def acwr(acute_total: float, chronic_total: float, acute_days: int = 7,
         chronic_days: int = 28) -> float | None:
    """Acute:chronic workload ratio — 7-day load over the 28-day daily average.

    A trend flag, not a prediction. The ratio has taken real methodological
    criticism in the literature; treat a spike as a prompt to look, not a verdict.
    """
    if not chronic_total:
        return None
    chronic_daily = chronic_total / chronic_days
    acute_daily = acute_total / acute_days
    if not chronic_daily:
        return None
    return round(acute_daily / chronic_daily, 2)


def acwr_band(value: float | None) -> str | None:
    return _band(value, ACWR_BANDS)


def monotony(daily_loads: list[float]) -> float | None:
    """Foster's training monotony: mean daily load / SD of daily load.

    Rest days count as zeros — that is the point of the metric. A week where
    every day looks the same scores high, which is the pattern that precedes
    stagnation.
    """
    if len(daily_loads) < 2:
        return None
    spread = statistics.pstdev(daily_loads)
    if spread == 0:
        return None
    return round(statistics.fmean(daily_loads) / spread, 2)


def strain(weekly_load: float | None, monotony_value: float | None) -> float | None:
    """Foster's training strain: weekly load x monotony."""
    if weekly_load is None or monotony_value is None:
        return None
    return round(weekly_load * monotony_value, 1)


# ------------------------------------------------------------- session shape

def fatigue_index(top_e1rm: float | None, last_e1rm: float | None) -> float | None:
    """Drop-off from the best set of a lift to the last one, as a percentage.

    Positive means the estimate fell across the session.
    """
    if not top_e1rm or not last_e1rm:
        return None
    return round((top_e1rm - last_e1rm) * 100.0 / top_e1rm, 1)


def density(volume_lb: float | None, duration_min: float | None) -> float | None:
    """Pounds moved per minute of training."""
    if not volume_lb or not duration_min:
        return None
    return round(volume_lb / duration_min, 1)


def work_ftlb(weight_lb: float | None, distance_ft: float | None) -> float | None:
    """Work done in a loaded carry or ruck — the tonnage equivalent for events."""
    if not weight_lb or not distance_ft:
        return None
    return round(weight_lb * distance_ft, 1)
