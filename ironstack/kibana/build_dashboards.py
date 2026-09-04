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

PHASES = [  # order is the training arc
    ("hypertrophy", "Hypertrophy", "#5a564f"),
    ("strength", "Strength", "#a8a094"),
    ("peaking", "Peaking", "#7a7873"),
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


def unique(field, label):
    return _col(label, "unique_count", "number", "ratio", field, params={"emptyAsNull": True})


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
    L = {"columns": columns, "columnOrder": order or list(columns), "incompleteColumns": {}, "sampling": 1}
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
       query="", legend=True, right_axis=(), palette=None):
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
        data_layer["palette"] = {"type": "palette", "name": palette}
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
    return lens(id_, title, "lnsXY", vis, layers, query=query)


def metric_vis(id_, title, dv, columns, primary, secondary=None, breakdown=None, max_cols=3,
               color=None, trend=None, query="", subtitle=None):
    """lnsMetric. trend: (time field, metric column factory) adds a sparkline layer."""
    vis = {"layerId": "l", "layerType": "data", "metricAccessor": primary, "maxCols": max_cols,
           "showBar": False}
    if secondary:
        vis["secondaryMetricAccessor"] = secondary
    if breakdown:
        vis["breakdownByAccessor"] = breakdown
    if color:
        vis["color"] = color
    if subtitle:
        vis["subtitle"] = subtitle
    layers = {"l": (dv, layer(columns))}
    if trend:
        time_field, make_metric = trend
        tcols = {"t-date": date_hist(time_field, "DATE"), "t-metric": make_metric()}
        order = ["t-date", "t-metric"]
        if breakdown:
            t_breakdown = copy.deepcopy(columns[breakdown])
            order_by = t_breakdown.get("params", {}).get("orderBy") or {}
            if order_by.get("type") == "column":
                order_by["columnId"] = "t-metric"
            tcols["t-breakdown"] = t_breakdown
            order = ["t-breakdown", "t-date", "t-metric"]
            vis["trendlineBreakdownByAccessor"] = "t-breakdown"
        layers["trend"] = (dv, layer(tcols, order, link_to="l"))
        vis.update({"trendlineLayerId": "trend", "trendlineLayerType": "metricTrendline",
                    "trendlineTimeAccessor": "t-date", "trendlineMetricAccessor": "t-metric"})
    return lens(id_, title, "lnsMetric", vis, layers, query=query)


def table(id_, title, dv, columns, sort=None, direction="asc", hidden=(), query="", page=20):
    vis = {
        "layerId": "l", "layerType": "data",
        "columns": [{"columnId": c, "alignment": "left", **({"hidden": True} if c in hidden else {})} for c in columns],
        "rowHeight": "single", "headerRowHeight": "single",
        "paging": {"size": page, "enabled": True},
    }
    if sort:
        vis["sorting"] = {"columnId": sort, "direction": direction}
    return lens(id_, title, "lnsDatatable", vis, {"l": (dv, layer(columns))}, query=query)


def heat_palette(top=BLOOD):
    stops = [RULE, STEEL, top]
    return {"type": "palette", "name": "custom", "params": {
        "name": "custom", "continuity": "above", "reverse": False, "rangeType": "percent",
        "rangeMin": 0, "rangeMax": 100, "steps": 3,
        "colorStops": [{"color": c, "stop": s} for c, s in zip(stops, (0, 40, 75))],
        "stops": [{"color": c, "stop": s} for c, s in zip(stops, (40, 75, 100))],
    }}


def heatmap(id_, title, dv, columns, x, y, value, query="", top=BLOOD):
    vis = {
        "layerId": "l", "layerType": "data", "shape": "heatmap",
        "xAccessor": x, "yAccessor": y, "valueAccessor": value,
        "legend": {"isVisible": False, "position": "right", "type": "heatmap_legend"},
        "gridConfig": {"type": "heatmap_grid", "isCellLabelVisible": False, "isYAxisLabelVisible": True,
                       "isXAxisLabelVisible": True, "isYAxisTitleVisible": False, "isXAxisTitleVisible": False},
        "palette": heat_palette(top),
    }
    return lens(id_, title, "lnsHeatmap", vis, {"l": (dv, layer(columns))}, query=query)


def markdown(id_, title, text):
    return {
        "id": id_,
        "type": "visualization",
        "attributes": {
            "title": title,
            "description": "",
            "version": 1,
            "uiStateJSON": "{}",
            "visState": json.dumps({"title": title, "type": "markdown", "aggs": [],
                                    "params": {"fontSize": 12, "openLinksInNewTab": False, "markdown": text}}),
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"query": {"query": "", "language": "kuery"}, "filter": []})},
        },
        "references": [],
        **MIGRATION,
        "typeMigrationVersion": "8.5.0",
    }


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


