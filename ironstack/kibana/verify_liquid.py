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
import build_dashboards as bd  # noqa: E402
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


def fixture_is_real(qname: str, row: dict) -> None:
    """A fixture may not invent a column the panel's query does not project.

    This is the test-side half of the lint added to build_dashboards.check() on
    2026-09-05. SIGNAL_LOAD's comeback branch could not fire for weeks because
    sig_load's KEEP projected neither acwr_off_layoff nor chronic_days_trained, and
    eight assertions in this file passed straight over the gap because the fixture
    they ran against invented both columns. A test that supplies data the panel can
    never receive is not a test, and this is how that stops being possible.
    """
    keep = bd._keep_columns(bd.Q[qname])
    check(f"{qname}: the query has a KEEP to check against", keep is not None,
          "no KEEP clause; the fixture cannot be verified")
    if keep is None:
        return
    for col in sorted(row):
        check(f"{qname} fixture: {col!r} is projected", bd._projected(col, keep),
              f"{col!r} is not in the query's KEEP, so no panel will ever see it")


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
        if not isinstance(value, str) or "<div" not in value:
            continue
        if "$" in value:
            continue  # an unfilled placeholder; covered via its factory below
        candidates.append((name, value))

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

def week(heavy, tot, state="closed", available=None):
    return {"iso_week": "2026-W00", "week_end": "2026-09-06", "week_state": state,
            "weeks_available": available, "heavy": heavy, "tot": tot}


# The real trailing 13 weeks off the cluster, newest first. W32 is the trap the
# design review turned on: four main-lift reps in the week, all of them heavy.
REAL_WEEKS = [week(5, 57), week(0, 10), week(0, 36), week(0, 38), week(4, 4),
              week(0, 99), week(0, 100), week(12, 44), week(3, 98), week(0, 102),
              week(0, 112), week(26, 62), week(0, 96)]


def section_intensity() -> None:
    t = tpl.SIGNAL_INTENSITY
    fixture_is_real("sig_intensity", week(5, 57))

    out = render(t, [])
    has("intensity: no rows", out, "No signal rows came back")
    lacks("intensity: no rows does not blame the rollup", out, "No weekly rollup yet")
    balanced("intensity (no rows)", out)

    out = render(t, rows_of(week(0, 0), week(3, 40)))
    has("intensity: no main-lift reps", out, "No main-lift reps logged this week.")
    lacks("intensity: no zero verdict", out, "Heavier than")
    balanced("intensity (no main work)", out)

    out = render(t, rows_of(week(5, 57), week(0, 30), week(1, 40)))
    has("intensity: thin history says so", out, "needs 4 earlier weeks")
    has("intensity: thin history counts what it has", out, "You have <b>2</b>")
    lacks("intensity: thin history does not rank", out, "Heavier than 2")

    # weeks_available is the indexer's count of closed weeks with main-lift work. The
    # query is LIMIT 13, so counting returned rows told a lifter with forty weeks behind
    # them that the log was thin.
    out = render(t, rows_of(week(5, 57, available=31), week(0, 30), week(1, 40)))
    has("intensity: thin history uses weeks_available", out, "You have <b>31</b>")
    lacks("intensity: thin history does not count rows", out, "You have <b>2</b>")

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

    # --- ties. `beat` incremented only on a strict <, so a tie counted as a loss.
    # Thirteen weeks of heavy = 0 is an ordinary hypertrophy block and it rendered
    # "Lighter than every one of your last 12 weeks" under evidence reading 0 of 80.
    flat = [week(0, 80) for _ in range(13)]
    out = render(t, rows_of(*flat))
    has("intensity: thirteen zero weeks read as level", out, "Level with your last 12 weeks.")
    lacks("intensity: thirteen zero weeks are not the lightest ever", out, "Lighter than every one")
    has("intensity: thirteen zero weeks keep the evidence", out, "<b>0</b> of 80 main-lift reps")
    band("intensity: a level week lands mid-scale", out, "b-normal")
    balanced("intensity (flat zeroes)", out)

    same = [week(10, 90) for _ in range(5)]
    out = render(t, rows_of(*same))
    has("intensity: five identical weeks read as level", out, "Level with your last 4 weeks.")
    band("intensity: five identical weeks land mid-scale", out, "b-normal")
    balanced("intensity (identical)", out)

    # A tie in the middle of a mixed history is scored at half, not at zero.
    mixed = [week(6, 90), week(6, 90), week(2, 90), week(3, 90),
             week(9, 90), week(11, 90), week(1, 90)]
    out = render(t, rows_of(*mixed))
    has("intensity: mixed week ranks", out, "Heavier than 3 of your last 6 weeks.")
    has("intensity: mixed week names the tie", out, "Level with 1 of them.")
    balanced("intensity (mixed)", out)

    # Level with some, under the rest: neither "lighter than every one" nor a rank.
    under = [week(4, 90), week(4, 90), week(9, 90), week(9, 90), week(9, 90)]
    out = render(t, rows_of(*under))
    has("intensity: level with some, under the rest", out,
        "Level with 1 of your last 4 weeks, under the rest.")
    balanced("intensity (level-under)", out)

    # --- the week in progress has to say so, in both branches
    out = render(t, rows_of(week(5, 57, state="in-progress"), *REAL_WEEKS[1:]))
    has("intensity: an open week says so", out, "this week is still open")
    out = render(t, rows_of(week(5, 57, state="in-progress"), week(1, 40)))
    has("intensity: an open week says so under the threshold too", out, "this week is still open")
    out = render(t, rows_of(*REAL_WEEKS))
    lacks("intensity: a closed week does not", out, "this week is still open")

    # Null Prilepin buckets are why the query COALESCEs; the card must not crash
    # if one arrives null anyway.
    out = render(t, rows_of(week(None, None), *REAL_WEEKS[1:]))
    has("intensity: nil buckets", out, "No main-lift reps logged this week.")


