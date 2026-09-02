#!/usr/bin/env python3
"""Validate and index Ironstack workout logs into Elasticsearch.

Usage:
    python ingest/index_workouts.py [paths...]

With no arguments, indexes every workouts/**/*.json in the repo.
Validation-only mode (no Elasticsearch needed): --validate

Idempotent: every document gets a deterministic _id derived from the
session, exercise, and set, so re-running after an edit updates in place.

Env:
  ES_ENDPOINT  e.g. https://my-project.es.us-east4.gcp.elastic.cloud:443
  ES_API_KEY   an API key with write access to the workout-* indices
"""

import json
import os
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "workout.schema.json"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def est_e1rm(weight: float, reps: float, rpe: float | None) -> float | None:
    """Estimated 1RM via Epley, extended with RPE (reps in reserve count as reps)."""
    if not weight or not reps or rpe is None:
        return None
    effective_reps = reps + (10 - rpe)
    if effective_reps <= 1:
        return round(weight, 1)
    return round(weight * (1 + effective_reps / 30.0), 1)


def load_schema() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def explode(log: dict) -> list[tuple[str, str, dict]]:
    """Turn one workout log into (index, _id, document) tuples."""
    session = log["session"]
    session_id = session.get("session_id") or session["date"]
    context = {
        "session_id": session_id,
        "date": session["date"],
        "time_of_day": session.get("time_of_day"),
        "location": {
            "name": (session.get("location") or {}).get("name"),
            "travel": (session.get("location") or {}).get("travel", False),
        },
    }
    program = session.get("program") or {}
    docs: list[tuple[str, str, dict]] = []

    tonnage = 0.0
    total_sets = working_sets = total_reps = 0
    working_rpes: list[float] = []

    for exercise in log["exercises"]:
        slug = slugify(exercise["name"])
        for position, s in enumerate(exercise["sets"], start=1):
            set_number = s.get("set_number", position)
            set_type = s.get("set_type", "working")
            weight = s.get("weight_lb", 0)
            reps = s["reps"]
            rep_unit = s.get("rep_unit", "reps")
            rpe = s.get("rpe")
            volume = round(weight * reps, 1) if rep_unit == "reps" else None

            total_sets += 1
            if rep_unit == "reps":
                total_reps += int(reps)
            if volume:
                tonnage += volume
            if set_type == "working":
                working_sets += 1
                if rpe is not None:
                    working_rpes.append(rpe)

            doc = {
                **context,
                "program": program,
                "exercise": {
                    "name": exercise["name"],
                    "slug": slug,
                    "category": exercise["category"],
                    "equipment": exercise.get("equipment"),
                    "emphasis": exercise.get("emphasis"),
                },
                "set_number": set_number,
                "set_type": set_type,
                "weight_lb": weight,
                "reps": reps,
                "rep_unit": rep_unit,
                "distance_ft": s.get("distance_ft"),
                "load_type": s.get("load_type", "external"),
                "rpe": rpe,
                "volume_lb": volume,
                "est_e1rm": est_e1rm(weight, reps, rpe)
                if exercise["category"] == "main" and set_type == "working" and rep_unit == "reps"
                else None,
                "gear": s.get("gear", exercise.get("gear", [])),
                "notes": s.get("notes"),
                "tags": s.get("tags", []),
            }
            docs.append(("workout-sets", f"{session_id}-{slug}-{set_type}-{set_number}", doc))

    for order, note in enumerate(log.get("notes", []), start=1):
        doc = {
            **context,
            "program": {"day": program.get("day"), "total_days": program.get("total_days")},
            "phase": note["phase"],
            "exercise": note.get("exercise"),
            "set_number": note.get("set_number"),
            "order": order,
            "text": note["text"],
            "tags": note.get("tags", []),
        }
        docs.append(("workout-notes", f"{session_id}-note-{order}", doc))

    session_doc = {
        **context,
        "start_time": session.get("start_time"),
        "duration_min": session.get("duration_min"),
        "environment": session.get("environment"),
        "program": program,
        "totals": {
            "tonnage_lb": round(tonnage, 1),
            "sets": total_sets,
            "working_sets": working_sets,
            "reps": total_reps,
            "exercises": len(log["exercises"]),
        },
        "avg_working_rpe": round(sum(working_rpes) / len(working_rpes), 2) if working_rpes else None,
        "gear_notes": session.get("gear_notes"),
        "wrap_up": session.get("wrap_up"),
        "watch_items": session.get("watch_items", []),
    }
    geo = (session.get("location") or {}).get("geo")
    if geo:
        session_doc["location"] = {**session_doc["location"], "geo": geo}
    docs.append(("workout-sessions", session_id, session_doc))
    return docs


def strip_nones(value):
    if isinstance(value, dict):
        return {k: strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_nones(v) for v in value]
    return value


def bulk_index(docs: list[tuple[str, str, dict]]) -> None:
    import requests

    endpoint = os.environ.get("ES_ENDPOINT", "").strip().rstrip("/")
    api_key = os.environ.get("ES_API_KEY", "").strip()
    if not endpoint or not api_key:
        sys.exit("error: ES_ENDPOINT and ES_API_KEY must be set (or use --validate)")

    lines = []
    for index, _id, doc in docs:
        lines.append(json.dumps({"index": {"_index": index, "_id": _id}}))
        lines.append(json.dumps(strip_nones(doc)))
    payload = "\n".join(lines) + "\n"

    resp = requests.post(
        f"{endpoint}/_bulk",
        data=payload.encode("utf-8"),
        headers={
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/x-ndjson",
        },
        timeout=60,
    )
    if not resp.ok:
        sys.exit(f"error: bulk request failed -> {resp.status_code} {resp.text[:500]}")
    body = resp.json()
    if body.get("errors"):
        failures = [
            item["index"]
            for item in body["items"]
            if item.get("index", {}).get("status", 200) >= 300
        ]
        sys.exit(f"error: {len(failures)} document(s) failed:\n{json.dumps(failures[:5], indent=2)}")
    print(f"indexed {len(docs)} document(s)")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    validate_only = "--validate" in sys.argv

    paths = [Path(a) for a in args] or sorted((REPO_ROOT / "workouts").rglob("*.json"))
    if not paths:
        print("no workout logs found — nothing to do")
        return

    validator = load_schema()
    all_docs: list[tuple[str, str, dict]] = []
    failed = False
    for path in paths:
        log = json.loads(path.read_text())
        errors = sorted(validator.iter_errors(log), key=lambda e: e.json_path)
        if errors:
            failed = True
            print(f"INVALID {path}")
            for error in errors[:10]:
                print(f"  {error.json_path}: {error.message}")
            continue
        docs = explode(log)
        all_docs.extend(docs)
        print(f"ok {path} -> {len(docs)} document(s)")

    if failed:
        sys.exit("error: fix the invalid log(s) above")
    if validate_only:
        print("validation passed")
        return
    bulk_index(all_docs)


if __name__ == "__main__":
    main()
