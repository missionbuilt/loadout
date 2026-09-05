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
.chip.miss{color:$FAINT;text-decoration:line-through}
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
.ex{margin-bottom:10px}
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


# --------------------------------------------------------------------------- Liquid helpers

def num(expr: str, dp: int = 0) -> str:
    """Liquid that renders `expr` as a grouped number: 14145 -> 14,145.

    Liquid has no number-format filter, so the digits are grouped by slicing the
    string. Lens formats its own numbers with separators; without this the Liquid
    cards printed raw integers next to them and the digits ran together.
    Handles up to 9 digits, which covers lifetime tonnage. nil renders as nothing.
    """
    r = f" | round: {dp}" if dp else " | round"
    return (
        # The nil guard is load-bearing: `nil | round` is 0, so an unlogged value
        # would print a confident "0". 0 itself is truthy in Liquid and still prints.
        "{%- if " + expr + " -%}"
        "{%- assign _n = " + expr + r + ' | append: "" -%}'
        '{%- assign _q = _n | split: "." -%}'
        "{%- assign _i = _q[0] -%}{%- assign _L = _i | size -%}"
        "{%- if _L > 6 -%}{%- assign _a = _L | minus: 6 -%}"
        "{{ _i | slice: 0, _a }},{{ _i | slice: _a, 3 }},{{ _i | slice: -3, 3 }}"
        "{%- elsif _L > 3 -%}{%- assign _a = _L | minus: 3 -%}"
        "{{ _i | slice: 0, _a }},{{ _i | slice: -3, 3 }}"
        "{%- else -%}{{ _i }}{%- endif -%}"
        "{%- if _q[1] -%}.{{ _q[1] }}{%- endif -%}"
        "{%- endif -%}"
    )


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


# A Liquid snippet that leaves `days` = whole days from now to the meet date in rows[0]['program.meet_date'].
DAYS_TO_MEET = """{% if rows[0]['program.meet_date'].value %}{% assign now_s = "now" | date: "%s" | plus: 0 %}{% assign meet_s = rows[0]['program.meet_date'].value | date: "%s" | plus: 0 %}{% assign days = meet_s | minus: now_s | divided_by: 86400.0 | ceil %}{% endif %}"""



# --------------------------------------------------------------------------- Overview cards

DAYS_TO_MEET_CARD = page(tok("""
<div class="stack">
{% if rows.size == 0 %}<div class="eyebrow">Days to meet</div>""" + empty("No sessions yet") + """{% else %}""" + DAYS_TO_MEET + """
<div><div class="eyebrow">Days to meet</div>
{% if days %}<div class="hero" style="margin-top:8px">{{ days }}</div>{% else %}<div class="empty" style="margin-top:10px">No meet on the calendar</div>{% endif %}</div>
<div class="sub">{{ rows[0]['meet_s'].value }}<br>{{ rows[0]['program.phase'].value }} &middot; week {{ rows[0]['program.week'].value }} &middot; day {{ rows[0]['program.day'].value }} of {{ rows[0]['program.total_days'].value }}<br><span class="faint">last trained {{ rows[0]['date_s'].value }}</span></div>
{% endif %}
</div>"""))

TOTAL_CARD = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Projected total</div>""" + empty() + """{% else %}
{%- assign total = 0 -%}{%- for r in rows -%}{%- assign _v = r['e1'].value | round -%}{%- assign total = total | plus: _v -%}{%- endfor -%}
{%- assign best = rows[0]['e1'].value | plus: 0 -%}
{%- comment -%} The query asks for 90 days and the picker is ANDed on top. At "Last 30
days" the number was 843 under a label still promising 90; the label now reports the
window it actually got. {%- endcomment -%}
{%- assign now_s = "now" | date: "%s" | plus: 0 -%}{%- assign oldest_s = 0 -%}
{%- for r in rows -%}{%- if r['first_d'].value -%}{%- assign fs = r['first_d'].value | date: "%s" | plus: 0 -%}{%- if oldest_s == 0 or fs < oldest_s -%}{%- assign oldest_s = fs -%}{%- endif -%}{%- endif -%}{%- endfor -%}
{%- assign span_d = 90 -%}{%- if oldest_s > 0 -%}{%- assign span_d = now_s | minus: oldest_s | divided_by: 86400 | floor -%}{%- endif -%}
<div class="eyebrow">Projected total</div>
<div class="hero" style="margin-top:7px">""" + num("total") + """<span style="font-size:20px;color:$DIM;margin-left:6px">lb</span></div>
<div class="sub" style="margin-top:3px">{% if span_d < 60 %}best of the last <span class="v">{{ span_d }}</span> days of main-lift work. The card reads 90; widen the time picker for the real number{% else %}best of the last 90 days of main-lift work{% endif %}</div>
<div style="margin-top:12px">
{% for r in rows %}<div class="liftrow"><span class="lname">{{ r['lift'].value }}</span><span class="lval">""" + num("r['e1'].value") + """</span><span class="lbar"><i style="width:{% if best > 0 %}{{ r['e1'].value | times: 100 | divided_by: best | round }}{% else %}0{% endif %}%"></i></span></div>{% endfor %}
</div>
{%- assign pct = total | times: 100 | divided_by: $MEET_MAX_NUM | round -%}{%- assign togo = $MEET_MAX_NUM | minus: total | round -%}
<div class="rule" style="margin-top:12px;padding-top:8px"><span class="sub">{% if total >= $MEET_MAX_NUM %}<span class="v">{{ pct }}%</span> of your meet best, $MEET_MAX lb{% else %}<span class="v">{{ pct }}%</span> of your meet best &middot; <span class="v">""" + num("togo") + """&nbsp;lb</span> to go{% endif %}</span></div>
{% endif %}"""))



WATCH_CARD = page(tok("""
<div class="eyebrow">In your own words</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("Nothing flagged yet") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{{ r['date_s'].value }}</span><span class="txt">{{ r['item'].value }}</span></div>{% endfor %}
</div>{% endif %}"""))


# --------------------------------------------------------------------------- header cards (Program, Session, Lift)

PROGRAM_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Program</div>""" + empty("No sessions in this block") + """{% else %}""" + DAYS_TO_MEET + """
<div class="hdr"><span class="eyebrow">Program</span></div>
<div class="hdr" style="margin-top:8px"><span class="title">{{ rows[0]['program.name'].value }}</span><span class="meta"><b>{{ rows[0]['program.block'].value }}</b> block &middot; <b>{{ rows[0]['program.phase'].value }}</b> phase &middot; week <b>{{ rows[0]['program.week'].value }}</b> &middot; day <b>{{ rows[0]['program.day'].value }}</b> of <b>{{ rows[0]['program.total_days'].value }}</b></span></div>
<div class="sub" style="margin-top:10px">{% if days %}Meet {{ rows[0]['meet_s'].value }} &middot; <span class="v">{{ days }}</span> days out &middot; {% endif %}{{ rows[0]['n'].value }} sessions logged in this block &middot; last trained {{ rows[0]['date_s'].value }}</div>
{% endif %}"""))

