#!/usr/bin/env python3
"""Round-trip every workout log through the shorthand and back.

    python ingest/test_shorthand.py

Encodes each workouts/**/*.json to shorthand, decodes it again, and requires
the result to be identical to the original. Defaults and prep templates are
switched off so this tests the format itself, not the fill-ins.

The corpus this walks is the corpus the indexer walks. That is checked, not
assumed: see main().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import index_workouts  # noqa: E402  (the one corpus walk, shared with the indexer)
import shorthand  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def normalize(doc):
    """`set_type: working` is what the indexer assumes when the key is absent
    (index_workouts.py: s.get("set_type", "working")), so the two spellings are
    the same document. The shorthand only ever writes the absent form."""
    for exercise in doc.get("exercises", []):
        for entry in exercise.get("sets", []):
            if entry.get("set_type") == "working":
                entry.pop("set_type")
    return doc


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a:
                yield f"{path}.{key}: missing in round-trip ({b[key]!r})"
            elif key not in b:
                yield f"{path}.{key}: dropped ({a[key]!r})"
            else:
                yield from diff(a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield f"{path}: length {len(a)} -> {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            yield from diff(x, y, f"{path}[{i}]")
    elif a != b:
        yield f"{path}: {a!r} -> {b!r}"


def walks_agree() -> tuple[list[Path], list[str]]:
    """This test's own walk of workouts/, and how it differs from the indexer's.

    The bug was never that an empty repo is invalid - a new instance legitimately
    has no logs. The bug was that this file walked glob("*/*.json") while the
    indexer walked rglob("*.json"), so the two agreed only for as long as every log
    happened to sit at exactly depth 2, and the moment one did not, this printed a
    pass over a corpus it could not see. Testing 0 of 0 files is only a failure when
    the indexer can see files this cannot.

    So the test is the comparison: whatever files index_workouts.log_paths() finds,
    these are the files that get round-tripped. Zero on both sides is a pass.
    """
    mine = sorted((REPO_ROOT / "workouts").rglob("*.json"))
    theirs = sorted(index_workouts.log_paths())
    problems = []
    for path in sorted(set(theirs) - set(mine)):
        problems.append(f"{path}: the indexer reads it, this test does not")
    for path in sorted(set(mine) - set(theirs)):
        problems.append(f"{path}: this test reads it, the indexer does not")
    return mine, problems


def main() -> int:
    files, disagreement = walks_agree()
    if disagreement:
        print("FAIL this test and index_workouts.log_paths() disagree about the corpus")
        for problem in disagreement:
            print(f"     {problem}")
        print("     Nothing was round-tripped. Make the two walks the same walk.")
        return 1
    if not files:
        # A new instance ships with no logs. Both walks found zero and agree, which is
        # the state a fresh clone is supposed to be in, not a broken glob.
        print("no logs yet - workouts/ is empty and the indexer sees nothing either")
        print("\n0/0 sessions round-tripped")
        return 0
    failures = 0
    for path in files:
        original = normalize(json.loads(path.read_text()))
        text = shorthand.encode(original, use_defaults=False)
        try:
            back = shorthand.decode(text, use_defaults=False, filename=path.name)
        except SystemExit as exc:
            print(f"FAIL {path}: {exc}")
            failures += 1
            continue
        problems = list(diff(original, back))
        if problems:
            failures += 1
            print(f"FAIL {path}")
            for problem in problems[:6]:
                print(f"     {problem}")
    print(f"\n{len(files) - failures}/{len(files)} sessions round-tripped")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
