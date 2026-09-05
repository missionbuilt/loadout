#!/usr/bin/env python3
"""Ranked guesses at what an unknown exercise name was meant to be.

The problem, in Mike's words: *"similar lift names can be grouped semantically — if
someone enters competitive squat, comp squat, high bar squat, we should be smart enough
to group them. Names do not need to be 100% matching."*

The answer here is deliberately lexical and deliberately not automatic.

**Why lexical first.** Every alias the taxonomy has accumulated so far is a mechanical
variant, not a semantic one:

    Cable curls                   -> Cable Curls               case
    Hammer Curl                   -> Hammer Curls              plural
    Lat Pulldown                  -> Lat Pulldowns             plural
    DB RDL                        -> DB RDLs                   plural
    Competition Deadlift          -> Comp Deadlift             abbreviation
    Competition Squat             -> Comp Squat                abbreviation
    Chest Supported Dumbbell Row  -> Chest Supported Rows      word substitution

Case, plurals, abbreviations and one substitution. An embedding model is not needed to
see that "Competition Squat" and "Comp Squat" are the same lift, and reaching for one
first would mean a new index, an inference endpoint and a reindex to solve a problem
`difflib` and a twenty-line abbreviation table already solve. If the miss log (see
`record()`) later shows real semantic misses — "hip hinge" for "Romanian Deadlift" —
that is the evidence for adding a semantic index, and it will be evidence rather than a
guess.

**Why not automatic.** 182 names, many of them one token apart: `1-Arm Cable Rows` and
`1-Arm Lat Pull Downs`, `3" Conv Block Pull` and `3" Sumo Block Pull`. A confident wrong
match silently merges two lifts' histories, and the e1RM reference, the drift card and
every ratio downstream would then be built on it. So this module only ever *ranks*. A
human accepts, and the acceptance is written into `config/exercises.json` where it is
reviewable in a diff and permanent.

**Never at index or query time.** Canonical names are decided once, by a person, in the
taxonomy. `derive.classify()` still raises on an unknown name; this module only makes
that error useful.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MISS_LOG = REPO / "config" / "name-suggestions.jsonl"

# Whole-token expansions only. Expanding inside a word turns "Deadlift" into
# "Deadromanian deadlift" and every score with it.
ABBREV = {
    "comp": "competition",
    "db": "dumbbell",
    "bb": "barbell",
    "kb": "kettlebell",
    "ohp": "overhead press",
    "rdl": "romanian deadlift",
    "sldl": "stiff leg deadlift",
    "ssb": "safety squat bar",
    "gm": "good morning",
    "bw": "bodyweight",
    "ez": "ez bar",
    "dl": "deadlift",
    "sq": "squat",
    "bp": "bench press",
    "pulldown": "pull down",
    "pushdown": "push down",
    "skullcrusher": "skull crusher",
    "bentover": "bent over",
    "pushup": "push up",
    "pullup": "pull up",
    "chinup": "chin up",
}


def _singular(token: str) -> str:
    """Curls -> curl. Long enough to be a word, and not a word that ends in ss."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize(name: str) -> str:
    """Case, punctuation, abbreviations and plurals folded away.

    After this, "Hammer Curl" and "Hammer Curls" are the same string, and so are
    "Competition Squat" and "Comp Squat" - which is most of the job.
    """
    text = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    tokens = []
    for token in text.split():
        expanded = ABBREV.get(_singular(token), _singular(token))
        tokens.extend(_singular(part) for part in expanded.split())
    return " ".join(tokens)


def score(a: str, b: str) -> float:
    """0..1 over two already-normalized names.

    Two measures, weighted equally and for different failure modes. The sequence ratio
    catches typos and dropped letters but is fooled by word order. Token overlap catches
    reordering and substitution but is blind to spelling. "Chest Supported Dumbbell Row"
    against "Chest Supported Rows" scores 0.75 on tokens and 0.79 on sequence; either
    alone would rank it below a closer-looking wrong answer.

    The sequence term is the better of the raw ratio and the ratio over sorted tokens,
    because reordering is the single most common way a lifter rewrites a name and the
    raw ratio punishes it hardest. "Incline DB Press" for "DB Incline Bench" is the
    case that forced it: the two share every token but one, and on the raw ratio alone
    the right answer ranked 8th - outside the five names log.py prints, so the person
    resolving it was never shown it. Sorted, it ranks 4th and is on screen. Overlap
    alone cannot do this job either; it ties "DB Incline Bench" with "Incline DB Fly"
    at 0.5, and only spelling separates them.
    """
    if not a or not b:
        return 0.0
    sequence = SequenceMatcher(None, a, b).ratio()
    sorted_a, sorted_b = " ".join(sorted(a.split())), " ".join(sorted(b.split()))
    sequence = max(sequence, SequenceMatcher(None, sorted_a, sorted_b).ratio())
    ta, tb = set(a.split()), set(b.split())
    overlap = len(ta & tb) / len(ta | tb)
    return round(0.5 * sequence + 0.5 * overlap, 4)


