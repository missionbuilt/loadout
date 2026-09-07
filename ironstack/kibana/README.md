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

Those counts are what the file in this directory actually holds, and `--check` asserts
them against `EXPECTED_OBJECTS` in `build_dashboards.py` rather than leaving them to be
kept in step by hand. That sentence used to be untrue: `check()` printed a total and
asserted nothing, so a panel added or dropped moved the number in the terminal and left
this line behind.

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
| `IRONSTACK_COACH_URL` | unset | The Ironstack Coach's URL. Set, every dashboard gets an ASK THE COACH links panel in its brand bar and the nav row narrows from 48 to 38 columns to make room. Unset, the panel is not built, the brand bar takes the full width, and the three strings on Mindset that point at "the coach" (the tagline, and the Signal card's provenance line and pointer) are swapped for wording that does not send the reader to something the page does not contain. `templates.py` reads this variable too, at import, applying the same `--check` neutralisation, because those strings are baked into the cards. Must be `http` or `https`; anything else is refused. |
| `IRONSTACK_MEET_MAX_LB` | unset | Your best competition total, in pounds. Set, Overview's projected-total chart gets an oxblood reference line at that number and says so in its title. Unset, the chart has no reference line and its title makes no claim about a meet best. The card beside it reads the real value out of `workout-meets` either way, so this is only for the Lens chart, which cannot read data. |
| `IRONSTACK_TZ` | `UTC` | A fixed offset (`UTC`, `-07:00`, `+0530`) used to compute days-to-meet. An unparseable value exits with that sentence rather than a traceback. It has to be a fixed offset, not an IANA zone: ES\|QL's `DATE_FORMAT` takes no timezone parameter, so the only lever either engine offers is shifting the instant before it is formatted. |

### Flags

| Flag | What it does |
|---|---|
| `--no-coach` | Build without ASK THE COACH. Without this, an unset `IRONSTACK_COACH_URL` is an error rather than a silent removal of the link from all seven dashboards. This is how the committed artifact is built. |
| `--no-meet-max` | Build the projected-total chart with no reference line and no number in its title. Without this, an unset `IRONSTACK_MEET_MAX_LB` is an error rather than a chart with no yardstick on it. This is how the committed artifact is built. The deployed Ironstack ran for a week without it: the Overview card said "96% of your meet best, 909 lb" while the chart of that exact number, eight inches to the right, had nothing to draw it against. |
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

**Build your own artifact before importing it.** The committed `dashboards.ndjson` is the
public one: `--no-coach --no-meet-max`, because a coach URL and a personal best cannot live
in this repo. Importing it into your own deployment is how Ironstack ran for a week with no
ASK THE COACH on any page and no reference line on the projected-total chart, while the
copy on Mindset still told the reader to go ask the coach. Both flags are now refusals
rather than defaults, and every build prints a `features:` line saying which of the two it
contains, so this cannot happen quietly again. For your own import:

