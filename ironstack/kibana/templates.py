"""Iron Log templates for Kibana custom-content panels.

Each template is HTML + CSS rendered by Kibana's Custom content panel inside a
sandboxed iframe (no scripts, no external fonts or images) through a Liquid
template bound to one ES|QL query. The panel exposes `rows`, each row a map of
column name -> {value, pct}. Liquid only runs when a query is attached.

Design rules (Iron Log): charcoal ground, warm chalks, rules not boxes, one
oxblood accent per dashboard, mono eyebrows, condensed display numbers.
No em-dashes in UI strings.
"""

from __future__ import annotations

import os
import sys
import re

# --------------------------------------------------------------------------- units
#
# The data model is imperial: weight_lb, tonnage_lb, distance_ft, environment.temp_f.
# That is not a display choice, it is what the indexer writes, so there is no
# IRONSTACK_UNITS switch here: relabelling "lb" as "kg" without converting the numbers
# would turn a 909 lb total into a 909 kg one, which is the loudest possible lie a
# training log can tell. What this block buys is that the labels live in ONE place
# instead of being littered as string literals across a dozen cards, so the day a
# conversion layer does exist there is exactly one row to change per unit.

UNITS = {
    "weight": "lb",    # weight_lb, tonnage_lb, cum_tonnage_lb, est_e1rm, total_lb
    "distance": "ft",  # distance_ft
    "temp": "F",       # environment.temp_f
    "mass_alt": "kg",  # workout-meets carries kg natively; not a conversion of the above
}

# --------------------------------------------------------------------------- timezone
#
# ES|QL DATE_FORMAT and Liquid's `"now" | date` both work in UTC, so a days-to-meet
# figure flipped at UTC midnight and every human-readable date on the pages was a UTC
# date. IRONSTACK_TZ is a build-time fixed offset ("UTC", "-07:00", "+0530"). It has to
# be a fixed offset rather than an IANA zone because the arithmetic it feeds is Liquid's
# "now" minus a date, and a shift is a number. It reaches ONLY that arithmetic, through
# the $TZ_OFF token. It must never reach an ES|QL DATE_FORMAT - see the timezone comment
# in build_dashboards.py for why that shifts calendar dates into the previous day.

TZ = os.environ.get("IRONSTACK_TZ", "UTC").strip() or "UTC"

# --check compares the build against the committed artifact, and the committed artifact
# is the UTC build - the offset is the reader's, not the repo's, the same way the coach
# URL and the meet best are. Read here rather than neutralised later because $TZ_OFF is
# substituted into every template at import, before main() gets a say. Without this, a
# reader who set their own offset and then ran the checks was told the committed file
# was stale when the only thing that differed was their own environment.
if "--check" in sys.argv:
    TZ = "UTC"


def tz_offset_seconds(tz: str) -> int:
    """Seconds to add to a UTC instant to land on the configured wall clock."""
    if tz.upper() in ("UTC", "Z", "GMT", ""):
        return 0
    m = re.fullmatch(r"(?:UTC|GMT)?([+-])(\d{1,2}):?(\d{2})?", tz.strip())
    if not m:
        raise ValueError(
            f"IRONSTACK_TZ must be UTC or a fixed offset like -07:00, got {tz!r}. "
            "ES|QL's DATE_FORMAT has no timezone parameter, so a named zone cannot "
            "be honoured at build time."
        )
    sign = -1 if m.group(1) == "-" else 1
    return sign * (int(m.group(2)) * 3600 + int(m.group(3) or 0) * 60)


try:
    TZ_OFFSET_SEC = tz_offset_seconds(TZ)
except ValueError as exc:
    # A clean exit, not a traceback. Every other bad-env path here (a non-numeric
    # IRONSTACK_MEET_MAX_LB, a javascript: coach URL) ends in sys.exit with a sentence
    # the reader can act on; this one raised at IMPORT, so `IRONSTACK_TZ=Denver
    # verify_liquid.py` died in a stack trace before either entry point had run a line.
    # The function still raises, because that is what the suite asserts on.
    sys.exit(f"error: {exc}\n       Nothing was written.")


# --------------------------------------------------------------------------- coach
#
# Whether there IS a coach. The ASK THE COACH panel and the COACH_PROMPT line under the
# Signal row are correctly built only when IRONSTACK_COACH_URL is set; three strings on
# Mindset were not, so the no-coach build shipped a page whose tagline, provenance line
# and pointer all sent the reader to something the dashboards do not contain and never
# name. Read the same way build_dashboards reads it, INCLUDING the --check neutralisation,
# because these strings are baked into the templates at import and --check has to build
# the committed artifact's configuration rather than the reader's.
# --no-coach belongs here beside --check, and for two years it was not: the flag was
# only consulted where the variable was ALREADY empty, so `--no-coach` with a coach URL
# in the environment built the coach anyway and said "ASK THE COACH on" while doing it.
# It reads as "build without the coach" and it did nothing. Found on 2026-09-06 trying
# to restore the public artifact from a shell that had the real URL exported: the build
# refused on seven private hosts, which is the private-host lint catching a flag that
# lied. A flag whose name is a promise has to keep it whatever the environment says.
COACH_URL = os.environ.get("IRONSTACK_COACH_URL", "").strip()
if "--check" in sys.argv or "--no-coach" in sys.argv:
    COACH_URL = ""
HAS_COACH = bool(COACH_URL)


def coach_or(with_coach: str, without: str) -> str:
    """The sentence to use when there is a coach to point at, or the one when there is not."""
    return with_coach if HAS_COACH else without

# --------------------------------------------------------------------------- tokens

BG = "#171513"
PANEL = "#1f1c19"
RULE = "#2a2622"
CHALK = "#ebe5d8"
DIM = "#a8a094"
FAINT = "#5a564f"
STEEL = "#8f8b84"  # 5.0:1 on the panel ground; the floor for any text that carries meaning
BLOOD = "#a8211a"
BLOOD_DIM = "#5e1e1c"
ARMY = "#7a8b3a"

DISPLAY = "'Oswald','Arial Narrow','Roboto Condensed','Helvetica Neue',Arial,sans-serif"
MONO = "'JetBrains Mono',ui-monospace,'SF Mono',Menlo,Consolas,monospace"
SERIF = "'Merriweather',Georgia,'Times New Roman',serif"

TOKENS = {
    "$BG": BG, "$PANEL": PANEL, "$RULE": RULE, "$CHALK": CHALK, "$DIM": DIM, "$FAINT": FAINT,
    "$STEEL": STEEL, "$BLOOD": BLOOD, "$BLOOD_DIM": BLOOD_DIM, "$ARMY": ARMY,
    "$DISPLAY": DISPLAY, "$MONO": MONO, "$SERIF": SERIF,
    # units and the build-time clock offset, so neither is a literal in a card
    "$U_WEIGHT": UNITS["weight"], "$U_DISTANCE": UNITS["distance"],
    "$U_TEMP": UNITS["temp"], "$U_MASS_ALT": UNITS["mass_alt"],
    "$TZ_OFF": str(TZ_OFFSET_SEC),
}


def tok(s: str) -> str:
    for k, v in TOKENS.items():
        s = s.replace(k, v)
    return s


# --------------------------------------------------------------------------- base css

BASE_CSS = tok("""<style>
*{box-sizing:border-box;margin:0;padding:0;border-radius:0!important;box-shadow:none!important}
html,body{height:100%}
body{background:$BG;color:$CHALK;font-family:$DISPLAY;padding:14px 18px;overflow-x:hidden;overflow-y:auto;-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-thumb{background:$RULE}::-webkit-scrollbar-track{background:transparent}
.eyebrow{font-family:$MONO;font-size:10px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:$STEEL;white-space:nowrap}
.eyebrow.blood{color:$BLOOD}
.eyebrow.dim{color:$DIM}
.hero{font-size:46px;font-weight:700;line-height:1;letter-spacing:-.015em;text-transform:uppercase;white-space:nowrap;font-variant-numeric:tabular-nums}
.hero.blood{color:$BLOOD}
.value{font-size:32px;font-weight:600;line-height:1.05;text-transform:uppercase;white-space:nowrap}
.value small{font-size:15px;font-weight:500;color:$DIM;letter-spacing:.04em;margin-left:5px}
.sub{font-family:$MONO;font-size:12px;color:$DIM;letter-spacing:.03em;line-height:1.55}
.faint{color:$STEEL}
.mono{font-family:$MONO}
.prose{font-family:$SERIF;font-size:14px;line-height:1.6;color:$DIM}
.rule{border-top:1px solid $RULE}
.stack{display:flex;flex-direction:column;justify-content:flex-start;gap:10px;height:100%}
.stack.spread{justify-content:space-between;gap:0}
.row{display:flex;gap:0;align-items:flex-start}
.card{flex:1;min-width:0;padding:0 18px;border-left:1px solid $RULE;display:flex;flex-direction:column;justify-content:flex-start;gap:5px}
.card:first-child{padding-left:0;border-left:0}
.card .top{display:flex;flex-direction:column;gap:5px}
.chip{display:inline-block;font-family:$MONO;font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:$DIM;border:1px solid $RULE;padding:1px 6px;margin:0 4px 2px 0;white-space:nowrap}
.chip.made{color:$CHALK;border-color:$STEEL}
/* A miss used to be $FAINT with a 1px strike: at 9px on this ground the line is
   invisible and a missed third attempt read the same as a made one. The strike stays,
   in oxblood and twice the weight, and the box border carries it too. */
.chip.miss{color:$STEEL;border-color:$BLOOD_DIM;text-decoration:line-through;text-decoration-color:$BLOOD;text-decoration-thickness:2px}
.chip.blood{color:$BLOOD;border-color:$BLOOD_DIM}
.bar{height:2px;background:$RULE;position:relative;margin-top:8px}
.bar i{position:absolute;left:0;top:0;bottom:0;background:$BLOOD;display:block}
.bar.dim i{background:$DIM}
.empty{color:$STEEL;font-family:$MONO;font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.list{display:flex;flex-direction:column}
.item{display:flex;align-items:baseline;gap:12px;padding:7px 0;border-top:1px solid $RULE;font-family:$MONO;font-size:13px}
.item:first-child{border-top:0}
.item .when{color:$STEEL;font-size:11px;letter-spacing:.06em;text-transform:uppercase;min-width:72px}
.item .txt{color:$CHALK;flex:1;min-width:0}
.item .num{color:$DIM;white-space:nowrap;font-variant-numeric:tabular-nums}
.set{display:flex;align-items:baseline;gap:9px;font-family:$MONO;font-size:14px;padding:4px 0;font-variant-numeric:tabular-nums}
.set .n{color:$FAINT;font-size:10px;min-width:14px;font-weight:400}
.set .w{color:$CHALK;min-width:62px;text-align:right;font-size:17px;font-weight:600;letter-spacing:-.01em}
.set .x{color:$FAINT;font-size:11px}
.set .r{color:$CHALK;min-width:30px;font-size:15px}
.set .rpe{font-size:13px;letter-spacing:.02em}
.set .rpe.lo{color:$FAINT}
.set .rpe.mid{color:$DIM}
.set .rpe.hi{color:$CHALK;font-weight:600}
.set .rpe.max{color:$BLOOD;font-weight:700}
.set .note{color:$STEEL;font-size:12px;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.set.prep{opacity:.55}
.set.prep .w{font-size:14px;font-weight:400;color:$DIM}
.set.prep .r{color:$DIM;font-size:13px}
.ex{margin-bottom:14px}
.ex .name{font-size:16px;font-weight:600;text-transform:uppercase;letter-spacing:.02em;line-height:1.3;padding-bottom:3px;border-bottom:1px solid $RULE;margin-bottom:3px}
.ex .name .cat{font-family:$MONO;font-size:9px;letter-spacing:.16em;color:$FAINT;margin-left:8px;font-weight:500}
.cols{column-count:2;column-gap:36px}
.liftrow{display:flex;align-items:center;gap:12px;padding:6px 0;border-top:1px solid $RULE}
.liftrow:first-child{border-top:0}
.lname{font-family:$MONO;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:$DIM;min-width:76px}
.lval{font-size:21px;font-weight:600;color:$CHALK;min-width:62px;text-align:right;font-variant-numeric:tabular-nums}
.lbar{flex:1;min-width:24px;height:3px;background:$RULE;position:relative}
.lbar i{position:absolute;left:0;top:0;bottom:0;background:$BLOOD;display:block}
.lkg{font-family:$MONO;font-size:11px;color:$STEEL;min-width:62px;text-align:right}
.warm{font-family:$MONO;font-size:12px;line-height:1.9;color:$DIM;margin-top:5px}
.warm .nm{color:$CHALK;text-transform:uppercase;letter-spacing:.04em;font-size:11px;margin-right:5px}
.warm .qty{color:$FAINT;margin-right:7px}
.warm .sep{color:$RULE;margin-right:9px}
.cols .ex{break-inside:avoid}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:4px 8px}
.k{color:$STEEL}
.v{color:$CHALK}
.hdr{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.hdr .title{font-size:30px;font-weight:700;text-transform:uppercase;letter-spacing:-.01em;line-height:1}
.hdr .meta{font-family:$MONO;font-size:12px;color:$DIM;letter-spacing:.05em;text-transform:uppercase}
.hdr .meta b{color:$CHALK;font-weight:500}
.dot{display:inline-block;width:7px;height:7px;background:$BLOOD;margin:0 8px;vertical-align:middle}
svg{display:block}
</style>""")


def page(body: str) -> str:
    return BASE_CSS + body


def empty(text="Not logged yet") -> str:
    return f'<div class="empty">{text}</div>'


# --------------------------------------------------------------------------- brand bar (static)

def brand_bar(section: str, tagline: str) -> str:
    """The chrome. Same on every dashboard; only the section name and tagline change."""
    return tok(f"""<style>
*{{box-sizing:border-box;margin:0;padding:0;border-radius:0!important;box-shadow:none!important}}
/* No height:100%, no flex. The panel iframe is not always the height Kibana
   implies, and any centring or space-between put the wordmark below the fold.
   Plain block flow starts at the top of the document and cannot be pushed down. */
body{{background:$BG;color:$CHALK;font-family:$DISPLAY;padding:10px 18px;overflow:hidden;-webkit-font-smoothing:antialiased}}
.eyebrow{{font-family:$MONO;font-size:10px;font-weight:500;letter-spacing:.24em;text-transform:uppercase;color:$BLOOD;margin-bottom:6px}}
.bar{{display:flex;align-items:baseline;justify-content:space-between;gap:16px}}
.left{{display:flex;align-items:baseline;gap:10px}}
.word{{font-size:22px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;line-height:1.1}}
.sq{{display:inline-block;width:11px;height:11px;background:$BLOOD;transform:translateY(-1px)}}
.vr{{width:1px;height:22px;background:$RULE;transform:translateY(4px);margin:0 6px}}
.section{{font-family:$MONO;font-size:12px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:$DIM}}
.tagline{{font-family:$MONO;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:$DIM;text-align:right;max-width:60%;line-height:1.55}}
</style>
<div class="eyebrow">&#9646;&#9646;&#9646;&nbsp;&nbsp;A Mission Built training system&nbsp;&nbsp;&#9646;&#9646;&#9646;</div>
<div class="bar"><div class="left"><span class="word">Iron</span><span class="sq"></span><span class="word">Stack</span><span class="vr"></span><span class="section">{section}</span></div><div class="tagline">{tagline}</div></div>""")



