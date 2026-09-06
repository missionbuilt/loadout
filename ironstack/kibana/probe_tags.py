#!/usr/bin/env python3
"""Read-only probe: why the Mindset tag chart and the Mindset card disagree.

Round three of the switcher walk found the card saying `motivation 4` over a tag
chart with no `motivation` bar at all - not a shorter one, none - on a 31-note
corpus at a year-wide range. The card was checked against the logs and is right:
14 distinct tags, 31 note documents. The chart shows 8 of those 14, and the notes
list on the same page renders tag chips (MOBILITY) for tags the chart beside it
does not bucket. Same index, same document, two readings.

So the disagreement is between the terms aggregation and the documents, and that
is a question only the cluster can answer. This asks it three ways:

  1. what the logs say the tags are            (the repo, no cluster)
  2. what a terms aggregation on `tags` returns (the chart's own query)
  3. what the documents actually carry          (a plain search, no aggregation)

If 1 and 3 agree and 2 is short, the mapping is the answer and the field types
printed at the end say which way. If 1 and 3 disagree, the index is stale and a
reindex is the answer. Writes nothing, indexes nothing, touches no saved object.

    cd /path/to/your-workout-log && set -a && source .env && set +a
    python ~/Projects/loadout/ironstack/kibana/probe_tags.py

Paste the whole output back into the session.
"""

from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

import requests

ENDPOINT = os.environ.get("ES_ENDPOINT", "").strip().rstrip("/")
API_KEY = os.environ.get("ES_API_KEY", "").strip()
if not ENDPOINT or not API_KEY:
    sys.exit("error: ES_ENDPOINT and ES_API_KEY must be set. "
             "`cd /path/to/your-workout-log && set -a && source .env && set +a`")

HEADERS = {"Authorization": f"ApiKey {API_KEY}", "Content-Type": "application/json"}
INDEX = "workout-notes"
# The chart's own bucket, copied from build_dashboards.py's tag_cols. If that
# changes, this has to change with it or the probe stops asking the real question.
TERMS_SIZE = 25


def post(path: str, body: dict) -> dict:
    resp = requests.post(f"{ENDPOINT}{path}", headers=HEADERS, json=body, timeout=60)
    if not resp.ok:
        sys.exit(f"error: {path} -> {resp.status_code} {resp.text[:600]}")
    return resp.json()


def get(path: str) -> dict:
    resp = requests.get(f"{ENDPOINT}{path}", headers=HEADERS, timeout=60)
    if not resp.ok:
        sys.exit(f"error: {path} -> {resp.status_code} {resp.text[:600]}")
    return resp.json()


def find_workouts() -> Path | None:
    """The logs directory, from wherever this was run.

    Path.cwd()/"workouts" was the first version and it read zero notes on the first
    real run, which the table then reported as fifteen rows of "index does not match
    the logs" - a probe written to settle a disagreement inventing one of its own.
    Walk up instead, and say out loud which directory was read.
    """
    for base in [Path.cwd(), *Path.cwd().parents]:
        if (base / "workouts").is_dir():
            return base / "workouts"
    return None


def from_logs() -> tuple[collections.Counter, int]:
    """Reading 1: the repo. Same walk the indexer does - rglob, not glob."""
    root = find_workouts()
    if root is None:
        print("  logs: no workouts/ directory at or above the current directory.\n"
              "        Run this from your workout-log repo; the log column below is "
              "empty and means nothing.\n")
        return collections.Counter(), 0
    print(f"  logs read from {root}")
    tags, docs = collections.Counter(), 0
    for path in sorted(root.rglob("*.json")):
        try:
            log = json.loads(path.read_text())
        except Exception as exc:                      # noqa: BLE001
            print(f"  unreadable: {path}: {exc}")
            continue
        for note in log.get("notes") or []:
            docs += 1
            for tag in note.get("tags") or []:
                tags[tag] += 1
        # watch_items are notes too, written with tags ["watch"] - see
        # index_workouts.py. They are nested under `session`, which is why an
        # earlier count of this corpus came out 19 instead of 31.
        watch = (log.get("watch_items")
                 or (log.get("session") or {}).get("watch_items") or [])
        for _ in watch:
            docs += 1
            tags["watch"] += 1
    return tags, docs


