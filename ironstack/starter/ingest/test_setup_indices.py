#!/usr/bin/env python3
"""Unit tests for ingest/setup_indices.py's argument handling. No Elasticsearch.

    python ingest/test_setup_indices.py

Only the parsing, and deliberately only the parsing: everything past it deletes and
rebuilds indices, and the whole point of these cases is that a mistyped argument must
be refused BEFORE anything reaches for a credential. Every case below asserts that
main() exits without a cluster being contacted, which is what the refusal is worth.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import setup_indices as si

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


def run(*argv):
    """main() with these arguments. Returns the exit message, or None if it did not
    exit - which here means it fell through to the cluster, and is a failure in
    itself, so the environment is deliberately left without credentials."""
    saved = sys.argv
    sys.argv = ["setup_indices.py", *argv]
    try:
        si.main()
        return None
    except SystemExit as exc:
        return str(exc.code)
    finally:
        sys.argv = saved


print("--all is a confirmation of --recreate, and means nothing without it")

# It was accepted on its own: no --recreate, so nothing was rebuilt, and the run then
# printed "ok" for all seven indices. Somebody who meant `--recreate --all` and dropped
# the --recreate got a plain mapping update reported in the same words as the rebuild
# they asked for. Nothing destructive happened, which is exactly why it was invisible.
alone = run("--all")
check("--all on its own is refused", alone is not None, True)
check("and the message says it needs --recreate",
      "--recreate" in (alone or ""), True)
check("and shows the spelling that does what was meant",
      "--recreate --all" in (alone or ""), True)
check("and says what the no-argument run does instead",
      "no arguments" in (alone or ""), True)

# The refusal it is modelled on, still refusing.
bare = run("--recreate")
check("--recreate with no names is still refused", bare is not None, True)
check("and still offers --all as the explicit spelling",
      "--recreate --all" in (bare or ""), True)

print("\nThe other refusals still hold")
check("an unknown index name is refused",
      "no such index" in (run("--recreate", "workout-sesions") or ""), True)
check("a known name without --recreate is refused",
      "without --recreate" in (run("workout-sets") or ""), True)
check("an unknown flag is refused",
      "unknown option" in (run("--recreat") or "") , True)
# The one that has to be refused before anything else: a misspelling of the safe flag
# must never be read as the dangerous one.
check("...and it is refused before any index name is even looked up",
      "unknown option" in (run("--recreat", "--all") or ""), True)

print()
if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all setup_indices tests passed")
