# kibana/

Seven dashboards, one navigation graph, shipped as saved objects. No plugins, so this
runs on Elastic Cloud Serverless and on a free self-hosted stack alike.

```
build_dashboards.py   generates dashboards.ndjson (stdlib only, deterministic)
templates.py          the Liquid + CSS for every custom-content panel
verify_liquid.py      renders every template and asserts on the output
dashboards.ndjson     4 index-patterns, 14 Lens panels, 7 dashboards (25 objects)
import.py             POSTs the NDJSON to Kibana's saved-objects import API
prune.py              lists (and optionally deletes) Ironstack objects nothing references
```

Those counts are what the file in this directory actually holds; they are checked by
`--check` rather than kept in step by hand.

## Build

```bash
python kibana/build_dashboards.py --no-coach    # what is committed here
python kibana/build_dashboards.py --check       # regenerate and diff against the file
python kibana/verify_liquid.py                  # render every card and assert (pip install python-liquid)
```

`build_dashboards.py` writes `dashboards.ndjson`. It refuses to write a file that fails
`check()`, and `--check` additionally compares the build against the committed artifact
and exits non-zero on any difference, so a hand-edited NDJSON is caught. Never edit the
NDJSON directly: edit `build_dashboards.py` or `templates.py` and regenerate.

### Environment

| Variable | Default | What it does |
|---|---|---|
| `IRONSTACK_COACH_URL` | unset | The Ironstack Coach's URL. Set, every dashboard gets an ASK THE COACH links panel in its brand bar and the nav row narrows from 48 to 38 columns to make room. Unset, the panel is not built and the brand bar takes the full width. Must be `http` or `https`; anything else is refused. |
| `IRONSTACK_MEET_MAX_LB` | unset | Your best competition total, in pounds. Set, Overview's projected-total chart gets an oxblood reference line at that number and says so in its title. Unset, the chart has no reference line and its title makes no claim about a meet best. The card beside it reads the real value out of `workout-meets` either way, so this is only for the Lens chart, which cannot read data. |
| `IRONSTACK_TZ` | `UTC` | A fixed offset (`UTC`, `-07:00`, `+0530`) used to format every human-readable date and to compute days-to-meet. It has to be a fixed offset, not an IANA zone: ES\|QL's `DATE_FORMAT` takes no timezone parameter, so the only lever either engine offers is shifting the instant before it is formatted. |

### Flags

| Flag | What it does |
|---|---|
| `--no-coach` | Build without ASK THE COACH. Without this, an unset `IRONSTACK_COACH_URL` is an error rather than a silent removal of the link from all seven dashboards. This is how the committed artifact is built. |
| `--check` | Build, run every check, and diff against the committed `dashboards.ndjson`. Writes nothing. Exits non-zero on a check failure or a difference. Always builds as `--no-coach`, so it runs the same whether the coach URL is set or not. |
| `--stdout` | Print instead of writing. The checks run first, and their output goes to stderr, so `--stdout > dashboards.ndjson` is safe. |
| `--allow-private-coach` | Permit an `externalLink` pointing at a host that is not a documented placeholder. Needed when you build this for your own import, because your coach really does live on your own deployment. Without it the build refuses, which is what stops such a URL being committed here again. |

## Import

Index at least one session first (`ingest/setup_indices.py`, then `ingest/index_workouts.py`
from your instance repo), then:

```bash
export KIBANA_URL=https://<your-project>.kb.<region>.gcp.elastic.cloud
export ES_API_KEY=<key with Kibana saved-object privileges>
pip install requests
python kibana/import.py
```

Or by hand: Kibana, Stack Management, Saved Objects, Import, pick `dashboards.ndjson`,
check "overwrite".

Re-importing is safe. Every object has a fixed id, so an import overwrites in place and
drilldowns and bookmarks keep working.

The NDJSON is written in the dashboard format Kibana 9 and Serverless save natively:
by-reference panels are `vis` / `legacy_vis`, by-value panels carry their config inline,
and drilldowns live in `embeddableConfig.enhancements.dynamicActions.events`
(`typeMigrationVersion` 10.3.0). An earlier build wrote them under
`embeddableConfig.drilldowns`, a key of this repo's own invention that Kibana stored and
ignored; `check()` now fails the build if it reappears. Older Kibana versions may not
import this file.

