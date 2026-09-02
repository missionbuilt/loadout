#!/usr/bin/env python3
"""Create (or update) the Ironstack indices in Elasticsearch.

Idempotent: safe to run on every deploy. Existing indices get a mapping
update (additive only); missing indices are created.

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
INDICES = ["workout-sessions", "workout-sets", "workout-notes"]

# Fields that gain a semantic_text sibling when semantic mode is on.
# source field -> semantic field (populated via copy_to)
SEMANTIC_FIELDS = {
    "workout-notes": {"text": "text_semantic"},
    "workout-sessions": {"wrap_up": "wrap_up_semantic"},
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


def put_index(session: requests.Session, endpoint: str, index: str, body: dict) -> requests.Response:
    exists = session.head(f"{endpoint}/{index}")
    if exists.status_code == 200:
        return session.put(f"{endpoint}/{index}/_mapping", json=body["mappings"])
    return session.put(f"{endpoint}/{index}", json=body)


def main() -> None:
    endpoint = env("ES_ENDPOINT")
    api_key = env("ES_API_KEY")
    semantic_mode = os.environ.get("ES_SEMANTIC", "auto").lower()

    session = requests.Session()
    session.headers.update(
        {"Authorization": f"ApiKey {api_key}", "Content-Type": "application/json"}
    )

    for index in INDICES:
        base = json.loads((MAPPINGS_DIR / f"{index}.json").read_text())
        attempts = []
        if semantic_mode in ("auto", "on"):
            attempts.append(("semantic", with_semantic(index, base)))
        if semantic_mode in ("auto", "off"):
            attempts.append(("plain", base))

        last = None
        for label, body in attempts:
            resp = put_index(session, endpoint, index, body)
            last = (label, resp)
            if resp.ok:
                print(f"{index}: ok ({label})")
                break
        else:
            label, resp = last
            sys.exit(f"error: {index} ({label}) -> {resp.status_code} {resp.text[:500]}")


if __name__ == "__main__":
    main()
