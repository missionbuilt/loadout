#!/usr/bin/env python3
"""Turn one shorthand session into everything the repo needs.

    python ingest/log.py workouts/2026/2026-09-04.iron            # expand, validate, write
    python ingest/log.py workouts/2026/2026-09-04.iron --commit   # ... and commit
    python ingest/log.py workouts/2026/2026-09-04.iron --push     # ... commit and push (CI indexes)
    python ingest/log.py --stdin --date 2026-09-04                # read shorthand on stdin

Flags: --strict fails when session metadata is missing, --no-weather skips the
weather lookup, --message "..." sets the commit message.

Does, in order: expand the shorthand (defaults, prep templates, `program: next`),
look up the weather the session was trained in, check the session metadata is
there, validate against schema/workout.schema.json, write the session JSON and
the markdown log, and print a summary. Nothing is committed unless you ask.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_md
import shorthand
import weather
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "workout.schema.json"
WORKOUTS_DIR = REPO_ROOT / "workouts"


def previous_session(before: str):
    """The most recent session JSON dated before `before`."""
    best = None
    for path in WORKOUTS_DIR.glob("*/*.json"):
        stem = path.stem[:10]
        if stem < before and (best is None or stem > best[0]):
            best = (stem, path)
    return json.loads(best[1].read_text()) if best else None


def resolve_program(doc: dict) -> None:
    """`program: next` -> the previous session's program, one day further in."""
    program = doc["session"].get("program") or {}
    if program.get("block") != "next" and not program.pop("_advance", False):
        return
    program.pop("block", None)
    previous = previous_session(doc["session"]["date"])
    if not previous:
        raise SystemExit("program: next needs an earlier session to count from")
    base = dict(previous["session"].get("program") or {})
    day = (base.get("day") or 0) + 1
    total = base.get("total_days")
    week = base.get("week")
    if total and day > total:
        day = 1
        if week is not None:
            week += 1
    base["day"] = day
    if week is not None:
        base["week"] = week
    base.update({k: v for k, v in program.items() if v is not None})
    doc["session"]["program"] = base


REQUIRED_LABELS = {
    "start_time": "start time",
    "duration_min": "duration",
    "location": "location",
    "environment.temp_f": "weather",
    "metrics.bodyweight_lb": "bodyweight",
    "metrics.sleep_hrs": "sleep",
}


def missing_metadata(session: dict, required: list) -> list:
    """Which of the session-level facts the log is supposed to carry aren't there."""
    gaps = []
    for field in required:
        head, _, tail = field.partition(".")
        value = session.get(head)
        if tail:
            value = (value or {}).get(tail)
        if value in (None, "", {}, []):
            gaps.append(REQUIRED_LABELS.get(field, field))
    return gaps


def add_weather(doc: dict) -> str:
    """Fill session.environment from the coordinates and the hour trained."""
    session = doc["session"]
    env = session.get("environment") or {}
    if env.get("temp_f") is not None:
        return ""
    geo = (session.get("location") or {}).get("geo")
    if not geo:
        return "no weather: the session has no coordinates (set location.geo in config/defaults.json)"
    hour = int((session.get("start_time") or "12:00").split(":")[0])
    found = weather.fetch(geo["lat"], geo["lon"], session["date"], hour,
                          session.get("timezone") or "auto")
    if not found:
        return "no weather: lookup failed (offline, or the date is out of range)"
    found.update(env)
    session["environment"] = found
    bits = [f"{found['temp_f']}F" if "temp_f" in found else "",
            f"{found['humidity_pct']}%" if "humidity_pct" in found else "",
            found.get("conditions", ""), found.get("wind", "")]
    return "weather: " + ", ".join(b for b in bits if b)


def summarize(doc: dict) -> str:
    """The same arithmetic index_workouts.py does, so the number you see when you
    log a session is the number the dashboard shows: tonnage over every set."""
    every = [s for e in doc["exercises"] for s in e["sets"]]
    sets = [s for s in every if s.get("set_type") != "prep"]
    tonnage = sum((s.get("weight_lb") or 0) * s["reps"]
                  for s in every if s.get("rep_unit", "reps") == "reps")
    rpes = [s["rpe"] for s in sets if s.get("rpe") is not None]
    work = [e for e in doc["exercises"] if e["category"] != "prep"]
    parts = [
        f"{len(work)} exercises",
        f"{len(sets)} working sets",
        f"{tonnage:,.0f} lb moved",
    ]
    if rpes:
        parts.append(f"avg RPE {sum(rpes) / len(rpes):.1f}")
    if doc.get("notes"):
        parts.append(f"{len(doc['notes'])} notes")
    return " · ".join(parts)


def main(argv: list) -> int:
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]

    def flag_value(name, default=None):
        if name in argv:
            index = argv.index(name)
            if index + 1 < len(argv):
                return argv[index + 1]
        return default

    if "--stdin" in flags:
        text = sys.stdin.read()
        session_date = flag_value("--date") or date.today().isoformat()
        source = None
    elif args:
        source = Path(args[0])
        text = source.read_text()
        session_date = source.stem[:10]
    else:
        print(__doc__)
        return 1

    doc = shorthand.decode(text, use_defaults=True, filename=f"{session_date}.iron")
    resolve_program(doc)

    note = "" if "--no-weather" in flags else add_weather(doc)

    defaults = shorthand.load_defaults()
    gaps = missing_metadata(doc["session"], defaults.get("require", []))

    session_date = doc["session"]["date"]
    year_dir = WORKOUTS_DIR / session_date[:4]
    year_dir.mkdir(parents=True, exist_ok=True)
    stem = doc["session"].get("session_id") or session_date
    json_path = year_dir / f"{stem}.json"
    md_path = year_dir / f"{stem}.md"
    iron_path = year_dir / f"{stem}.iron"

    errors = sorted(Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).iter_errors(doc),
                    key=lambda e: e.path)
    if errors:
        for error in errors:
            print(f"schema: {'/'.join(str(p) for p in error.path)}: {error.message}", file=sys.stderr)
        return 2

    if gaps and "--strict" in flags:
        print(f"missing session metadata: {', '.join(gaps)}", file=sys.stderr)
        return 4

    json_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    md_path.write_text(render_md.render(doc))
    if source is None or source.resolve() != iron_path.resolve():
        iron_path.write_text(text if text.endswith("\n") else text + "\n")

    print(f"{stem}: {summarize(doc)}")
    if note:
        print(f"  {note}")
    if gaps:
        print(f"  missing: {', '.join(gaps)}" + ("" if "--strict" in flags else " — ask before the memory fades"))
    print(f"  {json_path.relative_to(REPO_ROOT)}")
    print(f"  {md_path.relative_to(REPO_ROOT)}")
    print(f"  {iron_path.relative_to(REPO_ROOT)}")

    if "--commit" in flags or "--push" in flags:
        paths = [str(p.relative_to(REPO_ROOT)) for p in (iron_path, json_path, md_path)]
        subprocess.run(["git", "add", *paths], cwd=REPO_ROOT, check=True)
        message = flag_value("--message") or f"Log {session_date} — {summarize(doc)}"
        result = subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT,
                                capture_output=True, text=True)
        print(result.stdout.strip() or result.stderr.strip())
        if "--push" in flags:
            push = subprocess.run(["git", "push"], cwd=REPO_ROOT, capture_output=True, text=True)
            print(push.stdout.strip() or push.stderr.strip())
            if push.returncode != 0:
                print("push failed — commit is local; push from a terminal with credentials",
                      file=sys.stderr)
                return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