**Dark theme.** The Iron Log palette assumes Kibana's dark mode, which is a user setting,
not a saved object: your profile menu, Appearance, Dark.

## The indices

Seven, and the dashboards read all of them.

| Index | Written by | What the dashboards take from it |
|---|---|---|
| `workout-sessions` | the indexer | Session headers, tiles, the block timeline, watch items, the days-to-meet card |
| `workout-sets` | the indexer | Every set, e1RM over time, the intensity-zone charts, the projected total |
| `workout-notes` | the indexer | The notes cards, the tag chart, the session index on Mindset |
| `workout-meets` | the indexer | The meet record, best lifts, every attempt, and the meet best the projected-total card measures against |
| `workout-daily` | the indexer | Nothing at present. The daily rollup has no panel on any page. |
| `workout-weekly` | the indexer | The weekly loading table and the acute-vs-chronic chart |
| `ironstack-signals` | `derive.signal_docs()` | Every Signal verdict card: intensity, load, drift, block, taper, projection, tags, weekly loading |

`ironstack-signals` deliberately carries no date-typed field. Kibana scopes an ES\|QL
panel to the dashboard's time range by filtering on the index's date field, so with none
there is nothing to filter on and the time picker cannot re-scope a verdict. Each row is
already windowed at index time. A **filter** still applies, which is why every one of
those cards says so in its zero-row state rather than claiming there is no data.

Only four data views are built, because a data view is only needed where Lens reads:
`workout-sessions`, `workout-sets`, `workout-notes`, `workout-weekly`. ES\|QL names its
own index and needs none. `check()` fails the build if a Lens layer or a control asks for
a view that is not built, and if a `FROM` names an index outside the seven above.

## The dashboards

| Dashboard | id | Default range | What it answers |
|---|---|---|---|
| Overview | `ironstack-overview` | 2y | Where the block stands. Three Signal verdicts (how heavy was this week, am I ramping, what am I neglecting), what you wrote about it in your own words, days to meet, the projected total against your meet best, and the block timeline as the door into a session. |
| Program | `ironstack-program` | 1y | Block, week, day. How hard this week is loading, in words; every day in the range; the weekly loading table. Controls for block and week. |
| Session | `ironstack-session` | 1y | One session, start to finish. Header, top set, tiles, every set with its warm-up, notes in order, wrap-up, conditions, and PREV / NEXT. |
| Lift | `ironstack-lift` | 2y | One exercise over time. Where the lift sits against its own best, e1RM over time with that best drawn on it, where the reps land by zone, every working set. Control for block. |
| History | `ironstack-history` | 1y | How heavy this block is against earlier runs of the same kind, the share of reps by zone, the session timeline, acute vs chronic load, the sessions table. Controls for block and phase. |
| Meets | `ironstack-meets` | 10y | The platform record. Whether this run-in matches the last one, what the projected total has been worth on the platform, totals, DOTS, best lifts, every attempt. |
| Mindset | `ironstack-mindset` | 1y | Everything you wrote. What you keep writing down, the tag chart, recent notes, and the sessions behind them. |

The Signal cards lead every page that has one. They are ES\|QL-backed custom-content
panels: a question, a verdict in a sentence, the number as evidence, and the provenance
said out loud including what the metric cannot see. Every one renders "not enough yet" as
a first-class state that names what it is waiting for.

## The navigation graph

Every page carries a Links panel with all seven dashboards. Links carry neither the time
range nor the filters — each page is entered on its own terms, because every dashboard
sets a deliberate default range and a link that carried one left Meets' ten years behind
on every other page. `check()` fails the build if a nav link ever sets either.

Drilldowns are the other direction, and they do carry context:

| From | Trigger | To | Carries |
|---|---|---|---|
| Overview: projected-total chart | click a lift in the stack | Lift | `lift_slug`, and no time range, so Lift keeps its own 2y default |
| Overview: block timeline | click a bar | Session | `session_id` |
| Program: days table | click a row | Session | `session_id` |
| Session: PREV / NEXT | click a cell | Session | `session_id` = the cell value (URL drilldown) |
| Lift: e1RM chart, working-sets table | click a point or row | Session | `session_id` |
| History: session timeline, sessions table | click a bar or row | Session | `session_id` |
| Mindset: sessions table | click a row | Session | `session_id` |

