#!/usr/bin/env python3
"""Render the Iron Log Liquid templates and assert on the output.

    pip install python-liquid
    python kibana/verify_liquid.py

Why this exists: a custom-content template is invisible until it is imported, and a
render error takes the whole panel blank rather than failing loudly. Every Liquid bug
found in this project so far was caught by a test and not by reading the code:

  * `nil | round` is 0, so an unlogged value printed a confident "0"
  * `rpe_class` compared `nil >= 9`, a render error that blanks the panel, on any
    session containing a warm-up
  * `num()` wraps its expression in an `{% if %}`, and Liquid cannot take a filter
    inside a condition

Three sections:

  1. num() and rpe_class(), the two helpers every card depends on
  2. a generic pass over EVERY template in templates.py: rendered with no rows, and
     rendered with one row in which every column it references is nil. That second
     case is the shape both nil bugs had.
  3. the Overview Signal cards, in detail, including the real data that motivated
     their design

This is not the suite referenced in the Sept 4 docs. That file was never committed to
either repo and git has never seen it; these assertions were written fresh.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone

try:
    from liquid import Environment
except ImportError:
    sys.exit("error: pip install python-liquid")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import templates as tpl  # noqa: E402

env = Environment()

PASSED = 0
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSED
    if ok:
        PASSED += 1
    else:
        FAILED.append(f"{name}{(' — ' + detail) if detail else ''}")


def rows_of(*dicts) -> list[dict]:
    """Kibana hands Liquid `rows`, each a map of column -> {value, pct}."""
    return [{k: {"value": v, "pct": 100} for k, v in d.items()} for d in dicts]


def render(template: str, rows: list[dict]) -> str:
    return env.from_string(template).render(rows=rows)


def has(name: str, out: str, text: str) -> None:
    check(name, text in out, f"expected {text!r} in output")


def lacks(name: str, out: str, text: str) -> None:
    check(name, text not in out, f"did not expect {text!r} in output")


def band(name: str, out: str, cls: str) -> None:
    """Assert the verdict carries this band.

    Not `has(out, "b-max")` — SIGNAL_CSS defines every band class, so that string is
    present in every render and the assertion never fails. It has to be the rendered
    class attribute.
    """
    check(name, f'class="verdict {cls}"' in out, f"verdict is not {cls}")


def unbanded(name: str, out: str, cls: str) -> None:
    check(name, f'class="verdict {cls}"' not in out, f"verdict should not be {cls}")


def balanced(name: str, out: str) -> None:
    check(f"{name}: divs balanced", out.count("<div") == out.count("</div>"),
          f"{out.count('<div')} open vs {out.count('</div>')} close")


# ============================================================ 1. helpers

def section_helpers() -> None:
    def n(value, dp=0):
        return render(tpl.num("rows[0]['v'].value", dp), rows_of({"v": value}))

    for value, want in [(0, "0"), (1, "1"), (42, "42"), (999, "999"), (1000, "1,000"),
                        (14145, "14,145"), (99999, "99,999"), (999999, "999,999"),
                        (1000000, "1,000,000"), (5995467, "5,995,467"),
                        (123456789, "123,456,789")]:
        check(f"num({value})", n(value) == want, f"got {n(value)!r}, want {want!r}")

    # The nil guard is the whole point: `nil | round` is 0 and would print a
    # confident zero for a value that was never logged.
    check("num(nil) renders nothing", n(None) == "", f"got {n(None)!r}")
    # 0 is truthy in Liquid, so a real zero still has to print.
    check("num(0) still prints", n(0) == "0", f"got {n(0)!r}")
    check("num decimal", n(1234.56, 1) == "1,234.6", f"got {n(1234.56, 1)!r}")
    check("num decimal under 1000", n(6.26, 1) == "6.3", f"got {n(6.26, 1)!r}")

    def rc(value):
        return render(tpl.rpe_class("rows[0]['r'].value") + "{{ rc }}", rows_of({"r": value}))

    for value, want in [(None, "lo"), (0, "lo"), (6, "lo"), (6.9, "lo"), (7, "mid"),
                        (7.9, "mid"), (8, "hi"), (8.9, "hi"), (9, "max"), (10, "max")]:
        check(f"rpe_class({value})", rc(value) == want, f"got {rc(value)!r}, want {want!r}")


# ============================================================ 2. every template

COL = re.compile(r"\[' ?([A-Za-z0-9_.@]+) ?'\]")


def section_all_templates() -> None:
    """Every template must survive no rows, and one row of all-nil columns.

    Those are the two states a live panel actually hits: a filter that matches
    nothing, and a session missing an optional field.
    """
    candidates = []
    for name in dir(tpl):
        if name.startswith("__"):
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str) or ("{%" not in value and "{{" not in value):
            continue
        if not value.lstrip().startswith("<style") and "<div" not in value:
            continue
        if "$" in value:
            continue  # an unfilled placeholder; covered via its factory below
        candidates.append((name, value))
    candidates.append(("total_card()", tpl.total_card(909.4)))
    candidates.append(("metric_card()", tpl.metric_card("Bodyweight", "lb")))

    seen = 0
    for name, value in candidates:
        seen += 1
        try:
            out = render(value, [])
        except Exception as exc:  # noqa: BLE001
            check(f"{name}: renders with no rows", False, f"{type(exc).__name__}: {exc}")
            continue
        check(f"{name}: renders with no rows", True)
        balanced(f"{name} (empty)", out)

        cols = sorted(set(COL.findall(value)))
        if not cols:
            continue
        try:
            out = render(value, rows_of({c: None for c in cols}))
        except Exception as exc:  # noqa: BLE001
            check(f"{name}: renders with all-nil row", False, f"{type(exc).__name__}: {exc}")
            continue
        check(f"{name}: renders with all-nil row", True)
        balanced(f"{name} (nil row)", out)
        # A card that has no value to show must not assert one.
        lacks(f"{name}: no bare nil leaked", out, "nil")

    check("found templates to check", seen >= 15, f"only saw {seen}")


# ============================================================ 3. Signal cards

def week(heavy, tot):
    return {"iso_week": "2026-W00", "heavy": heavy, "tot": tot}


# The real trailing 13 weeks off the cluster, newest first. W32 is the trap the
# design review turned on: four main-lift reps in the week, all of them heavy.
REAL_WEEKS = [week(5, 57), week(0, 10), week(0, 36), week(0, 38), week(4, 4),
              week(0, 99), week(0, 100), week(12, 44), week(3, 98), week(0, 102),
              week(0, 112), week(26, 62), week(0, 96)]


def section_intensity() -> None:
    t = tpl.SIGNAL_INTENSITY

    out = render(t, [])
    has("intensity: no rows", out, "No weekly rollup yet.")
    balanced("intensity (no rows)", out)

    out = render(t, rows_of(week(0, 0), week(3, 40)))
    has("intensity: no main-lift reps", out, "No main-lift reps logged this week.")
    lacks("intensity: no zero verdict", out, "Heavier than")
    balanced("intensity (no main work)", out)

    out = render(t, rows_of(week(5, 57), week(0, 30), week(1, 40)))
    has("intensity: thin history says so", out, "Not enough weeks on record")
    lacks("intensity: thin history does not rank", out, "Heavier than 2")

    out = render(t, rows_of(*REAL_WEEKS))
    has("intensity: real verdict", out, "Heavier than 10 of your last 12 weeks.")
    has("intensity: real evidence", out, "<b>5</b> of 57 main-lift reps")
    has("intensity: real baseline", out, "your 12-week average: 3.8")
    band("intensity: band is heavy", out, "b-heavy")
    balanced("intensity (real)", out)

    # The regression this card exists to avoid. W32 as the current week scores 100%
    # of four reps; ranked by count it beats only the zero weeks and must not read
    # as the heaviest week on record.
    trap = [week(4, 4)] + [w for w in REAL_WEEKS if w["heavy"] != 4]
    out = render(t, rows_of(*trap))
    unbanded("intensity: W32 trap is not top-banded", out, "b-max")
    has("intensity: W32 trap ranks by count", out, "Heavier than 9 of your last 12 weeks.")

    top = [week(40, 90)] + REAL_WEEKS[1:]
    out = render(t, rows_of(*top))
    has("intensity: beats everything", out, "Heavier than any of your last 12 weeks.")
    band("intensity: top band", out, "b-max")

    bottom = [week(0, 90)] + [week(i + 1, 90) for i in range(12)]
    out = render(t, rows_of(*bottom))
    has("intensity: beats nothing", out, "Lighter than every one of your last 12 weeks.")
    band("intensity: light band", out, "b-light")

    # Null Prilepin buckets are why the query COALESCEs; the card must not crash
    # if one arrives null anyway.
    out = render(t, rows_of(week(None, None), *REAL_WEEKS[1:]))
    has("intensity: nil buckets", out, "No main-lift reps logged this week.")


def section_load() -> None:
    t = tpl.SIGNAL_LOAD

    def wk(acwr, band, month, mono=0.8):
        return {"iso_week": "2026-W00", "month_s": month, "acwr": acwr,
                "acwr_band": band, "monotony": mono}

    out = render(t, [])
    has("load: no rows", out, "No weekly rollup yet.")
    balanced("load (no rows)", out)

    out = render(t, rows_of(wk(None, None, "Sep 2026")))
    has("load: no acwr", out, "Not enough history yet.")
    balanced("load (no acwr)", out)

    # The real recent weeks. W35 is also "rising", so the precedent lookup has to
    # skip the contiguous run or it reports last week as the precedent.
    real = rows_of(
        wk(1.37, "rising", "Sep 2026", 1.09), wk(1.35, "rising", "Aug 2026"),
        wk(0.99, "steady", "Aug 2026"), wk(1.06, "steady", "Aug 2026"),
        wk(1.17, "steady", "Aug 2026"), wk(0.88, "steady", "Jul 2026"),
        wk(1.25, "steady", "Jul 2026"), wk(0.95, "steady", "Jul 2026"),
        wk(1.40, "rising", "Jul 2026"), wk(1.33, "rising", "Jul 2026"),
        wk(1.81, "spike", "Jun 2026"), wk(0.96, "steady", "Jun 2026"),
        wk(1.36, "rising", "May 2026"),
    )
    out = render(t, real)
    has("load: verdict", out, "Ramping.")
    has("load: pct above", out, "<b>37%</b> above")
    has("load: monotony", out, "Monotony 1.09")
    has("load: precedent", out, "The last two times you were here: <b>Jul 2026, May 2026</b>")
    lacks("load: skips the contiguous run", out, "Aug 2026")
    band("load: rising band", out, "b-heavy")
    balanced("load (real)", out)

    out = render(t, rows_of(wk(1.81, "spike", "Sep 2026"), wk(0.9, "steady", "Aug 2026")))
    has("load: spike verdict", out, "Sharp jump in load.")
    band("load: spike band", out, "b-max")
    has("load: no precedent", out, "No earlier week on record in this band.")

    out = render(t, rows_of(wk(0.76, "undertrained", "Sep 2026"),
                            wk(0.9, "steady", "Aug 2026"),
                            wk(0.7, "undertrained", "Mar 2026")))
    has("load: undertrained verdict", out, "Backing off.")
    band("load: undertrained band", out, "b-light")
    has("load: one precedent", out, "Last time you were here: <b>Mar 2026</b>")
    # A ratio below 1 must read as a positive number below the average, not -24%.
    has("load: reads below", out, "<b>24%</b> below")
    lacks("load: no negative percent", out, "-24")


def section_drift() -> None:
    t = tpl.SIGNAL_DRIFT
    now = datetime.now(timezone.utc)

    # A source assertion, because the two Liquid engines disagree and the local one
    # cannot reproduce the bug. python-liquid divides two integers into an integer;
    # Kibana's engine is JavaScript, where every number is a float, so the same
    # expression rendered "Calves: 17.02787037037037 days." on the live dashboard.
    # Same class as the "RPE 6.260000228881836" leak in the Sept 4 QA pass.
    divides = tpl.SIGNAL_DRIFT.count("divided_by: 86400")
    floored = tpl.SIGNAL_DRIFT.count("divided_by: 86400 | floor")
    check("drift: every day-gap is floored", divides == floored and divides == 2,
          f"{floored} of {divides} floored, expected 2 of 2")

    def group(name, days_ago, sessions):
        stamp = (now - timedelta(days=days_ago, hours=12)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return {"muscles_primary": name, "last_d": stamp, "sessions": sessions}

    out = render(t, [])
    has("drift: no rows", out, "No working sets in the last year.")
    balanced("drift (no rows)", out)

    # Groups trained fewer than six times a year have no meaningful cadence.
    out = render(t, rows_of(group("grip", 200, 5), group("core", 180, 3)))
    has("drift: nothing rankable", out, "Not enough repeat work yet")
    balanced("drift (unrankable)", out)

    # Everything inside its window. This is a real answer, not an empty state.
    out = render(t, rows_of(group("chest", 1, 120), group("lats", 1, 88),
                            group("quads", 4, 77)))
    has("drift: nothing drifting", out, "Nothing is drifting.")
    has("drift: counts what it checked", out, "All <b>3</b> muscle groups")
    band("drift: calm band", out, "b-normal")
    balanced("drift (calm)", out)

    # The real finding: calves at 17 days against a 6-day cadence.
    real = rows_of(group("rear-delt", 26, 17), group("adductors", 17, 9),
                   group("glute-medius", 17, 24), group("calves", 17, 58),
                   group("quads", 4, 77), group("chest", 1, 120))
    out = render(t, real)
    has("drift: real verdict", out, "Calves: 17 days.")
    has("drift: real cadence", out, "every <b>6</b>")
    band("drift: flagged band", out, "b-heavy")
    unbanded("drift: 2.7x is not top-banded", out, "b-max")
    balanced("drift (real)", out)
    # rear-delt at 26 days against a 21-day cadence is inside 2x and must not fire.
    lacks("drift: rear-delt not flagged", out, "Rear delt")
    lacks("drift: adductors not flagged", out, "Adductors")

    # A second flagged group is listed under the headline, not promoted over it.
    two = rows_of(group("traps", 60, 20), group("calves", 40, 58), group("chest", 1, 120))
    out = render(t, two)
    has("drift: headline is the first", out, "Traps: 60 days.")
    has("drift: second listed", out, "Calves 40d")
    # 40 days against a 6-day cadence is 6.4x; the gauge tops out rather than
    # overflowing its track.
    has("drift: gauge capped", out, "width:100%")
    balanced("drift (two)", out)


# Fields mapped float in schema/mappings, plus the ES|QL aliases the templates give
# them. Rendering one of these raw prints the full float32 expansion in Kibana's
# JavaScript Liquid — "7.130000114440918 avg RPE" — while python-liquid renders it
# clean, so no amount of local rendering catches it. Only a source check does.
FLOAT_COLUMNS = {
    "duration_min", "environment.temp_f", "environment.humidity_pct",
    "metrics.bodyweight_lb", "metrics.sleep_hrs", "totals.tonnage_lb",
    "avg_working_rpe", "inol_total", "fatigue_index", "density_lb_per_min", "load_au",
    "weight_lb", "weight_each_lb", "reps", "rpe", "est_e1rm", "volume_lb",
    "intensity_pct", "inol", "work_ftlb", "tut_sec", "distance_ft",
    "weight_kg", "total_kg", "total_lb", "dots", "bodyweight_kg", "bodyweight_lb",
    "acwr", "monotony", "strain", "load_7d", "load_28d", "projected_total_lb",
    "inol_hardest", "tonnage_lb",
    # ES|QL aliases
    "e1", "lb", "kg", "avg", "ton", "top", "v", "cad",
}

RAW_RENDER = re.compile(r"\{\{\s*[A-Za-z0-9_\[\]'.]*\['([^']+)'\]\.value\s*\}\}")


def section_float_leaks() -> None:
    for name in dir(tpl):
        if name.startswith("__"):
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str) or "{{" not in value:
            continue
        for col in RAW_RENDER.findall(value):
            check(f"{name}: {col} is not rendered raw", col not in FLOAT_COLUMNS,
                  "float field needs | round, | round: 1 or num()")


# num() ends in `{%- endif -%}`, and Liquid's `-%}` strips the whitespace that
# follows it, so a literal " lb" written after a num() call renders as "909.4lb".
# The check runs on the assembled template, not the source: in templates.py these
# are Python concatenations, and the two halves only meet at import time.
UNIT_AFTER_NUM = re.compile(r"\{%- endif -%\}\{%- endif -%\}(&nbsp;|\s)?([A-Za-z%]+)")


def section_unit_spacing() -> None:
    for name in dir(tpl):
        if name.startswith("__"):
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str):
            continue
        for sep, unit in UNIT_AFTER_NUM.findall(value):
            check(f"{name}: space before {unit!r} survives num()", sep == "&nbsp;",
                  "a plain space after num() is stripped by `-%}`; use &nbsp;")


def main() -> None:
    section_unit_spacing()
    section_float_leaks()
    section_helpers()
    section_all_templates()
    section_intensity()
    section_load()
    section_drift()

    total = PASSED + len(FAILED)
    if FAILED:
        print(f"{PASSED}/{total} ok, {len(FAILED)} FAILED\n")
        for line in FAILED:
            print(f"  FAIL  {line}")
        sys.exit(1)
    print(f"{PASSED}/{total} ok")


if __name__ == "__main__":
    main()
