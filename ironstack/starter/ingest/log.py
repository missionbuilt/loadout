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

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import derive
import index_workouts
import render_md
import shorthand
import suggest
import weather
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "workout.schema.json"
WORKOUTS_DIR = REPO_ROOT / "workouts"


def previous_session(before: str):
    """The most recent session JSON dated before `before`.

    Walks the corpus through index_workouts.log_paths(), not a glob of its own. This
    used to be glob("*/*.json") while the indexer walked rglob("*.json") - the exact
    second-walk drift already removed from verify_index.py. The two agreed only for as
    long as every log happened to sit at exactly depth 2, and the consequence here is
    not a count: `program: next` counts the day and week forward from whatever this
    returns, so a log the walk cannot see silently restarts the program a day early.
    """
    best = None
    for path in index_workouts.log_paths():
        stem = path.stem[:10]
        if stem < before and (best is None or stem > best[0]):
            best = (stem, path)
    return json.loads(best[1].read_text()) if best else None


CYCLES = ("weekly", "block")


def resolve_program(doc: dict) -> None:
    """`program: next` -> the previous session's program, one day further in.

    Two ways to count, chosen by `cycle` (config/defaults.json, or on the line):

      weekly  `d3/4` is day 3 of a 4-day training week; past day 4 the day wraps to
              1 and `week` ticks over. The default, and what most programs are.
      block   `d9/21` is day 9 of a 21-day block; no weeks. Past the last day the
              command refuses rather than inventing block 2 - the next block starts
              with an explicit `program:` line.

    What may override the previous session: the line itself, always; and the
    program's identity from defaults.json (`name`, `cycle`, `meet_date`) - change the
    program in the config and the next log follows it, remove the meet and it stops
    counting down. The counters (`day`, `week`, `total_days`, `block`, `phase`) come
    from the previous session unless the line says otherwise, and `total_days` comes
    from defaults only when the previous session was counting a different cycle.

    The bug this replaces: decode() merges defaults.json into the program before this
    runs, and the old code let every one of those merged values override the previous
    session. Sept 7 2026 said `d1/21`; defaults said `total_days: 4`; Sept 8's `next`
    came out "day 2 of 4". Nothing the lifter wrote had changed.
    """
    program = doc["session"].get("program") or {}
    mode = program.get("block") if program.get("block") in ("next", "same") else None
    if mode is None and program.pop("_advance", False):
        mode = "next"
    if mode is None:
        return
    program.pop("block", None)
    previous = previous_session(doc["session"]["date"])
    if not previous:
        raise SystemExit(f"program: {mode} needs an earlier session to count from")
    base = dict(previous["session"].get("program") or {})
    if mode == "same":
        # An extra session inside the same program day - a recovery-day arm blitz on
        # the Wednesday of a Mon/Tue/Thu/Fri week. The counter must not move, or
        # Thursday becomes day 4 and the week ends a day early.
        d_program = shorthand.load_defaults().get("program") or {}
        for key in ("name", "meet_date"):
            base.pop(key, None)
            if d_program.get(key):
                base[key] = d_program[key]
        base.update({k: v for k, v in program.items()
                     if v is not None and d_program.get(k) != v})
        doc["session"]["program"] = base
        return
    d_program = shorthand.load_defaults().get("program") or {}
    explicit = {k: v for k, v in program.items()
                if v is not None and d_program.get(k) != v}

    cycle = explicit.get("cycle") or d_program.get("cycle") or base.get("cycle") or "weekly"
    if cycle not in CYCLES:
        raise SystemExit(f"program cycle {cycle!r} is not one of {', '.join(CYCLES)}")
    same_cycle = base.get("cycle", "weekly" if base.get("week") is not None else None) == cycle
    if "total_days" in explicit:
        total = explicit["total_days"]
    elif same_cycle and base.get("total_days"):
        total = base["total_days"]
    else:
        total = d_program.get("total_days") or base.get("total_days")

    day = (base.get("day") or 0) + 1
    week = base.get("week")
    if not same_cycle and base.get("day") is not None:
        # Counting a different way than the previous session did is a new start, not
        # day 22 of a 4-day week.
        day, week = 1, 1
    if cycle == "weekly":
        week = week or 1
        if total and day > total:
            day, week = 1, week + 1
    else:
        week = None
        if total and day > total:
            label = "/".join(str(base[k]) for k in ("block", "phase") if base.get(k)) or "block"
            raise SystemExit(
                f"program: next - the {total}-day block ended on {previous['session']['date']} "
                f"(day {total}). Start the next one explicitly: program: {label} d1/{total}")

    for key in ("name", "meet_date"):
        base.pop(key, None)
        if d_program.get(key):
            base[key] = d_program[key]
    base["cycle"] = cycle
    base["day"] = day
    if week is not None:
        base["week"] = week
    else:
        base.pop("week", None)
    if total:
        base["total_days"] = total
    base.update(explicit)
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


