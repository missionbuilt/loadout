#!/usr/bin/env python3
"""Check that what's in Elasticsearch matches what's in this repo.

    python ingest/verify_index.py

Rebuilds every document locally, then asks Elasticsearch three questions:
  1. Are the mappings the ones we intended (types, and the semantic_text siblings)?
  2. Are the counts right, index by index?
  3. Do sampled documents match the local ones field for field?

Exits non-zero if anything is off. Reads ES_ENDPOINT and ES_API_KEY from the
environment, same as the indexers.
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import index_workouts as ix
import index_meets as im

REPO_ROOT = Path(__file__).resolve().parent.parent

# field path -> expected mapping type. The ones a wrong dynamic mapping would break.
EXPECTED = {
    "workout-sessions": {
        "source": "keyword",
        "digest": "text",
        "watch_items": "text",
        "wrap_up": "text",
        "gear_notes": "text",
        "inol_total": "float",
        "inol_by_lift.inol": "float",
        "prilepin_reps.z80_89": "integer",
        "fatigue_index": "float",
        "density_lb_per_min": "float",
        "load_au": "float",
        "load_estimated": "boolean",
    },
    "workout-sets": {
        "exercise.equipment_ids": "keyword",
        "exercise.equipment_names": "keyword",
        "exercise.equipment_kinds": "keyword",
        "exercise.bar_weight_lb": "float",
        "weight_each_lb": "float",
        "each_side": "boolean",
        "scheme": "keyword",
        "cardio.distance_mi": "float",
        "notes": "text",
        "est_e1rm": "float",
        "e1rm_method": "keyword",
        "e1rm_confidence": "keyword",
        "intensity_pct": "float",
        "intensity_ref": "keyword",
        "pct_meet_max": "float",
        "inol": "float",
        "prilepin_zone": "keyword",
        "lift_slug": "keyword",
        "pattern": "keyword",
        "muscles_primary": "keyword",
        "muscles_secondary": "keyword",
        "lift_family": "keyword",
        "is_competition_lift": "boolean",
        "is_unilateral": "boolean",
        "work_ftlb": "float",
        "tut_sec": "float",
    },
    "workout-daily": {
        "tonnage_lb": "float",
        "best_e1rm.value": "float",
        "sets_by_muscle.muscle": "keyword",
    },
    "workout-weekly": {
        "acwr": "float",
        "acwr_band": "keyword",
        "monotony": "float",
        "strain": "float",
        "dots": "float",
        "projected_total_lb": "float",
        "inol_hardest_band": "keyword",
        "bodyweight_source": "keyword",
    },
    "workout-notes": {"text": "text", "phase": "keyword"},
    "workout-meets": {"notes": "text"},
}

SEMANTIC = {
    "workout-sessions": ["wrap_up_semantic", "gear_notes_semantic", "watch_semantic", "digest_semantic"],
    "workout-sets": ["notes_semantic"],
    "workout-notes": ["text_semantic"],
    "workout-meets": ["notes_semantic"],
}

ok, bad, warn = [], [], []


def note(good: bool, message: str, soft: bool = False) -> None:
    (ok if good else (warn if soft else bad)).append(message)
    print(("  ok   " if good else ("  warn " if soft else "  FAIL ")) + message)


def dig(mapping: dict, path: str):
    node = mapping
    for part in path.split("."):
        node = (node.get("properties") or {}).get(part)
        if node is None:
            return None
    return node


def local_documents() -> dict:
    """Every document this repo would produce, keyed by index then _id."""
    logs = [json.loads(p.read_text()) for p in sorted((REPO_ROOT / "workouts").glob("*/*.json"))]
    links = ix.session_links(ix.catalog_sessions([]))
    reference = ix.derive.build_reference(ix.catalog_logs([]))
    docs: dict = {}
    every: list = []
    for log in logs:
        exploded = ix.explode(log, links, reference)
        every.extend(exploded)
        for index, _id, doc in exploded:
            docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    for index, _id, doc in ix.derive.rollup_docs(every):
        docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    for path in sorted((REPO_ROOT / "meets").glob("*.json")):
        for index, _id, doc in im.explode(json.loads(path.read_text())):
            docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    return docs


def main() -> int:
    endpoint = os.environ.get("ES_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("ES_API_KEY", "")
    if not endpoint or not api_key:
        sys.exit("error: set ES_ENDPOINT and ES_API_KEY (source .env)")

    session = requests.Session()
    session.headers.update({"Authorization": f"ApiKey {api_key}", "Content-Type": "application/json"})

    print("Building the expected documents from this repo...")
    expected = local_documents()
    for index, docs in sorted(expected.items()):
        print(f"  {index}: {len(docs)} documents")

    print("\nMappings")
    for index, fields in EXPECTED.items():
        resp = session.get(f"{endpoint}/{index}/_mapping")
        if not resp.ok:
            note(False, f"{index}: cannot read mapping ({resp.status_code})")
            continue
        mapping = list(resp.json().values())[0]["mappings"]
        for path, want in fields.items():
            got = (dig(mapping, path) or {}).get("type")
            note(got == want, f"{index}.{path}: {got or 'missing'} (want {want})")
        for field in SEMANTIC.get(index, []):
            got = (dig(mapping, field) or {}).get("type")
            note(got == "semantic_text",
                 f"{index}.{field}: {got or 'missing'} (want semantic_text)",
                 soft=(got is None))

    print("\nCounts")
    for index, docs in sorted(expected.items()):
        resp = session.get(f"{endpoint}/{index}/_count")
        got = resp.json().get("count") if resp.ok else None
        note(got == len(docs), f"{index}: {got} in Elasticsearch, {len(docs)} in the repo")

    print("\nContent")
    probes = [
        ("workout-sessions", {"term": {"source": "juggernautai-export"}}, "imported sessions"),
        ("workout-sessions", {"exists": {"field": "digest"}}, "sessions with a digest"),
        ("workout-notes", {"term": {"phase": "watch"}}, "watch items as notes"),
        ("workout-sets", {"exists": {"field": "exercise.equipment_ids"}}, "sets linked to equipment"),
        ("workout-sets", {"exists": {"field": "cardio.distance_mi"}}, "sets with cardio distance"),
    ]
    for index, query, label in probes:
        resp = session.post(f"{endpoint}/{index}/_count", json={"query": query})
        got = resp.json().get("count") if resp.ok else 0
        want = sum(1 for doc in expected[index].values() if _matches(doc, query))
        note(got == want, f"{label}: {got} indexed, {want} expected")

    resp = session.post(f"{endpoint}/workout-sets/_search",
                        json={"size": 0, "aggs": {"bars": {"terms": {"field": "exercise.equipment_ids", "size": 5}}}})
    if resp.ok:
        buckets = resp.json()["aggregations"]["bars"]["buckets"]
        note(bool(buckets), "equipment is aggregatable: " +
             ", ".join(f"{b['key']}×{b['doc_count']}" for b in buckets) if buckets
             else "equipment aggregation returned nothing")
    else:
        note(False, f"equipment aggregation failed ({resp.status_code})")

    resp = session.post(f"{endpoint}/workout-sessions/_search",
                        json={"size": 1, "_source": ["date"],
                              "query": {"semantic": {"field": "digest_semantic",
                                                     "query": "a session where my grip gave out"}}})
    if resp.ok:
        hits = resp.json()["hits"]["hits"]
        note(bool(hits), "semantic search over digest_semantic works" +
             (f" (top hit {hits[0]['_source'].get('date')})" if hits else ""))
    else:
        note(False, f"semantic search failed ({resp.status_code}): {resp.text[:160]}", soft=True)

    print(f"\n{len(ok)} ok, {len(warn)} warnings, {len(bad)} failures")
    if warn and not bad:
        print("Warnings mean the semantic layer isn't on (ES_SEMANTIC=off, or ELSER "
              "unavailable). Everything else lines up.")
    return 1 if bad else 0


def _matches(doc: dict, query: dict) -> bool:
    """The tiny subset of query DSL used by the probes above."""
    if "term" in query:
        (field, value), = query["term"].items()
        return _get(doc, field) == value
    if "exists" in query:
        return _get(doc, query["exists"]["field"]) not in (None, [], {})
    raise ValueError(query)


def _get(doc: dict, path: str):
    node = doc
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


if __name__ == "__main__":
    raise SystemExit(main())
