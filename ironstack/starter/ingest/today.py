#!/usr/bin/env python3
"""What today's session is, before it starts, from the repo alone.

    python ingest/today.py
    python ingest/today.py --date 2026-09-11
    python ingest/today.py --json

Prints what `program: next` will resolve to for the date (the same arithmetic
log.py uses, so the brief and the log agree), the last session and its summary line,
the watch items carried from the last two sessions, and - because the repo holds no
program file - the main lifts from the most recent session on the SAME program day,
each with its last performance. "Day 3 of 4" last week is the best guess at what day
3 of 4 is this week; the partner says so rather than presenting it as the plan.

No Elasticsearch, no network. Exit 0 always; a repo with no sessions prints that.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import last as lastmod  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_sessions() -> list[dict]:
    docs = []
    for path in lastmod.log_paths():
        docs.append(json.loads(path.read_text()))
    return docs


def resolve_for(day: str) -> dict | None:
    """What `program: next` becomes on `day`, without writing anything."""
    import log as logmod  # noqa: WPS433  (log.py imports the weather client; only needed here)
    import shorthand
    defaults = shorthand.load_defaults()
    program = {k: v for k, v in (defaults.get("program") or {}).items() if not k.startswith("_")}
    program["block"] = "next"
    doc = {"session": {"date": day, "program": program}}
    try:
        logmod.resolve_program(doc)
    except SystemExit as exc:
        return {"error": str(exc)}
    return doc["session"].get("program")


def summary_line(doc: dict) -> str:
    import log as logmod
    return logmod.summarize(doc)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="ingest/today.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD (default today)")
    parser.add_argument("--json", action="store_true")
    opts = parser.parse_args(argv)

    docs = [d for d in load_sessions() if (d.get("session") or {}).get("date", "") < opts.date]
    if not docs:
        print("no sessions before", opts.date)
        return 0
    docs.sort(key=lambda d: d["session"].get("session_id") or d["session"]["date"])
    previous = docs[-1]
    program = resolve_for(opts.date)

    watch = []
    for d in docs[-2:]:
        for item in d["session"].get("watch_items") or []:
            watch.append((d["session"]["date"], item))

    # The most recent session on the same program day, if the counter resolved.
    template = None
    if program and "error" not in program and program.get("day") is not None:
        for d in reversed(docs):
            p = d["session"].get("program") or {}
            if (p.get("day") == program["day"] and p.get("total_days") == program.get("total_days")
                    and p.get("name") == program.get("name") and p.get("block") == program.get("block")):
                template = d
                break
    lifts = []
    if template:
        for exercise in template.get("exercises", []):
            if exercise.get("category") == "main":
                rows = lastmod.performances(exercise["name"], 1)
                lifts.append({"name": exercise["name"], "last": rows[0] if rows else None})

    out = {
        "date": opts.date,
        "program": program,
        "previous": {"date": previous["session"]["date"],
                     "summary": summary_line(previous),
                     "program": lastmod.program_label(previous["session"])},
        "watch": [{"date": d, "item": i} for d, i in watch],
        "same_day_template": template["session"]["date"] if template else None,
        "main_lifts": lifts,
    }
    if opts.json:
        json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    print(f"{opts.date}")
    if program is None:
        print("  program: none configured")
    elif "error" in program:
        print(f"  program: {program['error']}")
    else:
        label = lastmod.program_label({"program": program})
        cycle = program.get("cycle", "weekly")
        extra = f" ({cycle})"
        if program.get("meet_date"):
            days = (date.fromisoformat(program["meet_date"]) - date.fromisoformat(opts.date)).days
            extra += f" · meet in {days} days"
        print(f"  program: {label}{extra}")
    print(f"  last session: {out['previous']['date']} {out['previous']['program']} - {out['previous']['summary']}")
    if watch:
        print("  watch:")
        for d, item in watch:
            print(f"    {d}  {item}")
    if template:
        print(f"  same program day last time: {template['session']['date']}")
        for lift in lifts:
            r = lift["last"]
            if r and r["top"]:
                print(f"    {lift['name']}: {lastmod.fmt_set(r['top'])}  ({r['date']})")
            else:
                print(f"    {lift['name']}: no working sets on record")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
