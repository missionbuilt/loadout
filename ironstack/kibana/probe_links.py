#!/usr/bin/env python3
"""Phase 4 probe: can a custom-content panel carry a working link?

templates.signal() says it cannot — "custom content panels render in a sandboxed iframe
with no scripts and no <a href>, so the Links panel is the only real door on the page" —
and the whole shape of the chrome follows from that: ASK THE COACH is a Kibana Links
panel sitting beside the nav, styled by Kibana, because a styled oxblood button inside
the brand bar was believed impossible.

Phase 4 wants that button. So the claim gets tested rather than inherited.

Four variants, side by side in one custom-content panel, plus a control:

    A  <a href target="_top">     navigates the whole page
    B  <a href target="_blank">   opens a tab
    C  <a href> with no target    navigates inside the iframe (may be blocked)
    D  a styled div               the control: looks identical, cannot be clicked

Each is drawn as the oxblood button Phase 4 wants, so the answer covers both questions
at once: does the link work, and does the button look right.

The coach link also carries ?q= so clicking it answers the second unknown — whether
Agent Builder accepts a pre-filled question in the URL.

    cd ~/Projects/loadout
    source ~/Projects/ironstack-log/.env
    python3 ironstack/kibana/probe_links.py            # create + import
    python3 ironstack/kibana/probe_links.py --clean    # remove it

Writes one dashboard, ironstack-probe-links. Touches nothing else. COACH_URL is read
from the environment and never printed.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import quote

import requests

DASH_ID = "ironstack-probe-links"
MIGRATION = {"coreMigrationVersion": "8.8.0", "typeMigrationVersion": "10.3.0"}

CARD = """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#171513;color:#ebe5d8;font-family:'JetBrains Mono',ui-monospace,Menlo,monospace;padding:16px 18px}
.eyebrow{font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:#a8211a;margin-bottom:14px}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.btn{display:inline-block;background:#a8211a;color:#ebe5d8;text-decoration:none;
     font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;
     padding:9px 16px;border:1px solid #a8211a}
.btn.ghost{background:transparent;color:#a8211a}
.note{font-size:11px;color:#8f8b84;margin-top:14px;line-height:1.7}
</style>
<div class="eyebrow">Phase 4 probe &mdash; which of these is clickable</div>
<div class="row">
<a class="btn" href="%(url)s" target="_top">A &middot; target=_top</a>
<a class="btn" href="%(url)s" target="_blank" rel="noopener">B &middot; target=_blank</a>
<a class="btn" href="%(url)s">C &middot; no target</a>
<span class="btn ghost">D &middot; div, the control</span>
</div>
<div class="note">A, B and C carry <b>?q=</b> with a test question, so a click also says
whether the coach accepts a pre-filled prompt. D is a span and must not be clickable &mdash;
if D "works", the test is measuring something else.</div>
"""


def env(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set. `source ~/Projects/ironstack-log/.env`")
    return value


def build(url: str) -> dict:
    panel = {
        "type": "custom_content",
        "embeddableConfig": {"template": CARD % {"url": url}, "hidePanelTitles": True},
        "panelIndex": "probe-links",
        "gridData": {"x": 0, "y": 0, "w": 48, "h": 8, "i": "probe-links"},
    }
    return {
        "id": DASH_ID, "type": "dashboard",
        "attributes": {
            "title": "Ironstack. PROBE links in a custom panel",
            "description": "Phase 4 probe. Delete when the question is answered.",
            "panelsJSON": json.dumps([panel]),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": True}),
            "timeRestore": True, "timeFrom": "now-1y", "timeTo": "now",
            "refreshInterval": {"pause": True, "value": 60000}, "version": 1,
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(
                {"query": {"query": "", "language": "kuery"}, "filter": []})},
        },
        "references": [], **MIGRATION,
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

    coach = env("IRONSTACK_COACH_URL")
    sep = "&" if "?" in coach else "?"
    url = f"{coach}{sep}q={quote('was my last deadlift session heavy for me')}"

    ndjson = json.dumps(build(url)).encode()
    r = requests.post(f"{kibana}/api/saved_objects/_import", params={"overwrite": "true"},
                      headers=headers, timeout=120,
                      files={"file": ("probe.ndjson", ndjson, "application/ndjson")})
    if not r.ok:
        sys.exit(f"error: import -> {r.status_code} {r.text[:400]}")
    body = r.json()
    if body.get("errors"):
        sys.exit(f"error: import errors -> {json.dumps(body['errors'])[:600]}")
    print(f"imported {body.get('successCount', 0)} dashboard")
    print(f"\nopen: {kibana}/app/dashboards#/view/{DASH_ID}")
    print("Click A, then B, then C. D must do nothing.")


if __name__ == "__main__":
    main()