SESSION_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Session</div>""" + empty("Open a session from any dashboard") + """{% else %}
<div class="hdr"><span class="eyebrow">Session</span><span class="eyebrow dim">{{ rows[0]['program.name'].value }}</span></div>
<div class="hdr" style="margin-top:8px"><span class="title">{{ rows[0]['program.block'].value }}<span class="dot"></span>week {{ rows[0]['program.week'].value }}<span class="dot"></span>day {{ rows[0]['program.day'].value }} of {{ rows[0]['program.total_days'].value }}</span></div>
<div class="sub" style="margin-top:10px"><span class="v">{{ rows[0]['date_s'].value }}</span>{% if rows[0]['start_time'].value %} &middot; {{ rows[0]['start_time'].value }}{% endif %}{% if rows[0]['time_of_day'].value %} &middot; {{ rows[0]['time_of_day'].value }}{% endif %}{% if rows[0]['location.name'].value %} &middot; {{ rows[0]['location.name'].value }}{% endif %}{% if rows[0]['location.travel'].value %} <span class="chip blood">travel</span>{% endif %}<br>
<span class="faint">prev</span> {{ rows[0]['prev_session_id'].value | default: "none" }} &nbsp; <span class="faint">next</span> {{ rows[0]['next_session_id'].value | default: "none" }} &nbsp; <span class="faint">open them from the panel on the right</span></div>
{% endif %}"""))

SESSION_TILES = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty() + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Tonnage</div><div class="value">""" + num("rows[0]['totals.tonnage_lb'].value") + """<small>lb</small></div></div><div class="sub">moved this session</div></div>
<div class="card"><div class="top"><div class="eyebrow">Length</div>{% if rows[0]['duration_min'].value %}<div class="value">{{ rows[0]['duration_min'].value | round }}<small>min</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div><div class="sub">{{ rows[0]['streak_day'].value }} day streak</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg working RPE</div><div class="value">{{ rows[0]['avg_working_rpe'].value | round: 1 }}</div></div><div class="sub">{{ rows[0]['totals.working_sets'].value }} working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Sets</div><div class="value">{{ rows[0]['totals.sets'].value }}</div></div><div class="sub">{{ rows[0]['totals.reps'].value }} reps &middot; {{ rows[0]['totals.exercises'].value }} lifts</div></div>
{% endif %}
</div>"""))

