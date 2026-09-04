#!/usr/bin/env python3
"""Round-trip every workout log through the shorthand and back.

    python ingest/test_shorthand.py

Encodes each workouts/**/*.json to shorthand, decodes it again, and requires
the result to be identical to the original. Defaults and prep templates are
switched off so this tests the format itself, not the fill-ins.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shorthand

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


def main() -> int:
    files = sorted((REPO_ROOT / "workouts").glob("*/*.json"))
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
