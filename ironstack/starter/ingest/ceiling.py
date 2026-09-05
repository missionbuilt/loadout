#!/usr/bin/env python3
"""The heaviest load either suggesting surface may name for one lift.

Usage:
    python ingest/ceiling.py "Comp Bench"
    python ingest/ceiling.py "Lat Pulldowns" --as-of 2026-06-01 --window 60
    python ingest/ceiling.py "Comp Squat" --json

The rule is written once, in the public spec (`ironstack/CEILING.md`), because two
surfaces suggest loads and a lifter must not get two answers. This script is the
half of it that runs with no cluster: `est_e1rm` is computed at index time and
appears in no file under `workouts/`, so a skill that has only the repo had no way
to check the ceiling it was told to respect. It has one now.

Nothing here is a new formula. `metrics.e1rm()` makes the estimate,
`derive.best_working_e1rm()` decides which estimate in a session counts, and
`index_workouts.catalog_logs()` reads the corpus - the same three the indexer uses,
so the number printed here and the number written to Elasticsearch cannot disagree.

What it will not do is invent a number. Above 12 reps there is no estimate at all;
at 10-12 reps there is one and it does not set a bar. When nothing qualifies the
answer is the heaviest weight actually moved, and when there is not even that the
answer is that there is no answer (exit 4) rather than a plausible-looking guess.

Exit codes: 0 printed, 1 usage, 4 no qualifying sets, 5 unknown exercise.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import derive
import metrics

BASIS_ESTIMATE = "est_e1rm"
BASIS_HEAVIEST = "heaviest working set"
NOTHING = "no qualifying sets — nothing to ceiling from"


# ------------------------------------------------------------------ formatting

def _num(value) -> str:
    """185.0 -> "185", 8.5 -> "8.5". A rep count is not a decimal."""
    if value is None:
        return "?"
    number = float(value)
    return str(int(number)) if number == int(number) else str(number)


def set_repr(s: dict) -> str:
    """One set as it would be said out loud: "185 x 5 @ 8"."""
    text = f"{_num(s.get('weight_lb'))} x {_num(s.get('reps'))}"
    if s.get("rpe") is not None:
        text += f" @ {_num(s['rpe'])}"
    return text


# ----------------------------------------------------------------- corpus walk

def _qualifies(s: dict) -> dict | None:
    """The estimate for a set, or None if it does not deserve one.

    Exactly `derive.best_working_e1rm()`'s test, applied to a single set so the
    provenance and the counts can name the individual set the session best came
    from. The session best itself still comes from derive - see `compute()`.
    """
    estimate = metrics.e1rm(s.get("weight_lb", 0), s["reps"], s.get("rpe"))
    if estimate and estimate["confidence"] != metrics.CONF_LOW:
        return estimate
    return None


def working_sets(logs: list[tuple[str, str, dict]], slug: str,
                 as_of: date) -> list[tuple[date, str, dict]]:
    """(day, session_id, set) for every working rep-set of `slug` on or before as_of.

    `set_type == "working"` and `rep_unit == "reps"` are the same two filters
    `derive.best_working_e1rm()` applies, and for the same reason: a warm-up single
    says nothing about a ceiling, and a timed hold has no reps to estimate from.
    """
    out = []
    for day_str, session_id, log in logs:
        day = date.fromisoformat(day_str)
        if day > as_of:
            continue
        for exercise in log.get("exercises", []):
            if derive.lift_slug(exercise["name"]) != slug:
                continue
            for s in exercise.get("sets", []):
                if s.get("set_type", "working") != "working":
                    continue
                if s.get("rep_unit", "reps") != "reps":
                    continue
                out.append((day, session_id, s))
    return sorted(out, key=lambda row: (row[0], row[1]))


def session_bests(logs: list[tuple[str, str, dict]], slug: str,
                  as_of: date) -> list[tuple[date, str, float]]:
    """(day, session_id, best e1RM) per session, straight from derive.

    The ceiling is chosen from these rather than from a maximum this file computes
    itself. That is the whole point: the number the coach is held to is the number
    the indexer wrote, by construction rather than by agreement.
    """
    out = []
    for day_str, session_id, log in logs:
        day = date.fromisoformat(day_str)
        if day > as_of:
            continue
        value = derive.best_working_e1rm(log).get(slug)
        if value:
            out.append((day, session_id, value))
    return sorted(out, key=lambda row: (row[0], row[1]))


def _attribute(rows: list[tuple[date, str, dict]], session_id: str,
               value: float) -> dict | None:
    """The set inside one session that the session best came from."""
    best = None
    for _day, sid, s in rows:
        if sid != session_id:
            continue
        estimate = _qualifies(s)
        if estimate and abs(estimate["value"] - value) < 1e-9:
            return {"set": s, "estimate": estimate}
        if estimate and (best is None or estimate["value"] > best["estimate"]["value"]):
            best = {"set": s, "estimate": estimate}
    return best


# --------------------------------------------------------------- the rule

EMPTY = {
    "ceiling_lb": None, "basis": None, "method": None, "confidence": None,
    "from_date": None, "from_session_id": None, "from_set": None,
    "window_ref": None, "stale_days": None,
    "heaviest_set_lb": None, "heaviest_set_date": None,
    "qualifying_sets": 0, "sessions": 0,
}


def compute(logs: list[tuple[str, str, dict]], name: str, slug: str,
            as_of: date, window_days: int) -> dict:
    """The ceiling for one lift as it stood on `as_of`, and where it came from.

    Rules 1-4 of CEILING.md in order: the best qualifying estimate in the trailing
    window; failing that the best at any time, marked stale; failing that the
    heaviest weight actually moved; failing that, nothing.
    """
    rows = working_sets(logs, slug, as_of)
    payload = {"lift": name, "slug": slug,
               "window_days": window_days, "as_of": as_of.isoformat(), **EMPTY}

    loaded = [row for row in rows if (row[2].get("weight_lb") or 0) > 0]
    if loaded:
        day, _sid, heaviest = max(loaded, key=lambda row: (row[2]["weight_lb"], row[0]))
        payload["heaviest_set_lb"] = round(float(heaviest["weight_lb"]), 1)
        payload["heaviest_set_date"] = day.isoformat()
        payload["heaviest_set"] = set_repr(heaviest)

    bests = session_bests(logs, slug, as_of)
    cutoff = as_of - timedelta(days=window_days)
    recent = [row for row in bests if row[0] >= cutoff]

    pool: list[tuple[date, str, dict]]
    if recent or bests:
        # Rule 1, then rule 2. The window is derive's own: the same days every
        # set's intensity_pct is measured against, falling back the same way.
        chosen = recent or bests
        payload["window_ref"] = "recent" if recent else "all-time"
        day, session_id, value = max(chosen, key=lambda row: (row[2], row[0]))
        found = _attribute(rows, session_id, value)
        payload.update(
            ceiling_lb=round(value, 1),
            basis=BASIS_ESTIMATE,
            from_date=day.isoformat(),
            from_session_id=session_id,
        )
        if found:
            payload["from_set"] = set_repr(found["set"])
            payload["method"] = found["estimate"]["method"]
            payload["confidence"] = found["estimate"]["confidence"]
        if not recent:
            payload["stale_days"] = (as_of - day).days
        horizon = cutoff if recent else date.min
        pool = [row for row in rows if row[0] >= horizon and _qualifies(row[2])]
    elif loaded:
        # Rule 3. No estimate anywhere, so the only honest number left is a weight
        # that was actually on the bar. It carries no method and no confidence
        # because it is not an estimate of anything.
        day, session_id, s = max(loaded, key=lambda row: (row[2]["weight_lb"], row[0]))
        payload.update(
            ceiling_lb=round(float(s["weight_lb"]), 1),
            basis=BASIS_HEAVIEST,
            from_date=day.isoformat(),
            from_session_id=session_id,
            from_set=set_repr(s),
            window_ref="all-time",
        )
        pool = loaded
    else:
        # Rule 4. Bodyweight-only movements land here, and so does a lift logged
        # once for time. There is nothing to suggest from and saying so is the
        # answer.
        return payload

    payload["qualifying_sets"] = len(pool)
    payload["sessions"] = len({sid for _d, sid, _s in pool})
    return payload


# ---------------------------------------------------------------- presentation

LABEL = 15
VALUE = 11
BASIS = 24


def render(payload: dict) -> str:
    """The block a skill reads out loud.

    Every line answers "and where did that come from". A ceiling with no date and
    no set behind it is a number the lifter cannot argue with, which is the one
    thing a guardrail must never be.
    """
    if payload["ceiling_lb"] is None:
        return NOTHING

    def row(label, pounds, basis, day, set_text):
        weight = "" if pounds is None else f"{pounds:.1f} lb"
        return (f"  {label:<{LABEL}}{weight:<{VALUE}}{basis:<{BASIS}}"
                f"{day}  {set_text}").rstrip()

    basis = payload["basis"]
    if payload["method"]:
        basis = f"{basis}  {payload['method']}/{payload['confidence']}"

    lines = [f"{payload['lift']}  ->  {payload['slug']}"]
    lines.append(row("ceiling", payload["ceiling_lb"], basis,
                     payload["from_date"], payload["from_set"] or ""))

    window = f"  {'window':<{LABEL}}{payload['window_days']} days ending {payload['as_of']}"
    if payload["stale_days"] is None:
        window += f"  ({payload['window_ref']})"
    else:
        # Rule 2 out loud. Silently reaching back years for a number and printing it
        # beside a 90-day window would be the most misleading thing this could do.
        window += (f"  ({payload['window_ref']} — stale, nothing qualifying in the "
                   f"window; this one is {payload['stale_days']} days old)")
    lines.append(window)

    if payload["heaviest_set_lb"] is not None:
        # The gap between an estimate and a lift, without a second command. When the
        # ceiling sits above this line, the ceiling has never actually been moved.
        lines.append(row("heaviest set", payload["heaviest_set_lb"], "",
                         payload["heaviest_set_date"], payload.get("heaviest_set", "")))

    lines.append(f"  {'qualifying':<{LABEL}}{payload['qualifying_sets']} working sets "
                 f"across {payload['sessions']} sessions")
    return "\n".join(lines)


JSON_KEYS = ("lift", "slug", "ceiling_lb", "basis", "method", "confidence",
             "from_date", "from_session_id", "from_set", "window_days",
             "window_ref", "heaviest_set_lb", "heaviest_set_date",
             "qualifying_sets", "sessions")


def as_json(payload: dict) -> str:
    """The same facts, for a caller that would rather parse than read."""
    return json.dumps({key: payload[key] for key in JSON_KEYS}, indent=2)


# ------------------------------------------------------------------------ main

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ceiling.py",
        description="The heaviest load that may be suggested for one lift.",
        add_help=True,
    )
    parser.add_argument("lift", nargs="?",
                        help="exercise name, or any alias in config/exercises.json")
    parser.add_argument("--as-of", default=None, metavar="YYYY-MM-DD",
                        help="compute the ceiling as it stood on that date (default today)")
    parser.add_argument("--window", type=int, default=derive.REFERENCE_WINDOW_DAYS,
                        metavar="N",
                        help=f"trailing window in days (default {derive.REFERENCE_WINDOW_DAYS})")
    parser.add_argument("--json", action="store_true",
                        help="emit one JSON object instead of the text block")
    return parser


def main(argv: list) -> int:
    opts = build_parser().parse_args(argv)

    if not opts.lift:
        print(__doc__)
        return 1
    try:
        as_of = date.fromisoformat(opts.as_of) if opts.as_of else date.today()
    except ValueError:
        print(f"--as-of: {opts.as_of!r} is not a YYYY-MM-DD date", file=sys.stderr)
        return 1
    if opts.window < 1:
        print(f"--window: {opts.window} is not a number of days", file=sys.stderr)
        return 1

    # The same failure log.py gives on the same typo, from the same suggester, so a
    # misremembered name fails once and identically wherever it is typed.
    try:
        name = derive.classify(opts.lift)["canonical"]
        slug = derive.lift_slug(opts.lift)
    except derive.UnknownExercise as exc:
        print(exc, file=sys.stderr)
        return 5

    import index_workouts

    try:
        logs = index_workouts.catalog_logs()
        payload = compute(logs, name, slug, as_of, opts.window)
    except derive.UnknownExercise as exc:
        # Not the caller's typo - a log in the corpus names something the taxonomy
        # does not have. Saying so beats reporting it against the lift they asked for.
        print(f"the corpus itself has an unknown exercise, so the history behind this "
              f"ceiling is incomplete:\n{exc}", file=sys.stderr)
        return 1

    print(as_json(payload) if opts.json else render(payload))
    return 0 if payload["ceiling_lb"] is not None else 4


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