def unregistered_equipment(doc: dict) -> list:
    """`@ids` in the session that config/equipment.json has never heard of.

    shorthand.equipment_item() accepts an unknown id as its own name, on purpose - an
    unregistered rack in a hotel gym is a real fact and not worth refusing a log over.
    What it must not be is silent: an id that is a typo of a registered one becomes a
    second equipment item, and every equipment panel then splits that bar's history
    across the two spellings with nothing anywhere reporting a problem.
    """
    known = shorthand.load_equipment()
    unknown = []
    for exercise in doc.get("exercises", []):
        for item in exercise.get("equipment_items", []) or []:
            if item["id"] not in known and item["id"] not in unknown:
                unknown.append(item["id"])
    return unknown


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


def build_parser() -> argparse.ArgumentParser:
    """Every flag this script has ever taken, declared in one place.

    The old hand-rolled parse was `[a for a in argv if not a.startswith("--")]`, which
    collects flag VALUES as positionals: `--message "Log foo" session.iron` read the
    source file as Path("Log foo") and died on a missing file, or - worse, when the
    message happened to name something readable - expanded the wrong input entirely.
    """
    parser = argparse.ArgumentParser(
        prog="ingest/log.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", nargs="?", type=Path,
                        help="the .iron shorthand file to expand")
    parser.add_argument("--stdin", action="store_true",
                        help="read the shorthand on stdin instead of from a file")
    parser.add_argument("--date", default=None,
                        help="session date for --stdin (default: today)")
    parser.add_argument("--no-weather", action="store_true",
                        help="skip the weather lookup")
    parser.add_argument("--skip-names", action="store_true",
                        help="do not check exercise names against the taxonomy")
    parser.add_argument("--strict", action="store_true",
                        help="fail when session metadata is missing")
    parser.add_argument("--commit", action="store_true",
                        help="git add and git commit the three written files")
    parser.add_argument("--push", action="store_true",
                        help="commit and push (CI then indexes)")
    parser.add_argument("--message", default=None,
                        help="commit message (default: 'Log <date> — <summary>')")
    return parser