TOP_SET_HERO = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Top set</div><div style="margin-top:10px">""" + empty("No working sets logged") + """</div>{% else %}
{%- assign sid = rows[0]['session_id'].value -%}{%- assign slug = rows[0]['lift_slug'].value -%}{%- assign tr = rows[0]['reps'].value -%}
{%- assign pw = "" -%}{%- assign pr = "" -%}{%- assign prpe = "" -%}{%- assign pd = "" -%}
{%- assign aw = "" -%}{%- assign ar = "" -%}{%- assign arpe = "" -%}{%- assign ad = "" -%}
{%- for r in rows -%}{%- if r['session_id'].value != sid and r['lift_slug'].value == slug -%}
{%- if pw == "" and r['reps'].value == tr -%}{%- assign pw = r['weight_lb'].value -%}{%- assign pr = r['reps'].value -%}{%- assign prpe = r['rpe'].value -%}{%- assign pd = r['date_s'].value -%}{%- endif -%}
{%- if aw == "" -%}{%- assign aw = r['weight_lb'].value -%}{%- assign ar = r['reps'].value -%}{%- assign arpe = r['rpe'].value -%}{%- assign ad = r['date_s'].value -%}{%- endif -%}
{%- endif -%}{%- endfor -%}
""" + rpe_class("rows[0]['rpe'].value") + """
<div class="eyebrow">Top set</div>
<div style="margin-top:7px;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
<span class="hero">""" + num("rows[0]['weight_lb'].value") + """<span style="font-size:20px;color:$DIM;margin-left:6px">lb</span></span>
<span class="hero" style="font-size:26px;color:$DIM">&times;&nbsp;{{ rows[0]['reps'].value | round }}</span>
{% if rows[0]['rpe'].value %}<span class="set" style="padding:0"><span class="rpe {{ rc }}" style="font-size:21px">@&nbsp;{{ rows[0]['rpe'].value | round: 1 }}</span></span>{% endif %}
</div>
<div class="value" style="font-size:17px;margin-top:7px;white-space:normal">{{ rows[0]['exercise.name'].value }}</div>
<div class="rule" style="margin-top:10px;padding-top:8px">
{% if pw != "" %}{%- assign delta = rows[0]['weight_lb'].value | minus: pw -%}
<span class="sub"><span class="faint">last {{ pr | round }}-rep set</span>&nbsp; <span class="v">""" + num("pw") + """&nbsp;&times;&nbsp;{{ pr | round }}</span>{% if prpe %} <span class="faint">@&nbsp;{{ prpe }}</span>{% endif %} <span class="faint">&middot; {{ pd }}</span></span>
{% if delta > 0 %}<span class="chip blood">+{{ delta | round }} lb</span>{% elsif delta < 0 %}<span class="chip">{{ delta | round }} lb</span>{% else %}<span class="chip">same weight</span>{% endif %}
{% elsif aw != "" %}<span class="sub"><span class="faint">last time</span>&nbsp; <span class="v">""" + num("aw") + """&nbsp;&times;&nbsp;{{ ar | round }}</span>{% if arpe %} <span class="faint">@&nbsp;{{ arpe }}</span>{% endif %} <span class="faint">&middot; {{ ad }}</span> <span class="faint">&mdash; different reps, not compared</span></span>
{% else %}<span class="sub faint">first time on record for this lift</span>{% endif %}</div>
{% endif %}"""))

CONDITIONS_CARD = page(tok("""
<div class="eyebrow">Conditions</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="grid3" style="margin-top:10px">
<div><div class="eyebrow">Temp</div>{% if rows[0]['environment.temp_f'].value %}<div class="value">{{ rows[0]['environment.temp_f'].value | round }}<small>F</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
<div><div class="eyebrow">Humidity</div>{% if rows[0]['environment.humidity_pct'].value %}<div class="value">{{ rows[0]['environment.humidity_pct'].value | round }}<small>%</small></div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
<div><div class="eyebrow">Sky</div>{% if rows[0]['environment.conditions'].value %}<div class="sub" style="margin-top:7px;color:$CHALK;font-size:13px;line-height:1.45">{{ rows[0]['environment.conditions'].value }}</div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
</div>
<div class="sub" style="margin-top:10px">{% if rows[0]['environment.wind'].value %}{{ rows[0]['environment.wind'].value }}{% if rows[0]['environment.setting'].value %} &middot; {% endif %}{% endif %}{{ rows[0]['environment.setting'].value }}</div>
{% endif %}"""))

PERFORMANCE_CARD = page(tok("""
<div class="eyebrow">Performance</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No sets logged") + """</div>{% else %}
{%- assign sid = rows[0]['session_id'].value -%}
{%- assign has_prep = false -%}{%- for r in rows -%}{%- if r['session_id'].value == sid and r['exercise.category'].value == "prep" -%}{%- assign has_prep = true -%}{%- endif -%}{%- endfor -%}
<div class="cols" style="margin-top:8px">
{% assign cur = "" %}{% for r in rows %}{% if r['session_id'].value == sid and r['exercise.category'].value != "prep" %}{% if r['exercise.name'].value != cur %}{% unless cur == "" %}</div>{% endunless %}{% assign cur = r['exercise.name'].value %}<div class="ex"><div class="name">{{ cur }}<span class="cat">{{ r['exercise.category'].value }}</span></div>{% endif %}
<div class="set {{ r['set_type'].value }}">""" + rpe_class("r['rpe'].value") + """<span class="n">{{ r['set_number'].value }}</span><span class="w">{% if r['load_type'].value == "bodyweight" %}BW{% elsif r['weight_lb'].value == 0 or r['weight_lb'].value == nil %}<span class="faint">&mdash;</span>{% else %}""" + num("r['weight_lb'].value") + """{% endif %}</span><span class="x">&times;</span><span class="r">{{ r['reps'].value | round }}{% if r['rep_unit'].value == "walks" %} walks{% if r['distance_ft'].value %} &middot; {{ r['distance_ft'].value | round }} ft{% endif %}{% elsif r['rep_unit'].value == "seconds" %} s{% endif %}</span>{% if r['rpe'].value %}<span class="rpe {{ rc }}">@ {{ r['rpe'].value | round: 1 }}</span>{% endif %}{% if r['gear_s'].value %}<span class="chip">{{ r['gear_s'].value }}</span>{% endif %}<span class="note">{{ r['notes'].value }}</span></div>
{% endif %}{% endfor %}{% unless cur == "" %}</div>{% endunless %}
</div>
{% if has_prep %}<div class="rule" style="margin-top:10px;padding-top:8px">
<div class="eyebrow">Warm-up</div>
<div class="warm">{%- assign pcur = "" -%}{%- assign firstp = true -%}{% for r in rows %}{% if r['session_id'].value == sid and r['exercise.category'].value == "prep" %}{% if r['exercise.name'].value != pcur %}{%- assign pcur = r['exercise.name'].value -%}{% unless firstp %}<span class="sep">&middot;</span>{% endunless %}{%- assign firstp = false -%}<span class="nm">{{ pcur }}</span>{% endif %}<span class="qty">{% if r['load_type'].value == "bodyweight" %}BW{% else %}""" + num("r['weight_lb'].value") + """{% endif %}&times;{{ r['reps'].value | round }}{% if r['rep_unit'].value == "seconds" %}s{% endif %}</span>{% endif %}{% endfor %}</div>
</div>{% endif %}
{% endif %}"""))

NOTES_CARD = page(tok("""
<div class="eyebrow">Notes</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No notes") + """</div>{% else %}
{% assign sid = rows[0]['session_id'].value %}
<div class="list" style="margin-top:8px">
{% for r in rows %}{% if r['session_id'].value == sid %}<div class="item"><span class="when">{{ r['phase'].value }}</span><span class="txt"><span class="prose" style="color:$CHALK">{{ r['text'].value }}</span>{% if r['exercise.name'].value %} <span class="faint">{{ r['exercise.name'].value }}</span>{% endif %}{% if r['tags_s'].value %}<br>{% assign tags = r['tags_s'].value | split: "|" %}{% for t in tags %}<span class="chip">{{ t }}</span>{% endfor %}{% endif %}</span></div>{% endif %}{% endfor %}
</div>{% endif %}"""))


WRAP_CARD = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Wrap up</div><div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="eyebrow">Wrap up</div>
<div class="prose" style="margin-top:8px">{{ rows[0]['wrap_up'].value | default: "Not written" }}</div>
{% if rows[0]['watch_s'].value %}<div class="eyebrow" style="margin-top:14px">Watch</div><div class="list" style="margin-top:4px">{% assign items = rows[0]['watch_s'].value | split: "|" %}{% for w in items %}<div class="item"><span class="txt" style="font-size:11px">{{ w }}</span></div>{% endfor %}</div>{% endif %}
{% if rows[0]['gear_notes'].value %}<div class="eyebrow" style="margin-top:14px">Gear</div><div class="prose" style="margin-top:4px;font-size:12px">{{ rows[0]['gear_notes'].value }}</div>{% endif %}
{% endif %}"""))