# A verdict card is an argument, and an argument the reader cannot answer is a lecture.
# This is the line that says the argument is answerable. It sits directly under the
# Signal row and points at the button, because a custom content panel cannot be a link
# itself - it renders in a sandboxed iframe with no scripts and no <a href>.
#
# It is deliberately not a fourth verdict: no eyebrow, no hero, one line, dim.

COACH_PROMPT = page(tok("""<style>
.ask{font-family:$MONO;font-size:12px;letter-spacing:.04em;color:$DIM;line-height:1.6}
.ask b{color:$CHALK;font-weight:600}
.ask .where{color:$STEEL;text-transform:uppercase;font-size:10px;letter-spacing:.14em}
</style>
<div class="ask">Disagree with a verdict, or want the reasoning behind one?
<b>Ask the coach.</b> It is the only thing here that has read your notes.
&nbsp;&nbsp;<span class="where">&#9652;&nbsp;top right</span></div>"""))


# The line under the two intensity-zone charts.
#
# Both of them bucket `prilepin_zone`, and a set only carries one when it has a relative
# intensity - which needs an earlier estimate for that lift to be measured against, and
# that estimate is built out of a logged RPE. Until now a set with neither was measured
# against its OWN Epley estimate, which made the number a pure function of rep count: a
# 135 lb warm-up triple and a 315 lb single both landed at 90.9%. That fallback is gone,
# correctly, and the consequence lands here - a lifter who does not log RPE now gets two
# charts with nothing in them.
#
# A Lens panel cannot say why it is empty. A title is a fixed string and a legend is a
# legend, and neither can read a row. So the explanation is a card of its own under the
# chart, reading the same sets the chart reads.
#
# It is not only a cold start, which is the mistake worth avoiding here: a state that
# exists only for the lifter who has none of something is a state nobody tests. This
# says how many reps carry a zone in EVERY case, which is what makes the stacked chart
# above it readable as a share of something rather than as a share of everything.
ZONE_COVERAGE = page(tok("""<style>
.zc{font-family:$MONO;font-size:11px;letter-spacing:.03em;color:$DIM;line-height:1.7}
.zc b{color:$CHALK;font-weight:600}
</style>
<div class="zc">
{%- if rows.size == 0 -%}
No working sets came back, so there is nothing above to place in a zone.
{%- else -%}
{%- assign zr = rows[0]['zr'].value | plus: 0 -%}
{%- assign tr = rows[0]['tr'].value | plus: 0 -%}
{%- if tr == 0 -%}
No working reps in this range, so the chart above has nothing to place.
{%- elsif zr == 0 -%}
None of these <b>{{ tr | round }}</b> working reps carry an intensity zone, which is why the
chart above is empty. A zone is a share of a reference weight, and a set gets one only once
that lift has an earlier estimate to measure against &mdash; which is built out of a logged
RPE. Put an RPE on your top sets and the zones fill in behind you.
{%- elsif zr < tr -%}
<b>{{ zr | round }}</b> of <b>{{ tr | round }}</b> working reps here carry an intensity zone.
The rest were logged with no RPE and nothing earlier to measure them against, so the chart
above does not count them.
{%- else -%}
All <b>{{ tr | round }}</b> working reps here carry an intensity zone.
{%- endif -%}
{%- endif -%}
</div>"""))


# --------------------------------------------------------------------------- Liquid helpers

def num(expr: str, dp: int = 0) -> str:
    """Liquid that renders `expr` as a grouped number: 14145 -> 14,145.

    Liquid has no number-format filter, so the digits are grouped by slicing the
    string. Lens formats its own numbers with separators; without this the Liquid
    cards printed raw integers next to them and the digits ran together.
    Handles up to 9 DIGITS, which covers lifetime tonnage. nil renders as nothing.

    The sign is stripped before the digits are grouped and re-emitted in front of
    them. It was not, and the grouping counted the "-" as a digit: num(-123) came out
    "-,123" - a minus sign, a comma, and three digits, on a card whose whole job is to
    render a number a lifter can read. A negative reaches this from any subtraction
    the cards do (a delta, a difference against a peer), so it is not a hypothetical.
    Past nine digits the number is emitted ungrouped rather than mis-grouped: wrong
    grouping reads as a different number, and no separator reads as a long one.
    """
    r = f" | round: {dp}" if dp else " | round"
    return (
        # The nil guard is load-bearing: `nil | round` is 0, so an unlogged value
        # would print a confident "0". 0 itself is truthy in Liquid and still prints.
        "{%- if " + expr + " -%}"
        "{%- assign _n = " + expr + r + ' | append: "" -%}'
        '{%- assign _q = _n | split: "." -%}'
        "{%- assign _i = _q[0] -%}"
        '{%- assign _sg = "" -%}'
        '{%- if _i contains "-" -%}{%- assign _sg = "-" -%}'
        '{%- assign _i = _i | remove_first: "-" -%}{%- endif -%}'
        "{%- assign _L = _i | size -%}{{ _sg }}"
        "{%- if _L > 9 -%}{{ _i }}"
        "{%- elsif _L > 6 -%}{%- assign _a = _L | minus: 6 -%}"
        "{{ _i | slice: 0, _a }},{{ _i | slice: _a, 3 }},{{ _i | slice: -3, 3 }}"
        "{%- elsif _L > 3 -%}{%- assign _a = _L | minus: 3 -%}"
        "{{ _i | slice: 0, _a }},{{ _i | slice: -3, 3 }}"
        "{%- else -%}{{ _i }}{%- endif -%}"
        "{%- if _q[1] -%}.{{ _q[1] }}{%- endif -%}"
        "{%- endif -%}"
    )


def ordinal(expr: str) -> str:
    """The English ordinal suffix for `expr`, as a Liquid fragment.

    A placing is one of the few numbers on this app a reader hears out loud, so "21th"
    is not a rounding detail - it is the whole card looking careless. The teens are the
    exception every naive version gets wrong: 11, 12 and 13 take "th" even though their
    last digits say otherwise, and they are exactly the range a mid-pack finish lands
    in. Two places print a placing and both call this, because the first version of it
    was written twice and only one copy would ever have been fixed.
    """
    return ("{%- assign _o = " + expr + " | plus: 0 -%}"
            "{%- assign _t = _o | modulo: 100 -%}{%- assign _d = _o | modulo: 10 -%}"
            "{%- if _t >= 11 and _t <= 13 -%}th"
            "{%- elsif _d == 1 -%}st{%- elsif _d == 2 -%}nd{%- elsif _d == 3 -%}rd"
            "{%- else -%}th{%- endif -%}")


def numr(expr: str, dp: int = 0) -> str:
    """`expr` rounded, or NOTHING AT ALL when it is nil. No thousands grouping.

    num()'s nil gate, for the places a grouped number would be wrong: an RPE, a DOTS
    score, a kilo total to one decimal. Those were written as a bare `| round` or
    `| round: 1`, and `nil | round` is 0 in both engines - so a lifter who never logs
    an RPE read "AVG WORKING RPE 0" on every session, a log with no meet in it read
    "Best total 0 kg", and the projection card said "Apr 2024 projected 0 and you
    totalled 0". A zero is a measurement. Absence is not, and the two must not print
    the same. This is the project's own rule ("no zeros standing in for absence")
    applied to the cards that predate it.

    Unlike num() the tags do NOT strip surrounding whitespace. num() opens with `{%-`
    and closes with `-%}`, which eats the space on either side of it and has needed a
    lint on both ends since; there is no reason to inherit that trap here. A caller
    that wants nothing at all around the number can still write the tags tight.
    """
    r = f" | round: {dp}" if dp else " | round"
    return "{% if " + expr + " %}{{ " + expr + r + " }}{% endif %}"


def rpe_class(expr: str) -> str:
    """Liquid that leaves `rc` = a class name banding RPE, so effort reads as colour."""
    return (
        # Prep sets carry no RPE, and comparing nil with >= is a render error that
        # takes the whole panel down, so the band is only computed when there is one.
        '{%- assign rc = "lo" -%}'
        "{%- if " + expr + " -%}"
        "{%- if " + expr + ' >= 9 -%}{%- assign rc = "max" -%}'
        "{%- elsif " + expr + ' >= 8 -%}{%- assign rc = "hi" -%}'
        "{%- elsif " + expr + ' >= 7 -%}{%- assign rc = "mid" -%}{%- endif -%}'
        "{%- endif -%}"
    )


# A Liquid snippet that leaves `days` = whole days from now to the meet date in
# rows[0]['program.meet_date'].
#
# It can be NEGATIVE, and every reader of it has to branch on that. A meet_date is
# config: it stays in the program block until someone edits the file, so the day after
# a meet `days` goes to -1 and keeps counting. `{% if days %}` is truthy for a negative
# in Liquid, so the Overview hero read "-658" and the Program header read "-658 days
# out" - a countdown running backwards, in the largest type on the page. derive.py
# already treats a planned date that has passed as a leftover; the cards now do too.
# `days_ago` is the same number with the sign taken off, for the sentence that says so.
DAYS_TO_MEET = """{% if rows[0]['program.meet_date'].value %}{% assign now_s = "now" | date: "%s" | plus: $TZ_OFF %}{% assign meet_s = rows[0]['program.meet_date'].value | date: "%s" | plus: 0 %}{% assign days = meet_s | minus: now_s | divided_by: 86400.0 | ceil %}{% endif %}"""



# --------------------------------------------------------------------------- Overview cards

DAYS_TO_MEET_CARD = page(tok("""
<div class="stack">
{% if rows.size == 0 %}<div class="eyebrow">Days to meet</div>""" + empty("No sessions yet") + """{% else %}""" + DAYS_TO_MEET + """
<div><div class="eyebrow">Days to meet</div>
{% if days and days >= 0 %}<div class="hero" style="margin-top:8px">{{ days }}</div>{% elsif days %}{% assign days_ago = 0 | minus: days %}<div class="empty" style="margin-top:10px">That meet was {{ days_ago }} day{% unless days_ago == 1 %}s{% endunless %} ago</div>{% else %}<div class="empty" style="margin-top:10px">No meet on the calendar</div>{% endif %}</div>
<div class="sub">{{ rows[0]['meet_s'].value | escape }}<br>{{ rows[0]['program.phase'].value | escape }} &middot; week {{ rows[0]['program.week'].value }} &middot; day {{ rows[0]['program.day'].value }} of {{ rows[0]['program.total_days'].value }}<br><span class="faint">last trained {{ rows[0]['date_s'].value | escape }}</span></div>
{% endif %}
</div>"""))

TOTAL_CARD = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Projected total</div>""" + empty() + """{% else %}
{%- comment -%} One panel, two indices. The lift rows come from workout-sets and carry a
lift family; one further row comes from workout-meets, carries no family, and holds
MAX(total_lb) - the reader's own meet best. Until 2026-09-05 that number was a build-time
constant carrying the author's last meet total, so a stranger's Overview asserted his
record as theirs. A custom-content panel's query can read data, so it reads it.
{%- endcomment -%}
{%- assign total = 0 -%}{%- assign best = 0 -%}{%- assign lifts = 0 -%}{%- assign meet_max = 0 -%}{%- assign pts = 0 -%}
{%- comment -%} The query asks for 90 days and the picker is ANDed on top. At "Last 30
days" the number was 843 under a label still promising 90; the label now reports the
window it actually got. {%- endcomment -%}
{%- assign now_s = "now" | date: "%s" | plus: $TZ_OFF -%}{%- assign oldest_s = 0 -%}
{%- for r in rows -%}
{%- if r['meet_lb'].value -%}{%- assign _m = r['meet_lb'].value | plus: 0 -%}{%- if _m > meet_max -%}{%- assign meet_max = _m -%}{%- endif -%}{%- endif -%}
{%- if r['pts'].value -%}{%- assign _p = r['pts'].value | plus: 0 -%}{%- if _p > pts -%}{%- assign pts = _p -%}{%- endif -%}{%- endif -%}
{%- if r['fam'].value -%}
{%- assign lifts = lifts | plus: 1 -%}
{%- assign _v = r['e1'].value | round -%}{%- assign total = total | plus: _v -%}
{%- if _v > best -%}{%- assign best = _v -%}{%- endif -%}
{%- if r['first_d'].value -%}{%- assign fs = r['first_d'].value | date: "%s" | plus: 0 -%}{%- if oldest_s == 0 or fs < oldest_s -%}{%- assign oldest_s = fs -%}{%- endif -%}{%- endif -%}
{%- endif -%}
{%- endfor -%}
{%- assign span_d = 90 -%}{%- if oldest_s > 0 -%}{%- assign span_d = now_s | minus: oldest_s | divided_by: 86400 | floor -%}{%- endif -%}
{% if lifts == 0 %}<div class="eyebrow">Projected total</div>""" + empty("No main-lift work in this window") + """{% else %}
{%- comment -%} Two sports, two questions. A meet scored on a TOTAL adds your lifts up,
so the hero is the sum and every lift under it is a component of one number. A meet
scored on POINTS ranks you event by event and adds the placings, so there is no total
to project - and a summed hero on that page would be a number no scoring table has ever
recognised, printed in the largest type on the app. The lift rows are the same rows
either way; what changes is whether they add up to anything. `pts` comes off the meets
half of the query, so the card follows the record rather than a setting.
{%- endcomment -%}
{% if pts > 0 %}
<div class="eyebrow">Event readiness</div>
<div class="hero" style="margin-top:7px">{{ lifts }}<span style="font-size:20px;color:$DIM;margin-left:6px">of your events</span></div>
<div class="sub" style="margin-top:3px">{% if span_d < 60 %}have a recent estimate, from the last <span class="v">{{ span_d }}</span> days. The card reads 90; widen the time picker for the real number{% else %}have an estimate from the last 90 days of main-lift work{% endif %}</div>
{% else %}
<div class="eyebrow">Projected total</div>
<div class="hero" style="margin-top:7px">""" + num("total") + """<span style="font-size:20px;color:$DIM;margin-left:6px">$U_WEIGHT</span></div>
<div class="sub" style="margin-top:3px">{% if span_d < 60 %}best of the last <span class="v">{{ span_d }}</span> days of main-lift work. The card reads 90; widen the time picker for the real number{% else %}best of the last 90 days of main-lift work{% endif %}</div>
{% endif %}
<div style="margin-top:12px">
{% for r in rows %}{% if r['fam'].value %}<div class="liftrow"><span class="lname">{{ r['fam'].value | escape }}</span><span class="lval">""" + num("r['e1'].value") + """</span><span class="lbar"><i style="width:{% if best > 0 %}{{ r['e1'].value | times: 100 | divided_by: best | round }}{% else %}0{% endif %}%"></i></span></div>{% endif %}{% endfor %}
</div>
<div class="rule" style="margin-top:12px;padding-top:8px"><span class="sub">
{%- if pts > 0 -%}
Your last meet was scored on points per event, so these do not add up to a total and this card does not pretend they do. Each lift is worth reading against its own best.
{%- elsif meet_max > 0 -%}
{%- assign pct = total | times: 100 | divided_by: meet_max | round -%}{%- assign togo = meet_max | minus: total | round -%}
{%- comment -%} "your meet best" was a claim the query cannot support. The meets half of
the union carries no date bound of its own, so MAX(total_lb) is the best meet the TIME
PICKER admits - and a lifter whose best day was three years ago is measured on this page
against a number that is not their best, in a sentence that says it is. The card is
scrupulous about exactly this two lines above ("The card reads 90; widen the time picker
for the real number"), so it says the same thing here rather than a different thing.
{%- endcomment -%}
{% if total >= meet_max %}<span class="v">{{ pct }}%</span> of your best meet total in this range,&nbsp;""" + num("meet_max") + """&nbsp;$U_WEIGHT{% else %}<span class="v">{{ pct }}%</span> of your best meet total in this range,&nbsp;""" + num("meet_max") + """&nbsp;$U_WEIGHT &middot; <span class="v">""" + num("togo") + """&nbsp;$U_WEIGHT</span> to go{% endif %}
<br><span class="faint">the time picker reaches the meet record too; widen it if an older meet was bigger</span>
{%- else -%}
No meet in this range, so there is nothing to hold this against. Log one, or widen the time picker past the last one, and this line starts keeping score.
{%- endif -%}
</span></div>
{% endif %}
{% endif %}"""))



WATCH_CARD = page(tok("""
<div class="eyebrow">In your own words</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("Nothing flagged yet") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{{ r['date_s'].value | escape }}</span><span class="txt">{{ r['item'].value | escape }}</span></div>{% endfor %}
</div>{% endif %}"""))


# --------------------------------------------------------------------------- header cards (Program, Session, Lift)

PROGRAM_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Program</div>""" + empty("No sessions in this block") + """{% else %}""" + DAYS_TO_MEET + """
<div class="hdr"><span class="eyebrow">Program</span></div>
<div class="hdr" style="margin-top:8px"><span class="title">{{ rows[0]['program.name'].value | escape }}</span><span class="meta"><b>{{ rows[0]['program.block'].value | escape }}</b> block &middot; <b>{{ rows[0]['program.phase'].value | escape }}</b> phase &middot; week <b>{{ rows[0]['program.week'].value }}</b> &middot; day <b>{{ rows[0]['program.day'].value }}</b> of <b>{{ rows[0]['program.total_days'].value }}</b></span></div>
<div class="sub" style="margin-top:10px">{% if days and days >= 0 %}Meet {{ rows[0]['meet_s'].value | escape }} &middot; <span class="v">{{ days }}</span> days out &middot; {% elsif days %}{% assign days_ago = 0 | minus: days %}{{ rows[0]['meet_s'].value | escape }} was <span class="v">{{ days_ago }}</span> day{% unless days_ago == 1 %}s{% endunless %} ago &middot; {% endif %}{{ rows[0]['n'].value }} sessions logged in this block &middot; last trained {{ rows[0]['date_s'].value | escape }}</div>
{% endif %}"""))

