#!/usr/bin/env python3
"""Check that what's in Elasticsearch matches what's in this repo.

    python ingest/verify_index.py

Rebuilds every document locally, then asks Elasticsearch three questions:
  1. Are the mappings the ones we intended (types, and the semantic_text siblings)?
  2. Are the counts right, index by index?
  3. Do sampled documents match the local ones field for field?

Question 3 used to be a claim rather than a check: local_documents() built every
expected document and then used it for len() and five count probes and nothing else,
so a wrong est_e1rm on every set in the cluster passed clean. It now samples ids per
index, _mget's them, and diffs them against the local copy field by field.

Exits non-zero if anything is off. Reads ES_ENDPOINT and ES_API_KEY from the
environment, same as the indexers.
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import index_workouts as ix
import index_meets as im
import setup_indices
from envconf import env_secret, env_url

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
    # The one index whose mapping correctness is load-bearing rather than cosmetic: a
    # single date-typed field here silently hands the Overview verdicts back to the
    # dashboard time picker. setup_indices guards the write; this checks what landed.
    "ironstack-signals": {
        "signal": "keyword",
        "computed_through": "keyword",
        "muscle": "keyword",
        "last_trained": "keyword",
        "first_trained": "keyword",
        "week_end": "keyword",
        "iso_week": "keyword",
        "month_s": "keyword",
        "cadence_days": "double",
        "acwr": "double",
        "acwr_off_layoff": "boolean",
        # taper. meet_date is the one most likely to drift back to a date type,
        # because it reads like one everywhere else in the repo.
        "cycle": "keyword",
        "cycle_label": "keyword",
        "meet_date": "keyword",
        "cycle_role": "keyword",
        "weeks_out": "integer",
        "week_state": "keyword",
        "top_pct": "double",
        "cum_tonnage_lb": "double",
        # block, tag and projection rows. peer_from / notes_from are the date-shaped
        # strings most likely to drift back to a date type.
        "block": "keyword",
        "block_role": "keyword",
        "ordinal": "integer",
        "heavy_per_session": "double",
        "peer_heavy_per_session": "double",
        "peer_from": "keyword",
        "tag": "keyword",
        "notes_from": "keyword",
        "notes_span_days": "integer",
        "platformed_pct": "double",
        "expected_lb": "double",
        "inol_hardest": "double",
        "inol_hardest_gloss": "keyword",
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
        "lift_name": "keyword",
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
        "acwr_off_layoff": "boolean",
        "chronic_days_trained": "integer",
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

# How many documents per index to pull back and compare field by field. Small enough
# that the whole check is one _mget per index, large enough that a systematic error -
# a formula change that moved every est_e1rm - cannot hide. Sampled fresh each run
# rather than from a fixed seed: a drift detector that always looks at the same 25
# documents only ever guards those 25.
SAMPLE_PER_INDEX = 25

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


def local_documents(today: date | None = None) -> dict:
    """Every document this repo would produce, keyed by index then _id."""
    # One clock for the whole comparison, for the same reason index_workouts.py takes
    # one for the whole run: rollup_docs and signal_docs each default to "now", so
    # calling them without one is two reads of the wall clock a few lines apart. A run
    # that straddles midnight would build a week marked in-progress on the rollup and
    # closed on the signal row and then report the cluster as drifted from itself.
    today = today or datetime.now(timezone.utc).date()
    # One corpus, walked by the indexer's own function. This used to glob("*/*.json")
    # while the indexer walked rglob("*.json"); they agreed only because every log
    # happens to sit at depth 2 today. The script whose entire job is catching drift
    # is the last place that should have a walk of its own.
    corpus = ix.catalog_logs()
    links = ix.session_links(sorted(((day, sid) for day, sid, _ in corpus),
                                    key=lambda pair: (pair[0], pair[1])))
    reference = ix.derive.build_reference(corpus)
    docs: dict = {}
    every: list = []
    for _day, _sid, log in sorted(corpus, key=lambda row: (row[0], row[1])):
        exploded = ix.explode(log, links, reference)
        every.extend(exploded)
        for index, _id, doc in exploded:
            docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    rollups = ix.derive.rollup_docs(every, today)
    for index, _id, doc in rollups:
        docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    for index, _id, doc in ix.derive.signal_docs(every, rollups, today):
        docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    for path in sorted((REPO_ROOT / "meets").glob("*.json")):
        for index, _id, doc in im.explode(json.loads(path.read_text())):
            docs.setdefault(index, {})[_id] = ix.strip_nones(doc)
    return docs


def cluster_stamp(session, endpoint: str) -> list[str]:
    """Every distinct `computed_through` in the signals index, newest first.

    One value is the healthy case: every row of a run carries that run's stamp, and
    sweep_signals deletes anything else. More than one means a sweep did not finish.
    None at all means the index is empty or unreachable.
    """
    resp = session.post(
        f"{endpoint}/{ix.derive.SIGNAL_INDEX}/_search",
        json={"size": 0, "aggs": {"stamps": {"terms": {"field": "computed_through",
                                                       "size": 10}}}})
    if not resp.ok:
        return []
    buckets = (resp.json().get("aggregations") or {}).get("stamps", {}).get("buckets", [])
    return sorted((b["key"] for b in buckets), reverse=True)


def as_of_date(session, endpoint: str, today: date) -> date:
    """The date to rebuild the repo's documents against, and a verdict on the clock.

    Everything in this script is a comparison between documents the repo builds NOW and
    documents the indexer built THEN, and several of them are functions of the date they
    were built on: `computed_through` is literally the date, the drift window's cutoff
    moves with it, `cadence_days` divides by a span that ends today, and which week is
    "in-progress" changes at midnight UTC. Rebuilding against the runner's own clock
    therefore reports the entire signals index as drifted whenever verification happens
    on a different UTC day from the indexing - which CI never sees, because both steps
    run seconds apart, and which anybody verifying an existing cluster by hand hits
    immediately. 275 rows of "computed_through: '2026-09-06' locally, '2026-09-05'
    indexed" says nothing about whether any FIELD is wrong.

    So the comparison is made against the date the cluster was actually indexed on, and
    the clock difference is reported once, as itself.
    """
    stamps = cluster_stamp(session, endpoint)
    if not stamps:
        note(False, f"{ix.derive.SIGNAL_INDEX}: no computed_through to read - the index "
                    f"is empty or unreadable; run python ingest/index_workouts.py")
        return today
    if len(stamps) > 1:
        note(False, f"{ix.derive.SIGNAL_INDEX}: {len(stamps)} different computed_through "
                    f"values ({', '.join(stamps)}) - a stale-row sweep did not finish, "
                    f"so rows from more than one run are live at once")
    stamp = date.fromisoformat(stamps[0])
    note(stamp == today,
         f"the cluster was indexed on {stamp.isoformat()} and today is "
         f"{today.isoformat()} UTC"
         + ("" if stamp == today else
            f" - every windowed row below is {(today - stamp).days} day(s) old. That is "
            f"staleness, not field drift: re-run python ingest/index_workouts.py. The "
            f"documents below are rebuilt against {stamp.isoformat()} so what is "
            f"compared is the data, not the clock."))
    return stamp


def differences(want, got, path: str = "") -> list[str]:
    """Every leaf where the local document and the indexed one disagree.

    Compared in both directions: a field the repo emits and the cluster does not have is
    the orphan case, and a field the cluster has and the repo does not is the leftover
    case. Both are drift, and only one of them shows up in a count.
    """
    if isinstance(want, dict) and isinstance(got, dict):
        out = []
        for key in sorted(set(want) | set(got)):
            out += differences(want.get(key), got.get(key), f"{path}.{key}" if path else key)
        return out
    if isinstance(want, list) and isinstance(got, list):
        if len(want) != len(got):
            return [f"{path}: {len(want)} item(s) locally, {len(got)} indexed"]
        out = []
        for i, (a, b) in enumerate(zip(want, got)):
            out += differences(a, b, f"{path}[{i}]")
        return out
    # 12.0 and 12 are the same number and Elasticsearch is entitled to hand back either.
    if isinstance(want, (int, float)) and isinstance(got, (int, float)) \
            and not isinstance(want, bool) and not isinstance(got, bool):
        return [] if float(want) == float(got) else [f"{path}: {want!r} locally, {got!r} indexed"]
    return [] if want == got else [f"{path}: {want!r} locally, {got!r} indexed"]


def compare_sample(session, endpoint: str, expected: dict) -> None:
    """Question 3, which until now the docstring only claimed.

    Counts catch documents that are missing or left over. They cannot catch a document
    that is present, countable, correctly typed and holding the wrong number - which is
    what a changed formula produces, on every document at once, in perfect silence.
    """
    for index, docs in sorted(expected.items()):
        ids = sorted(docs)
        if not ids:
            continue
        picked = random.sample(ids, min(SAMPLE_PER_INDEX, len(ids)))
        resp = session.post(
            f"{endpoint}/{index}/_mget",
            # The semantic_text siblings are populated by copy_to and inference; they are
            # in _source but are not something this repo produces, so comparing them would
            # report drift on every document.
            params={"_source_excludes": ",".join(SEMANTIC.get(index, []) or ["_none_"])},
            json={"ids": picked})
        if not resp.ok:
            note(False, f"{index}: could not fetch a sample ({resp.status_code})")
            continue
        missing, wrong = [], []
        for item in resp.json().get("docs", []):
            if not item.get("found"):
                missing.append(item["_id"])
                continue
            delta = differences(docs[item["_id"]], item.get("_source") or {})
            if delta:
                wrong.append((item["_id"], delta))
        if missing:
            note(False, f"{index}: {len(missing)} of {len(picked)} sampled document(s) "
                        f"are not in the cluster at all, e.g. {missing[0]}")
        if wrong:
            _id, delta = wrong[0]
            note(False, f"{index}: {len(wrong)} of {len(picked)} sampled document(s) "
                        f"differ from the repo. {_id}: "
                        + "; ".join(delta[:3])
                        + (f" (+{len(delta) - 3} more field(s))" if len(delta) > 3 else ""))
        if not missing and not wrong:
            note(True, f"{index}: {len(picked)} sampled document(s) match the repo "
                       f"field for field")


def main() -> int:
    if not os.environ.get("ES_ENDPOINT", "").strip() or not os.environ.get("ES_API_KEY", "").strip():
        sys.exit("error: set ES_ENDPOINT and ES_API_KEY (source .env)")
    # Same reading as the indexers: the endpoint loses a trailing slash, the key never
    # does. This script used to strip neither, so a newline picked up from `source .env`
    # failed verification against a cluster the indexer had just written successfully.
    endpoint = env_url("ES_ENDPOINT")
    api_key = env_secret("ES_API_KEY")

    session = requests.Session()
    session.headers.update({"Authorization": f"ApiKey {api_key}", "Content-Type": "application/json"})

    # Which day to rebuild against, before anything is built: see as_of_date().
    print("Clock")
    as_of = as_of_date(session, endpoint, datetime.now(timezone.utc).date())

    print("\nBuilding the expected documents from this repo...")
    expected = local_documents(as_of)
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

    # The signals index is range-proof only while it has no date field. Everything else
    # here checks that a type is right; this checks that a type is absent.
    resp = session.get(f"{endpoint}/{ix.derive.SIGNAL_INDEX}/_mapping")
    if resp.ok:
        live = list(resp.json().values())[0]["mappings"]
        # Recurse the same way setup_indices does. The index is flat today, and a flat
        # scan here would be the thing that stops being true first.
        dated = setup_indices._date_fields(live.get("properties"))
        note(not dated,
             f"{ix.derive.SIGNAL_INDEX}: no date-typed field"
             + (f", but found {', '.join(dated)} - the time picker can reach the "
                f"Overview verdicts again" if dated else ""))
        # And that the cluster still refuses to invent one. This is the check the repo
        # cannot make for itself: setup_indices validates the file, this validates what
        # Elasticsearch was actually left holding.
        note(live.get("date_detection") is False,
             f"{ix.derive.SIGNAL_INDEX}: date_detection off "
             f"(live: {live.get('date_detection')}) - on, an undeclared field holding "
             f"a date string is mapped as a date")
        note(live.get("dynamic") == "strict",
             f"{ix.derive.SIGNAL_INDEX}: dynamic strict "
             f"(live: {live.get('dynamic')}) - otherwise an undeclared field is mapped "
             f"silently instead of rejected")
    else:
        note(False, f"{ix.derive.SIGNAL_INDEX}: cannot read mapping ({resp.status_code})")

    print("\nCounts")
    # Refresh first. In CI this runs seconds after index_workouts.py, whose bulk write
    # sends no refresh, so an unrefreshed _count is a race: the documents are in the
    # cluster and not yet in the searchable view, and the verifier reports a mismatch
    # (or, worse, a stale match) that has nothing to do with the repo.
    indices = ",".join(sorted(expected))
    resp = session.post(f"{endpoint}/{indices}/_refresh")
    if not resp.ok:
        note(False, f"could not refresh {indices} before counting ({resp.status_code}) "
                    f"- the counts below may be a race, not a drift")
    for index, docs in sorted(expected.items()):
        resp = session.get(f"{endpoint}/{index}/_count")
        got = resp.json().get("count") if resp.ok else None
        note(got == len(docs), f"{index}: {got} in Elasticsearch, {len(docs)} in the repo"
             + ("" if got == len(docs) else
                f" - fix with: python ingest/setup_indices.py --recreate {index} && "
                f"python ingest/index_workouts.py && python ingest/index_meets.py. "
                f"Recreating {index} loses nothing: this repo is the source of truth "
                f"and every document in it is rebuilt from workouts/ and meets/"))

    print("\nSampled documents")
    compare_sample(session, endpoint, expected)

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