def from_terms() -> tuple[collections.Counter, int, int]:
    """Reading 2: the aggregation the chart runs."""
    body = {"size": 0, "aggs": {"tags": {"terms": {"field": "tags", "size": TERMS_SIZE}}}}
    agg = post(f"/{INDEX}/_search", body)["aggregations"]["tags"]
    counts = collections.Counter({b["key"]: b["doc_count"] for b in agg["buckets"]})
    return counts, agg.get("sum_other_doc_count", 0), agg.get("doc_count_error_upper_bound", 0)


def from_docs() -> tuple[collections.Counter, int]:
    """Reading 3: the documents, counted client-side with no aggregation."""
    body = {"size": 1000, "_source": ["tags", "date", "phase"],
            "query": {"match_all": {}}}
    hits = post(f"/{INDEX}/_search", body)["hits"]["hits"]
    tags = collections.Counter()
    for hit in hits:
        for tag in hit["_source"].get("tags") or []:
            tags[tag] += 1
    return tags, len(hits)


def main() -> None:
    print(f"probe_tags: {ENDPOINT} / {INDEX}\n")

    logs, log_docs = from_logs()
    terms, other, err = from_terms()
    docs, doc_count = from_docs()

    print(f"note documents  logs={log_docs}  index={doc_count}")
    print(f"terms agg       size={TERMS_SIZE}  buckets={len(terms)}  "
          f"sum_other_doc_count={other}  doc_count_error_upper_bound={err}\n")

    names = sorted(set(logs) | set(terms) | set(docs))
    width = max((len(n) for n in names), default=3)
    print(f"{'tag'.ljust(width)}  {'logs':>5} {'terms':>6} {'docs':>5}   verdict")
    print("-" * (width + 32))
    have_logs = log_docs > 0
    disagree = []
    for name in names:
        a, b, c = logs[name], terms[name], docs[name]
        if not have_logs:
            # No log reading, so the only comparison worth printing is agg vs docs.
            verdict = "" if b == c else "the agg and the documents disagree"
            if verdict:
                disagree.append(name)
            print(f"{name.ljust(width)}  {'-':>5} {b:>6} {c:>5}   {verdict}")
            continue
        if a == b == c:
            verdict = ""
        elif a == c and b == 0:
            verdict = "the agg cannot see it"
            disagree.append(name)
        elif a != c:
            verdict = "index does not match the logs"
            disagree.append(name)
        else:
            verdict = "counts differ"
            disagree.append(name)
        print(f"{name.ljust(width)}  {a:>5} {b:>6} {c:>5}   {verdict}")

    print("\nmapping for the fields in play:")
    mapping = get(f"/{INDEX}/_mapping")
    props = next(iter(mapping.values()))["mappings"].get("properties", {})
    for field in ("tags", "phase", "text", "date"):
        print(f"  {field:6} {json.dumps(props.get(field, 'NOT MAPPED'))}")

    print()
    if not have_logs:
        print("The log column was not read, so this run only compares the aggregation\n"
              "against the documents. Those two "
              + ("agree - whatever the chart shows, it is what the index holds."
                 if not disagree else "disagree, which is the mapping question.")
              + "\nRe-run from the workout-log repo for the third reading.")
    elif not disagree:
        print("all three readings agree - nothing to explain.")
    elif all(logs[n] == docs[n] for n in disagree):
        print("The documents match the logs and the aggregation is short, so this is a\n"
              "mapping question, not an indexing one. Read the `tags` mapping above:\n"
              "a terms aggregation reads doc_values, and a field that is `text`, or\n"
              "`keyword` with an `ignore_above` under the length of these values, or\n"
              "one with doc_values disabled, will bucket some values and not others.")
    else:
        print("The documents do not match the logs, so the index is behind the repo.\n"
              "Re-run ingest/index_workouts.py and probe again before reading the\n"
              "mapping as the cause.")


if __name__ == "__main__":
    main()