SESSION_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Session</div>""" + empty("Open a session from any dashboard") + """{% else %}
<div class="hdr"><span class="eyebrow">Session</span><span class="eyebrow dim">{{ rows[0]['program.name'].value | escape }}</span></div>
{%- comment -%} Program tracking is newer than the log: program.week and program.day are
absent on everything logged before it. Printed unconditionally the hero rendered
"HYPERTROPHY - WEEK - DAY OF" on those sessions - the largest type on the page, with the
labels standing and the numbers gone. A label with no value is not a smaller fact, it is
a broken one, so the segment is only drawn when there is something to put in it. The
block name is always there and carries the line on its own. {%- endcomment -%}
<div class="hdr" style="margin-top:8px"><span class="title">{{ rows[0]['program.block'].value | default: "Session" | escape }}{% if rows[0]['program.week'].value %}<span class="dot"></span>week {{ rows[0]['program.week'].value }}{% endif %}{% if rows[0]['program.day'].value %}<span class="dot"></span>day {{ rows[0]['program.day'].value }}{% if rows[0]['program.total_days'].value %} of {{ rows[0]['program.total_days'].value }}{% endif %}{% endif %}</span></div>
<div class="sub" style="margin-top:10px"><span class="v">{{ rows[0]['date_s'].value | escape }}</span>{% if rows[0]['start_time'].value %} &middot; {{ rows[0]['start_time'].value | escape }}{% endif %}{% if rows[0]['time_of_day'].value %} &middot; {{ rows[0]['time_of_day'].value | escape }}{% endif %}{% if rows[0]['location.name'].value %} &middot; {{ rows[0]['location.name'].value | escape }}{% endif %}{% if rows[0]['location.travel'].value %} <span class="chip blood">travel</span>{% endif %}<br>
<span class="faint">prev</span> {{ rows[0]['prev_session_id'].value | default: "none" | escape }} &nbsp; <span class="faint">next</span> {{ rows[0]['next_session_id'].value | default: "none" | escape }} &nbsp; <span class="faint">the panel on the right filters this page to either one</span></div>
{% endif %}"""))

SESSION_TILES = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty() + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Tonnage</div><div class="value">""" + num("rows[0]['totals.tonnage_lb'].value") + """<small>$U_WEIGHT</small></div></div><div class="sub">moved this session</div></div>
<div class="card"><div class="top"><div class="eyebrow">Length</div>{% if rows[0]['duration_min'].value %}<div class="value">{{ rows[0]['duration_min'].value | round }}<small>min</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div><div class="sub">{{ rows[0]['streak_day'].value }} day streak</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg working RPE</div>{% if rows[0]['avg_working_rpe'].value %}<div class="value">""" + numr("rows[0]['avg_working_rpe'].value", 1) + """</div>{% else %}<div class="empty">Not logged</div>{% endif %}</div><div class="sub">{{ rows[0]['totals.working_sets'].value }} working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Sets</div><div class="value">{{ rows[0]['totals.sets'].value }}</div></div><div class="sub">{{ rows[0]['totals.reps'].value }} reps &middot; {{ rows[0]['totals.exercises'].value }} lifts</div></div>
{% endif %}
</div>"""))

TOP_SET_HERO = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Top set</div><div style="margin-top:10px">""" + empty("No working sets logged") + """</div>{% else %}
{%- assign sid = rows[0]['session_id'].value -%}{%- assign slug = rows[0]['lift_slug'].value -%}{%- assign tr = rows[0]['reps'].value -%}
{%- assign pw = "" -%}{%- assign pr = "" -%}{%- assign prpe = "" -%}{%- assign pd = "" -%}
{%- assign aw = "" -%}{%- assign ar = "" -%}{%- assign arpe = "" -%}{%- assign ad = "" -%}{%- assign ae = "" -%}
{%- comment -%} e1RM is the one tool that makes 185x5@8 and 150x8@6 comparable, and the
app already computes it per set for the Lift chart. This card was the only place that
declined to use it, printing "different reps, not compared" over the exact question a
lifter opens a session to ask. Read off est_e1rm rather than recomputed here: the model
is an RPE lookup in metrics.py and a second implementation in Liquid would drift from it
the first time the table moved. A low-confidence estimate is not carried - a comparison
the indexer has already said not to trust is worse than no comparison. {%- endcomment -%}
{%- assign ce = "" -%}
{%- unless rows[0]['e1rm_confidence'].value == "low" -%}{%- assign ce = rows[0]['est_e1rm'].value -%}{%- endunless -%}
{%- comment -%} How many sessions this panel can actually see. The comparison below scans
`rows` for a set from a DIFFERENT session_id, and the Session page is filtered to ONE -
which is how all seven drilldowns land here. So on the page this card is built for the
scan always came up empty and the card printed "first time on record for this lift" over
every top set a lifter ever drilled into: a false statement where silence belonged.
It is only a claim the panel is entitled to make when it had more than one session to
look at. Distinct rather than a row count: one session is many rows. {%- endcomment -%}
{%- assign seen_sids = "" -%}{%- assign sessions_seen = 0 -%}
{%- for r in rows -%}
{%- assign _sid = r['session_id'].value | append: "|" -%}
{%- unless seen_sids contains _sid -%}
{%- assign seen_sids = seen_sids | append: _sid -%}
{%- assign sessions_seen = sessions_seen | plus: 1 -%}
{%- endunless -%}
{%- endfor -%}
{%- for r in rows -%}{%- if r['session_id'].value != sid and r['lift_slug'].value == slug -%}
{%- if pw == "" and r['reps'].value == tr -%}{%- assign pw = r['weight_lb'].value -%}{%- assign pr = r['reps'].value -%}{%- assign prpe = r['rpe'].value -%}{%- assign pd = r['date_s'].value -%}{%- endif -%}
{%- if aw == "" -%}{%- assign aw = r['weight_lb'].value -%}{%- assign ar = r['reps'].value -%}{%- assign arpe = r['rpe'].value -%}{%- assign ad = r['date_s'].value -%}{%- unless r['e1rm_confidence'].value == "low" -%}{%- assign ae = r['est_e1rm'].value -%}{%- endunless -%}{%- endif -%}
{%- endif -%}{%- endfor -%}
""" + rpe_class("rows[0]['rpe'].value") + """
<div class="eyebrow">Top set</div>
<div style="margin-top:7px;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
<span class="hero">""" + num("rows[0]['weight_lb'].value") + """<span style="font-size:20px;color:$DIM;margin-left:6px">$U_WEIGHT</span></span>
{% if rows[0]['reps'].value %}<span class="hero" style="font-size:26px;color:$DIM">&times;&nbsp;""" + numr("rows[0]['reps'].value") + """</span>{% endif %}
{% if rows[0]['rpe'].value %}<span class="set" style="padding:0"><span class="rpe {{ rc }}" style="font-size:21px">@&nbsp;{{ rows[0]['rpe'].value | round: 1 }}</span></span>{% endif %}
</div>
<div class="value" style="font-size:17px;margin-top:7px;white-space:normal">{{ rows[0]['exercise.name'].value | escape }}</div>
{% if pw != "" or aw != "" or sessions_seen > 1 %}<div class="rule" style="margin-top:10px;padding-top:8px">
{% if pw != "" %}{%- assign delta = rows[0]['weight_lb'].value | minus: pw -%}
<span class="sub"><span class="faint">last {{ pr | round }}-rep set</span>&nbsp; <span class="v">""" + num("pw") + """&nbsp;&times;&nbsp;{{ pr | round }}</span>{% if prpe %} <span class="faint">@&nbsp;{{ prpe | round: 1 }}</span>{% endif %} <span class="faint">&middot; {{ pd | escape }}</span></span>
{% if delta > 0 %}<span class="chip blood">+{{ delta | round }} $U_WEIGHT</span>{% elsif delta < 0 %}<span class="chip">{{ delta | round }} $U_WEIGHT</span>{% else %}<span class="chip">same weight</span>{% endif %}
{% elsif aw != "" %}<span class="sub"><span class="faint">last time</span>&nbsp; <span class="v">""" + num("aw") + """&nbsp;&times;&nbsp;{{ ar | round }}</span>{% if arpe %} <span class="faint">@&nbsp;{{ arpe | round: 1 }}</span>{% endif %} <span class="faint">&middot; {{ ad | escape }}</span> {% comment %}Neither `!= ""` nor truthiness works here and both were tried. A row projecting est_e1rm as null assigns nil, and nil != "" is TRUE, so the first guard printed an arrow between two blanks. In Liquid only nil and false are falsy - the empty string is truthy - so the second guard compared a skipped low-confidence estimate as 0 and reported the whole of the current estimate as a gain. `| plus: 0` sends nil and "" both to 0, which is the one test that holds for every shape this row arrives in.{% endcomment %}{% assign aev = ae | plus: 0 %}{% assign cev = ce | plus: 0 %}{% if aev > 0 and cev > 0 %}<span class="faint">&mdash; e1RM</span> <span class="v">{{ aev | round }}&nbsp;&rarr;&nbsp;{{ cev | round }}</span>{% assign ed = cev | minus: aev %}{% if ed > 0 %} <span class="chip blood">+{{ ed | round }} $U_WEIGHT</span>{% elsif ed < 0 %} <span class="chip">{{ ed | round }} $U_WEIGHT</span>{% else %} <span class="chip">level</span>{% endif %}{% else %}<span class="faint">&mdash; different reps, and neither set carries an estimate to compare them on</span>{% endif %}</span>
{% else %}<span class="sub faint">first time on record for this lift</span>{% endif %}</div>{% endif %}
{% endif %}"""))

CONDITIONS_CARD = page(tok("""
<div class="eyebrow">Conditions</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="grid3" style="margin-top:10px">
<div><div class="eyebrow">Temp</div>{% if rows[0]['environment.temp_f'].value %}<div class="value">{{ rows[0]['environment.temp_f'].value | round }}<small>$U_TEMP</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
<div><div class="eyebrow">Humidity</div>{% if rows[0]['environment.humidity_pct'].value %}<div class="value">{{ rows[0]['environment.humidity_pct'].value | round }}<small>%</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
<div><div class="eyebrow">Sky</div>{% if rows[0]['environment.conditions'].value %}<div class="sub" style="margin-top:7px;color:$CHALK;font-size:13px;line-height:1.45">{{ rows[0]['environment.conditions'].value | escape }}</div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
</div>
<div class="sub" style="margin-top:10px">{% if rows[0]['environment.wind'].value %}{{ rows[0]['environment.wind'].value | escape }}{% if rows[0]['environment.setting'].value %} &middot; {% endif %}{% endif %}{{ rows[0]['environment.setting'].value | escape }}</div>
{% endif %}"""))

PERFORMANCE_CARD = page(tok("""
<div class="eyebrow">Performance</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No sets logged") + """</div>{% else %}
{%- assign sid = rows[0]['session_id'].value -%}
{%- assign has_prep = false -%}{%- for r in rows -%}{%- if r['session_id'].value == sid and r['exercise.category'].value == "prep" -%}{%- assign has_prep = true -%}{%- endif -%}{%- endfor -%}
<div class="cols" style="margin-top:8px">
{% assign cur = "" %}{% for r in rows %}{% if r['session_id'].value == sid and r['exercise.category'].value != "prep" %}{% if r['exercise.name'].value != cur %}{% unless cur == "" %}</div>{% endunless %}{% assign cur = r['exercise.name'].value %}<div class="ex"><div class="name">{{ cur | escape }}<span class="cat">{{ r['exercise.category'].value | escape }}</span></div>{% endif %}
<div class="set {{ r['set_type'].value | escape }}">""" + rpe_class("r['rpe'].value") + """<span class="n">{{ r['set_number'].value }}</span><span class="w">{% if r['load_type'].value == "bodyweight" %}BW{% elsif r['weight_lb'].value == 0 or r['weight_lb'].value == nil %}<span class="faint">&mdash;</span>{% else %}""" + num("r['weight_lb'].value") + """{% endif %}</span><span class="x">&times;</span><span class="r">""" + numr("r['reps'].value") + """{% if r['rep_unit'].value == "walks" %} walks{% if r['distance_ft'].value %} &middot; {{ r['distance_ft'].value | round }} $U_DISTANCE{% endif %}{% elsif r['rep_unit'].value == "seconds" %} s{% endif %}</span>{% if r['rpe'].value %}<span class="rpe {{ rc }}">@ {{ r['rpe'].value | round: 1 }}</span>{% endif %}{% if r['gear_s'].value %}<span class="chip">{{ r['gear_s'].value | escape }}</span>{% endif %}<span class="note">{{ r['notes'].value | escape }}</span></div>
{% endif %}{% endfor %}{% unless cur == "" %}</div>{% endunless %}
</div>
{% if has_prep %}<div class="rule" style="margin-top:10px;padding-top:8px">
<div class="eyebrow">Warm-up</div>
<div class="warm">{%- assign pcur = "" -%}{%- assign firstp = true -%}{% for r in rows %}{% if r['session_id'].value == sid and r['exercise.category'].value == "prep" %}{% if r['exercise.name'].value != pcur %}{%- assign pcur = r['exercise.name'].value -%}{% unless firstp %}<span class="sep">&middot;</span>{% endunless %}{%- assign firstp = false -%}<span class="nm">{{ pcur | escape }}</span>{% endif %}<span class="qty">{% if r['load_type'].value == "bodyweight" %}BW{% else %}""" + num("r['weight_lb'].value") + """{% endif %}&times;""" + numr("r['reps'].value") + """{% if r['rep_unit'].value == "seconds" %}s{% endif %}</span>{% endif %}{% endfor %}</div>
</div>{% endif %}
{% endif %}"""))

NOTES_CARD = page(tok("""
<div class="eyebrow">Notes</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No notes") + """</div>{% else %}
{% assign sid = rows[0]['session_id'].value %}
<div class="list" style="margin-top:8px">
{% for r in rows %}{% if r['session_id'].value == sid %}<div class="item"><span class="when">{{ r['phase'].value | escape }}</span><span class="txt"><span class="prose" style="color:$CHALK">{{ r['text'].value | escape }}</span>{% if r['exercise.name'].value %} <span class="faint">{{ r['exercise.name'].value | escape }}</span>{% endif %}{% if r['tags_s'].value %}<br>{% assign tags = r['tags_s'].value | split: "|" %}{% for t in tags %}<span class="chip">{{ t | escape }}</span>{% endfor %}{% endif %}</span></div>{% endif %}{% endfor %}
</div>{% endif %}"""))


WRAP_CARD = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Wrap up</div><div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="eyebrow">Wrap up</div>
<div class="prose" style="margin-top:8px">{{ rows[0]['wrap_up'].value | default: "Not written" | escape }}</div>
{% if rows[0]['watch_s'].value %}<div class="eyebrow" style="margin-top:14px">Watch</div><div class="list" style="margin-top:4px">{% assign items = rows[0]['watch_s'].value | split: "|" %}{% for w in items %}<div class="item"><span class="txt" style="font-size:11px">{{ w | escape }}</span></div>{% endfor %}</div>{% endif %}
{% if rows[0]['gear_notes'].value %}<div class="eyebrow" style="margin-top:14px">Gear</div><div class="prose" style="margin-top:4px;font-size:12px">{{ rows[0]['gear_notes'].value | escape }}</div>{% endif %}
{% endif %}"""))