# The lift name and its numbers on one line. Until Phase 3 this was the name plus three
# hero tiles - best e1RM, best top set, avg RPE - which is the set of numbers a phone
# already shows, drawn at the same weight as the verdict underneath. Worse, BEST E1RM
# said 420 while the verdict beside it said "your best 420" and the chart's reference
# line sat at 420: the same number three times, twice as decoration.
#
# The numbers stay, at body size, on the sub-line. Nothing is lost and the verdict leads.

LIFT_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Lift</div>""" + empty("Open a lift from any dashboard") + """{% else %}
<div class="row">
<div class="card" style="flex:1"><div class="top"><div class="eyebrow">Lift</div><div class="title" style="font-size:30px;font-weight:700;text-transform:uppercase;line-height:1">{{ rows[0]['name'].value }}</div></div>
<div class="sub">{{ rows[0]['sessions'].value }} session{% if rows[0]['sessions'].value != 1 %}s{% endif %} &middot; {{ rows[0]['n'].value }} working sets &middot; last {{ rows[0]['last_s'].value }}</div>
<div class="sub">best e1RM&nbsp;""" + num("rows[0]['e1'].value") + """&nbsp;lb &middot; best top set&nbsp;""" + num("rows[0]['top'].value") + """&nbsp;lb &middot; avg RPE {{ rows[0]['rpe'].value | round: 1 }}</div></div>
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
<div class="card"><div class="top"><div class="eyebrow">Meets</div><div class="value">{{ rows[0]['meets'].value }}</div></div><div class="sub">in the page's range</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best total</div><div class="value" style="color:$BLOOD">{{ rows[0]['total_kg'].value | round: 1 }}<small>kg</small></div></div><div class="sub">""" + num("rows[0]['total_lb'].value", 1) + """&nbsp;lb</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best DOTS</div><div class="value">{{ rows[0]['dots'].value | round: 2 }}</div></div><div class="sub">across those meets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Attempts made</div><div class="value">{{ rows[0]['made'].value }}<small>of {{ rows[0]['attempts'].value }}</small></div></div><div class="sub">{%- assign att = rows[0]['attempts'].value | plus: 0 -%}{% if att > 0 %}{{ rows[0]['made'].value | times: 100 | divided_by: att | round }}% made in range{% else %}no attempts logged{% endif %}</div></div>
{% endif %}
</div>"""))

MEET_BESTS = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Best lifts</div>""" + empty("No meets logged") + """{% else %}
{%- assign best = rows[0]['lb'].value | plus: 0 -%}
<div class="eyebrow">Best lifts on the platform</div>
<div style="margin-top:10px">
{% for r in rows %}<div class="liftrow"><span class="lname">{{ r['lift'].value }}</span><span class="lval">""" + num("r['lb'].value", 1) + """<small style="font-size:11px;color:$FAINT;margin-left:4px">lb</small></span><span class="lbar"><i style="width:{% if best > 0 %}{{ r['lb'].value | times: 100 | divided_by: best | round }}{% else %}0{% endif %}%"></i></span><span class="lkg">{{ r['kg'].value | round: 1 }} kg</span></div>{% endfor %}
</div>{% endif %}"""))

