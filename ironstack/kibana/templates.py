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
body{background:$BG;color:$CHALK;font-family:$DISPLAY;padding:14px 18px;overflow:hidden;-webkit-font-smoothing:antialiased}
.eyebrow{font-family:$MONO;font-size:10px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:$FAINT;white-space:nowrap}
.eyebrow.blood{color:$BLOOD}
.eyebrow.dim{color:$DIM}
.hero{font-size:44px;font-weight:700;line-height:1;letter-spacing:-.01em;text-transform:uppercase}
.hero.blood{color:$BLOOD}
.value{font-size:26px;font-weight:600;line-height:1.1;text-transform:uppercase}
.value small{font-size:13px;font-weight:500;color:$DIM;letter-spacing:.04em;margin-left:4px}
.sub{font-family:$MONO;font-size:11px;color:$DIM;letter-spacing:.04em;line-height:1.5}
.faint{color:$FAINT}
.mono{font-family:$MONO}
.prose{font-family:$SERIF;font-size:13px;line-height:1.55;color:$DIM}
.rule{border-top:1px solid $RULE}
.stack{display:flex;flex-direction:column;justify-content:space-between;height:100%}
.row{display:flex;gap:0;height:100%}
.card{flex:1;min-width:0;padding:0 18px;border-left:1px solid $RULE;display:flex;flex-direction:column;justify-content:space-between}
.card:first-child{padding-left:0;border-left:0}
.card .top{display:flex;flex-direction:column;gap:6px}
.chip{display:inline-block;font-family:$MONO;font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:$DIM;border:1px solid $RULE;padding:1px 6px;margin:0 4px 2px 0;white-space:nowrap}
.chip.made{color:$CHALK;border-color:$STEEL}
.chip.miss{color:$FAINT;text-decoration:line-through}
.chip.blood{color:$BLOOD;border-color:$BLOOD_DIM}
.bar{height:2px;background:$RULE;position:relative;margin-top:8px}
.bar i{position:absolute;left:0;top:0;bottom:0;background:$BLOOD;display:block}
.bar.dim i{background:$DIM}
.empty{color:$FAINT;font-family:$MONO;font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.list{display:flex;flex-direction:column}
.item{display:flex;align-items:baseline;gap:12px;padding:6px 0;border-top:1px solid $RULE;font-family:$MONO;font-size:12px}
.item:first-child{border-top:0}
.item .when{color:$FAINT;font-size:10px;letter-spacing:.08em;text-transform:uppercase;min-width:64px}
.item .txt{color:$CHALK;flex:1;min-width:0}
.item .num{color:$DIM;white-space:nowrap}
.set{display:flex;align-items:baseline;gap:10px;font-family:$MONO;font-size:12px;padding:3px 0}
.set .n{color:$FAINT;font-size:10px;min-width:16px}
.set .w{color:$CHALK;min-width:46px;text-align:right}
.set .x{color:$FAINT}
.set .r{color:$CHALK;min-width:28px}
.set .rpe{color:$DIM}
.set .note{color:$FAINT;font-size:11px;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.set.prep .w,.set.prep .r{color:$DIM}
.ex{margin-bottom:10px}
.ex .name{font-size:15px;font-weight:600;text-transform:uppercase;letter-spacing:.02em;line-height:1.3}
.ex .name .cat{font-family:$MONO;font-size:9px;letter-spacing:.16em;color:$FAINT;margin-left:8px;font-weight:500}
.cols{column-count:2;column-gap:36px}
.cols .ex{break-inside:avoid}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:4px 8px}
.k{color:$FAINT}
.v{color:$CHALK}
.hdr{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.hdr .title{font-size:26px;font-weight:700;text-transform:uppercase;letter-spacing:-.01em;line-height:1}
.hdr .meta{font-family:$MONO;font-size:11px;color:$DIM;letter-spacing:.06em;text-transform:uppercase}
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
html,body{{height:100%}}
body{{background:$BG;color:$CHALK;font-family:$DISPLAY;padding:10px 18px 8px;overflow:hidden;display:flex;flex-direction:column;justify-content:center;-webkit-font-smoothing:antialiased}}
.eyebrow{{font-family:$MONO;font-size:10px;font-weight:500;letter-spacing:.24em;text-transform:uppercase;color:$BLOOD;margin-bottom:6px}}
.bar{{display:flex;align-items:baseline;justify-content:space-between;gap:16px}}
.left{{display:flex;align-items:baseline;gap:10px}}
.word{{font-size:26px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;line-height:1}}
.sq{{display:inline-block;width:11px;height:11px;background:$BLOOD;transform:translateY(-1px)}}
.vr{{width:1px;height:22px;background:$RULE;transform:translateY(4px);margin:0 6px}}
.section{{font-family:$MONO;font-size:12px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:$DIM}}
.tagline{{font-family:$MONO;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:$FAINT;white-space:nowrap}}
</style>
<div class="eyebrow">&#9646;&#9646;&#9646;&nbsp;&nbsp;A Mission Built training system&nbsp;&nbsp;&#9646;&#9646;&#9646;</div>
<div class="bar"><div class="left"><span class="word">Iron</span><span class="sq"></span><span class="word">Stack</span><span class="vr"></span><span class="section">{section}</span></div><div class="tagline">{tagline}</div></div>""")


# --------------------------------------------------------------------------- Liquid helpers

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
<div class="stack">
{% if rows.size == 0 %}<div class="eyebrow">Days to meet</div>""" + empty("No sessions yet") + """{% else %}""" + DAYS_TO_MEET + """
<div><div class="eyebrow">Days to meet</div>
<div class="hero" style="margin-top:8px">{{ days }}</div></div>
<div class="sub">{{ rows[0]['meet_s'].value }}<br>{{ rows[0]['program.phase'].value }} &middot; week {{ rows[0]['program.week'].value }} &middot; day {{ rows[0]['program.day'].value }} of {{ rows[0]['program.total_days'].value }}<br><span class="faint">last trained {{ rows[0]['date_s'].value }}</span></div>
{% endif %}
</div>"""))