# The lift name and its numbers on one line. Until Phase 3 this was the name plus three
# hero tiles - best e1RM, best top set, avg RPE - which is the set of numbers a phone
# already shows, drawn at the same weight as the verdict underneath. Worse, BEST E1RM
# said 420 while the verdict beside it said "your best 420" and the chart's reference
# line sat at 420: the same number three times, twice as decoration.
#
# The numbers stay, at body size, on the sub-line. Nothing is lost and the verdict leads.

# The cold start, and how the panel knows it is in one. Lift carries no lift_slug
# control on purpose (a control and a drilldown on the same field empty the page), so
# the ONLY thing that narrows this page to one lift is an incoming filter. The query is
# LIMIT 2 rather than LIMIT 1 for exactly this: filtered, one row comes back; unfiltered,
# two do, and the panel can tell which without being told. Before it could not, and a
# stranger clicking LIFT in the nav got a header naming one lift over charts drawn from
# everything they had ever lifted.
LIFT_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Lift</div>""" + empty("Open a lift from any dashboard") + """
{% elsif rows.size > 1 %}<div class="eyebrow">Lift</div>
<div class="hdr" style="margin-top:8px"><span class="title" style="font-size:30px;font-weight:700;text-transform:uppercase;line-height:1;color:$DIM">No lift chosen</span></div>
<div class="sub" style="margin-top:8px">This page is one exercise over time, and nothing has told it which one.
Everything below is drawn from every lift in the range, so read it as a total and not as a lift.<br>
<span class="faint">Click a lift in Overview's projected-total chart, or a point on this page's e1RM line, to land here on one lift.</span></div>
{% else %}
<div class="row">
<div class="card" style="flex:1"><div class="top"><div class="eyebrow">Lift</div><div class="title" style="font-size:30px;font-weight:700;text-transform:uppercase;line-height:1">{{ rows[0]['name'].value | escape }}</div></div>
<div class="sub">{{ rows[0]['sessions'].value }} session{% if rows[0]['sessions'].value != 1 %}s{% endif %} &middot; {{ rows[0]['n'].value }} working sets &middot; last {{ rows[0]['last_s'].value | escape }}</div>
<div class="sub">best e1RM&nbsp;""" + num("rows[0]['e1'].value") + """&nbsp;$U_WEIGHT &middot; best top set&nbsp;""" + num("rows[0]['top'].value") + """&nbsp;$U_WEIGHT{% if rows[0]['rpe'].value %} &middot; avg RPE """ + numr("rows[0]['rpe'].value", 1) + """{% endif %}</div></div>
</div>{% endif %}"""))


# --------------------------------------------------------------------------- Program days, Meets, Mindset


# FOUR_CARDS lived here: tonnage in range, per session, sessions, avg working RPE, drawn
# on History. Cut 2026-09-05 with Phase 3 - those are the four tiles a Hevy home screen
# already shows, and every one of them is still on the page in the sessions table and the
# timeline. Deleted rather than left unbuilt: verify_liquid fails a template that no
# dashboard draws, which is how this one was found the minute the panel went away.

MEET_CARDS = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty("No meets logged") + """</div>{% else %}
{%- comment -%} "logged" and "all meets" were lies at any picker narrower than the
record: at two years this read "1 competitions logged, 100% success" against a real
2 and 83%. The tiles now say what they count. {%- endcomment -%}
{%- comment -%} On a record with totals the best finish rides on the count tile rather
than taking a fifth of its own: the row is four tiles wide and measured at that width,
and a placing is a fact about the meets counted here rather than a fifth independent
measurement. On a points record the tile beside this one IS the placing, so this line
stands down rather than printing the same number twice in one row. {%- endcomment -%}
{%- assign pts = rows[0]['pts'].value | plus: 0 -%}
<div class="card"><div class="top"><div class="eyebrow">Meets</div><div class="value">{{ rows[0]['meets'].value }}</div></div><div class="sub">in the page's range{% if rows[0]['best_place'].value and pts == 0 %}<br>best finish <span class="v">{{ rows[0]['best_place'].value }}""" + ordinal("rows[0]['best_place'].value") + """</span>{% endif %}</div></div>
{%- comment -%} A meet scored on points has no total and no DOTS, and the two tiles
that print them would read "Not logged" forever - which says the lifter forgot to write
something down, when in fact their sport does not produce it. The tiles change question
instead: best placing and best points score, off the record. {%- endcomment -%}
{% if pts > 0 %}
<div class="card"><div class="top"><div class="eyebrow">Best placing</div>{% if rows[0]['best_place'].value %}<div class="value" style="color:$BLOOD">{{ rows[0]['best_place'].value }}<small>""" + ordinal("rows[0]['best_place'].value") + """</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div><div class="sub">{% if rows[0]['best_place'].value %}best finish in the page's range{% else %}no placing on any meet in range{% endif %}</div></div>
{% else %}
<div class="card"><div class="top"><div class="eyebrow">Best total</div>{% if rows[0]['total_kg'].value %}<div class="value" style="color:$BLOOD">""" + numr("rows[0]['total_kg'].value", 1) + """<small>$U_MASS_ALT</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div><div class="sub">{% if rows[0]['total_lb'].value %}""" + num("rows[0]['total_lb'].value") + """&nbsp;$U_WEIGHT{% else %}no total on any meet in range{% endif %}</div></div>
{% endif %}
{%- comment -%} DOTS needs a bodyweight and a sex to compute, and the indexer leaves it
ABSENT rather than assuming one. `nil | round: 2` is 0, so the tile read "BEST DOTS 0"
for every lifter who had not configured a sex - a score, in a unit, that no one scored.
{%- endcomment -%}
{% if pts > 0 %}
<div class="card"><div class="top"><div class="eyebrow">Best points</div>{% if rows[0]['best_points'].value %}<div class="value">""" + numr("rows[0]['best_points'].value", 1) + """</div>{% else %}<div class="empty">Not scored</div>{% endif %}</div><div class="sub">{% if rows[0]['best_points'].value %}across those meets{% else %}no points on any meet in range{% endif %}</div></div>
{% else %}
<div class="card"><div class="top"><div class="eyebrow">Best DOTS</div>{% if rows[0]['dots'].value %}<div class="value">""" + numr("rows[0]['dots'].value", 1) + """</div>{% else %}<div class="empty">Not scored</div>{% endif %}</div><div class="sub">{% if rows[0]['dots'].value %}across those meets{% else %}DOTS needs a bodyweight and a sex on the meet{% endif %}</div></div>
{% endif %}
<div class="card"><div class="top"><div class="eyebrow">Attempts made</div>{%- assign att = rows[0]['attempts'].value | plus: 0 -%}{% if att > 0 %}<div class="value">{{ rows[0]['made'].value }}<small>of {{ rows[0]['attempts'].value }}</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div><div class="sub">{% if att > 0 %}{{ rows[0]['made'].value | times: 100 | divided_by: att | round }}% made in range{% else %}no attempts logged{% endif %}</div></div>
{% endif %}
</div>"""))

MEET_BESTS = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Best lifts</div>""" + empty("No meets logged") + """{% else %}
{%- assign best = rows[0]['lb'].value | plus: 0 -%}
<div class="eyebrow">Best lifts on the platform <span class="faint">&middot; weight events only</span></div>
<div style="margin-top:10px">
{% for r in rows %}<div class="liftrow"><span class="lname">{{ r['event_name'].value | escape }}</span><span class="lval">""" + num("r['lb'].value") + """<small style="font-size:11px;color:$FAINT;margin-left:4px">$U_WEIGHT</small></span><span class="lbar"><i style="width:{% if best > 0 %}{{ r['lb'].value | times: 100 | divided_by: best | round }}{% else %}0{% endif %}%"></i></span><span class="lkg">{% if r['kg'].value %}""" + numr("r['kg'].value", 1) + """ $U_MASS_ALT{% endif %}</span></div>{% endfor %}
</div>{% endif %}"""))