def section_load() -> None:
    t = tpl.SIGNAL_LOAD

    def wk(acwr, band, month, mono=0.8, trained=16, off=False):
        return {"iso_week": "2026-W00", "month_s": month, "acwr": acwr,
                "acwr_band": band, "monotony": mono,
                "chronic_days_trained": trained, "acwr_off_layoff": off}

    fixture_is_real("sig_load", wk(1.0, "steady", "Sep 2026"))

    out = render(t, [])
    has("load: no rows", out, "No signal rows came back")
    lacks("load: no rows does not blame the rollup", out, "No weekly rollup yet")
    balanced("load (no rows)", out)

    out = render(t, rows_of(wk(None, None, "Sep 2026")))
    has("load: no acwr", out, "needs 28 days of load")
    has("load: no acwr counts weeks", out, "<b>1</b> week logged")
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
    has("load: no precedent", out, "No earlier week in your whole log in this band.")
    lacks("load: precedent is not range-scoped", out, "in this range")

    # A ratio off a layoff. Three blank weeks make chronic equal acute, so 4.0 arrives
    # before a single hard set - the card must not call that a spike and tell a lifter
    # coming back to do less. The indexer flags the week; this is the card honouring it.
    out = render(t, rows_of(wk(4.0, "spike", "Sep 2026", trained=4, off=True),
                            wk(1.0, "steady", "Aug 2026")))
    has("load: comeback is not a spike", out, "Coming back.")
    has("load: comeback shows the base it has", out, "<b>4</b> of the last 28 days")
    has("load: comeback says the ratio is arithmetic", out, "arithmetic rather than a spike")
    lacks("load: comeback drops the spike wording", out, "Sharp jump in load")
    lacks("load: comeback drops the percentage claim", out, "above")
    # "the last two times you were here" is scoped to a band this branch declines to claim.
    lacks("load: comeback drops the band precedent", out, "you were here")
    band("load: comeback is not top-banded", out, "b-normal")
    balanced("load (comeback)", out)

    # And the same week without the flag still bands normally, so the guard is not
    # swallowing real spikes.
    out = render(t, rows_of(wk(4.0, "spike", "Sep 2026", trained=18),
                            wk(1.0, "steady", "Aug 2026")))
    has("load: a real spike still bands", out, "Sharp jump in load.")
    lacks("load: a real spike is not a comeback", out, "Coming back.")

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
    # Two now, not three: the third lived in the Phase 0 span check, which the signals
    # index retired. The lint is the count matching, not the number 3.
    divides = tpl.SIGNAL_DRIFT.count("divided_by: 86400")
    floored = tpl.SIGNAL_DRIFT.count("divided_by: 86400 | floor")
    check("drift: every day-gap is floored", divides == floored and divides == 2,
          f"{floored} of {divides} floored, expected 2 of 2")

    # A row from ironstack-signals: the window was applied by derive.signal_docs at index
    # time, so last_trained is a plain keyword date and cadence arrives precomputed rather
    # than being derived as 365/n in the template.
    def group(name, days_ago, sessions, cadence=None):
        stamp = (now - timedelta(days=days_ago, hours=12)).strftime("%Y-%m-%d")
        return {"muscle": name, "last_trained": stamp, "sessions": sessions,
                "cadence_days": round(365 / sessions, 2) if cadence is None else cadence,
                "computed_through": now.strftime("%Y-%m-%d")}

    fixture_is_real("sig_drift", group("calves", 17, 58))

    out = render(t, [])
    # Not "no working sets in the last year": zero rows means unindexed or filtered, and
    # the card must not claim to know which.
    has("drift: no rows", out, "No signal rows came back")
    has("drift: no rows names the filter bar", out, "filter bar")
    has("drift: no rows says the picker is not the cause", out, "ignores the time picker")
    lacks("drift: no rows does not claim an empty year", out, "No working sets")
    balanced("drift (no rows)", out)

    # Groups trained fewer than six times a year have no meaningful cadence.
    out = render(t, rows_of(group("grip", 200, 5), group("core", 180, 3)))
    has("drift: nothing rankable", out, "needs 6 sessions in a year")
    has("drift: nothing rankable counts groups", out, "None of your <b>2</b>")
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

    # The picker can no longer cut the year - these rows are windowed at index time by
    # derive.signal_docs, and ironstack-signals has no date field for the picker to filter
    # on. So the Phase 0 span check is gone, and with it the "widen the time picker" copy.
    lacks("drift: no stale widen hint", out, "widen the time picker")
    lacks("drift: no stale range language", out, "the page is showing")

    # Cadence is read from the row now instead of being derived as 365/n, so for the first
    # time it can be absent. Unguarded that is `divided_by: 0`, which throws and renders
    # the panel blank - a verdict card showing nothing at all. Caught by this suite on
    # Sept 5 before it reached the browser.
    no_cad = rows_of(group("calves", 17, 58, cadence=0), group("chest", 1, 120))
    out = render(t, no_cad)
    check("drift: a cadence-less group cannot blank the card", "Calves" not in out,
          "a row with no cadence was ranked anyway")
    balanced("drift (no cadence)", out)

    # And the freshness stamp, because staleness is the failure mode this index has.
    out = render(t, rows_of(group("calves", 17, 58), group("chest", 1, 120)))
    has("drift: says when it was computed", out, "from the whole log, indexed")

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
    "inol_hardest", "tonnage_lb", "cum_tonnage_lb", "top_pct",
    "heavy_per_session", "peer_heavy_per_session", "share_pct", "peer_share_pct",
    "tonnage_per_session", "peer_tonnage_per_session", "platformed_pct",
    "peer_pct", "expected_lb",
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


# Columns carrying text a human typed, or a keyword the indexer copied out of one. A
# raw render of any of these puts whatever was in the log straight into the card's HTML.
# The panel sandbox strips <a> and <script>, so the live blast radius is layout rather
# than script execution - but a note containing "<div" silently breaks the card it is on,
# and the suite never saw it because until 2026-09-05 the only value it ever fed a text
# column was nil. Same shape as FLOAT_COLUMNS above: a source check, because the bug is
# invisible in a render that happens to use clean data.
TEXT_COLUMNS = {
    "item", "text", "notes", "gear_s", "gear_notes", "wrap_up", "tags_s", "watch_s",
    "exercise.name", "exercise.category", "location.name", "environment.conditions",
    "environment.wind", "environment.setting", "program.name", "program.block",
    "program.phase", "session_id", "prev_session_id", "next_session_id", "start_time",
    "time_of_day", "set_type", "phase", "lift", "lift_slug", "lift_name", "name", "fam",
    "muscle", "block", "block_role", "cycle", "cycle_label", "cycle_role", "week_state",
    "iso_week", "tag", "acwr_band", "acwr_gloss", "inol_hardest_band",
    "inol_hardest_lift", "inol_hardest_gloss", "meet_id",
    "date_s", "meet_s", "last_s", "when_s", "month_s", "notes_from", "computed_through",
    "last_trained", "first_trained", "peer_from", "peer_to", "week_end",
}

OUTPUT_TAG = re.compile(r"\{\{(?P<body>[^{}]*)\}\}")
COL_IN_TAG = re.compile(r"\['([^']+)'\]\.value")


def section_escaping() -> None:
    for name in dir(tpl):
        if name.startswith("__"):
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str) or "{{" not in value:
            continue
        for m in OUTPUT_TAG.finditer(value):
            body = m.group("body")
            cols = COL_IN_TAG.findall(body)
            if not cols or cols[0] not in TEXT_COLUMNS:
                continue
            check(f"{name}: {cols[0]} is escaped", "escape" in body,
                  f"text column rendered raw: {{{{{body}}}}}")


