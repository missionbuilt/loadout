#!/usr/bin/env python3
"""Generate the Ironstack Kibana dashboards as saved-object NDJSON.

    python kibana/build_dashboards.py            # writes kibana/dashboards.ndjson
    python kibana/build_dashboards.py --stdout   # prints instead

Everything is generated from one place so all panels share one style: the
Iron Log palette, the same layout grammar (hero row, tiles, charts, tables),
and one navigation graph wired with dashboard-to-dashboard drilldowns.

Fixed saved-object IDs keep drilldowns and bookmarks stable across re-imports.
Saved objects only: this runs on Elastic Cloud Serverless with no plugins.

Stdlib only. No network.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import templates as tpl  # noqa: E402
from templates import brand_bar  # noqa: E402

OUT = Path(__file__).resolve().parent / "dashboards.ndjson"

# --------------------------------------------------------------------------- Iron Log

# One palette, imported. This file used to carry its own copy of six tokens, four of
# which nothing read - and the fifth, STEEL, DISAGREED with templates.STEEL: #7a7873 here
# against #8f8b84 there. Only the templates copy is contrast-checked (verify_liquid's
# section_contrast asserts 4.5:1 on both grounds), so the copy nobody checked was the
# darker one, and any Lens panel that had reached for it would have shipped text at 3.9:1
# past a suite that believed it was checking the colour.
CHALK = tpl.CHALK
CHALK_DIM = tpl.DIM
BLOOD = tpl.BLOOD  # one accent per dashboard, never two unrelated things
STEEL = tpl.STEEL  # reference lines: a dashed grey, so the accent stays with the cards

# There is no PHASES constant any more, and that is the point.
#
# It used to be [hypertrophy, strength, peaking] with a luminance ramp along it, and
# block_timeline() turned it into three FILTERED metric columns - one per phase, each a
# literal `program.phase: "hypertrophy"` compiled into the saved object. But program.phase
# is free text: it is whatever the lifter types in their own shorthand. A lifter running
# base / accumulation / realization matched none of the three, so both block timelines
# drew nothing, under a legend naming three phases they had never used - and one of those
# two charts is Overview's only door into the Session page. The vocabulary of one author's
# programming was compiled into a public artifact exactly the way his meet total and his
# log's start month were.
#
# Lens CAN split on the field here, so it does: one metric, split by a terms bucket on
# program.phase, with missingBucket and otherBucket both on so a session with a blank
# phase or a twenty-first phase name still draws a bar and still opens. The legend is
# then whatever the lifter actually wrote, and there is no cold start to design because
# there is no state where the chart is empty but the log is not.
#
# What that costs is the fixed colour ramp: a split series takes a Lens palette, and a
# palette cannot know which of a stranger's phase names is the heavy one. "gray" is the
# same neutral ramp the Overview e1RM stack already uses for its lift split. Colour that
# means something is worth less than a chart that has the reader's own data on it.

# The Overview chart's oxblood reference line and its title. A Lens reference line is a
# static number baked into a saved object and a panel title is a string, so neither can
# read the reader's own data the way a Liquid card can. Until 2026-09-05 that number was
# 909.4 - the author's last meet total - which meant every install of this repo told a
# stranger, in the chart title and on the line, that their meet best was his.
#
# So it is optional and it comes from the environment. Unset: no reference line, and a
# title that makes no claim about a meet best. Set: today's behaviour, for the one person
# whose number it is. The card underneath (TOTAL_CARD) reads the real value out of
# workout-meets and is the honest surface for it.
def _env_float(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        sys.exit(f"error: {name} must be a number, got {raw!r}. Nothing was written.")


MEET_MAX_LB = _env_float("IRONSTACK_MEET_MAX_LB")

# --------------------------------------------------------------------------- ids

NS = uuid.UUID("6f3d3b2a-6c0e-4b2f-9a7e-1d2c3b4a5f60")


def uid(*parts: str) -> str:
    """Deterministic UUID so re-generating never changes panel or event ids."""
    return str(uuid.uuid5(NS, ":".join(parts)))


# Only the data views something actually points at. A data view is a saved object with
# an id, and an unreferenced one is an object a user has to look at in Saved Objects and
# wonder about. ironstack-dv-meets and ironstack-dv-daily were both dead: everything on
# the Meets page is a custom-content panel, and ES|QL names its own index, so neither
# needed one. check() fails if a Lens layer or a control ever asks for a view not here.
DV = {
    "sessions": ("ironstack-dv-sessions", "workout-sessions", "timestamp"),
    "sets": ("ironstack-dv-sets", "workout-sets", "date"),
    "notes": ("ironstack-dv-notes", "workout-notes", "date"),
    "weekly": ("ironstack-dv-weekly", "workout-weekly", "@timestamp"),
}

DASH = {
    "overview": "ironstack-overview",
    "program": "ironstack-program",
    "session": "ironstack-session",
    "lift": "ironstack-lift",
    "history": "ironstack-history",
    "meets": "ironstack-meets",
    "mindset": "ironstack-mindset",
}

MIGRATION = {"coreMigrationVersion": "8.8.0"}

# --------------------------------------------------------------------------- columns

FMT_INT = {"id": "number", "params": {"decimals": 0}}
FMT_1 = {"id": "number", "params": {"decimals": 1}}
# INOL is banded at 2 / 3 / 4 and the verdict card prints it to two places. At one
# place the evidence table under the card rounded 0.75 to 0.7, so a reader checking
# the card against its own table got a different number back.
FMT_2 = {"id": "number", "params": {"decimals": 2}}


def _col(label, op, dtype, scale, field=None, bucketed=False, params=None, **extra):
    col = {
        "label": label,
        "customLabel": True,   # without this Lens shows its own "Sum of totals.tonnage_lb"
        "dataType": dtype,
        "operationType": op,
        "isBucketed": bucketed,
        "scale": scale,
        "params": params or {},
    }
    if field is not None:
        col["sourceField"] = field
    col.update(extra)
    return col


def count(label="Count", fmt=None):
    c = _col(label, "count", "number", "ratio", "___records___", params={"emptyAsNull": True})
    if fmt:
        c["params"]["format"] = fmt
    return c


def metric(op, field, label, filt=None, fmt=None):
    c = _col(label, op, "number", "ratio", field, params={"emptyAsNull": True})
    if filt:
        c["filter"] = {"query": filt, "language": "kuery"}
    if fmt:
        c["params"]["format"] = fmt
    return c



def last(field, label, dtype="string", sort="date", fmt=None):
    """Last value by `sort`.

    An absent value renders as the literal string "(null)" in a Lens datatable and there
    is no way to change that. Two were tried and both are dead ends worth recording:

      * `emptyAsNull: False` is accepted, stored, and changes nothing on screen.
      * A runtime field emitting "" instead of nothing fails the panel outright —
        last_value compiles to a top_metrics aggregation, which needs doc values, and a
        runtime field has none: "top_metrics can only collect bytes that have segment
        ordinals".

    So a text column whose value is usually absent does not belong in a table. Drop it
    and show the value where it is actually present.
    """
    scale = "ratio" if dtype == "number" else "ordinal"
    c = _col(label, "last_value", dtype, scale, field, params={"sortField": sort, "showArrayValues": False})
    if fmt:
        c["params"]["format"] = fmt
    return c


def terms(field, label, size=10, dtype="string", direction="asc", by_col=None,
          missing=False, other=False):
    """A terms bucket. `missing` and `other` decide what happens to the rows it does not name.

    Both default to off, which is right for an x axis: a bar labelled "(missing value)"
    on a chart of sessions is noise. They exist for a SPLIT over a field the lifter fills
    in themselves, where off is not a display choice but a filter - a session whose
    program.phase is blank, or whose phase fell outside the top N, is dropped from the
    chart entirely. The block timeline is Overview's only door into the Session page, so
    a session it cannot colour still has to appear on it.
    """
    order_by = {"type": "column", "columnId": by_col} if by_col else {"type": "alphabetical", "fallback": True}
    return _col(
        label, "terms", dtype, "ordinal", field, bucketed=True,
        params={
            "size": size, "orderBy": order_by, "orderDirection": direction,
            "otherBucket": other, "missingBucket": missing, "parentFormat": {"id": "terms"},
            "include": [], "exclude": [], "includeIsRegex": False, "excludeIsRegex": False,
        },
    )


def date_hist(field, label="Date", interval="auto"):
    return _col(label, "date_histogram", "date", "interval", field, bucketed=True,
                params={"interval": interval, "includeEmptyRows": True, "dropPartials": False})


def static(value, label):
    return _col(label, "static_value", "number", "ratio", bucketed=False,
                params={"value": str(value)}, isStaticValue=True, references=[])


# --------------------------------------------------------------------------- layers

def layer(columns: dict, order: list[str] | None = None):
    if order is None:
        # Buckets before metrics, stable within each group. Lens resolves accessors
        # against this order; a metric listed first breaks the panel outright.
        names = list(columns)
        order = ([n for n in names if columns[n].get("isBucketed")] +
                 [n for n in names if not columns[n].get("isBucketed")])
    return {"columns": columns, "columnOrder": order, "incompleteColumns": {}, "sampling": 1}


# --------------------------------------------------------------------------- saved objects

def lens(id_, title, vtype, vis, layers: dict[str, tuple[str, dict]], query="", filters=None):
    """layers: layerId -> (data view key, layer)."""
    return {
        "id": id_,
        "type": "lens",
        "attributes": {
            "title": title,
            "description": "",
            "visualizationType": vtype,
            "state": {
                "visualization": vis,
                "query": {"query": query, "language": "kuery"},
                "filters": filters or [],
                "datasourceStates": {"formBased": {"layers": {k: v[1] for k, v in layers.items()}}},
                "internalReferences": [],
                "adHocDataViews": {},
            },
        },
        "references": [
            {"type": "index-pattern", "id": DV[v[0]][0], "name": f"indexpattern-datasource-layer-{k}"}
            for k, v in layers.items()
        ],
        **MIGRATION,
        "typeMigrationVersion": "8.9.0",
    }


XY_BASE = {
    "legend": {"isVisible": True, "position": "bottom", "shouldTruncate": True, "maxLines": 1},
    "valueLabels": "hide",
    "fittingFunction": "Linear",
    "curveType": "LINEAR",
    "emphasizeFitting": True,
    "yLeftExtent": {"mode": "full"},
    "axisTitlesVisibilitySettings": {"x": False, "yLeft": False, "yRight": False},
    "tickLabelsVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
    "labelsOrientation": {"x": 0, "yLeft": 0, "yRight": 0},
    "gridlinesVisibilitySettings": {"x": False, "yLeft": True, "yRight": False},
    "hideEndzones": True,
}


def color_mapping(terms_to_hex: dict[str, str]) -> dict:
    """Lens colour mapping for a terms split: named values get token colours, anything
    else loops the palette. This is the 9.x shape (`rules: [{type: "raw"}]`); 8.x used
    `rule: {type: "matchExactly", values: [...]}`. UNVERIFIED in the browser until the
    Phase 3 round-two walk: if the chart still paints Kibana's default blue-greys, this
    is the first thing to look at, and the fallback is the named palette beside it."""
    return {
        "assignments": [
            {"rules": [{"type": "raw", "value": term}],
             "color": {"type": "colorCode", "colorCode": hex_}, "touched": True}
            for term, hex_ in terms_to_hex.items()
        ],
        "specialAssignments": [{"rules": [{"type": "other"}], "color": {"type": "loop"}, "touched": False}],
        "paletteId": "default",
        "colorMode": {"type": "categorical"},
    }


def xy(id_, title, series, dv, columns, x, accessors, colors=None, split=None, ref=None,
       query="", legend=True, palette=None, ref_metric=None, ref_text=True, mapping=None):
    """One data layer (optionally a reference-line layer). colors: accessor -> hex.

    `ref` is a fixed number: the meet best, an ACWR of 1.0 - a line that means the same
    thing whatever is filtered. `ref_metric` is (op, field, label) and computes the line
    from the same rows the chart is drawn from, which is the only way to mark a value
    that changes with the filter. Lift needs the second kind: the verdict names this
    lift's best, and a static line would be right for one lift and wrong for the rest.
    The whole lens carries one query, so the line respects the panel filter and the
    dashboard filters alike."""
    data_layer = {
        "layerId": "l", "layerType": "data", "seriesType": series, "position": "top",
        "showGridlines": False, "xAccessor": x, "accessors": accessors,
        "yConfig": [
            {"forAccessor": a, "color": (colors or {}).get(a), "axisMode": "left"}
            for a in accessors
        ],
    }
    if palette:
        data_layer["palette"] = palette if isinstance(palette, dict) else {"type": "palette", "name": palette}
    if split:
        data_layer["splitAccessor"] = split
    if mapping:
        data_layer["colorMapping"] = color_mapping(mapping)
    layers = {"l": (dv, layer(columns))}
    vis_layers = [data_layer]
    if ref or ref_metric:
        if ref_metric:
            ref_op, ref_field, label = ref_metric
            layers["ref"] = (dv, layer({"ref": metric(ref_op, ref_field, label, fmt=FMT_INT)}))
        else:
            value, label = ref
            layers["ref"] = (dv, layer({"ref": static(value, label)}))
        vis_layers.append({
            "layerId": "ref", "layerType": "referenceLine", "accessors": ["ref"],
            "yConfig": [{
                "forAccessor": "ref", "axisMode": "left", "color": STEEL, "lineStyle": "dashed",
                "lineWidth": 2, "iconPosition": "auto", "textVisibility": ref_text, "fill": "none",
            }],
        })
    vis = {**XY_BASE, "preferredSeriesType": series, "layers": vis_layers}
    vis["legend"] = {**XY_BASE["legend"], "isVisible": legend}
    return lens(id_, title, "lnsXY", vis, layers, query=query)


def table(id_, title, dv, columns, sort=None, direction="asc", query="", page=20,
          row_height="single"):
    vis = {
        "layerId": "l", "layerType": "data",
        "columns": [{"columnId": c, "alignment": "left"} for c in columns],
        "rowHeight": row_height, "headerRowHeight": "single",
        "paging": {"size": page, "enabled": True},
    }
    if sort:
        vis["sorting"] = {"columnId": sort, "direction": direction}
    return lens(id_, title, "lnsDatatable", vis, {"l": (dv, layer(columns))}, query=query)


ZONES = [  # the Prilepin bands, light to heavy
    ("lt70", "0-69", "0-69", "#3a362f"),
    ("z70", "70-79", "70-79", "#7d7870"),
    ("z80", "80-89", "80-89", "#cfc7b6"),
    ("z90", "90+", "90+", BLOOD),
]


def zone_columns(op="sum", field="reps", fmt=FMT_INT):
    """One filtered metric column per intensity zone, coloured through yConfig.

    Not a palette. A Lens "custom" palette is a value-gradient construct — it is what
    heat_palette builds — and an XY chart splitting a series by term does not accept
    one: it rendered the panel completely blank. This is the phase_columns pattern,
    which has been colouring the block timeline correctly all along.
    """
    cols, colors = {}, {}
    for key, zone, label, color in ZONES:
        cid = f"zone-{key}"
        cols[cid] = metric(op, field, label, filt=f'prilepin_zone: "{zone}"', fmt=fmt)
        colors[cid] = color
    return cols, colors




def data_view(key):
    id_, index, time_field = DV[key]
    return {
        "id": id_,
        "type": "index-pattern",
        "attributes": {
            "title": index, "name": f"Ironstack {key}", "timeFieldName": time_field,
            "fields": "[]", "fieldAttrs": "{}", "runtimeFieldMap": "{}", "sourceFilters": "[]",
            "typeMeta": "{}", "fieldFormatMap": "{}", "allowNoIndex": True,
        },
        "references": [],
        **MIGRATION,
        "typeMigrationVersion": "8.0.0",
    }


# --------------------------------------------------------------------------- dashboards

class Inline:
    """A by-value panel (custom content, links). `key` makes the panelIndex deterministic."""

    def __init__(self, key: str, ptype: str, config: dict, refs: list[dict] | None = None):
        self.key = key
        self.ptype = ptype
        self.config = config
        self.refs = refs or []  # names are relative; the dashboard prefixes them with the panelIndex


def custom(key: str, template: str, esql: str | None = None) -> Inline:
    """Custom content panel. Liquid only runs when a query is attached.

    There is no way to scope one of these to its own time range. A `timeRange` in
    embeddableConfig is accepted, stored, survives import — and ignored; and this
    Kibana offers no "Customize time range" action for custom content OR for Lens.
    The dashboard picker reaches every panel, full stop.

    That matters because every card here defines its own window inside the ES|QL
    ("last 13 weeks", "trailing 90 days", "the latest session") and the picker is
    ANDed on top: at a 7-day range every Signal card fell back to its not-enough-data
    state while its provenance line still claimed 365 days. The fix is the dashboard
    default (see Overview's time_from) plus `windowed()` on the panels that must NOT
    see all of it.
    """
    return Inline(key, "custom_content", {"esql_query": [esql] if esql else [], "template": template,
                                          "hidePanelTitles": True})


def windowed(query: str, since: str = "now-1y") -> str:
    """Scope one panel to its own window, independently of the dashboard picker.

    A KQL date range inside the panel's own query is the only per-panel window this
    Kibana honours. Used to keep a chart readable on a dashboard whose picker has to
    be wide so the ES|QL cards can see their history.
    """
    clause = f'@timestamp >= "{since}"'
    return f"{query} and {clause}" if query else clause


# Six, not seven. `lift` is a DRILLDOWN DESTINATION and nothing else, which is what its
# own description has always said ("Arrives filtered on lift_slug", "Click a lift anywhere
# to land here"), and the nav strip was contradicting it by offering an unfiltered door.
#
# The page deliberately carries no lift_slug control - a control and a drilldown on the
# same field empty the page - so an arrival with no filter narrows nothing: li-header
# named one lift, li-signal followed whichever lift the newest session used, and li-e1rm,
# li-zones and li-sets drew every lift in the range, with the "your best in this range"
# reference line sitting at the global max. A stranger clicking LIFT got a header saying
# COMP DEADLIFT over charts of everything they had ever lifted.
#
# Closing the door is the fix; it does not make the page unreachable, because every path
# that is SUPPOSED to reach it (Overview's projected-total stack, and any lift on any
# chart) carries a lift_slug and still does. A bookmark or a back button can still land
# there cold, so li-header and li-signal say so when they do - see LIFT_HEADER and
# SIGNAL_LIFT in templates.py, and Q["lift_header"]'s LIMIT 2, which is how they know.
NAV_ORDER = ["overview", "program", "session", "history", "meets", "mindset"]

# Custom panels cannot navigate (no <a href>, no scripts in the sandbox), so a Links
# panel is the only door. It was once three grouped panels, spaced, to show hierarchy in
# the nav row; that collapsed to one full-width strip and NAV_GROUPS became a one-element
# list whose third field was destructured into `_`. Removed 2026-09-05.


# The Ironstack Coach is an Agent Builder agent and lives outside the dashboards. It is
# also the only surface the semantic layer has: five semantic_text fields are indexed and
# nothing in Kibana's own UI can reach them — a custom content panel is a sandboxed
# iframe with no scripts and no input, and the KQL bar is lexical. So the honest answer
# is a door, not a search box, and a Links panel is the only panel type that can be one.
#
# Phase 4 asked for that door to be a filled oxblood button in the brand bar. It cannot
# be: probe_links.py proved on 2026-09-05 that Kibana strips <a> out of a custom content
# panel entirely, class and all. A Links panel is styled by Kibana and offers no colour.
# So the button was made louder the only ways available - four units tall instead of two,
# on the brand row instead of sharing the nav row, and alone on that side of the page -
# and the Signal row got a line telling the reader it is there.
#
# The URL is deployment-specific, like ES_ENDPOINT, so it comes from the environment
# rather than the repo: a starter user's Kibana is not this one. Unset, the panel is
# simply not built and the nav takes the full width.
# Read once, in templates, because the CARDS need the same answer this file does: three
# strings on Mindset pointed at "the coach" in a build that has none. templates applies
# the same --check neutralisation at import time, which is when the card strings are
# baked, so the two cannot drift.
COACH_URL = tpl.COACH_URL

# The hosts a committed dashboards.ndjson is allowed to point at. Everything else is
# somebody's real deployment. One sat in this public repo, seven times over, from the
# day the coach link was built until the day someone read the artifact instead of the
# code that writes it. check() refuses to let another one through.
# Set by main() from --allow-private-coach: a lifter building this for their own
# import genuinely does point it at their own cluster, and should not be blocked. What
# must never happen silently is that build being the one that gets committed.
ALLOW_PRIVATE_COACH = False

COACH_PLACEHOLDER_HOSTS = {
    "kibana.example.com", "example.com", "www.example.com",
    "localhost", "127.0.0.1", "[::1]",
}


# A question the page can hand the coach, per dashboard. The coach is the only surface
# that can read the semantic fields, so the pages whose real question is a reading rather
# than a number get theirs pre-filled. Written as plain text: coach_destination() puts it
# in the URL's query component through urlencode, which is what does the quoting.
COACH_ASK = {
    "lift": "How has this lift been trending, and what should I do about it?",
    "mindset": "Read my training notes and tell me what keeps coming up.",
    "meets": "I am eight weeks out. What should I be watching?",
}


def coach_destination(base: str, ask: str | None) -> str:
    """`base` with `ask` in its QUERY component, whatever shape `base` is.

    The old test was `"?" in COACH_URL`, which is wrong for the URL Kibana actually
    hands you. A Kibana app URL is `https://host/app/x#/route?a=b`: the `?` lives in the
    fragment, so the naive test saw one, appended `&q=...`, and buried the parameter
    inside the fragment where the server never sees it. urlsplit knows the difference.
    """
    parts = urlsplit(base)
    if parts.scheme not in ("http", "https"):
        sys.exit(
            f"error: IRONSTACK_COACH_URL must be http or https, got {parts.scheme or '(none)'}://\n"
            f"       in {base!r}. A javascript:, data: or file: destination in a saved\n"
            "       object is a link somebody else can be sent. Nothing was written."
        )
    if not parts.netloc:
        sys.exit(f"error: IRONSTACK_COACH_URL has no host: {base!r}. Nothing was written.")
    if not ask:
        return base
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["q"] = ask
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def coach_link(current: str) -> Inline:
    # Unverified against a live Agent Builder: whether it reads ?q=. An unknown query
    # parameter is ignored by every app I have seen, so the downside is a link that works
    # without the prefill rather than a broken one.
    #
    # encode_url is True now. It was False because the ask was pre-quoted by hand; the
    # destination is now assembled by urlunsplit, which is already a valid URL, so
    # letting Kibana own the encoding is the smaller surface. NOT verified in a browser:
    # if a prefilled ask ever arrives at the coach double-encoded (%2520 for a space),
    # this flag is the first thing to look at.
    return Inline(f"coach-{current}", "links", {
        "title": "", "layout": "horizontal", "hidePanelTitles": True,
        "links": [{
            "type": "externalLink",
            "label": "ASK THE COACH",
            "destination": coach_destination(COACH_URL, COACH_ASK.get(current)),
            "order": 0,
            "options": {"open_in_new_tab": True, "encode_url": True},
        }],
    })


def links(current: str) -> Inline:
    """Kibana Links panel: the app nav. Carries neither filters nor time — each page is
    entered on its own terms."""
    items, refs = [], []
    for key in NAV_ORDER:
        link_id = uid("nav", current, key)
        # Sentence case, no brackets: Kibana underlines the current dashboard's link
        # itself, and "[ OVERVIEW ]" beside that underline was two signals for one state.
        items.append({"type": "dashboardLink", "label": key.capitalize(),
                      # use_time_range stays False on purpose. Every dashboard sets its
                      # own deliberate default (Overview 1y, Lift 2y, Meets 10y) and
                      # timeRestore cannot win against a link that carries one; visiting
                      # Meets used to leave every other page on a 10-year window.
                      # Drilldowns keep it True — clicking an old session has to carry a
                      # range wide enough to contain it.
                      # use_filters is False for the same reason use_time_range is.
                      # Verified in the browser: with comp-bench selected in Lift's control,
                      # clicking OVERVIEW pinned lift_slug: comp-bench into Overview's filter
                      # bar and the drift card ruled "Nothing is drifting. All 2 muscle groups
                      # trained inside their normal window." A leaked scope and a confident
                      # verdict — the same failure as the time picker. Drilldowns still carry
                      # filters: carrying one is the whole point of a drilldown.
                      "options": {"open_in_new_tab": False, "use_time_range": False, "use_filters": False},
                      "destinationRefName": f"link_{link_id}_dashboard"})
        refs.append({"name": f"link_{link_id}_dashboard", "type": "dashboard", "id": DASH[key]})
    # The key keeps its "-all" tail: it feeds uid(), and changing it would renumber
    # every nav panel in the artifact for no reader-visible gain.
    return Inline(f"nav-{current}-all", "links", {"title": "", "layout": "horizontal", "links": items,
                                                      "hidePanelTitles": True}, refs)


class Dashboard:
    """Collects panels row by row on Kibana's 48-column grid, in the dashboard format this
    Kibana writes itself (typeMigrationVersion 10.3.0): by-reference panels are `vis` /
    `legacy_vis` / `map` with a `{panelIndex}:savedObjectRef` reference; by-value panels carry
    their config inline; drilldowns live in `enhancements.dynamicActions.events`.

    NOT `embeddableConfig.drilldowns`. That was this repo's own invention, embeddableConfig
    is a free-form blob so Kibana stored all ten of them and read none, and check() now
    fails the build over that exact key - which this docstring went on recommending for a
    day after the fix landed."""

    PANEL_TYPE = {"lens": "vis", "visualization": "legacy_vis", "map": "map"}

    def __init__(self, key, title, description, tagline, controls=None, time_from="now-1y"):
        self.id = DASH[key]
        self.key = key
        self.title = title
        self.description = description
        self.controls = controls or []  # (data view key, field, label[, default])
        self.time_from = time_from
        self.panels: list[dict] = []
        self.refs: list[dict] = []
        self.y = 0
        self.objects: list[dict] = []  # saved objects this dashboard owns (Lens etc.)
        # chrome: brand bar + nav
        # Two units, not four (Phase 3 of the Sept 6 design plan): the bar is one line
        # now, and the coach link beside it is the same height. Four units of chrome
        # above the first verdict instead of six.
        brand = [(custom(f"brand-{key}", brand_bar(key.upper(), tagline),
                         "FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP date"),
                  38 if COACH_URL else 48, [])]
        if COACH_URL:
            brand.append((coach_link(key), 10, []))
        self.row(*brand, h=2)
        self.row((links(key), 48, []), h=2)

    def row(self, *items, h=8):
        """items: (saved object | Inline, width, drilldowns); drilldowns are
        (target key, name[, carry_time]) or ('url', template, name)."""
        x = 0
        for obj, w, drills in items:
            inline = isinstance(obj, Inline)
            idx = uid(self.id, obj.key if inline else obj["id"])
            # Drilldowns are `enhancements.dynamicActions.events`, which is the shape
            # Kibana actually reads. They were written as `embeddableConfig.drilldowns`
            # with a schema of this repo's own invention until Sept 5: embeddableConfig is
            # a free-form blob, so Kibana stored all ten of them and ignored every one.
            # The symptom was that a Lens legend offered only Filter for / Filter out and
            # never the drilldown, which made "click a lift anywhere to land here" a
            # promise the app did not keep. Verify in the browser, never in the build.
            events = []
            for d in drills:
                if d[0] == "url":
                    event_id = uid(idx, "drilldown", d[2])
                    events.append({
                        "eventId": event_id,
                        "triggers": ["VALUE_CLICK_TRIGGER"],
                        "action": {"factoryId": "URL_DRILLDOWN", "name": d[2],
                                   "config": {"url": {"template": d[1]},
                                              "openInNewTab": False, "encodeUrl": True}},
                    })
                else:
                    # (target, name[, carry_time[, carry_filters]]). carry_time governs
                    # whether the SOURCE dashboard's range travels. Session carries it —
                    # clicking an old session needs a window wide enough to hold it.
                    #
                    # It does NOT control the landing range when the click was on a date
                    # histogram. Verified in the browser: with carry_time False, clicking a
                    # week on ov-total-chart still lands Lift on Jul 7 - Jul 14, because the
                    # filter payload carries the clicked bucket's own range and that wins.
                    # So Lift is reached showing one week, reads "1 session, 4 working sets",
                    # and its verdict — which needs five sessions — cannot rule. The fix is
                    # a URL drilldown that builds a Lift URL with the lift and no range, so
                    # timeRestore gives Lift its 2y default. Not built; see ironstack-state.
                    target, name = d[0], d[1]
                    carry_time = d[2] if len(d) > 2 else True
                    # carry_filters defaults False. Every dashboard drilldown here lands on
                    # Session, which promises one session start to finish — carrying the
                    # source page's filters breaks that promise silently. Verified: clicking
                    # a point on Lift's TOP SET chart while filtered to comp-bench landed
                    # Session with BOTH lift_slug: comp-bench and session_id: 2025-03-21, so
                    # the page showed only the bench sets, the header fell back to its cold
                    # start, and PREV/NEXT read "No results found". The trigger's own filter
                    # is applied regardless; this flag governs only the source's.
                    carry_filters = d[3] if len(d) > 3 else False
                    event_id = uid(idx, "drilldown", target, name)
                    events.append({
                        "eventId": event_id,
                        # FILTER_TRIGGER only. Adding VALUE_CLICK_TRIGGER was tried against
                        # the datatable problem below and changed nothing, so it is not in
                        # the build.
                        "triggers": ["FILTER_TRIGGER"],
                        "action": {"factoryId": "DASHBOARD_TO_DASHBOARD_DRILLDOWN", "name": name,
                                   "config": {"useCurrentFilters": carry_filters,
                                              "useCurrentDateRange": carry_time,
                                              "openInNewTab": False}},
                    })
                    # Kibana extracts the target dashboard into a reference under this
                    # exact name; the panelIndex prefix is the panel-level convention.
                    ref_name = f"drilldown:DASHBOARD_TO_DASHBOARD_DRILLDOWN:{event_id}:dashboardId"
                    self.refs.append({"name": f"{idx}:{ref_name}", "type": "dashboard", "id": DASH[target]})
            if inline:
                config = dict(obj.config)
                ptype = obj.ptype
                for r in obj.refs:
                    self.refs.append({**r, "name": f"{idx}:{r['name']}"})
            else:
                config = {"title": obj["attributes"]["title"]}
                ptype = self.PANEL_TYPE[obj["type"]]
                self.refs.append({"name": f"{idx}:savedObjectRef", "type": obj["type"], "id": obj["id"]})
                self.objects.append(obj)
            if events:
                config["enhancements"] = {"dynamicActions": {"events": events}}
            self.panels.append({"type": ptype, "embeddableConfig": config, "panelIndex": idx,
                                "gridData": {"x": x, "y": self.y, "w": w, "h": h, "i": idx}})
            x += w
        self.y += h

    def build(self):
        attrs = {
            "title": self.title,
            "description": self.description,
            "panelsJSON": json.dumps(self.panels),
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False, "syncCursor": True,
                                       "syncTooltips": False, "hidePanelTitles": False,
                                       "hidePanelBorders": True, "autoApplyFilters": True}),
            "timeRestore": True, "timeFrom": self.time_from, "timeTo": "now",
            "refreshInterval": {"pause": True, "value": 60000},
            "version": 1,
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})},
        }
        refs = list(self.refs)
        if self.controls:
            panels = {}
            for order, control in enumerate(self.controls):
                dv, field, label = control[0], control[1], control[2]
                if dv not in DV:
                    # A named error, not a KeyError two frames down. The README used to
                    # promise check() caught this; check() never got the chance, because
                    # the build died here first with a bare traceback.
                    sys.exit(f"error: the {label} control on {self.key} asks for data "
                             f"view {dv!r},\n       which is not built. Add it to DV or "
                             "point the control at one that is.\n       Nothing was written.")
                default = list(control[3]) if len(control) > 3 else []
                cid = uid(self.id, "control", field)
                # Single select. Two lifts checked at once fed one blended verdict to the
                # Lift card and nothing on the page said so.
                explicit = {"id": cid, "fieldName": field, "title": label, "singleSelect": True,
                            "selectedOptions": default, "searchTechnique": "prefix",
                            "sort": {"by": "_key", "direction": "asc"}}
                if len(control) > 4:
                    explicit.update(control[4])
                panels[cid] = {"type": "optionsListControl", "order": order, "grow": False, "width": "small",
                               "explicitInput": explicit}
                refs.append({"name": f"controlGroup_{cid}:optionsListDataView", "type": "index-pattern", "id": DV[dv][0]})
            attrs["controlGroupInput"] = {
                "controlStyle": "oneLine", "chainingSystem": "HIERARCHICAL", "showApplySelections": False,
                "ignoreParentSettingsJSON": json.dumps({"ignoreFilters": False, "ignoreQuery": False,
                                                        "ignoreTimerange": False, "ignoreValidations": False}),
                "panelsJSON": json.dumps(panels),
            }
        return [*self.objects, {"id": self.id, "type": "dashboard", "attributes": attrs, "references": refs,
                                **MIGRATION, "typeMigrationVersion": "10.3.0"}]


# --------------------------------------------------------------------------- ES|QL

# How many competition lifts a card or chart will ask for. Not three - three is
# powerlifting. A strongman show runs five or six events, a weightlifting meet two,
# and until 2026-09-06 every one of those numbers was written as a literal 3 or 4 in
# three separate queries, so a lifter in any other sport lost their fourth lift with
# nothing on the page saying it had been dropped.
#
# This is a CAP on rows returned, not a count of anything: a card draws what comes
# back. The cost of a generous cap is a taller panel on a record that fills it; the
# cost of a tight one is a lift silently missing from a lifter's own dashboard.
#
# A constant rather than a read of config/exercises.json, deliberately: the build runs
# from the loadout checkout and would read the TEMPLATE taxonomy rather than the
# reader's, so a derived number would look responsive and be wrong.
COMP_LIFT_LIMIT = 8

Q = {
    "days": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL date_s = DATE_FORMAT("EEE MMM d", date), meet_s = DATE_FORMAT("EEE MMM d, yyyy", program.meet_date) | KEEP program.*, date_s, meet_s, days_to_meet',
    # The total and its three lifts come from ONE query, so the card cannot contradict
    # itself the way the old total card contradicted the e1RM tiles above it.
    # Two indices, one panel. A custom-content panel gets exactly one query, and the
    # card has to state the projected total AND what the reader's own meet best is - so
    # the query unions workout-meets in and lets one extra row carry MAX(total_lb). The
    # meet row has no lift_family, so it groups on its own and the card tells the two
    # apart by whether `fam` arrived. NULLS LAST keeps that row from winning the SORT.
    # `pts` is 1 when a meet in range was scored on points. It rides in on the meets
    # half of the union, which carries no lift_family, so it lands on the same null
    # row as meet_lb and the card reads it the same way. An integer rather than the
    # `scoring` keyword because CASE and MAX over integers is arithmetic every ESQL
    # version does the same thing with.
    #
    # `scoring IS NOT NULL` widens the union deliberately: a points meet has no
    # total_lb on any of its documents, so under the old WHERE not one of its rows
    # reached the panel and the card could not have known the sport had changed.
    "total": ('FROM workout-sets,workout-meets '
              '| WHERE (is_competition_lift == true AND set_type == "working" '
              'AND e1rm_confidence != "low" AND @timestamp >= NOW() - 90 days) '
              'OR total_lb IS NOT NULL OR scoring IS NOT NULL '
              '| EVAL p = CASE(scoring == "points", 1, 0) '
              '| STATS e1 = MAX(est_e1rm), first_d = MIN(date), meet_lb = MAX(total_lb), '
              'pts = MAX(p) '
              'BY lift_family '
              '| SORT e1 DESC NULLS LAST | LIMIT ' + str(COMP_LIFT_LIMIT) + ' '
              '| EVAL fam = lift_family | KEEP fam, e1, first_d, meet_lb, pts'),
    # unit == "kg" is the whole guard. `weight_lb` is null on a timed or a rep event by
    # design, so without it a yoke run came back as a lift with no weight and drew an
    # empty bar in a chart of platform bests.
    # BY event_name, not BY lift: `lift` is the id segment - a slug, lower case, and
    # for a strongman event a machine word like "sandbag-over-bar". event_name is what
    # the competition called it, which is what a card headed "best lifts on the
    # platform" should be printing.
    "meet_bests": ('FROM workout-meets | WHERE made == true AND unit == "kg" '
                   '| STATS lb = MAX(weight_lb), kg = MAX(weight_kg) BY event_name '
                   '| SORT lb DESC | LIMIT ' + str(COMP_LIFT_LIMIT)),
    "watch": 'FROM workout-sessions | WHERE watch_items IS NOT NULL | SORT @timestamp DESC | LIMIT 12 | MV_EXPAND watch_items | EVAL date_s = DATE_FORMAT("MMM d", date), item = watch_items | KEEP date_s, item',
    "program_header": 'FROM workout-sessions | EVAL wd = program.week * 100 + program.day | STATS n = COUNT(*), wd_max = MAX(wd), last_day = MAX(date) BY program.name, program.block, program.phase, program.total_days, program.meet_date | SORT last_day DESC | LIMIT 1 | EVAL program.week = FLOOR(wd_max / 100), program.day = wd_max % 100, date_s = DATE_FORMAT("EEE MMM d", last_day), meet_s = DATE_FORMAT("EEE MMM d, yyyy", program.meet_date)',
    "session_header": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL date_s = DATE_FORMAT("EEEE, MMM d, yyyy", date) | KEEP program.*, date_s, start_time, time_of_day, location.name, location.travel, prev_session_id, next_session_id',
    "session_tiles": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP duration_min, streak_day, avg_working_rpe, totals.*, days_to_meet',
    "top_set": ('FROM workout-sets '
                '| WHERE set_type == "working" AND weight_lb > 0 AND (rep_unit IS NULL OR rep_unit == "reps") '
                # main_rank, not a WHERE: a session with no main-lift work still needs a top set.
                # Sorted on weight alone the hero was whatever was heaviest that day, which on
                # 2026-05-13 was a 300 lb calf raise standing over a session of squats. The
                # timestamp stays the primary key so the historical scan below is unaffected.
                '| EVAL main_rank = CASE(exercise.category == "main", 0, 1) '
                '| SORT @timestamp DESC, main_rank ASC, weight_lb DESC, reps DESC '
                '| LIMIT 900 '
                '| EVAL date_s = DATE_FORMAT("MMM d", date) '
                # est_e1rm and its confidence: the card compares two sets at different rep
                # counts and e1RM is the only thing that makes them comparable. Projected
                # rather than recomputed in Liquid - the model is an RPE lookup table.
                '| KEEP session_id, date_s, lift_slug, exercise.name, weight_lb, reps, rpe, '
                'est_e1rm, e1rm_confidence'),
    "conditions": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP environment.*, time_of_day',
    "performance": 'FROM workout-sets | SORT @timestamp DESC, seq ASC | LIMIT 500 | EVAL gear_s = MV_CONCAT(gear, " / ") | KEEP session_id, set_number, exercise.name, exercise.category, set_type, load_type, weight_lb, reps, rep_unit, distance_ft, rpe, gear_s, notes',
    # WHERE phase != "watch": WRAP_CARD renders watch items in its own block, so
    # including them here printed the same sentence twice on the Session page.
    "notes": 'FROM workout-notes | WHERE phase != "watch" | SORT @timestamp DESC, order ASC | LIMIT 200 | EVAL tags_s = MV_CONCAT(tags, "|") | KEEP session_id, order, phase, exercise.name, text, tags_s',
    "wrap": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL watch_s = MV_CONCAT(watch_items, "|") | KEEP wrap_up, gear_notes, watch_s',
    # name comes from lift_name, the taxonomy's canonical, not exercise.name. The raw
    # logged spelling is whatever was typed that day, which is why this header read
    # COMPETITION DEADLIFT for one lift and COMP BENCH for another while both pages
    # claimed to be the same kind of page. Aliases already resolve onto one canonical,
    # so the name now matches the slug rather than the keystrokes.
    # LIMIT 2, not 1, and the second row is never rendered. It is how the header knows
    # whether this page was entered on a lift: with a lift_slug filter exactly one group
    # comes back, without one at least two do (for any lifter who trains more than a
    # single competition lift), and a custom-content panel has no other way to see the
    # filter bar. LIMIT 1 threw that away and the cold start was unwritable.
    "lift_header": 'FROM workout-sets | WHERE set_type == "working" AND is_competition_lift == true | EVAL e1c = CASE(e1rm_confidence == "low", 0.0, est_e1rm) | STATS e1 = MAX(e1c), top = MAX(weight_lb), rpe = AVG(rpe), n = COUNT(*), sessions = COUNT_DISTINCT(session_id), last_day = MAX(date), name = MAX(lift_name) BY lift_slug | SORT last_day DESC | LIMIT 2 | EVAL last_s = DATE_FORMAT("MMM d, yyyy", last_day)',
    "meet_cards": 'FROM workout-meets | EVAL m = CASE(made, 1, 0), p = CASE(scoring == "points", 1, 0) | STATS meets = COUNT_DISTINCT(meet_id), total_kg = MAX(total_kg), total_lb = MAX(total_lb), dots = MAX(dots), made = SUM(m), attempts = COUNT(*), pts = MAX(p), best_place = MIN(placing), best_points = MAX(points)',
    # event_no is the running order off the record. It was CASE(lift == "squat", 1,
    # lift == "bench", 2, 3) - a running order for one sport, which put every event of
    # every other sport in third place together.
    "meet_list": 'FROM workout-meets | EVAL date_s = DATE_FORMAT("MMM d, yyyy", date) | SORT date DESC, event_no ASC, attempt_no ASC | LIMIT 300 | KEEP meet_id, date_s, total_kg, dots, bodyweight_kg, placing, points, event_name, event_no, unit, value, attempt_no, made',
    # The coverage line under each intensity-zone chart. `zoned` carries the set's reps
    # when it has a zone and 0.0 when it does not, so the two sums are directly
    # comparable and the card can say "n of m" without a second query.
    "zone_cov_main": ('FROM workout-sets '
                      '| WHERE set_type == "working" AND exercise.category == "main" '
                      '| EVAL zoned = CASE(prilepin_zone IS NOT NULL, reps, 0.0) '
                      '| STATS zr = SUM(zoned), tr = SUM(reps) | KEEP zr, tr'),
    # The Lift page charts every working set of the lift it was entered on, not just
    # the main-lift ones, so its coverage line has to count the same population.
    "zone_cov_lift": ('FROM workout-sets | WHERE set_type == "working" '
                      '| EVAL zoned = CASE(prilepin_zone IS NOT NULL, reps, 0.0) '
                      '| STATS zr = SUM(zoned), tr = SUM(reps) | KEEP zr, tr'),
    "recent_notes": 'FROM workout-notes | SORT @timestamp DESC, order ASC | LIMIT 12 | EVAL date_s = DATE_FORMAT("MMM d", date), tags_s = MV_CONCAT(tags, "|") | KEEP date_s, phase, exercise.name, text, tags_s',
    # Signal cards. NOTE: `first` and `last` are reserved words in ES|QL — an alias
    # named either fails with "no viable alternative at input". That is what broke
    # lift_header on Sept 4, misdiagnosed then as the CASE shifting the parse.
    #
    # COALESCE on every Prilepin bucket: a null bucket would null the whole sum and
    # silently drop the week out of the ranking.
    # The three Overview verdicts read ironstack-signals, not the live indices.
    #
    # That index carries no date-typed field, which is the whole point: Kibana applies the
    # dashboard range to an ES|QL card by filtering on the index's date field, so with none
    # there is nothing to filter on and the picker cannot re-scope a verdict. Verified in
    # the browser on Sept 5 (kibana/probe_notime.py): at Last 15 minutes a card on a no-date
    # index returned every row while a control on workout-sessions returned zero.
    #
    # The rows are windowed by derive.signal_docs() at index time - 365 days for drift, 13
    # weeks for intensity - and shaped to match what these queries used to return, so the
    # templates keep their arithmetic. What they lose is the Phase 0 span check, which
    # existed to notice a picker that is now unreachable.
    #
    # Still reachable: a filter. A KQL query on a field this index does not have matches
    # nothing and empties the card, so the zero-row state names that possibility instead of
    # claiming there is no data.
    # training_days and heavy_per_training_day are not decoration: an open week has
    # fewer days in it than the weeks it is ranked against, and the card ranks the rate
    # while week_state is in-progress. They were emitted by derive.py and left out of
    # this KEEP for a day, which left the card ranking raw counts with a "still open"
    # caption underneath - a note where a correction was needed.
    "sig_intensity": ('FROM ironstack-signals | WHERE signal == "intensity" '
                      '| SORT week_end DESC | LIMIT 13 '
                      '| KEEP iso_week, week_end, week_state, weeks_available, '
                      'training_days, heavy_per_training_day, heavy, tot, '
                      'computed_through'),
    # acwr_off_layoff and chronic_days_trained are read by the comeback branch in
    # templates._LOAD_BODY. They were not in this KEEP, so `off` was always nil, the
    # branch could not fire, and eight tests in verify_liquid passed over the gap because
    # their fixture invented both columns. That class of bug is now linted in check().
    #
    # layoff_min_training_days is the bar chronic_days_trained is judged against, and it
    # is the lifter's own rather than a constant, so the card could not name it while it
    # lived only in derive.py. It is on the load row now, so the sentence that said
    # "Only N of the last 28 days" without saying under what finally can.
    #
    # load_window_end and week_end are BOTH projected, and the card is only interesting
    # because they differ: week_end is the last day trained, load_window_end is the day
    # the 7- and 28-day windows were measured back from (the week's own end, or today
    # while it is open). That gap is why the ratio moves on a rest day, and until derive
    # carried the second one onto this row the card could only state it as a rule.
    # keyword, not date, on both: ironstack-signals deliberately carries no date-typed
    # field, because that is what stops the dashboard time picker re-scoping a verdict.
    # So they arrive as strings and are compared as strings, which is exact for ISO dates
    # and needs no parsing in a template.
    "sig_load": ('FROM ironstack-signals | WHERE signal == "load" '
                 '| SORT week_end DESC | LIMIT 200 '
                 '| KEEP iso_week, week_end, load_window_end, month_s, acwr, acwr_band, '
                 'monotony, acwr_off_layoff, chronic_days_trained, '
                 'layoff_min_training_days, computed_through'),
    # `rankable` is the INDEXER's answer to "can this group's gap be read", and the card
    # honours it rather than re-deriving one - the same rule weeks_available established
    # on the intensity card. It is projected now because a drift row can arrive with no
    # cadence_days at all, and "no cadence" and "cadence too unstable to rank" are the
    # same verdict from the card's side but only the indexer can tell them apart. Absent,
    # the card falls back to its own test, so an older index still reads correctly.
    "sig_drift": ('FROM ironstack-signals | WHERE signal == "drift" '
                  '| SORT last_trained ASC | LIMIT 40 '
                  '| KEEP muscle, sessions, last_trained, cadence_days, rankable, '
                  'computed_through'),
    # SORT cycle DESC so the newest meets win the LIMIT rather than the oldest, and
    # weeks_out DESC so a cycle's rows arrive furthest-out first - the card reads the
    # last closed row it sees as the most recent week and depends on that order.
    "sig_program": ('FROM ironstack-signals | WHERE signal == "load" '
                    '| SORT week_end DESC | LIMIT 60 '
                    '| KEEP week_end, block, inol_hardest, inol_hardest_lift, '
                    'inol_hardest_band, inol_hardest_gloss, acwr, acwr_band, acwr_gloss, '
                    'computed_through'),
    # Every block run, oldest last. LIMIT 200 rather than a tighter one on purpose: the
    # peer median is computed at index time, but the card still has to FIND the current
    # block among these rows, and a limit that drops it turns the card off silently.
    "sig_block": ('FROM ironstack-signals | WHERE signal == "block" '
                  '| SORT ordinal ASC | LIMIT 200 '
                  '| KEEP block, ordinal, block_role, first_trained, sessions, heavy, '
                  'main_reps, heavy_per_session, share_pct, peers, peer_heavy_per_session, '
                  'peer_share_pct, peer_from, peer_window_sessions, computed_through'),
    "sig_projection": ('FROM ironstack-signals | WHERE signal == "projection" '
                       '| SORT cycle ASC | LIMIT 40 '
                       '| KEEP cycle, cycle_label, cycle_role, projected_total_lb, '
                       'meet_total_lb, platformed_pct, peers, peer_pct, expected_lb, '
                       'peer_from, peer_to, scoring, discipline, computed_through'),
    # recent DESC puts the tag the card leads with in row 0; the corpus span it checks
    # first is denormalised onto every row, so row 0 answers both questions.
    "sig_tags": ('FROM ironstack-signals | WHERE signal == "tag" '
                 '| SORT recent DESC, total DESC | LIMIT 25 '
                 '| KEEP tag, total, recent, prior, last_trained, window_days, '
                 'notes_total, notes_from, notes_span_days, computed_through'),
    "sig_taper": ('FROM ironstack-signals | WHERE signal == "taper" '
                  '| SORT cycle DESC, weeks_out DESC | LIMIT 80 '
                  '| KEEP cycle, cycle_label, cycle_role, week_state, weeks_out, '
                  'attempts_made, attempts_total, training_days, tonnage_lb, '
                  'avg_working_rpe, cum_weeks, cum_tonnage_lb, cum_heavy, computed_through'),
    # LIMIT 1000, not 200, and the Liquid still filters to one lift. Both halves have
    # a reason.
    #
    # A dashboard filter DOES reach an ES|QL panel - that is why the signals index was
    # built with no date field (the picker cannot filter what is not there) while the
    # note beside it records that a KQL query on a missing field still empties the card.
    # So when Lift is entered the way it is meant to be, by drilldown, `lift_slug` is in
    # the app filter array and these rows are already one lift. There is nothing left to
    # push down: the filter is the dashboard's, not ours, and Lift deliberately carries
    # no control of its own to push (see the Dashboard call below).
    #
    # The Liquid-side filter exists for the OTHER arrival - the nav strip, which carries
    # no filter - where the query returns every lift the log has. 200 session/lift pairs
    # across 30 exercises is under 7 sessions each, so a lifter with fifty was told the
    # card needs five. 1000 pairs is ~250 sessions of history at four lifts a session,
    # which covers this page's 2y default with room, and is a fraction of the 10,000-row
    # ES|QL ceiling.
    "sig_lift": ('FROM workout-sets '
                 '| WHERE set_type == "working" AND e1rm_confidence != "low" '
                 'AND est_e1rm IS NOT NULL '
                 '| STATS e1 = MAX(est_e1rm), sess_d = MAX(date) BY session_id, lift_slug '
                 '| SORT sess_d DESC | LIMIT 1000 '
                 '| EVAL when_s = DATE_FORMAT("MMM yyyy", sess_d) '
                 '| KEEP session_id, lift_slug, when_s, e1'),
}

# The indices this app is allowed to read. Six are written by the log's own indexer and
# ironstack-signals by derive.signal_docs; a FROM naming anything else is a query against
# an index the pipeline does not create, which imports cleanly and renders an error.
INDICES = {
    "workout-sessions", "workout-sets", "workout-notes", "workout-meets",
    "workout-daily", "workout-weekly", "ironstack-signals",
}

FROM_CLAUSE = re.compile(r"\bFROM\s+([A-Za-z0-9_,.*-]+)")

# ---------------------------------------------------------------- timezone
#
# IRONSTACK_TZ shifts Liquid's "now" arithmetic, through the $TZ_OFF token, and NOTHING
# ELSE. In particular it must never touch a DATE_FORMAT in a query here.
#
# It briefly did, and the reasoning was wrong in a way worth writing down. The premise
# was "a session logged at 8pm Sunday in Denver prints as Monday", which is a real bug
# about instants - but every DATE_FORMAT below formats a CALENDAR DATE, never an
# instant: `date`, `program.meet_date`, `MAX(date)`. Those are the lifter's own typed
# YYYY-MM-DD, indexed at midnight UTC, and already correct. Subtracting an offset from
# midnight moves them to the previous day, so a session logged 2026-09-05 rendered
# "Fri Sep 4" for every user west of Greenwich - and rendered correctly east of it,
# because midnight plus five and a half hours is still the same day. Silently right in
# India, silently wrong in Denver, in the feature the README tells you to configure.
#
# `@timestamp` is the field that IS an instant, and index_workouts.timestamp_for already
# writes it with the session's own offset. It is never formatted here, which is why
# there was never anything to fix. check() enforces both halves of that: no DATE_FORMAT
# may name @timestamp, and none may carry a seconds shift.

DATE_FORMAT_CALL = re.compile(r'DATE_FORMAT\("([^"]+)",\s*([A-Za-z0-9_.@]+)\s*\)')
DATE_FORMAT_ARG = re.compile(r'DATE_FORMAT\("[^"]+",\s*([A-Za-z0-9_.@]+)')
DATE_FORMAT_SHIFTED = re.compile(r'DATE_FORMAT\("[^"]+",\s*[A-Za-z0-9_.@]+\s*[+-]\s*\d+\s*second')


# --------------------------------------------------------------------------- shared Lens panels

SESSION_URL = (
    "{{kibanaUrl}}/app/dashboards#/view/" + DASH["session"] +
    "?_g=(time:(from:'{{context.panel.timeRange.from}}',to:'{{context.panel.timeRange.to}}'))"
    "&_a=(filters:!((meta:(alias:!n,disabled:!f,key:session_id,negate:!f,params:(query:'{{event.value}}'),type:phrase),"
    "query:(match_phrase:(session_id:'{{event.value}}')))))"
)


# points.1, not event.value. On a date histogram the first point is the x dimension, so
# {{event.value}} resolved to the clicked week as an epoch — the first build of this URL
# filtered lift_slug to 1751860800000 and found nothing. SESSION_URL gets away with
# {{event.value}} because its x axis IS session_id. Here x is the week and the split is
# the lift, so the lift is the second point.
#
# No _g at all, deliberately. A dashboard drilldown from a date histogram sets the
# target's range to the clicked bucket — verified: clicking a week landed Lift on seven
# days, where a verdict that needs five sessions cannot rule. A URL that names no range
# lets Lift's own timeRestore give it the 2y default it was built for.
LIFT_URL = (
    "{{kibanaUrl}}/app/dashboards#/view/" + DASH["lift"] +
    "?_a=(filters:!((meta:(alias:!n,disabled:!f,key:lift_slug,negate:!f,params:(query:'{{event.points.1.value}}'),type:phrase),"
    "query:(match_phrase:(lift_slug:'{{event.points.1.value}}')))))"
)


def block_timeline(id_, title="Block timeline", query=""):
    """Every session as a bar, coloured by whatever the lifter calls the phase.

    The split is the field, not a fixed column set - see the note where PHASES used to
    be. size=20 with otherBucket on is belt and braces: twenty distinct phase names is
    already more vocabulary than a program has, and anything past it lands in Other
    rather than falling off the chart and taking the drilldown with it.

    The drilldown is unaffected by the split. SESSION_URL reads {{event.value}}, which
    is the FIRST point of the click - the x dimension - and x is still session_id;
    LIFT_URL's comment records the same ordering from the other side.
    """
    columns = {
        # Not larger. 1000 was tried on 2026-09-06 to fix an apparent truncation on
        # Overview and the browser refuted it: that panel stops a year back because
        # windowed() scopes it to now-1y, and the only thing a bigger bucket did was pull
        # in sessions with no program.phase, which missingBucket renders as the literal
        # "(null)" and which pushed the split to four series - moving the gray palette off
        # the beige ramp and onto blue-grey. Reverted, and recorded so it is not tried again.
        "x": terms("session_id", "Session", size=300),
        "phase": terms("program.phase", "Phase", size=20, missing=True, other=True),
        "m": metric("sum", "totals.tonnage_lb", "Tonnage", fmt=FMT_INT),
    }
    return xy(id_, title, "bar_stacked", "sessions", columns, "x", ["m"],
              split="phase", palette="gray", query=query)


def sessions_table(id_, title="Sessions"):
    columns = {
        "sid": terms("session_id", "Session", size=200, direction="desc"),
        "block": last("program.block", "Block"),
        "loc": last("location.name", "Where"),
        "ton": last("totals.tonnage_lb", "Tonnage", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "Avg RPE", "number", fmt=FMT_1),
    }
    return table(id_, title, "sessions", columns, sort="sid", direction="desc")


def notes_table(id_, title, size=20):
    """A session index, not a second telling of the notes beside it.

    Dropped `#`, `EXERCISE` and `PHASE`. `#` was the note's internal sort key, so watch
    items rendered as "1,001" — a sort key with a thousands separator, read as an
    ordinal. `EXERCISE` is null on every pre, wrap-up and watch note. `PHASE` was worse
    than either: `last(phase)` picks one of a session's notes, so a day with a pre, a
    wrap-up and a watch note reported a single phase as though that were the note.

    What is left is a session and how many notes it holds — true for every row. This
    panel exists only because a custom content panel cannot navigate; RECENT NOTES
    beside it already shows the content in prose.
    """
    columns = {
        "sid": terms("session_id", "Session", size=size, direction="desc"),
        "n": count("Notes", fmt=FMT_INT),
    }
    return table(id_, title, "notes", columns, sort="sid", direction="desc", page=50)


# --------------------------------------------------------------------------- build

def build() -> list[dict]:
    objs: list[dict] = [data_view(k) for k in DV]
    S, T, N, W = "sessions", "sets", "notes", "weekly"
    L = lambda name: f"ironstack-lens-{name}"  # noqa: E731

    # ---------------------------------------------------------------- Overview
    # time_from is 2y on purpose, and it is a compromise. Every ES|QL card here carries
    # its own window and the picker is ANDed on top of it, so a narrow default silently
    # guts them: at the old 1y default the load card's "no earlier week in this band"
    # really meant "none in the last year". A 10y default fixes the cards and wrecks the
    # charts — windowed() filters rows but not the axis, so the weekly e1RM histogram
    # drew one year of bars against nine years of empty axis. 2y satisfies every card
    # (13 weeks, 90 days, 365 days, 104 weeks of precedent) and still plots cleanly.
    d = Dashboard("overview", "Ironstack. Overview",
                  "Heavy means heavy for you now. Intensity is measured against your best in the last 90 days.",
                  # The most defensible idea in the system, said out loud instead of in
                  # 10px grey at the bottom of one card. Every logging app compares a set
                  # to an all-time PR, which tells a lifter coming back from a layoff
                  # that everything is light. This one compares to current form.
                  "Heavy means heavy for you now. Intensity is measured against your best "
                  "in the last 90 days, not an all-time max.",
                  time_from="now-2y")
    # The Signal row leads. Mike's framing: the analysis has to be the first thing on
    # the page or the app reads as a log with charts bolted on. Everything below this
    # row is the log, in descending order of how often it answers a question.
    # Signal-card heights are MEASURED, not estimated. Every one of these was set a row
    # short on the first try and corrected against the browser: a card that slices its
    # own pointer line is the defect the height exists to prevent, and it is not visible
    # from the source. History still takes 10 because its evidence line runs long before
    # the paragraph starts.
    #
    # 9, and it was 8 for one build. The 11 before that was sized for a ~45-word method
    # paragraph wrapping to five or six lines inside a 16-column card; that paragraph
    # moved to SIGNAL_METHOD at the foot of the page and a one-line scope replaced it,
    # so rows came out with it. Subtracting the paragraph's lines from the old height
    # said 6; the browser said 8 was still a row short, and sliced the intensity card's
    # SEE HISTORY line in half.
    #
    # Three cards share one height, so the height belongs to the TALLEST STATE of the
    # tallest card, which is intensity mid-week: the open-week branch adds two lines
    # ("this week is still open, so it is ranked on heavy reps per training day") that
    # neither of the other two ever carries. Measured against a closed week this fits at
    # 8 and clips every Tuesday.
    d.row((custom("ov-sig-intensity", tpl.SIGNAL_INTENSITY, Q["sig_intensity"]), 16, []),
          (custom("ov-sig-load", tpl.SIGNAL_LOAD, Q["sig_load"]), 16, []),
          (custom("ov-sig-drift", tpl.SIGNAL_DRIFT, Q["sig_drift"]), 16, []), h=9)
    # The coach line that sat here is gone (Phase 4): one iframe fewer on the first
    # screen, and its sentence rides on the method panel's heading at the foot.
    # Watch items sit directly under the verdicts, on purpose. The drift card says
    # calves; these say grip, deadlift, lower back. Both are true — one measures volume
    # gaps, the other records what the lifter actually felt — and a lifter trusts the
    # thing he wrote himself. Nothing reconciles them and nothing should pretend to:
    # putting them adjacent makes the disagreement the point instead of an accident of
    # spacing. (A computed "recurring themes" card was considered and rejected: the note
    # corpus is ~28 documents and the real topic tags sit at 3-4 over a year.)
    d.row((custom("ov-watch", tpl.WATCH_CARD, Q["watch"]), 32, []),
          (custom("ov-days", tpl.DAYS_TO_MEET_CARD, Q["days"]), 16, []), h=11)
    # No reference line and no number in the title unless IRONSTACK_MEET_MAX_LB says
    # what it is. A Lens saved object cannot compute either from the reader's data; the
    # card to its left can, and does.
    total_title = "Projected total by week"
    if MEET_MAX_LB is not None:
        total_title = f"Projected total by week, against your meet best of {MEET_MAX_LB:g} lb"
    d.row((custom("ov-total", tpl.TOTAL_CARD, Q["total"]), 20, []),
          # Stacked, so the top edge is the projected total week by week and the dashed
          # line is the platform best. The old title said "e1RM" and nothing on the
          # panel said the stack meant anything; a lifter read it as three noisy bars.
          # Area instead of bars: the fitting function bridges weeks a lift was not
          # trained, so the edge reads as a line and not a picket fence.
          (xy(L("ov-total-chart"), total_title,
              "area_stacked", T,
              {"x": date_hist("date", "Week", "1w"), "lift": terms("lift_slug", "Lift", size=COMP_LIFT_LIMIT),
               "m": metric("max", "est_e1rm", "BEST e1RM", fmt=FMT_INT)},
              "x", ["m"], split="lift", palette="gray",
              # Token colours by lift slug, the three chalks, brightest on the biggest
              # lift. The slugs are the reader's own competition lifts, from
              # config/exercises.json; a lift not named here loops the gray palette.
              mapping={"comp-deadlift": CHALK, "comp-squat": CHALK_DIM, "comp-bench": STEEL},
              ref=(MEET_MAX_LB, "Meet best") if MEET_MAX_LB is not None else None,
              ref_text=False,
              query='is_competition_lift: true and set_type: "working" and not e1rm_confidence: "low"'),
           28, [("url", LIFT_URL, "Lift")]), h=13)
    # Streak, Latest session, Bodyweight and Sleep were cut from this page. Every one is
    # something a phone logging app shows better and shows at the gym, so here they only
    # told a lifter that Ironstack is a worse Strong. Bodyweight and Sleep also had one
    # reading between them in seven years of logs.
    # The block timeline stays as the door into a session. It is ~400 bars and is not
    # readable as a chart, which is why it is no longer above the fold.
    d.row((block_timeline(L("ov-timeline"), query=windowed("")), 48, [("session", "Session")]), h=10)
    # Last on the page, and three columns wide so each one sits under the card it
    # explains. The verdicts lead; the mechanism is one scroll down, in full, in one
    # place where the three windows can be read against each other. It takes no query -
    # it carries no number, because every figure on this page is computed by the cards.
    # 7, and it was 6 for one build: at 6 the intensity column died mid-sentence on
    # "heavy here and easy there - that". Its paragraph is the longest of the three, so
    # the height belongs to that column - the same rule as the row of cards above, one
    # panel further down the page.
    d.row((custom("ov-method", tpl.SIGNAL_METHOD), 48, []), h=7)
    objs += d.build()

    # ---------------------------------------------------------------- Program
    d = Dashboard("program", "Ironstack. Program", "Block, week, day. Pick a week, open a day.",
                  "The block, week by week. Program tracking is newer than the log, so "
                  "sessions from before it carry no week or day and do not appear above.",
                  controls=[(S, "program.block", "Block"), (S, "program.week", "Week")])
    d.row((custom("pr-header", tpl.PROGRAM_HEADER, Q["program_header"]), 48, []), h=4)
    # INOL and ACWR in words, above the table of decimals they explain.
    d.row((custom("pr-sig", tpl.SIGNAL_PROGRAM, Q["sig_program"]), 48, []), h=9)

    # One table, not two. WEEKS IN THE TRACKED PROGRAM held a single row above a panel of
    # empty space - program.week is populated on 4 sessions out of 643 - and the only
    # thing it did that this table cannot is filter by week, which the WEEK control above
    # already does.
    #
    # Carrying the week over as a column here was tried and reverted: last_value renders
    # an absent value as the literal "(null)" and there is no way to change that (see
    # last()), so a WEEK column would print "(null)" on 639 rows. A near-empty table
    # replaced by a near-empty column is not a cut.
    days_cols = {
        "sid": terms("session_id", "Session", size=100, direction="desc"),
        # No DATE column: session_id is the date, and a date field renders in the
        # browser timezone, showing the previous evening. No DAY column either:
        # program.day is null on everything logged before the program was tracked.
        "ton": last("totals.tonnage_lb", "Tonnage", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "Avg RPE", "number", fmt=FMT_1),
    }
    d.row((table(L("pr-days-table"), "Days in the range", S, days_cols,
                 sort="sid", direction="desc", page=25), 48, [("session", "Session")]), h=10)
    # HARDEST LIFT and INOL are both derived from the per-set `inol`, which exists only
    # where the set has a relative intensity - so on a log with no RPE in it they are
    # absent on every week and last_value renders the keyword one as the literal
    # "(null)" (see last(); there is no way to change that). The columns stay anyway:
    # dropping them would take the loading table's whole subject away from the lifter
    # who DOES log RPE, and the card directly above this panel - SIGNAL_PROGRAM's
    # no-inol branch, "INOL needs a working set on a lift with history behind it" -
    # already stands between the reader and an unexplained column of nulls. This is the
    # one place in these pages where the honest explanation is in an adjacent panel
    # rather than in the panel itself, and it is here because a Lens datatable cannot
    # carry one.
    loading_cols = {
        "week": terms("iso_week", "Week", size=60, direction="desc"),
        "lift": last("inol_hardest_lift", "Hardest lift", sort="@timestamp"),
        "inol": last("inol_hardest", "INOL", "number", sort="@timestamp", fmt=FMT_2),
        # BAND and LOAD were words restating the number beside them ("0.4  easy").
        "acwr": last("acwr", "ACWR", "number", sort="@timestamp", fmt=FMT_1),
        "ton": last("tonnage_lb", "Tonnage", "number", sort="@timestamp", fmt=FMT_INT),
    }
    d.row((table(L("pr-loading"), "Weekly loading", W, loading_cols,
                 sort="week", direction="desc", page=12), 48, []), h=10)
    # The mechanism behind the verdict card, last on the page (Phase 2 of the Sept 6
    # design plan): the card keeps one scope line and the method paragraph lives here,
    # where it can be read in full. Height is a first guess for a one-column paragraph;
    # MEASURE it in the browser like every other custom-panel height on this page.
    d.row((custom("pr-method", tpl.PROGRAM_METHOD), 48, []), h=4)
    objs += d.build()

    # ---------------------------------------------------------------- Session
    d = Dashboard("session", "Ironstack. Session", "One session. Arrives filtered to a session_id.",
                  "One session, start to finish. Click any session anywhere to land here, "
                  "or use PREV and NEXT to walk. With no session chosen this is the latest one.")
    # A Lens table of nothing but buckets renders no rows; the hidden count gives it one.
    nav_cols = {"sid": terms("session_id", "Session", size=1, direction="desc"),
                "prev": last("prev_session_id", "Prev", sort="timestamp"),
                "next": last("next_session_id", "Next", sort="timestamp")}
    nav = table(L("se-nav"), "Prev / next", S, nav_cols, sort="sid", direction="desc")
    d.row((custom("se-header", tpl.SESSION_HEADER, Q["session_header"]), 36, []),
          (nav, 12, [("url", SESSION_URL, "Open session")]), h=6)
    d.row((custom("se-top", tpl.TOP_SET_HERO, Q["top_set"]), 22, []),
          (custom("se-tiles", tpl.SESSION_TILES, Q["session_tiles"]), 26, []), h=5)
    # 5 and 16, measured 2026-09-06 (round two): the hero row carried two units of
    # ground under the top set at 7, and the performance card for a six-exercise
    # session scrolled its last set off the bottom at 15.
    d.row((custom("se-perf", tpl.PERFORMANCE_CARD, Q["performance"]), 48, []), h=16)
    d.row((custom("se-notes", tpl.NOTES_CARD, Q["notes"]), 32, []),
          (custom("se-wrap", tpl.WRAP_CARD, Q["wrap"]), 16, []), h=11)
    d.row((custom("se-cond", tpl.CONDITIONS_CARD, Q["conditions"]), 48, []), h=5)
    objs += d.build()

    # ---------------------------------------------------------------- Lift
    d = Dashboard("lift", "Ironstack. Lift", "One exercise over time. Arrives filtered on lift_slug.",
                  "One exercise over time. Click a lift anywhere to land here.",
                  # No control on lift_slug. Lift is a drilldown destination, and a control
                  # and a drilldown filtering the same field empty the page: the drilldown
                  # replaces the app filter array, the control's filter sits outside it, and
                  # the two AND. That is the Session bug, reproduced here on Sept 5 the hour
                  # the drilldowns started working — arriving from Overview with the control
                  # still holding comp-deadlift gave a filter pill, an invalid-selection
                  # warning and an empty page. Lift takes its identity from whatever brought
                  # the lifter here, and nothing else.
                  #
                  # A FAMILY control on lift_family was tried first and removed for the same
                  # reason. Sorting a lift picker by count does not put the competition lifts
                  # on top either (single-leg-calf-raises 300, unknown-exercise 261,
                  # comp-bench 208): count is the wrong proxy. If a picker comes back, it
                  # needs the lift_name display field from the Phase 1 reindex AND a page
                  # that is not a drilldown target.
                  #
                  # BLOCK stays: it filters program.block, so ANDing it with an incoming
                  # lift_slug filter asks a real question (this lift, in that block) and an
                  # empty answer to it is true rather than broken.
                  controls=[(T, "program.block", "Block")], time_from="now-2y")
    # 5, not 4: at 4 the second sub-line (best e1RM, best top set, avg RPE) was cut in
    # half on the live page. Measured 2026-09-06, round two.
    d.row((custom("li-header", tpl.LIFT_HEADER, Q["lift_header"]), 48, []), h=5)
    e1_cols = {"x": terms("session_id", "Session", size=300), "m": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT)}
    # The dashed line is this lift's best in whatever the page is showing, computed from
    # the same rows as the series. The verdict beside it says "your best 420" and before
    # this the chart had no 420 on it, so the two did not point at each other.
    e1 = xy(L("li-e1rm"), "e1RM over time", "line", T,
            e1_cols, "x", ["m"], colors={"m": CHALK}, legend=False,
            ref_metric=("max", "est_e1rm", "Your best"),
            query='set_type: "working" and not e1rm_confidence: "low"')
    # TOP SET OVER TIME is gone. It plotted max(weight_lb) per session against a chart
    # plotting max(est_e1rm) per session - the same sawtooth, one lift's heaviest day
    # either way - and two charts saying one thing is how a page starts reading as a log.
    # The y axis is a rep count with no title on it, so a bar reaching 40,000 read as
    # a weight. Lens draws no axis title here; the unit goes in the panel title.
    zdist = xy(L("li-zones"), "Reps by intensity zone", "bar", T,
               {"x": terms("prilepin_zone", "Zone", size=4),
                "v": metric("sum", "reps", "Reps", fmt=FMT_INT)},
               "x", ["v"], colors={"v": CHALK_DIM}, legend=False, query='set_type: "working"')
    # Verdict, the chart it is drawn from, then the distribution behind both, then the log.
    d.row((custom("li-signal", tpl.SIGNAL_LIFT, Q["sig_lift"]), 18, []),
          (e1, 30, [("session", "Session")]), h=10)
    d.row((zdist, 48, []), h=8)
    # Under the chart, not in its title: a title cannot read a row, and an empty zone
    # chart with no explanation is indistinguishable from a broken one. The terms bucket
    # above deliberately does NOT carry missing=True - a "(missing value)" bar in a
    # distribution of zones reads as a fifth zone, which is worse than the honest gap.
    d.row((custom("li-zone-cov", tpl.ZONE_COVERAGE, Q["zone_cov_lift"]), 48, []), h=3)
    all_cols = {
        "sid": terms("session_id", "Session", size=300, direction="desc"),
        "seq": terms("seq", "#", size=200, dtype="number"),
        "w": last("weight_lb", "lb", "number", fmt=FMT_INT),
        "reps": last("reps", "Reps", "number"),
        "rpe": last("rpe", "RPE", "number", fmt=FMT_1),
    }
    d.row((table(L("li-sets"), "Every working set", T, all_cols, sort="sid", direction="desc",
                 page=50, query='set_type: "working"', row_height="auto"), 48, [("session", "Session")]), h=12)
    # The mechanism behind the verdict card, last on the page (Phase 2 of the Sept 6
    # design plan): the card keeps one scope line and the method paragraph lives here,
    # where it can be read in full. Height is a first guess for a one-column paragraph;
    # MEASURE it in the browser like every other custom-panel height on this page.
    d.row((custom("li-method", tpl.LIFT_METHOD), 48, []), h=4)
    objs += d.build()

    # ---------------------------------------------------------------- History
    d = Dashboard("history", "Ironstack. History", "Sessions over any range. The time picker is the range toggle.",
                  "Every session in the range. The time picker is the range.", controls=[(S, "program.block", "Block"), (S, "program.phase", "Phase")])
    # The verdict first, then the chart that shows its shape, then the log. Before this
    # the page opened on four tiles a phone already shows and the zone chart - the only
    # picture in the app of the trailing-90-day idea - was the third scroll.
    d.row((custom("hi-sig", tpl.SIGNAL_BLOCK, Q["sig_block"]), 48, []), h=10)
    # The 4.0 in Aug 2025 is a layoff artefact (open item: suppress in derive.py). Until
    # then the title says how to read it, so the spike is not the scariest thing on the page.
    acwr = xy(L("hi-acwr"), "Acute vs chronic load, 1.0 is baseline", "line", W,
              {"x": date_hist("@timestamp", "Week", "1w"), "m": metric("max", "acwr", "ACWR", fmt=FMT_1)},
              "x", ["m"], colors={"m": CHALK}, legend=False, ref=(1.0, "Baseline"))
    zcols, zcolors = zone_columns()
    zone_cols = {"x": date_hist("date", "Month", "1M"), **zcols}
    zones = xy(L("hi-zones"), "Share of reps by zone, main lifts", "bar_percentage_stacked", T,
               zone_cols, "x", list(zcols), colors=zcolors,
               query='set_type: "working" and exercise.category: "main"')
    d.row((zones, 48, []), h=9)
    d.row((custom("hi-zone-cov", tpl.ZONE_COVERAGE, Q["zone_cov_main"]), 48, []), h=3)
    # The four tiles - tonnage in range, per session, sessions, avg RPE - are the four
    # Hevy shows on its home screen. Every one is still on the page, in the sessions
    # table and the timeline, for anyone who wants the number rather than the reading.
    # One timeline, not two. This and the Overview panel were the same chart under two
    # titles; naming it for what it is stops the page reading as a second copy.
    d.row((block_timeline(L("hi-timeline"), "Sessions. Click one to open it"),
           48, [("session", "Session")]), h=9)
    d.row((acwr, 48, []), h=8)
    d.row((sessions_table(L("hi-sessions")), 48, [("session", "Session")]), h=10)
    # The mechanism behind the verdict card, last on the page (Phase 2 of the Sept 6
    # design plan): the card keeps one scope line and the method paragraph lives here,
    # where it can be read in full. Height is a first guess for a one-column paragraph;
    # MEASURE it in the browser like every other custom-panel height on this page.
    d.row((custom("hi-method", tpl.BLOCK_METHOD), 48, []), h=4)
    objs += d.build()

    # ---------------------------------------------------------------- Meets
    d = Dashboard("meets", "Ironstack. Meets", "Competition record. Every attempt, made and missed.",
                  # Was "Click a best lift to see how it was trained." The best-lifts panel is
                  # custom content, which strips <a href> entirely, so nothing on it has ever
                  # been clickable. The line the reader actually needs is the attempt legend.
                  "The platform record, attempt by attempt. A struck-through attempt was missed.",
                  time_from="now-10y")
    # The verdict goes above the record. The record is what the lifter already knows;
    # how this cycle compares to it is the thing only the log can say.
    # 8 and 5, measured on 2026-09-06 after the card diet: at 10 and 6 both rows carried
    # two units of blank ground under their last line.
    d.row((custom("me-sig-taper", tpl.SIGNAL_TAPER, Q["sig_taper"]), 24, []),
          (custom("me-sig-proj", tpl.SIGNAL_PROJECTION, Q["sig_projection"]), 24, []), h=9)
    # 9, not 8: at 8 the projection card, which carries the three-meet line and a scope
    # line that wraps at 24 columns, scrolled its pointer off the bottom. Round two.
    d.row((custom("me-cards", tpl.MEET_CARDS, Q["meet_cards"]), 48, []), h=5)
    d.row((custom("me-best", tpl.MEET_BESTS, Q["meet_bests"]), 48, []), h=8)
    d.row((custom("me-list", tpl.MEET_LIST, Q["meet_list"]), 48, []), h=11)
    # The mechanism behind the verdict card, last on the page (Phase 2 of the Sept 6
    # design plan): the card keeps one scope line and the method paragraph lives here,
    # where it can be read in full. Height is a first guess for two columns of paragraph;
    # MEASURE it in the browser like every other custom-panel height on this page.
    # 6, not 5: at 5 the projection paragraph was cut at "Under" on the live page.
    d.row((custom("me-method", tpl.MEETS_METHOD), 48, []), h=6)
    objs += d.build()

    # ---------------------------------------------------------------- Mindset
    d = Dashboard("mindset", "Ironstack. Mindset", "Every note, tagged and in order.",
                  # "searchable" was a promise with no search box behind it: the semantic
                  # fields are reachable only through the coach.
                  # The notes list is custom content and opens nothing. The tag bar beside
                  # it is an XY chart and filters the whole page on one click, which is the
                  # gesture worth teaching.
                  "Everything you wrote, tagged and in order. Click a tag to filter the page. " +
                  tpl.coach_or("To ask a question of it, ask the coach.",
                               "A tag is a count, not a reading: what a note said stays in the note."))
    tag_cols = {"x": terms("tags", "Tag", size=25, by_col="c", direction="desc"), "c": count("Notes")}
    # size=25 categories in a 9-row panel is the bug that cost a whole review round.
    # Lens does not scroll a horizontal bar chart and it does not shrink the type: it
    # draws every bar and then prints only every OTHER axis label. Fifteen tags came
    # back, eight labels rendered, and two passes of this review read the seven
    # unlabelled bars as missing data - the chart was right, the reader could not tell.
    # Sized to the categories instead: the panel has to be tall enough that every bar
    # gets its name, because a bar nobody can name is worse than no bar.
    tags = xy(L("mi-tags"), "Tags. Click one to filter", "bar_horizontal", N, tag_cols, "x", ["c"], colors={"c": CHALK_DIM}, legend=False)
    # TAGS OVER TIME was three stacked bars under a twelve-entry legend that filled the
    # panel. The bar chart says the same thing and can be clicked.
    d.row((custom("mi-sig", tpl.SIGNAL_TAGS, Q["sig_tags"]), 48, []), h=9)
    d.row((tags, 48, []), h=15)
    d.row((custom("mi-recent", tpl.RECENT_NOTES, Q["recent_notes"]), 32, []),
          (notes_table(L("mi-notes"), "Sessions behind these notes"), 16, [("session", "Session")]), h=12)
    # The mechanism behind the verdict card, last on the page (Phase 2 of the Sept 6
    # design plan): the card keeps one scope line and the method paragraph lives here,
    # where it can be read in full. Height is a first guess for a one-column paragraph;
    # MEASURE it in the browser like every other custom-panel height on this page.
    d.row((custom("mi-method", tpl.TAGS_METHOD), 48, []), h=4)
    objs += d.build()

    # The de-duplication that made the duplicate-id check unfireable, handled
    # deliberately this time.
    #
    # It ran here, before check() ever saw the list, so check() counted duplicates in an
    # already-unique list and could not find one by construction: give every Lens the
    # same id and `--check` printed "0 duplicate ids" while thirteen panels silently
    # vanished from the artifact. That is the FIRST failure the README lists under how
    # this directory has actually broken, and the guard written for it was dead.
    #
    # The de-dup exists for shared builders - block_timeline() and the tables are called
    # from more than one dashboard - so it is kept, but only for its actual job: the
    # SAME object built twice. Two DIFFERENT objects wearing one id is the bug, and it
    # is fatal here, before anything can quietly drop one of them. check() still counts
    # duplicates in what it is handed, as a second net over a list that should now be
    # incapable of carrying any.
    seen, out, collisions = {}, [], []
    for o in objs:
        key = (o["type"], o["id"])
        if key not in seen:
            seen[key] = o
            out.append(o)
        elif json.dumps(seen[key], sort_keys=True) != json.dumps(o, sort_keys=True):
            collisions.append(f'{o["type"]} {o["id"]}')
    if collisions:
        sys.exit(
            "error: two different saved objects share one id:\n"
            + "".join(f"       {c}\n" for c in sorted(set(collisions)))
            + "       On import the second silently overwrites the first and its panels\n"
            "       render an error. Nothing was written."
        )
    return out


# A number a stranger cannot own. 909.4 (the author's meet total) and 266.72 (his best
# DOTS) were compiled into a panel title, a reference line and a card sentence, so every
# install of this repo asserted them as the reader's records. Two shapes catch it: a
# three- or four-digit number carrying a fraction, which in this app is always a measured
# record and never a design constant, and any such number sitting next to a unit.
PR_DECIMAL = re.compile(r"(?<![\d.])\d{3,4}\.\d+")
FONT_DATA = re.compile(r"url\(data:font/woff2;base64,[A-Za-z0-9+/=]+\)")
PR_WITH_UNIT = re.compile(r"(?<![\d.])\d{3,5}(?:\.\d+)?\s*(?:&nbsp;)?\s*(?:lb|LB|kg|KG|DOTS)\b")

# The same class of fact, in words instead of digits. The load card closed its provenance
# line with "so this reads back to Jan 2023" - the month THIS author's log starts, compiled
# into a public artifact and read by every install as a statement about the reader's own
# history. A record is a number a stranger cannot own; a month-year is a DATE a stranger
# cannot own, and it is worse than a number because it reads as documentation rather than
# as data. Nothing in these pages has a legitimate reason to name a calendar month at
# build time: every real month on screen is DATE_FORMATted out of the reader's own index
# (month_s, date_s, last_s, meet_s) or computed in Liquid from a row. So the rule is flat -
# no month-year literal in anything that ships - and there is no allowlist to get it wrong.
MONTH_YEAR = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:19|20)\d{2}\b")

# --------------------------------------------------------------------------- fields
#
# Nothing checked that a field EXISTS. Renaming `est_e1rm` in a Lens column, `weight_lb`
# inside an ES|QL STATS, or the `prilepin_zone` literal in a filter all built cleanly,
# passed every guard here, imported without complaint, and then rendered an empty or
# errored panel in the browser - which is the exact failure mode this whole file exists
# to make impossible. The mappings in starter/schema/ are where the field truth lives, so
# they are the thing to check against.

MAPPINGS = Path(__file__).resolve().parent.parent / "starter" / "schema" / "mappings"

# ES|QL aliases and the columns Kibana adds. `___records___` is Lens's own count column
# and names no field.
LENS_SYNTHETIC = {"___records___"}

# Words that are syntax, not fields. Function names never need listing: a function is
# followed by "(" and the extractor skips anything that is.
ESQL_WORDS = {
    "and", "or", "not", "is", "null", "true", "false", "as", "by", "asc", "desc",
    "nulls", "first", "last", "like", "rlike", "in", "metadata",
    # duration and date-period units, which ES|QL writes bare after a number
    "millisecond", "milliseconds", "second", "seconds", "minute", "minutes",
    "hour", "hours", "day", "days", "week", "weeks", "month", "months",
    "year", "years", "quarter", "quarters", "decade", "decades",
}

STRING_LITERAL = re.compile(r'"[^"]*"')
IDENTIFIER = re.compile(r"[A-Za-z_@][A-Za-z0-9_.@]*")
KQL_FIELD = re.compile(r'([A-Za-z_@][A-Za-z0-9_.@]*)\s*(?::|>=|<=|>|<)')


def _flatten(props: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for name, spec in props.items():
        dotted = prefix + name
        if "properties" in spec:
            out.update(_flatten(spec["properties"], dotted + "."))
        else:
            out[dotted] = spec.get("type", "object")
    return out


def index_field_types() -> dict[str, dict[str, str]]:
    """index name -> {dotted field: mapped type}.

    The types are what verify_liquid's raw-render lint is built from: a keyword or a text
    field rendered without `| escape` puts whatever was typed in the log into the card's
    HTML, and a float rendered without `| round` prints its full float32 expansion in
    Kibana's JavaScript Liquid ("7.130000114440918"). Those two lints used to be
    hand-maintained ALLOWLISTS, which is the wrong polarity: a text column nobody had
    thought to list passed.
    """
    if not MAPPINGS.is_dir():
        sys.exit(f"error: no mappings at {MAPPINGS}. Field checks cannot run and a build\n"
                 "       that cannot check its fields is the build that ships an empty "
                 "panel.\n       Nothing was written.")
    out = {}
    for path in sorted(MAPPINGS.glob("*.json")):
        mapping = json.loads(path.read_text())["mappings"]
        out[path.stem] = _flatten(mapping.get("properties", {}))
    missing = INDICES - set(out)
    if missing:
        sys.exit(f"error: no mapping file for {sorted(missing)}. Nothing was written.")
    return out


def index_fields() -> dict[str, set[str]]:
    """index name -> every dotted field its mapping declares."""
    return {index: set(fields) for index, fields in index_field_types().items()}


def _split_top(text: str, sep: str = ",") -> list[str]:
    """Split on `sep` at paren depth 0, so a function's own commas stay inside it."""
    parts, depth, buf = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def _identifiers(expr: str) -> list[str]:
    """Bare column references in an expression: not keywords, not function names."""
    out = []
    for m in IDENTIFIER.finditer(expr):
        word = m.group(0)
        if word.lower() in ESQL_WORDS:
            continue
        if expr[m.end():m.end() + 1] == "(":   # a function call, not a column
            continue
        out.append(word)
    return out


def esql_columns(query: str) -> tuple[set[str], list[tuple[str, str]], set[str]]:
    """(indices this query reads, [(stage kind, column referenced)], names it defines).

    Aliases are resolved rather than skipped: an EVAL, a STATS assignment and a RENAME
    each DEFINE a name, and a later stage referring to one is referring to a real column.
    Anything else has to exist in the mappings of the indices the FROM names.
    """
    stripped = STRING_LITERAL.sub('""', query)
    indices: set[str] = set()
    defined: set[str] = set()
    refs: list[tuple[str, str]] = []

    def use(kind: str, expr: str) -> None:
        for name in _identifiers(expr):
            if name not in defined:
                refs.append((kind, name))

    # Split on "|" only AFTER the string literals are gone: MV_CONCAT(tags, "|") writes
    # a pipe inside a literal, and splitting first cut two queries in half.
    for stage in stripped.split("|"):
        stage = stage.strip()
        head = stage.split(None, 1)[0].upper() if stage else ""
        rest = stage[len(head):].strip()
        if head == "FROM":
            indices |= {i.strip() for i in rest.split(",") if i.strip()}
        elif head in ("Where", "SORT", "DISSECT", "GROK"):
            use(head.lower(), rest)
        elif head == "EVAL":
            for item in _split_top(rest):
                name, sep, expr = item.partition("=")
                if sep:
                    use("eval", expr)
                    defined.add(name.strip())
                else:
                    use("eval", item)
        elif head == "STATS":
            # Keywords are uppercase throughout Q by convention, which is what makes
            # this split safe; a lowercase "by" would fold the grouping columns into the
            # aggregation list, which mislabels them but still checks every one.
            aggs, sep, by = rest.partition(" BY ")
            if not sep:
                aggs, by = rest, ""
            for item in _split_top(aggs):
                name, eq, expr = item.partition("=")
                if eq:
                    use("stats", expr)
                    defined.add(name.strip())
                else:
                    use("stats", item)
            if by:
                use("stats-by", by)
                for name in _identifiers(by):
                    defined.add(name)
            # A STATS drops every column it did not produce.
            defined |= {n.strip().split("=")[0].strip() for n in _split_top(aggs)}
        elif head == "RENAME":
            for item in _split_top(rest):
                source, _sep, target = item.partition(" AS ")
                use("rename", source)
                defined.add(target.strip())
        elif head in ("KEEP", "DROP"):
            for item in _split_top(rest):
                # A KEEP naming a column an earlier EVAL or STATS produced is naming a
                # real column; only the ones that have to come from the index are checked.
                if item not in defined:
                    refs.append((head.lower(), item))
                defined.add(item)
        elif head == "MV_EXPAND":
            use("mv_expand", rest)
    return indices, refs, defined


def _resolves(column: str, fields: set[str]) -> bool:
    if column in fields:
        return True
    if column.endswith("*"):
        stem = column[:-1]
        return any(f.startswith(stem) for f in fields)
    # An object path: KEEP totals.* is a wildcard, but `totals` alone names the object.
    return any(f.startswith(column + ".") for f in fields)


def check_fields(objs: list[dict]) -> list[str]:
    """Every field a panel names must exist in the index it reads it from."""
    fields = index_fields()
    dv_index = {dv_id: index for dv_id, index, _ in DV.values()}
    bad: list[str] = []

    for name, query in Q.items():
        indices, refs, _ = esql_columns(query)
        known: set[str] = set()
        for index in indices:
            known |= fields.get(index, set())
        if not known:
            continue  # an unknown index; the FROM lint above already says so
        for kind, column in refs:
            if not _resolves(column, known):
                bad.append(f'Q[{name!r}] {kind} names {column!r}, which '
                           f'{" or ".join(sorted(indices))} does not map')

    def kql_fields(where: str, query: str, known: set[str]) -> None:
        for field in KQL_FIELD.findall(STRING_LITERAL.sub('""', query or "")):
            if field.lower() in ("and", "or", "not"):
                continue
            if not _resolves(field, known):
                bad.append(f"{where} filters on {field!r}, which its index does not map")

    for o in objs:
        if o["type"] != "lens":
            continue
        state = o["attributes"]["state"]
        layer_index = {}
        for ref in o["references"]:
            if ref["name"].startswith("indexpattern-datasource-layer-"):
                layer = ref["name"].rsplit("-", 1)[-1]
                layer_index[layer] = dv_index[ref["id"]]
        for layer_id, layer in state["datasourceStates"]["formBased"]["layers"].items():
            index = layer_index.get(layer_id)
            known = fields.get(index, set())
            kql_fields(f'lens {o["id"]}', state["query"]["query"], known)
            for col_id, col in layer["columns"].items():
                source = col.get("sourceField")
                if source and source not in LENS_SYNTHETIC and not _resolves(source, known):
                    bad.append(f'lens {o["id"]} column {col_id!r} reads {source!r}, '
                               f"which {index} does not map")
                kql_fields(f'lens {o["id"]} column {col_id!r}',
                           (col.get("filter") or {}).get("query", ""), known)

    for o in objs:
        if o["type"] != "dashboard":
            continue
        group = o["attributes"].get("controlGroupInput")
        if not group:
            continue
        dv_for = {r["name"]: r["id"] for r in o["references"]
                  if r["name"].startswith("controlGroup_")}
        for cid, panel in json.loads(group["panelsJSON"]).items():
            field = panel["explicitInput"]["fieldName"]
            index = dv_index[dv_for[f"controlGroup_{cid}:optionsListDataView"]]
            if not _resolves(field, fields.get(index, set())):
                bad.append(f'{o["id"]}: the {panel["explicitInput"]["title"]} control '
                           f"asks for {field!r}, which {index} does not map")
    return bad


# Every column a Liquid template reads, and the KEEP that has to project it.
COL_READ = re.compile(r"\['([A-Za-z0-9_.@]+)'\]\.value")


def _keep_columns(esql: str) -> list[str] | None:
    """The columns the LAST `| KEEP` in this query projects, or None if it has none.

    A query with no KEEP returns whatever its last STATS or EVAL left, which this cannot
    know without a cluster, so those panels are skipped rather than guessed at.
    """
    keep = None
    for stage in esql.split("|"):
        stage = stage.strip()
        if stage.upper().startswith("KEEP "):
            keep = stage[5:]
    if keep is None:
        return None
    return [c.strip() for c in keep.split(",") if c.strip()]


def _projected(column: str, keep: list[str]) -> bool:
    for k in keep:
        if k == column or k == "*":
            return True
        if k.endswith("*") and column.startswith(k[:-1]):
            return True
    return False


# The object counts kibana/README.md publishes. It said they "are checked by --check"
# while check() only PRINTED a total, so the sentence was true of nothing: a panel added
# or dropped moved the number in the terminal and left the number in the README behind.
# Asserting them is what makes that sentence true, and the cost - one line to edit when a
# panel is deliberately added - is the point rather than the price.
EXPECTED_OBJECTS = {"index-pattern": 4, "lens": 14, "dashboard": 7}


def note(line: str) -> None:
    """Diagnostics go to stderr. `--stdout > dashboards.ndjson` is a supported
    invocation, and a finding printed on stdout lands inside the file it is about."""
    print(line, file=sys.stderr)


def check(objs: list[dict]) -> int:
    """Duplicate ids, dangling references and wiring shape — the ways this file breaks
    silently.

    A duplicate id means one object quietly overwrites another on import; a dangling
    reference means a panel imports fine and then renders an error where a chart
    should be. Both were checked by hand after the Sept 4 build; now they are checked
    by the build.

    The duplicate scan here is a SECOND net. build() de-duplicated by (type, id) before
    returning, so this counted duplicates in an already-unique list and could never find
    one; the first net now lives there, where the collision is still visible. This one
    stays because it costs nothing and it is the check that would notice if the two ever
    came apart again.
    """
    ids, dupes = set(), []
    for o in objs:
        if o["id"] in ids:
            dupes.append(f'{o["type"]} {o["id"]}')
        ids.add(o["id"])

    dangling = []
    for o in objs:
        for r in o.get("references", []):
            if r["id"] not in ids:
                dangling.append(f'{o["type"]} {o["id"]} -> {r["type"]} {r["id"]} ({r["name"]})')

    # Two bugs shipped for weeks because they were invisible to every check: ten
    # drilldowns written under a key Kibana does not read, and nav links carrying the
    # filters of the page you left. Neither is a duplicate id or a dangling reference,
    # and neither shows up in a Liquid render. They are shape, so shape is checked.
    shape = []
    # And three more, each of which shipped: a private Elastic host in a public artifact,
    # somebody else's meet total rendered as the reader's, and a card reading a column its
    # own query never projected.
    private, records, unprojected, months = [], [], [], []

    def scan_record(where: str, text: str):
        # The embedded fonts are ~135 KB of base64 per panel, and base64 can spell
        # "912lb/" by accident. They are not text a reader sees; scan without them.
        text = FONT_DATA.sub("url(data:font)", text)
        for m in PR_DECIMAL.findall(text) + PR_WITH_UNIT.findall(text):
            if MEET_MAX_LB is not None and f"{MEET_MAX_LB:g}" in m:
                continue  # the reader said this is theirs, in IRONSTACK_MEET_MAX_LB
            records.append(f"{where}: {m!r} looks like a hardcoded personal record")
        for m in MONTH_YEAR.findall(text):
            months.append(f"{where}: {m!r} is a hardcoded month; a date on these pages "
                          f"has to come from the reader's own rows")

    # The template SOURCE as well as the built panels, because the two are not the same
    # set: a card written but not yet wired to a panel ships in no dashboard and would
    # slip past a scan of the objects alone. A Liquid {% comment %} is source too - it
    # is stripped at render but it is still in the artifact - so it is scanned like the
    # rest rather than being the one place the rule does not reach.
    for attr in sorted(dir(tpl)):
        if attr.startswith("__"):
            continue
        text = getattr(tpl, attr)
        if isinstance(text, str):
            for m in MONTH_YEAR.findall(FONT_DATA.sub("url(data:font)", text)):
                months.append(f"templates.{attr}: {m!r} is a hardcoded month; a date on "
                              f"these pages has to come from the reader's own rows")

    for o in objs:
        attrs = o["attributes"]
        # Every saved-object string a reader can see, not the three that happened to be
        # listed. A dashboard DESCRIPTION is prose in the listing and under the title; a
        # lens description and an index-pattern name ship the same way. All of them sat
        # outside this scan while the comment above it claimed to catch "somebody else's
        # meet total rendered as the reader's" - the guard was real, its reach was not,
        # which is the same shape as the raw-render lint that could not see an assign.
        # Verified by planting "back to Jan 2023. Best total 909.4 lb." in the History
        # dashboard's description: check() passed it, 0 records and 0 months.
        for field in ("title", "description", "name"):
            if isinstance(attrs.get(field), str):
                scan_record(f'{o["type"]} {o["id"]} {field}', attrs[field])
        if o["type"] != "dashboard":
            continue
        for p in json.loads(attrs["panelsJSON"]):
            cfg = p.get("embeddableConfig", {})
            if "drilldowns" in cfg:
                shape.append(f'{o["id"]}: embeddableConfig.drilldowns is the dead key; '
                             f'Kibana reads enhancements.dynamicActions.events')
            for ev in cfg.get("enhancements", {}).get("dynamicActions", {}).get("events", []):
                if not ev.get("triggers") or not ev.get("action", {}).get("factoryId"):
                    shape.append(f'{o["id"]}: drilldown event missing triggers or factoryId')
            if cfg.get("title"):
                scan_record(f'{o["id"]} panel title', cfg["title"])
            for link in cfg.get("links", []):
                scan_record(f'{o["id"]} nav link label', str(link.get("label", "")))
                opts = link.get("options", {})
                if opts.get("use_filters") or opts.get("use_time_range"):
                    shape.append(f'{o["id"]}: nav link "{link.get("label")}" carries '
                                 f'filters or the time range; each page is entered on its own terms')
                if link.get("type") != "externalLink":
                    continue
                host = urlsplit(link.get("destination", "")).hostname or ""
                if host.lower() not in COACH_PLACEHOLDER_HOSTS and not ALLOW_PRIVATE_COACH:
                    private.append(
                        f'{o["id"]}: external link "{link.get("label")}" points at {host}, '
                        f'which is not a documented placeholder')
            template = cfg.get("template")
            if not template:
                continue
            scan_record(f'{o["id"]} custom panel {p["panelIndex"][:8]}', template)
            esql = (cfg.get("esql_query") or [None])[0]
            if not esql:
                continue
            keep = _keep_columns(esql)
            if keep is None:
                continue  # no KEEP: the projection is whatever the last stage left
            for column in sorted(set(COL_READ.findall(template))):
                if not _projected(column, keep):
                    unprojected.append(
                        f'{o["id"]}: a custom panel reads {column!r} but its query does '
                        f'not KEEP it')

    # Every DATE_FORMAT here formats a calendar date, and a calendar date must never be
    # shifted by a timezone offset - doing so moves it to the previous day for every
    # user west of Greenwich. See the timezone comment above. Two halves, both checked:
    # nothing formats @timestamp (which would need shifting), and nothing carries a
    # shift (which would break the dates that are already right).
    date_fmt = []
    for name, query in Q.items():
        for arg in DATE_FORMAT_ARG.findall(query):
            if arg == "@timestamp":
                date_fmt.append(
                    f'Q[{name!r}] formats @timestamp, which is an instant: format a '
                    f'calendar date, or shift it by the session timezone at index time')
        if DATE_FORMAT_SHIFTED.search(query):
            date_fmt.append(
                f'Q[{name!r}] shifts a DATE_FORMAT argument by seconds; calendar dates '
                f'are already the lifter\'s own day and a shift moves them backwards')

    # Every field a panel names, against the mappings in starter/schema/.
    missing_field = check_fields(objs)

    counts = {}
    for o in objs:
        counts[o["type"]] = counts.get(o["type"], 0) + 1
    miscount = []
    if counts != EXPECTED_OBJECTS:
        miscount.append(
            f"the build holds {counts} and EXPECTED_OBJECTS says {EXPECTED_OBJECTS}; "
            "update the constant and kibana/README.md together, or find the object "
            "that went missing")

    # A FROM naming an index the pipeline does not write imports cleanly and renders an
    # error. The list is the six the indexer creates plus the one derive.py writes.
    unknown_index = []
    for name, query in Q.items():
        for m in FROM_CLAUSE.findall(query):
            for idx in m.split(","):
                idx = idx.strip()
                if idx and idx not in INDICES:
                    unknown_index.append(f'Q[{name!r}] reads {idx!r}, which nothing indexes')

    for item in shape:
        note(f"  shape: {item}")

    for label, items in (("duplicate id", dupes), ("dangling reference", dangling),
                         ("private host", private), ("hardcoded record", records),
                         ("hardcoded month", months),
                         ("unprojected column", unprojected), ("unknown index", unknown_index),
                         ("date shift", date_fmt), ("missing field", missing_field),
                         ("object count", miscount)):
        for item in items:
            note(f"  {label}: {item}")
    bad = (len(dupes) + len(dangling) + len(shape) + len(private) + len(records)
           + len(months) + len(unprojected) + len(unknown_index) + len(date_fmt)
           + len(missing_field) + len(miscount))
    note(f"check: {len(objs)} objects "
          f"({', '.join(f'{n} {k}' for k, n in sorted(counts.items()))}), "
          f"{len(dupes)} duplicate ids, "
          f"{len(dangling)} dangling references, {len(shape)} shape problems, "
          f"{len(private)} private hosts, {len(records)} hardcoded records, "
          f"{len(months)} hardcoded months, "
          f"{len(unprojected)} unprojected columns, {len(unknown_index)} unknown indices, "
          f"{len(date_fmt)} date shifts, {len(missing_field)} missing fields, "
          f"{len(miscount)} count mismatches")
    return bad


def main() -> None:
    global COACH_URL, ALLOW_PRIVATE_COACH, MEET_MAX_LB
    args = sys.argv[1:]
    ALLOW_PRIVATE_COACH = "--allow-private-coach" in args
    checking = "--check" in args

    if checking:
        # --check compares the build against the committed artifact, so it has to build
        # the artifact's configuration and not the reader's. The committed file is the
        # --no-coach build with no meet best: both are deployment-specific and cannot
        # live in a public repo (see README).
        #
        # Neutralising only COACH_URL was not enough, and the failure was nasty: a
        # reader who followed the README - set your offset, set your meet best, run the
        # checks - got "dashboards.ndjson is not what this build produces", which says
        # the committed artifact is stale when the only thing that differed was their
        # own environment. A check that fails on correct configuration teaches people to
        # ignore it.
        COACH_URL = ""
        MEET_MAX_LB = None
    # The opt-outs turn the feature OFF, rather than only excusing its absence. Both
    # were written as "excuse", which made each one silently conditional on the reader's
    # environment: with the variable exported, the flag changed nothing at all.
    #
    # The --no-coach line here is REDUNDANT TODAY and deliberately kept. templates.py
    # reads the same flag at import and this module takes COACH_URL from it, so deleting
    # this line changes no output and survives the whole suite - a mutant that survives
    # because the invariant is enforced twice, not because it is untested. It stays as
    # the guard for the day someone makes this module read the environment itself, which
    # is how the bug arrived the first time. --no-meet-max has no second site and is
    # load-bearing on its own.
    if "--no-coach" in args:
        COACH_URL = ""
    if "--no-meet-max" in args:
        MEET_MAX_LB = None
    if not checking and not COACH_URL and "--no-coach" not in args:
        # Before the build, not after it. A note printed under a successful "wrote
        # dashboards.ndjson" is a note nobody reads, and the file it is describing has
        # already replaced the good one: seven dashboards silently lose ASK THE COACH and
        # the next import takes the link away. Caught on Sept 5 while adding the taper
        # card - the one-panel change came out as a fourteen-line diff.
        sys.exit(
            "error: IRONSTACK_COACH_URL is unset, so ASK THE COACH cannot be built and\n"
            "       importing the result would remove the link from all seven "
            "dashboards.\n"
            "       Export it (it is deployment-specific, like ES_ENDPOINT - see\n"
            "       kibana/README.md) first, or pass --no-coach\n"
            "       if dropping the link is what you meant.\n"
            "       Nothing was written."
        )

    # The same guard as --no-coach, for the same reason, found the same way. The
    # deployed Overview carried "PROJECTED TOTAL, WEEK BY WEEK. STACKED e1RM PER
    # COMPETITION LIFT" over an area chart with no reference line on it, because the
    # build that produced it ran without IRONSTACK_MEET_MAX_LB. The card beside it said
    # "96% of your meet best, 909 lb" off the meets index, so the page held the number
    # and the chart of the same number could not draw it. Two env vars unset, two of the
    # three best things on the page gone, and nothing anywhere said so.
    if not checking and MEET_MAX_LB is None and "--no-meet-max" not in args:
        sys.exit(
            "error: IRONSTACK_MEET_MAX_LB is unset, so the projected-total chart gets no\n"
            "       reference line and no number in its title - the panel becomes a\n"
            "       stack of weekly e1RMs with nothing to read it against.\n"
            "       Export it (see kibana/README.md) first, or pass --no-meet-max\n"
            "       if a chart with no yardstick is what you meant.\n"
            "       Nothing was written."
        )

    objs = build()
    # What this build actually contains, printed before the file lands rather than after.
    # Both features above are opt-out and both opt-outs are legitimate, so the honest
    # thing is not to forbid them but to make the result impossible to miss.
    note("features: ASK THE COACH " + ("on" if COACH_URL else "OFF (--no-coach)")
         + " | projected-total reference line "
         + (f"on at {MEET_MAX_LB:g} lb" if MEET_MAX_LB is not None else "OFF (--no-meet-max)"))
    # Above the --stdout branch, not below it. It sat below, so
    # `build_dashboards.py --stdout > dashboards.ndjson` wrote the file having run no
    # guard at all - the one invocation that most needed them.
    bad = check(objs)
    ndjson = "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n"

    if checking:
        # --check used to build the objects, inspect them, and never once look at the
        # file in the repo. Appending {"garbage":true} to dashboards.ndjson and running
        # it reported "0 shape problems" and exited 0.
        if not OUT.exists():
            note(f"  artifact: {OUT.name} does not exist")
            sys.exit(1)
        on_disk = OUT.read_text()
        if on_disk != ndjson:
            want, got = ndjson.splitlines(), on_disk.splitlines()
            note(f"  artifact: {OUT.name} is not what this build produces "
                 f"({len(got)} lines on disk, {len(want)} generated)")
            for n, (a, b) in enumerate(zip(want, got), 1):
                if a != b:
                    note(f"  artifact: first difference on line {n}")
                    note(f"      built: {a[:160]}")
                    note(f"    on disk: {b[:160]}")
                    break
            else:
                extra = got[len(want):] or want[len(got):]
                side = "on disk" if len(got) > len(want) else "built"
                note(f"  artifact: {len(extra)} extra line(s) {side}, "
                     f"first: {extra[0][:160]}")
            sys.exit(1)
        note(f"check: {OUT.name} matches the build")
        sys.exit(1 if bad else 0)

    if bad:
        sys.exit("refusing to write a broken dashboards.ndjson")
    if "--stdout" in args:
        sys.stdout.write(ndjson)
        return
    OUT.write_text(ndjson)
    kinds = {}
    for o in objs:
        kinds[o["type"]] = kinds.get(o["type"], 0) + 1
    print(f"wrote {OUT.name}: " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))


if __name__ == "__main__":
    main()
