#!/usr/bin/env python3
"""Probe: can a custom-content panel hide its provenance behind a disclosure?

The Overview Signal cards carry 60-90 words of provenance each, permanently on screen,
three across. That is ~250 words above the fold on the page whose whole job is three
sentences. The text is load-bearing - it is what makes the number defensible instead of
decorative - so the answer is to move it, not delete it.

Every obvious mechanism is a question about Kibana's sanitizer, and probe_links.py
already proved that sanitizer removes elements outright rather than just disabling them:
`<a href>` came back as bare text having lost even its class. So the mechanisms get
tested rather than assumed. Five variants in one panel:

    A  <details>/<summary>        native disclosure, no script. The one we want.
    B  checkbox + :checked        pure-CSS toggle, if <details> is stripped
    C  :hover reveal              CSS only, but dead on touch and to a keyboard
    D  title="" attribute         the browser's own tooltip
    E  plain visible text         the control - proves the panel rendered at all

Read the result in the browser:

    A works  -> click the summary and the paragraph appears. Ship A.
    B works  -> click the box and the paragraph appears. Ship B, note the a11y cost.
    C works  -> hover the card and the paragraph appears.
    D works  -> hover the dotted text and the OS tooltip appears after a beat.
    E only   -> the sanitizer allows none of them; shorten the copy instead.

    cd ~/Projects/loadout
    set -a; source /path/to/your-workout-log/.env; set +a
    python3 ironstack/kibana/probe_disclosure.py            # create + import
    python3 ironstack/kibana/probe_disclosure.py --clean    # remove it

Writes one dashboard, ironstack-probe-disclosure. Touches nothing else. Read-only
against your data: the panel carries no query at all, so no Liquid runs and nothing is
read from any index.
"""

from __future__ import annotations

import json
import os
import sys

import requests

DASH_ID = "ironstack-probe-disclosure"
MIGRATION = {"coreMigrationVersion": "8.8.0", "typeMigrationVersion": "10.3.0"}

# The real paragraph, so the answer is about the length this actually has to carry.
PROV = ("Heavy means heavy for you now. Every logging app measures a set against an "
        "all-time PR, so a lifter back from a layoff sees everything as light. This "
        "measures it against the trailing 90 days. Main lifts only.")

CARD = """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#171513;color:#ebe5d8;font-family:'JetBrains Mono',ui-monospace,Menlo,monospace;padding:18px 20px;font-size:12px;line-height:1.6}
h1{font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:#a8211a;margin-bottom:16px;font-weight:500}
.case{border-top:1px solid #2a2622;padding:14px 0}
.tag{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#8f8b84;margin-bottom:8px}
.prov{color:#a8a094;margin-top:8px}
summary{cursor:pointer;color:#8f8b84;font-size:10px;letter-spacing:.14em;text-transform:uppercase}
/* B: the checkbox itself is off-screen; its label is the control. */
.tog{position:absolute;left:-9999px}
.tog + label{cursor:pointer;color:#8f8b84;font-size:10px;letter-spacing:.14em;text-transform:uppercase}
.tog ~ .body{display:none}
.tog:checked ~ .body{display:block}
/* C */
.hov .body{display:none}
.hov:hover .body{display:block}
/* D */
.tip{border-bottom:1px dotted #8f8b84;cursor:help}
</style>
<h1>Disclosure probe &middot; which of these survives the sanitizer</h1>

<div class="case">
  <div class="tag">A &middot; details / summary</div>
  <details>
    <summary>How this is measured</summary>
    <div class="prov">__PROV__</div>
  </details>
</div>

<div class="case">
  <div class="tag">B &middot; checkbox + :checked</div>
  <input class="tog" type="checkbox" id="b1">
  <label for="b1">How this is measured</label>
  <div class="body"><div class="prov">__PROV__</div></div>
</div>

<div class="case hov">
  <div class="tag">C &middot; :hover reveal &mdash; hover this block</div>
  <div class="body"><div class="prov">__PROV__</div></div>
</div>

<div class="case">
  <div class="tag">D &middot; title attribute</div>
  <span class="tip" title="__PROV__">How this is measured &mdash; hover me</span>
</div>

<div class="case">
  <div class="tag">E &middot; control, plain text</div>
  <div class="prov">__PROV__</div>
</div>
""".replace("__PROV__", PROV)


def env(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def build() -> dict:
    panel = {
        "type": "custom_content",
        "panelIndex": "p1",
        "gridData": {"x": 0, "y": 0, "w": 24, "h": 26, "i": "p1"},
        "embeddableConfig": {"esql_query": [], "template": CARD, "hidePanelTitles": True},
    }
    return {
        "id": DASH_ID,
        "type": "dashboard",
        "managed": False,
        "attributes": {
            "title": "Ironstack. PROBE disclosure",
            "description": "Sanitizer probe. Delete when the question is answered.",
            "panelsJSON": json.dumps([panel]),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
            "timeRestore": False,
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})},
        },
        "references": [],
        **MIGRATION,
    }


def main() -> None:
    kibana, key = env("KIBANA_URL"), env("ES_API_KEY")
    headers = {"Authorization": f"ApiKey {key}", "kbn-xsrf": "ironstack"}

    if "--clean" in sys.argv:
        r = requests.delete(f"{kibana}/api/saved_objects/dashboard/{DASH_ID}",
                            headers=headers, timeout=60)
        print(f"dashboard delete -> {r.status_code}")
        if not r.ok:
            print("  serverless refuses this over the API; remove it in Stack Management")
        return

    ndjson = json.dumps(build()).encode()
    r = requests.post(f"{kibana}/api/saved_objects/_import", params={"overwrite": "true"},
                      headers=headers, timeout=120,
                      files={"file": ("probe.ndjson", ndjson, "application/ndjson")})
    if not r.ok:
        sys.exit(f"error: import -> {r.status_code} {r.text[:400]}")
    body = r.json()
    if body.get("errors"):
        sys.exit(f"error: import errors -> {json.dumps(body['errors'])[:600]}")
    print(f"imported {body.get('successCount', 0)} dashboard")
    print(f"\nopen in a NEW TAB: {kibana}/app/dashboards#/view/{DASH_ID}")
    print("A: click the summary. B: click the label. C: hover the block.")
    print("D: hover the dotted text. E must always be visible.")


if __name__ == "__main__":
    main()