MEET_LIST = page(tok("""
<div class="eyebrow">Meets</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No meets logged") + """</div>{% else %}
<div class="row" style="margin-top:10px;height:auto;gap:0">
{% assign cur = "" %}{% for r in rows %}{% if r['meet_id'].value != cur %}{% unless forloop.first %}</div></div>{% endunless %}{% assign cur = r['meet_id'].value %}{% assign curlift = "" %}
<div class="card"><div class="top"><div class="value" style="font-size:20px">{{ r['date_s'].value }}</div><div class="sub"><span class="v">{{ r['total_kg'].value | round: 1 }}</span> kg total &middot; <span class="v">{{ r['dots'].value | round: 2 }}</span> DOTS &middot; {{ r['bodyweight_kg'].value | round: 1 }} kg bw</div></div><div class="grid3" style="margin-top:10px">{% endif %}
{% if r['lift'].value != curlift %}{% assign curlift = r['lift'].value %}{% endif %}
<div><div class="eyebrow" style="letter-spacing:.1em">{{ r['lift'].value }} {{ r['attempt_no'].value }}</div><span class="chip {% if r['made'].value %}made{% else %}miss{% endif %}">{{ r['weight_kg'].value | round: 1 }}</span></div>
{% if forloop.last %}</div></div>{% endif %}{% endfor %}
</div>{% endif %}"""))

RECENT_NOTES = page(tok("""
<div class="eyebrow">Recent notes</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No notes") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{{ r['date_s'].value }}<br><span style="color:$DIM">{{ r['phase'].value }}</span></span><span class="txt"><span class="prose" style="color:$CHALK">{{ r['text'].value }}</span>{% if r['exercise.name'].value %} <span class="faint">{{ r['exercise.name'].value }}</span>{% endif %}{% if r['tags_s'].value %}<br>{% assign tags = r['tags_s'].value | split: "|" %}{% for t in tags %}<span class="chip">{{ t }}</span>{% endfor %}{% endif %}</span></div>{% endfor %}
</div>{% endif %}"""))


def total_card(meet_max: float) -> str:
    return TOTAL_CARD.replace("$MEET_MAX_NUM", str(meet_max)).replace("$MEET_MAX", f"{meet_max:g}")


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
.sig .verdict.b-max{color:$BLOOD;font-weight:700}
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
    return (BASE_CSS + SIGNAL_CSS + '<div class="sig">'
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
{%- assign prior = 0 -%}{%- assign beat = 0 -%}{%- assign sum = 0 -%}{%- assign maxh = hv -%}
{%- for r in rows offset: 1 -%}
  {%- assign rt = r['tot'].value | plus: 0 -%}
  {%- if rt > 0 -%}
    {%- assign rh = r['heavy'].value | plus: 0 -%}
    {%- assign prior = prior | plus: 1 -%}
    {%- assign sum = sum | plus: rh -%}
    {%- if rh < hv -%}{%- assign beat = beat | plus: 1 -%}{%- endif -%}
    {%- if rh > maxh -%}{%- assign maxh = rh -%}{%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if prior < 4 -%}
<div class="verdict b-normal">{{ hv }} rep{% unless hv == 1 %}s{% endunless %} at 80% or more.</div>
<div class="ev">Out of <b>{{ tot }}</b> main-lift reps this week.</div>
<div class="none">Ranking a week against your own history needs 4 earlier weeks
carrying main-lift work. You have <b>{{ prior }}</b>.
</div>
{%- else -%}
{%- assign share = beat | times: 100 | divided_by: prior -%}
{%- assign band = "b-light" -%}
{%- if share >= 85 -%}{%- assign band = "b-max" -%}
{%- elsif share >= 60 -%}{%- assign band = "b-heavy" -%}
{%- elsif share >= 25 -%}{%- assign band = "b-normal" -%}{%- endif -%}
<div class="verdict {{ band }}">
{%- if beat == prior -%}Heavier than any of your last {{ prior }} weeks.
{%- elsif beat == 0 -%}Lighter than every one of your last {{ prior }} weeks.
{%- else -%}Heavier than {{ beat }} of your last {{ prior }} weeks.{%- endif -%}
</div>
{%- assign avg = sum | times: 1.0 | divided_by: prior -%}
<div class="ev"><b>{{ hv }}</b> of {{ tot }} main-lift reps at 80% or more of your best in the last 90 days.</div>
{%- if maxh > 0 -%}
{%- assign w = hv | times: 100 | divided_by: maxh -%}
{%- assign bx = avg | times: 100 | divided_by: maxh | round -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:{{ bx }}%"></u></div>
{%- endif -%}
<div class="base">your {{ prior }}-week average: {{ avg | round: 1 }}</div>
{%- endif -%}
{%- endif -%}
{%- endif -%}
"""

SIGNAL_INTENSITY = signal(
    "How heavy was this week",
    _INTENSITY_BODY,
    # The moat, said in the evidence line above at body size, and defended here.
    "Heavy means heavy for you now. Every logging app measures a set against an "
    "all-time PR, so a lifter back from a layoff sees everything as light. This measures "
    "it against the trailing 90 days. Main lifts only.",
    "See History &#9656; where the reps live",
)


# --- 2. load trend ---------------------------------------------------------
#
# ACWR is already load_7d/7 over load_28d/28, so "x% above your 4-week average" is
# (acwr - 1) x 100 and cannot disagree with the band beside it. The precedent lookup
# is what turns a flag into a judgment, and it has to skip the contiguous run of the
# current band or it reports last week.

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
{%- if off -%}
<div class="verdict b-normal">Coming back.</div>
<div class="ev">Only <b>{{ trained }}</b> of the last 28 days carried load, so this ratio is
arithmetic rather than a spike. It will mean something again once the four-week base
refills.</div>
{%- else -%}
<div class="verdict {{ cls }}">{{ word }}</div>
{%- assign pct = acwr | minus: 1 | times: 100 | round -%}
<div class="ev">7-day load
{%- if pct >= 0 %} <b>{{ pct }}%</b> above{% else %}{%- assign under = 0 | minus: pct %} <b>{{ under }}%</b> below{% endif %}
your 4-week average.
{%- assign mono = rows[0]['monotony'].value -%}
{%- if mono %}<br>Monotony {{ mono | round: 2 }}.{% endif %}</div>
{%- comment -%} Skip the run of weeks already in this band, then take the two most
recent distinct months that were. {%- endcomment -%}
{%- assign run = true -%}{%- assign found = 0 -%}{%- assign prev_m = "" -%}{%- assign months = "" -%}
{%- for r in rows offset: 1 -%}
  {%- assign b = r['acwr_band'].value -%}
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
{%- if found == 0 -%}No earlier week in your whole log in this band.
{%- elsif found == 1 -%}Last time you were here: <b>{{ months }}</b>.
{%- else -%}The last two times you were here: <b>{{ months }}</b>.{%- endif -%}
</div>
{%- endif -%}
{%- endunless -%}
{%- endif -%}
"""

SIGNAL_LOAD = signal(
    "Am I ramping",
    _LOAD_BODY,
    "Acute:chronic is a flag, not a prediction. Load is tonnage, so this reads back to "
    "Jan 2023. Monotony counts rest days as zero, which is the point of it.",
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
{%- assign now_s = "now" | date: "%s" | plus: 0 -%}
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
  {%- if n >= 6 and cad > 0 -%}
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
{%- if ranked == 0 -%}
<div class="none">A muscle group needs 6 sessions in a year before its normal gap
means anything. None of your <b>{{ groups }}</b> qualify yet.</div>
{%- elsif flagged == 0 -%}
<div class="verdict b-normal">Nothing is drifting.</div>
<div class="ev">All <b>{{ ranked }}</b> muscle groups trained inside their normal window.</div>
{%- else -%}
{%- assign ratio = f_gap | times: 10 | divided_by: f_cad | round -%}
{%- assign cls = "b-heavy" -%}{%- if ratio >= 30 -%}{%- assign cls = "b-max" -%}{%- endif -%}
<div class="verdict {{ cls }}">{{ f_name }}: {{ f_gap }} days.</div>
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
  {%- if n >= 6 and cad > 0 and shown < 2 -%}
    {%- assign last_s = r['last_trained'].value | date: "%s" | plus: 0 -%}
    {%- assign gap = now_s | minus: last_s | divided_by: 86400 | floor -%}
    {%- assign lim = cad | times: 2 -%}
    {%- assign nm = r['muscle'].value | replace: "-", " " | capitalize -%}
    {%- if gap > lim and nm != f_name -%}
      {%- assign shown = shown | plus: 1 -%}
      {{ nm }} {{ gap }}d &middot; every {{ cad | round }}<br>
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value }}</div>
{%- endif -%}
"""


SIGNAL_DRIFT = signal(
    "What am I neglecting",
    _DRIFT_BODY,
    "Working sets, last 365 days, counted when the log was indexed rather than from what "
    "this page is showing. Normal is that group's average gap over the year; a group is "
    "flagged past twice it. Groups trained fewer than 6 times are not ranked.",
    "See Session &#9656; every set",
)


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
{%- comment -%} The control supplies the lift; with it cleared, follow whichever lift the
most recent session used, the way the header above does. {%- endcomment -%}
{%- assign slug = rows[0]['lift_slug'].value -%}
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
<div class="ev">Recent best <b>{{ recent | round }}</b> lb &middot;
your best <b>{{ peak | round }}</b> lb, {{ peak_s }}.</div>
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
"""

SIGNAL_LIFT = signal(
    "Where is this lift",
    _LIFT_BODY,
    "Confident e1RM estimates on working sets, for the lift you arrived on and this "
    "page's range. One session's estimate swings with how hard that day was, so this "
    "compares your best of five sessions, never one session to the next.",
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
      {%- assign cur_n = r['weeks_out'].value | plus: 0 -%}
      {%- assign cur_k = r['cum_weeks'].value | plus: 0 -%}
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
{%- assign ref_week = 0 -%}{%- assign ref_wk_days = 0 -%}{%- assign ref_wk_rpe = 0 -%}
{%- for r in rows -%}
  {%- if r['cycle'].value == ref -%}
    {%- assign wo = r['weeks_out'].value | plus: 0 -%}
    {%- assign ck = r['cum_weeks'].value | plus: 0 -%}
    {%- if cur_k > 0 and wo == cur_n and ck == cur_k -%}
      {%- assign ref_ton = r['cum_tonnage_lb'].value | plus: 0 -%}
      {%- assign ref_heavy = r['cum_heavy'].value | plus: 0 -%}
    {%- endif -%}
    {%- if cur_k == 0 and wo == open_n -%}
      {%- assign ref_week = r['tonnage_lb'].value | plus: 0 -%}
      {%- assign ref_wk_days = r['training_days'].value | plus: 0 -%}
      {%- assign ref_wk_rpe = r['avg_working_rpe'].value | plus: 0 -%}
    {%- endif -%}
  {%- endif -%}
{%- endfor -%}
{%- if cur_k == 0 -%}
{%- comment -%} The run-in has opened but no week of it has closed. Ruling here would
compare a Wednesday against a finished week and print a collapse in volume that is only
a calendar artefact. {%- endcomment -%}
<div class="verdict b-light">Week {{ open_n }} of the run-in, still open.</div>
<div class="ev"><b>__OPEN_DAYS__</b>&nbsp;training day{% if open_days != 1 %}s{% endif %} in,
<b>__OPEN_TON__</b>&nbsp;lb{%- if open_rpe > 0 %} at RPE __OPEN_RPE__{% endif -%}.
{%- if ref_week > 0 %} {{ ref_label }} closed the same week on <b>__REF_WEEK__</b>&nbsp;lb
across {{ ref_wk_days }} day{% if ref_wk_days != 1 %}s{% endif %}{% if ref_wk_rpe > 0 %} at RPE __REF_WK_RPE__{% endif %}.{% endif -%}
</div>
<div class="base">nothing is ranked until the week closes</div>
{%- elsif ref_ton > 0 -%}
{%- assign pct = cur_ton | times: 100 | divided_by: ref_ton | round -%}
{%- assign cls = "b-heavy" -%}
{%- if pct >= 90 and pct <= 110 -%}{%- assign cls = "b-normal" -%}{%- endif -%}
{%- if pct < 70 or pct > 130 -%}{%- assign cls = "b-max" -%}{%- endif -%}
<div class="verdict {{ cls }}">{{ pct }}% of {{ ref_label }}'s volume.</div>
<div class="ev">Through week <b>{{ cur_n }}</b> out,
<b>{{ cur_k }}</b> closed week{% if cur_k != 1 %}s{% endif %} of the run-in:
<b>__CUR_TON__</b>&nbsp;lb.
{{ ref_label }}, {{ ref_made }} for {{ ref_tot }},
had moved <b>__REF_TON__</b>&nbsp;lb by the same point.</div>
{%- comment -%} The bar runs to 150% of the yardstick so being ahead of it is visible
rather than pinned at full width, and the tick sits where the yardstick is. {%- endcomment -%}
{%- assign w = pct | times: 100 | divided_by: 150 -%}
{%- if w > 100 -%}{%- assign w = 100 -%}{%- endif -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:66%"></u></div>
<div class="base">tick marks {{ ref_label }}'s pace</div>
{%- if cur_heavy > 0 or ref_heavy > 0 -%}
<div class="also">reps at 80%+ &middot; you {{ cur_heavy }} &middot; {{ ref_label }} {{ ref_heavy }}</div>
{%- endif -%}
{%- elsif ref == "" -%}
<div class="none">No meet on record yet to measure the run-in to {{ cur_label }} against.
The comparison starts with your second meet.</div>
{%- else -%}
<div class="none">Through week <b>{{ cur_n }}</b> out you have <b>{{ cur_k }}</b> closed
week{% if cur_k != 1 %}s{% endif %} logged, and
{{ ref_label }} has no matching stretch at that distance &mdash;
the log does not reach far enough back before it.</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__OPEN_DAYS__", "{{ open_days }}")
            .replace("__OPEN_TON__", num("open_ton"))
            .replace("__OPEN_RPE__", "{{ open_rpe | round: 1 }}")
            .replace("__REF_WEEK__", num("ref_week"))
            .replace("__REF_WK_RPE__", "{{ ref_wk_rpe | round: 1 }}")
            .replace("__CUR_TON__", num("cur_ton"))
            .replace("__REF_TON__", num("ref_ton")))


_TAPER_BODY = _taper_body()


SIGNAL_TAPER = signal(
    "Am I running this in like the last one",
    _TAPER_BODY,
    "Weekly tonnage from the whole log, aligned by ISO week to each meet date and frozen "
    "when the log was indexed. The week in progress is excluded, and a past cycle counts "
    "only where it has the same number of closed weeks behind it. The yardstick is the "
    "meet with the best attempt record. Two meets is a comparison, not a rule &mdash; "
    "tonnage moves with exercise selection as much as with effort.",
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
<div class="verdict {{ cls }}">{{ band | capitalize }}.</div>
<div class="ev"><b>{{ w['inol_hardest_lift'].value }}</b> is the hardest lift of the week
at INOL __INOL__ &mdash; {{ w['inol_hardest_gloss'].value }}.
{%- if seen > 0 %} Harder than <b>{{ seen | minus: harder }}</b> of your last {{ seen }} weeks.{% endif -%}
</div>
{%- assign acwr = w['acwr'].value | plus: 0 -%}
{%- if acwr > 0 -%}
<div class="also">load {{ w['acwr_band'].value }} at __ACWR__ &middot; {{ w['acwr_gloss'].value }}</div>
{%- endif -%}
<div class="base">last trained {{ w['week_end'].value }}{% if w['block'].value %} &middot; {{ w['block'].value }} block{% endif %}</div>
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__INOL__", "{{ inol | round: 2 }}")
            .replace("__ACWR__", "{{ acwr | round: 2 }}"))


_PROGRAM_BODY = _program_body()


SIGNAL_PROGRAM = signal(
    "How hard is this week loading",
    _PROGRAM_BODY,
    "INOL is reps divided by (100 minus intensity), summed per lift across the week; the "
    "hardest single lift is the one worth banding, because Hristov's bands are per "
    "exercise and a total across five lifts is not comparable to them. Easy is under 2, "
    "loading to 3, brutal to 4, excessive above. Main lifts only, from the whole log "
    "rather than from what this page is showing.",
    "See the weekly loading table below",
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
{%- if peers == 0 or theirs == 0 -%}
<div class="verdict b-light">Your first {{ name }} block.</div>
<div class="ev"><b>__MINE__</b> heavy reps a session across <b>{{ cur['sessions'].value }}</b>
sessions &mdash; <b>{{ cur['heavy'].value }}</b> of <b>{{ cur['main_reps'].value }}</b>
main-lift reps at 80% or more. There is nothing of the same kind to rank it against yet.</div>
{%- else -%}
{%- assign pct = mine | times: 100 | divided_by: theirs | round -%}
{%- assign cls = "b-heavy" -%}
{%- if pct >= 90 and pct <= 110 -%}{%- assign cls = "b-normal" -%}{%- endif -%}
{%- if pct < 70 or pct > 130 -%}{%- assign cls = "b-max" -%}{%- endif -%}
<div class="verdict {{ cls }}">{{ pct }}% of the heavy work in a usual {{ name }} block.</div>
<div class="ev"><b>__MINE__</b> heavy reps a session this block,
against a median of <b>__THEIRS__</b> across your {{ peers }} earlier {{ name }} blocks.
That is <b>{{ cur['heavy'].value }}</b> of <b>{{ cur['main_reps'].value }}</b> main-lift reps
at 80% or more, against __PSHARE__% then.</div>
{%- assign w = pct | times: 100 | divided_by: 150 -%}
{%- if w > 100 -%}{%- assign w = 100 -%}{%- endif -%}
<div class="gauge"><i style="width:{{ w }}%"></i><u style="left:66%"></u></div>
<div class="base">tick marks your usual {{ name }} block</div>
{%- endif -%}
<div class="base">this block began {{ cur['first_trained'].value }}{% if peers > 0 %}, the comparison reaches back to {{ cur['peer_from'].value }}{% endif %}</div>
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__MINE__", "{{ mine | round: 2 }}")
            .replace("__THEIRS__", "{{ theirs | round: 2 }}")
            .replace("__PSHARE__", "{{ cur['peer_share_pct'].value | round: 1 }}"))


_BLOCK_BODY = _block_body()


SIGNAL_BLOCK = signal(
    "How heavy is this block",
    _BLOCK_BODY,
    "Heavy is 80% or more of your best estimate in the trailing 90 days, main lifts only. "
    "A block is a run of consecutive sessions sharing a program block, and the comparison "
    "is against earlier runs of the same kind only &mdash; a strength block and a "
    "hypertrophy block are not meant to load alike. Reps per session rather than share, "
    "because a share off a small denominator swings on one set. Runs under 4 sessions are "
    "not ranked.",
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
<div class="none">No projected total yet. It needs a recent estimate on all three
competition lifts.</div>
{%- else -%}
{%- assign peers = now['peers'].value | plus: 0 -%}
{%- assign ratio = now['peer_pct'].value | plus: 0 -%}
{%- if peers == 0 or ratio == 0 -%}
<div class="verdict b-light">__NOW__&nbsp;lb projected.</div>
<div class="ev">No meet on record has a projection behind it yet, so there is nothing to
say about what this number has been worth on the platform.</div>
{%- else -%}
<div class="verdict b-normal">{{ ratio | round }}% of projection, both times.</div>
<div class="ev">
{%- for r in rows -%}
  {%- if r['cycle_role'].value == "past" -%}
{{ r['cycle_label'].value }} projected <b>{{ r['projected_total_lb'].value | round }}</b> and you totalled <b>{{ r['meet_total_lb'].value | round }}</b>.&#32;
  {%- endif -%}
{%- endfor -%}
It reads <b>__NOW__</b>&nbsp;lb today, which puts a realistic platform total near
<b>__EXPECTED__</b>&nbsp;lb.</div>
<div class="base">a projection is a training estimate;
the platform is singles at a commanded pace</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value }}</div>
{%- endif -%}
"""
    return (raw
            .replace("__NOW__", "{{ now['projected_total_lb'].value | round }}")
            .replace("__EXPECTED__", "{{ now['expected_lb'].value | round }}"))


_PROJECTION_BODY = _projection_body()


SIGNAL_PROJECTION = signal(
    "What is this projection worth",
    _PROJECTION_BODY,
    "The projected total is the sum of your best estimate on each competition lift inside "
    "a 90-day window, taken from competition lifts only. For each meet on record it is the "
    "projection as it stood in the last week before that meet &mdash; what you would have "
    "been told walking in, not a number computed afterwards. Two meets is a ratio, not a "
    "rule.",
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
<div class="none">No tagged notes yet. Tags are written in the log beside a note; once
there are a few weeks of them this card starts reading them back.</div>
{%- else -%}
{%- assign span = rows[0]['notes_span_days'].value | plus: 0 -%}
{%- assign total = rows[0]['notes_total'].value | plus: 0 -%}
{%- assign win = rows[0]['window_days'].value | plus: 0 -%}
{%- if span < __MIN_SPAN__ -%}
<div class="verdict b-light">Too new to read a pattern.</div>
<div class="ev">Your notes begin <b>{{ rows[0]['notes_from'].value }}</b> &mdash;
<b>{{ total }}</b> of them across <b>{{ span }}</b> days. A tag needs about
{{ __MIN_SPAN__ }} days behind it before "more than usual" means anything.</div>
<div class="also">
{%- for r in rows limit: 3 -%}
{{ r['tag'].value }} {{ r['total'].value }}{% unless forloop.last %} &middot; {% endunless %}
{%- endfor -%}
</div>
{%- else -%}
{%- assign t = rows[0] -%}
{%- assign n = t['recent'].value | plus: 0 -%}
{%- if n == 0 -%}
<div class="verdict b-light">Nothing written in the last {{ win }} days.</div>
<div class="ev">The log has <b>{{ total }}</b> tagged notes, most recently
{{ t['last_trained'].value }}.</div>
{%- else -%}
{%- assign before = t['prior'].value | plus: 0 -%}
<div class="verdict b-normal">
You have written &ldquo;{{ t['tag'].value }}&rdquo; {{ n }} time{% if n != 1 %}s{% endif %} in {{ win }} days.</div>
<div class="ev">
{%- if before > 0 -%}Against <b>{{ before }}</b> in the {{ win }} days before that.
{%- else -%}Nothing tagged that way in the {{ win }} days before that.{%- endif -%}
{%- if rows.size > 1 %} Next: {{ rows[1]['tag'].value }} ({{ rows[1]['recent'].value }}).{% endif -%}
</div>
{%- endif -%}
{%- endif -%}
<div class="base">from the whole log, indexed {{ rows[0]['computed_through'].value }}</div>
{%- endif -%}
"""
    return raw.replace("__MIN_SPAN__", str(MIN_TAG_SPAN_DAYS))


_TAG_BODY = _tag_body()


SIGNAL_TAGS = signal(
    "What do I keep writing down",
    _TAG_BODY,
    "Tags on your own notes, counted over the whole log rather than what this page is "
    "showing. A count is not a diagnosis: it says what you wrote often, not what mattered "
    "most. The question this page cannot answer &mdash; what a note actually said &mdash; "
    "goes to the coach.",
    "Ask the coach to read the notes themselves",
)