TOTAL_CARD = page(tok("""
<div class="stack">
{% if rows.size == 0 or rows[0]['total'].value == nil %}<div class="eyebrow">Total</div>""" + empty() + """{% else %}
<div><div class="eyebrow">Projected total</div>
<div class="hero" style="margin-top:8px">{{ rows[0]['total'].value | round }}<span class="value" style="font-size:16px;color:$DIM;margin-left:6px">lb</span></div></div>
<div><div class="sub">{{ rows[0]['lifts'].value }} lifts &middot; best e1RM each<br><span class="faint">meet max $MEET_MAX lb</span></div>
{% assign pct = rows[0]['total'].value | times: 100 | divided_by: $MEET_MAX_NUM %}{% if pct > 100 %}{% assign pct = 100 %}{% endif %}
<div class="bar"><i style="width:{{ pct }}%"></i></div>
<div class="sub" style="margin-top:4px">{{ pct | round }}% of meet max</div></div>
{% endif %}
</div>"""))

STREAK_CARD = page(tok("""
<div class="stack">
{% if rows.size == 0 %}<div class="eyebrow">Streak</div>""" + empty("No sessions yet") + """{% else %}
<div><div class="eyebrow">Streak</div>
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
<div class="sub"><span class="v">{{ rows[0]['totals.tonnage_lb'].value | round }}</span> lb &middot; <span class="v">{{ rows[0]['avg_working_rpe'].value }}</span> avg RPE &middot; <span class="v">{{ rows[0]['totals.working_sets'].value }}</span> working sets</div>
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
<div class="sub" style="margin-top:10px"><span class="v">{{ rows[0]['date_s'].value }}</span>{% if rows[0]['start_time'].value %} &middot; {{ rows[0]['start_time'].value }}{% endif %} &middot; {{ rows[0]['time_of_day'].value }} &middot; {{ rows[0]['location.name'].value }}{% if rows[0]['location.travel'].value %} <span class="chip blood">travel</span>{% endif %}<br>
<span class="faint">prev</span> {{ rows[0]['prev_session_id'].value | default: "none" }} &nbsp; <span class="faint">next</span> {{ rows[0]['next_session_id'].value | default: "none" }} &nbsp; <span class="faint">open them from the panel on the right</span></div>
{% endif %}"""))

