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

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from index_workouts import bulk_index  # noqa: E402  (shared bulk + error handling)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "meet.schema.json"
MEETS_DIR = REPO_ROOT / "meets"
KG_TO_LB = 2.20462
LIFTS = ("squat", "bench", "deadlift")
# How each competition lift is named in your workout logs, so a meet's best lift
# can drill into that lift's training history. Override per meet with "lift_names".
DEFAULT_LIFT_NAMES = {
    "squat": "Competition Squat",
    "bench": "Competition Bench Press",
    "deadlift": "Competition Deadlift",
}


def slugify(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def lb(kg: float | None) -> float | None:
    return round(kg * KG_TO_LB, 1) if kg is not None else None


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
    docs = []
    for a in attempts:
        doc = {
            **header,
            "lift": a["lift"],
            "exercise": {"name": lift_names[a["lift"]], "slug": slugify(lift_names[a["lift"]])},
            "attempt_no": a["attempt_no"],
            "weight_kg": a["weight_kg"],
            "weight_lb": lb(a["weight_kg"]),
            "made": a["made"],
            "best": bool(a["made"] and a["weight_kg"] == best_kg[a["lift"]]),
            "notes": a.get("notes") or header["notes"],
        }
        docs.append(("workout-meets", f"{meet_id}-{a['lift']}-{a['attempt_no']}", doc))
    return docs


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    validate_only = "--validate" in sys.argv

    paths = [Path(a) for a in args] or (sorted(MEETS_DIR.glob("*.json")) if MEETS_DIR.exists() else [])
    if not paths:
        print("no meet records found: nothing to do")
        return

    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    all_docs: list[tuple[str, str, dict]] = []
    failed = False
    for path in paths:
        meet = json.loads(path.read_text())
        errors = sorted(validator.iter_errors(meet), key=lambda e: e.json_path)
        if errors:
            failed = True
            print(f"INVALID {path}")
            for error in errors[:10]:
                print(f"  {error.json_path}: {error.message}")
            continue
        docs = explode(meet)
        all_docs.extend(docs)
        print(f"ok {path} -> {len(docs)} attempt(s)")

    if failed:
        sys.exit("error: fix the invalid meet record(s) above")
    if validate_only:
        print("validation passed")
        return
    bulk_index(all_docs)


if __name__ == "__main__":
    main()
