#!/usr/bin/env python3
"""`program: next` and `program: same`, the cases that have already gone wrong once.

    python ingest/test_log.py

No files, no network: the previous session and config/defaults.json are stubbed, so
this checks the counting and nothing else.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import log  # noqa: E402
import shorthand  # noqa: E402

FAILURES = 0


def check(label: str, got, want) -> None:
    global FAILURES
    ok = got == want
    FAILURES += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       got  {got!r}\n       want {want!r}")


def run(previous: dict | None, defaults: dict, line: str, date: str = "2026-09-08"):
    log.previous_session = lambda before: ({"session": {"date": "2026-09-07", "program": previous}}
                                           if previous is not None else None)
    shorthand.load_defaults = lambda use_defaults=True: {"program": defaults}
    program = {k: v for k, v in defaults.items() if not k.startswith("_")}
    program.update(shorthand.parse_program(line))
    doc = {"session": {"date": date, "program": program}}
    try:
        log.resolve_program(doc)
    except SystemExit as exc:
        return f"refused: {exc}"
    return doc["session"]["program"]


def main() -> int:
    weekly = {"name": "Shaw Elite", "cycle": "weekly", "total_days": 4}

    # The Sept 8 2026 bug: the lifter wrote d1/21 on day one, defaults said 4, and
    # `next` produced day 2 of 4. Under weekly defaults that IS the intended answer now;
    # the point is that the previous session's counters, not the defaults, drive it.
    prev = {"block": "strongman", "phase": "block1", "week": 1, "day": 2, "total_days": 4,
            "cycle": "weekly", "name": "Shaw Elite"}
    check("weekly: day advances, week held",
          run(prev, weekly, "next"),
          {"block": "strongman", "phase": "block1", "week": 1, "day": 3, "total_days": 4,
           "cycle": "weekly", "name": "Shaw Elite"})

    prev4 = dict(prev, day=4)
    check("weekly: past the last day the week ticks over",
          run(prev4, weekly, "next"),
          {"block": "strongman", "phase": "block1", "week": 2, "day": 1, "total_days": 4,
           "cycle": "weekly", "name": "Shaw Elite"})

    check("same: an extra session inside the day moves nothing",
          run(prev, weekly, "same"),
          prev)

    # Defaults are identity, not counters: a meet removed from the config stops
    # propagating even though the previous session carried it.
    prev_meet = dict(prev, meet_date="2026-10-24")
    check("meet removed from defaults does not carry forward",
          run(prev_meet, weekly, "next").get("meet_date"), None)
    check("meet added to defaults is picked up",
          run(prev, dict(weekly, meet_date="2026-12-05"), "next").get("meet_date"), "2026-12-05")
    check("program renamed in defaults follows on the next log",
          run(prev, dict(weekly, name="Shaw Elite 2"), "next").get("name"), "Shaw Elite 2")

    # A previous session with no cycle field but a week is a weekly session.
    legacy = {"block": "strength", "week": 21, "day": 4, "total_days": 4, "name": "JuggernautAI"}
    check("legacy weekly session wraps into week 22",
          run(legacy, weekly, "next"),
          {"block": "strength", "week": 22, "day": 1, "total_days": 4, "name": "Shaw Elite",
           "cycle": "weekly"})

    block = {"name": "Shaw Elite", "cycle": "block", "total_days": 21}
    prev_b = {"block": "strongman", "phase": "block1", "day": 9, "total_days": 21, "cycle": "block",
              "name": "Shaw Elite"}
    check("block: day advances, no week",
          run(prev_b, block, "next"),
          dict(prev_b, day=10))
    check("block: past the last day it refuses",
          run(dict(prev_b, day=21), block, "next").startswith("refused: program: next - the 21-day block ended"),
          True)
    check("block: an explicit line starts the next block",
          run(dict(prev_b, day=21), block, "strongman/block2 d1/21"),
          {"block": "strongman", "phase": "block2", "day": 1, "total_days": 21, "cycle": "block",
           "name": "Shaw Elite"})

    check("switching cycle in defaults restarts the count",
          run(prev_b, weekly, "next"),
          {"block": "strongman", "phase": "block1", "day": 1, "total_days": 4, "cycle": "weekly",
           "name": "Shaw Elite", "week": 1})

    check("the line overrides everything",
          run(prev, weekly, "next cycle=block d5/21")["total_days"], 21)

    check("no previous session refuses",
          run(None, weekly, "next"), "refused: program: next needs an earlier session to count from")

    print(f"\n{'all passed' if not FAILURES else f'{FAILURES} failed'}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