def main(argv: list) -> int:
    opts = build_parser().parse_args(argv)

    if opts.stdin:
        text = sys.stdin.read()
        session_date = opts.date or date.today().isoformat()
        source = None
    elif opts.source is not None:
        source = opts.source
        try:
            text = source.read_text()
        except OSError as exc:
            print(f"cannot read {source}: {exc.strerror or exc}", file=sys.stderr)
            return 1
        session_date = source.stem[:10]
    else:
        print(__doc__)
        return 1

    doc = shorthand.decode(text, use_defaults=True, filename=f"{session_date}.iron")
    resolve_program(doc)

    note = "" if opts.no_weather else add_weather(doc)

    defaults = shorthand.load_defaults()
    gaps = missing_metadata(doc["session"], defaults.get("require", []))

    session_date = doc["session"]["date"]
    year_dir = WORKOUTS_DIR / session_date[:4]
    year_dir.mkdir(parents=True, exist_ok=True)
    stem = doc["session"].get("session_id") or session_date
    json_path = year_dir / f"{stem}.json"
    md_path = year_dir / f"{stem}.md"
    iron_path = year_dir / f"{stem}.iron"

    # Exercise names, before the write. Until now nothing here classified them, so an
    # unknown name was written, committed, pushed, and first failed in CI at
    # index_workouts --validate - by which time the person who could say what they meant
    # has moved on. This is the only moment they are still sitting here.
    if not opts.skip_names:
        taxonomy = derive.load_taxonomy()
        unknown = []
        for exercise in doc.get("exercises", []):
            name = exercise.get("name")
            if name and name not in taxonomy and name not in unknown:
                unknown.append(name)
        if unknown:
            interactive = sys.stdin.isatty() and not opts.stdin
            accepted, unresolved = suggest.resolve(unknown, taxonomy,
                                                   interactive=interactive)
            if unresolved:
                print("", file=sys.stderr)
                for name in unresolved:
                    print(f"unknown exercise: {name!r}", file=sys.stderr)
                print("Add it to config/exercises.json with its movement pattern and "
                      "muscles, or fix the name in the log.", file=sys.stderr)
                if not interactive:
                    print("(no terminal to ask on - rerun in a shell to be offered "
                          "the close matches)", file=sys.stderr)
                print("Nothing was written.", file=sys.stderr)
                return 5

    # format_checker, for the same reason the indexers pass one: without it Draft 2020-12
    # treats "format": "date" as an annotation, so a malformed date is written to disk
    # here and only surfaces later as a bare ValueError with no filename attached.
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()),
                                     format_checker=Draft202012Validator.FORMAT_CHECKER)
    # Equipment ids, before the write, for the same reason exercise names are checked
    # here: this is the last moment the person who typed it is still in the room.
    strays = unregistered_equipment(doc)
    if strays:
        print(f"unregistered equipment: {', '.join(repr(s) for s in strays)}",
              file=sys.stderr)
        print("Add it to config/equipment.json, or fix the id. Left as it is, each one "
              "becomes its own equipment item in the analytics.", file=sys.stderr)
        if opts.strict:
            print("Nothing was written.", file=sys.stderr)
            return 7

    errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    if errors:
        for error in errors:
            print(f"schema: {'/'.join(str(p) for p in error.path)}: {error.message}", file=sys.stderr)
        return 2

    if gaps and opts.strict:
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
        print(f"  missing: {', '.join(gaps)}" + ("" if opts.strict else " — ask before the memory fades"))
    print(f"  {json_path.relative_to(REPO_ROOT)}")
    print(f"  {md_path.relative_to(REPO_ROOT)}")
    print(f"  {iron_path.relative_to(REPO_ROOT)}")

    if opts.commit or opts.push:
        paths = [str(p.relative_to(REPO_ROOT)) for p in (iron_path, json_path, md_path)]
        # check=True here raised a bare CalledProcessError traceback at the end of an
        # otherwise successful run. The files are written by this point; the only thing
        # that failed is git, so say which command failed and what it said.
        added = subprocess.run(["git", "add", *paths], cwd=REPO_ROOT,
                               capture_output=True, text=True)
        if added.returncode != 0:
            print(f"git add failed ({added.returncode}): "
                  f"{added.stderr.strip() or added.stdout.strip()}", file=sys.stderr)
            print("The session files are written; stage and commit them by hand.",
                  file=sys.stderr)
            return 6
        message = opts.message or f"Log {session_date} — {summarize(doc)}"
        result = subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT,
                                capture_output=True, text=True)
        print(result.stdout.strip() or result.stderr.strip())
        # The commit's return code was never looked at, and --push ran regardless: a
        # failed commit (a hook rejecting it, nothing staged) pushed whatever happened
        # to be on the branch already and reported success for a session that was never
        # committed at all.
        if result.returncode != 0:
            print(f"commit failed ({result.returncode}) — nothing was pushed; "
                  f"the session files are written and staged", file=sys.stderr)
            return 6
        if opts.push:
            push = subprocess.run(["git", "push"], cwd=REPO_ROOT, capture_output=True, text=True)
            print(push.stdout.strip() or push.stderr.strip())
            if push.returncode != 0:
                print("push failed — commit is local; push from a terminal with credentials",
                      file=sys.stderr)
                return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