def section_escaping_renders() -> None:
    """The other half: actually push markup and an ampersand through a card.

    balanced() is the assertion that matters. An unescaped "<div" arrives with no
    closing tag, so the card's own div count stops matching and the panel renders
    with the rest of its content swallowed by the stray element.
    """
    # Deliberately unbalanced. A closed <div> escapes into the card without tripping
    # balanced(), which is exactly the note that would slip through: the failure a lifter
    # actually sees is an unterminated tag swallowing the rest of the panel.
    nasty = '<div onclick="x">bench & press'

    out = render(tpl.NOTES_CARD, rows_of({"session_id": "s1", "order": 1, "phase": "pre",
                                          "exercise.name": nasty, "text": nasty,
                                          "tags_s": "grip|<b>bold</b>"}))
    balanced("escaping: a note carrying markup", out)
    # python-liquid emits &quot;; Kibana's JavaScript Liquid emits &#34;. Assert on the
    # part both agree about rather than on one engine's entity spelling.
    has("escaping: the note is escaped", out, "&lt;div onclick=")
    lacks("escaping: the raw tag is gone", out, "<div onclick")
    has("escaping: the ampersand is escaped", out, "bench &amp; press")
    lacks("escaping: no live attribute survives", out, 'onclick="x"')
    has("escaping: a tag is escaped too", out, "&lt;b&gt;bold&lt;/b&gt;")

    out = render(tpl.RECENT_NOTES, rows_of({"date_s": "Sep 4", "phase": "wrap",
                                            "exercise.name": nasty, "text": nasty,
                                            "tags_s": "grip"}))
    balanced("escaping: recent notes", out)
    has("escaping: recent notes escaped", out, "&amp;")

    out = render(tpl.WATCH_CARD, rows_of({"date_s": "Sep 4", "item": nasty}))
    balanced("escaping: a watch item", out)
    lacks("escaping: watch item has no raw div", out, '<div onclick')

    out = render(tpl.WRAP_CARD, rows_of({"wrap_up": nasty, "gear_notes": nasty,
                                         "watch_s": nasty + "|" + nasty}))
    balanced("escaping: a wrap-up and its watch items", out)
    has("escaping: wrap-up escaped", out, "&lt;div")

    out = render(tpl.PERFORMANCE_CARD, rows_of(
        {"session_id": "s1", "set_number": 1, "exercise.name": nasty,
         "exercise.category": "main", "set_type": "working", "load_type": "barbell",
         "weight_lb": 315, "reps": 3, "rep_unit": "reps", "distance_ft": None,
         "rpe": 8, "gear_s": nasty, "notes": nasty}))
    balanced("escaping: an exercise name and a set note", out)
    has("escaping: the exercise name is escaped", out, "&lt;div onclick")

    out = render(tpl.SESSION_HEADER, rows_of(
        {"program.name": nasty, "program.block": nasty, "program.week": 1,
         "program.day": 2, "program.total_days": 12, "date_s": "Sep 4",
         "start_time": "06:00", "time_of_day": "morning", "location.name": nasty,
         "location.travel": False, "prev_session_id": "2026-09-03",
         "next_session_id": "2026-09-05"}))
    balanced("escaping: a location and a program name", out)
    has("escaping: the location is escaped", out, "&lt;div onclick")

    out = render(tpl.CONDITIONS_CARD, rows_of(
        {"environment.temp_f": 71, "environment.humidity_pct": 40,
         "environment.conditions": nasty, "environment.wind": nasty,
         "environment.setting": nasty, "time_of_day": "morning"}))
    balanced("escaping: the conditions line", out)
    has("escaping: conditions escaped", out, "&lt;div onclick")

    out = render(tpl.SIGNAL_TAGS, rows_of(tag_row(nasty, 9, 5, prior=1, span=60, notes=210)))
    balanced("escaping: a tag in the verdict", out)
    lacks("escaping: no raw div in a verdict", out, "<div onclick")

    out = render(tpl.SIGNAL_DRIFT, rows_of(
        {"muscle": nasty, "sessions": 20, "cadence_days": 6.0,
         "last_trained": "2020-01-01", "computed_through": "2026-09-05"}))
    balanced("escaping: a muscle name in the verdict", out)
    lacks("escaping: no raw div in the drift verdict", out, "<div onclick")


# num() ends in `{%- endif -%}`, and Liquid's `-%}` strips the whitespace that
# follows it, so a literal " lb" written after a num() call renders as "909.4lb".
# The check runs on the assembled template, not the source: in templates.py these
# are Python concatenations, and the two halves only meet at import time.
UNIT_AFTER_NUM = re.compile(r"\{%- endif -%\}\{%- endif -%\}(&nbsp;|\s)?([A-Za-z%]+)")


# The same trap on the other end: num() OPENS with `{%- if`, and `{%-` strips the
# whitespace BEFORE it, so a literal "best e1RM " written ahead of a num() call renders
# as "best e1RM420". Found on the Lift header 2026-09-05, after the trailing-side check
# above had been passing for weeks. Matched on `{%- assign _n`, which only num() emits.
UNIT_BEFORE_NUM = re.compile(r"([A-Za-z0-9%])(&nbsp;|\s)?\{%- if [^{}]*?-%\}\{%- assign _n")


def section_unit_spacing_before() -> None:
    for name in dir(tpl):
        if name.startswith("__"):
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str):
            continue
        for last_char, sep in UNIT_BEFORE_NUM.findall(value):
            check(f"{name}: space after {last_char!r} survives into num()", sep == "&nbsp;",
                  "a plain space before num() is stripped by `{%-`; use &nbsp;")


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


# The real comp-deadlift series off the cluster, newest first. The point of these
# numbers is the noise: 243 to 383 across seven months, because a confident e1RM comes
# from whatever the day's top working set was. Ranking session against session here
# would have produced a verdict that flipped weekly.
DEADLIFT = [339.1, 243.6, 360.9, 330.9, 346.5, 312.9, 347.8, 308.8, 321.6, 324.2,
            308.8, 297.1, 347.8, 346.5, 383.4, 352.5, 314.4, 351.5, 340.5, 353.4]


def lift_rows(values, slug="comp-deadlift", when="Jul 2026"):
    return [{"session_id": f"s{i}", "lift_slug": slug, "when_s": when, "e1": v}
            for i, v in enumerate(values)]


def section_lift() -> None:
    t = tpl.SIGNAL_LIFT
    fixture_is_real("sig_lift", lift_rows([300.0])[0])

    out = render(t, [])
    has("lift: no rows", out, "No confident estimates for this lift yet.")
    balanced("lift (no rows)", out)

    out = render(t, rows_of(*lift_rows([340.0, 300.0, 320.0])))
    has("lift: thin history", out, "needs 5 sessions carrying a confident")
    has("lift: thin history counts what it has", out, "You have <b>3</b>")
    lacks("lift: thin history does not rank", out, "under your best")
    balanced("lift (thin)", out)

    # The real case: recent best 360.9 against a peak of 420.4 set in Mar 2025 — a peak
    # that sits outside the last 20 sessions entirely, which is why the card reads the
    # whole range and not a recent window.
    real = lift_rows(DEADLIFT) + lift_rows([420.4], when="Mar 2025")
    out = render(t, rows_of(*real))
    has("lift: real verdict", out, "14% under your best.")
    band("lift: real band", out, "b-normal")
    has("lift: recent best", out, "Recent best <b>361</b> lb")
    has("lift: peak and date", out, "your best <b>420</b> lb, Mar 2025.")
    has("lift: gauge", out, "width:86%")
    has("lift: direction", out, "Up <b>4%</b> on the five sessions before.")
    balanced("lift (real)", out)

    out = render(t, rows_of(*lift_rows([500.0] + DEADLIFT)))
    has("lift: at best", out, "At your best.")
    band("lift: at-best band", out, "b-max")

    out = render(t, rows_of(*lift_rows([380.0, 370.0, 360.0, 350.0, 340.0,
                                        330.0, 320.0, 310.0, 300.0, 400.0])))
    has("lift: close to best", out, "Close to your best.")
    band("lift: close band", out, "b-heavy")

    # Another lift's sessions must not leak into the ranking. With the control cleared
    # the query returns every lift, so the card follows rows[0]'s slug and ignores the
    # rest — bench at 900 here would otherwise blow the peak apart.
    mixed = []
    for i, v in enumerate(DEADLIFT):
        mixed.append({"session_id": f"d{i}", "lift_slug": "comp-deadlift",
                      "when_s": "Jul 2026", "e1": v})
        mixed.append({"session_id": f"b{i}", "lift_slug": "comp-bench",
                      "when_s": "Jul 2026", "e1": 900.0})
    out = render(t, rows_of(*mixed))
    has("lift: ignores other lifts", out, "your best <b>383</b> lb")
    lacks("lift: no cross-lift gap", out, "60% under your best.")
    balanced("lift (mixed)", out)

    # Exactly five sessions: there is no earlier five to compare against, so the
    # direction line must be absent rather than dividing by zero.
    out = render(t, rows_of(*lift_rows([360.0, 350.0, 340.0, 330.0, 320.0])))
    has("lift: five sessions still ranks", out, "At your best.")
    lacks("lift: no direction without a prior five", out, "sessions before")


