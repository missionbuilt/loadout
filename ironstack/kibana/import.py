#!/usr/bin/env python3
"""Import the Ironstack dashboards into Kibana.

    export KIBANA_URL=https://my-project.kb.us-east4.gcp.elastic.cloud
    export ES_API_KEY=...          # never paste a key into a chat; set it in your shell
    python kibana/import.py        # imports kibana/dashboards.ndjson, overwriting by id

Uses the saved objects import API with overwrite=true, so re-importing after
`build_dashboards.py` is safe: the fixed ids mean drilldowns and bookmarks
keep working. Works on Elastic Cloud Serverless and self-managed Kibana.

The API key needs Kibana privileges for saved objects (Serverless: a key
created from the project's API keys page has them). Nothing else is sent.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

NDJSON = Path(__file__).resolve().parent / "dashboards.ndjson"


def env(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def main() -> None:
    kibana = env("KIBANA_URL")
    api_key = env("ES_API_KEY")
    if not NDJSON.exists():
        sys.exit(f"error: {NDJSON} not found. Run kibana/build_dashboards.py first.")

    resp = requests.post(
        f"{kibana}/api/saved_objects/_import",
        params={"overwrite": "true"},
        headers={"Authorization": f"ApiKey {api_key}", "kbn-xsrf": "ironstack"},
        files={"file": (NDJSON.name, NDJSON.read_bytes(), "application/ndjson")},
        timeout=120,
    )
    if not resp.ok:
        sys.exit(f"error: import failed -> {resp.status_code} {resp.text[:800]}")

    body = resp.json()
    counts: dict[str, int] = {}
    for obj in body.get("successResults", []):
        counts[obj["type"]] = counts.get(obj["type"], 0) + 1
    summary = ", ".join(f"{n} {t}" for t, n in sorted(counts.items())) or "nothing"
    print(f"imported {body.get('successCount', 0)} object(s): {summary}")

    errors = body.get("errors", [])
    if errors:
        print(f"\n{len(errors)} object(s) failed:")
        for e in errors[:20]:
            print(f"  {e.get('type')}/{e.get('id')}: {json.dumps(e.get('error'))[:300]}")
        sys.exit(1)

    print(f"\nopen: {kibana}/app/dashboards#/view/ironstack-overview")


if __name__ == "__main__":
    main()
