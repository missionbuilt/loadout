#!/usr/bin/env python3
"""Probe: the three questions Phase 0 of the Sept 6 design plan has to answer.

Three panels on one scratch dashboard, each a question about the custom-content
sandbox that nothing in this repo has asked. Every one of them gates a real change,
so each is tested rather than assumed - probe_links.py and probe_disclosure.py both
found the sanitizer doing something no one had predicted.

    P1  GROUND      body{background:transparent}
                    Does the iframe show Kibana's panel ground through it? If it does,
                    $BG becomes transparent and the warm-card-on-navy split on every
                    page ends in one line, and follows any future theme change for free.
                    If the sandbox paints it white or black, the fallback is the sampled
                    hex (#0d1627) as a token.

    P2  FONTS       @font-face with a base64 data: URI
                    Kibana's CSP sets no font-src, so a data: font SHOULD pass - but a
                    custom panel fetches nothing, and nothing has tried. Three faces,
                    each drawn twice: once through the embedded @font-face, once through
                    the fallback stack. If the pairs look the same, the fonts are blocked.

    P3  MULTIQUERY  esql_query as a list of two
                    custom() passes esql_query as a list. If a panel accepts more than
                    one query and exposes both to Liquid, the three Overview signal cards
                    can be one panel (one iframe, one shared height, no more measuring
                    three cards against each other). The panel prints what it was given.

Read the results in the browser, in a NEW TAB:

    P1  The panel ground reads "same as the panels around it" or it reads white/black.
    P2  Each row: LEFT is embedded, RIGHT is fallback. Different = fonts work.
        Oswald is a condensed grotesk; JetBrains Mono has a slashed zero and a wide
        lower-case; Merriweather has a large x-height and bracketed serifs.
    P3  "rows.size = N": 1 means only the first query ran, 3 only the second, 4 means
        they were concatenated. The other lines print candidate names for a second
        result set; whichever is non-empty is the name.

    cd ~/Projects/loadout
    set -a; source ~/Projects/ironstack-log/.env; set +a
    python3 ironstack/kibana/probe_phase0.py            # create + import
    python3 ironstack/kibana/probe_phase0.py --clean    # remove it (or Stack Management)

Writes one dashboard, ironstack-probe-phase0. Touches nothing else. P3 reads two rows
from workout-sessions and three from workout-meets and prints only their counts and a
session_id. Record all three answers in kibana/README.md whichever way they go.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import requests

DASH_ID = "ironstack-probe-phase0"
MIGRATION = {"coreMigrationVersion": "8.8.0", "typeMigrationVersion": "10.3.0"}
FONTS = Path(__file__).resolve().parent / "fonts"

BASE = """*{box-sizing:border-box;margin:0;padding:0}
body{color:#ebe5d8;font-family:Georgia,serif;padding:16px 18px;font-size:14px;line-height:1.55}
h1{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#8f8b84;margin-bottom:12px;font-weight:500}
.case{border-top:1px solid #2a2622;padding:12px 0}
.tag{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8f8b84;margin-bottom:6px}
.dim{color:#a8a094}
"""


def font_face(family: str, weight: int, file: str) -> str:
    data = base64.b64encode((FONTS / file).read_bytes()).decode()
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
            f"font-display:block;src:url(data:font/woff2;base64,{data}) format('woff2')}}\n")


# P1 ------------------------------------------------------------------------------------
GROUND = "<style>\n" + BASE + """body{background:transparent}
</style>
<h1>P1 &middot; ground &middot; body{background:transparent}</h1>
<p>If the ground behind this text is the <b>same navy as the panels around it</b>, the
iframe is transparent and $BG can be. If it is <b>white or black</b>, the sandbox paints
its own ground and the fallback is the sampled hex.</p>
<p class="dim" style="margin-top:8px">The text is chalk #ebe5d8 on purpose: it reads on
navy and on black, and it disappears on white, which is its own answer.</p>
"""

# P2 ------------------------------------------------------------------------------------
def fonts_card() -> str:
    faces = (font_face("Oswald", 700, "oswald-700.woff2")
             + font_face("JetBrains Mono", 500, "jetbrains-mono-500.woff2")
             + font_face("Merriweather", 400, "merriweather-400.woff2"))
    return "<style>\n" + BASE + faces + """
body{background:#0d1627}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:baseline}
.osw{font-family:'Oswald','Arial Narrow',sans-serif;font-weight:700;font-size:34px;text-transform:uppercase;letter-spacing:-.015em;line-height:1}
.osw.fb{font-family:'Arial Narrow','Helvetica Neue',Arial,sans-serif}
.mono{font-family:'JetBrains Mono',Menlo,monospace;font-weight:500;font-size:14px}
.mono.fb{font-family:Menlo,Consolas,monospace}
.ser{font-family:'Merriweather',Georgia,serif;font-size:15px}
.ser.fb{font-family:Georgia,'Times New Roman',serif}
</style>
<h1>P2 &middot; fonts &middot; left is embedded @font-face, right is the fallback stack</h1>
<div class="case"><div class="tag">Oswald 700 &middot; embedded / Arial Narrow</div>
<div class="pair"><div class="osw">872 lb &middot; Comp Bench</div><div class="osw fb">872 lb &middot; Comp Bench</div></div></div>
<div class="case"><div class="tag">JetBrains Mono 500 &middot; embedded / Menlo</div>
<div class="pair"><div class="mono">0O 1lI &middot; 185 &times; 5 @ 8 &middot; 2026-09-04</div><div class="mono fb">0O 1lI &middot; 185 &times; 5 @ 8 &middot; 2026-09-04</div></div></div>
<div class="case"><div class="tag">Merriweather 400 &middot; embedded / Georgia</div>
<div class="pair"><div class="ser">Heavier than 9 of your last 12 weeks, ranked per training day.</div><div class="ser fb">Heavier than 9 of your last 12 weeks, ranked per training day.</div></div></div>
<p class="dim" style="margin-top:10px">Pairs that look identical mean the data: font was
blocked. A Mac without Arial Narrow shows Helvetica on the right; the comparison still holds.</p>
"""

# P3 ------------------------------------------------------------------------------------
MULTI_QUERIES = [
    "FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP session_id",
    "FROM workout-meets | SORT @timestamp DESC | LIMIT 3 | KEEP meet_id",
]
MULTI = "<style>\n" + BASE + """body{background:#0d1627}
code{font-family:ui-monospace,Menlo,monospace;color:#ebe5d8}
</style>
<h1>P3 &middot; multi-query &middot; esql_query is a list of two</h1>
<p>Query 1 returns <b>1</b> row (a session_id). Query 2 returns <b>3</b> rows (meet_ids).</p>
<div class="case"><div class="tag">what Liquid was handed</div>
<p><code>rows.size = {{ rows.size }}</code> &nbsp; <span class="dim">1 = first only &middot; 3 = second only &middot; 4 = concatenated</span></p>
<p><code>rows[0].session_id = {{ rows[0]['session_id'].value }}</code> &nbsp; <code>rows[0].meet_id = {{ rows[0]['meet_id'].value }}</code></p>
</div>
<div class="case"><div class="tag">candidate names for a second result set (non-empty = that is the name)</div>
<p><code>results.size = {{ results.size }}</code> &nbsp; <code>queries.size = {{ queries.size }}</code> &nbsp; <code>data.size = {{ data.size }}</code></p>
<p><code>rows2.size = {{ rows2.size }}</code> &nbsp; <code>results[1].size = {{ results[1].size }}</code> &nbsp; <code>esql.size = {{ esql.size }}</code></p>
</div>
<p class="dim">If every candidate is empty and rows.size is 1 or 3, a panel takes one
query and the signal cards stay three panels. Record it either way.</p>
"""


def env(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def panel(index: str, x: int, y: int, w: int, h: int, template: str, esql: list[str]) -> dict:
    return {
        "type": "custom_content",
        "panelIndex": index,
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": index},
        "embeddableConfig": {"esql_query": esql, "template": template, "hidePanelTitles": True},
    }


def build() -> dict:
    panels = [
        panel("p1", 0, 0, 16, 9, GROUND, []),
        panel("p2", 16, 0, 32, 9, fonts_card(), []),
        panel("p3", 0, 9, 48, 8, MULTI, MULTI_QUERIES),
    ]
    return {
        "id": DASH_ID,
        "type": "dashboard",
        "managed": False,
        "attributes": {
            "title": "Ironstack. PROBE phase 0",
            "description": "Ground, fonts, multi-query. Delete when the three answers are in the README.",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "hidePanelTitles": False}),
            "timeRestore": True,
            "timeFrom": "now-10y", "timeTo": "now",
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})},
        },
        "references": [],
        **MIGRATION,
    }


def main() -> None:
    for f in ("oswald-700.woff2", "jetbrains-mono-500.woff2", "merriweather-400.woff2"):
        if not (FONTS / f).exists():
            sys.exit(f"error: {FONTS / f} is missing; the subsets live in kibana/fonts/")
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
    print(f"payload {len(ndjson) // 1024} KB (three faces embedded once: ~70 KB of it)")
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
    print("P1: is the ground navy, or white/black?  P2: do the pairs differ?  P3: rows.size = ?")


if __name__ == "__main__":
    main()