```bash
export IRONSTACK_COACH_URL=https://<your-deployment>/app/agent_builder/...
export IRONSTACK_MEET_MAX_LB=909
python kibana/build_dashboards.py --allow-private-coach
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
own index and needs none. `check()` fails the build if a
`FROM` names an index outside the seven above. A control pointing at a data view that is
not built fails earlier still, by name, in `Dashboard.build()` - which is where it always
died, previously as a bare `KeyError` under a sentence in this file promising `check()`
would catch it.

Every field a panel names is checked against `starter/schema/mappings/*.json`: each Lens
`sourceField`, each KQL filter field, each control `fieldName`, and every column an ES|QL
query references in a `WHERE`, `EVAL`, `SORT`, `STATS`, `STATS ... BY` or `KEEP`. ES|QL
aliases are resolved rather than skipped, so `e1 = MAX(est_e1rm)` is checked on
`est_e1rm` and `e1` is then a real column. Renaming `est_e1rm` in a Lens column,
`weight_lb` in a `STATS`, or the `prilepin_zone` literal in a filter used to build
cleanly, pass every check, import without complaint, and render an empty panel.

## The dashboards

| Dashboard | id | Default range | What it answers |
|---|---|---|---|
| Overview | `ironstack-overview` | 2y | Where the block stands. Three Signal verdicts (how heavy was this week, am I ramping, what am I neglecting), what you wrote about it in your own words, days to meet, the projected total against your meet best, and the block timeline as the door into a session. |
| Program | `ironstack-program` | 1y | Block, week, day. How hard this week is loading, in words; every day in the range; the weekly loading table. Controls for block and week. |
| Session | `ironstack-session` | 1y | One session, start to finish. Header, top set, tiles, every set with its warm-up, notes in order, wrap-up, conditions, and PREV / NEXT. |
| Lift | `ironstack-lift` | 2y | One exercise over time. Where the lift sits against its own best, e1RM over time with that best drawn on it, where the reps land by zone, every working set. Control for block. |
| History | `ironstack-history` | 1y | How heavy this block is against earlier runs of the same kind, the share of reps by zone with a coverage line under it, the session timeline, acute vs chronic load, the sessions table. Controls for block and phase. |
| Meets | `ironstack-meets` | 10y | The platform record. Whether this run-in matches the last one, what the projected total has been worth on the platform, totals, DOTS, best lifts, every attempt. |
| Mindset | `ironstack-mindset` | 1y | Everything you wrote. What you keep writing down, the tag chart, recent notes, and the sessions behind them. |

The Signal cards lead every page that has one. They are ES\|QL-backed custom-content
panels: a question, a verdict in a sentence, the number as evidence, and the provenance
said out loud including what the metric cannot see. Every one renders "not enough yet" as
a first-class state that names what it is waiting for.

## The navigation graph

Every page carries a Links panel with six of the seven dashboards. **Lift is not one of
them.** It is a drilldown destination and carries no `lift_slug` control (a control and a
drilldown on the same field empty the page), so nothing but an incoming filter narrows
it: entered from the nav, `li-header` named one lift while `li-signal` followed whichever
lift the newest session used and `li-e1rm`, `li-zones` and `li-sets` drew every lift in
the range, reference line included. Closing that door is the fix. A bookmark or a back
button can still land there cold, so `li-header` and `li-signal` say so when they do -
the header query is `LIMIT 2` for exactly that reason, since one row back means a filter
narrowed it and two means nothing did.

Links carry neither the time
range nor the filters — each page is entered on its own terms, because every dashboard
sets a deliberate default range and a link that carried one left Meets' ten years behind
on every other page. `check()` fails the build if a nav link ever sets either.

Drilldowns are the other direction, and they do carry context:

| From | Trigger | To | Carries |
|---|---|---|---|
| Overview: projected-total chart | click a lift in the stack | Lift | `lift_slug`, and no time range, so Lift keeps its own 2y default. This is the only door into Lift. |
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

## A custom content panel takes no pointer input at all

Not "links are stripped" - the panel is inert. `probe_disclosure.py` put five mechanisms
in one panel and clicked and hovered every one of them:

| | |
|---|---|
| `<details>` / `<summary>` | renders, will not open |
| checkbox + `:checked` | renders, will not toggle |
| CSS `:hover` reveal | never fires |
| `title=""` tooltip | never appears |
| plain text | works |

So there is no tooltip, no disclosure, no hover and no link inside a card, and there
cannot be. Anything a reader has to be able to reach is either on the card in plain text
or it is somewhere else entirely - a Links panel, an XY chart's drilldown, or the coach.

This is why the Signal cards' provenance is short rather than folded: it could not be
folded, so it was cut, from 816 words across nine cards to 399, and from 232 words on
Overview's opening row to 125 - and then, in Phase 2 of the Sept 6 design plan, to a
fixed anatomy with a budget.

## A verdict card: five parts and forty words

`signal(question, body, scope, see, method)` in `templates.py`:

1. **Label** (`.q`) - the question, one per card. A state chip can sit beside it: the
   intensity card's `Open week` (a body that carries `__Q__` draws its own label).
2. **Verdict** (`.verdict`) - the answer, Oswald 22, chalk. A band changes weight, never
   colour; the max band adds an oxblood square and lights the gauge.
3. **Evidence** (`.ev`) - one sentence, serif 14, numbers inline in mono chalk.
4. **Gauge** with its baseline tick, captioned `Tick: ...` (`.base`).
5. **Scope** (`.prov`, under the rule) - ONE line, what window and what population.
   The last `.base` on a card that reads `ironstack-signals` is `Indexed <date>.`

Then the pointer (`.see`), plain: `History › reps by week`. No em-dashes anywhere in a
card; a dash that was doing a sentence's work became a period, a colon or a middot.

The **method paragraph is not on the card.** `signal()` collects it in `METHODS` and
`method_panel()` draws it once at the foot of the page - `SIGNAL_METHOD` on Overview
(three columns, one under each card), `PROGRAM_METHOD`, `LIFT_METHOD`, `BLOCK_METHOD`,
`MEETS_METHOD` (two columns) and `TAGS_METHOD` on their pages. A card that restates a
sentence of its own method fails `section_switcher_round_two`.

`section_word_budget` in `verify_liquid.py` measures every state the suite renders,
through `render()` itself, and fails any card whose WORST state puts more than 40 words
between the label and the rule (35 is the target). At Phase 2 the worst states sit at
32-40 across ~120 rendered states; the open-week intensity card, which was 61 words on a
Tuesday, is 38. The scope line is held to 18 words.

## After an import: open a NEW TAB, not a hard reload

A custom content panel's Liquid template is cached in the browser per panel, and
**cmd-shift-R does not clear it**. Verified on 2026-09-06: an import that changed the
projected-total card was checked with two hard reloads in the open tab, both of which
kept serving the previous template - the old number, the old panel height - while a
Lens title changed on the same import in the same tab proved the import itself had
landed. The same dashboard in a new tab showed both changes immediately.

The failure mode is worse than a stale page, because it is *selective*: Lens objects
refresh and custom panels do not, so a dashboard renders half the new build and half
the old one and looks like a bug in the build. Two working fixes were nearly reported
as failures this way. **Verify an import in a tab that was opened after it.**

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

- duplicate saved-object ids, which overwrite each other silently on import. The guard
  for this lives in `build()`, before the de-duplication that used to make it unfireable:
  `build()` collapsed `(type, id)` duplicates and only then handed the list to `check()`,
  so `check()` counted duplicates in an already-unique list. Give every Lens one id and
  `--check` printed `0 duplicate ids` while thirteen panels vanished. The de-dup is kept
  for shared builders, but only for identical objects; two DIFFERENT objects wearing one
  id is fatal
- dangling references, which import cleanly and render an error where a chart should be
- `embeddableConfig.drilldowns`, the dead key Kibana stores and ignores
- nav links carrying filters or a time range
- an `externalLink` pointing at a host that is not a documented placeholder — this repo
  shipped a private Elastic deployment's hostname, seven times over, until 2026-09-05
- a hardcoded personal record, and a hardcoded month-year, in any string a reader can
  see: a Lens or panel title, a Liquid template, a nav link's label, and — since
  2026-09-06 — a dashboard's own title and description, which were outside the scan while
  its comment claimed to cover "somebody else's meet total rendered as the reader's".
  Planting `back to Jan 2023. Best total 909.4 lb.` in the History dashboard's
  description passed `--check` clean before that was fixed. The month-year rule is flat
  and has no allowlist: every real month on these pages is `DATE_FORMAT`ted out of the
  reader's own index or computed in Liquid from a row, so a literal one is always
  somebody's personal history compiled into a public artifact. The load card used to
  close its provenance line with "so this reads back to Jan 2023"
- a custom-content panel reading a column its own ES\|QL `KEEP` does not project — the
  generic form of the bug that left the load card's comeback branch unreachable for weeks
- a `FROM` naming an index nothing indexes
- the committed `dashboards.ndjson` differing from what the build produces
- every template rendered with no rows, and with one row of all-nil columns, because
  `nil | round` is `0` and an unlogged value printed a confident zero. The all-nil render
  additionally asserts that no `0`, `0.0` or `0.00` stands alone inside a `.value`,
  `.hero` or `<b>` element — a zero is a measurement and absence is not, and the two must
  not print the same. A number inside a `.none` block is exempt, because a `.none` block
  is the card declining to rule and the number in it is a count of what it has
- a column whose mapped type is a float rendered raw, which python-liquid formats cleanly
  and Kibana's JavaScript Liquid renders as `7.130000114440918`. This follows
  ASSIGNMENTS as well as direct reads: `{% assign prpe = r['rpe'].value %}` and then
  `{{ prpe }}` carries no column name at the render site, so until 2026-09-06 the whole
  assign-then-render path was invisible to a guard whose entire job is that failure, and
  an unrounded `8.100000381469727` shipped to the Session page through it. A variable
  assigned from a column — or from another traced variable, including as a filter
  ARGUMENT — inherits that column's type until a filter launders it (`round`, `ceil`,
  `floor`, `size`, `escape`, `date`); arithmetic does not launder, so `| plus: 0` on a
  float32 is still a float32
- a column whose mapped type is anything else rendered without `| escape`, which lets a
  note containing `<div` break the card it is on. Both of these are built from
  `starter/schema/mappings/*.json` plus a declared table of ES\|QL alias types, and the
  table is closed against the queries in both directions. They were hand-maintained
  allowlists of column names until 2026-09-06, which is the wrong polarity: a text field
  nobody had listed passed, and `exercise.emphasis` was one
- a field that does not exist — in a Lens column, a KQL filter, a control, or anywhere in
  an ES\|QL query — checked against the mappings
- a test fixture inventing a column the panel's query does not project
- any colour below 4.5:1 styling text a lifter has to read
- a template no dashboard builds

An intensity zone exists only where a set has a relative intensity, which needs an earlier
estimate for that lift to measure against, which is built out of a logged RPE. A lifter who
logs no RPE therefore has `prilepin_zone` on nothing, and both zone charts — `hi-zones` and
`li-zones` — come back empty. A Lens panel cannot say why it is empty: a title is a fixed
string and a legend is a legend. So each of the two carries a `ZONE_COVERAGE` card directly
under it, reading the same sets, saying how many of the reps in range carry a zone. It says
that in every state rather than only in the empty one, on the principle that a branch which
exists only for the lifter who has none of something is a branch nobody tests.

The load card's comeback branch names the bar it is judging against. It used to say "Only 4
of the last 28 days carried load" and stop, which is a count presented as low with nothing
to be low against; it now says "under the 9 this ratio needs", reading
`layoff_min_training_days` off the row. That threshold is measured from the lifter's own
history rather than being a constant, and it moves as the corpus grows, which is exactly why
it has to come off the row and cannot be copy. The card does not restate how it is derived —
that lives in `derive.layoff_min_training_days` next to the constants that produce it — and
it guards on the field rather than assuming it, so an index written before the field existed
still renders and declines to name a bar rather than printing one of zero.

The same card names the day its windows were measured back from. `week_end` is the last day
TRAINED; `load_window_end` is the week's own end, or today while the week is open. When they
differ — the ordinary case, because most weeks end on a rest day — the ratio has moved since
the lifter last trained, which is the single most confusing thing this card does, and naming
both dates is what explains it:

    7-day load 37% above your 4-week average.
    Monotony 1.09.
    Measured to 2026-09-06; you last trained 2026-09-04.

When the week ended on a training day the two dates are equal and it says so once —
`Measured to 2026-09-06, the last day you trained.` Printing the same date twice to say two
things are equal reads worse than naming it plainly. When `load_window_end` is absent, which
is an index written before `derive` carried it onto the load row, the line is not drawn at
all: no blank, no nil, no dangling "Measured to". Both branches of the card make the same
implicit claim — "the last 28 days", "your 4-week average" — so both get the line, from one
substituted fragment rather than two copies that would drift silently.

Both fields are `keyword` on `ironstack-signals`, not `date`, because that index deliberately
carries no date-typed field — which is what stops the dashboard time picker re-scoping a
verdict. They arrive as ISO strings and are compared as strings, which is exact and needs no
parsing in a template.

## Style

Iron Log on Kibana's ground: the cards are transparent over the panel behind them, warm
chalk foregrounds, and oxblood `#a8211a` for exactly one thing per dashboard. `RULE` is
Kibana's own border colour, sampled, so a card's hairlines match the panel edge. Split
series use the gray palette, except the projected-total chart, which maps the three
competition lifts to the three chalks (`color_mapping()`, unverified until the Phase 3
round-two walk). Reference lines are STEEL dashed, so the accent stays with the cards.

Lens titles are two-to-four-word nouns in sentence case ("Block timeline", "Every working
set"); column labels and controls are sentence case too. An instruction survives in a
title only where the click works ("Sessions. Click one to open it", "Tags. Click one to
filter"); `verify_liquid` fails a datatable title that promises a click. No em-dashes in
UI strings.

The chrome is four grid units: a one-line brand bar (wordmark, section, the Mission Built
credit at the right) with the coach link beside it at h=2, and the nav at h=2, sentence
case, no brackets (Kibana underlines the current page itself). The dashboard description
carries what the tagline used to say.

Legend names on the projected-total chart are still slugs (`comp-deadlift`). The split
has to stay on `lift_slug` because the drilldown reads the split value into the Lift
page's `lift_slug` filter, and the signals index that page's card reads carries no
display name to filter on instead. Naming the legend means indexing `exercise.name` on
the lift signal rows first; it is on the after-the-meet list.

The custom panels follow the type system from the Sept 6 design review (Workouts project,
`ironstack-design-review-2026-09-06`), and `verify_liquid.py` `section_type_system` holds
them to it:

- **Six steps, one job each.** Display 40 (`.hero`, hero numbers, one per page), Title 28
  (`.title`, `.value`), Verdict 22 (`.sig .verdict`, sentence case, chalk), Body 14
  (Merriweather: `.prose`, `.sig .ev`, the method panel), Data 13 (mono: set rows, tables),
  Label 11 (mono caps: `.eyebrow`, `.sig .q`, one per card). Display and Title are
  `clamp()`ed to the panel width so a phone-wide card wraps instead of clipping. Nothing
  renders under 11px.
- **Three colours of text:** CHALK, DIM, STEEL. STEEL (5.0:1) is the floor. FAINT is for
  rules and BLOOD_DIM for the miss border; neither styles text.
- **Oxblood is a mark, never text:** the wordmark square, the strike through a missed
  attempt, the square after a max-band verdict and RPE, and a gauge fill only when its
  verdict is in the max band (`.sig .verdict.b-max ~ .gauge i`). Gauges are DIM otherwise.
- **Capitals live on a label or a name.** `UPPERCASE_ALLOWED` in `verify_liquid.py` is the
  list; a new selector that needs them is added there on purpose.
- **Warm-up sets are smaller, not fainter.** `.set.prep` is STEEL at 13px, no opacity.

### The three Phase 0 answers (probe_phase0.py, 2026-09-06)

- **Ground: transparent works.** `body{background:transparent}` shows Kibana's panel
  through the iframe. `$BG` is `transparent`; `GROUND` (`#0d1627`, sampled) exists only
  for the contrast arithmetic in `verify_liquid.section_contrast`. The warm-card-on-navy
  split the review measured on every page is gone, and the cards follow the theme.
- **Fonts: a base64 `@font-face` renders.** Kibana sets no `font-src`, and the sandbox
  honoured a `data:` woff2. `templates.py` embeds four of the five subsets from `fonts/` at
  import (JetBrains Mono 400 resolves to the 500 beside it) (`FONT_FACES`, at the top of `BASE_CSS` and the brand bar) and refuses to build
  without them. Cost: ~110 KB of CSS per custom panel, forty panels, ~4.5 MB of artifact;
  the Overview saved object alone is ~1 MB. If serverless ever refuses the import,
  Merriweather (the heaviest, 41 KB) is the one to drop first.
  `build_dashboards.check()` strips the data URIs before scanning for hardcoded records
  and months, and `verify_liquid.render()` strips them from every render - base64 will
  spell any three digits eventually, and the first run found "872" inside Merriweather.
- **Multi-query: no, and worse than no.** A panel whose `esql_query` is a list of two
  is not rendered empty; Kibana drops the panel from the dashboard on load (the tell is
  the "unsaved changes" prompt in edit mode - it repaired the panel list). One query per
  panel, so the three Overview cards stay three panels, and Phase 4 is the two deletions
  (the tagline, the coach prompt folded into the signal row) rather than a merge.

The block timeline used to carry its own three-colour phase ramp, because it was drawn as
three FILTERED metric columns — one each for `hypertrophy`, `strength` and `peaking`, the
literals compiled into the saved object. But `program.phase` is free text the lifter types
in their own shorthand, so a lifter running `base / accumulation / realization` matched
none of the three and got two empty charts under a legend naming phases they had never
used — and one of those two is Overview's only door into the Session page. Since
2026-09-06 the timelines split on the field instead: one metric, a `terms` bucket on
`program.phase` with `missingBucket` and `otherBucket` both on so a session with a blank
phase or a twenty-first phase name still draws a bar and still opens. The legend is
whatever the lifter actually wrote. The cost is the fixed ramp — a Lens palette cannot
know which of a stranger's phase names is the heavy one — and a chart with the reader's
own data on it is worth more than colour that means something.