def session_map(id_):
    """Maps saved object: one dot per session on a desaturated basemap. Best effort."""
    layers_ = [
        {"id": "base", "type": "EMS_VECTOR_TILE", "alpha": 1, "visible": True, "minZoom": 0, "maxZoom": 24,
         "sourceDescriptor": {"type": "EMS_TMS", "isAutoSelect": True, "lightModeDefault": "road_map_desaturated"},
         "style": {"type": "EMS_VECTOR_TILE", "color": ""}},
        {"id": "sessions", "type": "GEOJSON_VECTOR", "label": "Sessions", "alpha": 0.9, "visible": True,
         "minZoom": 0, "maxZoom": 24,
         "sourceDescriptor": {"type": "ES_SEARCH", "geoField": "location.geo", "scalingType": "LIMIT",
                              "topHitsSize": 1, "tooltipProperties": ["location.name", "date"],
                              "applyGlobalQuery": True, "applyGlobalTime": True, "filterByMapBounds": False,
                              "indexPatternRefName": "layer_1_source_index_pattern"},
         "style": {"type": "VECTOR", "isTimeAware": True, "properties": {
             "fillColor": {"type": "STATIC", "options": {"color": BLOOD}},
             "lineColor": {"type": "STATIC", "options": {"color": CHALK}},
             "lineWidth": {"type": "STATIC", "options": {"size": 1}},
             "iconSize": {"type": "STATIC", "options": {"size": 8}},
             "symbolizeAs": {"options": {"value": "circle"}}}}},
    ]
    return {
        "id": id_,
        "type": "map",
        "attributes": {
            "title": "WHERE",
            "description": "",
            "layerListJSON": json.dumps(layers_),
            "mapStateJSON": json.dumps({"zoom": 4, "center": {"lon": -80, "lat": 40},
                                        "timeFilters": {"from": "now-1y", "to": "now"},
                                        "refreshConfig": {"isPaused": True, "interval": 0},
                                        "query": {"query": "", "language": "kuery"}, "filters": [],
                                        "settings": {"autoFitToDataBounds": True}}),
            "uiStateJSON": json.dumps({"isLayerTOCOpen": False, "openTOCDetails": []}),
        },
        "references": [{"name": "layer_1_source_index_pattern", "type": "index-pattern", "id": DV["sessions"][0]}],
        **MIGRATION,
        "typeMigrationVersion": "8.4.0",
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
    """Custom content panel. Liquid only runs when a query is attached."""
    return Inline(key, "custom_content", {"esql_query": [esql] if esql else [], "template": template,
                                          "hidePanelTitles": True})


NAV_ORDER = ["overview", "program", "session", "lift", "history", "meets", "mindset"]


def links(current: str) -> Inline:
    """Kibana Links panel: the app nav. Carries filters and time so context survives a hop."""
    items, refs = [], []
    for key in NAV_ORDER:
        link_id = uid("nav", current, key)
        items.append({"type": "dashboardLink", "label": key.upper() if key != current else f"[ {key.upper()} ]",
                      "options": {"open_in_new_tab": False, "use_time_range": True, "use_filters": True},
                      "destinationRefName": f"link_{link_id}_dashboard"})
        refs.append({"name": f"link_{link_id}_dashboard", "type": "dashboard", "id": DASH[key]})
    return Inline(f"nav-{current}", "links", {"title": "", "layout": "horizontal", "links": items,
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
        self.controls = controls or []  # (data view key, field, label)
        self.time_from = time_from
        self.panels: list[dict] = []
        self.refs: list[dict] = []
        self.y = 0
        self.objects: list[dict] = []  # saved objects this dashboard owns (Lens etc.)
        # chrome: brand bar + nav
        self.row((custom(f"brand-{key}", brand_bar(key.upper(), tagline)), 48, []), h=4)
        self.row((links(key), 48, []), h=2)

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
            for order, (dv, field, label) in enumerate(self.controls):
                cid = uid(self.id, "control", field)
                panels[cid] = {"type": "optionsListControl", "order": order, "grow": False, "width": "small",
                               "explicitInput": {"id": cid, "fieldName": field, "title": label,
                                                 "selectedOptions": [], "searchTechnique": "prefix",
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
    "total": 'FROM workout-weekly | WHERE projected_total_lb IS NOT NULL | SORT @timestamp DESC | LIMIT 1 | EVAL total = projected_total_lb, lifts = 3 | KEEP total, lifts',
    "streak": 'FROM workout-sessions | EVAL in7 = CASE(date >= NOW() - 7 days, 1, 0), in28 = CASE(date >= NOW() - 28 days, 1, 0) | STATS n7 = SUM(in7), n28 = SUM(in28), streak = MAX(streak_day)',
    "latest": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL date_s = DATE_FORMAT("EEE MMM d", date) | KEEP date_s, program.block, program.day, time_of_day, totals.*, avg_working_rpe, wrap_up',
    "watch": 'FROM workout-sessions | WHERE watch_items IS NOT NULL | SORT @timestamp DESC | LIMIT 12 | MV_EXPAND watch_items | EVAL date_s = DATE_FORMAT("MMM d", date), item = watch_items | KEEP date_s, item',
    "bodyweight": 'FROM workout-sessions | WHERE metrics.bodyweight_lb IS NOT NULL | SORT @timestamp ASC | LIMIT 90 | EVAL v = metrics.bodyweight_lb | KEEP v',
    "sleep": 'FROM workout-sessions | WHERE metrics.sleep_hrs IS NOT NULL | SORT @timestamp ASC | LIMIT 90 | EVAL v = metrics.sleep_hrs | KEEP v',
    "program_header": 'FROM workout-sessions | EVAL wd = program.week * 100 + program.day | STATS n = COUNT(*), wd_max = MAX(wd), last = MAX(date) BY program.name, program.block, program.phase, program.total_days, program.meet_date | SORT last DESC | LIMIT 1 | EVAL program.week = FLOOR(wd_max / 100), program.day = wd_max % 100, date_s = DATE_FORMAT("EEE MMM d", last), meet_s = DATE_FORMAT("EEE MMM d, yyyy", program.meet_date)',
    "days_list": 'FROM workout-sessions | SORT date ASC | LIMIT 200 | EVAL date_s = DATE_FORMAT("EEE MMM d", date) | KEEP program.week, program.day, date_s, time_of_day, location.name, totals.tonnage_lb, avg_working_rpe, duration_min',
    "session_header": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL date_s = DATE_FORMAT("EEEE, MMM d, yyyy", date) | KEEP program.*, date_s, start_time, time_of_day, location.name, location.travel, prev_session_id, next_session_id',
    "session_tiles": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP duration_min, streak_day, avg_working_rpe, totals.*, days_to_meet',
    "session_tonnage": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP totals.tonnage_lb',
    "conditions": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | KEEP environment.*, time_of_day',
    "performance": 'FROM workout-sets | SORT seq ASC | LIMIT 500 | EVAL gear_s = MV_CONCAT(gear, " / ") | KEEP set_number, exercise.name, exercise.category, set_type, load_type, weight_lb, reps, rep_unit, distance_ft, rpe, gear_s, notes',
    "notes": 'FROM workout-notes | SORT order ASC | LIMIT 200 | EVAL tags_s = MV_CONCAT(tags, "|") | KEEP order, phase, exercise.name, text, tags_s',
    "wrap": 'FROM workout-sessions | SORT @timestamp DESC | LIMIT 1 | EVAL watch_s = MV_CONCAT(watch_items, "|") | KEEP wrap_up, gear_notes, watch_s',
    "lift_header": 'FROM workout-sets | WHERE set_type == "working" | EVAL e1c = CASE(e1rm_confidence == "low", 0.0, est_e1rm) | STATS e1 = MAX(e1c), top = MAX(weight_lb), rpe = AVG(rpe), n = COUNT(*), sessions = COUNT_DISTINCT(session_id), last_day = MAX(date) BY exercise.name | SORT n DESC | LIMIT 1 | EVAL last_s = DATE_FORMAT("MMM d, yyyy", last_day)',
    "history_cards": 'FROM workout-sessions | STATS ton = SUM(totals.tonnage_lb), avg = AVG(totals.tonnage_lb), n = COUNT(*), sets = SUM(totals.working_sets), rpe = AVG(avg_working_rpe)',
    "meet_cards": 'FROM workout-meets | EVAL m = CASE(made, 1, 0) | STATS meets = COUNT_DISTINCT(meet_id), total_kg = MAX(total_kg), total_lb = MAX(total_lb), dots = MAX(dots), made = SUM(m), attempts = COUNT(*)',
    "meet_list": 'FROM workout-meets | EVAL lift_no = CASE(lift == "squat", 1, lift == "bench", 2, 3), date_s = DATE_FORMAT("MMM d, yyyy", date) | SORT date DESC, lift_no ASC, attempt_no ASC | LIMIT 300 | KEEP meet_id, date_s, total_kg, dots, bodyweight_kg, lift, attempt_no, weight_kg, made',
    "recent_notes": 'FROM workout-notes | SORT @timestamp DESC, order ASC | LIMIT 12 | EVAL date_s = DATE_FORMAT("MMM d", date), tags_s = MV_CONCAT(tags, "|") | KEEP date_s, phase, exercise.name, text, tags_s',
}

# --------------------------------------------------------------------------- shared Lens panels

SESSION_URL = (
    "{{kibanaUrl}}/app/dashboards#/view/" + DASH["session"] +
    "?_g=(time:(from:'{{context.panel.timeRange.from}}',to:'{{context.panel.timeRange.to}}'))"
    "&_a=(filters:!((meta:(alias:!n,disabled:!f,key:session_id,negate:!f,params:(query:'{{event.value}}'),type:phrase),"
    "query:(match_phrase:(session_id:'{{event.value}}')))))"
)


def block_timeline(id_, title="BLOCK TIMELINE"):
    cols, colors = phase_columns("sum", "totals.tonnage_lb")
    columns = {"x": terms("session_id", "SESSION", size=300), **cols}
    return xy(id_, title, "bar_stacked", "sessions", columns, "x", list(cols), colors=colors)


def calendar(id_, title="CALENDAR"):
    columns = {"x": date_hist("date", "WEEK", "1w"), "y": terms("weekday", "DAY", size=7), "v": count("SESSIONS")}
    return heatmap(id_, title, "sessions", columns, "x", "y", "v")


def sessions_table(id_, title="SESSIONS"):
    columns = {
        "sid": terms("session_id", "SESSION", size=200, direction="desc"),
        "date": last("date", "DATE", "date"),
        "block": last("program.block", "BLOCK"),
        "week": last("program.week", "WEEK", "number"),
        "day": last("program.day", "DAY", "number"),
        "loc": last("location.name", "WHERE"),
        "dur": last("duration_min", "MIN", "number", fmt=FMT_INT),
        "ton": last("totals.tonnage_lb", "TONNAGE", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "AVG RPE", "number", fmt=FMT_1),
    }
    return table(id_, title, "sessions", columns, sort="sid", direction="desc")


def notes_table(id_, title, size=20):
    columns = {
        "sid": terms("session_id", "SESSION", size=size, direction="desc"),
        "order": terms("order", "#", size=50, dtype="number"),
        "phase": last("phase", "PHASE"),
        "ex": last("exercise.name", "EXERCISE"),
        "text": last("text.keyword", "NOTE"),
        "tags": last("tags", "TAGS", arrays=True),
    }
    return table(id_, title, "notes", columns, sort="sid", direction="desc", page=50)


# --------------------------------------------------------------------------- build

def build() -> list[dict]:
    objs: list[dict] = [data_view(k) for k in DV]
    S, T, N, M, D, W = "sessions", "sets", "notes", "meets", "daily", "weekly"
    L = lambda name: f"ironstack-lens-{name}"  # noqa: E731

    # ---------------------------------------------------------------- Overview
    d = Dashboard("overview", "Ironstack. Overview", "The block at a glance. Every chart opens its detail.",
                  "Training at a glance.")
    d.row((custom("ov-days", tpl.DAYS_TO_MEET_CARD, Q["days"]), 16, []),
          (block_timeline(L("ov-timeline")), 32, [("session", "Session")]), h=10)
    lifts = metric_vis(L("ov-lifts"), "BEST e1RM. THIS BLOCK. CLICK A LIFT", T,
                       {"m": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT),
                        "b": terms("exercise.name", "LIFT", size=3, by_col="m", direction="desc")},
                       "m", breakdown="b", max_cols=3,
                       trend=("date", lambda: metric("max", "est_e1rm", "e1RM", fmt=FMT_INT)),
                       query='is_competition_lift: true and set_type: "working" and not e1rm_confidence: "low"')
    d.row((lifts, 48, [("lift", "Lift")]), h=9)
    total_cols = {"x": date_hist("date", "WEEK", "1w"), "lift": terms("lift_family", "LIFT", size=3),
                  "m": metric("max", "est_e1rm", "BEST e1RM", fmt=FMT_INT)}
    total = xy(L("ov-total"), "TOTAL VS MEET MAX", "bar_stacked", T, total_cols, "x", ["m"], split="lift",
               palette="gray", ref=(MEET_MAX_LB, "MEET MAX"),
               query='is_competition_lift: true and set_type: "working" and not e1rm_confidence: "low"')
    d.row((custom("ov-total", tpl.total_card(MEET_MAX_LB), Q["total"]), 16, []), (total, 32, []), h=9)
    readiness = metric_vis(L("ov-readiness"), "READINESS. LATEST WEEK", W,
                           {"m": last("acwr", "ACWR", "number", sort="@timestamp", fmt=FMT_1),
                            "s": last("monotony", "MONOTONY", "number", sort="@timestamp", fmt=FMT_1)},
                           "m", secondary="s", max_cols=1)
    dots = xy(L("ov-dots"), "DOTS TRAJECTORY. COMP LIFTS", "line", W,
              {"x": date_hist("@timestamp", "WEEK", "1w"), "m": metric("max", "dots", "DOTS", fmt=FMT_1)},
              "x", ["m"], colors={"m": BLOOD}, legend=False, ref=(MEET_BEST_DOTS, "BEST MEET"))
    d.row((readiness, 16, []), (dots, 32, []), h=9)
    d.row((calendar(L("ov-calendar")), 20, [("history", "History")]),
          (custom("ov-streak", tpl.STREAK_CARD, Q["streak"]), 12, []),
          (custom("ov-latest", tpl.LATEST_CARD, Q["latest"]), 16, []), h=9)
    rpe_cols = {"x": terms("rpe", "RPE", size=20, dtype="number"), "c": count("WORKING SETS")}
    rpe_hist = xy(L("ov-rpe"), "WORKING SET RPE", "bar", T, rpe_cols, "x", ["c"], colors={"c": CHALK_DIM},
                  query='set_type: "working"', legend=False)
    d.row((custom("ov-watch", tpl.WATCH_CARD, Q["watch"]), 24, []), (rpe_hist, 24, []), h=8)
    d.row((custom("ov-bw", tpl.metric_card("Bodyweight", "lb"), Q["bodyweight"]), 24, []),
          (custom("ov-sleep", tpl.metric_card("Sleep", "hrs"), Q["sleep"]), 24, []), h=6)
    objs += d.build()

    # ---------------------------------------------------------------- Program
    d = Dashboard("program", "Ironstack. Program", "Block, week, day. Pick a week, open a day.",
                  "Block. Week. Day.", controls=[(S, "program.block", "BLOCK"), (S, "program.week", "WEEK")])
    d.row((custom("pr-header", tpl.PROGRAM_HEADER, Q["program_header"]), 48, []), h=6)
    d.row((block_timeline(L("pr-timeline")), 48, [("session", "Session")]), h=8)
    weeks_cols = {
        "week": terms("program.week", "WEEK", size=60, dtype="number"),
        "n": count("SESSIONS", fmt=FMT_INT),
        "ton": metric("sum", "totals.tonnage_lb", "TONNAGE", fmt=FMT_INT),
        "rpe": metric("average", "avg_working_rpe", "AVG RPE", fmt=FMT_1),
    }
    weeks = table(L("pr-weeks"), "WEEKS. CLICK ONE TO FILTER", S, weeks_cols, sort="week")
    d.row((custom("pr-days", tpl.DAYS_LIST, Q["days_list"]), 28, []), (weeks, 20, []), h=10)
    days_cols = {
        "sid": terms("session_id", "SESSION", size=100),
        "day": last("program.day", "DAY", "number"),
        "date": last("date", "DATE", "date"),
        "ton": last("totals.tonnage_lb", "TONNAGE", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "AVG RPE", "number", fmt=FMT_1),
    }
    d.row((table(L("pr-days-table"), "OPEN A DAY. CLICK THE SESSION", S, days_cols, sort="sid"), 48, [("session", "Session")]), h=8)
    loading_cols = {
        "week": terms("iso_week", "WEEK", size=60, direction="desc"),
        "lift": last("inol_hardest_lift", "HARDEST LIFT", sort="@timestamp"),
        "inol": last("inol_hardest", "INOL", "number", sort="@timestamp", fmt=FMT_1),
        "band": last("inol_hardest_band", "BAND", sort="@timestamp"),
        "acwr": last("acwr", "ACWR", "number", sort="@timestamp", fmt=FMT_1),
        "load": last("acwr_band", "LOAD", sort="@timestamp"),
        "ton": last("tonnage_lb", "TONNAGE", "number", sort="@timestamp", fmt=FMT_INT),
    }
    d.row((table(L("pr-loading"), "WEEKLY LOADING. INOL IS PER LIFT, NOT PER WEEK", W, loading_cols,
                 sort="week", direction="desc", page=12), 48, []), h=10)
    objs += d.build()

    # ---------------------------------------------------------------- Session
    d = Dashboard("session", "Ironstack. Session", "One session. Arrives filtered to a session_id.", "One session.")
    nav_cols = {"prev": terms("prev_session_id", "PREV", size=1), "next": terms("next_session_id", "NEXT", size=1)}
    nav = table(L("se-nav"), "PREV / NEXT. CLICK TO OPEN", S, nav_cols)
    d.row((custom("se-header", tpl.SESSION_HEADER, Q["session_header"]), 36, []),
          (nav, 12, [("url", SESSION_URL, "Open session")]), h=7)
    d.row((custom("se-tonnage", tpl.TONNAGE_HERO, Q["session_tonnage"]), 12, []),
          (custom("se-tiles", tpl.SESSION_TILES, Q["session_tiles"]), 36, []), h=6)
    smap = session_map("ironstack-map-session")
    d.row((smap, 24, []), (custom("se-cond", tpl.CONDITIONS_CARD, Q["conditions"]), 24, []), h=8)
    d.row((custom("se-perf", tpl.PERFORMANCE_CARD, Q["performance"]), 48, []), h=16)
    sets_cols = {
        "ex": terms("exercise.name", "LIFT. CLICK FOR HISTORY", size=50),
        "n": count("SETS", fmt=FMT_INT),
        "w": metric("max", "weight_lb", "TOP LB", fmt=FMT_INT),
        "e1": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT),
        "vol": metric("sum", "volume_lb", "VOLUME", fmt=FMT_INT),
    }
    sets_t = table(L("se-sets"), "BY EXERCISE", T, sets_cols)
    rpe_line = xy(L("se-rpe-line"), "RPE BY SET", "line", T,
                  {"x": terms("seq", "#", size=200, dtype="number"), "ex": terms("exercise.name", "EXERCISE", size=20),
                   "m": metric("max", "rpe", "RPE", fmt=FMT_1)}, "x", ["m"], split="ex", palette="gray")
    d.row((sets_t, 20, [("lift", "Lift")]), (rpe_line, 28, []), h=9)
    d.row((custom("se-notes", tpl.NOTES_CARD, Q["notes"]), 32, []),
          (custom("se-wrap", tpl.WRAP_CARD, Q["wrap"]), 16, []), h=11)
    objs += d.build()

    # ---------------------------------------------------------------- Lift
    d = Dashboard("lift", "Ironstack. Lift", "One exercise over time. Arrives filtered to exercise.name.",
                  "One lift. Every set.", controls=[(T, "program.block", "BLOCK")], time_from="now-2y")
    d.row((custom("li-header", tpl.LIFT_HEADER, Q["lift_header"]), 48, []), h=6)
    e1_cols = {"x": terms("session_id", "SESSION", size=300), "m": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT)}
    e1 = xy(L("li-e1rm"), "e1RM OVER TIME", "line", T, e1_cols, "x", ["m"], colors={"m": BLOOD}, legend=False,
            query='set_type: "working" and not e1rm_confidence: "low"')
    top_cols = {"x": terms("session_id", "SESSION", size=300), "m": metric("max", "weight_lb", "TOP SET", fmt=FMT_INT),
                "p": metric("max", "rpe", "RPE", fmt=FMT_1)}
    top = xy(L("li-top"), "TOP SET OVER TIME", "line", T, top_cols, "x", ["m", "p"], colors={"m": CHALK, "p": CHALK_FAINT},
             right_axis=("p",), query='set_type: "working"')
    d.row((e1, 24, [("session", "Session")]), (top, 24, [("session", "Session")]), h=9)
    pcols, pcolors = phase_columns("sum", "volume_lb")
    lvol = xy(L("li-vol"), "VOLUME PER SESSION", "bar_stacked", T, {"x": terms("session_id", "SESSION", size=300), **pcols},
              "x", list(pcols), colors=pcolors)
    load_cols = {"x": terms("weight_lb", "LB", size=40, dtype="number"), "y": terms("rpe", "RPE", size=20, dtype="number"),
                 "v": count("SETS")}
    load = heatmap(L("li-load"), "RPE VS LOAD", T, load_cols, "x", "y", "v", query='set_type: "working"', top=CHALK)
    d.row((lvol, 24, [("session", "Session")]), (load, 24, []), h=9)
    inol = xy(L("li-inol"), "INOL PER SESSION", "bar", T,
              {"x": terms("session_id", "SESSION", size=300), "m": metric("sum", "inol", "INOL", fmt=FMT_1)},
              "x", ["m"], colors={"m": CHALK_DIM}, legend=False, query='set_type: "working"')
    zdist = xy(L("li-zones"), "REPS BY INTENSITY ZONE", "bar", T,
               {"x": terms("prilepin_zone", "ZONE", size=4),
                "v": metric("sum", "reps", "REPS", fmt=FMT_INT)},
               "x", ["v"], colors={"v": CHALK_DIM}, legend=False, query='set_type: "working"')
    d.row((inol, 24, [("session", "Session")]), (zdist, 24, []), h=9)
    all_cols = {
        "sid": terms("session_id", "SESSION", size=300, direction="desc"),
        "seq": terms("seq", "#", size=200, dtype="number"),
        "type": last("set_type", "TYPE"),
        "w": last("weight_lb", "LB", "number", fmt=FMT_INT),
        "reps": last("reps", "REPS", "number"),
        "rpe": last("rpe", "RPE", "number", fmt=FMT_1),
        "e1rm": last("est_e1rm", "e1RM", "number", fmt=FMT_INT),
        "gear": last("gear", "GEAR", arrays=True),
        "notes": last("notes.keyword", "NOTES"),
    }
    d.row((table(L("li-sets"), "ALL SETS. CLICK A SESSION", T, all_cols, sort="sid", direction="desc", page=50), 48,
           [("session", "Session")]), h=12)
    d.row((notes_table(L("li-notes"), "NOTES ABOUT THIS LIFT"), 48, [("session", "Session")]), h=8)
    objs += d.build()

    # ---------------------------------------------------------------- History
    d = Dashboard("history", "Ironstack. History", "Sessions over any range. The time picker is the range toggle.",
                  "Every session.", controls=[(S, "program.block", "BLOCK"), (S, "program.phase", "PHASE")])
    d.row((custom("hi-cards", tpl.FOUR_CARDS, Q["history_cards"]), 48, []), h=6)
    d.row((block_timeline(L("hi-timeline"), "TONNAGE PER SESSION"), 48, [("session", "Session")]), h=9)
    tod_cols = {"x": terms("time_of_day", "WHEN", size=4), "t": metric("average", "totals.tonnage_lb", "AVG TONNAGE", fmt=FMT_INT),
                "r": metric("average", "avg_working_rpe", "AVG RPE", fmt=FMT_1)}
    tod = xy(L("hi-tod"), "TIME OF DAY", "bar", S, tod_cols, "x", ["t", "r"], colors={"t": CHALK_DIM, "r": CHALK_FAINT},
             right_axis=("r",))
    d.row((calendar(L("hi-calendar")), 24, [("session", "Session")]), (tod, 24, []), h=9)
    env_cols = {"x": terms("environment.temp_f", "TEMP F", size=40, dtype="number"),
                "t": metric("average", "totals.tonnage_lb", "AVG TONNAGE", fmt=FMT_INT),
                "r": metric("average", "avg_working_rpe", "AVG RPE", fmt=FMT_1)}
    env = xy(L("hi-env"), "TEMPERATURE VS EFFORT", "bar", S, env_cols, "x", ["t", "r"],
             colors={"t": CHALK_DIM, "r": CHALK_FAINT}, right_axis=("r",))
    d.row((env, 48, []), h=8)
    acwr = xy(L("hi-acwr"), "ACUTE VS CHRONIC LOAD. 7 DAY OVER 28 DAY", "line", W,
              {"x": date_hist("@timestamp", "WEEK", "1w"), "m": metric("max", "acwr", "ACWR", fmt=FMT_1)},
              "x", ["m"], colors={"m": CHALK}, legend=False, ref=(1.0, "BASELINE"))
    mono = xy(L("hi-mono"), "TRAINING MONOTONY", "line", W,
              {"x": date_hist("@timestamp", "WEEK", "1w"), "m": metric("max", "monotony", "MONOTONY", fmt=FMT_1)},
              "x", ["m"], colors={"m": CHALK_DIM}, legend=False)
    d.row((acwr, 24, []), (mono, 24, []), h=9)
    zones = heatmap(L("hi-zones"), "WHERE THE REPS LIVE. MAIN LIFTS BY INTENSITY ZONE", T,
                    {"x": date_hist("date", "MONTH", "1M"),
                     "y": terms("prilepin_zone", "ZONE", size=4),
                     "v": metric("sum", "reps", "REPS", fmt=FMT_INT)},
                    "x", "y", "v", query='set_type: "working" and exercise.category: "main"')
    d.row((zones, 48, []), h=9)
    d.row((sessions_table(L("hi-sessions")), 48, [("session", "Session")]), h=10)
    objs += d.build()

    # ---------------------------------------------------------------- Meets
    d = Dashboard("meets", "Ironstack. Meets", "Competition record. Click a best lift for its training history.",
                  "Competition record.", time_from="now-10y")
    d.row((custom("me-cards", tpl.MEET_CARDS, Q["meet_cards"]), 48, []), h=6)
    best = metric_vis(L("me-best"), "BEST LIFTS. CLICK FOR TRAINING HISTORY", M,
                      {"m": metric("max", "weight_lb", "LB", fmt=FMT_1), "s": metric("max", "weight_kg", "KG", fmt=FMT_1),
                       "b": terms("exercise.name", "LIFT", size=3)},
                      "m", secondary="s", breakdown="b", max_cols=3, query="made: true")
    d.row((best, 48, [("lift", "Lift")]), h=7)
    d.row((custom("me-list", tpl.MEET_LIST, Q["meet_list"]), 48, []), h=11)
    tot_cols = {"x": terms("meet_id", "MEET", size=50), "m": metric("max", "total_lb", "TOTAL LB", fmt=FMT_1)}
    tot = xy(L("me-totals"), "TOTAL OVER MEETS", "line", M, tot_cols, "x", ["m"], colors={"m": CHALK}, legend=False)
    att_cols = {
        "mid": terms("meet_id", "MEET", size=50, direction="desc"),
        "lift": terms("lift", "LIFT", size=3),
        "no": terms("attempt_no", "ATTEMPT", size=4, dtype="number"),
        "kg": last("weight_kg", "KG", "number", fmt=FMT_1),
        "lb": last("weight_lb", "LB", "number", fmt=FMT_1),
        "made": last("made", "MADE", "boolean"),
    }
    d.row((tot, 24, []), (table(L("me-attempts"), "ATTEMPTS", M, att_cols, sort="mid", direction="desc", page=50), 24, []), h=10)
    objs += d.build()

    # ---------------------------------------------------------------- Mindset
    d = Dashboard("mindset", "Ironstack. Mindset", "Every note. Search above; semantic where ELSER is on.",
                  "Every note.")
    nps = xy(L("mi-per-session"), "NOTES PER SESSION", "line", N,
             {"x": terms("session_id", "SESSION", size=300), "c": count("NOTES")}, "x", ["c"], colors={"c": BLOOD}, legend=False)
    d.row((nps, 48, [("session", "Session")]), h=8)
    tag_cols = {"x": terms("tags", "TAG", size=25, by_col="c", direction="desc"), "c": count("NOTES")}
    tags = xy(L("mi-tags"), "TAGS. CLICK TO FILTER", "bar_horizontal", N, tag_cols, "x", ["c"], colors={"c": CHALK_DIM}, legend=False)
    tt_cols = {"x": terms("session_id", "SESSION", size=300), "tag": terms("tags", "TAG", size=6, by_col="c", direction="desc"),
               "c": count("NOTES")}
    tag_trend = xy(L("mi-tag-trend"), "TAGS OVER TIME", "bar_stacked", N, tt_cols, "x", ["c"], split="tag", palette="gray")
    d.row((tags, 20, []), (tag_trend, 28, []), h=9)
    d.row((custom("mi-recent", tpl.RECENT_NOTES, Q["recent_notes"]), 28, []),
          (notes_table(L("mi-notes"), "OPEN A SESSION. CLICK THE SESSION CELL"), 20, [("session", "Session")]), h=12)
    d.row((custom("mi-watch", tpl.WATCH_CARD, Q["watch"]), 48, []), h=8)
    objs += d.build()

    # de-duplicate by (type, id): shared builders are called for more than one dashboard
    seen, out = set(), []
    for o in objs:
        key = (o["type"], o["id"])
        if key not in seen:
            seen.add(key)
            out.append(o)
    return out


def main() -> None:
    objs = build()
    ndjson = "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(ndjson)
        return
    OUT.write_text(ndjson)
    kinds = {}
    for o in objs:
        kinds[o["type"]] = kinds.get(o["type"], 0) + 1
    print(f"wrote {OUT.name}: " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))


if __name__ == "__main__":
    main()