A dashboard-to-dashboard drilldown does not carry the source page's own filters unless it
says so: every one of these lands on Session, which promises one session start to finish,
and carrying Lift's `lift_slug` alongside made that page show only the bench sets under a
header that had fallen back to its cold start.

Custom-content panels cannot be doors. Kibana strips `<a>` out of one entirely, class and
all — verified with `probe_links.py` on 2026-09-05, where a `<span>` styled as a button
rendered and three anchors came out as bare text. That is why the nav is a Links panel and
why the coach is one too.

## What Lens cannot do here, and what is in its place

- **Days to meet** is computed in Liquid from `program.meet_date`, not by Lens, which has
  no clean "today minus a date".
- **The meet-best reference line** on the projected-total chart is a static number in a
  saved object. It cannot read your data, so it is only drawn when
  `IRONSTACK_MEET_MAX_LB` says what the number is. The card beside it reads
  `MAX(total_lb)` from `workout-meets` and is the honest surface for it.
- **Sets as `weight x reps @ rpe`** are a custom-content panel, not a Lens table: Lens
  tables cannot compose strings without a formula per row.
- **A text column whose value is usually absent** does not belong in a Lens table at all.
  `last_value` renders an absent value as the literal string `(null)` and there is no way
  to change that, so those columns were dropped and the values are shown where they are
  actually present.
- **Per-panel time ranges** do not exist for custom content or for Lens in this Kibana. A
  `timeRange` in `embeddableConfig` is accepted, stored, and ignored. Panels that must not
  see the whole picker window carry their own date clause inside their query instead.

## Units and the clock

The data model is imperial and the labels say so: `weight_lb`, `tonnage_lb`,
`distance_ft`, `environment.temp_f`. `workout-meets` additionally carries kilograms
natively, because that is what a platform records; those are not a conversion of the
pounds beside them.

There is no `IRONSTACK_UNITS` switch. Relabelling `lb` as `kg` without converting the
numbers would turn a 909 lb total into a 909 kg one, which is the loudest lie a training
log can tell, and a real conversion belongs in the indexer rather than in a display
template. What does exist is `templates.UNITS`: every unit label in every card comes from
that one dict through the `$U_WEIGHT` / `$U_DISTANCE` / `$U_TEMP` / `$U_MASS_ALT` tokens,
so the day there is a conversion layer there is one row to change per unit instead of a
dozen string literals to find.

`IRONSTACK_TZ` is the same shape of decision: a fixed offset applied once, over every
`DATE_FORMAT` in the build and to Liquid's own `"now"` arithmetic, rather than a
timezone argument at eight call sites that ES\|QL does not accept anyway.

## The checks

`build_dashboards.py --check` and `verify_liquid.py` are the two gates. Between them they
cover the ways this directory has actually broken:

- duplicate saved-object ids, which overwrite each other silently on import
- dangling references, which import cleanly and render an error where a chart should be
- `embeddableConfig.drilldowns`, the dead key Kibana stores and ignores
- nav links carrying filters or a time range
- an `externalLink` pointing at a host that is not a documented placeholder — this repo
  shipped a private Elastic deployment's hostname, seven times over, until 2026-09-05
- a hardcoded personal record in a panel title or a Liquid template
- a custom-content panel reading a column its own ES\|QL `KEEP` does not project — the
  generic form of the bug that left the load card's comeback branch unreachable for weeks
- a `FROM` naming an index nothing indexes
- the committed `dashboards.ndjson` differing from what the build produces
- every template rendered with no rows, and with one row of all-nil columns, because
  `nil | round` is `0` and an unlogged value printed a confident zero
- a float column rendered raw, which python-liquid formats cleanly and Kibana's JavaScript
  Liquid renders as `7.130000114440918`
- a text column rendered without `| escape`, which lets a note containing `<div` break the
  card it is on
- a test fixture inventing a column the panel's query does not project
- any colour below 4.5:1 styling text a lifter has to read
- a template no dashboard builds

## Style

Iron Log: charcoal ground, warm chalk foregrounds, phase colours `#4a463f` / `#8f8a80` /
`#e4ddce` as a luminance ramp along the training arc, and oxblood `#a8211a` for exactly
one thing per dashboard. Split series use Kibana's built-in gray palette. Titles are short
and uppercase. No em-dashes in UI strings.
