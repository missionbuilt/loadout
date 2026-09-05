#!/usr/bin/env python3
"""Tests for the exercise-name suggester.

Two of these exist because the bug they describe was real and shipped-adjacent. Both were
found by evaluating the matcher against the whole 182-name taxonomy before wiring it to
anything, which is the only reason they are tests and not incidents.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive  # noqa: E402
import suggest  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RAW = json.loads((REPO / "config" / "exercises.json").read_text())

failures: list[str] = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


print("Normalization")
# Plurals have to be folded BEFORE the abbreviation lookup. Expanding first left "RDLs"
# as "rdl" while plain "RDL" became "romanian deadlift", so two spellings of one lift
# normalized to different strings and "DB RDL" ranked "Deficit DB RDL" over "DB RDLs".
check("RDL and RDLs normalize alike",
      suggest.normalize("DB RDL") == suggest.normalize("DB RDLs"), True)
check("case is folded", suggest.normalize("Cable Curls"), suggest.normalize("cable curls"))
check("comp expands to competition",
      suggest.normalize("Comp Squat"), suggest.normalize("Competition Squat"))
check("pulldown and pull down agree",
      suggest.normalize("Lat Pulldown"), suggest.normalize("Lat Pull Downs"))
check("punctuation and spacing collapse",
      suggest.normalize('3"  Conv   Block Pull'), suggest.normalize("3 conv block pull"))

print("\nCanonical targets")
# derive.load_taxonomy() resolves aliases: it drops `alias_of` and adds `canonical`. An
# `alias_of` test alone therefore saw every name as canonical on that shape and offered
# one alias as the target for another - which would write an alias of an alias.
raw_names = suggest.canonical_names(RAW)
resolved_names = suggest.canonical_names(derive.load_taxonomy())
check("both taxonomy shapes agree", raw_names == resolved_names, True)
aliases = {k for k, v in RAW.items() if v.get("alias_of")}
check("no alias is offered as a target", sorted(aliases & set(resolved_names)), [])

print("\nEvery alias the taxonomy already has is offered")
# Two different claims, and conflating them made this test dishonest. The one that
# has to hold for every alias is that a person resolving the name WOULD SEE the
# right answer: the true canonical is somewhere in the five names log.py prints.
# Whether it ranks first is a quality measure of a lexical matcher, and a lexical
# matcher has a known ceiling - "Incline DB Press" shares 'incline' and 'db' with
# both "DB Incline Bench" and "Incline DB Fly", and nothing in difflib knows that a
# press is a bench and a fly is not. Naming that miss here is the point: this list
# is the evidence that would justify a semantic index, and it stays honest only if
# a NEW miss fails the run rather than being absorbed into a softer assertion.
KNOWN_NOT_FIRST = {"Incline DB Press"}

not_first = []
for alias, entry in sorted(RAW.items()):
    truth = entry.get("alias_of")
    if not truth:
        continue
    offered = [name for name, _ in suggest.candidates(alias, RAW, limit=5)]
    check(f"{alias!r} -> {truth!r} is offered", truth in offered, True)
    if not offered or offered[0] != truth:
        not_first.append(alias)

check("the misses are the ones we know about", sorted(not_first),
      sorted(KNOWN_NOT_FIRST))
check("and the rest rank first",
      len([a for a, e in RAW.items() if e.get("alias_of")]) - len(not_first),
      len([a for a, e in RAW.items() if e.get("alias_of")]) - len(KNOWN_NOT_FIRST))

print("\nThe brief's own example")
check("'competitive squat'", suggest.candidates("competitive squat", RAW)[0][0], "Comp Squat")
check("'hi bar squat'", suggest.candidates("hi bar squat", RAW)[0][0], "High Bar Squat")

print("\nWriting an alias")
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "exercises.json"
    path.write_text(json.dumps(RAW, indent=2, ensure_ascii=False) + "\n")
    suggest.add_alias("Competitive Squat", "Comp Squat", path=path)
    after = json.loads(path.read_text())
    check("the alias is written", after["Competitive Squat"], {"alias_of": "Comp Squat"})
    check("keys stay sorted", list(after) == sorted(after), True)
    check("nothing else changed", len(after), len(RAW) + 1)
    check("trailing newline kept", path.read_text().endswith("}\n"), True)

    for label, args in (
        ("an existing name is refused", ("Comp Squat", "Front Squat")),
        ("an unknown target is refused", ("Whatever Curl", "Not A Lift")),
        # load_taxonomy() resolves one hop only, so an alias of an alias points nowhere.
        ("an alias as target is refused", ("Another Name", "Competition Squat")),
    ):
        try:
            suggest.add_alias(*args, path=path)
            check(label, "accepted", "ValueError")
        except ValueError:
            check(label, "ValueError", "ValueError")

print("\nThe miss log")
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "misses.jsonl"
    offered = suggest.candidates("competitive squat", RAW, limit=3)
    suggest.record("competitive squat", offered, "Comp Squat", path=path)
    suggest.record("Sled Drag Thing", offered, None, path=path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    check("one row per resolution", len(rows), 2)
    check("an accepted top match is marked", rows[0]["top_was_chosen"], True)
    check("a rejection records no choice", rows[1]["chosen"], None)
    check("the scores offered are kept", len(rows[0]["offered"]), 3)

print()
if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all suggester tests passed")
