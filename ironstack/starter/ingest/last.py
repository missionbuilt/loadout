#!/usr/bin/env python3
"""The last few times a lift was done, from the repo alone.

    python ingest/last.py "Competition Bench"
    python ingest/last.py "Log Clean and Press" --n 5
    python ingest/last.py "Dips" --json

Reads workouts/**/*.json and prints, newest first, each session the lift appears in:
the date, program day, pacing and equipment, every set on one line, and the lifter's
own notes on it. No Elasticsearch, no network - this is what the training partner
reads before a session ("last time on press: 95x3 @10, belt on, nothing left") and
it has to work in a sandbox with nothing but the files.

Names resolve the way log.py resolves them: the canonical name in
config/exercises.json, or any alias of it, case-insensitive. An unknown name gets the
closest matches and exit 5, the same code log.py uses, so the partner shows the list
and asks rather than guessing.

Exit codes: 0 printed, 1 usage, 5 unknown exercise name.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKOUTS_DIR = REPO_ROOT / "workouts"
EXERCISES_PATH = REPO_ROOT / "config" / "exercises.json"


def log_paths() -> list[Path]:
    """Every session log, oldest first. The same walk index_workouts.py makes."""
    return sorted(WORKOUTS_DIR.rglob("*.json"))


def canonical(name: str) -> str | None:
    """`comp bench` -> `Competition Bench`, through the taxonomy's aliases."""
    if not EXERCISES_PATH.exists():
        return name
    taxonomy = json.loads(EXERCISES_PATH.read_text())
    by_lower = {k.lower(): k for k in taxonomy if not k.startswith("_")}
    key = by_lower.get(name.strip().lower())
    if key is None:
        return None
    entry = taxonomy.get(key) or {}
    return entry.get("alias_of") or key


def closest(name: str, limit: int = 5) -> list[str]:
    if not EXERCISES_PATH.exists():
        return []
    names = [k for k in json.loads(EXERCISES_PATH.read_text()) if not k.startswith("_")]
    return difflib.get_close_matches(name, names, n=limit, cutoff=0.5)


def same_lift(a: str, b: str) -> bool:
    return (canonical(a) or a).lower() == (canonical(b) or b).lower()


def fmt_weight(value) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def fmt_set(s: dict) -> str:
    """One set, the way the shorthand writes it."""
    if s.get("load_type") == "bodyweight":
        core = "bw" + (fmt_weight(s["weight_lb"]) if s.get("weight_lb") else "")
    elif s.get("weight_each_lb") is not None:
        core = f"{fmt_weight(s['weight_each_lb'])}ea"
    else:
        core = fmt_weight(s.get("weight_lb", 0))
    unit = {"seconds": "s", "walks": "w"}.get(s.get("rep_unit", "reps"), "")
    core += f"x{fmt_weight(s.get('reps', 0))}{unit}"
    if s.get("each_side"):
        core += "/s"
    if s.get("distance_ft"):
        core += f" ft={fmt_weight(s['distance_ft'])}"
    if s.get("rpe") is not None:
        core += f" @{fmt_weight(s['rpe'])}"
    if s.get("gear"):
        core += " +" + ", ".join(s["gear"])
    if s.get("notes"):
        core += f' "{s["notes"]}"'
    return core


def program_label(session: dict) -> str:
    program = session.get("program") or {}
    bits = []
    if program.get("name"):
        bits.append(program["name"])
    if program.get("week") is not None:
        bits.append(f"w{program['week']}")
    if program.get("day") is not None:
        day = f"d{program['day']}"
        if program.get("total_days"):
            day += f"/{program['total_days']}"
        bits.append(day)
    return " ".join(bits)


def performances(name: str, n: int) -> list[dict]:
    """Newest first: every session the lift appears in, with its sets and notes."""
    out = []
    for path in reversed(log_paths()):
        doc = json.loads(path.read_text())
        session = doc.get("session") or {}
        for exercise in doc.get("exercises", []):
            if not same_lift(exercise["name"], name):
                continue
            notes = [n_ for n_ in doc.get("notes", [])
                     if n_.get("phase") == "exercise" and n_.get("exercise") == exercise["name"]]
            working = [s for s in exercise.get("sets", []) if s.get("set_type", "working") != "prep"]
            top = None
            for s in working:
                key = (s.get("weight_lb") or 0, s.get("reps") or 0)
                if top is None or key > ((top.get("weight_lb") or 0), (top.get("reps") or 0)):
                    top = s
            out.append({
                "date": session.get("date"),
                "session_id": session.get("session_id"),
                "program": program_label(session),
                "name": exercise["name"],
                "category": exercise.get("category"),
                "equipment": exercise.get("equipment"),
                "pacing_sec": exercise.get("pacing_sec"),
                "emphasis": exercise.get("emphasis"),
                "sets": exercise.get("sets", []),
                "top": top,
                "notes": [n_["text"] for n_ in notes],
                "watch": session.get("watch_items") or [],
            })
        if len(out) >= n:
            break
    return out[:n]


def render(rows: list[dict], name: str) -> str:
    if not rows:
        return f"{name}: never logged"
    lines = [f"{rows[0]['name']} - last {len(rows)} of {len(rows)}" if len(rows) == 1
             else f"{rows[0]['name']} - last {len(rows)}"]
    for r in rows:
        head = [r["date"], r["program"], r["category"]]
        if r["pacing_sec"]:
            head.append(f"every {r['pacing_sec'] // 60}:{r['pacing_sec'] % 60:02d}")
        if r["equipment"]:
            head.append(r["equipment"])
        if r["emphasis"]:
            head.append(r["emphasis"])
        lines.append("  " + " · ".join(h for h in head if h))
        working = [s for s in r["sets"] if s.get("set_type", "working") != "prep"]
        prep = [s for s in r["sets"] if s.get("set_type") == "prep"]
        if prep:
            lines.append("    w: " + ", ".join(fmt_set(s) for s in prep))
        if working:
            lines.append("    " + " · ".join(fmt_set(s) for s in working))
        if r["top"]:
            lines.append(f"    top: {fmt_set(r['top'])}")
        for note in r["notes"]:
            lines.append(f"    - {note}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ingest/last.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lift", nargs="?", help="exercise name or alias, as in config/exercises.json")
    parser.add_argument("--n", type=int, default=3, help="how many sessions back (default 3)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    opts = parser.parse_args(argv)
    if not opts.lift:
        parser.print_usage()
        return 1
    name = canonical(opts.lift)
    if name is None:
        print(f"unknown exercise {opts.lift!r} - not in config/exercises.json", file=sys.stderr)
        for guess in closest(opts.lift):
            print(f"  did you mean: {guess}", file=sys.stderr)
        return 5
    rows = performances(name, max(opts.n, 1))
    if opts.json:
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(render(rows, name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
