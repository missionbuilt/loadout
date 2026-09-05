#!/usr/bin/env python3
"""Phase 1 mechanism probe: does the dashboard time picker reach an ES|QL card
whose index has no time field?

The Phase 1 plan rests on a `derive.py`-written `ironstack-signals` index with no
time field, on the theory that a card reading it is immune to the picker and so
its verdict cannot be made to lie. That theory has two possible failure modes and
this probe tells them apart:

  * the picker is ignored           -> the mechanism works, build on it
  * the picker's range filter is    -> the card empties at any narrow range,
    applied and matches nothing        which is worse than today

Creates a 3-doc scratch index with NO date field, and a scratch dashboard with two
custom-content cards side by side: one reading the scratch index, one reading
workout-sessions as the control. Narrow the picker and watch which one changes.

    cd ~/Projects/loadout
    source ~/Projects/ironstack-log/.env
    python3 ironstack/kibana/probe_notime.py            # create + import
    python3 ironstack/kibana/probe_notime.py --clean    # delete both, leave no trace

Writes one index named ironstack-probe-notime and one dashboard with the same id.
Touches nothing else. `prune.py --only ironstack-` WOULD match the dashboard, so
clean up rather than leaving it.
"""

from __future__ import annotations

import io
import json
import os
import sys

import requests

INDEX = "ironstack-probe-notime"
DASH_ID = "ironstack-probe-notime"

MIGRATION = {"coreMigrationVersion": "8.8.0", "typeMigrationVersion": "10.3.0"}

CARD = """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#171513;color:#ebe5d8;font-family:'JetBrains Mono',ui-monospace,Menlo,monospace;padding:14px 18px}
.eyebrow{font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:#a8211a;margin-bottom:8px}
.hero{font-size:44px;line-height:1;color:#ebe5d8}
.sub{font-size:12px;color:#8f8b84;margin-top:8px}
</style>
<div class="eyebrow">%(eyebrow)s</div>
{%% if rows.size == 0 %%}<div class="hero">0</div><div class="sub">no rows came back</div>
{%% else %%}<div class="hero">{{ rows[0]['n'].value }}</div><div class="sub">%(sub)s</div>{%% endif %%}
"""


def env(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set. `source ~/Projects/ironstack-log/.env`")
    return value


def panel(key: str, esql: str, eyebrow: str, sub: str, x: int) -> dict:
    return {
        "type": "custom_content",
        "embeddableConfig": {
            "esql_query": [esql],
            "template": CARD % {"eyebrow": eyebrow, "sub": sub},
            "hidePanelTitles": True,
        },
        "panelIndex": key,
        "gridData": {"x": x, "y": 0, "w": 24, "h": 8, "i": key},
    }


def build() -> dict:
    panels = [
        panel("probe-notime", f"FROM {INDEX} | STATS n = COUNT(*)",
              "no time field", "docs in ironstack-probe-notime", 0),
        panel("probe-control", "FROM workout-sessions | STATS n = COUNT(*)",
              "control, has @timestamp", "sessions in workout-sessions", 24),
    ]
    return {
        "id": DASH_ID,
        "type": "dashboard",
        "attributes": {
            "title": "Ironstack. PROBE no-time index",
            "description": "Phase 1 mechanism probe. Delete when the question is answered.",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": True}),
            "timeRestore": True, "timeFrom": "now-2y", "timeTo": "now",
            "refreshInterval": {"pause": True, "value": 60000},
            "version": 1,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})
            },
        },
        "references": [],
        **MIGRATION,
    }


def main() -> None:
    es, kibana, key = env("ES_ENDPOINT"), env("KIBANA_URL"), env("ES_API_KEY")
    es_headers = {"Authorization": f"ApiKey {key}", "Content-Type": "application/json"}
    kb_headers = {"Authorization": f"ApiKey {key}", "kbn-xsrf": "ironstack"}

    if "--clean" in sys.argv:
        r = requests.delete(f"{kibana}/api/saved_objects/dashboard/{DASH_ID}",
                            headers=kb_headers, timeout=60)
        print(f"dashboard delete -> {r.status_code} {r.text[:160]}")
        blocked = not r.ok
        r = requests.delete(f"{es}/{INDEX}", headers=es_headers, timeout=60)
        print(f"index delete     -> {r.status_code} {r.text[:200]}")
        if blocked:
            # Same wall prune.py hits: this serverless Kibana refuses saved-object
            # deletes over the API, as it refuses _find and the saved-objects GET.
            print("\nThis Kibana refuses API deletes. Remove it by hand:")
            print("  Stack Management > Saved Objects, search for")
            print(f"  {DASH_ID}")
            print("The index is gone either way, so the dashboard renders empty until then.")
        return

    # An explicit mapping, so this is a deliberate no-date index rather than one
    # that happens to have no dates in its sample.
    requests.delete(f"{es}/{INDEX}", headers=es_headers, timeout=60)
    r = requests.put(f"{es}/{INDEX}", headers=es_headers, timeout=60, json={
        "mappings": {"properties": {
            "signal": {"type": "keyword"},
            "verdict": {"type": "keyword"},
            "value": {"type": "double"},
        }}
    })
    if not r.ok:
        sys.exit(f"error: create index -> {r.status_code} {r.text[:400]}")

    bulk = io.StringIO()
    for sig, verdict, value in (("intensity", "heavier", 10.0),
                                ("load", "ramping", 1.37),
                                ("drift", "calves", 17.0)):
        bulk.write(json.dumps({"index": {"_index": INDEX}}) + "\n")
        bulk.write(json.dumps({"signal": sig, "verdict": verdict, "value": value}) + "\n")
    r = requests.post(f"{es}/_bulk?refresh=true", headers=es_headers, timeout=60,
                      data=bulk.getvalue())
    if not r.ok or r.json().get("errors"):
        sys.exit(f"error: bulk -> {r.status_code} {r.text[:400]}")
    print(f"indexed 3 docs into {INDEX}, no date field in the mapping")

    ndjson = json.dumps(build()).encode()
    r = requests.post(f"{kibana}/api/saved_objects/_import", params={"overwrite": "true"},
                      headers=kb_headers, timeout=120,
                      files={"file": ("probe.ndjson", ndjson, "application/ndjson")})
    if not r.ok:
        sys.exit(f"error: import -> {r.status_code} {r.text[:400]}")
    body = r.json()
    if body.get("errors"):
        sys.exit(f"error: import errors -> {json.dumps(body['errors'])[:600]}")
    print(f"imported {body.get('successCount', 0)} dashboard")
    print(f"\nopen: {kibana}/app/dashboards#/view/{DASH_ID}")
    print("Then set the picker to Last 15 minutes. The control should go to 0;")
    print("the no-time card tells us whether the mechanism holds.")


if __name__ == "__main__":
    main()