ORPHAN_EXEMPT = {"BASE_CSS", "SIGNAL_CSS", "TOKENS", "DAYS_TO_MEET"}


def section_orphans() -> None:
    """Every template in templates.py must be reachable from a dashboard.

    build_dashboards.py --check catches saved objects that nothing references. This is
    the same check one layer up: a card nothing builds is invisible, untestable in
    practice, and quietly rots. DAYS_LIST sat dead for a day before this existed.
    """
    build = (__import__("pathlib").Path(__file__).resolve().parent / "build_dashboards.py").read_text()
    for name in dir(tpl):
        if name.startswith("_") or name in ORPHAN_EXEMPT:
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str) or "<div" not in value:
            continue
        base = name.rstrip("_")
        referenced = f"tpl.{name}" in build or f"{base.lower()}(" in build
        check(f"{name}: reachable from a dashboard", referenced,
              "defined in templates.py and built by nothing")


def section_total_card() -> None:
    """The label must report the window the picker actually left, not the one asked for,
    and the meet best has to come from the reader's own log or not be claimed at all."""
    t = tpl.TOTAL_CARD
    now = datetime.now(timezone.utc)

    def lift(name, e1, first_days_ago):
        return {"fam": name, "e1": e1, "meet_lb": None,
                "first_d": (now - timedelta(days=first_days_ago, hours=12)).strftime("%Y-%m-%dT%H:%M:%S.000Z")}

    def meet(lb):
        return {"fam": None, "e1": None, "first_d": None, "meet_lb": lb}

    fixture_is_real("total", lift("deadlift", 361.0, 88))

    lifts = [lift("deadlift", 361.0, 88), lift("squat", 283.0, 80), lift("bench", 228.0, 85)]
    out = render(t, rows_of(*(lifts + [meet(909.4)])))
    has("total: full window label", out, "best of the last 90 days")
    has("total: sum", out, "872")
    has("total: the meet best is the reader's own", out, "909.4")
    has("total: the comparison", out, "of your meet best")
    has("total: what is left to go", out, "37")
    lacks("total: no widen hint at full window", out, "widen the time picker")
    # The meet row carries no lift family and must not be drawn as a fourth lift.
    rowcount = out.count('class="liftrow"')
    check("total: the meet row is not a lift row", rowcount == 3, f"{rowcount} lift rows")
    balanced("total (full)", out)

    # No meet on record: the card says so rather than showing a percentage of nothing.
    out = render(t, rows_of(*lifts))
    has("total: still names the projection", out, "872")
    has("total: no meet says so", out, "No meet on the record yet")
    lacks("total: no percentage of nothing", out, "of your meet best")
    lacks("total: nothing to go", out, "to go")
    balanced("total (no meet)", out)

    out = render(t, rows_of(lift("deadlift", 339.0, 29), lift("squat", 276.0, 25),
                            lift("bench", 228.0, 28), meet(909.4)))
    has("total: narrow window says its width", out, "best of the last <span class=\"v\">29</span> days")
    has("total: narrow window says how to fix it", out, "widen the time picker")
    lacks("total: narrow window does not claim 90", out, "best of the last 90 days")
    balanced("total (narrow)", out)

    # No first_d at all (an older query shape): fall back to the plain label.
    out = render(t, rows_of({"fam": "deadlift", "e1": 361.0}))
    has("total: no first_d falls back", out, "best of the last 90 days")

    # Only the meet row came back: no main-lift work in the window, and the card must
    # not print a confident zero total.
    out = render(t, rows_of(meet(909.4)))
    has("total: no lifts says so", out, "No main-lift work in this window")
    lacks("total: no zero total", out, "class=\"hero\"")
    balanced("total (no lifts)", out)

    # The author's numbers must not be reachable from the template source at all.
    src = tpl.TOTAL_CARD
    check("total: no build-time meet best in the source", "909.4" not in src)
    check("total: no build-time DOTS in the source", "266.72" not in src)


def section_meet_cards() -> None:
    out = render(tpl.MEET_CARDS, rows_of({"meets": 1, "total_kg": 412.5, "total_lb": 909.4,
                                          "dots": 266.72, "made": 9, "attempts": 9}))
    has("meets: count says what it counts", out, "in the page's range")
    has("meets: success says what it counts", out, "100% made in range")
    lacks("meets: no 'logged' claim", out, "competitions logged")
    lacks("meets: no 'all meets' claim", out, "all meets")


def section_moat() -> None:
    """The trailing-90-day idea is the most defensible thing in the system and it was
    set in 10px grey. It now has to be in the evidence line of the intensity verdict."""
    out = render(tpl.SIGNAL_INTENSITY, rows_of(*REAL_WEEKS))
    has("moat: in the evidence line", out, "of your best in the last 90 days")
    has("moat: provenance says why", out, "Heavy means heavy for you now")
    # And the thin-history state tells the lifter what to do about the picker.
    out = render(tpl.SIGNAL_INTENSITY, rows_of(week(5, 57), week(0, 30), week(1, 40)))
    has("intensity: thin history still names the threshold", out, "needs 4 earlier weeks")
    # The 13 weeks come from ironstack-signals, so a short history is a short history -
    # not a picker the lifter can widen. Telling them to widen it would be a lie now.
    lacks("intensity: no stale widen hint", out, "widen it")
    lacks("intensity: no stale range language", out, "in the page's range")


def section_contrast() -> None:
    """No colour below 4.5:1 on either ground may style text a lifter has to read.

    FAINT is 2.5:1 on the panel ground. It is fine for a hairline or a separator and
    it was styling eyebrows, provenance, cold-start copy and the tagline that carries
    the product's one defensible idea.
    """
    def lum(h):
        r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    def ratio(a, b):
        la, lb = sorted((lum(a), lum(b)), reverse=True)
        return (la + .05) / (lb + .05)

    for name, colour in (("STEEL", tpl.STEEL), ("DIM", tpl.DIM), ("CHALK", tpl.CHALK)):
        for ground in (tpl.BG, tpl.PANEL):
            check(f"contrast: {name} on {ground} >= 4.5", ratio(colour, ground) >= 4.5,
                  f"{ratio(colour, ground):.2f}")
    faint = tpl.FAINT
    for cls in (".eyebrow{", ".sig .q{", ".sig .prov{", ".sig .none{", ".sig .base{", ".empty{",
                ".item .when{", ".faint{"):
        src = tpl.BASE_CSS + tpl.SIGNAL_CSS
        i = src.find(cls)
        rule = src[i:src.find("}", i)]
        check(f"contrast: {cls.rstrip('{')} is not FAINT", faint not in rule and "$FAINT" not in rule,
              "text role styled with a 2.5:1 colour")
    check("contrast: brand tagline is not FAINT", faint not in tpl.brand_bar("X", "y").split(".tagline")[1].split("}")[0])


