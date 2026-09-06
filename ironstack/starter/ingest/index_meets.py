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


def explode(meet: dict) -> list[tuple[str, str, dict]]:
    meet_id = meet.get("meet_id") or meet["date"]
    attempts = meet["attempts"]

    best_kg = {lift: 0.0 for lift in LIFTS}
    for a in attempts:
        if a["made"] and a["weight_kg"] > best_kg[a["lift"]]:
            best_kg[a["lift"]] = a["weight_kg"]
    total_kg = meet.get("total_kg")
    if total_kg is None:
        total_kg = sum(best_kg.values())

    header = {
        "@timestamp": meet["date"],
        "meet_id": meet_id,
        "date": meet["date"],
        "name": meet.get("name"),
        "federation": meet.get("federation"),
        "total_kg": total_kg,
        "total_lb": lb(total_kg),
        "dots": meet.get("dots"),
        "bodyweight_kg": meet.get("bodyweight_kg"),
        "bodyweight_lb": lb(meet.get("bodyweight_kg")),
        "attempts_made": sum(1 for a in attempts if a["made"]),
        "notes": meet.get("notes"),
    }

    lift_names = {**DEFAULT_LIFT_NAMES, **(meet.get("lift_names") or {})}
    exercises = {lift: canonical_exercise(name) for lift, name in lift_names.items()}
    docs = []
    for a in attempts:
        doc = {
            **header,
            "lift": a["lift"],
            "exercise": exercises[a["lift"]],
            "lift_slug": exercises[a["lift"]]["slug"],
            "attempt_no": a["attempt_no"],
            "weight_kg": a["weight_kg"],
            "weight_lb": lb(a["weight_kg"]),
            "made": a["made"],
            "best": bool(a["made"] and a["weight_kg"] == best_kg[a["lift"]]),
            "notes": a.get("notes") or header["notes"],
        }
        docs.append(("workout-meets", f"{meet_id}-{a['lift']}-{a['attempt_no']}", doc))
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
