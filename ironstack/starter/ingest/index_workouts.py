#!/usr/bin/env python3
"""Validate and index Ironstack workout logs into Elasticsearch.

Usage:
    python ingest/index_workouts.py [paths...]

With no arguments, indexes every workouts/**/*.json in the repo.
Validation-only mode (no Elasticsearch needed): --validate

Idempotent: every document gets a deterministic _id derived from the session and
the set's position within it, so re-running after an edit updates in place. The id
deliberately carries no exercise name - renaming a lift must not orphan its history.

Session links (prev_session_id / next_session_id / streak_day) are computed
from every log under workouts/, not hand-written, so they stay correct even
when only one file is passed on the command line.

Env:
  ES_ENDPOINT  e.g. https://my-project.es.us-east4.gcp.elastic.cloud:443
  ES_API_KEY   an API key with write access to the workout-* indices
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import derive
from envconf import env_secret, env_url

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "workout.schema.json"
WORKOUTS_DIR = REPO_ROOT / "workouts"

PROGRAM_FIELDS = ("name", "block", "phase", "week", "day", "total_days", "meet_date")


def _fmt_number(value) -> str:
    if value is None:
        return "0"
    return str(int(value)) if float(value) == int(value) else str(value)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# est_e1rm moved to metrics.e1rm(), which uses Tuchscherer's RPE table rather than
# Epley with reps-in-reserve folded into the rep count, reports which model it used,
# and carries a confidence tier. derive.set_fields() writes it onto every working set
# — not only the main lifts, as the old version did.


def load_schema() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


def session_key(session: dict) -> str:
    return session.get("session_id") or session["date"]


def resolve_timezone(tz_name: str):
    """ZoneInfo for an IANA name, or ValueError. Never a silent fallback.

    An unrecognised zone is a typo, not a condition: swallowing it produced an
    offset-less timestamp, and @timestamp is mapped `date`, so Elasticsearch read
    the string as UTC. A 6am America/New_York session landed at 1am and every
    hour-of-day panel shifted with nothing anywhere reporting an error.
    """
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError(f"unknown timezone {tz_name!r} ({exc})") from exc


def timestamp_for(session: dict) -> str:
    """ISO instant for the session start. Falls back to the date at midnight local.

    Note on the fold: naive.replace(tzinfo=...) uses fold=0, so on the ambiguous
    hour of the DST fall-back (01:00-01:59 local, which happens twice) this resolves
    to the FIRST, still-daylight-saving occurrence. That is a one-hour ambiguity on
    one hour of one night a year, and the log has no way to say which pass it was.
    """
    day = session["date"]
    start = session.get("start_time") or "00:00"
    tz_name = session.get("timezone")
    naive = datetime.fromisoformat(f"{day}T{start}:00")
    if tz_name:
        try:
            return naive.replace(tzinfo=resolve_timezone(tz_name)).isoformat()
        except ValueError as exc:
            where = source_path(session_key(session))
            sys.exit(f"error: {where or session_key(session)}: {exc}\n"
                     f"       Fix session.timezone: it must be an IANA name such as "
                     f"America/New_York.")
    return naive.isoformat()


def weekday_for(day: str) -> str:
    """'1 Mon' .. '7 Sun': sorts chronologically as a keyword, reads as a label."""
    d = date.fromisoformat(day)
    return f"{d.isoweekday()} {d.strftime('%a')}"


def days_to_meet(session: dict) -> int | None:
    """Days from this session to program.meet_date, as of the session date."""
    meet = (session.get("program") or {}).get("meet_date")
    if not meet:
        return None
    return (date.fromisoformat(meet) - date.fromisoformat(session["date"])).days


def program_block(program: dict) -> dict:
    """The denormalized program context carried by every document."""
    return {k: program[k] for k in PROGRAM_FIELDS if program.get(k) is not None}


# --------------------------------------------------------------------------- links


# session_id -> the file it was read from, so an error about a session can name the
# file a person has to open. Filled by catalog_logs().
_SOURCE_PATHS: dict[str, Path] = {}


def source_path(session_id: str) -> Path | None:
    return _SOURCE_PATHS.get(session_id)


def log_paths(extra_paths: list[Path] | None = None) -> list[Path]:
    """Every workout log this repo knows about.

    The one walk of the corpus. verify_index.py used to do its own glob("*/*.json")
    while this walked rglob("*.json"); they agreed only for as long as every log
    happened to sit at exactly depth 2. The script whose whole job is catching drift
    must not have a walk of its own to drift.
    """
    paths = sorted(WORKOUTS_DIR.rglob("*.json")) if WORKOUTS_DIR.exists() else []
    return paths + list(extra_paths or [])


def catalog_logs(extra_paths: list[Path] | None = None) -> list[tuple[str, str, dict]]:
    """(date, session_id, log) for every session the repo knows about.

    The analytics reference (best e1RM per lift as of each date) has to see the
    whole history, not just the files named on the command line. That is exactly why
    nothing here may be skipped quietly: this corpus feeds build_reference,
    rollup_docs and signal_docs, so one unreadable file computes the whole analysis
    layer on partial history and reports success. Every skip is fatal and named.
    """
    seen: dict[str, tuple[str, dict]] = {}
    skipped: list[str] = []
    _SOURCE_PATHS.clear()
    for path in log_paths(extra_paths):
        try:
            log = json.loads(path.read_text())
        except OSError as exc:
            skipped.append(f"{path}: cannot be read ({exc.strerror or exc})")
            continue
        except ValueError as exc:
            skipped.append(f"{path}: is not valid JSON ({exc})")
            continue
        session = log.get("session") or {}
        if "date" not in session:
            skipped.append(f"{path}: session has no date")
            continue
        key = session_key(session)
        if key in seen:
            first = _SOURCE_PATHS.get(key)
            skipped.append(f"{path}: session_id {key!r} is already used by {first} "
                           f"- one of the two would silently overwrite the other")
            continue
        seen[key] = (session["date"], log)
        _SOURCE_PATHS[key] = path
    if skipped:
        sys.exit("error: the corpus is incomplete, so nothing downstream of it can be "
                 "trusted:\n" + "\n".join(f"  {line}" for line in skipped))
    return [(day, sid, log) for sid, (day, log) in seen.items()]


def session_links(ordered: list[tuple[str, str]]) -> dict[str, dict]:
    """prev/next ids and streak_day (consecutive calendar days trained) per session."""
    links: dict[str, dict] = {}
    prev_day: date | None = None
    streak = 0
    for i, (day_str, sid) in enumerate(ordered):
        day = date.fromisoformat(day_str)
        if prev_day is None or day - prev_day > timedelta(days=1):
            streak = 1
        elif day - prev_day == timedelta(days=1):
            streak += 1
        # same day: streak unchanged
        prev_day = day
        links[sid] = {
            "prev_session_id": ordered[i - 1][1] if i > 0 else None,
            "next_session_id": ordered[i + 1][1] if i + 1 < len(ordered) else None,
            "streak_day": streak,
        }
    return links


# --------------------------------------------------------------------------- explode


def explode(log: dict, links: dict[str, dict] | None = None,
            reference: derive.Reference | None = None) -> list[tuple[str, str, dict]]:
    """Turn one workout log into (index, _id, document) tuples."""
    session = log["session"]
    session_id = session_key(session)
    program = program_block(session.get("program") or {})
    context = {
        "@timestamp": timestamp_for(session),
        "session_id": session_id,
        "date": session["date"],
        "weekday": weekday_for(session["date"]),
        "time_of_day": session.get("time_of_day"),
        "location": {
            "name": (session.get("location") or {}).get("name"),
            "travel": (session.get("location") or {}).get("travel", False),
        },
        "program": program,
        # Denormalised onto every set and note so effort can be compared against the
        # conditions it happened in without a join back to the session.
        "environment": session.get("environment"),
    }
    docs: list[tuple[str, str, dict]] = []
    set_docs: list[dict] = []

    tonnage = 0.0
    total_sets = working_sets = total_reps = 0
    working_rpes: list[float] = []
    seq = 0  # order of every set within the session, across exercises

    for exercise in log["exercises"]:
        slug = slugify(exercise["name"])
        for position, s in enumerate(exercise["sets"], start=1):
            seq += 1
            set_number = s.get("set_number", position)
            set_type = s.get("set_type", "working")
            weight = s.get("weight_lb", 0)
            reps = s["reps"]
            rep_unit = s.get("rep_unit", "reps")
            rpe = s.get("rpe")
            volume = round(weight * reps, 1) if rep_unit == "reps" else None

            total_sets += 1
            if rep_unit == "reps":
                total_reps += int(reps)
            if volume:
                tonnage += volume
            if set_type == "working":
                working_sets += 1
                if rpe is not None:
                    working_rpes.append(rpe)

            doc = {
                **context,
                "exercise": {
                    "name": exercise["name"],
                    "slug": slug,
                    "category": exercise["category"],
                    "equipment": exercise.get("equipment"),
                    "equipment_ids": [i["id"] for i in exercise.get("equipment_items", [])],
                    "equipment_names": [i["name"] for i in exercise.get("equipment_items", [])],
                    "equipment_kinds": sorted({i["kind"] for i in exercise.get("equipment_items", [])
                                               if i.get("kind")}),
                    "bar_weight_lb": next((i["weight_lb"] for i in exercise.get("equipment_items", [])
                                           if i.get("kind") == "barbell" and i.get("weight_lb")), None),
                    "emphasis": exercise.get("emphasis"),
                },
                "seq": seq,
                "set_number": set_number,
                "set_type": set_type,
                "weight_lb": weight,
                "weight_each_lb": s.get("weight_each_lb"),
                "each_side": s.get("each_side", False),
                "scheme": s.get("scheme"),
                "cardio": s.get("cardio"),
                "reps": reps,
                "rep_unit": rep_unit,
                "distance_ft": s.get("distance_ft"),
                "load_type": s.get("load_type", "external"),
                "rpe": rpe,
                "volume_lb": volume,
                "gear": s.get("gear", exercise.get("gear", [])),
                "notes": s.get("notes"),
                "tags": s.get("tags", []),
            }
            doc.update(derive.set_fields(exercise, s, session_id, reference))
            set_docs.append(doc)
            # The id is the set's position in the session, never its name. It used to
            # be {session_id}-{slug}-{set_type}-{set_number}: renaming an exercise
            # changed the id, so the reindex stopped being an upsert and left the old
            # documents behind (429 of them on 2026-09-05). The slug also disagreed
            # with derive.set_fields' canonical lift_slug on the very same document,
            # and two same-named exercises in one session collided silently. `seq`
            # counts every set in the session across exercises, so it is unique by
            # construction and survives any rename. check_unique_ids() proves it.
            docs.append(("workout-sets", f"{session_id}-{seq}", doc))

    for order, note in enumerate(log.get("notes", []), start=1):
        doc = {
            **context,
            "phase": note["phase"],
            "exercise": {"name": note["exercise"], "slug": slugify(note["exercise"])} if note.get("exercise") else None,
            "set_number": note.get("set_number"),
            "order": order,
            "text": note["text"],
            "tags": note.get("tags", []),
        }
        docs.append(("workout-notes", f"{session_id}-note-{order}", doc))

    for order, item in enumerate(session.get("watch_items", []) or [], start=1):
        # A watch item is a note the lifter wrote about the future; it deserves to be
        # findable the same way ("when was my grip last a problem?").
        docs.append(("workout-notes", f"{session_id}-watch-{order}", {
            **context,
            "phase": "watch",
            "exercise": None,
            "set_number": None,
            "order": 1000 + order,
            "text": item,
            "tags": ["watch"],
        }))

    top_sets = []
    for exercise in log["exercises"]:
        if exercise["category"] != "main":
            continue
        working = [s for s in exercise["sets"] if s.get("set_type", "working") == "working"]
        if not working:
            continue
        best = max(working, key=lambda s: (s.get("weight_lb") or 0, s["reps"]))
        label = f"{exercise['name']} {_fmt_number(best.get('weight_lb'))} lb x{_fmt_number(best['reps'])}"
        if best.get("rpe") is not None:
            label += f" at RPE {_fmt_number(best['rpe'])}"
        top_sets.append(label)

    session_doc = {
        **context,
        "source": session.get("source"),
        "start_time": session.get("start_time"),
        "timestamp": timestamp_for(session),
        "duration_min": session.get("duration_min"),
        "days_to_meet": days_to_meet(session),
        "environment": session.get("environment"),
        "metrics": session.get("metrics"),
        "totals": {
            "tonnage_lb": round(tonnage, 1),
            "sets": total_sets,
            "working_sets": working_sets,
            "reps": total_reps,
            "exercises": len(log["exercises"]),
        },
        "avg_working_rpe": round(sum(working_rpes) / len(working_rpes), 2) if working_rpes else None,
        "gear_notes": session.get("gear_notes"),
        "wrap_up": session.get("wrap_up"),
        "watch_items": session.get("watch_items", []),
        **((links or {}).get(session_id) or {}),
    }
    session_doc.update(derive.session_fields(set_docs, session, session_doc["totals"],
                                             session_doc["avg_working_rpe"]))
    session_doc["digest"] = session_digest(log, session_doc["totals"],
                                           session_doc["avg_working_rpe"], top_sets)
    geo = (session.get("location") or {}).get("geo")
    if geo:
        session_doc["location"] = {**session_doc["location"], "geo": geo}
    docs.append(("workout-sessions", session_id, session_doc))
    return docs


def session_digest(log: dict, totals: dict, avg_rpe, top_sets: list) -> str:
    """One paragraph that says what the session was, for semantic search to embed.

    Composed here rather than written by hand: the log stays terse, and the
    AI-facing view is rebuilt from it on every index run.
    """
    session = log["session"]
    day = date.fromisoformat(session["date"])
    parts = [day.strftime("%A, %B %-d, %Y")]
    if session.get("time_of_day"):
        parts.append(session["time_of_day"])

    location = session.get("location") or {}
    where = location.get("name")
    if where:
        parts.append(f"traveling in {where}" if location.get("travel") else where)
    env = session.get("environment") or {}
    weather = [f"{env['temp_f']:.0f}F" if env.get("temp_f") is not None else "",
               env.get("conditions", ""), env.get("setting", "")]
    weather = [w for w in weather if w]
    if weather:
        parts.append(", ".join(weather))

    program = session.get("program") or {}
    if program.get("name"):
        block = " ".join(dict.fromkeys(str(x) for x in [program.get("block"), program.get("phase")] if x))
        label = f"{program['name']} {block}".strip()
        if program.get("week") is not None:
            label += f", week {program['week']}"
        if program.get("day") is not None:
            label += f" day {program['day']}"
        parts.append(label)
    remaining = days_to_meet(session)
    if remaining is not None:
        parts.append(f"{remaining} days to the meet")

    lines = [". ".join(parts) + "."]
    if session.get("source"):
        lines.append(f"Imported from {session['source']}; no notes were captured at the time.")
    if top_sets:
        lines.append("Top sets: " + "; ".join(top_sets) + ".")
    names = [e["name"] for e in log["exercises"] if e["category"] != "prep"]
    if names:
        lines.append("Trained: " + ", ".join(names) + ".")
    equipment = []
    for exercise in log["exercises"]:
        equipment += [i["name"] for i in exercise.get("equipment_items", [])]
    if equipment:
        lines.append("Equipment: " + ", ".join(dict.fromkeys(equipment)) + ".")
    lines.append(f"{totals['working_sets']} working sets, {totals['tonnage_lb']:,.0f} lb moved"
                 + (f", average working RPE {avg_rpe}." if avg_rpe else "."))
    metrics = session.get("metrics") or {}
    if metrics.get("bodyweight_lb") is not None:
        body = f"Bodyweight {metrics['bodyweight_lb']} lb"
        if metrics.get("sleep_hrs") is not None:
            body += f", {metrics['sleep_hrs']} hours of sleep"
        lines.append(body + ".")
    for note in log.get("notes", []):
        lines.append(note["text"])
    if session.get("wrap_up"):
        lines.append(session["wrap_up"])
    if session.get("watch_items"):
        lines.append("Watching: " + "; ".join(session["watch_items"]) + ".")
    return " ".join(lines)


def strip_nones(value):
    if isinstance(value, dict):
        return {k: strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_nones(v) for v in value]
    return value


# --------------------------------------------------------------------------- index


def bulk_index(docs: list[tuple[str, str, dict]]) -> None:
    import requests

    if not os.environ.get("ES_ENDPOINT", "").strip() or not os.environ.get("ES_API_KEY", "").strip():
        sys.exit("error: ES_ENDPOINT and ES_API_KEY must be set (or use --validate)")
    endpoint = env_url("ES_ENDPOINT")
    api_key = env_secret("ES_API_KEY")

    lines = []
    for index, _id, doc in docs:
        lines.append(json.dumps({"index": {"_index": index, "_id": _id}}))
        lines.append(json.dumps(strip_nones(doc)))
    payload = "\n".join(lines) + "\n"

    resp = requests.post(
        f"{endpoint}/_bulk",
        data=payload.encode("utf-8"),
        headers={
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/x-ndjson",
        },
        timeout=60,
    )
    if not resp.ok:
        sys.exit(f"error: bulk request failed -> {resp.status_code} {resp.text[:500]}")
    body = resp.json()
    if body.get("errors"):
        failures = [
            item["index"]
            for item in body["items"]
            if item.get("index", {}).get("status", 200) >= 300
        ]
        sys.exit(f"error: {len(failures)} document(s) failed:\n{json.dumps(failures[:5], indent=2)}")
    print(f"indexed {len(docs)} document(s)")


def check_unique_ids(docs: list[tuple[str, str, dict]]) -> None:
    """No two documents in one index may share an _id.

    A collision is invisible in Elasticsearch - the second document simply replaces
    the first, the bulk call succeeds, and the count quietly comes up short. Since
    the ids are generated here, that can only ever be a bug here.
    """
    seen: dict[tuple[str, str], dict] = {}
    clashes: list[str] = []
    for index, _id, doc in docs:
        key = (index, _id)
        if key in seen:
            clashes.append(f"  {index} _id={_id} (sessions {seen[key].get('session_id')!r} "
                           f"and {doc.get('session_id')!r})")
        else:
            seen[key] = doc
    if clashes:
        sys.exit(f"error: {len(clashes)} duplicate document id(s); each one would "
                 f"silently overwrite the other:\n" + "\n".join(clashes[:10]))


def check_signal_fields(signals: list[tuple[str, str, dict]]) -> None:
    """Every field the signal rows carry must be declared in the mapping.

    ironstack-signals is `dynamic: strict`, so a field added to signal_docs and not to
    schema/mappings/ironstack-signals.json is rejected by Elasticsearch - correctly, but
    as a bulk error listing document ids, in CI, after the run has already written its
    other indices. Caught here it is one line naming the field and the file to add it to,
    before anything is sent.

    Strict is what makes this necessary and is worth it anyway: the alternative is
    Elasticsearch inventing the mapping, and for a field holding "2026-10-24" the mapping
    it invents is a date - which is the one thing this index must never contain.
    """
    declared = set(
        json.loads((REPO_ROOT / "schema" / "mappings" / f"{derive.SIGNAL_INDEX}.json")
                   .read_text())["mappings"]["properties"]
    )
    undeclared = sorted({k for _index, _id, doc in signals
                         for k in strip_nones(doc)} - declared)
    if undeclared:
        sys.exit(
            f"error: signal_docs emits {', '.join(undeclared)}, which "
            f"schema/mappings/{derive.SIGNAL_INDEX}.json does not declare.\n"
            f"       That index is dynamic: strict, so Elasticsearch would reject every "
            f"row carrying them.\n"
            f"       Add them to the mapping as keyword - never as date, whatever they "
            f"hold - and run setup_indices.py."
        )


def sweep_signals(stamp: str) -> None:
    """Delete signal rows this run did not write.

    Signal ids carry meaning - drift:calves, intensity:2026-W36 - so a row stops being
    rewritten the moment its subject leaves the window: a muscle group not trained for
    366 days, or a week that ages out of the last 13. The bulk index replaces documents
    by id and has no opinion about ids it was not given, so those rows would survive
    forever, carrying a last_trained and a session count from a window that no longer
    exists. The drift card reads every drift row, so a stale one can become the headline
    verdict. That is the same failure this index was built to remove, arriving by a
    different door.

    Every row written this run carries today's stamp, so anything else is stale by
    definition and no id bookkeeping is needed.
    """
    import requests

    endpoint = env_url("ES_ENDPOINT")
    api_key = env_secret("ES_API_KEY")
    headers = {"Authorization": f"ApiKey {api_key}", "Content-Type": "application/json"}

    # The bulk write above sends no refresh, so the rows it just wrote are not yet
    # searchable. `refresh=true` on _delete_by_query means "refresh AFTER the delete",
    # not before the search, so without this the sweep scrolls a pre-write view: it
    # matches the previous versions of rows this run just rewrote, hits version
    # conflicts, and with the default conflicts=abort stops the whole request while
    # still answering 200. Refresh first, and the sweep sees what was written.
    resp = requests.post(f"{endpoint}/{derive.SIGNAL_INDEX}/_refresh",
                         headers=headers, timeout=60)
    if not resp.ok:
        sys.exit(f"error: could not refresh {derive.SIGNAL_INDEX} before the stale-row "
                 f"sweep -> {resp.status_code} {resp.text[:200]}")

    resp = requests.post(
        f"{endpoint}/{derive.SIGNAL_INDEX}/_delete_by_query",
        # conflicts=proceed: a row rewritten between the refresh and the scroll is not
        # a reason to abandon the sweep half-done. Any conflict that does happen is
        # reported below rather than counted as success.
        params={"refresh": "true", "conflicts": "proceed"},
        json={"query": {"bool": {"must_not": {"term": {"computed_through": stamp}}}}},
        headers=headers,
        timeout=60,
    )
    if not resp.ok:
        sys.exit(f"error: could not sweep stale signal rows -> {resp.status_code} "
                 f"{resp.text[:500]}")
    try:
        body = resp.json()
    except ValueError:
        sys.exit(f"error: stale-row sweep returned no JSON body -> {resp.text[:200]}")

    # _delete_by_query answers 200 even when it did nothing at all. The counts are the
    # only report there is, so none of them may be dropped on the floor.
    deleted = body.get("deleted", 0)
    total = body.get("total", 0)
    conflicts = body.get("version_conflicts", 0)
    failures = body.get("failures") or []
    timed_out = bool(body.get("timed_out"))
    noops = body.get("noops", 0)
    print(f"signals -> swept {deleted} of {total} matched stale row(s)"
          + (f", {noops} noop(s)" if noops else ""))
    if conflicts or failures or timed_out:
        sys.exit(
            f"error: the stale signal sweep did not complete: {conflicts} version "
            f"conflict(s), {len(failures)} failure(s)"
            f"{', and it timed out' if timed_out else ''}.\n"
            f"       {deleted} of {total} matched row(s) were deleted, so stale "
            f"verdicts may still be in {derive.SIGNAL_INDEX}.\n"
            + (f"       first failures: {json.dumps(failures[:3])[:500]}\n" if failures else "")
            + f"       Re-run the indexer; if it repeats, the index is being written "
            f"by something else at the same time."
        )


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    validate_only = "--validate" in sys.argv

    paths = [Path(a) for a in args] or log_paths()
    if not paths:
        print("no workout logs found: nothing to do")
        return

    validator = load_schema()
    outside = [p for p in paths if WORKOUTS_DIR not in p.resolve().parents]
    # One walk of the corpus. Links, the analytics reference and the rollups all need
    # the whole history regardless of which files were named on the command line.
    corpus = catalog_logs(outside)
    links = session_links(sorted(((day, sid) for day, sid, _ in corpus),
                                 key=lambda pair: (pair[0], pair[1])))
    reference = derive.build_reference(corpus)
    requested = {session_key(json.loads(path.read_text())["session"]) for path in paths}

    # Validate the WHOLE corpus, not only the named files. Every log below is exploded
    # a few lines further down whether or not it was named on the command line, and in
    # explode() a missing key is a bare KeyError traceback rather than a schema error
    # pointing at a file. The documents are already in memory; this is one more pass.
    failed = []
    for _day, sid, log in sorted(corpus, key=lambda row: (row[0], row[1])):
        errors = sorted(validator.iter_errors(log), key=lambda e: e.json_path)
        if not errors:
            continue
        failed.append(sid)
        print(f"INVALID {source_path(sid) or sid}")
        for error in errors[:10]:
            print(f"  {error.json_path}: {error.message}")
    if failed:
        sys.exit(f"error: fix the {len(failed)} invalid log(s) above")

    # Explode the whole corpus once. The requested sessions are indexed; the rest are
    # here because the daily and weekly rollups describe the whole history and cannot
    # be computed from a single day. Deterministic ids make re-emitting them an upsert.
    every: list[tuple[str, str, dict]] = []
    try:
        for _day, _sid, log in corpus:
            every.extend(explode(log, links, reference))
    except derive.UnknownExercise as exc:
        sys.exit(f"error: {exc}")

    check_unique_ids(every)

    all_docs = [d for d in every if d[2].get("session_id") in requested]
    for sid in sorted(requested):
        print(f"ok {sid} -> {sum(1 for d in all_docs if d[2].get('session_id') == sid)} document(s)")

    # One clock for the whole run. rollup_docs and signal_docs each default to the
    # current UTC date, so calling them without one is two reads of the wall clock a
    # few lines apart: a run that straddles midnight would mark the same week
    # in-progress on the rollup and closed on the signal row, or the reverse.
    today = datetime.now(timezone.utc).date()

    rollups = derive.rollup_docs(every, today)
    all_docs.extend(rollups)
    print(f"rollups -> {len(rollups)} document(s)")

    # The Overview verdicts, windowed at index time so the dashboard picker cannot
    # re-scope them. See derive.signal_docs for why this index carries no date field.
    signals = derive.signal_docs(every, rollups, today)
    check_signal_fields(signals)
    all_docs.extend(signals)
    print(f"signals -> {len(signals)} document(s)")

    if validate_only:
        print("validation passed")
        return
    bulk_index(all_docs)
    if signals:
        sweep_signals(signals[0][2]["computed_through"])


if __name__ == "__main__":
    main()
