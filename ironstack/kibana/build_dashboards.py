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

import copy
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import templates as tpl  # noqa: E402
from templates import brand_bar  # noqa: E402

OUT = Path(__file__).resolve().parent / "dashboards.ndjson"

# --------------------------------------------------------------------------- Iron Log

CHALK = "#ebe5d8"
CHALK_DIM = "#a8a094"
CHALK_FAINT = "#5a564f"
STEEL = "#7a7873"
RULE = "#2a2622"
PANEL = "#1f1c19"
BLOOD = "#a8211a"  # one accent per dashboard, never two unrelated things

PHASES = [  # order is the training arc, and the tones are a luminance ramp along it
    # The previous three (#5a564f / #a8a094 / #7a7873) were all mid-greys: the legend
    # promised a split you could not see on the bars.
    ("hypertrophy", "Hypertrophy", "#4a463f"),
    ("strength", "Strength", "#8f8a80"),
    ("peaking", "Peaking", "#e4ddce"),
]

MEET_MAX_LB = 909.4    # last meet total; the oxblood reference line on Overview
MEET_BEST_DOTS = 266.72  # Nov 16 2024; the line the DOTS trajectory is measured against

# --------------------------------------------------------------------------- ids

NS = uuid.UUID("6f3d3b2a-6c0e-4b2f-9a7e-1d2c3b4a5f60")


def uid(*parts: str) -> str:
    """Deterministic UUID so re-generating never changes panel or event ids."""
    return str(uuid.uuid5(NS, ":".join(parts)))


