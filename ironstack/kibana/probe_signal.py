#!/usr/bin/env python3
"""Read-only calibration probe for the Overview Signal cards.

Runs the ES|QL the three verdict cards will use, plus the distribution stats
needed to pick band thresholds from Mike's own history rather than inventing
them. Writes nothing, indexes nothing, touches no saved object.

    cd ~/Projects/ironstack-log && source .env
    python ~/Projects/loadout/ironstack/kibana/probe_signal.py

Paste the whole output back into the session.
"""

from __future__ import annotations

import json
import os
import sys

import requests

ENDPOINT = os.environ.get("ES_ENDPOINT", "").strip().rstrip("/")
API_KEY = os.environ.get("ES_API_KEY", "").strip()
if not ENDPOINT or not API_KEY:
    sys.exit("error: ES_ENDPOINT and ES_API_KEY must be set. `cd ~/Projects/ironstack-log && source .env`")

HEADERS = {"Authorization": f"ApiKey {API_KEY}", "Content-Type": "application/json"}

# COALESCE throughout: a null Prilepin bucket would otherwise null the whole sum
# and silently drop the week from every ratio below.
HEAVY = ('COALESCE(prilepin_reps.z80_89, 0) + COALESCE(prilepin_reps.z90plus, 0)')
TOTAL = ('COALESCE(prilepin_reps.lt70, 0) + COALESCE(prilepin_reps.z70_79, 0) + '
         'COALESCE(prilepin_reps.z80_89, 0) + COALESCE(prilepin_reps.z90plus, 0)')

QUERIES = {
    # ---- card 1, intensity: the exact 13 rows the card will read -------------
    "intensity_window": f"""
        FROM workout-weekly
        | SORT @timestamp DESC
        | LIMIT 13
        | EVAL heavy = {HEAVY}, tot = {TOTAL}
        | EVAL pct = CASE(tot > 0, heavy * 100.0 / tot, null)
        | KEEP iso_week, week_start, heavy, tot, pct, tonnage_lb, sessions
    """,
    # ---- card 1 calibration: where do the bands actually fall ---------------
    "intensity_spread": f"""
        FROM workout-weekly
        | EVAL heavy = {HEAVY}, tot = {TOTAL}
        | WHERE tot > 0
        | EVAL pct = heavy * 100.0 / tot
        | STATS weeks = COUNT(*), avg = AVG(pct), p25 = PERCENTILE(pct, 25),
                p50 = PERCENTILE(pct, 50), p75 = PERCENTILE(pct, 75),
                p90 = PERCENTILE(pct, 90), max = MAX(pct)
    """,
    "intensity_zero_weeks": f"""
        FROM workout-weekly
        | EVAL tot = {TOTAL}
        | EVAL has = CASE(tot > 0, 1, 0)
        | STATS weeks = COUNT(*), with_main_reps = SUM(has)
    """,
    # ---- card 2, load trend: current week plus the precedent lookup ---------
    "load_recent": """
        FROM workout-weekly
        | SORT @timestamp DESC
        | LIMIT 14
        | EVAL month_s = DATE_FORMAT("MMM yyyy", @timestamp)
        | KEEP iso_week, month_s, acwr, acwr_band, monotony, load_7d, load_28d, tonnage_lb
    """,
    "load_band_counts": """
        FROM workout-weekly
        | STATS weeks = COUNT(*) BY acwr_band
        | SORT weeks DESC
    """,
    "load_band_history": """
        FROM workout-weekly
        | WHERE acwr_band IS NOT NULL
        | SORT @timestamp DESC
        | LIMIT 200
        | EVAL month_s = DATE_FORMAT("MMM yyyy", @timestamp)
        | KEEP iso_week, month_s, acwr, acwr_band
    """,
    # ---- card 3, drift: cadence vs current gap ------------------------------
    "drift_lifts": """
        FROM workout-sets
        | WHERE set_type == "working" AND is_competition_lift == true
          AND @timestamp >= NOW() - 365 days
        | STATS last_d = MAX(date), sessions = COUNT_DISTINCT(session_id),
                name = MAX(exercise.name) BY lift_slug
        | SORT last_d ASC
    """,
    "drift_muscles": """
        FROM workout-sets
        | WHERE set_type == "working" AND @timestamp >= NOW() - 365 days
          AND muscles_primary IS NOT NULL
        | MV_EXPAND muscles_primary
        | STATS last_d = MAX(date), sessions = COUNT_DISTINCT(session_id) BY muscles_primary
        | SORT last_d ASC
        | LIMIT 40
    """,
    # ---- provenance: the caveats the cards have to state out loud -----------
    "provenance": """
        FROM workout-sets
        | WHERE set_type == "working"
        | EVAL self_ref = CASE(intensity_ref == "self", 1, 0),
               low_conf = CASE(e1rm_confidence == "low", 1, 0)
        | STATS sets = COUNT(*), self_referenced = SUM(self_ref), low_confidence = SUM(low_conf)
    """,
    "weekly_coverage": """
        FROM workout-weekly
        | STATS weeks = COUNT(*), first = MIN(@timestamp), last = MAX(@timestamp),
                with_acwr = COUNT(acwr), with_dots = COUNT(dots)
    """,
}


def run(name: str, esql: str) -> None:
    query = " ".join(line.strip() for line in esql.strip().splitlines())
    print(f"\n{'=' * 72}\n{name}\n{'=' * 72}")
    try:
        r = requests.post(f"{ENDPOINT}/_query", headers=HEADERS,
                          json={"query": query}, timeout=60)
    except requests.RequestException as exc:
        print(f"  REQUEST FAILED: {exc}")
        return
    if r.status_code != 200:
        # The parse errors are the point of running this before writing the cards.
        print(f"  HTTP {r.status_code}")
        print(f"  {r.text[:600]}")
        print(f"  query: {query}")
        return
    body = r.json()
    cols = [c["name"] for c in body.get("columns", [])]
    rows = body.get("values", [])
    if not rows:
        print("  (no rows)")
        return
    widths = [max(len(c), *(len(str(row[i])) for row in rows)) for i, c in enumerate(cols)]
    print("  " + "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("  " + "  ".join("-" * w for w in widths))
    for row in rows:
        print("  " + "  ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)))


def main() -> None:
    host = ENDPOINT.split("//")[-1].split(".")[0]
    print(f"Ironstack Signal card probe. Project: {host}. Read-only.")
    for name, esql in QUERIES.items():
        run(name, esql)
    print("\nDone. Nothing was written.")


if __name__ == "__main__":
    main()
