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
STEEL = "#7a7873"
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
.eyebrow{font-family:$MONO;font-size:10px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:$FAINT;white-space:nowrap}
.eyebrow.blood{color:$BLOOD}
.eyebrow.dim{color:$DIM}
.hero{font-size:46px;font-weight:700;line-height:1;letter-spacing:-.015em;text-transform:uppercase;white-space:nowrap;font-variant-numeric:tabular-nums}
.hero.blood{color:$BLOOD}
.value{font-size:32px;font-weight:600;line-height:1.05;text-transform:uppercase;white-space:nowrap}
.value small{font-size:15px;font-weight:500;color:$DIM;letter-spacing:.04em;margin-left:5px}
.sub{font-family:$MONO;font-size:12px;color:$DIM;letter-spacing:.03em;line-height:1.55}
.faint{color:$FAINT}
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
.empty{color:$FAINT;font-family:$MONO;font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.list{display:flex;flex-direction:column}
.item{display:flex;align-items:baseline;gap:12px;padding:7px 0;border-top:1px solid $RULE;font-family:$MONO;font-size:13px}
.item:first-child{border-top:0}
.item .when{color:$FAINT;font-size:11px;letter-spacing:.06em;text-transform:uppercase;min-width:72px}
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
.set .note{color:$FAINT;font-size:12px;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
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
.lkg{font-family:$MONO;font-size:11px;color:$FAINT;min-width:62px;text-align:right}
.warm{font-family:$MONO;font-size:12px;line-height:1.9;color:$DIM;margin-top:5px}
.warm .nm{color:$CHALK;text-transform:uppercase;letter-spacing:.04em;font-size:11px;margin-right:5px}
.warm .qty{color:$FAINT;margin-right:7px}
.warm .sep{color:$RULE;margin-right:9px}
.cols .ex{break-inside:avoid}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:4px 8px}
.k{color:$FAINT}
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
.tagline{{font-family:$MONO;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:$FAINT;text-align:right;max-width:52%;line-height:1.5}}
</style>
<div class="eyebrow">&#9646;&#9646;&#9646;&nbsp;&nbsp;A Mission Built training system&nbsp;&nbsp;&#9646;&#9646;&#9646;</div>
<div class="bar"><div class="left"><span class="word">Iron</span><span class="sq"></span><span class="word">Stack</span><span class="vr"></span><span class="section">{section}</span></div><div class="tagline">{tagline}</div></div>""")


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
DAYS_TO_MEET = """{% assign now_s = "now" | date: "%s" | plus: 0 %}{% assign meet_s = rows[0]['program.meet_date'].value | date: "%s" | plus: 0 %}{% assign days = meet_s | minus: now_s | divided_by: 86400.0 | ceil %}"""


def sparkline(rows_expr: str, field: str, width=160, height=36, color=CHALK) -> str:
    """Polyline over rows using the value's `.pct` (share of column max) for y."""
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="'
        f"{{% assign n = {rows_expr}.size | minus: 1 %}}{{% if n < 1 %}}{{% assign n = 1 %}}{{% endif %}}"
        f"{{% for r in {rows_expr} %}}{{{{ forloop.index0 | times: {width} | divided_by: n }}}},"
        f"{{{{ 100 | minus: r['{field}'].pct | times: {height - 4} | divided_by: 100 | plus: 2 }}}} {{% endfor %}}"
        '"/></svg>'
    )


# --------------------------------------------------------------------------- Overview cards

DAYS_TO_MEET_CARD = page(tok("""
<div class="stack spread">
{% if rows.size == 0 %}<div class="eyebrow">Days to meet</div>""" + empty("No sessions yet") + """{% else %}""" + DAYS_TO_MEET + """
<div><div class="eyebrow">Days to meet</div>
<div class="hero" style="margin-top:8px">{{ days }}</div></div>
<div class="sub">{{ rows[0]['meet_s'].value }}<br>{{ rows[0]['program.phase'].value }} &middot; week {{ rows[0]['program.week'].value }} &middot; day {{ rows[0]['program.day'].value }} of {{ rows[0]['program.total_days'].value }}<br><span class="faint">last trained {{ rows[0]['date_s'].value }}</span></div>
{% endif %}
</div>"""))

