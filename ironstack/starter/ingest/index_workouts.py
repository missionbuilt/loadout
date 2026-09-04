#!/usr/bin/env python3
"""Validate and index Ironstack workout logs into Elasticsearch.

Usage:
    python ingest/index_workouts.py [paths...]

With no arguments, indexes every workouts/**/*.json in the repo.
Validation-only mode (no Elasticsearch needed): --validate

Idempotent: every document gets a deterministic _id derived from the
session, exercise, and set, so re-running after an edit updates in place.

Session links (prev_session_id / next_session_id / streak_day) are computed
from every log under workouts/, not hand-written, so they stay correct even
when only one file is passed on the command line.

Env:
  ES_ENDPOINT  e.g. https://my-project.es.us-east4.gcp.elastic.cloud:443
  ES_API_KEY   an API key with write access to the workout-* indices
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

import derive

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "workout.schema.json"
WORKOUTS_DIR = REPO_ROOT / "workouts"

PROGRAM_FIELDS = ("name", "block", "phase", "week", "day", "total_days", "meet_date")


def _fmt_number(value) -> str:
    if value is None:
        return "0"
    return str(int(value)) if float(value) == int(value) else str(value)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# est_e1rm moved to metrics.e1rm(), which uses Tuchscherer's RPE table rather than
# Epley with reps-in-reserve folded into the rep count, reports which model it used,
# and carries a confidence tier. derive.set_fields() writes it onto every working set
# — not only the main lifts, as the old version did.


def load_schema() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def session_key(session: dict) -> str:
    return session.get("session_id") or session["date"]


def timestamp_for(session: dict) -> str:
    """ISO instant for the session start. Falls back to the date at midnight local."""
    day = session["date"]
    start = session.get("start_time") or "00:00"
    tz_name = session.get("timezone")
    naive = datetime.fromisoformat(f"{day}T{start}:00")
    if tz_name:
        try:
            from zoneinfo import ZoneInfo

            return naive.replace(tzinfo=ZoneInfo(tz_name)).isoformat()
        except Exception:  # unknown zone: index as a naive local time
            pass
    return naive.isoformat()


def weekday_for(day: str) -> str:
    """'1 Mon' .. '7 Sun': sorts chronologically as a keyword, reads as a label."""
    d = date.fromisoformat(day)
    return f"{d.isoweekday()} {d.strftime('%a')}"


def days_to_meet(session: dict) -> int | None:
    """Days from this session to program.meet_date, as of the session date."""
    meet = (session.get("program") or {}).get("meet_date")
    if not meet:
        return None
    return (date.fromisoformat(meet) - date.fromisoformat(session["date"])).days


def program_block(program: dict) -> dict:
    """The denormalized program context carried by every document."""
    return {k: program[k] for k in PROGRAM_FIELDS if program.get(k) is not None}


# --------------------------------------------------------------------------- links


def catalog_sessions(extra_paths: list[Path]) -> list[tuple[str, str]]:
    """All (date, session_id) pairs the repo knows about, sorted chronologically."""
    seen: dict[str, str] = {}
    paths = list(WORKOUTS_DIR.rglob("*.json")) if WORKOUTS_DIR.exists() else []
    paths += extra_paths
    for path in paths:
        try:
            session = json.loads(path.read_text()).get("session") or {}
            if "date" in session:
                seen[session_key(session)] = session["date"]
        except (OSError, ValueError):
            continue
    return sorted(((d, sid) for sid, d in seen.items()), key=lambda pair: (pair[0], pair[1]))


def catalog_logs(extra_paths: list[Path]) -> list[tuple[str, str, dict]]:
    """(date, session_id, log) for every session the repo knows about.

    The analytics reference (best e1RM per lift as of each date) has to see the
    whole history, not just the files named on the command line.
    """
    seen: dict[str, tuple[str, dict]] = {}
    paths = list(WORKOUTS_DIR.rglob("*.json")) if WORKOUTS_DIR.exists() else []
    paths += extra_paths
    for path in paths:
        try:
            log = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        session = log.get("session") or {}
        if "date" in session:
            seen[session_key(session)] = (session["date"], log)
    return [(day, sid, log) for sid, (day, log) in seen.items()]


def session_links(ordered: list[tuple[str, str]]) -> dict[str, dict]:
    """prev/next ids and streak_day (consecutive calendar days trained) per session."""
    links: dict[str, dict] = {}
    prev_day: date | None = None
    streak = 0
    for i, (day_str, sid) in enumerate(ordered):
        day = date.fromisoformat(day_str)
        if prev_day is None or day - prev_day > timedelta(days=1):
            streak = 1
        elif day - prev_day == timedelta(days=1):
            streak += 1
        # same day: streak unchanged
        prev_day = day
        links[sid] = {
            "prev_session_id": ordered[i - 1][1] if i > 0 else None,
            "next_session_id": ordered[i + 1][1] if i + 1 < len(ordered) else None,
            "streak_day": streak,
        }
    return links


# --------------------------------------------------------------------------- explode


def explode(log: dict, links: dict[str, dict] | None = None,
            reference: derive.Reference | None = None) -> list[tuple[str, str, dict]]:
    """Turn one workout log into (index, _id, document) tuples."""
    session = log["session"]
    session_id = session_key(session)
    program = program_block(session.get("program") or {})
    context = {
        "@timestamp": timestamp_for(session),
        "session_id": session_id,
        "date": session["date"],
        "weekday": weekday_for(session["date"]),
        "time_of_day": session.get("time_of_day"),
        "location": {
            "name": (session.get("location") or {}).get("name"),
            "travel": (session.get("location") or {}).get("travel", False),
        },
        "program": program,
    }
    docs: list[tuple[str, str, dict]] = []
    set_docs: list[dict] = []

    tonnage = 0.0
    total_sets = working_sets = total_reps = 0
    working_rpes: list[float] = []
    seq = 0  # order of every set within the session, across exercises

    for exercise in log["exercises"]:
        slug = slugify(exercise["name"])
        for position, s in enumerate(exercise["sets"], start=1):
            seq += 1
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
                "exercise": {
                    "name": exercise["name"],
                    "slug": slug,
                    "category": exercise["category"],
                    "equipment": exercise.get("equipment"),
                    "equipment_ids": [i["id"] for i in exercise.get("equipment_items", [])],
                    "equipment_names": [i["name"] for i in exercise.get("equipment_items", [])],
                    "equipment_kinds": sorted({i["kind"] for i in exercise.get("equipment_items", [])
                                               if i.get("kind")}),
                    "bar_weight_lb": next((i["weight_lb"] for i in exercise.get("equipment_items", [])
                                           if i.get("kind") == "barbell" and i.get("weight_lb")), None),
                    "emphasis": exercise.get("emphasis"),
                },
                "seq": seq,
                "set_number": set_number,
                "set_type": set_type,
                "weight_lb": weight,
                "weight_each_lb": s.get("weight_each_lb"),
                "each_side": s.get("each_side", False),
                "scheme": s.get("scheme"),
                "cardio": s.get("cardio"),
                "reps": reps,
                "rep_unit": rep_unit,
                "distance_ft": s.get("distance_ft"),
                "load_type": s.get("load_type", "external"),
                "rpe": rpe,
                "volume_lb": volume,
                "gear": s.get("gear", exercise.get("gear", [])),
                "notes": s.get("notes"),
                "tags": s.get("tags", []),
            }
            doc.update(derive.set_fields(exercise, s, session_id, slug, reference))
            set_docs.append(doc)
            docs.append(("workout-sets", f"{session_id}-{slug}-{set_type}-{set_number}", doc))

    for order, note in enumerate(log.get("notes", []), start=1):
        doc = {
            **context,
            "phase": note["phase"],
            "exercise": {"name": note["exercise"], "slug": slugify(note["exercise"])} if note.get("exercise") else None,
            "set_number": note.get("set_number"),
            "order": order,
            "text": note["text"],
            "tags": note.get("tags", []),
        }
        docs.append(("workout-notes", f"{session_id}-note-{order}", doc))

    for order, item in enumerate(session.get("watch_items", []) or [], start=1):
        # A watch item is a note the lifter wrote about the future; it deserves to be
        # findable the same way ("when was my grip last a problem?").
        docs.append(("workout-notes", f"{session_id}-watch-{order}", {
            **context,
            "phase": "watch",
            "exercise": None,
            "set_number": None,
            "order": 1000 + order,
            "text": item,
            "tags": ["watch"],
        }))

    top_sets = []
    for exercise in log["exercises"]:
        if exercise["category"] != "main":
            continue
        working = [s for s in exercise["sets"] if s.get("set_type", "working") == "working"]
        if not working:
            continue
        best = max(working, key=lambda s: (s.get("weight_lb") or 0, s["reps"]))
        label = f"{exercise['name']} {_fmt_number(best.get('weight_lb'))} lb x{_fmt_number(best['reps'])}"
        if best.get("rpe") is not None:
            label += f" at RPE {_fmt_number(best['rpe'])}"
        top_sets.append(label)

    session_doc = {
        **context,
        "source": session.get("source"),
        "start_time": session.get("start_time"),
        "timestamp": timestamp_for(session),
        "duration_min": session.get("duration_min"),
        "days_to_meet": days_to_meet(session),
        "environment": session.get("environment"),
        "metrics": session.get("metrics"),
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
        **((links or {}).get(session_id) or {}),
    }
    session_doc.update(derive.session_fields(set_docs, session, session_doc["totals"],
                                             session_doc["avg_working_rpe"]))
    session_doc["digest"] = session_digest(log, session_doc["totals"],
                                           session_doc["avg_working_rpe"], top_sets)
    geo = (session.get("location") or {}).get("geo")
    if geo:
        session_doc["location"] = {**session_doc["location"], "geo": geo}
    docs.append(("workout-sessions", session_id, session_doc))
    return docs


def session_digest(log: dict, totals: dict, avg_rpe, top_sets: list) -> str:
    """One paragraph that says what the session was, for semantic search to embed.

    Composed here rather than written by hand: the log stays terse, and the
    AI-facing view is rebuilt from it on every index run.
    """
    session = log["session"]
    day = date.fromisoformat(session["date"])
    parts = [day.strftime("%A, %B %-d, %Y")]
    if session.get("time_of_day"):
        parts.append(session["time_of_day"])

    location = session.get("location") or {}
    where = location.get("name")
    if where:
        parts.append(f"traveling in {where}" if location.get("travel") else where)
    env = session.get("environment") or {}
    weather = [f"{env['temp_f']:.0f}F" if env.get("temp_f") is not None else "",
               env.get("conditions", ""), env.get("setting", "")]
    weather = [w for w in weather if w]
    if weather:
        parts.append(", ".join(weather))

    program = session.get("program") or {}
    if program.get("name"):
        block = " ".join(dict.fromkeys(str(x) for x in [program.get("block"), program.get("phase")] if x))
        label = f"{program['name']} {block}".strip()
        if program.get("week") is not None:
            label += f", week {program['week']}"
        if program.get("day") is not None:
            label += f" day {program['day']}"
        parts.append(label)
    remaining = days_to_meet(session)
    if remaining is not None:
        parts.append(f"{remaining} days to the meet")

    lines = [". ".join(parts) + "."]
    if session.get("source"):
        lines.append(f"Imported from {session['source']}; no notes were captured at the time.")
    if top_sets:
        lines.append("Top sets: " + "; ".join(top_sets) + ".")
    names = [e["name"] for e in log["exercises"] if e["category"] != "prep"]
    if names:
        lines.append("Trained: " + ", ".join(names) + ".")
    equipment = []
    for exercise in log["exercises"]:
        equipment += [i["name"] for i in exercise.get("equipment_items", [])]
    if equipment:
        lines.append("Equipment: " + ", ".join(dict.fromkeys(equipment)) + ".")
    lines.append(f"{totals['working_sets']} working sets, {totals['tonnage_lb']:,.0f} lb moved"
                 + (f", average working RPE {avg_rpe}." if avg_rpe else "."))
    metrics = session.get("metrics") or {}
    if metrics.get("bodyweight_lb") is not None:
        body = f"Bodyweight {metrics['bodyweight_lb']} lb"
        if metrics.get("sleep_hrs") is not None:
            body += f", {metrics['sleep_hrs']} hours of sleep"
        lines.append(body + ".")
    for note in log.get("notes", []):
        lines.append(note["text"])
    if session.get("wrap_up"):
        lines.append(session["wrap_up"])
    if session.get("watch_items"):
        lines.append("Watching: " + "; ".join(session["watch_items"]) + ".")
    return " ".join(lines)


def strip_nones(value):
    if isinstance(value, dict):
        return {k: strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_nones(v) for v in value]
    return value


# --------------------------------------------------------------------------- index


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

    paths = [Path(a) for a in args] or sorted(WORKOUTS_DIR.rglob("*.json"))
    if not paths:
        print("no workout logs found: nothing to do")
        return

    validator = load_schema()
    outside = [p for p in paths if WORKOUTS_DIR not in p.resolve().parents]
    links = session_links(catalog_sessions(outside))
    reference = derive.build_reference(catalog_logs(outside))
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
        docs = explode(log, links, reference)
        all_docs.extend(docs)
        print(f"ok {path} -> {len(docs)} document(s)")

    if failed:
        sys.exit("error: fix the invalid log(s) above")

    # Daily and weekly rollups describe the whole history, not the files named on
    # the command line, so they are always built from every log in the repo. The
    # ids are deterministic, so re-emitting every week on every run is an upsert.
    every = all_docs
    if len(paths) != len(catalog_logs([])):
        every = []
        for _day, _sid, log in catalog_logs([]):
            every.extend(explode(log, links, reference))
    rollups = derive.rollup_docs(every)
    all_docs.extend(rollups)
    print(f"rollups -> {len(rollups)} document(s)")

    if validate_only:
        print("validation passed")
        return
    bulk_index(all_docs)


if __name__ == "__main__":
    main()
