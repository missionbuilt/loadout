#!/usr/bin/env python3
"""Does the public template still match the instance it was forked from?

    python sync_check.py --instance /path/to/your-workout-log
    python sync_check.py --instance . --starter ./loadout/ironstack/starter

The template in this folder is a copy of a working private instance's pipeline.
Copies drift. For several days this one did: `ironstack-signals` was added to the
instance and never reached the template, so the dashboards this repo ships queried
an index the template never created and a stranger's import raised eight errors.
Nothing checked, so nothing said.

This is the check. It reads sync-manifest.json - the one list of which files are
shared - and compares each of them. It makes no network call, needs no
credentials, and reads nothing outside the two folders it is given.

Run it from the instance's CI: the instance is where the changes are made, so it
is where the failure has to land. Exit 0 means the two are in sync.

Exit codes: 0 in sync, 1 drift or a missing file, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "sync-manifest.json"


def read(path: Path) -> str | None:
    try:
        return path.read_text()
    except OSError:
        return None


def redact(text: str, rules: list[dict], where: str) -> tuple[str, list[str]]:
    """Apply the manifest's line replacements to the instance's copy.

    A rule names its line by a substring that holds none of the private value, then
    replaces the whole line. That indirection is the point: this manifest lives in
    the public repo, so it must not spell out the coordinates and meet totals it
    exists to keep out. `of` pins how many lines that substring is expected to hit,
    so an upstream edit that adds or removes one fails here as stale rather than
    silently redacting the wrong line.

    Every rule is resolved against the original text before anything is written, so
    two rules cannot chase each other's output, and two rules landing on the same
    line is itself an error.
    """
    lines = text.split("\n")
    problems, edits = [], {}
    for rule in rules:
        needle, want = rule["contains"], rule.get("of", 1)
        hits = [i for i, line in enumerate(lines) if needle in line]
        if len(hits) != want:
            problems.append(
                f"{where}: {needle!r} matches {len(hits)} line(s), the manifest "
                f"expects {want} - the upstream file changed under the redaction")
            continue
        index = hits[rule.get("nth", 1) - 1]
        if index in edits:
            problems.append(
                f"{where}: two rules both target line {index + 1}")
            continue
        edits[index] = rule["public"]
    for index, replacement in edits.items():
        lines[index] = replacement
    return "\n".join(lines), problems


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(prog="sync_check.py", description=__doc__.split("\n")[0])
    parser.add_argument("--instance", required=True, metavar="DIR",
                        help="root of the private instance (the repo with workouts/ in it)")
    parser.add_argument("--starter", default=str(HERE), metavar="DIR",
                        help="root of this template (default: the folder this script is in)")
    opts = parser.parse_args(argv)

    instance, starter = Path(opts.instance).resolve(), Path(opts.starter).resolve()
    manifest = json.loads((starter / "sync-manifest.json").read_text())

    drifted: list[str] = []
    missing: list[str] = []
    broken: list[str] = []

    for rel in manifest["verbatim"]:
        src, dst = read(instance / rel), read(starter / rel)
        if src is None:
            missing.append(f"{rel}: not in the instance at {instance}")
        elif dst is None:
            missing.append(f"{rel}: on the shared list but not in the template")
        elif src != dst:
            drifted.append(rel)

    for rel, spec in manifest["redacted"].items():
        src, dst = read(instance / rel), read(starter / rel)
        if src is None:
            missing.append(f"{rel}: not in the instance at {instance}")
            continue
        if dst is None:
            missing.append(f"{rel}: on the shared list but not in the template")
            continue
        expected, problems = redact(src, spec["lines"], rel)
        broken.extend(problems)
        if not problems and expected != dst:
            drifted.append(rel)

    # A leak is not drift and cannot be fixed by copying harder, so it is checked
    # from the other direction: these must not be here at all.
    never = manifest["never_copy"]
    leaked = [p for p in never["must_be_absent"] if (starter / p).exists()]
    leaked += [str(hit.relative_to(starter))
               for pattern in never["must_match_nothing"]
               for hit in sorted(starter.glob(pattern))
               # The folders ship empty but not unexplained: each keeps its README.
               if hit.name != "README.md"]

    checked = len(manifest["verbatim"]) + len(manifest["redacted"])
    if not (drifted or missing or broken or leaked):
        print(f"in sync: {checked} shared file(s) match {instance}")
        return 0

    print("The public template has drifted from the instance it was forked from.\n")
    for rel in sorted(drifted):
        print(f"  differs   {rel}")
    for line in sorted(missing):
        print(f"  missing   {line}")
    for line in sorted(broken):
        print(f"  stale     {line}")
    for rel in sorted(leaked):
        print(f"  leaked    {rel}: on the never-copy list but present in the template")

    print(f"""
What to do, from the instance repo root:

  git clone --depth 1 https://github.com/{manifest['upstream']['public_repo']}.git /tmp/loadout
  STARTER=/tmp/loadout/{manifest['upstream']['starter_path']}

  # copy each file named above back out, keeping the same relative path:
  cp <file> "$STARTER"/<file>

  # then re-apply the redactions and confirm:
  python "$STARTER"/sync_check.py --instance . --starter "$STARTER"

Open a PR on {manifest['upstream']['public_repo']} with the result. The shared-file list
lives in {manifest['upstream']['starter_path']}/sync-manifest.json - if a file
belongs in the template and is not on that list, add it there in the same PR.

A 'stale' line means a redacted file changed upstream on or around the line the
manifest replaces. Read both versions and decide whether the public line changes
too, then update sync-manifest.json.""")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