DV = {
    "sessions": ("ironstack-dv-sessions", "workout-sessions", "timestamp"),
    "sets": ("ironstack-dv-sets", "workout-sets", "date"),
    "notes": ("ironstack-dv-notes", "workout-notes", "date"),
    "meets": ("ironstack-dv-meets", "workout-meets", "date"),
    "daily": ("ironstack-dv-daily", "workout-daily", "@timestamp"),
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


def count(label="COUNT", filt=None, fmt=None):
    c = _col(label, "count", "number", "ratio", "___records___", params={"emptyAsNull": True})
    if filt:
        c["filter"] = {"query": filt, "language": "kuery"}
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



def last(field, label, dtype="string", sort="date", fmt=None, arrays=False):
    scale = "ratio" if dtype == "number" else "ordinal"
    c = _col(label, "last_value", dtype, scale, field, params={"sortField": sort, "showArrayValues": arrays})
    if fmt:
        c["params"]["format"] = fmt
    return c


def terms(field, label, size=10, dtype="string", order="alphabetical", direction="asc", by_col=None):
    order_by = {"type": "column", "columnId": by_col} if by_col else {"type": "alphabetical", "fallback": True}
    return _col(
        label, "terms", dtype, "ordinal", field, bucketed=True,
        params={
            "size": size, "orderBy": order_by, "orderDirection": direction,
            "otherBucket": False, "missingBucket": False, "parentFormat": {"id": "terms"},
            "include": [], "exclude": [], "includeIsRegex": False, "excludeIsRegex": False,
        },
    )


def date_hist(field, label="DATE", interval="auto"):
    return _col(label, "date_histogram", "date", "interval", field, bucketed=True,
                params={"interval": interval, "includeEmptyRows": True, "dropPartials": False})


def static(value, label):
    return _col(label, "static_value", "number", "ratio", bucketed=False,
                params={"value": str(value)}, isStaticValue=True, references=[])


def phase_columns(op, field, fmt=FMT_INT):
    """One metric column per phase (filtered), so phase colors are fixed via yConfig."""
    cols, colors = {}, {}
    for key, label, color in PHASES:
        cid = f"phase-{key}"
        cols[cid] = metric(op, field, label.upper(), filt=f'program.phase: "{key}"', fmt=fmt)
        colors[cid] = color
    return cols, colors


# --------------------------------------------------------------------------- layers

def layer(columns: dict, order: list[str] | None = None, link_to: str | None = None):
    if order is None:
        # Buckets before metrics, stable within each group. Lens resolves accessors
        # against this order; a metric listed first breaks the panel outright.
        names = list(columns)
        order = ([n for n in names if columns[n].get("isBucketed")] +
                 [n for n in names if not columns[n].get("isBucketed")])
    L = {"columns": columns, "columnOrder": order, "incompleteColumns": {}, "sampling": 1}
    if link_to:
        L["linkToLayers"] = [link_to]
    return L


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


def xy(id_, title, series, dv, columns, x, accessors, colors=None, split=None, ref=None,
       query="", legend=True, right_axis=(), palette=None, y_bounds=None):
    """One data layer (optionally a reference-line layer). colors: accessor -> hex."""
    data_layer = {
        "layerId": "l", "layerType": "data", "seriesType": series, "position": "top",
        "showGridlines": False, "xAccessor": x, "accessors": accessors,
        "yConfig": [
            {"forAccessor": a, "color": (colors or {}).get(a), "axisMode": "right" if a in right_axis else "left"}
            for a in accessors
        ],
    }
    if palette:
        data_layer["palette"] = palette if isinstance(palette, dict) else {"type": "palette", "name": palette}
    if y_bounds:
        lower, upper = y_bounds
        vis_extent = {"mode": "custom", "lowerBound": lower, "upperBound": upper}
    if split:
        data_layer["splitAccessor"] = split
    layers = {"l": (dv, layer(columns))}
    vis_layers = [data_layer]
    if ref:
        value, label = ref
        layers["ref"] = (dv, layer({"ref": static(value, label)}))
        vis_layers.append({
            "layerId": "ref", "layerType": "referenceLine", "accessors": ["ref"],
            "yConfig": [{
                "forAccessor": "ref", "axisMode": "left", "color": BLOOD, "lineStyle": "dashed",
                "lineWidth": 2, "iconPosition": "auto", "textVisibility": True, "fill": "none",
            }],
        })
    vis = {**XY_BASE, "preferredSeriesType": series, "layers": vis_layers}
    vis["legend"] = {**XY_BASE["legend"], "isVisible": legend}
    if y_bounds:
        vis["yLeftExtent"] = vis_extent
    return lens(id_, title, "lnsXY", vis, layers, query=query)


def table(id_, title, dv, columns, sort=None, direction="asc", hidden=(), query="", page=20,
          row_height="single"):
    vis = {
        "layerId": "l", "layerType": "data",
        "columns": [{"columnId": c, "alignment": "left", **({"hidden": True} if c in hidden else {})} for c in columns],
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


NAV_ORDER = ["overview", "program", "session", "lift", "history", "meets", "mindset"]

# The nav in three groups. Custom panels cannot navigate (no <a href>, no scripts in the
# sandbox), so a Links panel is the only door — and three of them, spaced, is the only way
# to show hierarchy in the nav row.
NAV_GROUPS = [("all", NAV_ORDER, 48)]


# The Ironstack Coach is an Agent Builder agent and lives outside the dashboards. It is
# also the only surface the semantic layer has: five semantic_text fields are indexed and
# nothing in Kibana's own UI can reach them — a custom content panel is a sandboxed
# iframe with no scripts and no input, and the KQL bar is lexical. So the honest answer
# is a door, not a search box, and a Links panel is the only panel type that can be one.
#
# The URL is deployment-specific, like ES_ENDPOINT, so it comes from the environment
# rather than the repo: a starter user's Kibana is not this one. Unset, the panel is
# simply not built and the nav takes the full width.
COACH_URL = os.environ.get("IRONSTACK_COACH_URL", "").strip()


def coach_link(current: str) -> Inline:
    return Inline(f"coach-{current}", "links", {
        "title": "", "layout": "horizontal", "hidePanelTitles": True,
        "links": [{
            "type": "externalLink",
            "label": "ASK THE COACH",
            "destination": COACH_URL,
            "order": 0,
            "options": {"open_in_new_tab": True, "encode_url": False},
        }],
    })


def links(current: str, group: str = "all", keys: list[str] | None = None) -> Inline:
    """Kibana Links panel: the app nav. Carries filters and time so context survives a hop."""
    items, refs = [], []
    for key in (keys or NAV_ORDER):
        link_id = uid("nav", current, key)
        items.append({"type": "dashboardLink", "label": key.upper() if key != current else f"[ {key.upper()} ]",
                      # use_time_range stays False on purpose. Every dashboard sets its
                      # own deliberate default (Overview 1y, Lift 2y, Meets 10y) and
                      # timeRestore cannot win against a link that carries one; visiting
                      # Meets used to leave every other page on a 10-year window.
                      # Drilldowns keep it True — clicking an old session has to carry a
                      # range wide enough to contain it.
                      "options": {"open_in_new_tab": False, "use_time_range": False, "use_filters": True},
                      "destinationRefName": f"link_{link_id}_dashboard"})
        refs.append({"name": f"link_{link_id}_dashboard", "type": "dashboard", "id": DASH[key]})
    return Inline(f"nav-{current}-{group}", "links", {"title": "", "layout": "horizontal", "links": items,
                                                      "hidePanelTitles": True}, refs)


class Dashboard:
    """Collects panels row by row on Kibana's 48-column grid, in the dashboard format this
    Kibana writes itself (typeMigrationVersion 10.3.0): by-reference panels are `vis` /
    `legacy_vis` / `map` with a `{panelIndex}:savedObjectRef` reference; by-value panels carry
    their config inline; drilldowns live in `embeddableConfig.drilldowns`."""

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
        self.row((custom(f"brand-{key}", brand_bar(key.upper(), tagline),
                         "FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP date"), 48, []), h=4)
        nav_w = 40 if COACH_URL else 48
        nav = [(links(key, name, members), nav_w, []) for name, members, _ in NAV_GROUPS]
        if COACH_URL:
            nav.append((coach_link(key), 8, []))
        self.row(*nav, h=2)

    def row(self, *items, h=8):
        """items: (saved object | Inline, width, drilldowns); drilldowns are (target key, name) or ('url', template, name)."""
        x = 0
        for obj, w, drills in items:
            inline = isinstance(obj, Inline)
            idx = uid(self.id, obj.key if inline else obj["id"])
            drilldowns = []
            for d in drills:
                if d[0] == "url":
                    drilldowns.append({"type": "url_drilldown", "label": d[2], "trigger": "on_click_value",
                                       "open_in_new_tab": False, "encode_url": True, "url": d[1]})
                else:
                    target, name = d
                    ref_name = f"dashboard_drilldown_{DASH[target]}"
                    drilldowns.append({"type": "dashboard_drilldown", "label": name, "trigger": "on_apply_filter",
                                       "open_in_new_tab": False, "use_time_range": True, "use_filters": True,
                                       "dashboardRefName": ref_name})
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
            if drilldowns:
                config["drilldowns"] = drilldowns
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
                default = list(control[3]) if len(control) > 3 else []
                cid = uid(self.id, "control", field)
                panels[cid] = {"type": "optionsListControl", "order": order, "grow": False, "width": "small",
                               "explicitInput": {"id": cid, "fieldName": field, "title": label,
                                                 "selectedOptions": default, "searchTechnique": "prefix",
                                                 "sort": {"by": "_key", "direction": "asc"}}}
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

Q = {
    "days": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL date_s = DATE_FORMAT("EEE MMM d", date), meet_s = DATE_FORMAT("EEE MMM d, yyyy", program.meet_date) | KEEP program.*, date_s, meet_s, days_to_meet',
    # The total and its three lifts come from ONE query, so the card cannot contradict
    # itself the way the old total card contradicted the e1RM tiles above it.
    "total": ('FROM workout-sets '
              '| WHERE is_competition_lift == true AND set_type == "working" '
              'AND e1rm_confidence != "low" AND @timestamp >= NOW() - 90 days '
              '| STATS e1 = MAX(est_e1rm) BY lift_family '
              '| SORT e1 DESC | LIMIT 3 | EVAL lift = lift_family | KEEP lift, e1'),
    "meet_bests": ('FROM workout-meets | WHERE made == true '
                   '| STATS lb = MAX(weight_lb), kg = MAX(weight_kg) BY lift '
                   '| SORT lb DESC | LIMIT 3'),
    "watch": 'FROM workout-sessions | WHERE watch_items IS NOT NULL | SORT @timestamp DESC | LIMIT 12 | MV_EXPAND watch_items | EVAL date_s = DATE_FORMAT("MMM d", date), item = watch_items | KEEP date_s, item',
    "program_header": 'FROM workout-sessions | EVAL wd = program.week * 100 + program.day | STATS n = COUNT(*), wd_max = MAX(wd), last_day = MAX(date) BY program.name, program.block, program.phase, program.total_days, program.meet_date | SORT last_day DESC | LIMIT 1 | EVAL program.week = FLOOR(wd_max / 100), program.day = wd_max % 100, date_s = DATE_FORMAT("EEE MMM d", last_day), meet_s = DATE_FORMAT("EEE MMM d, yyyy", program.meet_date)',
    "session_header": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL date_s = DATE_FORMAT("EEEE, MMM d, yyyy", date) | KEEP program.*, date_s, start_time, time_of_day, location.name, location.travel, prev_session_id, next_session_id',
    "session_tiles": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP duration_min, streak_day, avg_working_rpe, totals.*, days_to_meet',
    "top_set": ('FROM workout-sets '
                '| WHERE set_type == "working" AND weight_lb > 0 AND (rep_unit IS NULL OR rep_unit == "reps") '
                '| SORT @timestamp DESC, weight_lb DESC, reps DESC '
                '| LIMIT 900 '
                '| EVAL date_s = DATE_FORMAT("MMM d", date) '
                '| KEEP session_id, date_s, lift_slug, exercise.name, weight_lb, reps, rpe'),
    "conditions": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP environment.*, time_of_day',
    "performance": 'FROM workout-sets | SORT @timestamp DESC, seq ASC | LIMIT 500 | EVAL gear_s = MV_CONCAT(gear, " / ") | KEEP session_id, set_number, exercise.name, exercise.category, set_type, load_type, weight_lb, reps, rep_unit, distance_ft, rpe, gear_s, notes',
    # WHERE phase != "watch": WRAP_CARD renders watch items in its own block, so
    # including them here printed the same sentence twice on the Session page.
    "notes": 'FROM workout-notes | WHERE phase != "watch" | SORT @timestamp DESC, order ASC | LIMIT 200 | EVAL tags_s = MV_CONCAT(tags, "|") | KEEP session_id, order, phase, exercise.name, text, tags_s',
    "wrap": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL watch_s = MV_CONCAT(watch_items, "|") | KEEP wrap_up, gear_notes, watch_s',
    "lift_header": 'FROM workout-sets | WHERE set_type == "working" AND is_competition_lift == true | EVAL e1c = CASE(e1rm_confidence == "low", 0.0, est_e1rm) | STATS e1 = MAX(e1c), top = MAX(weight_lb), rpe = AVG(rpe), n = COUNT(*), sessions = COUNT_DISTINCT(session_id), last_day = MAX(date), name = MAX(exercise.name) BY lift_slug | SORT last_day DESC | LIMIT 1 | EVAL last_s = DATE_FORMAT("MMM d, yyyy", last_day)',
    "history_cards": 'FROM workout-sessions | STATS ton = SUM(totals.tonnage_lb), avg = AVG(totals.tonnage_lb), n = COUNT(*), sets = SUM(totals.working_sets), rpe = AVG(avg_working_rpe)',
    "meet_cards": 'FROM workout-meets | EVAL m = CASE(made, 1, 0) | STATS meets = COUNT_DISTINCT(meet_id), total_kg = MAX(total_kg), total_lb = MAX(total_lb), dots = MAX(dots), made = SUM(m), attempts = COUNT(*)',
    "meet_list": 'FROM workout-meets | EVAL lift_no = CASE(lift == "squat", 1, lift == "bench", 2, 3), date_s = DATE_FORMAT("MMM d, yyyy", date) | SORT date DESC, lift_no ASC, attempt_no ASC | LIMIT 300 | KEEP meet_id, date_s, total_kg, dots, bodyweight_kg, lift, attempt_no, weight_kg, made',
    "recent_notes": 'FROM workout-notes | SORT @timestamp DESC, order ASC | LIMIT 12 | EVAL date_s = DATE_FORMAT("MMM d", date), tags_s = MV_CONCAT(tags, "|") | KEEP date_s, phase, exercise.name, text, tags_s',
    # Signal cards. NOTE: `first` and `last` are reserved words in ES|QL — an alias
    # named either fails with "no viable alternative at input". That is what broke
    # lift_header on Sept 4, misdiagnosed then as the CASE shifting the parse.
    #
    # COALESCE on every Prilepin bucket: a null bucket would null the whole sum and
    # silently drop the week out of the ranking.
    "sig_intensity": ('FROM workout-weekly | SORT @timestamp DESC | LIMIT 13 '
                      '| EVAL heavy = COALESCE(prilepin_reps.z80_89, 0) + COALESCE(prilepin_reps.z90plus, 0), '
                      'tot = COALESCE(prilepin_reps.lt70, 0) + COALESCE(prilepin_reps.z70_79, 0) '
                      '+ COALESCE(prilepin_reps.z80_89, 0) + COALESCE(prilepin_reps.z90plus, 0) '
                      '| KEEP iso_week, heavy, tot'),
    # 200 rows covers the whole 178-week history, which the precedent lookup needs:
    # the last time he was in this band can be years back.
    # No `WHERE acwr IS NOT NULL`: rows[0] must be the LATEST week so the card speaks
    # about now. Filtering nulls out meant the most recent week carrying an acwr was
    # presented as current, which for a week without one is a stale verdict.
    "sig_load": ('FROM workout-weekly | SORT @timestamp DESC | LIMIT 200 '
                 '| EVAL month_s = DATE_FORMAT("MMM yyyy", @timestamp) '
                 '| KEEP iso_week, month_s, acwr, acwr_band, monotony'),
    # lift_slug comes from the page control; it is kept in the result so the card can
    # follow one lift even if the control is cleared, the way lift_header does.
    "sig_lift": ('FROM workout-sets '
                 '| WHERE set_type == "working" AND e1rm_confidence != "low" '
                 'AND est_e1rm IS NOT NULL '
                 '| STATS e1 = MAX(est_e1rm), sess_d = MAX(date) BY session_id, lift_slug '
                 '| SORT sess_d DESC | LIMIT 200 '
                 '| EVAL when_s = DATE_FORMAT("MMM yyyy", sess_d) '
                 '| KEEP session_id, lift_slug, when_s, e1'),
    "sig_drift": ('FROM workout-sets '
                  '| WHERE set_type == "working" AND @timestamp >= NOW() - 365 days '
                  'AND muscles_primary IS NOT NULL '
                  '| MV_EXPAND muscles_primary '
                  '| STATS last_d = MAX(date), sessions = COUNT_DISTINCT(session_id) BY muscles_primary '
                  '| SORT last_d ASC | LIMIT 40'),
}

# --------------------------------------------------------------------------- shared Lens panels

SESSION_URL = (
    "{{kibanaUrl}}/app/dashboards#/view/" + DASH["session"] +
    "?_g=(time:(from:'{{context.panel.timeRange.from}}',to:'{{context.panel.timeRange.to}}'))"
    "&_a=(filters:!((meta:(alias:!n,disabled:!f,key:session_id,negate:!f,params:(query:'{{event.value}}'),type:phrase),"
    "query:(match_phrase:(session_id:'{{event.value}}')))))"
)


def block_timeline(id_, title="BLOCK TIMELINE", query=""):
    cols, colors = phase_columns("sum", "totals.tonnage_lb")
    columns = {"x": terms("session_id", "SESSION", size=300), **cols}
    return xy(id_, title, "bar_stacked", "sessions", columns, "x", list(cols), colors=colors,
              query=query)


def sessions_table(id_, title="SESSIONS"):
    columns = {
        "sid": terms("session_id", "SESSION", size=200, direction="desc"),
        "block": last("program.block", "BLOCK"),
        "loc": last("location.name", "WHERE"),
        "ton": last("totals.tonnage_lb", "TONNAGE", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "AVG RPE", "number", fmt=FMT_1),
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
        "sid": terms("session_id", "SESSION", size=size, direction="desc"),
        "n": count("NOTES", fmt=FMT_INT),
    }
    return table(id_, title, "notes", columns, sort="sid", direction="desc", page=50)


# --------------------------------------------------------------------------- build

def build() -> list[dict]:
    objs: list[dict] = [data_view(k) for k in DV]
    S, T, N, M, D, W = "sessions", "sets", "notes", "meets", "daily", "weekly"
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
    d.row((custom("ov-sig-intensity", tpl.SIGNAL_INTENSITY, Q["sig_intensity"]), 16, []),
          (custom("ov-sig-load", tpl.SIGNAL_LOAD, Q["sig_load"]), 16, []),
          (custom("ov-sig-drift", tpl.SIGNAL_DRIFT, Q["sig_drift"]), 16, []), h=10)
    # Watch items sit directly under the verdicts, on purpose. The drift card says
    # calves; these say grip, deadlift, lower back. Both are true — one measures volume
    # gaps, the other records what the lifter actually felt — and a lifter trusts the
    # thing he wrote himself. Nothing reconciles them and nothing should pretend to:
    # putting them adjacent makes the disagreement the point instead of an accident of
    # spacing. (A computed "recurring themes" card was considered and rejected: the note
    # corpus is ~28 documents and the real topic tags sit at 3-4 over a year.)
    d.row((custom("ov-watch", tpl.WATCH_CARD, Q["watch"]), 32, []),
          (custom("ov-days", tpl.DAYS_TO_MEET_CARD, Q["days"]), 16, []), h=11)
    d.row((custom("ov-total", tpl.total_card(MEET_MAX_LB), Q["total"]), 20, []),
          (xy(L("ov-total-chart"), "BEST e1RM PER WEEK. COMPETITION LIFTS", "bar_stacked", T,
              {"x": date_hist("date", "WEEK", "1w"), "lift": terms("lift_family", "LIFT", size=3),
               "m": metric("max", "est_e1rm", "BEST e1RM", fmt=FMT_INT)},
              "x", ["m"], split="lift", palette="gray", ref=(MEET_MAX_LB, "MEET BEST"),
              query='is_competition_lift: true and set_type: "working" and not e1rm_confidence: "low"'),
           28, [("lift", "Lift")]), h=11)
    # Streak, Latest session, Bodyweight and Sleep were cut from this page. Every one is
    # something a phone logging app shows better and shows at the gym, so here they only
    # told a lifter that Ironstack is a worse Strong. Bodyweight and Sleep also had one
    # reading between them in seven years of logs.
    # The block timeline stays as the door into a session. It is ~400 bars and is not
    # readable as a chart, which is why it is no longer above the fold.
    d.row((block_timeline(L("ov-timeline"), query=windowed("")), 48, [("session", "Session")]), h=10)
    objs += d.build()

    # ---------------------------------------------------------------- Program
    d = Dashboard("program", "Ironstack. Program", "Block, week, day. Pick a week, open a day.",
                  "The block, week by week. Click a day to open that session.", controls=[(S, "program.block", "BLOCK"), (S, "program.week", "WEEK")])
    d.row((custom("pr-header", tpl.PROGRAM_HEADER, Q["program_header"]), 48, []), h=6)

    weeks_cols = {
        "week": terms("program.week", "WEEK", size=60, dtype="number"),
        "n": count("SESSIONS", fmt=FMT_INT),
        "ton": metric("sum", "totals.tonnage_lb", "TONNAGE", fmt=FMT_INT),
        "rpe": metric("average", "avg_working_rpe", "AVG RPE", fmt=FMT_1),
    }
    weeks = table(L("pr-weeks"), "WEEKS. CLICK ONE TO FILTER", S, weeks_cols, sort="week", direction="desc")
    d.row((weeks, 48, []), h=6)
    days_cols = {
        "sid": terms("session_id", "SESSION", size=100, direction="desc"),
        # No DATE column: session_id is the date, and a date field renders in the
        # browser timezone, showing the previous evening. No DAY column either:
        # program.day is null on everything logged before the program was tracked.
        "ton": last("totals.tonnage_lb", "TONNAGE", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "AVG RPE", "number", fmt=FMT_1),
    }
    d.row((table(L("pr-days-table"), "OPEN A DAY. CLICK THE SESSION", S, days_cols, sort="sid",
                 direction="desc"), 48, [("session", "Session")]), h=8)
    loading_cols = {
        "week": terms("iso_week", "WEEK", size=60, direction="desc"),
        "lift": last("inol_hardest_lift", "HARDEST LIFT", sort="@timestamp"),
        "inol": last("inol_hardest", "INOL", "number", sort="@timestamp", fmt=FMT_1),
        # BAND and LOAD were words restating the number beside them ("0.4  easy").
        "acwr": last("acwr", "ACWR", "number", sort="@timestamp", fmt=FMT_1),
        "ton": last("tonnage_lb", "TONNAGE", "number", sort="@timestamp", fmt=FMT_INT),
    }
    d.row((table(L("pr-loading"), "WEEKLY LOADING. INOL IS PER LIFT, NOT PER WEEK", W, loading_cols,
                 sort="week", direction="desc", page=12), 48, []), h=10)
    objs += d.build()

    # ---------------------------------------------------------------- Session
    d = Dashboard("session", "Ironstack. Session", "One session. Arrives filtered to a session_id.", "One session, start to finish. Pick one above, or click any session elsewhere to land here.",
                  controls=[(S, "session_id", "SESSION")])
    # A Lens table of nothing but buckets renders no rows; the hidden count gives it one.
    nav_cols = {"sid": terms("session_id", "SESSION", size=1, direction="desc"),
                "prev": last("prev_session_id", "PREV", sort="timestamp"),
                "next": last("next_session_id", "NEXT", sort="timestamp")}
    nav = table(L("se-nav"), "PREV / NEXT. CLICK TO OPEN", S, nav_cols, sort="sid", direction="desc")
    d.row((custom("se-header", tpl.SESSION_HEADER, Q["session_header"]), 36, []),
          (nav, 12, [("url", SESSION_URL, "Open session")]), h=6)
    d.row((custom("se-top", tpl.TOP_SET_HERO, Q["top_set"]), 22, []),
          (custom("se-tiles", tpl.SESSION_TILES, Q["session_tiles"]), 26, []), h=7)

    d.row((custom("se-perf", tpl.PERFORMANCE_CARD, Q["performance"]), 48, []), h=15)
    d.row((custom("se-notes", tpl.NOTES_CARD, Q["notes"]), 32, []),
          (custom("se-wrap", tpl.WRAP_CARD, Q["wrap"]), 16, []), h=11)
    d.row((custom("se-cond", tpl.CONDITIONS_CARD, Q["conditions"]), 48, []), h=5)
    objs += d.build()

    # ---------------------------------------------------------------- Lift
    d = Dashboard("lift", "Ironstack. Lift", "One exercise over time. Arrives filtered to exercise.name.",
                  "One exercise over time. Pick a lift above, or click a lift anywhere to land here.",
                  controls=[(T, "lift_slug", "LIFT", ["comp-deadlift"]),
                            (T, "program.block", "BLOCK")], time_from="now-2y")
    d.row((custom("li-header", tpl.LIFT_HEADER, Q["lift_header"]), 48, []), h=6)
    e1_cols = {"x": terms("session_id", "SESSION", size=300), "m": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT)}
    e1 = xy(L("li-e1rm"), "e1RM OVER TIME", "line", T, e1_cols, "x", ["m"], colors={"m": BLOOD}, legend=False,
            query='set_type: "working" and not e1rm_confidence: "low"')
    # One measure per chart. Weight and RPE on two axes made the crossing points an
    # artifact of the scale ranges rather than anything in the data.
    top = xy(L("li-top"), "TOP SET OVER TIME", "line", T,
             {"x": terms("session_id", "SESSION", size=300), "m": metric("max", "weight_lb", "TOP SET", fmt=FMT_INT)},
             "x", ["m"], colors={"m": CHALK}, legend=False, query='set_type: "working"')
    zdist = xy(L("li-zones"), "WHERE THE REPS LAND. INTENSITY ZONE", "bar", T,
               {"x": terms("prilepin_zone", "ZONE", size=4),
                "v": metric("sum", "reps", "REPS", fmt=FMT_INT)},
               "x", ["v"], colors={"v": CHALK_DIM}, legend=False, query='set_type: "working"')
    # The verdict leads, and the charts it is drawn from sit beside it. Both charts are
    # honest and neither answers "is this going up" on its own: they are sawtooths.
    d.row((custom("li-signal", tpl.SIGNAL_LIFT, Q["sig_lift"]), 18, []),
          (e1, 30, [("session", "Session")]), h=10)
    d.row((top, 24, [("session", "Session")]), (zdist, 24, []), h=8)
    all_cols = {
        "sid": terms("session_id", "SESSION", size=300, direction="desc"),
        "seq": terms("seq", "#", size=200, dtype="number"),
        "w": last("weight_lb", "LB", "number", fmt=FMT_INT),
        "reps": last("reps", "REPS", "number"),
        "rpe": last("rpe", "RPE", "number", fmt=FMT_1),
        "e1rm": last("est_e1rm", "e1RM", "number", fmt=FMT_INT),
        "notes": last("notes.keyword", "NOTES"),
    }
    d.row((table(L("li-sets"), "WORKING SETS. CLICK A SESSION", T, all_cols, sort="sid", direction="desc",
                 page=50, query='set_type: "working"', row_height="auto"), 48, [("session", "Session")]), h=12)
    objs += d.build()

    # ---------------------------------------------------------------- History
    d = Dashboard("history", "Ironstack. History", "Sessions over any range. The time picker is the range toggle.",
                  "Every session in the range. The time picker is the range.", controls=[(S, "program.block", "BLOCK"), (S, "program.phase", "PHASE")])
    d.row((custom("hi-cards", tpl.FOUR_CARDS, Q["history_cards"]), 48, []), h=6)
    d.row((block_timeline(L("hi-timeline"), "TONNAGE PER SESSION"), 48, [("session", "Session")]), h=9)
    tod = xy(L("hi-tod"), "TONNAGE BY TIME OF DAY", "bar", S,
             {"x": terms("time_of_day", "WHEN", size=4),
              "t": metric("average", "totals.tonnage_lb", "AVG TONNAGE", fmt=FMT_INT)},
             "x", ["t"], colors={"t": CHALK_DIM}, legend=False)
    d.row((tod, 48, []), h=8)
    acwr = xy(L("hi-acwr"), "ACUTE VS CHRONIC LOAD. 7 DAY OVER 28 DAY", "line", W,
              {"x": date_hist("@timestamp", "WEEK", "1w"), "m": metric("max", "acwr", "ACWR", fmt=FMT_1)},
              "x", ["m"], colors={"m": CHALK}, legend=False, ref=(1.0, "BASELINE"))
    d.row((acwr, 48, []), h=8)
    zcols, zcolors = zone_columns()
    zone_cols = {"x": date_hist("date", "MONTH", "1M"), **zcols}
    zones = xy(L("hi-zones"), "SHARE OF REPS BY INTENSITY ZONE. MAIN LIFTS", "bar_percentage_stacked", T,
               zone_cols, "x", list(zcols), colors=zcolors,
               query='set_type: "working" and exercise.category: "main"')
    d.row((zones, 48, []), h=9)
    d.row((sessions_table(L("hi-sessions")), 48, [("session", "Session")]), h=10)
    objs += d.build()

    # ---------------------------------------------------------------- Meets
    d = Dashboard("meets", "Ironstack. Meets", "Competition record. Click a best lift for its training history.",
                  "The platform record. Click a best lift to see how it was trained.", time_from="now-10y")
    d.row((custom("me-cards", tpl.MEET_CARDS, Q["meet_cards"]), 48, []), h=6)
    d.row((custom("me-best", tpl.MEET_BESTS, Q["meet_bests"]), 48, []), h=8)
    d.row((custom("me-list", tpl.MEET_LIST, Q["meet_list"]), 48, []), h=11)
    objs += d.build()

    # ---------------------------------------------------------------- Mindset
    d = Dashboard("mindset", "Ironstack. Mindset", "Every note. Search above; semantic where ELSER is on.",
                  "Everything you wrote, searchable. Click a note to open its session.")
    tag_cols = {"x": terms("tags", "TAG", size=25, by_col="c", direction="desc"), "c": count("NOTES")}
    tags = xy(L("mi-tags"), "TAGS. CLICK TO FILTER", "bar_horizontal", N, tag_cols, "x", ["c"], colors={"c": CHALK_DIM}, legend=False)
    # TAGS OVER TIME was three stacked bars under a twelve-entry legend that filled the
    # panel. The bar chart says the same thing and can be clicked.
    d.row((tags, 48, []), h=9)
    d.row((custom("mi-recent", tpl.RECENT_NOTES, Q["recent_notes"]), 32, []),
          (notes_table(L("mi-notes"), "OPEN THE SESSION BEHIND A NOTE"), 16, [("session", "Session")]), h=12)
    objs += d.build()

    # de-duplicate by (type, id): shared builders are called for more than one dashboard
    seen, out = set(), []
    for o in objs:
        key = (o["type"], o["id"])
        if key not in seen:
            seen.add(key)
            out.append(o)
    return out


def check(objs: list[dict]) -> int:
    """Duplicate ids and dangling references, the two ways this file breaks silently.

    A duplicate id means one object quietly overwrites another on import; a dangling
    reference means a panel imports fine and then renders an error where a chart
    should be. Both were checked by hand after the Sept 4 build; now they are checked
    by the build.
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

    for label, items in (("duplicate id", dupes), ("dangling reference", dangling)):
        for item in items:
            print(f"  {label}: {item}")
    bad = len(dupes) + len(dangling)
    print(f"check: {len(objs)} objects, {len(dupes)} duplicate ids, {len(dangling)} dangling references")
    return bad


def main() -> None:
    objs = build()
    if "--check" in sys.argv:
        sys.exit(1 if check(objs) else 0)
    ndjson = "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(ndjson)
        return
    if check(objs):
        sys.exit("refusing to write a broken dashboards.ndjson")
    OUT.write_text(ndjson)
    kinds = {}
    for o in objs:
        kinds[o["type"]] = kinds.get(o["type"], 0) + 1
    print(f"wrote {OUT.name}: " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    if not COACH_URL:
        print("  note: IRONSTACK_COACH_URL is unset, so ASK THE COACH was not built. "
              "Importing this file removes the link from all seven dashboards.")


if __name__ == "__main__":
    main()