def canonical_names(taxonomy: dict) -> list[str]:
    """The names a suggestion may point at: canonical entries only, never an alias.

    Two shapes reach this. The raw config/exercises.json marks an alias with `alias_of`.
    `derive.load_taxonomy()` RESOLVES aliases first - it copies the target's fields over
    and replaces `alias_of` with `canonical` - so on that shape an `alias_of` test sees
    every name as canonical and happily offers one alias as the target for another. That
    would have written an alias of an alias, which load_taxonomy() resolves in one hop
    and so would silently point at nothing.
    """
    names = []
    for name, entry in taxonomy.items():
        if entry.get("alias_of"):
            continue                                   # raw file shape
        canonical = entry.get("canonical")
        if canonical and canonical != name:
            continue                                   # resolved shape
        names.append(name)
    return sorted(names)


def candidates(name: str, taxonomy: dict, limit: int = 5) -> list[tuple[str, float]]:
    """(canonical name, score) best first. Never returns `name` itself."""
    target = normalize(name)
    scored = [
        (candidate, score(target, normalize(candidate)))
        for candidate in canonical_names(taxonomy)
        if candidate != name
    ]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return scored[:limit]


def record(typed: str, offered: list[tuple[str, float]], chosen: str | None,
           path: Path | None = None) -> None:
    """Append one resolution to the miss log.

    This is the instrumentation that decides whether a semantic index is ever justified.
    It stores what was typed, what was offered and with what scores, and what the human
    actually picked - so the question "would an embedding have done better here" can be
    answered from the record rather than argued.

    `chosen` is None when the human rejected every suggestion, which is the interesting
    row: either a genuinely new lift, or the case lexical matching cannot see.
    """
    path = path or MISS_LOG
    top = offered[0][0] if offered else None
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "typed": typed,
        "chosen": chosen,
        "top_was_chosen": bool(chosen and top == chosen),
        "offered": [{"name": n, "score": s} for n, s in offered],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def format_candidates(name: str, offered: list[tuple[str, float]]) -> str:
    """The suggestion block, for an error message or a prompt."""
    if not offered:
        return f"exercise {name!r} is not in config/exercises.json, and nothing looks close."
    lines = [f"exercise {name!r} is not in config/exercises.json. Did you mean:"]
    for index, (candidate, value) in enumerate(offered, 1):
        lines.append(f"  {index}. {candidate}   ({value:.2f})")
    return "\n".join(lines)


TAXONOMY_PATH = REPO / "config" / "exercises.json"


def add_alias(typed: str, canonical: str, path: Path | None = None) -> None:
    """Write `typed` into the taxonomy as an alias of `canonical`.

    Keys stay sorted and the file keeps its 2-space indent and trailing newline, so the
    diff is one added entry and nothing else. That matters: this file is the one place a
    person decides what two names mean, and a review of it should be three lines long.
    """
    path = path or TAXONOMY_PATH
    taxonomy = json.loads(path.read_text())
    if typed in taxonomy:
        raise ValueError(f"{typed!r} is already in the taxonomy")
    if canonical not in taxonomy:
        raise ValueError(f"{canonical!r} is not in the taxonomy")
    if taxonomy[canonical].get("alias_of"):
        # Aliases of aliases would make load_taxonomy()'s single-hop resolution wrong.
        raise ValueError(f"{canonical!r} is itself an alias of "
                         f"{taxonomy[canonical]['alias_of']!r}; point at that instead")
    taxonomy[typed] = {"alias_of": canonical}
    ordered = {k: taxonomy[k] for k in sorted(taxonomy)}
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")


def resolve(names: list[str], taxonomy: dict, *, interactive: bool,
            out=None) -> tuple[dict[str, str], list[str]]:
    """Offer a match for every unknown name. Returns (accepted, still unknown).

    Nothing is written without a person typing a number. The alternative - accepting the
    top candidate above some threshold - is what merges `3" Conv Block Pull` into
    `3" Sumo Block Pull` one quiet evening and puts two lifts' histories in one series.
    """
    import sys as _sys

    out = out or _sys.stderr
    accepted: dict[str, str] = {}
    unresolved: list[str] = []
    for name in names:
        offered = candidates(name, taxonomy, limit=5)
        print("", file=out)
        print(format_candidates(name, offered), file=out)
        if not interactive or not offered:
            record(name, offered, None)
            unresolved.append(name)
            continue
        print("  n. none of these - it is a new exercise", file=out)
        try:
            answer = input("  pick a number, or n: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("", file=out)
            record(name, offered, None)
            unresolved.append(name)
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(offered):
            chosen = offered[int(answer) - 1][0]
            add_alias(name, chosen)
            record(name, offered, chosen)
            accepted[name] = chosen
            print(f"  {name!r} is now an alias of {chosen!r} in config/exercises.json",
                  file=out)
        else:
            record(name, offered, None)
            unresolved.append(name)
    return accepted, unresolved