TOTAL_CARD = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Projected total</div>""" + empty() + """{% else %}
{%- assign total = 0 -%}{%- for r in rows -%}{%- assign _v = r['e1'].value | round -%}{%- assign total = total | plus: _v -%}{%- endfor -%}
{%- assign best = rows[0]['e1'].value -%}
<div class="eyebrow">Projected total</div>
<div class="hero" style="margin-top:7px">""" + num("total") + """<span style="font-size:20px;color:$DIM;margin-left:6px">lb</span></div>
<div class="sub" style="margin-top:3px">best of the last 90 days</div>
<div style="margin-top:12px">
{% for r in rows %}<div class="liftrow"><span class="lname">{{ r['lift'].value }}</span><span class="lval">""" + num("r['e1'].value") + """</span><span class="lbar"><i style="width:{{ r['e1'].value | times: 100 | divided_by: best | round }}%"></i></span></div>{% endfor %}
</div>
{%- assign pct = total | times: 100 | divided_by: $MEET_MAX_NUM | round -%}{%- assign togo = $MEET_MAX_NUM | minus: total | round -%}
<div class="rule" style="margin-top:12px;padding-top:8px"><span class="sub">{% if total >= $MEET_MAX_NUM %}<span class="v">{{ pct }}%</span> of your meet best, $MEET_MAX lb{% else %}<span class="v">{{ pct }}%</span> of your meet best &middot; <span class="v">""" + num("togo") + """&nbsp;lb</span> to go{% endif %}</span></div>
{% endif %}"""))

STREAK_CARD = page(tok("""
<div class="stack">
{% if rows.size == 0 %}<div class="eyebrow">Streak</div>""" + empty("No sessions yet") + """{% else %}
<div><div class="eyebrow">Best streak</div>
<div class="hero" style="margin-top:8px">{{ rows[0]['streak'].value }}<span class="value" style="font-size:16px;color:$DIM;margin-left:6px">day{% if rows[0]['streak'].value != 1 %}s{% endif %}</span></div></div>
<div class="sub">{{ rows[0]['n7'].value }} in 7 days<br>{{ rows[0]['n28'].value }} in 28 days</div>
{% endif %}
</div>"""))

LATEST_CARD = page(tok("""
<div class="stack">
{% if rows.size == 0 %}<div class="eyebrow">Latest session</div>""" + empty("No sessions yet") + """{% else %}
<div><div class="eyebrow">Latest session</div>
<div class="value" style="margin-top:8px">{{ rows[0]['date_s'].value }}</div>
<div class="sub">{{ rows[0]['program.block'].value }} &middot; day {{ rows[0]['program.day'].value }} &middot; {{ rows[0]['time_of_day'].value }}</div></div>
<div class="sub"><span class="v">""" + num("rows[0]['totals.tonnage_lb'].value") + """</span> lb &middot; <span class="v">{{ rows[0]['avg_working_rpe'].value }}</span> avg RPE &middot; <span class="v">{{ rows[0]['totals.working_sets'].value }}</span> working sets</div>
<div class="prose" style="overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{{ rows[0]['wrap_up'].value }}</div>
{% endif %}
</div>"""))

WATCH_CARD = page(tok("""
<div class="eyebrow">Watch items</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("Nothing to watch") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{{ r['date_s'].value }}</span><span class="txt">{{ r['item'].value }}</span></div>{% endfor %}
</div>{% endif %}"""))

METRIC_CARD = page(tok("""
<div class="stack">
<div><div class="eyebrow">$TITLE</div>
{% if rows.size == 0 or rows[0]['v'].value == nil %}<div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="hero" style="margin-top:8px">{{ rows[0]['v'].value | round: 1 }}<span class="value" style="font-size:16px;color:$DIM;margin-left:6px">$UNIT</span></div>{% endif %}</div>
{% if rows.size > 1 %}""" + sparkline("rows", "v", 220, 30, DIM) + """{% endif %}
</div>"""))


def metric_card(title: str, unit: str) -> str:
    return METRIC_CARD.replace("$TITLE", title).replace("$UNIT", unit)


# --------------------------------------------------------------------------- header cards (Program, Session, Lift)

PROGRAM_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Program</div>""" + empty("No sessions in this block") + """{% else %}""" + DAYS_TO_MEET + """
<div class="hdr"><span class="eyebrow">Program</span></div>
<div class="hdr" style="margin-top:8px"><span class="title">{{ rows[0]['program.name'].value }}</span><span class="meta"><b>{{ rows[0]['program.block'].value }}</b> block &middot; <b>{{ rows[0]['program.phase'].value }}</b> phase &middot; week <b>{{ rows[0]['program.week'].value }}</b> &middot; day <b>{{ rows[0]['program.day'].value }}</b> of <b>{{ rows[0]['program.total_days'].value }}</b></span></div>
<div class="sub" style="margin-top:10px">Meet {{ rows[0]['meet_s'].value }} &middot; <span class="v">{{ days }}</span> days out &middot; {{ rows[0]['n'].value }} sessions logged in this block &middot; last trained {{ rows[0]['date_s'].value }}</div>
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
<div class="card"><div class="top"><div class="eyebrow">Avg working RPE</div><div class="value">{{ rows[0]['avg_working_rpe'].value }}</div></div><div class="sub">{{ rows[0]['totals.working_sets'].value }} working sets</div></div>
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
{% if rows[0]['rpe'].value %}<span class="set" style="padding:0"><span class="rpe {{ rc }}" style="font-size:21px">@&nbsp;{{ rows[0]['rpe'].value }}</span></span>{% endif %}
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
<div><div class="eyebrow">Sky</div>{% if rows[0]['environment.conditions'].value %}<div class="value">{{ rows[0]['environment.conditions'].value }}</div>{% else %}<div class="empty">Not logged</div>{% endif %}</div>
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
<div class="set {{ r['set_type'].value }}">""" + rpe_class("r['rpe'].value") + """<span class="n">{{ r['set_number'].value }}</span><span class="w">{% if r['load_type'].value == "bodyweight" %}BW{% elsif r['weight_lb'].value == 0 or r['weight_lb'].value == nil %}<span class="faint">&mdash;</span>{% else %}""" + num("r['weight_lb'].value") + """{% endif %}</span><span class="x">&times;</span><span class="r">{{ r['reps'].value | round }}{% if r['rep_unit'].value == "walks" %} walks{% if r['distance_ft'].value %} &middot; {{ r['distance_ft'].value | round }} ft{% endif %}{% elsif r['rep_unit'].value == "seconds" %} s{% endif %}</span>{% if r['rpe'].value %}<span class="rpe {{ rc }}">@ {{ r['rpe'].value }}</span>{% endif %}{% if r['gear_s'].value %}<span class="chip">{{ r['gear_s'].value }}</span>{% endif %}<span class="note">{{ r['notes'].value }}</span></div>
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

LIFT_HEADER = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Lift</div>""" + empty("Open a lift from any dashboard") + """{% else %}
<div class="row">
<div class="card" style="flex:1.6"><div class="top"><div class="eyebrow">Lift</div><div class="title" style="font-size:30px;font-weight:700;text-transform:uppercase;line-height:1">{{ rows[0]['name'].value }}</div></div><div class="sub">{{ rows[0]['sessions'].value }} session{% if rows[0]['sessions'].value != 1 %}s{% endif %} &middot; {{ rows[0]['n'].value }} working sets &middot; last {{ rows[0]['last_s'].value }}</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best e1RM</div><div class="value">""" + num("rows[0]['e1'].value") + """<small>lb</small></div></div><div class="sub">estimated, working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best top set</div><div class="value">""" + num("rows[0]['top'].value") + """<small>lb</small></div></div><div class="sub">heaviest working set</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg RPE</div><div class="value">{{ rows[0]['rpe'].value | round: 1 }}</div></div><div class="sub">across working sets</div></div>
</div>{% endif %}"""))

