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
from datetime import date, datetime, timedelta, timezone
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
DEFAULTS_PATH = REPO / "config" / "defaults.json"

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
        # The close matches go in the message. CI cannot ask, but it can say what the
        # name probably was, which turns a stop into a one-line fix.
        import suggest

        raise UnknownExercise(
            suggest.format_candidates(name, suggest.candidates(name, taxonomy))
            + "\n       Add it to config/exercises.json with its movement pattern, "
              "or fix the name in the log."
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


def best_working_e1rm(log: dict) -> dict:
    """Best e1RM per canonical exercise within one session.

    Public because it is the definition of "a number worth setting a bar by", and
    two things now need that definition to be the same one: the intensity
    reference built below, and `ingest/ceiling.py`, which has no cluster to read
    `est_e1rm` back from. A private name there would have meant a second copy of
    the working-set / rep-unit / not-low filter, and a second copy is how the
    guardrail and the indexed data drift apart.
    """
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
        for slug, value in best_working_e1rm(log).items():
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
        # The canonical name, not exercise.name. The raw logged spelling is whatever was
        # typed that day, which is why the Lift header read COMPETITION DEADLIFT for one
        # lift and COMP BENCH for another. load_taxonomy() resolves aliases onto a single
        # canonical, so this is the name that matches the slug rather than the keystrokes.
        "lift_name": taxonomy.get("canonical"),
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


ZONE_FIELD = {"0-69": "lt70", "70-79": "z70_79", "80-89": "z80_89", "90+": "z90plus"}


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
# Below this many training days inside the 28-day window, the acute:chronic ratio stops
# describing a spike and starts describing a return. Three blank weeks and one week back
# gives chronic == acute, so the ratio is 4.0 by arithmetic - a real number, and a
# meaningless one. Mike trains roughly four days a week, so a normal 28-day window carries
# ~16; eight is half of that and well clear of a taper.
LAYOFF_MIN_TRAINING_DAYS = 8
COMP_FAMILIES = ("squat", "bench", "deadlift")


def _iso_week(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def rollup_docs(docs: list[tuple[str, str, dict]],
                today: date | None = None) -> list[tuple[str, str, dict]]:
    """workout-daily and workout-weekly documents for the whole repo.

    `today` decides which week is still in progress, and so how many days of it are
    real. UTC for the same reason signal_docs() uses it: CI runs there.
    """
    today = today or datetime.now(timezone.utc).date()
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
        # ...and once that base has training in it. The length guard above only asks
        # whether 28 days have elapsed, not whether they were trained.
        chronic_days_trained = sum(
            1 for d, v in calendar.items()
            if end - timedelta(days=CHRONIC_DAYS - 1) <= d <= end and v > 0)
        off_layoff = ratio is not None and chronic_days_trained < LAYOFF_MIN_TRAINING_DAYS

        # Days that have not happened yet are not rest days. Monotony is mean daily load
        # over its SD, so padding an unfinished week out to seven with zeros pulls the
        # mean down and the SD up and reports a calm, evenly-spread week that is really a
        # Wednesday - 2026-W36 read 1.09/58,767 padded against 1.31/70,629 over the six
        # days that had happened. A CLOSED week is unaffected: its Sunday is on or before
        # today, so (today - start).days + 1 is already >= 7 and the clamp is a no-op.
        elapsed = max(1, min(7, (today - start).days + 1))
        week_loads = [calendar.get(start + timedelta(days=i), 0.0) for i in range(elapsed)]
        mono = metrics.monotony(week_loads)
        week_state = "in-progress" if week == _iso_week(today) else "closed"

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
            # Monotony, strain and every total below cover only the days that have
            # happened when this is "in-progress". Consumers mark it provisional.
            "week_state": week_state,
            "sessions": sum(m["sessions"] for m in members),
            "tonnage_lb": tonnage,
            "working_sets": sum(m["working_sets"] for m in members),
            "reps": sum(m["reps"] for m in members),
            "avg_working_rpe": round(sum(rpes) / len(rpes), 2) if rpes else None,
            "inol_total": inol_total,
            "inol_hardest_lift": hardest[0] if hardest else None,
            "inol_hardest": hardest[1] if hardest else None,
            "inol_hardest_band": metrics.inol_week_band(hardest[1]) if hardest else None,
            # The band name alone is a measurement, not a judgment: "brutal" is the
            # verdict, "sustainable only briefly" is why. Carried on the row so the
            # copy cannot drift from the thresholds it describes.
            "inol_hardest_gloss": metrics.inol_week_gloss(hardest[1]) if hardest else None,
            "inol_by_lift": [{"exercise": k, "inol": v, "band": metrics.inol_week_band(v)}
                             for k, v in sorted(lifts.items())],
            "prilepin_reps": zones,
            "load_7d": round(acute, 1),
            "load_28d": round(chronic, 1),
            "acwr": ratio,
            "acwr_band": metrics.acwr_band(ratio),
            "acwr_gloss": metrics.acwr_gloss(ratio),
            "chronic_days_trained": chronic_days_trained,
            "acwr_off_layoff": off_layoff,
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


# ------------------------------------------------------------------ signals

# The three Overview verdict cards read these rows instead of the live indices.
#
# The point is the window, not the arithmetic. Every one of those cards defines its own
# window in ES|QL ("last 365 days", "the last 13 weeks") and the dashboard time picker is
# ANDed on top, so at "Last 30 days" the drift card ruled "Nothing is drifting" over a
# real 17-day calves gap. Phase 0 taught the cards to notice and decline. This removes the
# cause: an index with NO date-typed field anywhere is not reachable by the picker at all.
# Verified in the browser on Sept 5 with kibana/probe_notime.py — at Last 15 minutes a
# card reading a no-date index still returned every row while the control went to zero.
#
# So: keep the freshness stamp as a keyword string. A `date` mapping here, even one named
# computed_at, is what Kibana reaches for when it applies the range, and it would silently
# undo the whole mechanism with no visible symptom.
#
# One document per ROW, not per signal. ES|QL has no nested support, so an array of group
# objects comes back as parallel multivalued fields with no guaranteed alignment between
# them. A row per group keeps the cards' result shape identical to what they read today.
#
# The verdict arithmetic stays in the Liquid. `gap = now - last_trained` has to be
# computed when the page is drawn: decided here it would freeze at index time and read
# "Calves: 17 days" three days after it became 20.

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

SIGNAL_INDEX = "ironstack-signals"
DRIFT_WINDOW_DAYS = 365
INTENSITY_WEEKS = 13
LOAD_WEEKS = 200


# --- taper: how this meet cycle is loading against the ones already lifted ----
#
# The comparison the lifter needs at seven weeks out, and the one no phone app can
# make: this cycle's run-in laid over the same weeks before every meet already on
# the record. Aligned by ISO week rather than by date, so a Saturday meet and a
# Sunday meet line up instead of drifting a week apart.
#
# Frozen here for the usual reason - the alignment is a join against meets/, which
# ES|QL cannot express - and for one more. A cumulative total over "the weeks so
# far" is a different sum every week; computed in Liquid off whatever rows the
# picker let through, it would be the same class of lie the signals index exists
# to remove.
#
# The week in progress is marked partial and excluded from every cumulative total.
# A half-finished week laid against a finished one reads as a collapse in volume
# that is really just a Wednesday.

TAPER_WEEKS = 8


def _meet_cycles(today: date) -> list[dict]:
    """Every meet on the record plus the one being trained for, oldest first."""
    cycles: list[dict] = []
    for path in sorted(MEETS_DIR.glob("*.json")):
        meet = json.loads(path.read_text())
        attempts = meet.get("attempts") or []
        total_kg = meet.get("total_kg")
        cycles.append({
            "cycle": meet.get("meet_id") or meet["date"],
            "meet_date": meet["date"],
            "attempts_made": sum(1 for a in attempts if a.get("made")) if attempts else None,
            "attempts_total": len(attempts) or None,
            "meet_total_lb": round(total_kg * metrics.LB_PER_KG, 1) if total_kg else None,
        })
    planned = ((json.loads(DEFAULTS_PATH.read_text()).get("program") or {})
               .get("meet_date"))
    # Only if it is not already lifted: once the meet file lands, the record is the
    # better source and the planned date is a leftover in the config.
    if planned and not any(c["meet_date"] == planned for c in cycles):
        cycles.append({"cycle": planned, "meet_date": planned, "attempts_made": None,
                       "attempts_total": None, "meet_total_lb": None})
    for c in cycles:
        day = date.fromisoformat(c["meet_date"])
        c["upcoming"] = day >= today
        c["cycle_label"] = f"{MONTHS[day.month - 1]} {day.year}"
    return sorted(cycles, key=lambda c: c["meet_date"])


def _preceding_cumulative(monday: date, by_week: dict, first_week: str,
                          this_week: str, today: date) -> tuple[float, int, int]:
    """The closed weeks immediately behind `monday`, at most TAPER_WEEKS of them.

    The cumulative has to be the SAME measurement on every row or `cum_weeks` cannot be
    the card's guard. Anchoring the current cycle's running total on today and a peer's
    on its own meet made `cum_weeks: 7` and `cum_weeks: 1` at the same weeks_out two
    different questions, and a coincidental match would have let the card divide one by
    the other. So neither side gets a special case: a row's cumulative is the eight
    weeks behind that row's own week, wherever in whichever cycle that week sits.

    A blank week inside the span counts - a rest week in a run-in is a fact about the
    run-in, not a gap in it. The week in progress never contributes, and weeks before
    the log begins are not invented, so a row near the start of the corpus honestly
    reports a shorter span rather than borrowing one.
    """
    tonnage, heavy, counted = 0.0, 0, 0
    for back in range(TAPER_WEEKS, 0, -1):
        prior = monday - timedelta(days=7 * back)
        if prior.isoformat() < first_week or prior > today:
            continue
        iso = _iso_week(prior)
        if iso == this_week:
            continue
        week = by_week.get(iso) or {}
        zones = week.get("prilepin_reps") or {}
        tonnage += week.get("tonnage_lb") or 0.0
        heavy += (zones.get("z80_89") or 0) + (zones.get("z90plus") or 0)
        counted += 1
    return tonnage, heavy, counted


def _taper_rows(docs: list[tuple[str, str, dict]], weekly: list[dict],
                today: date, stamp: str) -> list[tuple[str, str, dict]]:
    """One row per (meet cycle, weeks out), eight weeks deep."""
    by_week = {w["iso_week"]: w for w in weekly}
    if not by_week:
        return []

    # Hardest working set of the week, competition families only. Restricted on
    # purpose: a top set is a taper signal only on the lifts being tapered for, and
    # a lateral raise at 100% of its own reference would otherwise outrank a squat
    # at 88% and make the intensity line meaningless.
    top: dict[str, float] = {}
    for index, _id, doc in docs:
        if index != "workout-sets" or doc.get("set_type") != "working":
            continue
        pct = doc.get("intensity_pct")
        if not pct or doc.get("lift_family") not in COMP_FAMILIES:
            continue
        week = _iso_week(date.fromisoformat(doc["date"]))
        top[week] = max(top.get(week, 0.0), pct)

    first_week = min(w["week_start"] for w in weekly)
    this_week = _iso_week(today)
    out: list[tuple[str, str, dict]] = []

    for c in _meet_cycles(today):
        meet_day = date.fromisoformat(c["meet_date"])
        meet_monday = meet_day - timedelta(days=meet_day.weekday())
        # Every cycle emits the same eight rows, anchored on its own meet. The row set
        # is not where the current cycle differs from its peers - the cumulative is, and
        # that is now computed identically for both by _preceding_cumulative().
        for n in range(TAPER_WEEKS, 0, -1):
            monday = meet_monday - timedelta(days=7 * (n - 1))
            # Before the log begins, or still ahead of today: no row at all. A zero
            # row here would read as a rest week the lifter never took.
            if monday.isoformat() < first_week or monday > today:
                continue
            iso = _iso_week(monday)
            week = by_week.get(iso) or {}
            partial = iso == this_week
            zones = week.get("prilepin_reps") or {}
            heavy = (zones.get("z80_89") or 0) + (zones.get("z90plus") or 0)
            tonnage = week.get("tonnage_lb") or 0.0
            cum_tonnage, cum_heavy, counted = _preceding_cumulative(
                monday, by_week, first_week, this_week, today)
            out.append((SIGNAL_INDEX, f"taper:{c['cycle']}:{n}", {
                "signal": "taper",
                "computed_through": stamp,
                "cycle": c["cycle"],
                "cycle_label": c["cycle_label"],
                "meet_date": c["meet_date"],
                # Keywords, not booleans, and deliberately. The card branches on both
                # of these, and Liquid treats the STRING "false" as truthy - so if
                # Kibana ever hands a boolean to the template as text, a boolean test
                # inverts silently and the card rules on the wrong cycle. A keyword
                # compared with == cannot fail that way in either Liquid.
                "cycle_role": "current" if c["upcoming"] else "past",
                "attempts_made": c["attempts_made"],
                "attempts_total": c["attempts_total"],
                "meet_total_lb": c["meet_total_lb"],
                "weeks_out": n,
                "iso_week": iso,
                "week_state": "in-progress" if partial else "closed",
                "training_days": week.get("training_days") or 0,
                "tonnage_lb": round(tonnage, 1),
                "avg_working_rpe": week.get("avg_working_rpe"),
                "heavy": heavy,
                "top_pct": top.get(iso),
                "projected_total_lb": week.get("projected_total_lb"),
                # Totals over the closed weeks immediately BEHIND this row's week, at
                # most TAPER_WEEKS of them, on the same rule for every row of every
                # cycle. cum_weeks is how many that came to, so two rows at the same
                # weeks_out with the same cum_weeks are measuring the same span by
                # construction rather than by luck. It stays the card's guard: a row
                # near the start of the log has fewer weeks behind it and says so, and
                # the card should still decline rather than scale one span onto another.
                # None, not 0, when nothing has been counted yet. strip_nones() drops
                # the field entirely, so a card cannot read a zero that only means "no
                # closed week in this cycle's window" and divide it into a peer total.
                "cum_weeks": counted or None,
                "cum_tonnage_lb": round(cum_tonnage, 1) if counted else None,
                "cum_heavy": cum_heavy if counted else None,
            }))
    return out


# --- blocks, tags and projection: the Program, History, Mindset and Meets verdicts ---
#
# BLOCK RUNS. `program.block` is a block TYPE, not a block instance: "strength" spans
# 2023-05-29 to 2026-09-04 across nine separate runs. So a block is a maximal run of
# consecutive sessions sharing a name, and "your last strength block" means the previous
# run with the same name - never the previous run of any name. Comparing a strength block
# to a hypertrophy block on heavy work is measuring the program's intent, not the
# lifter's: hypertrophy is high-volume and low-intensity by construction, so strength
# wins that comparison every time and the verdict is trivially true.
#
# HEAVY REPS PER SESSION, not share. Measured over Mike's nine strength blocks the two
# agree on direction, and the rate is the safer one to rank: the current block carries 67
# main-lift reps, and a share off a denominator that small inverts on a single set. This
# is the same lesson the intensity card learned on weeks. The share is still written out,
# with its denominator, as evidence.
#
# TAGS. Notes exist only from 2026-09-01 - 31 of them, four days. Ranking a tag over that
# would be the confident-empty verdict this whole index exists to prevent, so every tag
# row carries the corpus span and the card refuses to rank until it is wide enough. The
# card becomes useful on its own as notes accumulate; nothing has to be rebuilt.

# Every block run the log contains, deliberately uncapped. A cap here is a hidden
# window that changes the verdict: at 14 runs the current strength block's heavy work
# read level with "the last two", because the only strength blocks still in view were
# the three recent light ones. Over all nine it is half the median. The row count is
# bounded by how many blocks a lifter has trained - 29 after four years - so there is
# nothing to save by truncating and a verdict to lose.
BLOCK_MIN_SESSIONS = 4
TAG_WINDOW_DAYS = 28
TAG_TOP_N = 25
# Two meets, both from 2024, is not a base rate - it is two numbers and a median that
# reads like one. Below this the projection row still ships, carrying `peers` and the
# span the evidence covers, so the card can say why it is declining to name a figure
# instead of naming one nobody should act on.
PROJECTION_MIN_PEERS = 3


def _median(values: list[float]) -> float | None:
    """The middle value, or the mean of the middle two. Not a mean: block measures are
    skewed by a single unusual block and the median is what survives one."""
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def _heavy_reps(sessions: list[dict]) -> int:
    """Main-lift reps at 80% and above across a slice of sessions."""
    heavy = 0
    for s in sessions:
        zones = s.get("prilepin_reps") or {}
        heavy += (zones.get("z80_89") or 0) + (zones.get("z90plus") or 0)
    return heavy


def _block_runs(sessions: list[dict]) -> list[dict]:
    """Maximal runs of consecutive sessions sharing a program.block, oldest first."""
    runs: list[dict] = []
    for s in sorted(sessions, key=lambda d: (d["date"], d.get("session_id") or "")):
        name = (s.get("program") or {}).get("block")
        if runs and runs[-1]["block"] == name:
            runs[-1]["sessions"].append(s)
        else:
            runs.append({"block": name, "sessions": [s]})
    return runs


def _block_rows(docs, today, stamp):
    sessions = [d for index, _id, d in docs if index == "workout-sessions"]
    runs = [r for r in _block_runs(sessions) if r["block"]]
    if not runs:
        return []
    rows: list[tuple[int, str, dict, list[dict]]] = []
    for ordinal, run in enumerate(reversed(runs)):
        members = run["sessions"]
        zones: dict[str, int] = {}
        for s in members:
            for zone, n in (s.get("prilepin_reps") or {}).items():
                zones[zone] = zones.get(zone, 0) + n
        heavy = (zones.get("z80_89") or 0) + (zones.get("z90plus") or 0)
        main_reps = sum(zones.values())
        tonnage = sum((s.get("totals") or {}).get("tonnage_lb") or 0 for s in members)
        rpes = [s["avg_working_rpe"] for s in members if s.get("avg_working_rpe") is not None]
        first, last = members[0]["date"], members[-1]["date"]
        n = len(members)
        rows.append((ordinal, run["block"], {
            "signal": "block",
            "computed_through": stamp,
            "block": run["block"],
            # ordinal 0 is the run in progress. Not a date, because "which block am I in"
            # is answered by position in the log, not by the viewer's clock.
            "ordinal": ordinal,
            "block_role": "current" if ordinal == 0 else "past",
            "first_trained": first,
            "last_trained": last,
            "sessions": n,
            "heavy": heavy,
            "main_reps": main_reps,
            # Rate, not share - see the note above. Rounded to 2dp because one heavy rep
            # in six sessions is 0.17 and the difference from 0.0 is the whole point.
            "heavy_per_session": round(heavy / n, 2),
            "share_pct": round(heavy * 100 / main_reps, 1) if main_reps else None,
            "tonnage_per_session": round(tonnage / n, 1),
            "avg_working_rpe": round(sum(rpes) / len(rpes), 2) if rpes else None,
            # Below this the run is a fragment - two sessions between two blocks - and
            # ranking against it says more about the calendar than the training.
            "rankable": n >= BLOCK_MIN_SESSIONS,
        }, members))

    # The peer comparison, computed here rather than in the card. Liquid cannot sort, so
    # a median taken there would have to be a mean, and the mean of this lifter's eight
    # previous strength blocks is dragged half a rep per session by one 4.06 outlier.
    # Doing it in Python also means it is covered by the same tests as everything else.
    out = []
    for ordinal, name, doc, members in rows:
        # `rankable` was computed on every row and consulted only for the peers. So a
        # block one session in - a fragment by the same definition - still shipped a
        # full peer comparison off a single session, which is exactly the confident
        # verdict on nothing this index exists to prevent. The run in progress has to
        # clear the same bar it holds its peers to before any peer field is attached.
        if ordinal == 0 and doc["rankable"]:
            peers = [(d, m) for o, nm, d, m in rows
                     if o > 0 and nm == name and d["rankable"]]
            doc["peers"] = len(peers)
            if peers:
                # Peers are COMPLETE blocks and the current one is six sessions in, and
                # a strength block is back-loaded - the heavy work is at the end. So the
                # comparison the card was making was 0.83 against a full-block median of
                # 1.75 (47%), when the honest one is against those same blocks through
                # their own first six sessions: 1.58 (53%). peer_window_sessions is that
                # length, so the card can say "through the same six sessions".
                window = len(members)
                doc["peer_window_sessions"] = window
                doc["peer_heavy_per_session"] = _median(
                    [round(_heavy_reps(m[:window]) / min(window, len(m)), 2)
                     for _d, m in peers])
                # The full-block median stays, under its own name. Nothing that already
                # reads a number called peer_heavy_per_session silently changes meaning
                # to mean something else; it changes to the number it should have been.
                doc["peer_heavy_per_session_full"] = _median(
                    [d["heavy_per_session"] for d, _m in peers])
                doc["peer_share_pct"] = _median(
                    [d["share_pct"] for d, _m in peers if d["share_pct"] is not None])
                doc["peer_tonnage_per_session"] = _median(
                    [d["tonnage_per_session"] for d, _m in peers])
                doc["peer_from"] = min(d["first_trained"] for d, _m in peers)
        out.append((SIGNAL_INDEX, f"block:{ordinal}", doc))
    return out


def _tag_rows(docs, today, stamp):
    notes = [d for index, _id, d in docs if index == "workout-notes" and d.get("date")]
    if not notes:
        return []
    days = sorted(d["date"] for d in notes)
    span = (date.fromisoformat(days[-1]) - date.fromisoformat(days[0])).days + 1
    cutoff = (today - timedelta(days=TAG_WINDOW_DAYS)).isoformat()
    prior_cutoff = (today - timedelta(days=2 * TAG_WINDOW_DAYS)).isoformat()

    tags: dict[str, dict] = {}
    for note in notes:
        day = note["date"]
        for tag in note.get("tags") or []:
            t = tags.setdefault(tag, {"total": 0, "recent": 0, "prior": 0,
                                      "first": day, "last": day})
            t["total"] += 1
            if day >= cutoff:
                t["recent"] += 1
            elif day >= prior_cutoff:
                t["prior"] += 1
            t["first"] = min(t["first"], day)
            t["last"] = max(t["last"], day)

    ranked = sorted(tags.items(), key=lambda kv: (-kv[1]["recent"], -kv[1]["total"], kv[0]))
    out = []
    for tag, t in ranked[:TAG_TOP_N]:
        out.append((SIGNAL_INDEX, f"tag:{tag}", {
            "signal": "tag",
            "computed_through": stamp,
            "tag": tag,
            "total": t["total"],
            "recent": t["recent"],
            "prior": t["prior"],
            "first_trained": t["first"],
            "last_trained": t["last"],
            # The corpus, denormalised onto every row: the card's first job is to decide
            # whether it has enough note history to rank anything, and an ES|QL card gets
            # one query. Cheap - 25 rows.
            "window_days": TAG_WINDOW_DAYS,
            "notes_total": len(notes),
            "notes_from": days[0],
            "notes_to": days[-1],
            "notes_span_days": span,
        }))
    return out


def _projection_rows(rollups, today, stamp):
    """What the projected total has been worth on the platform, and what it reads now."""
    weekly = sorted((doc for index, _id, doc in rollups if index == "workout-weekly"),
                    key=lambda d: d["iso_week"])
    out = []
    for cycle in _meet_cycles(today):
        if cycle["upcoming"] or not cycle["meet_total_lb"]:
            continue
        # The projection as it stood in the last week that ended on or before the meet:
        # what the lifter would have been told walking in, not a number computed after.
        prior = [w for w in weekly
                 if w["week_end"] <= cycle["meet_date"] and w.get("projected_total_lb")]
        if not prior:
            continue
        projected = prior[-1]["projected_total_lb"]
        out.append((SIGNAL_INDEX, f"projection:{cycle['cycle']}", {
            "signal": "projection",
            "computed_through": stamp,
            "cycle": cycle["cycle"],
            "cycle_label": cycle["cycle_label"],
            "meet_date": cycle["meet_date"],
            "cycle_role": "past",
            "attempts_made": cycle["attempts_made"],
            "attempts_total": cycle["attempts_total"],
            "projected_total_lb": projected,
            "meet_total_lb": cycle["meet_total_lb"],
            "platformed_pct": round(cycle["meet_total_lb"] * 100 / projected, 1),
        }))
    current = [w for w in weekly if w.get("projected_total_lb")]
    if current:
        pcts = [d["platformed_pct"] for _i, _id, d in out]
        meet_days = sorted(d["meet_date"] for _i, _id, d in out)
        enough = len(pcts) >= PROJECTION_MIN_PEERS
        now = current[-1]["projected_total_lb"]
        out.append((SIGNAL_INDEX, "projection:now", {
            "signal": "projection",
            "computed_through": stamp,
            "cycle": "now",
            "cycle_label": "now",
            "cycle_role": "current",
            "projected_total_lb": now,
            "iso_week": current[-1]["iso_week"],
            "peers": len(pcts),
            "peer_pct": _median(pcts) if enough else None,
            # How old the evidence is. Both keywords, never dates - see the index note.
            "peer_from": meet_days[0] if meet_days else None,
            "peer_to": meet_days[-1] if meet_days else None,
            # What that ratio makes of today's projection. Frozen here so the card does
            # not multiply two numbers and imply a precision neither of them has; the
            # copy rounds it to the nearest five. Withheld, with peer_pct, below
            # PROJECTION_MIN_PEERS.
            "expected_lb": round(now * _median(pcts) / 100, 1) if enough else None,
        }))
    return out


def signal_docs(docs: list[tuple[str, str, dict]],
                rollups: list[tuple[str, str, dict]],
                today: date | None = None) -> list[tuple[str, str, dict]]:
    """Rows for the Overview verdicts, windowed here rather than by a dashboard."""
    # UTC, not the runner's local date: CI runs in UTC and the cards compute their
    # gaps from the viewer's clock. A local date makes computed_through read as
    # tomorrow to a viewer behind the runner, and moves the window edge by a day.
    today = today or datetime.now(timezone.utc).date()
    stamp = today.isoformat()
    out: list[tuple[str, str, dict]] = []

    # ---- drift: one row per muscle group, working sets inside the window
    cutoff = today - timedelta(days=DRIFT_WINDOW_DAYS)
    groups: dict[str, dict] = {}
    for index, _id, doc in docs:
        if index != "workout-sets" or doc.get("set_type") != "working":
            continue
        day = doc.get("date")
        if not day or date.fromisoformat(day) < cutoff:
            continue
        for muscle in doc.get("muscles_primary") or []:
            g = groups.setdefault(muscle, {"sessions": set(), "last": day, "first": day})
            g["sessions"].add(doc.get("session_id"))
            g["last"] = max(g["last"], day)
            g["first"] = min(g["first"], day)
    for muscle, g in sorted(groups.items()):
        n = len(g["sessions"])
        # The span the sessions actually cover, not the window they happen to sit in.
        # DRIFT_WINDOW_DAYS/n divides a 365-day numerator by a denominator that may
        # describe five months: lower back, first trained 2026-04-16, reported a 52-day
        # average gap against an observed ~20, so the card needed 104 days of silence
        # before it would flag a group trained weekly. Clamped at the cutoff so a group
        # with history older than the window is still measured over the window.
        first_trained = date.fromisoformat(g["first"])
        span = (today - max(cutoff, first_trained)).days + 1
        out.append((SIGNAL_INDEX, f"drift:{muscle}", {
            "signal": "drift",
            "computed_through": stamp,
            # Kept so the card can still say "over the last year" - it names the window
            # the sessions were counted in, which is not the span they are divided by.
            "window_days": DRIFT_WINDOW_DAYS,
            "muscle": muscle,
            "sessions": n,
            "last_trained": g["last"],
            "first_trained": g["first"],
            # The group's average gap across its own span. The card flags past twice it.
            "cadence_days": round(span / n, 2) if n and span > 0 else None,
        }))

    # ---- intensity and load: the weekly rollups this same pass just built
    weekly = sorted((doc for index, _id, doc in rollups if index == "workout-weekly"),
                    key=lambda d: d["iso_week"], reverse=True)

    # Which block each week sat in. A week can straddle two, so the last session in it
    # wins - the block the lifter was in when the week ended is the one the week reads as.
    week_block: dict[str, str] = {}
    for _index, _id, doc in sorted(
            (d for d in docs if d[0] == "workout-sessions"),
            key=lambda d: (d[2]["date"], d[2].get("session_id") or "")):
        name = (doc.get("program") or {}).get("block")
        if name:
            week_block[_iso_week(date.fromisoformat(doc["date"]))] = name

    this_week = _iso_week(today)
    ranked_weeks = weekly[:INTENSITY_WEEKS]

    def _main_reps(w: dict) -> int:
        zones = w.get("prilepin_reps") or {}
        return sum(zones.get(k) or 0 for k in ZONE_FIELD.values())

    # Denormalised onto every row, the same trick the tag rows use. An ES|QL card gets
    # one query, so its only other way to know how much history it has is to count the
    # rows it got back - which counts the week in progress, the one week it must not
    # rank, and counts weeks with no main-lift work at all.
    weeks_available = sum(1 for w in ranked_weeks
                          if w["iso_week"] != this_week and _main_reps(w) > 0)

    for week in ranked_weeks:
        zones = week.get("prilepin_reps") or {}
        heavy = (zones.get("z80_89") or 0) + (zones.get("z90plus") or 0)
        total = heavy + (zones.get("lt70") or 0) + (zones.get("z70_79") or 0)
        training_days = week.get("training_days") or 0
        out.append((SIGNAL_INDEX, f"intensity:{week['iso_week']}", {
            "signal": "intensity",
            "computed_through": stamp,
            "iso_week": week["iso_week"],
            "week_end": week["week_end"],
            # heavy and tot are raw counts over however much of the week has happened,
            # so the top row is a Friday ranked against twelve Sundays and the card had
            # nothing on the row to branch on. These do not change what is counted; they
            # say what the count is worth.
            "week_state": "in-progress" if week["iso_week"] == this_week else "closed",
            "training_days": training_days,
            "weeks_available": weeks_available,
            "heavy": heavy,
            "tot": total,
            # The rate, which is the only form in which a part week is comparable at all.
            "heavy_per_training_day": (round(heavy / training_days, 2)
                                       if training_days else None),
        }))

    for week in weekly[:LOAD_WEEKS]:
        end = date.fromisoformat(week["week_end"])
        out.append((SIGNAL_INDEX, f"load:{week['iso_week']}", {
            "signal": "load",
            "computed_through": stamp,
            "iso_week": week["iso_week"],
            "week_end": week["week_end"],
            # Monotony and strain on the week in progress are computed over the days
            # that have elapsed, not a padded seven. Provisional, and says so.
            "week_state": week.get("week_state"),
            # Precomputed here because DATE_FORMAT needs a date field and this index
            # deliberately has none.
            # Not strftime("%b"): that follows the runner's locale, and this string is
            # printed to the lifter ("The last two times you were here: Jul 2026").
            # The ES|QL this replaces used DATE_FORMAT, which is always English.
            "month_s": f"{MONTHS[end.month - 1]} {end.year}",
            "acwr": week.get("acwr"),
            "acwr_band": week.get("acwr_band"),
            "monotony": week.get("monotony"),
            "chronic_days_trained": week.get("chronic_days_trained"),
            "acwr_off_layoff": week.get("acwr_off_layoff"),
            "inol_hardest": week.get("inol_hardest"),
            "inol_hardest_lift": week.get("inol_hardest_lift"),
            "inol_hardest_band": week.get("inol_hardest_band"),
            "inol_hardest_gloss": metrics.inol_week_gloss(week.get("inol_hardest")),
            "acwr_gloss": metrics.acwr_gloss(week.get("acwr")),
            "block": week_block.get(week["iso_week"]),
        }))

    # ---- taper: the run-in to each meet, aligned by weeks out
    out.extend(_taper_rows(docs, weekly, today, stamp))
    # ---- the Program, History, Mindset and Meets-projection verdicts
    out.extend(_block_rows(docs, today, stamp))
    out.extend(_tag_rows(docs, today, stamp))
    out.extend(_projection_rows(rollups, today, stamp))

    return out


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