def section_cold_start() -> None:
    """Week one through week twelve — the state that decides whether anyone stays.

    Every card must say what is accumulating and what unlocks it. "Not enough data" is
    the answer that loses a user who would have kept logging if they knew the payoff
    was six weeks out.
    """
    # A brand-new lifter: one week logged, nothing else.
    out = render(tpl.SIGNAL_INTENSITY, rows_of(week(2, 30)))
    has("cold intensity: still reports the count", out, "2 rep")
    has("cold intensity: names the threshold", out, "4 earlier weeks")
    has("cold intensity: counts what it has", out, "You have <b>0</b>")
    lacks("cold intensity: does not rank", out, "Heavier than")
    balanced("cold intensity", out)

    out = render(tpl.SIGNAL_LOAD, rows_of({"iso_week": "2026-W01", "month_s": "Jan 2026",
                                           "acwr": None, "acwr_band": None, "monotony": None}))
    has("cold load: names the threshold", out, "28 days of load")
    has("cold load: singular week", out, "<b>1</b> week logged")
    lacks("cold load: no verdict", out, "Ramping.")
    balanced("cold load", out)

    now = datetime.now(timezone.utc)
    # muscles_primary / last_d were the pre-signals column names and the card has not
    # read either since the index landed. A fixture on dead columns tests nothing, which
    # is why fixture_is_real() now runs over every one of them.
    thin = [{"muscle": m, "sessions": 2, "cadence_days": 40.0,
             "last_trained": (now - timedelta(days=5, hours=12)).strftime("%Y-%m-%d")}
            for m in ("chest", "quads", "lats")]
    out = render(tpl.SIGNAL_DRIFT, rows_of(*thin))
    has("cold drift: names the threshold", out, "6 sessions in a year")
    has("cold drift: counts groups seen", out, "None of your <b>3</b>")
    balanced("cold drift", out)

    out = render(tpl.SIGNAL_LIFT, rows_of(*lift_rows([300.0, 290.0])))
    has("cold lift: names the threshold", out, "needs 5 sessions")
    has("cold lift: counts what it has", out, "You have <b>2</b>")
    balanced("cold lift", out)


# --- taper -----------------------------------------------------------------
#
# The real rows off the repo, Sept 5 2026: a run-in one week old with that week
# still open, and two finished cycles behind it. The live state on the day the
# card shipped is the first case, so it is the one tested hardest.

def taper_row(cycle, label, role, wo, state="closed", days=3, ton=0.0, rpe=6.5,
              heavy=0, k=0, cum=0.0, cum_heavy=0, made=None, tot=None,
              absent_cum=False):
    """`absent_cum` drops the three cumulative columns from the row entirely.

    That is what the indexer now writes for a cycle with no closed week inside its
    run-in: absent, not zero. The distinction is the whole of the taper fix - `nil |
    plus: 0` is 0, so a card that does not check presence cannot tell "no closed weeks"
    from "the field did not arrive", and those want opposite sentences.
    """
    row = {
        "cycle": cycle, "cycle_label": label, "cycle_role": role,
        "week_state": state, "weeks_out": wo, "training_days": days,
        "tonnage_lb": ton, "avg_working_rpe": rpe,
        "attempts_made": made, "attempts_total": tot,
        "cum_weeks": k, "cum_tonnage_lb": cum, "cum_heavy": cum_heavy,
        "computed_through": "2026-09-05",
    }
    if absent_cum:
        for col in ("cum_weeks", "cum_tonnage_lb", "cum_heavy"):
            del row[col]
    return row


# Nov 2024 went nine for nine; Apr 2024 went six for nine. Weeks 8 and 7 out, in the
# order the ES|QL delivers them: cycle descending, weeks_out descending.
NOV = [taper_row("2024-11-16", "Nov 2024", "past", 8, ton=75340.0, rpe=6.44,
                 k=1, cum=75340.0, cum_heavy=0, made=9, tot=9),
       taper_row("2024-11-16", "Nov 2024", "past", 7, ton=92962.0, rpe=6.62,
                 k=2, cum=168302.0, cum_heavy=12, made=9, tot=9)]
APR = [taper_row("2024-04-06", "Apr 2024", "past", 8, ton=34140.0, rpe=6.6,
                 k=1, cum=34140.0, cum_heavy=3, made=6, tot=9),
       taper_row("2024-04-06", "Apr 2024", "past", 7, ton=47266.0, rpe=6.95,
                 k=2, cum=81406.0, cum_heavy=8, made=6, tot=9)]