# --------------------------------------------------------------------------- Program days, History cards, Meets, Mindset

DAYS_LIST = page(tok("""
<div class="eyebrow">Days</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No sessions in this selection") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{% if r['program.week'].value %}wk {{ r['program.week'].value }}{% if r['program.day'].value %} &middot; d{{ r['program.day'].value }}{% endif %}{% else %}{{ r['date_s'].value }}{% endif %}</span><span class="txt">{% if r['program.week'].value %}{{ r['date_s'].value }} {% endif %}<span class="faint">{{ r['time_of_day'].value }}{% if r['location.name'].value %} &middot; {{ r['location.name'].value }}{% endif %}</span></span><span class="num">""" + num("r['totals.tonnage_lb'].value") + """ lb &middot; RPE {{ r['avg_working_rpe'].value | round: 1 }}{% if r['duration_min'].value %} &middot; {{ r['duration_min'].value | round }} min{% endif %}</span></div>{% endfor %}
</div>{% endif %}"""))

FOUR_CARDS = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty("No sessions in range") + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Tonnage</div><div class="value">""" + num("rows[0]['ton'].value") + """<small>lb</small></div></div><div class="sub">in range</div></div>
<div class="card"><div class="top"><div class="eyebrow">Per session</div><div class="value">""" + num("rows[0]['avg'].value") + """<small>lb</small></div></div><div class="sub">average</div></div>
<div class="card"><div class="top"><div class="eyebrow">Sessions</div><div class="value">{{ rows[0]['n'].value }}</div></div><div class="sub">{{ rows[0]['sets'].value }} working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg working RPE</div><div class="value">{{ rows[0]['rpe'].value | round: 1 }}</div></div><div class="sub">across sessions</div></div>
{% endif %}
</div>"""))

MEET_CARDS = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty("No meets logged") + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Meets</div><div class="value">{{ rows[0]['meets'].value }}</div></div><div class="sub">competitions logged</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best total</div><div class="value" style="color:$BLOOD">{{ rows[0]['total_kg'].value | round: 1 }}<small>kg</small></div></div><div class="sub">""" + num("rows[0]['total_lb'].value", 1) + """ lb</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best DOTS</div><div class="value">{{ rows[0]['dots'].value | round: 2 }}</div></div><div class="sub">all meets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Attempts made</div><div class="value">{{ rows[0]['made'].value }}<small>of {{ rows[0]['attempts'].value }}</small></div></div><div class="sub">{{ rows[0]['made'].value | times: 100 | divided_by: rows[0]['attempts'].value | round }}% success</div></div>
{% endif %}
</div>"""))

MEET_BESTS = page(tok("""
{% if rows.size == 0 %}<div class="eyebrow">Best lifts</div>""" + empty("No meets logged") + """{% else %}
{%- assign best = rows[0]['lb'].value -%}
<div class="eyebrow">Best lifts on the platform</div>
<div style="margin-top:10px">
{% for r in rows %}<div class="liftrow"><span class="lname">{{ r['lift'].value }}</span><span class="lval">""" + num("r['lb'].value", 1) + """<small style="font-size:11px;color:$FAINT;margin-left:4px">lb</small></span><span class="lbar"><i style="width:{{ r['lb'].value | times: 100 | divided_by: best | round }}%"></i></span><span class="lkg">{{ r['kg'].value | round: 1 }} kg</span></div>{% endfor %}
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