SESSION_TILES = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty() + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Length</div><div class="value">{{ rows[0]['duration_min'].value | default: "?" }}<small>min</small></div></div><div class="sub">{{ rows[0]['streak_day'].value }} day streak</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg working RPE</div><div class="value">{{ rows[0]['avg_working_rpe'].value }}</div></div><div class="sub">{{ rows[0]['totals.working_sets'].value }} working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Sets</div><div class="value">{{ rows[0]['totals.sets'].value }}</div></div><div class="sub">{{ rows[0]['totals.reps'].value }} reps</div></div>
<div class="card"><div class="top"><div class="eyebrow">Exercises</div><div class="value">{{ rows[0]['totals.exercises'].value }}</div></div><div class="sub">{{ rows[0]['days_to_meet'].value }} days to meet</div></div>
{% endif %}
</div>"""))

TONNAGE_HERO = page(tok("""
<div class="stack">
<div><div class="eyebrow">Tonnage</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="hero blood" style="margin-top:8px">{{ rows[0]['totals.tonnage_lb'].value | round }}</div>{% endif %}</div>
<div class="sub">lb moved this session</div>
</div>"""))

CONDITIONS_CARD = page(tok("""
<div class="eyebrow">Conditions</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty() + """</div>{% else %}
<div class="grid3" style="margin-top:10px">
<div><div class="eyebrow">Temp</div><div class="value">{{ rows[0]['environment.temp_f'].value | default: "?" }}<small>F</small></div></div>
<div><div class="eyebrow">Humidity</div><div class="value">{{ rows[0]['environment.humidity_pct'].value | default: "?" }}<small>%</small></div></div>
<div><div class="eyebrow">Sky</div><div class="value">{{ rows[0]['environment.conditions'].value | default: "?" }}</div></div>
</div>
<div class="sub" style="margin-top:10px">{{ rows[0]['environment.wind'].value }}{% if rows[0]['environment.setting'].value %} &middot; {{ rows[0]['environment.setting'].value }}{% endif %}</div>
{% endif %}"""))

