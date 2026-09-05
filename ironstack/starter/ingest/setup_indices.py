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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from envconf import env_secret, env_url  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPINGS_DIR = REPO_ROOT / "schema" / "mappings"
INDICES = ["workout-sessions", "workout-sets", "workout-notes", "workout-meets",
           "workout-daily", "workout-weekly", "ironstack-signals"]

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


# The signals index is only range-proof for as long as it has no date field. That is a
# property of a JSON file, which is exactly the kind of thing that gets edited back by
# someone adding an innocent computed_at. Nothing else in the stack would complain: the
# index would build, the cards would render, and the time picker would quietly start
# filtering the verdicts again. So it is checked here, where the mapping is applied.
NO_DATE_INDICES = ("ironstack-signals",)


def _date_fields(props: dict, prefix: str = "") -> list[str]:
    """Every date-typed field, however deeply nested.

    A flat scan of top-level properties reads as coverage and is not: a date inside an
    object field, or in a multi-field `fields` block, would sail straight past it.
    """
    found = []
    for name, spec in (props or {}).items():
        path = f"{prefix}{name}"
        if spec.get("type") in ("date", "date_nanos"):
            found.append(path)
        found.extend(_date_fields(spec.get("properties"), f"{path}."))
        found.extend(_date_fields(spec.get("fields"), f"{path}."))
    return sorted(found)


def check_no_date_fields(index: str, body: dict) -> None:
    mappings = body["mappings"]
    # The declared properties are only half the guarantee. Elasticsearch maps what it
    # is SENT, so a field the repo forgot to declare - meet_date, say, holding
    # "2026-10-24" - gets auto-detected as a date, and the picker reaches these rows
    # again with nothing in the repo to show for it. Both settings close that door:
    # date_detection off so a date-shaped string stays a string, strict so an
    # undeclared field is a rejected document in CI rather than a silent new mapping.
    missing = [
        f"{key}: {want}"
        for key, want in (("date_detection", False), ("dynamic", "strict"))
        if mappings.get(key) != want
    ]
    if missing:
        sys.exit(
            f"error: {index} must set {', '.join(missing)} in its mapping.\n"
            f"       Without them a field this repo never declared can still be mapped "
            f"as a date,\n"
            f"       which is the one thing this index exists to prevent. See "
            f"schema/mappings/{index}.json."
        )
    dated = _date_fields(mappings.get("properties"))
    if dated:
        sys.exit(
            f"error: {index} must not carry a date-typed field, and {', '.join(dated)} "
            f"is one.\n"
            f"       A date field is how Kibana applies the dashboard time picker to an "
            f"ES|QL card.\n"
            f"       With one here, the Overview verdicts become re-scopable again and "
            f"nothing visibly breaks.\n"
            f"       Store dates as keyword strings in this index. See "
            f"schema/mappings/{index}.json."
        )


def is_type_conflict(resp: requests.Response) -> bool:
    """A mapping change Elasticsearch will not make in place.

    A field's `format` is as unchangeable as its type - @timestamp gaining an explicit
    strict_date_time format is rejected the same way - and it deserves the same
    "rebuild it, the repo is the source of truth" message rather than a raw 400.
    """
    if resp.status_code != 400:
        return False
    return ("cannot be changed from type" in resp.text
            or "Cannot update parameter [format]" in resp.text)


def main() -> None:
    argv = sys.argv[1:]
    recreate_all = "--recreate" in argv
    named = [a for a in argv if not a.startswith("--")]

    # Arguments first, before anything reaches for a credential: a typo has to be an
    # error here, not a no-op that talks to a cluster. `--recreate workout-sesions`
    # matched no index, recreated nothing, and still printed "ok (plain)" for all
    # seven - a rebuild that silently did not happen, reported as a success.
    unknown = [name for name in named if name not in INDICES]
    if unknown:
        sys.exit(f"error: no such index: {', '.join(unknown)}\n"
                 f"       known indices: {', '.join(INDICES)}")
    if named and not recreate_all:
        sys.exit(f"error: {', '.join(named)} was named without --recreate, and this "
                 f"script has no other use for an index name.\n"
                 f"       Run it with no arguments to update every mapping, or with "
                 f"--recreate {' '.join(named)} to rebuild those.")

    endpoint = env_url("ES_ENDPOINT")
    # Never rstrip("/") an API key: "/" is in the base64 alphabet, so a key ending in
    # one was quietly truncated here and the cluster answered 401 with no explanation.
    api_key = env_secret("ES_API_KEY")
    semantic_mode = os.environ.get("ES_SEMANTIC", "auto").lower()

    session = requests.Session()
    session.headers.update(
        {"Authorization": f"ApiKey {api_key}", "Content-Type": "application/json"}
    )

    conflicts = []
    for index in INDICES:
        recreate = recreate_all and (not named or index in named)
        base = json.loads((MAPPINGS_DIR / f"{index}.json").read_text())
        if index in NO_DATE_INDICES:
            check_no_date_fields(index, base)
        attempts = []
        if semantic_mode in ("auto", "on"):
            attempts.append(("semantic", with_semantic(index, base)))
        if semantic_mode in ("auto", "off"):
            attempts.append(("plain", base))

        last = None
        failed_attempts = []
        for label, body in attempts:
            resp = put_index(session, endpoint, index, body, recreate)
            last = (label, resp)
            if resp.ok:
                # In auto mode a semantic PUT that fails for ANY reason - ELSER not
                # deployed, or a real mapping error - fell back to plain and printed a
                # clean "ok (plain)". Say what was actually wrong, so "semantic search
                # is off" and "the mapping is broken" stop looking identical.
                fallback = ("" if not failed_attempts else
                            " after " + "; ".join(failed_attempts))
                print(f"{index}: ok ({label}{', recreated' if recreate else ''})"
                      f"{fallback}")
                break
            failed_attempts.append(f"{label} failed: {resp.status_code} "
                                   f"{resp.text[:160].strip()}")
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
