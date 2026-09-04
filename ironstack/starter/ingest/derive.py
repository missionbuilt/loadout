#!/usr/bin/env python3
"""Derived analytics fields, computed once at index time.

`metrics.py` holds the formulas; this module is what knows about the repo — the
exercise taxonomy, the meet records, and each lift's history. `index_workouts.py`
calls `build_reference()` once, then `set_fields()` and `session_fields()` per
session.

Relative intensity is the reason this file exists. A working weight only means
something against a max, and the honest max is the best estimate that existed
*at the time* — never a lookahead from a PR set months later. So the reference
is built by walking every session in date order and carrying a running best per
exercise, the same shape as `session_links()` in the indexer.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import metrics

REPO = Path(__file__).resolve().parent.parent

# Relative intensity is meaningful against what the lifter can do *now*, not
# against an all-time best they may be months detrained from. So the reference
# max is the best estimate inside a trailing window; an older best is still used
# when there is nothing recent, but the set records that it is stale.
REFERENCE_WINDOW_DAYS = 90
TAXONOMY_PATH = REPO / "config" / "exercises.json"
MEETS_DIR = REPO / "meets"

_taxonomy: dict | None = None


# ------------------------------------------------------------------- taxonomy

def load_taxonomy() -> dict:
    """Exercise name -> {pattern, muscles, lift_family, competition, unilateral}."""
    global _taxonomy
    if _taxonomy is None:
        raw = json.loads(TAXONOMY_PATH.read_text())
        resolved = {}
        for name, entry in raw.items():
            target = entry.get("alias_of")
            # An alias carries the canonical name with it, so "Competition Deadlift"
            # and "Comp Deadlift" share one history rather than splitting it in two.
            resolved[name] = {**(raw[target] if target else entry),
                              "canonical": target or name}
        _taxonomy = resolved
    return _taxonomy


class UnknownExercise(ValueError):
    """Raised when a log names an exercise the taxonomy has never seen."""


def classify(name: str) -> dict:
    """An unknown exercise name is a hard error, not a silent gap.

    The same rule as an unknown `key=` in the shorthand: a renamed lift must not
    quietly drop out of the muscle-group and ratio metrics. Raised rather than
    exited so callers stay testable and can report it their own way.
    """
    taxonomy = load_taxonomy()
    if name not in taxonomy:
        raise UnknownExercise(
            f"exercise {name!r} is not in config/exercises.json. "
            "Add it (and its movement pattern) there, or fix the name in the log."
        )
    return taxonomy[name]


# ------------------------------------------------------------------ reference

class Reference:
    """Best e1RM per exercise, and meet maxes per lift, as of each session."""

    def __init__(self, bests: dict, meets: dict):
        self._bests = bests      # session_id -> {slug: (lb, "recent"|"all-time")}
        self._meets = meets      # session_id -> {family: lb}

    def best_before(self, session_id: str, slug: str) -> tuple[float, str] | None:
        return self._bests.get(session_id, {}).get(slug)

    def meet_max(self, session_id: str, family: str | None) -> float | None:
        if not family:
            return None
        return self._meets.get(session_id, {}).get(family)


def lift_slug(name: str) -> str:
    """Slug of the canonical exercise, so aliases share one series."""
    from index_workouts import slugify

    return slugify(classify(name)["canonical"])


def _best_working_e1rm(log: dict) -> dict:
    """Best e1RM per canonical exercise within one session."""
    out: dict[str, float] = {}
    for exercise in log.get("exercises", []):
        slug = lift_slug(exercise["name"])
        for s in exercise.get("sets", []):
            if s.get("set_type", "working") != "working":
                continue
            if s.get("rep_unit", "reps") != "reps":
                continue
            estimate = metrics.e1rm(s.get("weight_lb", 0), s["reps"], s.get("rpe"))
            if estimate and estimate["confidence"] != metrics.CONF_LOW:
                # Low-confidence estimates (10-12 reps) are worth showing but not
                # worth setting the bar every later percentage is measured against.
                out[slug] = max(out.get(slug, 0), estimate["value"])
    return out


def meet_bodyweights() -> list[tuple[str, float]]:
    """(date, bodyweight in lb) from the meet records."""
    out = []
    for path in sorted(MEETS_DIR.glob("*.json")):
        meet = json.loads(path.read_text())
        if meet.get("bodyweight_kg"):
            out.append((meet["date"], round(meet["bodyweight_kg"] * metrics.LB_PER_KG, 1)))
    return sorted(out)


def _meet_maxes() -> list[tuple[str, dict]]:
    """(date, {family: best made attempt in lb}) for every meet, chronological."""
    out = []
    for path in sorted(MEETS_DIR.glob("*.json")):
        meet = json.loads(path.read_text())
        best: dict[str, float] = {}
        for attempt in meet.get("attempts", []):
            if not attempt.get("made"):
                continue
            lift = attempt["lift"]
            pounds = attempt["weight_kg"] * metrics.LB_PER_KG
            best[lift] = max(best.get(lift, 0), round(pounds, 1))
        if best:
            out.append((meet["date"], best))
    return sorted(out)


def build_reference(logs: list[tuple[str, str, dict]]) -> Reference:
    """logs: (date, session_id, log) for every session in the repo, any order."""
    ordered = sorted(logs, key=lambda t: (t[0], t[1]))

    bests: dict[str, dict] = {}
    history: dict[str, list[tuple[date, float]]] = {}
    for day_str, session_id, log in ordered:
        day = date.fromisoformat(day_str)
        cutoff = day - timedelta(days=REFERENCE_WINDOW_DAYS)
        snapshot: dict[str, tuple[float, str]] = {}
        for slug, entries in history.items():
            recent = [v for d, v in entries if d >= cutoff]
            if recent:
                snapshot[slug] = (max(recent), "recent")
            else:
                snapshot[slug] = (max(v for _, v in entries), "all-time")
        bests[session_id] = snapshot              # strictly before this session
        for slug, value in _best_working_e1rm(log).items():
            history.setdefault(slug, []).append((day, value))

    meet_history = _meet_maxes()
    meets: dict[str, dict] = {}
    for day, session_id, _log in ordered:
        current: dict[str, float] = {}
        for meet_day, best in meet_history:
            if meet_day <= day:
                current = best
        meets[session_id] = current

    return Reference(bests, meets)


# ------------------------------------------------------------- derived fields

def set_fields(exercise: dict, s: dict, session_id: str,
               reference: Reference | None) -> dict:
    """Analytics fields for one set document."""
    taxonomy = classify(exercise["name"])
    slug = lift_slug(exercise["name"])
    fields: dict = {
        "lift_slug": slug,
        "pattern": taxonomy.get("pattern"),
        "muscles_primary": taxonomy.get("muscles_primary", []),
        "muscles_secondary": taxonomy.get("muscles_secondary", []),
        "lift_family": taxonomy.get("lift_family"),
        "is_competition_lift": taxonomy.get("competition", False),
        "is_unilateral": taxonomy.get("unilateral", False),
        "work_ftlb": metrics.work_ftlb(s.get("weight_lb"), s.get("distance_ft")),
        "tut_sec": s["reps"] if s.get("rep_unit") == "seconds" else None,
    }

    weight = s.get("weight_lb", 0)
    reps = s.get("reps")
    is_working = s.get("set_type", "working") == "working"
    if not (is_working and s.get("rep_unit", "reps") == "reps" and weight and reps):
        return fields

    estimate = metrics.e1rm(weight, reps, s.get("rpe"))
    if estimate:
        fields["est_e1rm"] = estimate["value"]
        fields["e1rm_method"] = estimate["method"]
        fields["e1rm_confidence"] = estimate["confidence"]

    # Intensity against the best estimate that existed before today, preferring
    # one from the last REFERENCE_WINDOW_DAYS. With no history for this lift yet,
    # the set is measured against its own estimate — which is what the RPE said
    # about it, and is marked as such.
    prior = reference.best_before(session_id, slug) if reference else None
    if prior:
        fields["intensity_pct"] = metrics.relative_intensity(weight, prior[0])
        fields["intensity_ref"] = prior[1]
    elif estimate:
        fields["intensity_pct"] = metrics.relative_intensity(weight, estimate["value"])
        fields["intensity_ref"] = "self"

    meet_max = reference.meet_max(session_id, taxonomy.get("lift_family")) if reference else None
    if meet_max:
        fields["pct_meet_max"] = metrics.relative_intensity(weight, meet_max)

    intensity = fields.get("intensity_pct")
    fields["prilepin_zone"] = metrics.prilepin_zone(intensity)
    if exercise.get("category") == "main":
        fields["inol"] = metrics.inol(reps, intensity)
    return fields


ZONE_FIELD = {"<70": "lt70", "70-79": "z70_79", "80-89": "z80_89", "90+": "z90plus"}


def session_fields(set_docs: list[dict], session: dict, totals: dict,
                   avg_working_rpe: float | None) -> dict:
    """Analytics fields for the session document, from its own set documents."""
    working = [d for d in set_docs if d.get("set_type") == "working"]

    inol_by_lift: dict[str, float] = {}
    zone_reps = {name: 0 for name in ZONE_FIELD.values()}
    for doc in working:
        if doc.get("inol"):
            name = doc["exercise"]["name"]
            inol_by_lift[name] = round(inol_by_lift.get(name, 0) + doc["inol"], 4)
        zone = doc.get("prilepin_zone")
        # Prilepin's chart describes main-lift work. Accessory reps are measured
        # against their own estimates and would swamp the zones if counted.
        if zone and doc.get("rep_unit") == "reps" and doc["exercise"].get("category") == "main":
            zone_reps[ZONE_FIELD[zone]] += int(doc["reps"])

    # Drop-off across the session's main lifts: best estimate of the day against
    # the last one recorded for the same lift.
    drops = []
    for name in {d["exercise"]["name"] for d in working
                 if d["exercise"].get("category") == "main"}:
        lift = [d for d in working if d["exercise"]["name"] == name and d.get("est_e1rm")]
        if len(lift) < 2:
            continue
        drop = metrics.fatigue_index(max(d["est_e1rm"] for d in lift), lift[-1]["est_e1rm"])
        if drop is not None:
            drops.append(drop)

    duration = session.get("duration_min")
    return {
        "inol_total": round(sum(inol_by_lift.values()), 4) if inol_by_lift else None,
        "inol_by_lift": [{"exercise": k, "inol": v, "band": metrics.inol_session_band(v)}
                         for k, v in sorted(inol_by_lift.items())],
        "prilepin_reps": zone_reps,
        "fatigue_index": round(sum(drops) / len(drops), 1) if drops else None,
        "density_lb_per_min": metrics.density(totals.get("tonnage_lb"), duration),
        "load_au": metrics.session_au(avg_working_rpe, duration),
        # AU is always derived from the session's average working RPE; no session RPE
        # is logged today. The flag says "this load figure is an estimate", which it is
        # whenever there is a duration to compute one from.
        "load_estimated": bool(duration),
    }


# ----------------------------------------------------------------- rollups

# Daily and weekly documents, built in the same pass as everything else rather
# than by an Elasticsearch transform. The indexer already holds every session in
# memory, the ids are deterministic so the documents rebuild from the repo like
# any other, and a continuous transform would need a reset after every reindex
# that changed historical values. See claude/ironstack-indexing-procedure.md.
#
# The load unit is tonnage, not session RPE x duration: duration exists on one
# session out of 642, so an AU-based series could not describe any history.

ACUTE_DAYS = 7
CHRONIC_DAYS = 28
COMP_FAMILIES = ("squat", "bench", "deadlift")


def _iso_week(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def rollup_docs(docs: list[tuple[str, str, dict]]) -> list[tuple[str, str, dict]]:
    """workout-daily and workout-weekly documents for the whole repo."""
    sessions = [d for index, _id, d in docs if index == "workout-sessions"]
    sets = [d for index, _id, d in docs if index == "workout-sets"]
    if not sessions:
        return []

    by_day: dict[str, dict] = {}
    for session in sessions:
        day = by_day.setdefault(session["date"], {
            "sessions": 0, "tonnage_lb": 0.0, "working_sets": 0, "reps": 0,
            "inol_total": 0.0, "rpes": [], "load_au": 0.0, "bodyweight_lb": None,
            "sleep_hrs": None, "duration_min": 0.0,
            "prilepin_reps": {k: 0 for k in ZONE_FIELD.values()},
        })
        totals = session.get("totals") or {}
        day["sessions"] += 1
        day["tonnage_lb"] += totals.get("tonnage_lb") or 0
        day["working_sets"] += totals.get("working_sets") or 0
        day["reps"] += totals.get("reps") or 0
        day["inol_total"] += session.get("inol_total") or 0
        day["duration_min"] += session.get("duration_min") or 0
        day["load_au"] += session.get("load_au") or 0
        if session.get("avg_working_rpe") is not None:
            day["rpes"].append(session["avg_working_rpe"])
        for zone, count in (session.get("prilepin_reps") or {}).items():
            day["prilepin_reps"][zone] += count
        measures = session.get("metrics") or {}
        if measures.get("bodyweight_lb"):
            day["bodyweight_lb"] = measures["bodyweight_lb"]
        if measures.get("sleep_hrs"):
            day["sleep_hrs"] = measures["sleep_hrs"]

    # Best e1RM and working sets per muscle, per day, from the set documents.
    best_by_day: dict[str, dict[str, float]] = {}
    muscles_by_day: dict[str, dict[str, int]] = {}
    inol_by_day: dict[str, dict[str, float]] = {}
    for doc in sets:
        if doc.get("set_type") != "working":
            continue
        day = doc["date"]
        if doc.get("est_e1rm") and doc.get("e1rm_confidence") != metrics.CONF_LOW:
            slot = best_by_day.setdefault(day, {})
            slug = doc.get("lift_slug")
            slot[slug] = max(slot.get(slug, 0), doc["est_e1rm"])
        counts = muscles_by_day.setdefault(day, {})
        for muscle in doc.get("muscles_primary") or []:
            counts[muscle] = counts.get(muscle, 0) + 1
        if doc.get("inol"):
            lifts = inol_by_day.setdefault(day, {})
            name = doc["exercise"]["name"]
            lifts[name] = round(lifts.get(name, 0) + doc["inol"], 4)

    days = sorted(by_day)
    first, last = date.fromisoformat(days[0]), date.fromisoformat(days[-1])

    # A continuous calendar, rest days included as zero load — monotony is a
    # statement about how a week is distributed, so the empty days count.
    calendar: dict[date, float] = {}
    cursor = first
    while cursor <= last:
        calendar[cursor] = by_day.get(cursor.isoformat(), {}).get("tonnage_lb", 0.0)
        cursor += timedelta(days=1)

    # Every bodyweight the repo knows about, sessions and meets alike.
    bodyweight_series = sorted(
        [(d, by_day[d]["bodyweight_lb"]) for d in days if by_day[d]["bodyweight_lb"]]
        + meet_bodyweights()
    )

    out: list[tuple[str, str, dict]] = []

    for day_str in days:
        day = by_day[day_str]
        as_date = date.fromisoformat(day_str)
        doc = {
            "@timestamp": f"{day_str}T12:00:00Z",
            "date": day_str,
            "weekday": as_date.strftime("%A"),
            "iso_week": _iso_week(as_date),
            "sessions": day["sessions"],
            "tonnage_lb": round(day["tonnage_lb"], 1),
            "working_sets": day["working_sets"],
            "reps": day["reps"],
            "duration_min": day["duration_min"] or None,
            "inol_total": round(day["inol_total"], 4) or None,
            "load_au": round(day["load_au"], 1) or None,
            "avg_working_rpe": round(sum(day["rpes"]) / len(day["rpes"]), 2) if day["rpes"] else None,
            "bodyweight_lb": day["bodyweight_lb"],
            "sleep_hrs": day["sleep_hrs"],
            "prilepin_reps": day["prilepin_reps"],
            "best_e1rm": [{"lift_slug": k, "value": v}
                          for k, v in sorted(best_by_day.get(day_str, {}).items())],
            "sets_by_muscle": [{"muscle": k, "sets": v}
                               for k, v in sorted(muscles_by_day.get(day_str, {}).items())],
        }
        out.append(("workout-daily", day_str, doc))

    # ------------------------------------------------------------------ weekly
    weeks: dict[str, list[str]] = {}
    for day_str in days:
        weeks.setdefault(_iso_week(date.fromisoformat(day_str)), []).append(day_str)

    e1rm_history: dict[str, list[tuple[date, float]]] = {}
    for day_str, slots in best_by_day.items():
        for slug, value in slots.items():
            e1rm_history.setdefault(slug, []).append((date.fromisoformat(day_str), value))

    for week, week_days in sorted(weeks.items()):
        members = [by_day[d] for d in week_days]
        end = date.fromisoformat(week_days[-1])
        start = end - timedelta(days=end.weekday())

        tonnage = round(sum(m["tonnage_lb"] for m in members), 1)
        rpes = [r for m in members for r in m["rpes"]]

        acute = sum(v for d, v in calendar.items() if end - timedelta(days=ACUTE_DAYS - 1) <= d <= end)
        chronic = sum(v for d, v in calendar.items() if end - timedelta(days=CHRONIC_DAYS - 1) <= d <= end)
        # ACWR only means something once there is a 28-day base to compare against.
        ratio = metrics.acwr(acute, chronic) if (end - first).days >= CHRONIC_DAYS else None

        week_loads = [calendar.get(start + timedelta(days=i), 0.0) for i in range(7)]
        mono = metrics.monotony(week_loads)

        zones = {k: sum(m["prilepin_reps"][k] for m in members) for k in ZONE_FIELD.values()}

        best: dict[str, float] = {}
        for day_str in week_days:
            for slug, value in best_by_day.get(day_str, {}).items():
                best[slug] = max(best.get(slug, 0), value)

        muscles: dict[str, int] = {}
        for day_str in week_days:
            for muscle, count in muscles_by_day.get(day_str, {}).items():
                muscles[muscle] = muscles.get(muscle, 0) + count

        lifts: dict[str, float] = {}
        for day_str in week_days:
            for name, value in inol_by_day.get(day_str, {}).items():
                lifts[name] = round(lifts.get(name, 0) + value, 4)

        bodyweights = [m["bodyweight_lb"] for m in members if m["bodyweight_lb"]]
        if bodyweights:
            bodyweight = round(sum(bodyweights) / len(bodyweights), 1)
            bodyweight_source = "logged"
        else:
            carried = [w for d, w in bodyweight_series if d <= end.isoformat()]
            bodyweight = carried[-1] if carried else None
            bodyweight_source = "carried" if bodyweight else None

        # Projected meet total from the week's best estimates of the three lifts,
        # and the DOTS that total would score at the week's bodyweight.
        # Projection uses the competition lifts only. A high-bar squat or a wide-grip
        # bench belongs to the same family for grouping, but it does not transfer to
        # the platform one for one, and a total built from variants reads high.
        comp_best = {family: 0.0 for family in COMP_FAMILIES}
        window = end - timedelta(days=REFERENCE_WINDOW_DAYS)
        for slug, entries in e1rm_history.items():
            family = _projection_family(slug)
            if family not in comp_best:
                continue
            recent = [v for d, v in entries if window <= d <= end]
            if recent:
                comp_best[family] = max(comp_best[family], max(recent))
        projected = round(sum(comp_best.values()), 1) if all(comp_best.values()) else None
        score = (metrics.dots(metrics.lb_to_kg(bodyweight), metrics.lb_to_kg(projected))
                 if projected and bodyweight else None)

        inol_total = round(sum(lifts.values()), 4) if lifts else None
        # Hristov's weekly bands are per exercise. The hardest single lift of the
        # week is the number worth banding; the total is context, not a verdict.
        hardest = max(lifts.items(), key=lambda kv: kv[1]) if lifts else None
        out.append(("workout-weekly", week, {
            "@timestamp": f"{end.isoformat()}T12:00:00Z",
            "iso_week": week,
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "training_days": len(week_days),
            "sessions": sum(m["sessions"] for m in members),
            "tonnage_lb": tonnage,
            "working_sets": sum(m["working_sets"] for m in members),
            "reps": sum(m["reps"] for m in members),
            "avg_working_rpe": round(sum(rpes) / len(rpes), 2) if rpes else None,
            "inol_total": inol_total,
            "inol_hardest_lift": hardest[0] if hardest else None,
            "inol_hardest": hardest[1] if hardest else None,
            "inol_hardest_band": metrics.inol_week_band(hardest[1]) if hardest else None,
            "inol_by_lift": [{"exercise": k, "inol": v, "band": metrics.inol_week_band(v)}
                             for k, v in sorted(lifts.items())],
            "prilepin_reps": zones,
            "load_7d": round(acute, 1),
            "load_28d": round(chronic, 1),
            "acwr": ratio,
            "acwr_band": metrics.acwr_band(ratio),
            "monotony": mono,
            "strain": metrics.strain(tonnage, mono),
            "bodyweight_lb": bodyweight,
            "bodyweight_source": bodyweight_source,
            "projected_total_lb": projected,
            "dots": score,
            "best_e1rm": [{"lift_slug": k, "value": v} for k, v in sorted(best.items())],
            "sets_by_muscle": [{"muscle": k, "sets": v} for k, v in sorted(muscles.items())],
        }))

    return out


_slug_family: dict[str, str] | None = None


def _projection_family(slug: str) -> str | None:
    """Competition lift family for a canonical slug, competition lifts only.

    Deliberately stricter than `lift_family`: Comp Bench qualifies, Extra Wide
    Bench Press does not, even though both are in the bench family.
    """
    global _slug_family
    if _slug_family is None:
        from index_workouts import slugify

        _slug_family = {}
        for entry in load_taxonomy().values():
            family = entry.get("lift_family")
            if family in COMP_FAMILIES and entry.get("competition"):
                _slug_family[slugify(entry["canonical"])] = family
    return _slug_family.get(slug)
