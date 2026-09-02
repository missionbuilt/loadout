# kibana/

Seven dashboards, one navigation graph, shipped as saved objects. No plugins, so this runs on Elastic Cloud Serverless and on a free self-hosted stack alike.

```
build_dashboards.py   generates dashboards.ndjson (stdlib only, deterministic)
dashboards.ndjson     4 data views, 62 Lens panels, 1 map, 7 dashboards
import.py             POSTs the NDJSON to Kibana's saved-objects import API
```

## Import

Index at least one session first (`ingest/setup_indices.py`, then `ingest/index_workouts.py` from your instance repo), then:

```bash
export KIBANA_URL=https://<your-project>.kb.<region>.gcp.elastic.cloud
export ES_API_KEY=<key with Kibana saved-object privileges>
pip install requests
python kibana/import.py
```

Re-importing is safe. Every object has a fixed id, so an import overwrites in place and drilldowns and bookmarks keep working. To change a panel, edit `build_dashboards.py`, regenerate, and import again; do not edit the NDJSON by hand.

Or import by hand: Kibana, Stack Management, Saved Objects, Import, pick `dashboards.ndjson`, check "overwrite".

**Dark theme.** The Iron Log palette assumes Kibana's dark mode, which is a user setting, not a saved object: your profile menu, Appearance, Dark.

## The dashboards

| Dashboard | id | What it answers |
|---|---|---|
| Overview | `ironstack-overview` | Where the block stands. Days to meet, tonnage timeline by phase, best e1RM per lift, total vs the meet max, calendar, streak, latest session, watch items. |
| Program | `ironstack-program` | Block, week, day. Controls for block and week; a weeks table and a days table. |
| Session | `ironstack-session` | One session. Header, tiles, map and conditions, every set, RPE by set, volume by exercise, notes in order, wrap-up. |
| Lift | `ironstack-lift` | One exercise over time. e1RM, top set, volume by phase, RPE vs load, every set, every note about it. |
| History | `ironstack-history` | Sessions over any range. The time picker is the 1W / 1M / 6M / 1Y / All toggle. |
| Meets | `ironstack-meets` | Competition record. Totals, DOTS, best lifts, every attempt. |
| Mindset | `ironstack-mindset` | Every note. Search in the query bar (semantic where ELSER is on), tags, phases, watch items. |

## The navigation graph

Every aggregate is a door to its detail, and the detail carries its context as a filter.

```
                 +-----------+   block    +-----------+
                 | Overview  |----------->|  Program  |
                 +-----------+            +-----------+
     lift  /   |    |    |   \  range          |  session
          v    |    |    |    v                v
   +--------+  |    |    |  +-----------+  +-----------+
   |  Lift  |<-+    |    +->|  History  |->|  Session  |<-- prev / next (URL drilldown
   +--------+  sess |  sess +-----------+  +-----------+    on prev_session_id / next_session_id)
        ^           v                          |  ^
        |      +-----------+       lift        |  |  session
        +------|   Meets   |         +---------+  |
     best lift +-----------+         v            |
                              (Session -> Lift)   +---- Mindset (note, notes-per-session point)
```

What each click carries:

| From | To | Filter |
|---|---|---|
| Overview: days-to-meet tile | Program | `program.block` |
| Overview: timeline bar, latest session, watch item | Session | `session_id` |
| Overview: calendar cell, streak, last 28 days | History | time range (calendar cell: week + weekday) |
| Overview: lift tile | Lift | `exercise.name` |
| Any dashboard: nav strip | any | none (a Markdown link row at the top of every dashboard) |
| Program: timeline bar, days table row | Session | `session_id` |
| Session: header, block or week cell | Program | `program.block` or `program.week` |
| Session: sets table, volume bar | Lift | `exercise.name` |
| Session: prev / next cell | Session | `session_id` = the cell value |
| Lift: e1RM point, top-set point, volume bar, sets row, note row | Session | `session_id` |
| History: bar, calendar cell, list row | Session | `session_id` (calendar: date) |
| Meets: best-lift tile | Lift | `exercise.name` |
| Meets: meet row | Meets | `meet_id` (native filter, same dashboard) |
| Mindset: note row, notes-per-session point, watch item | Session | `session_id` |

In a table, click the **session** cell (or the lift cell) to travel; other cells filter in place. A click on a chart carries every bucket it touches, so charts whose buckets would not exist on the target (total vs meet max, RPE vs load, tags over time) deliberately have no drilldown; use the nav strip.

The carried field is `exercise.name` rather than `exercise.slug`: it is a keyword on sets, notes, and meets alike, and it reads as a label in the filter bar. The slug is still on every document if you would rather carry that.

## Substitutions (Serverless, Lens only)

Where the spec asked for something Lens cannot draw as saved objects, the nearest thing is in its place:

- **Days to meet** is `days_to_meet` as of the last logged session (the indexer writes it), not a live countdown. Lens has no clean "today minus a date".
- **Calendar heatmap** colors by session count, not by phase; a heatmap has one value. The indexer writes `weekday` ("2 Tue") so the rows sort Monday to Sunday.
- **Total vs meet max** stacks the best e1RM per lift by week; the stack height is the total. The dashed oxblood line is the last meet total.
- **Prev / next session** is a two-cell table with a URL drilldown, since a Markdown panel cannot read data.
- **Sets as `weight x reps @ rpe`** are separate columns; Lens tables cannot compose strings without a formula per row.
- **RPE vs load** is a heatmap (weight by RPE, count of sets); Lens has no scatter plot.
- **Attempt chips** on Meets are an attempts table with a MADE column, not a 3x3 grid.
- **Phase-change annotation** on History is carried by the bar colors themselves.
- **All-time sessions** tile is omitted; every Lens panel honors the time range.
- **Bodyweight and sleep** tiles show empty until `metrics` is logged; Lens panels do not hide themselves.
- **Tag cloud** is a horizontal bar of tags; calmer, and it filters on click.
- The **map** panel is best effort. If it errors on your stack, remove it from the Session dashboard; nothing else depends on it.

## Style

Iron Log: charcoal ground, warm chalk foregrounds, phase colors `#5a564f` / `#a8a094` / `#7a7873`, and oxblood `#a8211a` for exactly one thing per dashboard (the meet-max line on Overview, the tonnage tile on Session, days to meet on Program, the e1RM line on Lift, the calendar peak on History, best total on Meets, notes per session on Mindset). Split series use Kibana's built-in gray palette. Titles are short and uppercase; no em-dashes in UI strings.
