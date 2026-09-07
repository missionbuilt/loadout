#!/usr/bin/env python3
"""Import the Ironstack dashboards into Kibana.

    export KIBANA_URL=https://my-project.kb.us-east4.gcp.elastic.cloud
    export ES_API_KEY=...          # never paste a key into a chat; set it in your shell
    python kibana/import.py        # imports kibana/dashboards.ndjson, overwriting by id

Refuses an artifact with no ASK THE COACH or no projected-total reference line unless
--no-coach / --no-meet-max says so, and prints which of the two the file contains and
when it was built. The build has the same guards; this one is here because the build
refusing is not the same as the import not happening.

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
from datetime import datetime
from pathlib import Path

import requests

NDJSON = Path(__file__).resolve().parent / "dashboards.ndjson"


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


def features(raw: str) -> tuple[bool, bool]:
    """What the artifact on disk actually contains, read from the artifact.

    Not from the environment. The environment is what the BUILD reads, and the two are
    only the same when the build succeeded - which is exactly the case that failed on
    2026-09-06: `build_dashboards.py` refused for an unset IRONSTACK_MEET_MAX_LB, wrote
    nothing, and the `import.py` on the next line of the same paste imported the stale
    file underneath it. Two commands, one intention, and only the first one had a guard.
    """
    # Not "is there a reference line anywhere" - the first version of this test said
    # yes on the public artifact, because History's ACWR chart carries a BASELINE line of
    # its own. The projected-total title is the one string build_dashboards.py writes
    # only when IRONSTACK_MEET_MAX_LB is set, so it is the thing to look for.
    # The title is sentence case since Phase 3 of the design plan ("Projected total by
    # week, against your meet best of 909 lb"); the old all-caps string made this
    # importer refuse a build that had the line. Read the title the build writes.
    return ("ASK THE COACH" in raw, "against your meet best of" in raw)


def main() -> None:
    kibana = env_url("KIBANA_URL")
    api_key = env_secret("ES_API_KEY")
    if not NDJSON.exists():
        sys.exit(f"error: {NDJSON} not found. Run kibana/build_dashboards.py first.")

    raw = NDJSON.read_text()
    has_coach, has_ref = features(raw)
    stamp = datetime.fromtimestamp(NDJSON.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    print(f"importing {NDJSON.name} (built {stamp}): ASK THE COACH "
          + ("on" if has_coach else "OFF")
          + " | projected-total reference line " + ("on" if has_ref else "OFF"))

    # The same refusal shape as the build, one step later, because this is the step that
    # actually reaches the lifter. Both opt-outs stay legitimate - the committed artifact
    # is the public one and importing it deliberately is a real thing to want.
    missing = []
    if not has_coach and "--no-coach" not in sys.argv[1:]:
        missing.append(("ASK THE COACH", "ASK THE COACH",
                        "--no-coach", "IRONSTACK_COACH_URL"))
    if not has_ref and "--no-meet-max" not in sys.argv[1:]:
        missing.append(("reference line on the projected-total chart",
                        "the projected-total reference line",
                        "--no-meet-max", "IRONSTACK_MEET_MAX_LB"))
    if missing:
        lines = [f"error: {NDJSON.name} has no "
                 + " and no ".join(m[0] for m in missing) + ", so importing it"]
        lines.append("       would take " + ("them" if len(missing) > 1 else "it")
                     + " off every dashboard in this deployment.")
        for _short, long, flag, var in missing:
            lines.append(f"       Set {var} and re-run build_dashboards.py, or pass {flag}")
            lines.append(f"       here if importing without {long} is what you meant.")
        lines.append("       Nothing was imported.")
        sys.exit("\n".join(lines))

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