MEET_LIST = page(tok("""
<div class="eyebrow">Meets <span class="faint">&middot; struck through = missed</span></div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No meets logged") + """</div>{% else %}
<div class="row" style="margin-top:10px;height:auto;gap:0">
{% assign cur = "" %}{% for r in rows %}{% if r['meet_id'].value != cur %}{% unless forloop.first %}</div></div>{% endunless %}{% assign cur = r['meet_id'].value %}{% assign curlift = "" %}
<div class="card"><div class="top"><div class="value" style="font-size:20px">{{ r['date_s'].value | escape }}</div><div class="sub">{%- comment -%} Three clauses that each stand or fall on their own, not a chain of
elsifs. Written as an elsif chain, a PLACING was shown only where there was no total to
show instead - so on a powerlifting record, where every meet has a total, first place
never appeared anywhere in the app. That is the result the lifter is most likely to say
out loud, and it was structurally unreachable.

The `shown` flag carries the separator rather than each clause assuming one, because a
meet may have any combination of the three and a leading or doubled middot is the tell
that a line was assembled by guessing. And "no total recorded" prints only when none of
the three said anything: a show scored on points has no total by definition, and that
phrase read as a reproach on every one of them. {%- endcomment -%}{%- assign shown = 0 -%}{% if r['total_kg'].value %}<span class="v">""" + numr("r['total_kg'].value", 1) + """</span> $U_MASS_ALT total{% assign shown = 1 %}{% endif %}{% if r['placing'].value %}{% if shown == 1 %} &middot; {% endif %}<span class="v">{{ r['placing'].value }}""" + ordinal("r['placing'].value") + """</span> place{% assign shown = 1 %}{% endif %}{% if r['points'].value %}{% if shown == 1 %} &middot; {% endif %}<span class="v">""" + numr("r['points'].value", 1) + """</span> points{% assign shown = 1 %}{% endif %}{% if shown == 0 %}<span class="faint">no total recorded</span>{% endif %}{% if r['dots'].value %} &middot; <span class="v">""" + numr("r['dots'].value", 1) + """</span> DOTS{% endif %}{% if r['bodyweight_kg'].value %} &middot; """ + numr("r['bodyweight_kg'].value", 1) + """ $U_MASS_ALT bw{% endif %}</div></div><div class="grid3" style="margin-top:10px">{% endif %}
{% if r['event_name'].value != curlift %}{% assign curlift = r['event_name'].value %}{% endif %}
{%- comment -%} The chip carried weight_kg, which is null on every event that is not
measured in kilograms - so a 12.9-second yoke run and a 5-rep sandbag ladder both
rendered as an em dash, indistinguishable from an attempt nobody wrote down. It prints
`value` in the event's own unit instead, and names the unit, because 12.9 and 12.9 kg
are not the same fact. {%- endcomment -%}
<div><div class="eyebrow" style="letter-spacing:.1em">{{ r['event_name'].value | escape }} {{ r['attempt_no'].value }}</div><span class="chip {% if r['made'].value %}made{% else %}miss{% endif %}">{% if r['value'].value %}""" + numr("r['value'].value", 1) + """{% assign u = r['unit'].value %}{% if u == "seconds" %}s{% elsif u == "reps" %} reps{% elsif u == "m" %} m{% endif %}{% else %}&mdash;{% endif %}</span></div>
{% if forloop.last %}</div></div>{% endif %}{% endfor %}
</div>{% endif %}"""))

RECENT_NOTES = page(tok("""
<div class="eyebrow">Recent notes</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No notes") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{{ r['date_s'].value | escape }}<br><span style="color:$DIM">{{ r['phase'].value | escape }}</span></span><span class="txt"><span class="prose" style="color:$CHALK">{{ r['text'].value | escape }}</span>{% if r['exercise.name'].value %} <span class="faint">{{ r['exercise.name'].value | escape }}</span>{% endif %}{% if r['tags_s'].value %}<br>{% assign tags = r['tags_s'].value | split: "|" %}{% for t in tags %}<span class="chip">{{ t | escape }}</span>{% endfor %}{% endif %}</span></div>{% endfor %}
</div>{% endif %}"""))


# --------------------------------------------------------------------------- Signal cards
#
# Verdict cards for the Overview Signal row. A card states a finding in a sentence,
# with the number as supporting evidence and its provenance stated out loud. The
# analytics were cut from the dashboards in the Sept 4 lifter audit not for being
# wrong but for being shipped as measurements; this is the same data in the form
# that carries a judgment.
#
# Every card renders "not enough data yet" as a first-class state. No zeros standing
# in for absence.

SIGNAL_CSS = tok("""<style>
/* Plain block flow, no height:100% and no margin-top:auto. The panel iframe is not
   always the height Kibana implies, and anything that pushes to the bottom opened a
   ~100px hole between a number and its caption on the Session cards. */
.sig{display:block}
.sig .q{font-family:$MONO;font-size:10px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:$STEEL;line-height:1.45}
.sig .verdict{font-size:20px;font-weight:600;line-height:1.25;letter-spacing:-.005em;margin-top:9px;color:$CHALK}
.sig .verdict.b-light{color:$DIM;font-weight:500}
.sig .verdict.b-normal{color:$CHALK;font-weight:600}
.sig .verdict.b-heavy{color:$CHALK;font-weight:700}
.sig .verdict.b-max{color:$CHALK;font-weight:700}
/* The max band used to be the only verdict headline drawn in oxblood, which put the
   single most important sentence on History at ~2.5:1 on this ground - the hardest
   text in the app to read, and the only page whose verdict did not look like the
   other six. The red signal survives as a mark rather than as type. */
.sig .verdict.b-max::after{content:"";display:inline-block;width:8px;height:8px;background:$BLOOD;margin-left:10px;vertical-align:middle}
.sig .ev{font-family:$MONO;font-size:12px;color:$DIM;letter-spacing:.02em;line-height:1.6;margin-top:9px;font-variant-numeric:tabular-nums}
.sig .ev b{color:$CHALK;font-weight:600}
/* The baseline tick is what makes the bar an argument instead of a decoration. */
.sig .gauge{height:3px;background:$RULE;position:relative;margin:10px 0 6px}
.sig .gauge i{position:absolute;left:0;top:0;bottom:0;background:$BLOOD;display:block}
.sig .gauge u{position:absolute;top:-4px;bottom:-4px;width:1px;background:$STEEL;display:block}
.sig .base{font-family:$MONO;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:$STEEL}
.sig .also{font-family:$MONO;font-size:12px;color:$DIM;letter-spacing:.02em;line-height:1.7;margin-top:7px;font-variant-numeric:tabular-nums}
.sig .prov{font-family:$MONO;font-size:11px;line-height:1.6;color:$DIM;letter-spacing:.02em;margin-top:12px;padding-top:9px;border-top:1px solid $RULE}
.sig .see{font-family:$MONO;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:$STEEL;margin-top:8px}
.sig .none{font-family:$MONO;font-size:12px;color:$DIM;letter-spacing:.03em;margin-top:10px;line-height:1.55}
</style>""")


# A custom content panel takes NO POINTER INPUT AT ALL. Not "links are stripped" - the
# panel is inert: probe_disclosure.py put five mechanisms in one panel and clicked and
# hovered every one. <details>/<summary> rendered and would not open. A checkbox and its
# label rendered and would not toggle. A CSS :hover reveal never fired. A title= tooltip
# never appeared. Only plain text works.
#
# So there is no tooltip, no disclosure and no hover here, and there cannot be. The
# provenance is not load-bearing enough to justify a quarter of a thousand words on the
# opening screen of a page whose job is three sentences, and it cannot be folded away, so
# it is CUT: each card keeps the sentence that makes its number defensible and drops the
# mechanism. The mechanism is what the coach is for, and Overview says so directly under
# the Signal row.
def signal(question: str, body: str, prov: str, see: str = "") -> str:
    """One verdict card: question, verdict, evidence, provenance, drilldown hint.

    The provenance line is not optional. It is what makes the number defensible
    instead of decorative, and it is the honest place to say what a metric cannot
    see. `see` is a text pointer, not a link: custom content panels render in a
    sandboxed iframe with no scripts and no <a href>, so the Links panel is the
    only real door on the page.

    Re-verified 2026-09-05 with kibana/probe_links.py, before Phase 4 built anything
    on top of it. Four buttons in one panel, identical CSS: <a target="_top">,
    <a target="_blank">, <a> with no target, and a <span> as the control. The span
    rendered as the styled button; all three anchors came out as bare text having
    lost even their class, and clicking them did nothing. Kibana strips the element,
    not just its behaviour. So a coach button drawn inside a card is not possible,
    and neither is our own nav - which is what would have made embed mode stick.
    """
    tail = f'<div class="see">{see}</div>' if see else ""
    # tok() over the assembled card, not just the CSS. The bodies are plain module
    # strings and carry $U_WEIGHT and $TZ_OFF now; an unsubstituted token is a Liquid
    # syntax error, which blanks the panel.
    return tok(BASE_CSS + SIGNAL_CSS + '<div class="sig">'
               + f'<div class="q">{question}</div>'
               + body
               + f'<div class="prov">{prov}</div>' 
               + tail + "</div>")


# --- 1. intensity ----------------------------------------------------------
#
# Counts, not share. Measured over Mike's 178 weeks the share of main-lift reps at
# 80%+ has a median of 1.9% and a p25 of 0.0 — half his weeks carry essentially no
# heavy main-lift work — while a week with four main-lift reps, all heavy, scores
# 100%. Banding that share would have printed "unusually heavy" off a denominator
# of four. The rep count cannot blow up, and ranking it against his own recent
# weeks is the judgment the card exists to deliver.

_INTENSITY_BODY = """
{%- if rows.size == 0 -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet,
or a filter on this page excludes them &mdash; this card ignores the time picker, but not
the filter bar.</div>
{%- else -%}
{%- assign hv = rows[0]['heavy'].value | plus: 0 -%}
{%- assign tot = rows[0]['tot'].value | plus: 0 -%}
{%- if tot == 0 -%}
<div class="none">No main-lift reps logged this week.<br>Nothing to weigh yet.</div>
{%- else -%}
{%- comment -%} `equal` is not a rounding detail. Thirteen weeks of heavy = 0 is an
ordinary hypertrophy block, and counting a tie as a loss made every one of those weeks
read "Lighter than every one of your last 13 weeks" under evidence saying 0 of 80. Ties
are carried separately and score half, so a week level with its history lands mid-scale.
{%- endcomment -%}
{%- assign open_wk = false -%}
{%- if rows[0]['week_state'].value == "in-progress" -%}{%- assign open_wk = true -%}{%- endif -%}
{%- comment -%} An open week has fewer days in it than the weeks it is being ranked
against, so a raw count compares a Wednesday with twelve Sundays. The indexer writes
heavy_per_training_day for exactly this, and until the query carried it the card ranked
counts and printed "still open" underneath - a caption on an unqualified verdict rather
than a correction to it. Rank the rate while the week is open, the count once it closes,
and say which. {%- endcomment -%}
{%- assign cur = hv -%}
{%- if open_wk -%}{%- assign cur = rows[0]['heavy_per_training_day'].value | plus: 0 -%}{%- endif -%}
{%- assign prior = 0 -%}{%- assign beat = 0 -%}{%- assign equal = 0 -%}
{%- assign sum = 0 -%}{%- assign maxv = cur -%}
{%- for r in rows offset: 1 -%}
  {%- assign rt = r['tot'].value | plus: 0 -%}
  {%- if rt > 0 -%}
    {%- assign rh = r['heavy'].value | plus: 0 -%}
    {%- assign rv = rh -%}
    {%- if open_wk -%}{%- assign rv = r['heavy_per_training_day'].value | plus: 0 -%}{%- endif -%}
    {%- assign prior = prior | plus: 1 -%}
    {%- assign sum = sum | plus: rh -%}
    {%- if rv < cur -%}{%- assign beat = beat | plus: 1 -%}
    {%- elsif rv == cur -%}{%- assign equal = equal | plus: 1 -%}{%- endif -%}
    {%- if rv > maxv -%}{%- assign maxv = rv -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- comment -%} How much history exists is the indexer's answer, not a count of the rows
this query happened to return: a week with no main-lift work in it, and the week still
in progress, both come back and neither can be ranked against, so counting rows told a
lifter with ten usable weeks behind them that they had thirteen.

It is not unbounded. derive.INTENSITY_WEEKS is 13 and weeks_available is counted over
those thirteen rows with the open week excluded, so it maxes out at 12 - the same
ceiling the ranking itself has. A fixture asserting 31 here would be asserting on a
number the indexer cannot produce. {%- endcomment -%}
{%- assign avail = prior -%}
{%- if rows[0]['weeks_available'].value -%}
{%- assign avail = rows[0]['weeks_available'].value | plus: 0 -%}
{%- endif -%}
{%- if prior < 4 -%}
<div class="verdict b-normal">{{ hv }} rep{% unless hv == 1 %}s{% endunless %} at 80% or more.</div>
<div class="ev">Out of <b>{{ tot }}</b> main-lift reps this week.</div>
{%- if open_wk -%}<div class="base">this week is still open; both counts will grow</div>{%- endif -%}
<div class="none">Ranking a week against your own history needs 4 earlier weeks
carrying main-lift work. You have <b>{{ avail }}</b>.
</div>
{%- else -%}
{%- comment -%} (beat + equal/2) / prior, in integer arithmetic. {%- endcomment -%}
{%- assign share = beat | times: 2 | plus: equal | times: 50 | divided_by: prior -%}
{%- assign band = "b-light" -%}
{%- if share >= 85 -%}{%- assign band = "b-max" -%}
{%- elsif share >= 60 -%}{%- assign band = "b-heavy" -%}
{%- elsif share >= 25 -%}{%- assign band = "b-normal" -%}{%- endif -%}
<div class="verdict {{ band }}">
{%- if beat == prior -%}Heavier than any of your last {{ prior }} weeks.
{%- elsif equal == prior -%}Level with your last {{ prior }} weeks.
{%- elsif beat == 0 and equal == 0 -%}Lighter than every one of your last {{ prior }} weeks.
{%- elsif beat == 0 -%}Level with {{ equal }} of your last {{ prior }} weeks, under the rest.
{%- else -%}Heavier than {{ beat }} of your last {{ prior }} weeks.{%- endif -%}
</div>
{%- assign avg = sum | times: 1.0 | divided_by: prior -%}
<div class="ev"><b>{{ hv }}</b> of {{ tot }} main-lift reps at 80% or more of your best in the last 90 days.
{%- if equal > 0 and beat > 0 and beat != prior %} Level with {{ equal }} of them.{% endif -%}
</div>
{%- if open_wk -%}<div class="base">this week is still open, so it is ranked on heavy reps
per training day &mdash; {{ cur | round: 1 }} across {{ rows[0]['training_days'].value }} so far</div>{%- endif -%}
{%- comment -%} The gauge has to be drawn on whatever the verdict was ranked on, or a
partial week's bar reads short under a sentence saying it is ahead. {%- endcomment -%}
{%- if maxv > 0 -%}
{%- assign avgv = avg -%}
{%- if open_wk -%}
{%- assign sumv = 0 -%}
{%- for r in rows offset: 1 -%}
  {%- assign rt2 = r['tot'].value | plus: 0 -%}
  {%- if rt2 > 0 -%}
    {%- assign rd = r['heavy_per_training_day'].value | plus: 0 -%}
    {%- assign sumv = sumv | plus: rd -%}
  {%- endif -%}
{%- endfor -%}
{%- assign avgv = sumv | times: 1.0 | divided_by: prior -%}
{%- endif -%}
{%- assign w = cur | times: 100 | divided_by: maxv | round -%}
{%- assign bx = avgv | times: 100 | divided_by: maxv | round -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:{{ bx }}%"></u></div>
{%- endif -%}
<div class="base">your {{ prior }}-week average: {{ avg | round: 1 }} rep{% unless avg == 1 %}s{% endunless %} a week</div>
{%- endif -%}
{%- endif -%}
{%- endif -%}
"""

# The three Overview cards state their SCOPE and nothing else.
#
# Provenance is what makes a number defensible instead of decorative, and it has never
# been optional. But the three cards ran side by side above the fold, and a ~40-word
# method paragraph on each put 125 words of mechanism on the first screen of the page
# whose entire job is three sentences. The earlier pass halved that text in place -
# because probe_disclosure.py had proved a custom content panel takes NO pointer input
# at all and there was nowhere to fold it to. Halving something that should not be on
# the card still leaves it on the card.
#
# The panel being inert does not mean the text has to live on the card. It means it has
# to live in a DIFFERENT PANEL. So each card keeps the one clause a reader needs to
# judge the number at a glance - what window, what population - and the mechanism moves
# whole to SIGNAL_METHOD at the bottom of the page. Nothing is deleted and nothing is
# hidden: it is one scroll down, in full, in one place where the three can be read
# against each other.
#
# METHOD_* is the single copy of each. A card and its method are one explanation, and
# the way that goes wrong is two copies drifting apart, so the card cannot restate it -
# verify_liquid fails any card carrying a sentence from these.
SCOPE_INTENSITY = "main lifts only &middot; ranked against your last 13 weeks"
SCOPE_LOAD = "tonnage &middot; 7 days against the trailing 28"
SCOPE_DRIFT = "working sets, whole log, last 365 days &middot; not this page"

# The moat is already said twice on this page - in the brand-bar tagline above the nav
# and in this card's own evidence line. What is left for the method to carry is the part
# neither of those says: WHY the trailing window is the right one, and why the card one
# click away can rank the same week differently.
METHOD_INTENSITY = (
    # "This one measures against your best in the last 90 days" was here and came out
    # again. That sentence is already the brand-bar tagline above the nav AND the card's
    # own evidence line; a third copy is the exact duplication the card's provenance was
    # cut for in the first place, reintroduced by writing this paragraph fresh instead of
    # moving the one that existed. What the method owes the reader is the REASON, which
    # is said nowhere else.
    "Every logging app measures a set against an all-time PR, so a lifter back from a "
    "layoff sees everything as light. Main lifts only. Program ranks the same week on "
    "work, not weight, so a week can come out heavy here and easy there - that "
    "disagreement is a finding, not a fault.")
METHOD_LOAD = (
    "Acute:chronic is a flag, not a prediction. Load is tonnage, so a week you did not "
    "train reads as zero and the ratio moves on a rest day. Precedent reads only the "
    "weeks this card was handed.")
METHOD_DRIFT = (
    "Normal is that group's own average gap, measured across the stretch it has "
    "actually been trained; a group is flagged past twice it. Fewer than 6 sessions is "
    "not ranked. This card reads the whole log and ignores the time picker.")

SIGNAL_INTENSITY = signal(
    "How heavy was this week",
    _INTENSITY_BODY,
    SCOPE_INTENSITY,
    "See History &#9656; where the reps live",
)


# --- 2. load trend ---------------------------------------------------------
#
# ACWR is already load_7d/7 over load_28d/28, so "x% above your 4-week average" is
# (acwr - 1) x 100 and cannot disagree with the band beside it. The precedent lookup
# is what turns a flag into a judgment, and it has to skip the contiguous run of the
# current band or it reports last week.

# The day the windows were measured back from, said once, in whichever evidence line ran.
#
# Both branches of the load card make the same implicit claim - "the last 28 days", "your
# 4-week average" - and neither could say what those windows ended on until derive carried
# load_window_end onto the load row. week_end is the last day TRAINED; load_window_end is
# the week's own end, or today while the week is open. When they differ the ratio has moved
# since the lifter last trained, which is the single most confusing thing this card does,
# and naming both dates is what explains it.
#
# When they are the SAME the card says so once. Printing "measured to Sep 6; you last
# trained Sep 6" is a distinction with nothing on either side of it, and a card that
# repeats a date to say two things are equal reads worse than one that just names it.
#
# Absent, it says nothing at all rather than a blank or a nil: an index written before the
# field existed still renders, and declines. Guarded the same way layoff_min_training_days
# is, and for the same reason - absence here means "this index predates the field", not
# "the window ended on nothing".
#
# One string, substituted into both branches, because two copies of this are two things to
# keep in step and the drift would be silent.
_LOAD_WINDOW = """
{%- assign lwe = rows[0]['load_window_end'].value -%}
{%- assign wend = rows[0]['week_end'].value -%}
{%- if lwe -%}<br>Measured to {{ lwe | escape }}
{%- if wend and wend != lwe %}; you last trained {{ wend | escape }}.
{%- elsif wend %}, the last day you trained.
{%- else %}.{% endif -%}
{%- endif -%}"""

_LOAD_BODY = """
{%- if rows.size == 0 -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet,
or a filter on this page excludes them &mdash; this card ignores the time picker, but not
the filter bar.</div>
{%- else -%}
{%- assign acwr = rows[0]['acwr'].value -%}
{%- unless acwr -%}
<div class="none">Ramping needs 28 days of load behind it before the ratio means
anything. You have <b>{{ rows.size }}</b> week{% unless rows.size == 1 %}s{% endunless %} logged.</div>
{%- else -%}
{%- assign band = rows[0]['acwr_band'].value -%}
{%- assign cls = "b-normal" -%}{%- assign word = "Holding steady." -%}
{%- if band == "spike" -%}{%- assign cls = "b-max" -%}{%- assign word = "Sharp jump in load." -%}
{%- elsif band == "rising" -%}{%- assign cls = "b-heavy" -%}{%- assign word = "Ramping." -%}
{%- elsif band == "undertrained" -%}{%- assign cls = "b-light" -%}{%- assign word = "Backing off." -%}{%- endif -%}
{%- comment -%} A ratio off a layoff is arithmetic, not a spike. Three blank weeks make
chronic equal acute, so the number is 4.0 before a single hard set is lifted. Calling that
"Sharp jump in load" tells a lifter coming back to do less, which is both wrong and the
opposite of useful. The indexer flags the week; the card refuses to band it. {%- endcomment -%}
{%- assign off = rows[0]['acwr_off_layoff'].value -%}
{%- assign trained = rows[0]['chronic_days_trained'].value | plus: 0 -%}
{%- comment -%} "Only N of the last 28 days" left the bar implicit, and a count presented
as low with nothing to be low AGAINST is a judgment the reader cannot check. The bar is
layoff_min_training_days: it is measured from this lifter's own history rather than being a
constant, it moves as the corpus grows, and it is carried on the row precisely so that the
flag beside it is auditable from the document. It is guarded rather than assumed because an
index written before the field existed still has to render - and because that is what an
absent field means here, not a threshold of zero.

The card does NOT restate how the number is derived. That lives in derive.layoff_min_
training_days next to the constants that produce it, and a copy of it here would drift from
them the way the INOL band words would if this file spelled them out. {%- endcomment -%}
{%- assign lmin = rows[0]['layoff_min_training_days'].value -%}
{%- if off -%}
<div class="verdict b-normal">Coming back.</div>
<div class="ev">Only <b>{{ trained }}</b> of the last 28 days carried load{% if lmin %}, under the <b>{{ lmin }}</b> this ratio needs{% endif %}, so it is
arithmetic rather than a spike. It will mean something again once the four-week base
refills.__WINDOW__</div>
{%- else -%}
<div class="verdict {{ cls }}">{{ word }}</div>
{%- assign pct = acwr | minus: 1 | times: 100 | round -%}
<div class="ev">7-day load
{%- if pct >= 0 %} <b>{{ pct }}%</b> above{% else %}{%- assign under = 0 | minus: pct %} <b>{{ under }}%</b> below{% endif %}
your 4-week average.
{%- assign mono = rows[0]['monotony'].value -%}
{%- if mono %}<br>Monotony {{ mono | round: 2 }}.{% endif %}__WINDOW__</div>
{%- comment -%} Skip the run of weeks already in this band, then take the two most
recent distinct months that were. {%- endcomment -%}
{%- comment -%} `scanned` and `oldest_m` are the reach of this lookup, measured rather
than asserted. The provenance line used to close by naming the month one particular
author's log begins, compiled in as though it were every reader's, and the empty branch
below said "your whole log" - both of them claims about a corpus neither the query nor
the card can see. Q["sig_load"] is LIMIT 200 and the dashboard time picker is ANDed on
top of it, so what this card was handed is a window, and the window is what it now names.
{%- endcomment -%}
{%- assign run = true -%}{%- assign found = 0 -%}{%- assign prev_m = "" -%}{%- assign months = "" -%}
{%- assign scanned = 0 -%}{%- assign oldest_m = "" -%}
{%- for r in rows offset: 1 -%}
  {%- assign b = r['acwr_band'].value -%}
  {%- assign scanned = scanned | plus: 1 -%}
  {%- if r['month_s'].value -%}{%- assign oldest_m = r['month_s'].value -%}{%- endif -%}
  {%- if run and b != band -%}{%- assign run = false -%}{%- endif -%}
  {%- unless run -%}
    {%- if b == band and found < 2 -%}
      {%- assign m = r['month_s'].value -%}
      {%- if m != prev_m -%}
        {%- if months == "" -%}{%- assign months = m -%}
        {%- else -%}{%- assign months = months | append: ", " | append: m -%}{%- endif -%}
        {%- assign prev_m = m -%}{%- assign found = found | plus: 1 -%}
      {%- endif -%}
    {%- endif -%}
  {%- endunless -%}
{%- endfor -%}
<div class="also">
{%- if found == 0 and scanned == 0 -%}No earlier week to compare this one against yet.
{%- elsif found == 0 and oldest_m == "" -%}Nothing else in this band in the <b>{{ scanned }}</b> earlier
week{% unless scanned == 1 %}s{% endunless %} behind this one.
{%- elsif found == 0 -%}Nothing else in this band in the <b>{{ scanned }}</b> earlier
week{% unless scanned == 1 %}s{% endunless %} behind this one, back to <b>{{ oldest_m | escape }}</b>.
{%- elsif found == 1 -%}Last time you were here: <b>{{ months | escape }}</b>.
{%- else -%}The last two times you were here: <b>{{ months | escape }}</b>.{%- endif -%}
</div>
{%- endif -%}
{%- endunless -%}
{%- endif -%}
"""

_LOAD_BODY = _LOAD_BODY.replace("__WINDOW__", _LOAD_WINDOW)

SIGNAL_LOAD = signal(
    "Am I ramping",
    _LOAD_BODY,
    SCOPE_LOAD,
    "See History &#9656; acute vs chronic",
)


# --- 3. drift --------------------------------------------------------------
#
# Muscle groups, not the competition lifts. Squat, bench and deadlift are trained on a
# 10-day cadence or tighter and never drift, so a lift row would always read "fine".
# The neglect is in the accessories: calves at 17 days against a 6-day cadence.

_DRIFT_BODY = """
{%- if rows.size == 0 -%}
{%- comment -%} Not "no working sets": this card reads ironstack-signals, which is written
from the whole log at index time. Zero rows means the log has not been indexed, or a filter
on this page excluded them. The time picker cannot do it - that is what the index is for -
but a KQL query on a field this index does not carry matches nothing and empties the card.
Saying "no working sets in the last year" here would be the same class of lie the whole
signals index exists to remove. {%- endcomment -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet, or a
filter on this page excludes them &mdash; this card ignores the time picker, but not the
filter bar.</div>
{%- else -%}
{%- assign now_s = "now" | date: "%s" | plus: $TZ_OFF -%}
{%- assign flagged = 0 -%}{%- assign ranked = 0 -%}{%- assign groups = 0 -%}
{%- assign f_name = "" -%}{%- assign f_gap = 0 -%}{%- assign f_cad = 0 -%}
{%- for r in rows -%}
  {%- assign n = r['sessions'].value | plus: 0 -%}
  {%- if n > 0 -%}{%- assign groups = groups | plus: 1 -%}{%- endif -%}
  {%- assign cad = r['cadence_days'].value | plus: 0 -%}
  {%- comment -%} cadence is read from the row now, not derived as 365/n, so for the first
  time it can be missing or zero. Unguarded, `divided_by: f_cad` throws and Kibana renders
  the panel blank rather than showing a verdict. A group with no cadence cannot be ranked,
  which is the honest thing to do with it anyway. {%- endcomment -%}
  {%- comment -%} rankable is the indexer's veto and it is only a veto: absent (an index
  written before the field existed) the card falls back to its own test, and present-and-
  true it still has to clear that test, because `divided_by: f_cad` throws on a zero
  cadence no matter who says the group is rankable. {%- endcomment -%}
  {%- assign vetoed = false -%}
  {%- if r['rankable'].value == false -%}{%- assign vetoed = true -%}{%- endif -%}
  {%- if n >= 6 and cad > 0 and vetoed == false -%}
    {%- assign ranked = ranked | plus: 1 -%}
    {%- comment -%} gap is computed here, not at index time. Decided by the indexer it
    would freeze: a card written on Tuesday would still say 17 days on Friday. {%- endcomment -%}
    {%- assign last_s = r['last_trained'].value | date: "%s" | plus: 0 -%}
    {%- assign gap = now_s | minus: last_s | divided_by: 86400 | floor -%}
    {%- assign lim = cad | times: 2 -%}
    {%- if gap > lim -%}
      {%- assign flagged = flagged | plus: 1 -%}
      {%- if f_name == "" -%}
        {%- assign f_name = r['muscle'].value | replace: "-", " " | capitalize -%}
        {%- assign f_gap = gap -%}{%- assign f_cad = cad -%}
      {%- endif -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if ranked == 0 and groups == 0 -%}
{%- comment -%} groups counts rows carrying at least one session, so with `sessions`
absent on every row it is 0 - and the branch below printed "None of your 0 qualify
yet", which counts nothing and denies something in the same sentence. {%- endcomment -%}
<div class="none">No muscle groups came back with any sessions on them. Either the log
has not been indexed yet, or a filter on this page excludes the rows this card reads.</div>
{%- elsif ranked == 0 -%}
<div class="none">A muscle group needs six sessions in the year, far enough apart to
measure, before its normal gap means anything. None of your <b>{{ groups }}</b> qualify yet.</div>
{%- elsif flagged == 0 -%}
<div class="verdict b-normal">Nothing is drifting.</div>
<div class="ev">All <b>{{ ranked }}</b> muscle groups trained inside their normal window.</div>
{%- else -%}
{%- assign ratio = f_gap | times: 10 | divided_by: f_cad | round -%}
{%- assign cls = "b-heavy" -%}{%- if ratio >= 30 -%}{%- assign cls = "b-max" -%}{%- endif -%}
<div class="verdict {{ cls }}">{{ f_name | escape }}: {{ f_gap }} days.</div>
<div class="ev">Normally every <b>{{ f_cad | round }}</b> days.</div>
{%- assign scale = f_cad | times: 3 -%}
{%- assign w = f_gap | times: 100 | divided_by: scale | round -%}
{%- if w > 100 -%}{%- assign w = 100 -%}{%- endif -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:33%"></u></div>
<div class="base">tick marks your normal gap</div>
{%- if flagged > 1 -%}
<div class="also">
{%- assign shown = 0 -%}
{%- for r in rows -%}
  {%- assign n = r['sessions'].value | plus: 0 -%}
  {%- assign cad = r['cadence_days'].value | plus: 0 -%}
  {%- assign vetoed = false -%}
  {%- if r['rankable'].value == false -%}{%- assign vetoed = true -%}{%- endif -%}
  {%- if n >= 6 and cad > 0 and shown < 2 and vetoed == false -%}
    {%- assign last_s = r['last_trained'].value | date: "%s" | plus: 0 -%}
    {%- assign gap = now_s | minus: last_s | divided_by: 86400 | floor -%}
    {%- assign lim = cad | times: 2 -%}
    {%- assign nm = r['muscle'].value | replace: "-", " " | capitalize -%}
    {%- if gap > lim and nm != f_name -%}
      {%- assign shown = shown | plus: 1 -%}
      {{ nm | escape }} {{ gap }}d &middot; every {{ cad | round }}<br>
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- endif -%}
"""


SIGNAL_DRIFT = signal(
    "What am I neglecting",
    _DRIFT_BODY,
    SCOPE_DRIFT,
    "See Session &#9656; every set",
)


# The method behind the three cards above, in one panel at the foot of the page.
#
# Laid out in three columns on a 48-column panel so each one sits under the card it
# explains. That is the whole reason it is one panel and not three: read side by side,
# the three windows are visibly different - 13 weeks, 28 days, 365 days - which is the
# fact that makes two cards ranking the same week differently comprehensible instead of
# alarming. Split across three panels nobody would ever compare them.
#
# No query, so no Liquid runs here (see custom()): this is plain text and must stay
# plain text. It carries no number, which is also why it can be - every figure on this
# page is computed from the reader's own log by the cards above.
SIGNAL_METHOD = page(tok("""<style>
.mth{font-family:$MONO;font-size:11px;line-height:1.65;color:$DIM}
.mth .hd{font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:$STEEL;margin-bottom:12px}
.mth .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:22px}
.mth .q{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:$BLOOD;margin-bottom:6px}
.mth p{margin:0}
</style>
<div class="mth">
<div class="hd">How the three verdicts above are measured</div>
<div class="cols">
<div><div class="q">How heavy was this week</div><p>__M_INTENSITY__</p></div>
<div><div class="q">Am I ramping</div><p>__M_LOAD__</p></div>
<div><div class="q">What am I neglecting</div><p>__M_DRIFT__</p></div>
</div>
</div>""".replace("__M_INTENSITY__", METHOD_INTENSITY)
     .replace("__M_LOAD__", METHOD_LOAD)
     .replace("__M_DRIFT__", METHOD_DRIFT)))


# --- 4. lift trajectory (Lift page) ----------------------------------------
#
# "Is this lift going up" cannot be answered session to session. A confident e1RM is
# taken from whatever the day's top working set happened to be, so across 20 deadlift
# sessions it swings 243 to 383 — that is how hard the day was, not how strong the
# lifter is. Ranking one session against recent ones would flip the verdict weekly.
#
# So: best of the last five sessions against the best in the page's range. Both ends
# are a max, so a light day cannot drag either one, and the gap is a real statement
# about where the lift sits.

_LIFT_BODY = """
{%- if rows.size == 0 -%}
<div class="none">No confident estimates for this lift yet.</div>
{%- else -%}
{%- comment -%} Which lift this page is on, and whether it is on one at all. This query
returns every lift the log has; a lift_slug filter on the dashboard is what cuts it to
one. With no filter the rows carry several slugs, and the card used to silently follow
whichever one the most recent session happened to use - a verdict about deadlifts under
a page of everything. Counting the distinct slugs is how the panel knows, since Liquid
cannot see the filter bar. {%- endcomment -%}
{%- assign slug = rows[0]['lift_slug'].value -%}
{%- assign seen_slugs = "" -%}{%- assign slugs_seen = 0 -%}
{%- for r in rows -%}
{%- assign _sl = r['lift_slug'].value | append: "|" -%}
{%- unless seen_slugs contains _sl -%}
{%- assign seen_slugs = seen_slugs | append: _sl -%}
{%- assign slugs_seen = slugs_seen | plus: 1 -%}
{%- endunless -%}
{%- endfor -%}
{%- if slugs_seen > 1 -%}
<div class="verdict b-light">No lift chosen.</div>
<div class="ev">This page ranks ONE lift against its own history, and
<b>{{ slugs_seen }}</b> came back &mdash; so nothing here is filtered to a lift yet.</div>
<div class="none">Click a lift in Overview's projected-total chart, or a point on this page's e1RM line,
and this card rules on that lift.</div>
{%- else -%}
{%- assign n = 0 -%}{%- assign recent = 0 -%}{%- assign prev = 0 -%}
{%- assign peak = 0 -%}{%- assign peak_s = "" -%}
{%- for r in rows -%}
  {%- if r['lift_slug'].value == slug -%}
    {%- assign v = r['e1'].value | plus: 0 -%}
    {%- if v > 0 -%}
      {%- assign n = n | plus: 1 -%}
      {%- if n <= 5 -%}
        {%- if v > recent -%}{%- assign recent = v -%}{%- endif -%}
      {%- elsif n <= 10 -%}
        {%- if v > prev -%}{%- assign prev = v -%}{%- endif -%}
      {%- endif -%}
      {%- if v > peak -%}{%- assign peak = v -%}{%- assign peak_s = r['when_s'].value -%}{%- endif -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if n < 5 -%}
<div class="none">Placing a lift needs 5 sessions carrying a confident estimate.
You have <b>{{ n }}</b> in this range.</div>
{%- else -%}
{%- assign gap = peak | minus: recent | times: 100 | divided_by: peak | round -%}
{%- assign cls = "b-light" -%}
{%- if gap <= 2 -%}{%- assign cls = "b-max" -%}
{%- elsif gap <= 8 -%}{%- assign cls = "b-heavy" -%}
{%- elsif gap <= 15 -%}{%- assign cls = "b-normal" -%}{%- endif -%}
<div class="verdict {{ cls }}">
{%- if gap <= 2 -%}At your best.
{%- elsif gap <= 8 -%}Close to your best.
{%- else -%}{{ gap }}% under your best.{%- endif -%}
</div>
<div class="ev">Recent best <b>{{ recent | round }}</b> $U_WEIGHT &middot;
your best <b>{{ peak | round }}</b> $U_WEIGHT, {{ peak_s | escape }}.</div>
{%- if peak > 0 -%}
{%- assign w = recent | times: 100 | divided_by: peak | round -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:100%"></u></div>
<div class="base">tick marks your best</div>
{%- endif -%}
{%- if prev > 0 -%}
{%- assign dif = recent | minus: prev -%}{%- assign dir = "Up" -%}
{%- if dif < 0 -%}{%- assign dif = 0 | minus: dif -%}{%- assign dir = "Down" -%}{%- endif -%}
{%- assign dpct = dif | times: 100 | divided_by: prev | round -%}
<div class="also">
{%- if dpct == 0 -%}Level with the five sessions before.
{%- else -%}{{ dir }} <b>{{ dpct }}%</b> on the five sessions before.{%- endif -%}
</div>
{%- endif -%}
{%- endif -%}
{%- endif -%}
{%- endif -%}
"""

SIGNAL_LIFT = signal(
    "Where is this lift",
    _LIFT_BODY,
    "Confident e1RM estimates on working sets, for the lift you arrived on. One "
    "session's estimate swings with how hard that day was, so this compares your best of "
    "five sessions, never one session to the next.",
    "Below &#9656; every working set",
)


# --- 5. taper (Meets page) --------------------------------------------------
#
# The one comparison the phone cannot make: this cycle's run-in laid over the same
# weeks before every meet already on the record.
#
# Volume, not intensity, carries the verdict. Both meets on record are one data
# point each, but the volume gap between them is large and one-directional - the
# nine-for-nine cycle moved 38% more weight at a LOWER average RPE - while their
# peak relative intensities are close enough to be noise. So the card ranks the
# thing that separates them and says out loud, in the provenance, that two meets
# is a comparison rather than a rule.
#
# Alignment is by ISO week, because workout-weekly is what every other weekly
# number in this app is built from and a second definition of "a week" here would
# drift from it. The Sept 4 analysis counted back in seven-day blocks from the meet
# date instead; the per-week figures differ, the eight-week totals are identical
# (552,178 lb for Nov 2024 either way), and that is the whole of the difference.

def _taper_body() -> str:
    raw = """
{%- if rows.size == 0 -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet,
or a filter on this page excludes them &mdash;
this card ignores the time picker, but not the filter bar.</div>
{%- else -%}
{%- comment -%} The cycle being trained for, and how far into its run-in it is. Rows
arrive weeks_out descending inside a cycle, so the last closed week seen is the most
recent one; the week in progress always has the smallest weeks_out and is read on its
own, never folded into a total. {%- endcomment -%}
{%- assign cur = "" -%}{%- assign cur_label = "" -%}
{%- assign cur_n = 0 -%}{%- assign cur_k = 0 -%}
{%- comment -%} cum_weeks is now ABSENT, not zero, on a cycle with no closed week inside
its run-in, and `nil | plus: 0` is 0 - so presence is carried in its own flag. Without
that the card cannot tell "no closed weeks" from "the field did not arrive", and the two
want opposite sentences. {%- endcomment -%}
{%- assign cur_closed = false -%}{%- assign cur_has = false -%}
{%- assign cur_ton = 0 -%}{%- assign cur_heavy = 0 -%}
{%- assign open_n = 0 -%}{%- assign open_ton = 0 -%}{%- assign open_days = 0 -%}{%- assign open_rpe = 0 -%}
{%- for r in rows -%}
  {%- if r['cycle_role'].value == "current" -%}
    {%- assign cur = r['cycle'].value -%}
    {%- assign cur_label = r['cycle_label'].value -%}
    {%- if r['week_state'].value == "in-progress" -%}
      {%- assign open_n = r['weeks_out'].value | plus: 0 -%}
      {%- assign open_ton = r['tonnage_lb'].value | plus: 0 -%}
      {%- assign open_days = r['training_days'].value | plus: 0 -%}
      {%- assign open_rpe = r['avg_working_rpe'].value | plus: 0 -%}
    {%- else -%}
      {%- assign cur_closed = true -%}
      {%- assign cur_n = r['weeks_out'].value | plus: 0 -%}
      {%- if r['cum_weeks'].value -%}
        {%- assign cur_has = true -%}
        {%- assign cur_k = r['cum_weeks'].value | plus: 0 -%}
      {%- else -%}
        {%- assign cur_has = false -%}{%- assign cur_k = 0 -%}
      {%- endif -%}
      {%- assign cur_ton = r['cum_tonnage_lb'].value | plus: 0 -%}
      {%- assign cur_heavy = r['cum_heavy'].value | plus: 0 -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if cur == "" -%}
<div class="none">No meet on the calendar. Set <b>meet_date</b> in the program block and
this card starts measuring the run-in to it.</div>
{%- else -%}
{%- comment -%} The yardstick: the meet on record with the best attempt count, most
recent on a tie. Two passes rather than promote-and-demote, which Liquid cannot express
without more carried state than one card should own. {%- endcomment -%}
{%- assign best = 0 -%}
{%- for r in rows -%}
  {%- if r['cycle_role'].value == "past" -%}
    {%- assign tot = r['attempts_total'].value | plus: 0 -%}
    {%- if tot > 0 -%}
      {%- assign sc = r['attempts_made'].value | times: 100 | divided_by: tot -%}
      {%- if sc > best -%}{%- assign best = sc -%}{%- endif -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- assign ref = "" -%}{%- assign ref_label = "" -%}
{%- assign ref_made = 0 -%}{%- assign ref_tot = 0 -%}
{%- for r in rows -%}
  {%- if ref == "" and r['cycle_role'].value == "past" -%}
    {%- assign tot = r['attempts_total'].value | plus: 0 -%}
    {%- if tot > 0 -%}
      {%- assign sc = r['attempts_made'].value | times: 100 | divided_by: tot -%}
      {%- if sc == best -%}
        {%- assign ref = r['cycle'].value -%}
        {%- assign ref_label = r['cycle_label'].value -%}
        {%- assign ref_made = r['attempts_made'].value | plus: 0 -%}
        {%- assign ref_tot = tot -%}
      {%- endif -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- comment -%} Its matching stretch. weeks_out aligns by distance to the meet; cum_weeks
has to match as well, because a cycle whose run-in predates the log carries fewer closed
weeks at the same distance, and its total would read low for that reason alone rather
than because the lifter did less. {%- endcomment -%}
{%- assign ref_ton = 0 -%}{%- assign ref_heavy = 0 -%}
{%- assign ref_k = 0 -%}{%- assign ref_has = false -%}
{%- assign ref_week = 0 -%}{%- assign ref_wk_days = 0 -%}{%- assign ref_wk_rpe = 0 -%}
{%- for r in rows -%}
  {%- if r['cycle'].value == ref -%}
    {%- assign wo = r['weeks_out'].value | plus: 0 -%}
    {%- if wo == cur_n -%}
      {%- if r['cum_weeks'].value -%}
        {%- assign ref_has = true -%}
        {%- assign ref_k = r['cum_weeks'].value | plus: 0 -%}
      {%- endif -%}
      {%- comment -%} The current cycle's cumulative window was widened at index time, so
      two rows at the same weeks_out can cover a different number of closed weeks. Dividing
      across that mismatch produced 466% where the old structural zero produced 0%; both
      numbers describe the calendar, not the lifter. Compare only on an exact match.
      {%- endcomment -%}
      {%- if cur_has and ref_has and ref_k == cur_k -%}
        {%- assign ref_ton = r['cum_tonnage_lb'].value | plus: 0 -%}
        {%- assign ref_heavy = r['cum_heavy'].value | plus: 0 -%}
      {%- endif -%}
    {%- endif -%}
    {%- if cur_closed == false and wo == open_n -%}
      {%- assign ref_week = r['tonnage_lb'].value | plus: 0 -%}
      {%- assign ref_wk_days = r['training_days'].value | plus: 0 -%}
      {%- assign ref_wk_rpe = r['avg_working_rpe'].value | plus: 0 -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if cur_closed == false -%}
{%- comment -%} The run-in has opened but no week of it has closed. Ruling here would
compare a Wednesday against a finished week and print a collapse in volume that is only
a calendar artefact. {%- endcomment -%}
{%- comment -%} This branch used to print the open week's TOTAL beside the reference
week's total and then say nothing is ranked: four days of an open week next to a finished
three-day one, under a sentence declining to compare them. Every reader divides, and the
division they do is the wrong one - a partial week against a finished one. The same
correction the intensity card already makes is available here: an open week is only
comparable per training day, so both sides are put on that footing and the card says so.
The refusal to rank stays, because a rate off two or three days is still thin; what goes
is the invitation to rank it yourself off the wrong pair of numbers. {%- endcomment -%}
{%- assign open_rate = 0 -%}
{%- if open_days > 0 -%}{%- assign open_rate = open_ton | divided_by: open_days -%}{%- endif -%}
{%- assign ref_rate = 0 -%}
{%- if ref_wk_days > 0 -%}{%- assign ref_rate = ref_week | divided_by: ref_wk_days -%}{%- endif -%}
<div class="verdict b-light">Week {{ open_n }} of the run-in, still open.</div>
<div class="ev"><b>__OPEN_DAYS__</b>&nbsp;training day{% if open_days != 1 %}s{% endif %} in,
{%- if open_rate > 0 %} <b>__OPEN_RATE__</b>&nbsp;$U_WEIGHT a day{% else %} <b>__OPEN_TON__</b>&nbsp;$U_WEIGHT{% endif -%}
{%- if open_rpe > 0 %} at RPE __OPEN_RPE__{% endif -%}.
{%- if ref_rate > 0 %} {{ ref_label | escape }}'s same week ran <b>__REF_RATE__</b>&nbsp;$U_WEIGHT a day
across {{ ref_wk_days }} day{% if ref_wk_days != 1 %}s{% endif %}{% if ref_wk_rpe > 0 %} at RPE __REF_WK_RPE__{% endif %}.{% endif -%}
</div>
<div class="base">a day rate, because a part week and a finished one are not comparable on the
total &mdash; nothing is ranked until the week closes</div>
{%- elsif ref_ton > 0 -%}
{%- assign pct = cur_ton | times: 100 | divided_by: ref_ton | round -%}
{%- assign cls = "b-heavy" -%}
{%- if pct >= 90 and pct <= 110 -%}{%- assign cls = "b-normal" -%}{%- endif -%}
{%- if pct < 70 or pct > 130 -%}{%- assign cls = "b-max" -%}{%- endif -%}
<div class="verdict {{ cls }}">{{ pct }}% of {{ ref_label | escape }}'s volume.</div>
<div class="ev">Through week <b>{{ cur_n }}</b> out,
<b>{{ cur_k }}</b> closed week{% if cur_k != 1 %}s{% endif %} of the run-in:
<b>__CUR_TON__</b>&nbsp;$U_WEIGHT.
{{ ref_label | escape }}, {{ ref_made }} for {{ ref_tot }},
had moved <b>__REF_TON__</b>&nbsp;$U_WEIGHT by the same point.</div>
{%- comment -%} The bar runs to 150% of the yardstick so being ahead of it is visible
rather than pinned at full width, and the tick sits where the yardstick is. {%- endcomment -%}
{%- assign w = pct | times: 100 | divided_by: 150 -%}
{%- if w > 100 -%}{%- assign w = 100 -%}{%- endif -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:66%"></u></div>
<div class="base">tick marks {{ ref_label | escape }}'s pace</div>
{%- if cur_heavy > 0 or ref_heavy > 0 -%}
<div class="also">reps at 80%+ &middot; you {{ cur_heavy }} &middot; {{ ref_label | escape }} {{ ref_heavy }}</div>
{%- endif -%}
{%- elsif ref == "" -%}
<div class="none">No meet on record yet to measure the run-in to {{ cur_label | escape }} against.
The comparison starts with your second meet.</div>
{%- else -%}
<div class="none">Through week <b>{{ cur_n }}</b> out this run-in has
{%- if cur_has %} <b>{{ cur_k }}</b> closed week{% if cur_k != 1 %}s{% endif %} behind it
{%- else %} no closed week behind it yet{% endif %}, and {{ ref_label | escape }} has
{%- if ref_has %} <b>{{ ref_k }}</b> at the same distance{% else %} none recorded at that distance{% endif %}.
Two run-ins only compare across the same number of closed weeks, so this one waits for
them to line up.</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__OPEN_DAYS__", "{{ open_days }}")
            .replace("__OPEN_TON__", num("open_ton"))
            .replace("__OPEN_RATE__", num("open_rate"))
            .replace("__REF_RATE__", num("ref_rate"))
            .replace("__OPEN_RPE__", "{{ open_rpe | round: 1 }}")
            .replace("__REF_WEEK__", num("ref_week"))
            .replace("__REF_WK_RPE__", "{{ ref_wk_rpe | round: 1 }}")
            .replace("__CUR_TON__", num("cur_ton"))
            .replace("__REF_TON__", num("ref_ton")))


_TAPER_BODY = _taper_body()


SIGNAL_TAPER = signal(
    "Am I running this in like the last one",
    _TAPER_BODY,
    "Weekly tonnage aligned by ISO week to each meet date. The yardstick is the meet "
    "with the best attempt record, counted only where it has the same number of closed "
    "weeks behind it. Two meets is a comparison, not a rule &mdash; tonnage moves with "
    "exercise selection as much as with effort.",
    "See Program &#9656; the weeks behind this",
)


# --- 6. program: this week's loading, in words ------------------------------
#
# The defect this fixes, named in the Sept 5 switcher review: "Weekly loading is the
# only differentiated content on the page, and it is a table of unlabelled decimals.
# INOL 1.2 means nothing to someone who has not read Prilepin."
#
# So the band and its sentence both come off the row. They are written once, in
# metrics.INOL_WEEK_BANDS, next to the thresholds that produce them - restating them
# here would let the words drift from the numbers they describe.

def _program_body() -> str:
    raw = """
{%- if rows.size == 0 -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet,
or a filter on this page excludes them &mdash;
this card ignores the time picker, but not the filter bar.</div>
{%- else -%}
{%- assign w = rows[0] -%}
{%- assign inol = w['inol_hardest'].value | plus: 0 -%}
{%- assign band = w['inol_hardest_band'].value -%}
{%- if band == nil or inol == 0 -%}
<div class="none">No main-lift work with a measurable intensity this week, so there is
no loading index to band. INOL needs a working set on a lift with history behind it.</div>
{%- else -%}
{%- assign cls = "b-light" -%}
{%- if band == "loading" -%}{%- assign cls = "b-normal" -%}{%- endif -%}
{%- if band == "brutal" -%}{%- assign cls = "b-heavy" -%}{%- endif -%}
{%- if band == "excessive" -%}{%- assign cls = "b-max" -%}{%- endif -%}
{%- comment -%} Rank against the lifter's own recent weeks, so the band is not the only
thing the card knows. Twelve weeks is the window the intensity card already uses.
{%- endcomment -%}
{%- assign harder = 0 -%}{%- assign seen = 0 -%}
{%- for r in rows offset: 1 limit: 12 -%}
  {%- assign v = r['inol_hardest'].value | plus: 0 -%}
  {%- if v > 0 -%}
    {%- assign seen = seen | plus: 1 -%}
    {%- if v > inol -%}{%- assign harder = harder | plus: 1 -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
<div class="verdict {{ cls }}">{{ band | capitalize | escape }}.</div>
<div class="ev"><b>{{ w['inol_hardest_lift'].value | escape }}</b> is the hardest lift of the week
at INOL __INOL__{% if w['inol_hardest_gloss'].value %} &mdash; {{ w['inol_hardest_gloss'].value | escape }}{% endif %}.
{%- if seen > 0 %} More work on that lift than <b>{{ seen | minus: harder }}</b> of your last {{ seen }} weeks.{% endif -%}
</div>
{%- assign acwr = w['acwr'].value | plus: 0 -%}
{%- if acwr > 0 -%}
<div class="also">load {{ w['acwr_band'].value | escape }} at __ACWR__{% if w['acwr_gloss'].value %} &middot; {{ w['acwr_gloss'].value | escape }}{% endif %}</div>
{%- endif -%}
<div class="base">last trained {{ w['week_end'].value | escape }}{% if w['block'].value %} &middot; {{ w['block'].value | escape }} block{% endif %}</div>
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__INOL__", "{{ inol | round: 2 }}")
            .replace("__ACWR__", "{{ acwr | round: 2 }}"))


_PROGRAM_BODY = _program_body()


SIGNAL_PROGRAM = signal(
    "How hard is this week loading",
    _PROGRAM_BODY,
    "INOL is reps divided by (100 minus intensity), per lift; the hardest single lift is "
    "the one worth banding. Easy is under 2, loading to 3, brutal to 4, excessive above. "
    "Overview ranks the same week on weight, not work, and both are true.",
    "See the weekly loading table below &middot; Overview ranks the same week on weight",
)


# --- 7. block intensity (History page) --------------------------------------
#
# `program.block` is a block TYPE and not an instance - "strength" spans 2023 to 2026
# across nine separate runs - so the comparison is against previous runs with the SAME
# name. Against a hypertrophy block a strength block wins on heavy work by construction,
# and a verdict that is true by definition is not a verdict.
#
# The rate is ranked, not the share: the current block carries 67 main-lift reps and a
# share off that denominator moves 1.5 points on one set. The share is still shown, with
# its denominator visible, which is the same bargain the intensity card struck on weeks.

def _block_body() -> str:
    raw = """
{%- if rows.size == 0 -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet,
or a filter on this page excludes them &mdash;
this card ignores the time picker, but not the filter bar.</div>
{%- else -%}
{%- assign cur = nil -%}
{%- for r in rows -%}
  {%- if r['block_role'].value == "current" -%}{%- assign cur = r -%}{%- endif -%}
{%- endfor -%}
{%- if cur == nil -%}
<div class="none">No block in progress. Every session carries a program block; this card
starts once one of them is the most recent.</div>
{%- else -%}
{%- assign name = cur['block'].value -%}
{%- assign peers = cur['peers'].value | plus: 0 -%}
{%- assign mine = cur['heavy_per_session'].value | plus: 0 -%}
{%- assign theirs = cur['peer_heavy_per_session'].value | plus: 0 -%}
{%- comment -%} The peer median is taken over each earlier block's FIRST N sessions,
N being this block's length, so a six-session block is not measured against the whole of
a fifty-session one. The card has to say which N, or the number reads as a full-block
median it no longer is. {%- endcomment -%}
{%- assign win = cur['peer_window_sessions'].value | plus: 0 -%}
{%- if peers == 0 or theirs == 0 -%}
<div class="verdict b-light">Your first {{ name | escape }} block.</div>
<div class="ev"><b>__MINE__</b> heavy reps a session across <b>{{ cur['sessions'].value }}</b>
sessions &mdash; <b>{{ cur['heavy'].value }}</b> of <b>{{ cur['main_reps'].value }}</b>
main-lift reps at 80% or more. There is nothing of the same kind to rank it against yet.</div>
{%- else -%}
{%- assign pct = mine | times: 100 | divided_by: theirs | round -%}
{%- assign cls = "b-heavy" -%}
{%- if pct >= 90 and pct <= 110 -%}{%- assign cls = "b-normal" -%}{%- endif -%}
{%- if pct < 70 or pct > 130 -%}{%- assign cls = "b-max" -%}{%- endif -%}
<div class="verdict {{ cls }}">{{ pct }}% of the heavy work in a usual {{ name | escape }} block.</div>
<div class="ev"><b>__MINE__</b> heavy reps a session this block,
against a median of <b>__THEIRS__</b> across{% if win > 0 %} the first {{ win }} session{% if win != 1 %}s{% endif %} of{% endif %} your {{ peers }} earlier {{ name | escape }} blocks.
That is <b>{{ cur['heavy'].value }}</b> of <b>{{ cur['main_reps'].value }}</b> main-lift reps
at 80% or more,{% if cur['peer_share_pct'].value %} against __PSHARE__% then{% else %} against a share those blocks did not record{% endif %}.</div>
{%- assign w = pct | times: 100 | divided_by: 150 -%}
{%- if w > 100 -%}{%- assign w = 100 -%}{%- endif -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:66%"></u></div>
<div class="base">tick marks your usual {{ name | escape }} block</div>
{%- endif -%}
<div class="base">this block began {{ cur['first_trained'].value | escape }}{% if peers > 0 %}, the comparison reaches back to {{ cur['peer_from'].value | escape }}{% endif %}</div>
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__MINE__", "{{ mine | round: 2 }}")
            .replace("__THEIRS__", "{{ theirs | round: 2 }}")
            .replace("__PSHARE__", numr("cur['peer_share_pct'].value", 1)))


_BLOCK_BODY = _block_body()


SIGNAL_BLOCK = signal(
    "How heavy is this block",
    _BLOCK_BODY,
    "Heavy is 80% or more of your best estimate in the trailing 90 days, main lifts only. "
    "A block is compared only against earlier runs of the same kind, each measured over as "
    "many sessions as this one has run. Runs under 4 sessions are not ranked.",
    "See the zone chart below for the shape of it",
)


# --- 8. projection calibration (Meets page) ---------------------------------
#
# The projected total is the best card below the fold on Overview and it has never been
# checked against what actually happened. Twice now the lifter has walked onto a platform
# carrying one of these numbers, and both times the platform total came in under it. That
# gap is the most useful thing the meet record can say about the number on the other page.

def _projection_body() -> str:
    raw = """
{%- if rows.size == 0 -%}
<div class="none">No signal rows came back. Either the log has not been indexed yet,
or a filter on this page excludes them &mdash;
this card ignores the time picker, but not the filter bar.</div>
{%- else -%}
{%- assign now = nil -%}
{%- for r in rows -%}
  {%- if r['cycle_role'].value == "current" -%}{%- assign now = r -%}{%- endif -%}
{%- endfor -%}
{%- if now == nil -%}
<div class="none">No projection yet. It needs a recent estimate on the lifts you
compete in &mdash; the ones marked as competition lifts in your exercise list.</div>
{%- else -%}
{%- assign peers = now['peers'].value | plus: 0 -%}
{%- comment -%} A sport scored on points per event has no total, so this card has no
question to ask: it cannot tell you what your projected total has been worth on the
platform, because neither half of that sentence exists. Saying so, and naming the card
that DOES have an answer, beats printing a percentage of nothing. The scoring comes off
the meet record - the next meet on the calendar if there is one, the last one otherwise.
{%- endcomment -%}
{%- if now['scoring'].value == "points" -%}
<div class="verdict b-light">Scored on points, so there is no total to project.</div>
<div class="ev">Your {{ now['discipline'].value | default: "next meet" | escape }} is
ranked event by event and the placings are added, not the weights. A projected total
would be a number no scoring table recognises, so this card does not compute one.
Readiness on this record is per event.</div>
<div class="base">see Overview &#9656; event readiness</div>
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- else -%}
{%- comment -%} peer_pct and expected_lb are absent, not zero, under three peer meets:
a ratio off one or two of them is whichever day went best, not a calibration. The card
has to tell those two silences apart - no meet has a projection behind it at all, versus
some do but not enough of them - because they are different things to be waiting for.
{%- endcomment -%}
{%- assign ratio = now['peer_pct'].value | plus: 0 -%}
{%- if ratio == 0 -%}
<div class="verdict b-light">__NOW__&nbsp;$U_WEIGHT projected.</div>
{%- if peers == 0 -%}
<div class="ev">No meet on record has a projection behind it yet, so there is nothing to
say about what this number has been worth on the platform.</div>
{%- else -%}
<div class="ev">Only <b>{{ peers }}</b> meet{% if peers != 1 %}s{% endif %} on record
{% if peers == 1 %}carries{% else %}carry{% endif %} a projection behind
{% if peers == 1 %}it{% else %}them{% endif %}. Calibrating this number against the
platform needs three, or the ratio is just whichever day went best.</div>
{%- endif -%}
{%- else -%}
<div class="verdict b-normal">{{ ratio | round }}% of projection, across {{ peers }} meets.</div>
<div class="ev">
{%- for r in rows -%}
  {%- if r['cycle_role'].value == "past" -%}
{%- if r['projected_total_lb'].value and r['meet_total_lb'].value -%}
{{ r['cycle_label'].value | escape }} projected <b>__P_PROJ__</b> and you totalled <b>__P_MEET__</b>.&#32;
{%- endif -%}
  {%- endif -%}
{%- endfor -%}
It reads <b>__NOW__</b>&nbsp;$U_WEIGHT today, which puts a realistic platform total near
<b>__EXPECTED__</b>&nbsp;$U_WEIGHT.</div>
<div class="base">a projection is a training estimate;
the platform is singles at a commanded pace</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- endif -%}
{%- endif -%}
"""
    return (raw
            .replace("__P_PROJ__", numr("r['projected_total_lb'].value"))
            .replace("__P_MEET__", numr("r['meet_total_lb'].value"))
            .replace("__NOW__", numr("now['projected_total_lb'].value"))
            .replace("__EXPECTED__", numr("now['expected_lb'].value")))


_PROJECTION_BODY = _projection_body()


SIGNAL_PROJECTION = signal(
    "What is this projection worth",
    _PROJECTION_BODY,
    "The sum of your best estimate on each competition lift inside a 90-day window, "
    "where the sport adds them up. For each meet on record it is the projection as it "
    "stood walking in, not one computed afterwards. Under three meets it declines to rank.",
    "See Overview &#9656; projected total",
)


# --- 9. tags over time (Mindset page) ---------------------------------------
#
# The review asked for "you have written 'grip' five times in two weeks". The log will not
# support that sentence yet: notes begin 2026-09-01 and there are 31 of them across four
# days, so the top tag by count is whatever was written this week. Ranking that would be
# the confident-empty verdict the whole signals index exists to prevent.
#
# So the card carries the corpus span on every row and refuses to rank until the span is
# wide enough, reporting what it has in the meantime. Nothing needs rebuilding when the
# notes accumulate - the card turns itself on.

MIN_TAG_SPAN_DAYS = 21


def _tag_body() -> str:
    raw = """
{%- if rows.size == 0 -%}
<div class="none">No tagged notes came back. Either none have been written yet &mdash;
tags go in the log beside a note, and this card starts reading them back once there are a
few weeks of them &mdash; or a filter on this page excludes them. This card ignores the
time picker, but not the filter bar.</div>
{%- else -%}
{%- assign span = rows[0]['notes_span_days'].value | plus: 0 -%}
{%- assign total = rows[0]['notes_total'].value | plus: 0 -%}
{%- assign win = rows[0]['window_days'].value | plus: 0 -%}
{%- if total == 0 -%}
{%- comment -%} notes_total and notes_span_days are denormalised onto every tag row, so
with rows in hand they are always there - unless the query stopped projecting them, which
is the shape this card has to survive. `nil | plus: 0` is 0, and the thin-corpus branch
below then asserted "0 of them across 0 days" beside a date that rendered as nothing: a
measurement of a corpus the card could not see. {%- endcomment -%}
<div class="none">Tag counts came back without the note corpus behind them, so there is
nothing to say yet about how long you have been writing.</div>
{%- elsif span < __MIN_SPAN__ -%}
<div class="verdict b-light">Too new to read a pattern.</div>
<div class="ev">Your notes begin <b>{{ rows[0]['notes_from'].value | escape }}</b> &mdash;
<b>{{ total }}</b> of them across <b>{{ span }}</b> days. A tag needs about
{{ __MIN_SPAN__ }} days behind it before "more than usual" means anything.</div>
{%- comment -%} The rows arrive ranked by `recent` and this line printed `total`, so
the order and the numbers were two different quantities sitting next to each other: the
card led with the tag written most in the window and labelled it with a whole-log count,
which put its second place somewhere the chart below it never puts anything. One
quantity, named. {%- endcomment -%}
<div class="also">
{%- for r in rows limit: 3 -%}
{{ r['tag'].value | escape }} {{ r['recent'].value }}{% unless forloop.last %} &middot; {% endunless %}
{%- endfor -%}
<span class="faint"> &middot; in the last {{ win }} days</span>
</div>
{%- else -%}
{%- assign t = rows[0] -%}
{%- assign n = t['recent'].value | plus: 0 -%}
{%- if n == 0 -%}
<div class="verdict b-light">Nothing written in the last {{ win }} days.</div>
<div class="ev">The log has <b>{{ total }}</b> tagged notes, most recently
{{ t['last_trained'].value | escape }}.</div>
{%- else -%}
{%- assign before = t['prior'].value | plus: 0 -%}
<div class="verdict b-normal">
You have written &ldquo;{{ t['tag'].value | escape }}&rdquo; {{ n }} time{% if n != 1 %}s{% endif %} in {{ win }} days.</div>
<div class="ev">
{%- if before > 0 -%}Against <b>{{ before }}</b> in the {{ win }} days before that.
{%- else -%}Nothing tagged that way in the {{ win }} days before that.{%- endif -%}
{%- if rows.size > 1 %} Next: {{ rows[1]['tag'].value | escape }} ({{ rows[1]['recent'].value }}).{% endif -%}
</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value | escape }}</div>
{%- endif -%}
"""
    return raw.replace("__MIN_SPAN__", str(MIN_TAG_SPAN_DAYS))


_TAG_BODY = _tag_body()


SIGNAL_TAGS = signal(
    "What do I keep writing down",
    _TAG_BODY,
    "Tags on your own notes, counted over the whole log. A count is not a diagnosis: it "
    "says what you wrote often, not what mattered most. " + coach_or(
        "The question this page cannot answer &mdash; what a note actually said &mdash; "
        "goes to the coach.",
        "The question this page cannot answer &mdash; what a note actually said &mdash; "
        "is not answered anywhere in these dashboards: a count is all a tag can carry."),
    coach_or("Ask the coach to read the notes themselves",
             "See Session &#9656; the notes in full"),
)