def section_taper() -> None:
    T = tpl.SIGNAL_TAPER
    fixture_is_real("sig_taper", NOV[0])

    # --- the live case: week 8 open, nothing closed yet
    live = [taper_row("2026-10-24", "Oct 2026", "current", 8, state="in-progress",
                      days=4, ton=53915.0, rpe=6.94, k=0, cum=0.0)] + NOV + APR
    out = render(T, rows_of(*live))
    balanced("taper open week", out)
    has("taper open: names the week", out, "Week 8 of the run-in, still open")
    has("taper open: days so far", out, "<b>4</b>&nbsp;training days in")
    has("taper open: tonnage so far", out, "53,915")
    has("taper open: its own RPE", out, "6.9")
    has("taper open: the yardstick's finished week", out, "75,340")
    has("taper open: names the yardstick", out, "Nov 2024 closed the same week")
    has("taper open: declines to rank", out, "nothing is ranked until the week closes")
    # The whole point of the branch: no percentage, no gauge, no verdict class.
    lacks("taper open: no ratio", out, "% of Nov 2024")
    lacks("taper open: no gauge", out, 'class="gauge"')
    unbanded("taper open", out, "b-max")
    # Apr 2024 is on record but is not the yardstick, and must not be quoted as one.
    lacks("taper open: does not quote the worse meet", out, "Apr 2024 closed")

    # --- two closed weeks: the ratio branch, against the real numbers
    run = [taper_row("2026-10-24", "Oct 2026", "current", 8, ton=53915.0, rpe=6.94,
                     k=1, cum=53915.0, cum_heavy=5),
           taper_row("2026-10-24", "Oct 2026", "current", 7, ton=62000.0, rpe=6.8,
                     k=2, cum=115915.0, cum_heavy=9)]
    out = render(T, rows_of(*(run + NOV + APR)))
    balanced("taper ratio", out)
    # 115,915 / 168,302 = 68.9% -> 69
    has("taper ratio: the percentage is the verdict", out, "69% of Nov 2024's volume")
    has("taper ratio: closed-week count", out, "<b>2</b> closed weeks of the run-in")
    has("taper ratio: names the last week counted, not where the lifter stands",
        out, "Through week <b>7</b> out")
    has("taper ratio: its own tonnage", out, "115,915")
    has("taper ratio: the yardstick's", out, "168,302")
    has("taper ratio: the yardstick's attempt record", out, "9 for 9")
    has("taper ratio: heavy reps both ways", out, "you 9 &middot; Nov 2024 12")
    has("taper ratio: gauge", out, 'class="gauge"')
    has("taper ratio: tick is the yardstick", out, "tick marks Nov 2024's pace")
    band("taper ratio: under 70 is the loudest band", out, "b-max")

    # --- on pace reads as normal, ahead reads as loud, and neither throws
    for cum, want_pct, want_cls in ((160000.0, 95, "b-normal"),
                                    (185000.0, 110, "b-normal"),
                                    (230000.0, 137, "b-max"),
                                    (200000.0, 119, "b-heavy")):
        rows = [taper_row("2026-10-24", "Oct 2026", "current", 7, ton=cum, rpe=6.8,
                          k=2, cum=cum, cum_heavy=9)]
        out = render(T, rows_of(*(rows + NOV + APR)))
        has(f"taper band {want_pct}%", out, f"{want_pct}% of Nov 2024's volume")
        band(f"taper band {want_pct}% class", out, want_cls)

    # --- the yardstick is the attempt record, not recency
    # Give the older meet the better record and it has to become the yardstick.
    flipped = []
    for r in NOV:
        r = dict(r); r["attempts_made"] = 5
        flipped.append(r)
    for r in APR:
        r = dict(r); r["attempts_made"] = 9
        flipped.append(r)
    out = render(T, rows_of(*([taper_row("2026-10-24", "Oct 2026", "current", 7,
                                         ton=40000.0, k=2, cum=81406.0, cum_heavy=9)]
                              + flipped)))
    has("taper yardstick follows the record", out, "100% of Apr 2024's volume")

    # --- spans that do not match are refused rather than compared
    # The current cycle has two closed weeks; the yardstick's row at that distance
    # only has one behind it, so the totals cover different ground.
    short = [dict(NOV[1], cum_weeks=1, cum_tonnage_lb=92962.0), NOV[0]]
    out = render(T, rows_of(*([taper_row("2026-10-24", "Oct 2026", "current", 7,
                                         ton=62000.0, k=2, cum=115915.0)] + short)))
    balanced("taper mismatched span", out)
    has("taper mismatched span: names its own count", out, "<b>2</b> closed weeks behind it")
    has("taper mismatched span: names the peer's count", out, "<b>1</b> at the same distance")
    has("taper mismatched span: says what it is waiting for", out, "same number of closed")
    has("taper mismatched span: still names the window", out, "Through week <b>7</b> out")
    lacks("taper mismatched span: no ratio", out, "% of Nov 2024's volume")

    # --- the shape the widened index actually produces on 2026-09-05: seven weeks out,
    # the current cycle carrying seven closed weeks in its (widened) cumulative window,
    # the yardstick carrying one at the same distance. The old card divided across that
    # mismatch and would have printed 466% - as meaningless as the 0% the structural
    # zero used to produce. It has to decline and name both counts.
    wide = [taper_row("2026-10-24", "Oct 2026", "current", 7, ton=62000.0,
                      k=7, cum=159000.0, cum_heavy=9)]
    peer = [dict(NOV[1], cum_weeks=1, cum_tonnage_lb=34140.0),
            dict(NOV[0], cum_weeks=1, cum_tonnage_lb=34140.0)]
    out = render(T, rows_of(*(wide + peer)))
    balanced("taper widened window", out)
    has("taper widened: names its own count", out, "<b>7</b> closed weeks behind it")
    has("taper widened: names the peer's count", out, "<b>1</b> at the same distance")
    has("taper widened: says what it waits for", out, "same number of closed")
    lacks("taper widened: no percentage", out, "% of Nov 2024's volume")
    lacks("taper widened: no 466", out, "466")
    lacks("taper widened: no zero either", out, "0% of")
    lacks("taper widened: no gauge", out, 'class="gauge"')

    # --- the current closed row arrives with no cumulative columns at all
    out = render(T, rows_of(*([taper_row("2026-10-24", "Oct 2026", "current", 7,
                                         ton=62000.0, absent_cum=True)] + NOV + APR)))
    balanced("taper absent cum on the current row", out)
    has("taper absent cum: says it has none", out, "no closed week behind it yet")
    lacks("taper absent cum: does not claim the week is open", out, "still open")
    lacks("taper absent cum: no ratio", out, "% of Nov 2024's volume")

    # --- and the peer row is the one missing them
    bare = [dict(r) for r in NOV]
    for r in bare:
        for col in ("cum_weeks", "cum_tonnage_lb", "cum_heavy"):
            r.pop(col, None)
    out = render(T, rows_of(*([taper_row("2026-10-24", "Oct 2026", "current", 7,
                                         ton=62000.0, k=2, cum=115915.0)] + bare + APR)))
    balanced("taper absent cum on the peer row", out)
    has("taper absent peer cum: says so", out, "none recorded at that distance")
    lacks("taper absent peer cum: no ratio", out, "% of Nov 2024's volume")

    # --- no meet on the calendar
    out = render(T, rows_of(*(NOV + APR)))
    balanced("taper no meet", out)
    has("taper no meet: names the fix", out, "Set <b>meet_date</b>")
    lacks("taper no meet: no verdict", out, 'class="verdict"')

    # --- a first meet, with nothing on record to measure against
    out = render(T, rows_of(taper_row("2026-10-24", "Oct 2026", "current", 7,
                                      ton=62000.0, k=2, cum=115915.0)))
    balanced("taper first meet", out)
    has("taper first meet: says so", out, "starts with your second meet")
    lacks("taper first meet: no ratio", out, "% of")

    # --- the cold-start empty state, worded like the other signal cards
    out = render(T, [])
    has("taper empty: not indexed yet", out, "No signal rows came back")
    has("taper empty: names the filter bar", out, "not the filter bar")

    # --- a zero-tonnage yardstick must not divide by zero and blank the panel
    zero = [dict(r, cum_tonnage_lb=0.0, tonnage_lb=0.0) for r in NOV]
    out = render(T, rows_of(*([taper_row("2026-10-24", "Oct 2026", "current", 7,
                                         ton=62000.0, k=2, cum=115915.0)] + zero)))
    balanced("taper zero yardstick", out)
    lacks("taper zero yardstick: no ratio", out, "% of Nov 2024's volume")

    # --- an RPE-less week renders without printing a bare "at RPE"
    out = render(T, rows_of(*([taper_row("2026-10-24", "Oct 2026", "current", 8,
                                         state="in-progress", days=1, ton=9000.0,
                                         rpe=None, k=0, cum=0.0)] + NOV + APR)))
    balanced("taper no rpe", out)
    has("taper no rpe: singular day", out, "<b>1</b>&nbsp;training day in")
    lacks("taper no rpe: no dangling label", out, "at RPE .")


# --- program, block, projection, tags ---------------------------------------
#
# Every number below is off the repo on 2026-09-05, so a change in the arithmetic shows
# up here as a wrong sentence rather than as a passing test about invented data.

def load_row(inol=0.7472, lift="Comp Bench", band="easy",
             gloss="recovery, or a week after a hard one", acwr=1.37,
             acwr_band="rising", acwr_gloss="loading faster than the 28-day base",
             week_end="2026-09-06", block="strength"):
    return {"week_end": week_end, "block": block, "inol_hardest": inol,
            "inol_hardest_lift": lift, "inol_hardest_band": band,
            "inol_hardest_gloss": gloss, "acwr": acwr, "acwr_band": acwr_band,
            "acwr_gloss": acwr_gloss, "computed_through": "2026-09-05"}


def block_row(ordinal, block="strength", role="past", sessions=20, heavy=17,
              main_reps=83, hps=0.85, share=20.5, peers=None, peer_hps=None,
              peer_share=None, peer_from=None, first="2026-02-09", window=None):
    return {"block": block, "ordinal": ordinal, "block_role": role,
            "first_trained": first, "sessions": sessions, "heavy": heavy,
            "main_reps": main_reps, "heavy_per_session": hps, "share_pct": share,
            "peers": peers, "peer_heavy_per_session": peer_hps,
            "peer_share_pct": peer_share, "peer_from": peer_from,
            "peer_window_sessions": window, "computed_through": "2026-09-05"}


# The live shape: the current strength block, eight earlier strength blocks behind it.
BLOCK_LIVE = [
    block_row(0, role="current", sessions=6, heavy=5, main_reps=67, hps=0.83, share=7.5,
              peers=8, peer_hps=1.75, peer_share=12.05, peer_from="2023-05-29",
              first="2026-08-24", window=6),
    block_row(1, block="hypertrophy", sessions=56, heavy=48, main_reps=1461, hps=0.86),
    block_row(4, sessions=20, heavy=17, main_reps=83, hps=0.85),
]

