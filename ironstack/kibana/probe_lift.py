#!/usr/bin/env python3
"""Read-only calibration probe for the Lift Signal card.

The Lift page asks one question — is this lift going up? — and currently answers it with
two noisy sawtooth charts and no verdict. This probe returns the exact rows the card
would read, for all three competition lifts, plus the coverage stats that decide whether
a rank-based or a delta-based sentence is honest.

    cd ~/Projects/ironstack-log && source .env
    python ~/Projects/loadout/ironstack/kibana/probe_lift.py

Paste the whole output back into the session.

Aliases avoid `first` and `last`, which are reserved words in ES|QL — the cause of the
lift_header failure on Sept 4, misdiagnosed then as a CASE shifting the parse.
"""

from __future__ import annotations

import os
import sys

import requests

ENDPOINT = os.environ.get("ES_ENDPOINT", "").strip().rstrip("/")
API_KEY = os.environ.get("ES_API_KEY", "").strip()
if not ENDPOINT or not API_KEY:
    sys.exit("error: ES_ENDPOINT and ES_API_KEY must be set. `cd ~/Projects/ironstack-log && source .env`")

HEADERS = {"Authorization": f"ApiKey {API_KEY}", "Content-Type": "application/json"}
LIFTS = ["comp-deadlift", "comp-bench", "comp-squat"]

# The card's own query, one lift at a time. On the dashboard the lift_slug control
# supplies the WHERE; here it is spelled out.
def history(slug: str) -> str:
    return f"""
        FROM workout-sets
        | WHERE set_type == "working" AND lift_slug == "{slug}"
          AND e1rm_confidence != "low" AND est_e1rm IS NOT NULL
        | STATS e1 = MAX(est_e1rm), top_lb = MAX(weight_lb), sess_d = MAX(date) BY session_id
        | SORT sess_d DESC
        | LIMIT 20
        | EVAL when_s = DATE_FORMAT("MMM d, yyyy", sess_d)
        | KEEP session_id, when_s, e1, top_lb
    """


QUERIES = {}
for _slug in LIFTS:
    QUERIES[f"history: {_slug}"] = history(_slug)

# How much of each lift's history is usable at all. If confident estimates are rare, a
# rank against "your last N sessions" is measuring coverage, not strength.
QUERIES["confidence coverage by lift"] = """
    FROM workout-sets
    | WHERE set_type == "working" AND is_competition_lift == true
    | EVAL ok = CASE(e1rm_confidence != "low" AND est_e1rm IS NOT NULL, 1, 0)
    | STATS sets = COUNT(*), confident = SUM(ok),
            sessions = COUNT_DISTINCT(session_id) BY lift_slug
    | SORT lift_slug ASC
"""

# Sessions carrying a confident estimate, which is what the card can actually rank.
QUERIES["rankable sessions by lift"] = """
    FROM workout-sets
    | WHERE set_type == "working" AND is_competition_lift == true
      AND e1rm_confidence != "low" AND est_e1rm IS NOT NULL
    | STATS sessions = COUNT_DISTINCT(session_id), best = MAX(est_e1rm),
            heaviest = MAX(weight_lb) BY lift_slug
    | SORT lift_slug ASC
"""

# Where the all-time best sits in time. If every lift peaked years ago the verdict has to
# be about the recent window, not the record.
QUERIES["when each lift peaked"] = """
    FROM workout-sets
    | WHERE set_type == "working" AND is_competition_lift == true
      AND e1rm_confidence != "low" AND est_e1rm IS NOT NULL
    | STATS e1 = MAX(est_e1rm) BY lift_slug, session_id
    | SORT e1 DESC
    | LIMIT 12
"""


def run(name: str, esql: str) -> None:
    query = " ".join(line.strip() for line in esql.strip().splitlines())
    print(f"\n{'=' * 74}\n{name}\n{'=' * 74}")
    try:
        r = requests.post(f"{ENDPOINT}/_query", headers=HEADERS, json={"query": query}, timeout=60)
    except requests.RequestException as exc:
        print(f"  REQUEST FAILED: {exc}")
        return
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}\n  {r.text[:500]}\n  query: {query}")
        return
    body = r.json()
    cols = [c["name"] for c in body.get("columns", [])]
    rows = body.get("values", [])
    if not rows:
        print("  (no rows)")
        return
    w = [max(len(c), *(len(str(row[i])) for row in rows)) for i, c in enumerate(cols)]
    print("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    print("  " + "  ".join("-" * x for x in w))
    for row in rows:
        print("  " + "  ".join(str(v).ljust(w[i]) for i, v in enumerate(row)))


def main() -> None:
    print("Ironstack Lift card probe. Read-only.")
    for name, esql in QUERIES.items():
        run(name, esql)
    print("\nDone. Nothing was written.")


if __name__ == "__main__":
    main()
