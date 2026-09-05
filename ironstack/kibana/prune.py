#!/usr/bin/env python3
"""List (and optionally delete) Ironstack saved objects no dashboard references.

    export KIBANA_URL=...  ES_API_KEY=...        # same shell the import uses
    python kibana/prune.py                       # dry run, lists orphans
    python kibana/prune.py --only ironstack-lens-,ironstack-map-   # scope the list
    python kibana/prune.py --only ... --delete   # delete, after writing a backup

Safe by design: the keep-set is read from kibana/dashboards.ndjson, which is the
same file import.py just pushed, and anything not in it is only reported unless
--delete is passed. Objects whose id does not start with "ironstack-" are never
touched, so hand-built dashboards and their panels are left alone.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

NDJSON = Path(__file__).resolve().parent / "dashboards.ndjson"
PREFIX = "ironstack-"
# index-pattern is on the list because the build stopped emitting two data views on
# 2026-09-05 (ironstack-dv-daily and ironstack-dv-meets, which nothing pointed at). They
# still exist in any Kibana that imported an earlier build, and an orphaned data view is
# a saved object a user has to look at and wonder about. Deleting one is only ever done
# with --only and --delete, and only for ids starting with "ironstack-".
TYPES = ["lens", "map", "visualization", "search", "index-pattern"]


def env_url(name: str) -> str:
    """A URL: trailing slash is noise, and stripping it makes f-strings safe."""
    value = os.environ.get(name, "").strip().rstrip("/")
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def env_secret(name: str) -> str:
    """A key: strip whitespace and nothing else.

    "/" is in the base64 alphabet an Elastic API key is drawn from, so the
    rstrip("/") that is right for a URL silently truncated a key that happened to
    end in one - and the cluster answered 401 with nothing pointing at the cause.
    Same helper pair as ingest/envconf.py, for the same reason.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"error: {name} is not set")
    return value


def main() -> None:
    kibana, api_key = env_url("KIBANA_URL"), env_secret("ES_API_KEY")
    if not NDJSON.exists():
        sys.exit(f"error: {NDJSON} not found. Run kibana/build_dashboards.py first.")

    keep = {(o["type"], o["id"]) for o in
            (json.loads(line) for line in NDJSON.read_text().splitlines() if line.strip())}
    print(f"{len(keep)} objects in {NDJSON.name}")

    headers = {"Authorization": f"ApiKey {api_key}", "kbn-xsrf": "true",
               "x-elastic-internal-origin": "kibana", "Content-Type": "application/json"}

    # Serverless disables the public _find API, so enumeration goes through _export,
    # which returns one JSON object per line and is the same API import.py's twin uses.
    def export(kinds: list[str]) -> list[dict]:
        r = requests.post(f"{kibana}/api/saved_objects/_export", headers=headers, timeout=120,
                          json={"type": kinds, "excludeExportDetails": True})
        if not r.ok:
            print(f"  _export {kinds} -> {r.status_code}: {r.text[:400]}")
            return []
        out = []
        for line in r.text.splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    live = export(TYPES)
    if not live:                       # one unsupported type fails the whole export
        for kind in TYPES:
            got = export([kind])
            print(f"  {kind:<14} {len(got)}")
            live.extend(got)
    if not live:
        sys.exit("error: could not enumerate saved objects. The response above says why.")
    print(f"{len(live)} object(s) in Kibana")

    only = None
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            only = tuple(p.strip() for p in sys.argv[i + 1].split(",") if p.strip())

    orphans = [o for o in live
               if o["id"].startswith(PREFIX) and (o["type"], o["id"]) not in keep
               and (only is None or o["id"].startswith(only))]
    held = [o for o in live
            if o["id"].startswith(PREFIX) and (o["type"], o["id"]) not in keep
            and only is not None and not o["id"].startswith(only)]
    skipped = [o for o in live
               if not o["id"].startswith(PREFIX) and (o["type"], o["id"]) not in keep]

    if skipped:
        print(f"\n{len(skipped)} unreferenced object(s) NOT built by this repo, left alone:")
        for o in skipped:
            print(f"  {o['type']:<14} {o['id']}  {o['attributes'].get('title', '')}")

    if not orphans:
        print("\nnothing to prune")
        return

    print(f"\n{len(orphans)} orphaned Ironstack object(s):")
    for o in orphans:
        print(f"  {o['type']:<14} {o['id']:<34} {o['attributes'].get('title', '')}")

    if held:
        print(f"\n{len(held)} more orphan(s) held back by --only:")
        for o in held:
            print(f"  {o['type']:<14} {o['id']:<34} {o['attributes'].get('title', '')}")

    if "--delete" not in sys.argv:
        print("\ndry run. re-run with --delete to remove them.")
        return

    # Deletion is permanent and some of these are not regenerable from this repo, so
    # everything is written to an importable NDJSON first. Restore with import.py
    # pointed at that file, or Saved Objects > Import in the UI.
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = Path(__file__).resolve().parent / f"pruned-backup-{stamp}.ndjson"
    ids = [{"type": o["type"], "id": o["id"]} for o in orphans]
    r = requests.post(f"{kibana}/api/saved_objects/_export", headers=headers, timeout=120,
                      json={"objects": ids, "includeReferencesDeep": True,
                            "excludeExportDetails": True})
    if not r.ok or not r.text.strip():
        sys.exit(f"error: backup export failed ({r.status_code}), refusing to delete.\n{r.text[:300]}")
    backup.write_text(r.text)
    print(f"\nbacked up {len(r.text.splitlines())} object(s) to {backup.name}")

    blocked = False
    for o in orphans:
        r = requests.delete(f"{kibana}/api/saved_objects/{o['type']}/{o['id']}",
                            headers=headers, timeout=60)
        if r.ok:
            print(f"  deleted  {o['id']}")
        else:
            blocked = True
            print(f"  FAILED {r.status_code}  {o['id']}  {r.text[:160]}")
    if blocked:
        print("\nThis Kibana refuses API deletes. Delete them in the UI instead:")
        print("  Stack Management > Saved Objects, paste each id into the search box.")


if __name__ == "__main__":
    main()
