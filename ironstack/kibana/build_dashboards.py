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
import sys
import uuid
from pathlib import Path

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

MEET_MAX_LB = 909.4  # last meet total; the oxblood reference line on Overview

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
                "lineWidth": 2, "icon": "none", "iconPosition": "auto", "textVisibility": True, "fill": "none",
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
            tcols["t-breakdown"] = columns[breakdown]
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
        "name": "custom", "continuity": "above", "reverse": False, "rangeType": "number",
        "rangeMin": 0, "rangeMax": None, "steps": 3,
        "colorStops": [{"color": c, "stop": i} for i, c in enumerate(stops)],
        "stops": [{"color": c, "stop": i + 1} for i, c in enumerate(stops)],
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

class Dashboard:
    """Collects panels row by row on Kibana's 48-column grid."""

    W = 48

    def __init__(self, key, title, description, controls=None, time_from="now-1y"):
        self.id = DASH[key]
        self.key = key
        self.title = title
        self.description = description
        self.controls = controls or []  # (data view key, field, label)
        self.time_from = time_from
        self.panels: list[dict] = []
        self.refs: list[dict] = []
        self.y = 0

    def nav(self):
        self.row((nav_strip(self.key), 48, []), h=3)

    def row(self, *items, h=8):
        """items: (saved object, width, drilldowns) with drilldowns a list of (target key, name) or ('url', template, name)."""
        x = 0
        for obj, w, drills in items:
            idx = uid(self.id, obj["id"])
            enhancements = {"dynamicActions": {"events": []}}
            for d in drills:
                event_id = uid(self.id, obj["id"], str(d))
                if d[0] == "url":
                    enhancements["dynamicActions"]["events"].append({
                        "eventId": event_id, "triggers": ["VALUE_CLICK_TRIGGER"],
                        "action": {"factoryId": "URL_DRILLDOWN", "name": d[2],
                                   "config": {"url": {"template": d[1]}, "openInNewTab": False, "encodeUrl": True}},
                    })
                else:
                    target, name = d
                    enhancements["dynamicActions"]["events"].append({
                        "eventId": event_id, "triggers": ["VALUE_CLICK_TRIGGER"],
                        "action": {"factoryId": "DASHBOARD_TO_DASHBOARD_DRILLDOWN", "name": name,
                                   "config": {"useCurrentFilters": True, "useCurrentDateRange": True, "openInNewTab": False}},
                    })
                    self.refs.append({"name": f"{idx}:drilldown:DASHBOARD_TO_DASHBOARD_DRILLDOWN:{event_id}:dashboardId",
                                      "type": "dashboard", "id": DASH[target]})
            self.panels.append({
                "version": "8.9.0", "type": obj["type"],
                "gridData": {"x": x, "y": self.y, "w": w, "h": h, "i": idx},
                "panelIndex": idx,
                "embeddableConfig": {"enhancements": enhancements},
                "title": obj["attributes"]["title"],
                "panelRefName": f"panel_{idx}",
            })
            self.refs.append({"name": f"panel_{idx}", "type": obj["type"], "id": obj["id"]})
            x += w
        self.y += h

    def build(self):
        attrs = {
            "title": self.title,
            "description": self.description,
            "panelsJSON": json.dumps(self.panels),
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False, "syncCursor": True,
                                       "syncTooltips": False, "hidePanelTitles": False}),
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
                panels[cid] = {"type": "optionsListControl", "order": order, "grow": True, "width": "medium",
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
        return {"id": self.id, "type": "dashboard", "attributes": attrs, "references": refs,
                **MIGRATION, "typeMigrationVersion": "8.9.0"}


# --------------------------------------------------------------------------- shared panels

NAV_ORDER = ["overview", "program", "session", "lift", "history", "meets", "mindset"]


def nav_strip(current: str):
    """Mono nav row: every dashboard by name, the current one in bold. Relative links survive a base path."""
    parts = []
    for key in NAV_ORDER:
        label = key.upper()
        parts.append(f"**{label}**" if key == current else f"[{label}](dashboards#/view/{DASH[key]})")
    return markdown(f"ironstack-nav-{current}", "IRONSTACK", " &nbsp;·&nbsp; ".join(parts))


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


def watch_items(id_, title="WATCH ITEMS"):
    columns = {
        "sid": terms("session_id", "SESSION", size=20, direction="desc"),
        "item": terms("watch_items", "WATCH", size=20),
    }
    return table(id_, title, "sessions", columns, sort="sid", direction="desc")


# --------------------------------------------------------------------------- build

def build() -> list[dict]:
    objs: list[dict] = [data_view(k) for k in DV]
    S, T, N, M = "sessions", "sets", "notes", "meets"
    L = lambda name: f"ironstack-lens-{name}"  # noqa: E731

    # ---------------------------------------------------------------- Overview
    d = Dashboard("overview", "Ironstack. Overview", "The block at a glance. Every tile opens its detail.")
    d.nav()
    days = metric_vis(L("ov-days"), "DAYS TO MEET", S,
                      {"m": last("days_to_meet", "DAYS TO MEET", "number", sort="timestamp", fmt=FMT_INT),
                       "s": last("program.week", "WEEK", "number", sort="timestamp", fmt=FMT_INT),
                       "b": terms("program.block", "BLOCK", size=1, direction="desc")},
                      "m", secondary="s", breakdown="b", max_cols=1, subtitle="as of the last session")
    d.row((days, 12, [("program", "Program")]), (block_timeline(L("ov-timeline")), 36, [("session", "Session")]), h=8)

    lifts = metric_vis(L("ov-lifts"), "BEST e1RM. THIS BLOCK", T,
                       {"m": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT),
                        "b": terms("exercise.name", "LIFT", size=3, by_col="m", direction="desc")},
                       "m", breakdown="b", max_cols=3,
                       trend=("date", lambda: metric("max", "est_e1rm", "e1RM", fmt=FMT_INT)),
                       query='exercise.category: "main" and set_type: "working"')
    total_cols = {"x": date_hist("date", "WEEK", "1w"), "lift": terms("exercise.name", "LIFT", size=3),
                  "m": metric("max", "est_e1rm", "BEST e1RM", fmt=FMT_INT)}
    total = xy(L("ov-total"), "TOTAL VS MEET MAX", "bar_stacked", T, total_cols, "x", ["m"], split="lift",
               palette="gray", ref=(MEET_MAX_LB, "MEET MAX"),
               query='exercise.category: "main" and set_type: "working"')
    d.row((lifts, 24, [("lift", "Lift")]), (total, 24, []), h=9)

    streak = metric_vis(L("ov-streak"), "STREAK", S,
                        {"m": last("streak_day", "DAY", "number", sort="timestamp", fmt=FMT_INT),
                         "b": terms("program.block", "BLOCK", size=1, direction="desc")},
                        "m", breakdown="b", max_cols=1)
    recent = metric_vis(L("ov-recent"), "LAST 28 DAYS", S,
                        {"m": count("SESSIONS", filt='date >= "now-28d"', fmt=FMT_INT),
                         "s": count("LAST 7", filt='date >= "now-7d"', fmt=FMT_INT),
                         "b": terms("program.block", "BLOCK", size=1, direction="desc")},
                        "m", secondary="s", breakdown="b", max_cols=1)
    latest_cols = {
        "sid": terms("session_id", "SESSION", size=1, by_col="ts", direction="desc"),
        "ts": metric("max", "timestamp", "TS"),
        "day": last("program.day", "DAY", "number"),
        "ton": last("totals.tonnage_lb", "TONNAGE", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "AVG RPE", "number", fmt=FMT_1),
        "wrap": last("wrap_up.keyword", "WRAP UP"),
    }
    latest = table(L("ov-latest"), "LATEST SESSION", S, latest_cols, hidden=("ts",))
    d.row((calendar(L("ov-calendar")), 20, [("history", "History")]),
          (streak, 8, [("history", "History")]), (recent, 8, [("history", "History")]),
          (latest, 12, [("session", "Session")]), h=9)

    rpe_cols = {"x": terms("rpe", "RPE", size=20, dtype="number"), "c": count("WORKING SETS")}
    rpe_hist = xy(L("ov-rpe"), "WORKING SET RPE", "bar", T, rpe_cols, "x", ["c"], colors={"c": CHALK_DIM},
                  query='set_type: "working"', legend=False)
    d.row((watch_items(L("ov-watch")), 24, [("session", "Session")]), (rpe_hist, 24, []), h=8)

    bw = metric_vis(L("ov-bw"), "BODYWEIGHT", S,
                    {"m": last("metrics.bodyweight_lb", "LB", "number", sort="timestamp", fmt=FMT_1)}, "m",
                    max_cols=1, trend=("timestamp", lambda: last("metrics.bodyweight_lb", "LB", "number", sort="timestamp")))
    sleep = metric_vis(L("ov-sleep"), "SLEEP", S,
                       {"m": last("metrics.sleep_hrs", "HRS", "number", sort="timestamp", fmt=FMT_1)}, "m",
                       max_cols=1, trend=("timestamp", lambda: last("metrics.sleep_hrs", "HRS", "number", sort="timestamp")))
    d.row((bw, 24, []), (sleep, 24, []), h=6)
    objs += [days, lifts, total, streak, recent, latest, rpe_hist, bw, sleep, d.build()]
    objs += [o for o in (block_timeline(L("ov-timeline")), calendar(L("ov-calendar")), watch_items(L("ov-watch")))]

    # ---------------------------------------------------------------- Program
    d = Dashboard("program", "Ironstack. Program", "Block, week, day. Pick a week, open a day.",
                  controls=[(S, "program.block", "BLOCK"), (S, "program.week", "WEEK")])
    d.nav()
    header_cols = {
        "block": last("program.block", "BLOCK", sort="timestamp"),
        "phase": last("program.phase", "PHASE", sort="timestamp"),
        "week": last("program.week", "WEEK", "number", sort="timestamp"),
        "day": last("program.day", "DAY", "number", sort="timestamp"),
        "of": last("program.total_days", "OF", "number", sort="timestamp"),
        "done": count("SESSIONS DONE", fmt=FMT_INT),
        "meet": last("program.meet_date", "MEET", "date", sort="timestamp"),
    }
    header = table(L("pr-header"), "WHERE YOU ARE", S, header_cols)
    pdays = metric_vis(L("pr-days"), "DAYS TO MEET", S,
                       {"m": last("days_to_meet", "DAYS", "number", sort="timestamp", fmt=FMT_INT)}, "m",
                       max_cols=1, color=BLOOD, subtitle="as of the last session")
    d.row((header, 36, []), (pdays, 12, []), h=6)
    d.row((block_timeline(L("pr-timeline")), 48, [("session", "Session")]), h=8)
    weeks_cols = {
        "week": terms("program.week", "WEEK", size=60, dtype="number"),
        "n": count("SESSIONS", fmt=FMT_INT),
        "ton": metric("sum", "totals.tonnage_lb", "TONNAGE", fmt=FMT_INT),
        "rpe": metric("average", "avg_working_rpe", "AVG RPE", fmt=FMT_1),
    }
    weeks = table(L("pr-weeks"), "WEEKS", S, weeks_cols, sort="week")
    days_cols = {
        "sid": terms("session_id", "SESSION", size=100),
        "day": last("program.day", "DAY", "number"),
        "date": last("date", "DATE", "date"),
        "tod": last("time_of_day", "WHEN"),
        "loc": last("location.name", "WHERE"),
        "dur": last("duration_min", "MIN", "number", fmt=FMT_INT),
        "ton": last("totals.tonnage_lb", "TONNAGE", "number", fmt=FMT_INT),
        "rpe": last("avg_working_rpe", "AVG RPE", "number", fmt=FMT_1),
    }
    pdays_t = table(L("pr-days-table"), "DAYS", S, days_cols, sort="sid")
    d.row((weeks, 20, []), (pdays_t, 28, [("session", "Session")]), h=10)
    objs += [header, pdays, block_timeline(L("pr-timeline")), weeks, pdays_t, d.build()]

    # ---------------------------------------------------------------- Session
    d = Dashboard("session", "Ironstack. Session", "One session. Arrives filtered to a session_id.")
    d.nav()
    title_cols = {
        "block": terms("program.block", "BLOCK", size=1),
        "phase": last("program.phase", "PHASE", sort="timestamp"),
        "week": terms("program.week", "WEEK", size=1, dtype="number"),
        "day": last("program.day", "DAY", "number", sort="timestamp"),
        "of": last("program.total_days", "OF", "number", sort="timestamp"),
        "date": last("date", "DATE", "date", sort="timestamp"),
        "start": last("start_time", "START", sort="timestamp"),
        "loc": last("location.name", "WHERE", sort="timestamp"),
    }
    stitle = table(L("se-title"), "SESSION. CLICK BLOCK OR WEEK FOR THE PROGRAM", S, title_cols)
    nav_cols = {"prev": terms("prev_session_id", "PREV", size=1),
                "next": terms("next_session_id", "NEXT", size=1)}
    nav = table(L("se-nav"), "PREV / NEXT. CLICK TO OPEN", S, nav_cols)
    d.row((stitle, 36, [("program", "Program")]), (nav, 12, [("url", SESSION_URL, "Open session")]), h=5)

    def tile(name, title, col, color=None, fmt=FMT_INT):
        return metric_vis(L(name), title, S, {"m": last(col, title, "number", sort="timestamp", fmt=fmt)}, "m",
                          max_cols=1, color=color)
    d.row((tile("se-dur", "MINUTES", "duration_min"), 12, []),
          (tile("se-rpe", "AVG WORKING RPE", "avg_working_rpe", fmt=FMT_1), 12, []),
          (tile("se-ton", "TONNAGE", "totals.tonnage_lb", color=BLOOD), 12, []),
          (tile("se-sets", "SETS", "totals.sets"), 12, []), h=6)
    d.row((tile("se-wsets", "WORKING SETS", "totals.working_sets"), 12, []),
          (tile("se-reps", "REPS", "totals.reps"), 12, []),
          (tile("se-ex", "EXERCISES", "totals.exercises"), 12, []),
          (tile("se-streak", "STREAK DAY", "streak_day"), 12, []), h=5)
    cond_cols = {
        "temp": last("environment.temp_f", "TEMP F", "number", sort="timestamp"),
        "hum": last("environment.humidity_pct", "HUMIDITY", "number", sort="timestamp"),
        "cond": last("environment.conditions", "SKY", sort="timestamp"),
        "wind": last("environment.wind", "WIND", sort="timestamp"),
        "tod": last("time_of_day", "WHEN", sort="timestamp"),
        "travel": last("location.travel", "TRAVEL", "boolean", sort="timestamp"),
    }
    cond = table(L("se-cond"), "CONDITIONS", S, cond_cols)
    smap = session_map("ironstack-map-session")
    d.row((smap, 24, []), (cond, 24, []), h=8)
    sets_cols = {
        "seq": terms("seq", "#", size=200, dtype="number"),
        "ex": terms("exercise.name", "EXERCISE", size=50),
        "type": last("set_type", "TYPE"),
        "w": last("weight_lb", "LB", "number", fmt=FMT_INT),
        "reps": last("reps", "REPS", "number"),
        "unit": last("rep_unit", "UNIT"),
        "dist": last("distance_ft", "FT", "number"),
        "rpe": last("rpe", "RPE", "number", fmt=FMT_1),
        "e1rm": last("est_e1rm", "e1RM", "number", fmt=FMT_INT),
        "gear": last("gear", "GEAR", arrays=True),
        "notes": last("notes.keyword", "NOTES"),
    }
    sets_t = table(L("se-sets"), "SETS. CLICK A LIFT FOR ITS HISTORY", T, sets_cols, sort="seq", page=50)
    d.row((sets_t, 48, [("lift", "Lift")]), h=14)
    rpe_line = xy(L("se-rpe-line"), "RPE BY SET", "line", T,
                  {"x": terms("seq", "#", size=200, dtype="number"), "ex": terms("exercise.name", "EXERCISE", size=20),
                   "m": metric("max", "rpe", "RPE", fmt=FMT_1)}, "x", ["m"], split="ex", palette="gray")
    vol_cols = {"x": terms("exercise.name", "EXERCISE", size=20, by_col="m", direction="desc"),
                "m": metric("sum", "volume_lb", "VOLUME", fmt=FMT_INT)}
    vol = xy(L("se-vol"), "VOLUME BY EXERCISE", "bar_horizontal", T, vol_cols, "x", ["m"], colors={"m": CHALK_DIM},
             legend=False)
    d.row((rpe_line, 24, []), (vol, 24, [("lift", "Lift")]), h=8)
    wrap_cols = {"wrap": last("wrap_up.keyword", "WRAP UP", sort="timestamp"),
                 "gear": last("gear_notes.keyword", "GEAR", sort="timestamp"),
                 "watch": last("watch_items", "WATCH", sort="timestamp", arrays=True)}
    wrap = table(L("se-wrap"), "WRAP UP. GEAR. WATCH", S, wrap_cols)
    d.row((notes_table(L("se-notes"), "NOTES. IN ORDER", size=5), 32, []), (wrap, 16, []), h=10)
    objs += [stitle, nav, cond, smap, sets_t, rpe_line, vol, wrap, notes_table(L("se-notes"), "NOTES. IN ORDER", size=5)]
    objs += [tile("se-dur", "MINUTES", "duration_min"), tile("se-rpe", "AVG WORKING RPE", "avg_working_rpe", fmt=FMT_1),
             tile("se-ton", "TONNAGE", "totals.tonnage_lb", color=BLOOD), tile("se-sets", "SETS", "totals.sets"),
             tile("se-wsets", "WORKING SETS", "totals.working_sets"), tile("se-reps", "REPS", "totals.reps"),
             tile("se-ex", "EXERCISES", "totals.exercises"), tile("se-streak", "STREAK DAY", "streak_day"), d.build()]

    # ---------------------------------------------------------------- Lift
    d = Dashboard("lift", "Ironstack. Lift", "One exercise over time. Arrives filtered to exercise.name.",
                  controls=[(T, "program.block", "BLOCK")], time_from="now-2y")
    d.nav()
    lh_cols = {
        "lift": terms("exercise.name", "LIFT", size=1, by_col="n", direction="desc"),
        "e1": metric("max", "est_e1rm", "BEST e1RM", fmt=FMT_INT),
        "top": metric("max", "weight_lb", "BEST TOP SET", fmt=FMT_INT),
        "lastd": metric("max", "date", "LAST PERFORMED"),
        "n": count("WORKING SETS", fmt=FMT_INT),
        "sess": unique("session_id", "SESSIONS"),
    }
    lh_cols["lastd"]["dataType"] = "date"
    lhead = table(L("li-header"), "LIFT", T, lh_cols, query='set_type: "working"')
    d.row((lhead, 48, []), h=5)
    e1_cols = {"x": terms("session_id", "SESSION", size=300), "m": metric("max", "est_e1rm", "e1RM", fmt=FMT_INT)}
    e1 = xy(L("li-e1rm"), "e1RM OVER TIME", "line", T, e1_cols, "x", ["m"], colors={"m": BLOOD}, legend=False,
            query='set_type: "working"')
    top_cols = {"x": terms("session_id", "SESSION", size=300), "m": metric("max", "weight_lb", "TOP SET", fmt=FMT_INT),
                "r": metric("max", "reps", "REPS"), "p": metric("max", "rpe", "RPE", fmt=FMT_1)}
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
    all_sets = table(L("li-sets"), "ALL SETS", T, all_cols, sort="sid", direction="desc", page=50)
    d.row((all_sets, 48, [("session", "Session")]), h=12)
    d.row((notes_table(L("li-notes"), "NOTES ABOUT THIS LIFT"), 48, [("session", "Session")]), h=8)
    objs += [lhead, e1, top, lvol, load, all_sets, notes_table(L("li-notes"), "NOTES ABOUT THIS LIFT"), d.build()]

    # ---------------------------------------------------------------- History
    d = Dashboard("history", "Ironstack. History", "Sessions over any range. The time picker is the range toggle.",
                  controls=[(S, "program.block", "BLOCK"), (S, "program.phase", "PHASE")])
    d.nav()
    h_ton = metric_vis(L("hi-ton"), "TONNAGE", S, {"m": metric("sum", "totals.tonnage_lb", "LB", fmt=FMT_INT)}, "m", max_cols=1)
    h_avg = metric_vis(L("hi-avg"), "PER SESSION", S, {"m": metric("average", "totals.tonnage_lb", "LB", fmt=FMT_INT)}, "m", max_cols=1)
    h_n = metric_vis(L("hi-n"), "SESSIONS", S, {"m": count("SESSIONS", fmt=FMT_INT)}, "m", max_cols=1)
    h_rpe = metric_vis(L("hi-rpe"), "AVG WORKING RPE", S, {"m": metric("average", "avg_working_rpe", "RPE", fmt=FMT_1)}, "m", max_cols=1)
    d.row((h_ton, 12, []), (h_avg, 12, []), (h_n, 12, []), (h_rpe, 12, []), h=6)
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
    d.row((sessions_table(L("hi-sessions")), 48, [("session", "Session")]), h=10)
    objs += [h_ton, h_avg, h_n, h_rpe, block_timeline(L("hi-timeline"), "TONNAGE PER SESSION"), tod,
             calendar(L("hi-calendar")), env, sessions_table(L("hi-sessions")), d.build()]

    # ---------------------------------------------------------------- Meets
    d = Dashboard("meets", "Ironstack. Meets", "Competition record. Click a meet to see its attempts.", time_from="now-10y")
    d.nav()
    m_n = metric_vis(L("me-n"), "MEETS", M, {"m": unique("meet_id", "MEETS")}, "m", max_cols=1)
    m_total = metric_vis(L("me-total"), "BEST TOTAL", M,
                         {"m": metric("max", "total_lb", "LB", fmt=FMT_1), "s": metric("max", "total_kg", "KG", fmt=FMT_1)},
                         "m", secondary="s", max_cols=1, color=BLOOD)
    m_dots = metric_vis(L("me-dots"), "BEST DOTS", M, {"m": metric("max", "dots", "DOTS", fmt=FMT_1)}, "m", max_cols=1)
    m_made = metric_vis(L("me-made"), "ATTEMPTS MADE", M,
                        {"m": count("MADE", filt="made: true", fmt=FMT_INT), "s": count("OF", fmt=FMT_INT)},
                        "m", secondary="s", max_cols=1)
    d.row((m_n, 12, []), (m_total, 12, []), (m_dots, 12, []), (m_made, 12, []), h=6)
    best = metric_vis(L("me-best"), "BEST LIFTS. CLICK FOR TRAINING HISTORY", M,
                      {"m": metric("max", "weight_lb", "LB", fmt=FMT_1), "s": metric("max", "weight_kg", "KG", fmt=FMT_1),
                       "b": terms("exercise.name", "LIFT", size=3)},
                      "m", secondary="s", breakdown="b", max_cols=3, query="made: true")
    d.row((best, 48, [("lift", "Lift")]), h=7)
    meets_cols = {
        "mid": terms("meet_id", "MEET", size=50, direction="desc"),
        "name": last("name", "NAME"),
        "kg": last("total_kg", "TOTAL KG", "number", fmt=FMT_1),
        "lb": last("total_lb", "TOTAL LB", "number", fmt=FMT_1),
        "dots": last("dots", "DOTS", "number", fmt=FMT_1),
        "bw": last("bodyweight_lb", "BW LB", "number", fmt=FMT_1),
        "made": last("attempts_made", "MADE", "number"),
    }
    meets_t = table(L("me-table"), "MEETS. CLICK ONE TO FILTER", M, meets_cols, sort="mid", direction="desc")
    tot_cols = {"x": terms("meet_id", "MEET", size=50), "m": metric("max", "total_lb", "TOTAL LB", fmt=FMT_1)}
    tot = xy(L("me-totals"), "TOTAL OVER MEETS", "line", M, tot_cols, "x", ["m"], colors={"m": CHALK}, legend=False)
    d.row((meets_t, 24, []), (tot, 24, []), h=8)
    att_cols = {
        "mid": terms("meet_id", "MEET", size=50, direction="desc"),
        "lift": terms("lift", "LIFT", size=3),
        "no": terms("attempt_no", "ATTEMPT", size=4, dtype="number"),
        "kg": last("weight_kg", "KG", "number", fmt=FMT_1),
        "lb": last("weight_lb", "LB", "number", fmt=FMT_1),
        "made": last("made", "MADE", "boolean"),
    }
    att = table(L("me-attempts"), "ATTEMPTS", M, att_cols, sort="mid", direction="desc", page=50)
    d.row((att, 48, []), h=10)
    objs += [m_n, m_total, m_dots, m_made, best, meets_t, tot, att, d.build()]

    # ---------------------------------------------------------------- Mindset
    d = Dashboard("mindset", "Ironstack. Mindset", "Every note. Search above; semantic where ELSER is on.")
    d.nav()
    np_cols = {"x": terms("session_id", "SESSION", size=300), "c": count("NOTES")}
    nps = xy(L("mi-per-session"), "NOTES PER SESSION", "line", N, np_cols, "x", ["c"], colors={"c": BLOOD}, legend=False)
    d.row((nps, 48, [("session", "Session")]), h=8)
    tag_cols = {"x": terms("tags", "TAG", size=25, by_col="c", direction="desc"), "c": count("NOTES")}
    tags = xy(L("mi-tags"), "TAGS", "bar_horizontal", N, tag_cols, "x", ["c"], colors={"c": CHALK_DIM}, legend=False)
    tt_cols = {"x": terms("session_id", "SESSION", size=300), "tag": terms("tags", "TAG", size=6, by_col="c", direction="desc"),
               "c": count("NOTES")}
    tag_trend = xy(L("mi-tag-trend"), "TAGS OVER TIME", "bar_stacked", N, tt_cols, "x", ["c"], split="tag", palette="gray")
    d.row((tags, 20, []), (tag_trend, 28, []), h=9)
    ph_cols = {"x": terms("phase", "PHASE", size=4), "c": count("NOTES")}
    phase = xy(L("mi-phase"), "BY PHASE", "bar", N, ph_cols, "x", ["c"], colors={"c": CHALK_DIM}, legend=False)
    d.row((phase, 16, []), (notes_table(L("mi-notes"), "RECENT NOTES"), 32, [("session", "Session")]), h=10)
    d.row((watch_items(L("mi-watch")), 48, [("session", "Session")]), h=8)
    objs += [nps, tags, tag_trend, phase, notes_table(L("mi-notes"), "RECENT NOTES"), watch_items(L("mi-watch")), d.build()]

    objs += [nav_strip(k) for k in NAV_ORDER]

    # de-duplicate by (type, id): shared builders are called twice for the same id
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
