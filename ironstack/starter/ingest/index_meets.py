#!/usr/bin/env python3
"""Validate and index Ironstack meet records into Elasticsearch.

Usage:
    python ingest/index_meets.py [paths...]

With no arguments, indexes every meets/*.json in the repo.
Validation-only mode (no Elasticsearch needed): --validate

One meet file becomes one workout-meets document per attempt, each carrying
the meet-level fields (total, DOTS, bodyweight) so a single index answers
both "best squat ever" and "total per meet". kg is the source of truth;
lb is derived here.

Idempotent: _id is {meet_id}-{lift}-{attempt_no}.

Env:
  ES_ENDPOINT  e.g. https://my-project.es.us-east4.gcp.elastic.cloud:443
  ES_API_KEY   an API key with write access to the workout-* indices
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
# noqa: E402 - shared bulk, error handling and id-collision guard. Mirrored rather than
# reimplemented: index_workouts.py has had both of these since a rename orphaned 429
# documents, and this script wrote to the same cluster with neither.
from index_workouts import (bulk_index, check_unique_ids,  # noqa: E402
                            delete_by_query, refresh_indices)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "meet.schema.json"
MEETS_DIR = REPO_ROOT / "meets"
LIFTS = ("squat", "bench", "deadlift")
# Units an event can be measured in, and which direction is better. This is the whole
# of what makes the model discipline-agnostic: powerlifting and weightlifting are kg
# events end to end, and strongman is a mix - a log press in kg, a yoke in seconds, a
# sandbag in reps, a Conan's wheel in metres. A single "weight_kg" column could not
# hold that, and a total summed across them would be a number no scoring table has
# ever recognised.
LOWER_IS_BETTER = {"seconds"}
UNITS = ("kg", "seconds", "reps", "m")
# How each competition lift is named in your workout logs, so a meet's best lift
# can drill into that lift's training history. Override per meet with "lift_names".
#
# These are resolved through config/exercises.json before they are written, so an
# alias here and the canonical name in your logs end up as the same exercise. That
# resolution is the whole point: until it existed, a meet document carried
# "Competition Squat" while every training set carried "Comp Squat", the Meets ->
# Lift drilldown filtered on a name no set had, and the target dashboard came back
# empty with nothing anywhere reporting a problem.
DEFAULT_LIFT_NAMES = {
    "squat": "Comp Squat",
    "bench": "Comp Bench",
    "deadlift": "Comp Deadlift",
}


def slugify(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def canonical_exercise(name: str) -> dict:
    """The exercise a meet attempt should be filed under, as the logs spell it.

    A meet is the only place a lift's name is typed by configuration rather than by
    the lifter, so it is the one place the two vocabularies can silently diverge.
    Resolving through the taxonomy means "Competition Bench Press" in a meet file and
    "Comp Bench" in a log are one exercise, sharing one slug, and the Meets -> Lift
    drilldown lands on real sets. An unresolvable name is a hard error with the close
    matches attached, exactly as it is for a workout log: a meet that cannot reach its
    training history is a broken meet, not a meet with a cosmetic problem.
    """
    import derive

    try:
        canonical = derive.classify(name)["canonical"]
    except derive.UnknownExercise as exc:
        sys.exit(f"error: meet lift name {name!r} is not in config/exercises.json.\n"
                 f"{exc}\n"
                 "Add it as an alias of the name your logs use, or set \"lift_names\" "
                 "on the meet record.")
    return {"name": canonical, "slug": slugify(canonical)}


def lb(kg: float | None) -> float | None:
    """kg -> lb, through the one conversion constant this repo has.

    There were two: 2.20462 here and 1/0.45359237 in metrics.py, which derive.py uses
    for the same conversion on the same numbers. They agree to five decimal places and
    disagree at one decimal place on a plate load often enough to matter - a meet
    document and the training history it is meant to line up against could print the
    same lift as two different weights. A physical constant does not get two values in
    one codebase; 0.45359237 is the exact definition of the pound.
    """
    import metrics

    return round(kg * metrics.LB_PER_KG, 1) if kg is not None else None


def normalise(meet: dict) -> list[dict]:
    """The meet as a list of events, whichever shape the file was written in.

    A meet used to be three named lifts with three attempts each, and that shape is
    still what most powerlifting files look like, so it is kept and translated rather
    than deprecated: `attempts` becomes three kg events with the same keys, the same
    ids and the same documents it produced before. A file written in 2024 indexes
    byte-identically after this change - which is the test that matters, because the
    alternative is asking every existing user to rewrite their history.

    `key` is what goes in the `lift` column and into the document `_id`. For a legacy
    file it stays "squat"/"bench"/"deadlift" so no id moves; for an events file it is
    the slug of the event name.
    """
    if meet.get("events"):
        out = []
        for event in meet["events"]:
            out.append({
                "key": slugify(event["name"]),
                "name": event["name"],
                "unit": event.get("unit", "kg"),
                "lift_name": event.get("lift_name"),
                "lift_name_claimed": "lift_name" in event,
                "attempts": [{"attempt_no": a["attempt_no"], "value": a["value"],
                              "made": a["made"], "notes": a.get("notes")}
                             for a in event["attempts"]],
                "result": event.get("result"),
                "points": event.get("points"),
                "placing": event.get("placing"),
                "notes": event.get("notes"),
            })
        return out

    lift_names = {**DEFAULT_LIFT_NAMES, **(meet.get("lift_names") or {})}
    by_lift: dict[str, list] = {}
    for a in meet["attempts"]:
        by_lift.setdefault(a["lift"], []).append(a)
    return [{
        "key": lift,
        # The event as the competition called it, not as your logs spell it. Those are
        # different words on purpose: a platform announces the squat, your log calls it
        # Comp Squat, and `lift_name` below is what carries the second one.
        "name": lift.capitalize(),
        "unit": "kg",
        "lift_name": lift_names[lift],
        "lift_name_claimed": True,
        "attempts": [{"attempt_no": a["attempt_no"], "value": a["weight_kg"],
                      "made": a["made"], "notes": a.get("notes")}
                     for a in by_lift[lift]],
        "result": None, "points": None, "placing": None, "notes": None,
    } for lift in LIFTS if lift in by_lift]


def event_result(event: dict) -> float | None:
    """The official result: the best MADE attempt, in the direction the unit runs."""
    made = [a["value"] for a in event["attempts"] if a["made"]]
    if not made:
        return None
    return min(made) if event["unit"] in LOWER_IS_BETTER else max(made)


def event_exercise(event: dict) -> dict:
    """The exercise this event maps to in the training logs, if it maps to one.

    A claimed link is checked and an unclaimed one is not. `lift_name` given and
    unresolvable is a hard error, exactly as a legacy meet's lift name has always
    been: a meet that says it links to a lift and lands on an empty dashboard is worse
    than a meet that says nothing. With no `lift_name`, the event is filed under its
    own name - a medley, a Conan's wheel and a sandbag-over-bar have no training
    analogue, and inventing one so the column is never null would be a lie in a field.
    """
    if event.get("lift_name_claimed") and event.get("lift_name"):
        return canonical_exercise(event["lift_name"])
    import derive
    try:
        canonical = derive.classify(event["name"])["canonical"]
    except derive.UnknownExercise:
        return {"name": event["name"], "slug": slugify(event["name"])}
    return {"name": canonical, "slug": slugify(canonical)}


def explode(meet: dict) -> list[tuple[str, str, dict]]:
    meet_id = meet.get("meet_id") or meet["date"]
    events = normalise(meet)
    scoring = meet.get("scoring", "total")

    for event in events:
        if event.get("result") is None:
            event["result"] = event_result(event)

    # A total is the sum of the kg events and nothing else, and only where the
    # competition was scored on one. Strongman is scored on points per event placing:
    # summing a log press and a yoke run produces a number no scoring table recognises,
    # so `points` scoring gets no total at all rather than a plausible-looking wrong one.
    total_kg = meet.get("total_kg")
    if total_kg is None and scoring == "total":
        weights = [e["result"] for e in events
                   if e["unit"] == "kg" and e["result"] is not None]
        total_kg = sum(weights) if weights else None
    # And a stated one is dropped too, not just an uncomputed one. This is the strict
    # reading on purpose: the Meets page ranks meets by total and by DOTS, and both of
    # those rankings are powerlifting rankings. A strongman show that carries a
    # kilogram total - because the file was copied from a powerlifting one, or because
    # the log press and the deadlift medley were added up by hand - would sort into
    # that ranking as a peer of meets it has nothing in common with. Saying `points`
    # is saying this meet was not scored on weight, and Ironstack takes it at its word.
    if scoring != "total":
        total_kg = None

    header = {
        "@timestamp": meet["date"],
        "meet_id": meet_id,
        "date": meet["date"],
        "name": meet.get("name"),
        "federation": meet.get("federation"),
        "discipline": meet.get("discipline", "powerlifting"),
        "scoring": scoring,
        "total_kg": total_kg,
        "total_lb": lb(total_kg),
        # DOTS scores a summed total against a bodyweight. Without a total it scores
        # nothing, so a points meet carrying one is dropped rather than indexed as a
        # number the Meets page would happily rank.
        "dots": meet.get("dots") if scoring == "total" else None,
        "bodyweight_kg": meet.get("bodyweight_kg"),
        "bodyweight_lb": lb(meet.get("bodyweight_kg")),
        "points": meet.get("points"),
        "placing": meet.get("placing"),
        "attempts_made": sum(1 for e in events for a in e["attempts"] if a["made"]),
        "notes": meet.get("notes"),
    }

    docs = []
    for ordinal, event in enumerate(events, start=1):
        exercise = event_exercise(event)
        for a in event["attempts"]:
            is_kg = event["unit"] == "kg"
            doc = {
                **header,
                "lift": event["key"],
                "event_name": event["name"],
                # Running order, so the Meets list can print a show in the order it was
                # contested. It used to be `CASE(lift == "squat", 1, lift == "bench", 2, 3)`
                # in the query - which is a running order, for exactly one sport.
                "event_no": ordinal,
                "exercise": exercise,
                "lift_slug": exercise["slug"],
                "unit": event["unit"],
                "attempt_no": a["attempt_no"],
                "value": a["value"],
                # weight_kg stays kg-only on purpose: every query that asks for a best
                # lift or a total reads it, and a yoke time in that column would be
                # ranked as a weight.
                "weight_kg": a["value"] if is_kg else None,
                "weight_lb": lb(a["value"]) if is_kg else None,
                "made": a["made"],
                "best": bool(a["made"] and event["result"] is not None
                             and a["value"] == event["result"]),
                "event_result": event["result"],
                "event_points": event.get("points"),
                "event_placing": event.get("placing"),
                "notes": a.get("notes") or event.get("notes") or header["notes"],
            }
            docs.append(("workout-meets", f"{meet_id}-{event['key']}-{a['attempt_no']}", doc))
    return docs


def build_parser() -> argparse.ArgumentParser:
    """Every flag this script has ever taken, declared in one place.

    Same reason as index_workouts.build_parser(): `"--validate" in sys.argv` beside a
    positional filter that drops anything starting with `--` means a misspelled
    `--valdate` is not refused, it is discarded - and the run falls through to
    bulk_index() and writes. The parser rejects what it does not know.
    """
    parser = argparse.ArgumentParser(
        prog="ingest/index_meets.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", type=Path,
                        help="meet records to index (default: every meets/*.json)")
    parser.add_argument("--validate", action="store_true",
                        help="validate and build every document, but write nothing "
                             "and need no Elasticsearch")
    return parser


def main(argv: list | None = None) -> None:
    opts = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    validate_only = opts.validate

    paths = list(opts.paths) or (sorted(MEETS_DIR.glob("*.json")) if MEETS_DIR.exists() else [])
    if not paths:
        print("no meet records found: nothing to do")
        return

    # format_checker, or `format` is an annotation and nothing else. Draft 2020-12 says
    # format is informational unless a checker is supplied, so every "format": "date" in
    # the schema was decoration: "date": "banana" validated clean, and then died in
    # session_links() as `ValueError: month must be in 1..12` - five lines of Python,
    # no filename, and nothing to say which of 643 logs to open.
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()),
                                     format_checker=Draft202012Validator.FORMAT_CHECKER)
    all_docs: list[tuple[str, str, dict]] = []
    failed = False
    # meet_id -> the file it came from. Every _id this script writes starts with the
    # meet_id, so two files sharing one produce two full sets of identical ids and the
    # second meet silently replaces the first, attempt for attempt, in a bulk call that
    # reports success. catalog_logs() has guarded exactly this for workout logs; meets
    # had nothing, and a meet is the easiest file in the repo to copy as a starting point
    # for the next one.
    seen: dict[str, Path] = {}
    for path in paths:
        meet = json.loads(path.read_text())
        errors = sorted(validator.iter_errors(meet), key=lambda e: e.json_path)
        if errors:
            failed = True
            print(f"INVALID {path}")
            for error in errors[:10]:
                print(f"  {error.json_path}: {error.message}")
            continue
        meet_id = meet.get("meet_id") or meet["date"]
        if meet_id in seen:
            failed = True
            print(f"INVALID {path}")
            print(f"  meet_id {meet_id!r} is already used by {seen[meet_id]} - one of the "
                  f"two would silently overwrite the other")
            continue
        seen[meet_id] = path
        docs = explode(meet)
        all_docs.extend(docs)
        print(f"ok {path} -> {len(docs)} attempt(s)")

    if failed:
        sys.exit("error: fix the invalid meet record(s) above")
    # And the belt to that braces: an id collision from anywhere else - two attempts
    # sharing a lift and attempt_no inside one file - is just as invisible in a bulk call.
    check_unique_ids(all_docs)
    if validate_only:
        print("validation passed")
        return
    bulk_index(all_docs)
    if not opts.paths:
        # A deleted or renamed meet file orphans its attempt documents exactly the way a
        # deleted workout log orphans its sets: the bulk write replaces by id and has no
        # opinion about ids it was not given, so the old attempts stay - in the totals, in
        # the DOTS series, and in the Meets card's "best ever". A run over the whole meets/
        # folder knows every attempt that should exist, so anything else is stale. A run
        # given explicit paths does not, and sweeps nothing.
        refresh_indices(("workout-meets",), "the stale-meet sweep")
        body = delete_by_query(
            "workout-meets",
            {"bool": {"must_not": [{"ids": {"values": [i for _ix, i, _d in all_docs]}}]}},
            "stale workout-meets documents",
            "attempts from deleted meet records may still be in workout-meets.",
        )
        print(f"workout-meets -> swept {body.get('deleted', 0)} of "
              f"{body.get('total', 0)} matched stale document(s)")


if __name__ == "__main__":
    main()