PERFORMANCE_CARD = page(tok("""
<div class="eyebrow">Performance</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No sets logged") + """</div>{% else %}
<div class="cols" style="margin-top:8px">
{% assign cur = "" %}{% for r in rows %}{% if r['exercise.name'].value != cur %}{% unless forloop.first %}</div>{% endunless %}{% assign cur = r['exercise.name'].value %}<div class="ex"><div class="name">{{ cur }}<span class="cat">{{ r['exercise.category'].value }}</span></div>{% endif %}
<div class="set {{ r['set_type'].value }}"><span class="n">{{ r['set_number'].value }}</span><span class="w">{% if r['load_type'].value == "bodyweight" %}BW{% else %}{{ r['weight_lb'].value | round }}{% endif %}</span><span class="x">x</span><span class="r">{{ r['reps'].value | round }}{% if r['rep_unit'].value == "walks" %} walks{% if r['distance_ft'].value %} &middot; {{ r['distance_ft'].value | round }} ft{% endif %}{% elsif r['rep_unit'].value == "seconds" %} s{% endif %}</span>{% if r['rpe'].value %}<span class="rpe">@ {{ r['rpe'].value }}</span>{% endif %}{% if r['gear_s'].value %}<span class="chip">{{ r['gear_s'].value }}</span>{% endif %}<span class="note">{{ r['notes'].value }}</span></div>
{% if forloop.last %}</div>{% endif %}{% endfor %}
</div>{% endif %}"""))

NOTES_CARD = page(tok("""
<div class="eyebrow">Notes</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No notes") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">{{ r['phase'].value }}</span><span class="txt"><span class="prose" style="color:$CHALK">{{ r['text'].value }}</span>{% if r['exercise.name'].value %} <span class="faint">{{ r['exercise.name'].value }}</span>{% endif %}{% if r['tags_s'].value %}<br>{% assign tags = r['tags_s'].value | split: "|" %}{% for t in tags %}<span class="chip">{{ t }}</span>{% endfor %}{% endif %}</span></div>{% endfor %}
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
<div class="card" style="flex:1.6"><div class="top"><div class="eyebrow">Lift</div><div class="title" style="font-size:26px;font-weight:700;text-transform:uppercase;line-height:1">{{ rows[0]['exercise.name'].value }}</div></div><div class="sub">{{ rows[0]['sessions'].value }} sessions &middot; {{ rows[0]['n'].value }} working sets &middot; last {{ rows[0]['last_s'].value }}</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best e1RM</div><div class="value">{{ rows[0]['e1'].value | round }}<small>lb</small></div></div><div class="sub">estimated, working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best top set</div><div class="value">{{ rows[0]['top'].value | round }}<small>lb</small></div></div><div class="sub">heaviest working set</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg RPE</div><div class="value">{{ rows[0]['rpe'].value | round: 1 }}</div></div><div class="sub">across working sets</div></div>
</div>{% endif %}"""))

# --------------------------------------------------------------------------- Program days, History cards, Meets, Mindset

DAYS_LIST = page(tok("""
<div class="eyebrow">Days</div>
{% if rows.size == 0 %}<div style="margin-top:10px">""" + empty("No sessions in this selection") + """</div>{% else %}
<div class="list" style="margin-top:8px">
{% for r in rows %}<div class="item"><span class="when">wk {{ r['program.week'].value }} &middot; day {{ r['program.day'].value }}</span><span class="txt">{{ r['date_s'].value }} <span class="faint">&middot; {{ r['time_of_day'].value }} &middot; {{ r['location.name'].value }}</span></span><span class="num">{{ r['totals.tonnage_lb'].value | round }} lb &middot; RPE {{ r['avg_working_rpe'].value }}{% if r['duration_min'].value %} &middot; {{ r['duration_min'].value | round }} min{% endif %}</span></div>{% endfor %}
</div>{% endif %}"""))

FOUR_CARDS = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty("No sessions in range") + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Tonnage</div><div class="value">{{ rows[0]['ton'].value | round }}<small>lb</small></div></div><div class="sub">in range</div></div>
<div class="card"><div class="top"><div class="eyebrow">Per session</div><div class="value">{{ rows[0]['avg'].value | round }}<small>lb</small></div></div><div class="sub">average</div></div>
<div class="card"><div class="top"><div class="eyebrow">Sessions</div><div class="value">{{ rows[0]['n'].value }}</div></div><div class="sub">{{ rows[0]['sets'].value }} working sets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Avg working RPE</div><div class="value">{{ rows[0]['rpe'].value | round: 1 }}</div></div><div class="sub">across sessions</div></div>
{% endif %}
</div>"""))

MEET_CARDS = page(tok("""
<div class="row">
{% if rows.size == 0 %}<div class="card">""" + empty("No meets logged") + """</div>{% else %}
<div class="card"><div class="top"><div class="eyebrow">Meets</div><div class="value">{{ rows[0]['meets'].value }}</div></div><div class="sub">competitions logged</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best total</div><div class="value" style="color:$BLOOD">{{ rows[0]['total_kg'].value | round: 1 }}<small>kg</small></div></div><div class="sub">{{ rows[0]['total_lb'].value | round: 1 }} lb</div></div>
<div class="card"><div class="top"><div class="eyebrow">Best DOTS</div><div class="value">{{ rows[0]['dots'].value | round: 2 }}</div></div><div class="sub">all meets</div></div>
<div class="card"><div class="top"><div class="eyebrow">Attempts made</div><div class="value">{{ rows[0]['made'].value }}<small>of {{ rows[0]['attempts'].value }}</small></div></div><div class="sub">{{ rows[0]['made'].value | times: 100 | divided_by: rows[0]['attempts'].value | round }}% success</div></div>
{% endif %}
</div>"""))

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
