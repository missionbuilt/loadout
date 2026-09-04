#!/usr/bin/env python3
"""Create (or update) the Ironstack indices in Elasticsearch.

Idempotent: safe to run on every deploy. Existing indices get a mapping
update (additive only); missing indices are created.

Some mapping changes cannot be applied in place: Elasticsearch will not change a
field's type on a live index (watch_items went keyword -> text, for one). When that
happens this script says so and stops. Pass --recreate to delete and rebuild the
affected indices — safe here because every document is rebuilt from the repo by
index_workouts.py / index_meets.py with deterministic ids:

    python ingest/setup_indices.py --recreate workout-sessions
    python ingest/index_workouts.py

Semantic search (ELSER via semantic_text) is optional by design:
  ES_SEMANTIC=auto  (default) try semantic mappings, fall back to plain
  ES_SEMANTIC=on    require semantic mappings, fail loudly if unsupported
  ES_SEMANTIC=off   plain mappings only (works on any Elastic, free tier included)

Env:
  ES_ENDPOINT  e.g. https://my-project.es.us-east4.gcp.elastic.cloud:443
  ES_API_KEY   an API key with index-management privileges
"""

import copy
import json
import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPINGS_DIR = REPO_ROOT / "schema" / "mappings"
INDICES = ["workout-sessions", "workout-sets", "workout-notes", "workout-meets",
           "workout-daily", "workout-weekly"]

# Fields that gain a semantic_text sibling when semantic mode is on.
# source field -> semantic field (populated via copy_to)
SEMANTIC_FIELDS = {
    "workout-notes": {"text": "text_semantic"},
    "workout-sets": {"notes": "notes_semantic"},
    "workout-meets": {"notes": "notes_semantic"},
    "workout-sessions": {
        "wrap_up": "wrap_up_semantic",
        "gear_notes": "gear_notes_semantic",
        "watch_items": "watch_semantic",
        # `digest` is the whole session written out as a paragraph by the indexer.
        # It is the field to search when the question is about a session rather
        # than a sentence: "how did I feel training in Las Vegas?"
        "digest": "digest_semantic",
    },
}


def env(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def with_semantic(index: str, body: dict) -> dict:
    semantic = SEMANTIC_FIELDS.get(index)
    if not semantic:
        return body
    body = copy.deepcopy(body)
    props = body["mappings"]["properties"]
    for source, target in semantic.items():
        props[source]["copy_to"] = target
        props[target] = {"type": "semantic_text"}
    return body


def put_index(session: requests.Session, endpoint: str, index: str, body: dict,
              recreate: bool = False) -> requests.Response:
    exists = session.head(f"{endpoint}/{index}").status_code == 200
    if exists and recreate:
        session.delete(f"{endpoint}/{index}")
        exists = False
    if exists:
        return session.put(f"{endpoint}/{index}/_mapping", json=body["mappings"])
    return session.put(f"{endpoint}/{index}", json=body)


def is_type_conflict(resp: requests.Response) -> bool:
    """A mapping change Elasticsearch will not make in place."""
    return resp.status_code == 400 and "cannot be changed from type" in resp.text


def main() -> None:
    argv = sys.argv[1:]
    recreate_all = "--recreate" in argv
    named = [a for a in argv if not a.startswith("--")]

    endpoint = env("ES_ENDPOINT")
    api_key = env("ES_API_KEY")
    semantic_mode = os.environ.get("ES_SEMANTIC", "auto").lower()

    session = requests.Session()
    session.headers.update(
        {"Authorization": f"ApiKey {api_key}", "Content-Type": "application/json"}
    )

    conflicts = []
    for index in INDICES:
        recreate = recreate_all and (not named or index in named)
        base = json.loads((MAPPINGS_DIR / f"{index}.json").read_text())
        attempts = []
        if semantic_mode in ("auto", "on"):
            attempts.append(("semantic", with_semantic(index, base)))
        if semantic_mode in ("auto", "off"):
            attempts.append(("plain", base))

        last = None
        for label, body in attempts:
            resp = put_index(session, endpoint, index, body, recreate)
            last = (label, resp)
            if resp.ok:
                print(f"{index}: ok ({label}{', recreated' if recreate else ''})")
                break
        else:
            label, resp = last
            if is_type_conflict(resp):
                conflicts.append(index)
                print(f"{index}: needs a rebuild — a field's type changed and "
                      "Elasticsearch won't do that in place")
                continue
            sys.exit(f"error: {index} ({label}) -> {resp.status_code} {resp.text[:500]}")

    if conflicts:
        names = " ".join(conflicts)
        sys.exit(
            "\nNothing was changed on: " + names + "\n"
            "Every document in these indices is rebuilt from this repo, so deleting and\n"
            "recreating them loses nothing. To do that:\n\n"
            f"    python ingest/setup_indices.py --recreate {names}\n"
            "    python ingest/index_workouts.py\n"
            "    python ingest/index_meets.py\n"
        )


if __name__ == "__main__":
    main()