PROJ_PAST = [
    {"cycle": "2024-04-06", "cycle_label": "Apr 2024", "cycle_role": "past",
     "projected_total_lb": 885.4, "meet_total_lb": 854.3, "platformed_pct": 96.5,
     "computed_through": "2026-09-05"},
    {"cycle": "2024-11-16", "cycle_label": "Nov 2024", "cycle_role": "past",
     "projected_total_lb": 929.1, "meet_total_lb": 909.4, "platformed_pct": 97.9,
     "computed_through": "2026-09-05"},
]
PROJ_NOW = {"cycle": "now", "cycle_label": "now", "cycle_role": "current",
            "projected_total_lb": 871.9, "peers": 3, "peer_pct": 97.2,
            "expected_lb": 847.5, "peer_from": "2024-04-06", "peer_to": "2026-03-14",
            "computed_through": "2026-09-05"}


def tag_row(tag, total, recent, prior=0, span=4, notes=31, frm="2026-09-01"):
    return {"tag": tag, "total": total, "recent": recent, "prior": prior,
            "last_trained": "2026-09-04", "window_days": 28, "notes_total": notes,
            "notes_from": frm, "notes_span_days": span, "computed_through": "2026-09-05"}


def section_program() -> None:
    T = tpl.SIGNAL_PROGRAM
    fixture_is_real("sig_program", load_row())

    out = render(T, rows_of(load_row(), load_row(inol=0.40, week_end="2026-08-30"),
                            load_row(inol=0.99, week_end="2026-08-23")))
    balanced("program", out)
    has("program: the band is the verdict", out, "Easy.")
    has("program: names the lift", out, "<b>Comp Bench</b>")
    has("program: the number", out, "INOL 0.75")
    has("program: the band in words", out, "recovery, or a week after a hard one")
    has("program: ranks against recent weeks", out, "of your last 2 weeks")
    has("program: acwr in words", out, "loading faster than the 28-day base")
    has("program: acwr banded", out, "load rising at 1.37")
    has("program: names the block", out, "strength block")
    # week_end is the last day trained, not the week's end - the copy must not promise
    # the calendar week. See derive.rollup_docs.
    has("program: labels the week honestly", out, "last trained 2026-09-06")
    lacks("program: does not claim a calendar week end", out, "week ending")
    lacks("program: does not imply the week starts then", out, "week of 2026")
    band("program: easy is the quiet band", out, "b-light")

    for inol, bandname, cls in ((2.4, "loading", "b-normal"),
                                (3.4, "brutal", "b-heavy"),
                                (4.6, "excessive", "b-max")):
        out = render(T, rows_of(load_row(inol=inol, band=bandname, gloss="x")))
        has(f"program {bandname}", out, f"{bandname.capitalize()}.")
        band(f"program {bandname} class", out, cls)

    # A week with no main-lift intensity has no INOL, and nil comparisons blank a panel.
    out = render(T, rows_of(load_row(inol=None, band=None, gloss=None)))
    balanced("program no inol", out)
    has("program no inol: says why", out, "no loading index to band")
    lacks("program no inol: no empty band", out, "<div class=\"verdict")

    out = render(T, rows_of(load_row(acwr=None, acwr_band=None, acwr_gloss=None)))
    balanced("program no acwr", out)
    lacks("program no acwr: no dangling load line", out, "load  at")

    # Both glosses are indexed now (they were KEEPed and rendered before anything wrote
    # them, which is where "at INOL 0.75 - ." came from). Present, they read; absent,
    # the sentence has to close cleanly rather than trailing an em-dash into a full stop.
    out = render(T, rows_of(load_row(gloss=None)))
    balanced("program no inol gloss", out)
    has("program no inol gloss: keeps the number", out, "INOL 0.75.")
    lacks("program no inol gloss: no dangling em-dash", out, "&mdash; .")
    lacks("program no inol gloss: no orphaned dash", out, "0.75 &mdash;")

    out = render(T, rows_of(load_row(acwr_gloss=None)))
    balanced("program no acwr gloss", out)
    has("program no acwr gloss: keeps the band and number", out, "load rising at 1.37")
    lacks("program no acwr gloss: no dangling middot", out, "1.37 &middot;")

    out = render(T, [])
    has("program empty", out, "No signal rows came back")


def section_block() -> None:
    T = tpl.SIGNAL_BLOCK
    fixture_is_real("sig_block", BLOCK_LIVE[0])

    out = render(T, rows_of(*BLOCK_LIVE))
    balanced("block", out)
    # 0.83 / 1.75 = 47.4%
    has("block: the ratio is the verdict", out, "47% of the heavy work in a usual strength block")
    has("block: its own rate", out, "<b>0.83</b> heavy reps a session")
    has("block: the peer median", out, "median of <b>1.75</b>")
    has("block: how many peers", out, "your 8 earlier strength blocks")
    has("block: names the window the median was taken over", out, "the first 6 sessions of")
    has("block: the denominator is visible", out, "<b>5</b> of <b>67</b> main-lift reps")
    has("block: how far back the comparison reaches", out, "reaches back to 2023-05-29")
    has("block: gauge", out, 'class="gauge"')
    band("block: under 70 is the loudest band", out, "b-max")
    # A hypertrophy block sits in the rows and must not be blended into the comparison.
    # The provenance names it deliberately, so scope this to the verdict line.
    verdict = out.split('class="verdict')[1].split("</div>")[0]
    check("block: the verdict names only this block type",
          "hypertrophy" not in verdict, verdict[:80])
    has("block: peer count is same-kind only", out, "your 8 earlier strength blocks")

    # peer_window_sessions absent (an older index): the sentence still has to read.
    out = render(T, rows_of(dict(BLOCK_LIVE[0], peer_window_sessions=None), *BLOCK_LIVE[1:]))
    balanced("block no window", out)
    has("block no window: still ranks", out, "47% of the heavy work")
    lacks("block no window: drops the window clause", out, "the first")
    has("block no window: keeps the peer count", out, "your 8 earlier strength blocks")

    out = render(T, rows_of(block_row(0, role="current", peers=0, sessions=6,
                                      heavy=5, main_reps=67, hps=0.83)))
    balanced("block first", out)
    has("block first: says so", out, "Your first strength block")
    lacks("block first: no ratio", out, "% of the heavy work")

    # Rows exist but none is current - a state the index should never produce, and the
    # card still has to render rather than go blank.
    out = render(T, rows_of(block_row(1), block_row(2)))
    balanced("block no current", out)
    has("block no current: says so", out, "No block in progress")

    for hps, want, cls in ((1.70, 97, "b-normal"), (2.30, 131, "b-max"), (2.10, 120, "b-heavy")):
        rows = [dict(BLOCK_LIVE[0], heavy_per_session=hps)]
        out = render(T, rows_of(*rows))
        has(f"block band {want}%", out, f"{want}% of the heavy work")
        band(f"block band {want}% class", out, cls)

    out = render(T, [])
    has("block empty", out, "No signal rows came back")


def section_projection() -> None:
    T = tpl.SIGNAL_PROJECTION
    fixture_is_real("sig_projection", PROJ_NOW)
    fixture_is_real("sig_projection", PROJ_PAST[0])

    out = render(T, rows_of(*(PROJ_PAST + [PROJ_NOW])))
    balanced("projection", out)
    has("projection: the ratio is the verdict", out, "97% of projection, across 3 meets")
    has("projection: Nov numbers", out, "Nov 2024 projected <b>929</b>")
    has("projection: Nov total", out, "you totalled <b>909</b>")
    has("projection: Apr numbers", out, "Apr 2024 projected <b>885</b>")
    has("projection: today's reading", out, "<b>872</b>")
    has("projection: what it implies", out, "platform total near")
    has("projection: the caveat is on the card", out, "singles at a commanded pace")

    # peer_pct and expected_lb are absent entirely under three peer meets now. The card
    # must degrade to naming the projection, and must not print "near lb" off a nil.
    out = render(T, rows_of(dict(PROJ_NOW, peers=2, peer_pct=None, expected_lb=None)))
    balanced("projection two peers", out)
    has("projection two peers: still names the number", out, "872")
    has("projection two peers: counts what it has", out, "<b>2</b> meets")
    has("projection two peers: names the threshold", out, "needs three")
    lacks("projection two peers: no ratio", out, "% of projection")
    lacks("projection two peers: no expected total", out, "platform total near")

    # And the other silence: no meet on record carries a projection at all.
    out = render(T, rows_of(dict(PROJ_NOW, peers=0, peer_pct=None, expected_lb=None)))
    balanced("projection no peers", out)
    has("projection no peers: still names the number", out, "872")
    has("projection no peers: says why it cannot rank", out, "No meet on record has a projection")
    lacks("projection no peers: does not count to three", out, "needs three")
    lacks("projection no peers: no ratio", out, "% of projection")

    out = render(T, rows_of(*PROJ_PAST))
    balanced("projection no current", out)
    has("projection no current: says so", out, "No projected total yet")

    out = render(T, [])
    has("projection empty", out, "No signal rows came back")


def section_tags() -> None:
    T = tpl.SIGNAL_TAGS
    fixture_is_real("sig_tags", tag_row("grip", 9, 5))

    # The live state: 31 notes across four days. Ranking here would be the confident
    # empty verdict, so the card must refuse and say what it has.
    live = [tag_row("watch", 12, 12), tag_row("motivation", 4, 4),
            tag_row("experiment", 3, 3), tag_row("grip", 2, 2)]
    out = render(T, rows_of(*live))
    balanced("tags too new", out)
    has("tags too new: refuses", out, "Too new to read a pattern")
    has("tags too new: names the start", out, "<b>2026-09-01</b>")
    has("tags too new: the corpus", out, "<b>31</b> of them across <b>4</b> days")
    has("tags too new: still shows what it has", out, "watch 12")
    lacks("tags too new: no claim about a trend", out, "You have written")

    # Once the notes are wide enough the same card ranks, with no rebuild.
    wide = [tag_row("grip", 9, 5, prior=1, span=60, notes=210),
            tag_row("fatigue", 6, 3, prior=3, span=60, notes=210)]
    out = render(T, rows_of(*wide))
    balanced("tags ranked", out)
    has("tags ranked: the sentence", out, "You have written &ldquo;grip&rdquo; 5 times in 28 days")
    has("tags ranked: the comparison", out, "Against <b>1</b> in the 28 days before")
    has("tags ranked: the runner-up", out, "Next: fatigue (3)")

    out = render(T, rows_of(tag_row("grip", 9, 1, prior=0, span=60, notes=210)))
    has("tags ranked: singular", out, "1 time in 28 days")

    out = render(T, rows_of(tag_row("grip", 9, 0, prior=0, span=60, notes=210)))
    balanced("tags quiet", out)
    has("tags quiet: says so", out, "Nothing written in the last 28 days")

    out = render(T, [])
    balanced("tags empty", out)
    has("tags empty: names the cause", out, "No tagged notes yet")


def section_units_and_timezone() -> None:
    """Unit labels come from templates.UNITS, and the clock comes from IRONSTACK_TZ.

    Neither is a conversion. The data model is lb / ft / F and saying otherwise without
    converting the numbers would be the loudest lie a training log can tell; what these
    assert is that the LABELS have one home, so the day a conversion exists there is one
    row to change per unit rather than a dozen string literals to find.
    """
    for key, want in (("weight", "lb"), ("distance", "ft"), ("temp", "F"),
                      ("mass_alt", "kg")):
        check(f"units: {key} is {want}", tpl.UNITS[key] == want, tpl.UNITS[key])
        check(f"units: ${key.upper()} token substitutes",
              tpl.tok(f"$U_{key.upper()}") == want, tpl.tok(f"$U_{key.upper()}"))

    # No unit token may survive into a rendered card: an unsubstituted $ is a Liquid
    # syntax error and blanks the panel, which is how the signal cards broke the hour
    # the tokens were introduced (signal() was concatenating, not tok()ing).
    for name in dir(tpl):
        if name.startswith("_"):
            continue
        value = getattr(tpl, name)
        if not isinstance(value, str) or "<div" not in value:
            continue
        check(f"{name}: no unsubstituted token", "$" not in value,
              f"holds {value[value.index('$'):value.index('$') + 12]!r}" if "$" in value else "")

    check("tz: UTC is the default", tpl.tz_offset_seconds("UTC") == 0)
    check("tz: a negative offset", tpl.tz_offset_seconds("-07:00") == -25200)
    check("tz: a positive offset", tpl.tz_offset_seconds("+05:30") == 19800)
    check("tz: a compact offset", tpl.tz_offset_seconds("-0700") == -25200)
    try:
        tpl.tz_offset_seconds("America/Denver")
        check("tz: a named zone is refused", False, "accepted an IANA zone")
    except ValueError as exc:
        check("tz: a named zone is refused", True)
        check("tz: and says why", "DATE_FORMAT" in str(exc), str(exc))

    # The offset reaches both engines: Liquid through $TZ_OFF, ES|QL through
    # build_dashboards.with_timezone.
    check("tz: $TZ_OFF reaches the days-to-meet arithmetic",
          "$TZ_OFF" in tpl.DAYS_TO_MEET)
    check("tz: UTC leaves ES|QL untouched",
          bd.with_timezone('EVAL d = DATE_FORMAT("MMM d", date)')
          == 'EVAL d = DATE_FORMAT("MMM d", date)')
    # Not a live-cluster assertion, just that the shift is emitted where TZ is set.
    shifted = bd.DATE_FORMAT_CALL.sub(
        lambda m: f'DATE_FORMAT("{m.group(1)}", {m.group(2)} - 25200 seconds)',
        'EVAL d = DATE_FORMAT("MMM d", date)')
    check("tz: a non-UTC offset shifts the instant",
          shifted == 'EVAL d = DATE_FORMAT("MMM d", date - 25200 seconds)', shifted)

    # Every DATE_FORMAT in Q has to be reachable by that rewrite, or a card keeps
    # printing UTC while everything around it moved.
    for name, query in bd.Q.items():
        raw = query.count("DATE_FORMAT(")
        seen = len(bd.DATE_FORMAT_CALL.findall(query))
        check(f"tz: every DATE_FORMAT in Q[{name!r}] is rewritable", raw == seen,
              f"{seen} of {raw} matched")


def main() -> None:
    section_cold_start()
    section_total_card()
    section_meet_cards()
    section_moat()
    section_contrast()
    section_orphans()
    section_lift()
    section_unit_spacing()
    section_unit_spacing_before()
    section_float_leaks()
    section_escaping()
    section_escaping_renders()
    section_units_and_timezone()
    section_helpers()
    section_all_templates()
    section_intensity()
    section_load()
    section_drift()
    section_taper()
    section_program()
    section_block()
    section_projection()
    section_tags()

    total = PASSED + len(FAILED)
    if FAILED:
        print(f"{PASSED}/{total} ok, {len(FAILED)} FAILED\n")
        for line in FAILED:
            print(f"  FAIL  {line}")
        sys.exit(1)
    print(f"{PASSED}/{total} ok")


if __name__ == "__main__":
    main()
