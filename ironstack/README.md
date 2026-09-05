# Ironstack

**Train with a partner. Own your data. See everything.**

Ironstack turns Claude into your training partner and Elasticsearch + Kibana into your
training log. You log sessions conversationally — Claude asks the questions a good partner
asks, writes the log, and keeps you honest and motivated. Your data lands in **your own**
Elasticsearch, and seven Kibana dashboards read it back: what you lifted, how hard it was,
where you were, and how it felt.

Then you can ask it things:

> *"What did I squat a couple weeks ago?"*
> *"How did I feel when I was traveling in Las Vegas?"*
> *"What cue fixed my bench setup last block?"*

Like the rest of [The Loadout](../README.md), the skills are plain markdown — no installer,
no API key, no telemetry. And like Floodlight, Ironstack keeps your data where it belongs:
**every rep you log lives in your own private repo and your own Elasticsearch.** Nothing
here phones home.

> **Not medical advice.** Ironstack logs your training and encourages you. It does not
> build training programs, and it does not assess pain or injuries — it will point you to
> qualified professionals instead. Nothing in this project is a substitute for a doctor,
> physical therapist, or qualified coach.

## What's here

```
ironstack/
├── skills/          ← the Claude skills (drop into .claude/skills/)
│   ├── workout-partner/    log + motivate: your training partner with a notebook
│   └── workout-recall/     ask your training history anything
├── coach/           ← the Kibana agent behind ASK THE COACH: prompt, tools, privileges
├── starter/         ← the plumbing: copy this into your own PRIVATE repo
│   ├── schema/             JSON Schemas (workout, meet) + the index mappings
│   ├── ingest/             log.py, setup_indices.py, index_workouts.py, index_meets.py
│   ├── workflows/          GitHub Action → place at .github/workflows/index.yml
│   ├── config/             defaults, the exercise taxonomy, the equipment registry
│   ├── workouts/           where your logs go
│   └── meets/              where your meet records go (two public examples included)
├── examples/        ← one fictionalized session (.iron + .json + .md) showing the format
├── kibana/          ← build_dashboards.py → dashboards.ndjson, import.py, the dashboard map
└── CEILING.md       ← the load ceiling, written once for every surface that suggests a weight
```

**Skills are shared and public.** They live here in the Loadout. **Your data is private.**
It lives in a repo you create from `starter/`, plus your own Elasticsearch. The two meet in
your Claude session.

## How it works

```
you + Claude (workout-partner skill)
        │  conversation during or after your session
        ▼
workouts/2026/2026-09-01.iron            ← written once, by hand
        │  python ingest/log.py … --push
        ▼
… .json + .md in your private repo       ← generated, never hand-edited
        │  git push → GitHub Action validates & indexes
        ▼
your Elasticsearch, seven indices
        │
        ├─ Kibana: Overview → Program / Session / Lift / History / Meets / Mindset
        ├─ the Ironstack Coach, if you build one (coach/)
        └─ you + Claude (workout-recall skill): ask your history anything
```

## The seven indices

| Index | One doc per |
|---|---|
| `workout-sessions` | session, including `digest` — the whole day written out as a paragraph |
| `workout-sets` | set, with the derived numbers on it: e1RM, intensity, INOL, muscles, equipment |
| `workout-notes` | note, watch items included |
| `workout-meets` | competition attempt |
| `workout-daily` | training day, pre-aggregated |
| `workout-weekly` | ISO week, pre-aggregated: ACWR, monotony, strain, projected total |
| `ironstack-signals` | verdict row — the data behind the dashboards' Signal cards |

`ironstack-signals` carries no date-typed field on purpose. Every row is windowed when it is
written, so the time picker cannot quietly re-scope a verdict after the fact.

## Get started

### 1. Stand up Elasticsearch

Pick one:

- **Elastic Cloud Serverless** — create an **Elasticsearch** project ([docs](https://www.elastic.co/docs/solutions/elasticsearch-solution-project/get-started)). ELSER semantic search over your notes works out of the box.
- **Free self-hosted** — `curl -fsSL https://elastic.co/start-local | sh`, or your own Docker setup. The core app runs on the free tier; the semantic layer switches on wherever it's supported (`ES_SEMANTIC=auto`).

Create an API key with write access and note your Elasticsearch endpoint URL.

### 2. Make your private instance repo

Copy `starter/` into a new **private** repo (see [starter/README.md](starter/README.md) for
the commands), and move `workflows/index.yml` to `.github/workflows/index.yml`. Then add two
Actions secrets:

- `ES_ENDPOINT` — your Elasticsearch URL
- `ES_API_KEY` — the write API key

Every push that touches `workouts/**` or `meets/` now validates and indexes automatically.
No CI? Run `python ingest/setup_indices.py`, `python ingest/index_meets.py`, and
`python ingest/index_workouts.py` by hand — all three are idempotent.

### 3. Import the dashboards

```bash
export KIBANA_URL=https://<your-project>.kb.<region>.gcp.elastic.cloud
export ES_API_KEY=<key with Kibana saved-object privileges>
python kibana/import.py
```

(Or Kibana → Stack Management → Saved Objects → Import → `kibana/dashboards.ndjson`.)
Switch Kibana to dark mode; the palette assumes it.

Seven dashboards, one navigation graph, every aggregate a door to its detail:

| Dashboard | What it answers |
|---|---|
| **Overview** | Where the block stands. Three Signal verdicts, what you wrote about it in your own words, days to meet, the projected total against your meet best, and the block timeline as the door into a session |
| **Program** | Block, week, day. How hard this week is loading, in words; every day in the range; the weekly loading table |
| **Session** | One session, start to finish: header, top set, tiles, every set with its warm-up, notes in order, wrap-up, conditions, PREV / NEXT |
| **Lift** | One exercise over time: where it sits against its own best, e1RM with that best drawn on it, where the reps land by zone, every working set |
| **History** | How heavy this block is against earlier runs of the same kind, reps by zone, the session timeline, acute vs chronic load, the sessions table |
| **Meets** | The platform record: whether this run-in matches the last one, totals, DOTS, best lifts, every attempt |
| **Mindset** | Everything you wrote: what you keep writing down, the tag chart, recent notes, the sessions behind them |

Click a bar, a point or a row and you land on its detail with the context carried as a
filter: Overview → block timeline → Session → prev / next. [kibana/README.md](kibana/README.md)
has the full map, the drilldown table, and what Lens can and cannot do here.

**Three values are set at build time**, not in the saved objects:

| Variable | What it does |
|---|---|
| `IRONSTACK_COACH_URL` | Your coach's URL. Set it and every dashboard gets an ASK THE COACH panel. Unset, no panel is built — and `--no-coach` is how the committed `dashboards.ndjson` is built, so nothing here points at anyone's deployment |
| `IRONSTACK_MEET_MAX_LB` | Your best competition total, in pounds. Draws the reference line on Overview's projected-total chart, which is a Lens chart and cannot read your data. The card beside it reads the real number out of `workout-meets` either way |
| `IRONSTACK_TZ` | A fixed offset (`UTC`, `-07:00`) used to format dates and compute days-to-meet |

Rebuilding is `python kibana/build_dashboards.py` with those set, then `python kibana/import.py`.
With no coach of your own, build with `--no-coach`; an unset `IRONSTACK_COACH_URL` is an
error rather than a silent removal of the link from all seven dashboards.

### 4. Train with Claude

Add the two skills from `skills/` to Claude (Claude Code, Cowork, or claude.ai skills):

- **[workout-partner](skills/workout-partner/README.md)** — log sessions conversationally.
  It writes one `.iron` file in your private repo and runs the one command that generates
  the rest.
- **[workout-recall](skills/workout-recall/README.md)** — connect Claude to your
  Elasticsearch (e.g. the [Elasticsearch MCP server](https://github.com/elastic/mcp-server-elasticsearch))
  with a **read-only** API key and ask your history anything.

Each skill folder carries its own README, licence and references, so copying the folder
copies everything it needs. See `examples/` for what a logged session looks like.

### 5. The coach, if you want one

The ASK THE COACH button on the dashboards points at an agent you build in Kibana Agent
Builder: read-only tools over your seven indices, the same load ceiling the skills obey, and
the same two refusals. [coach/](coach/README.md) has the system prompt, the tools with the
ES|QL each one runs, and the minimum privileges for its API key.

**Agent Builder availability varies by Elastic tier and version.** Everything else works
without it — the logs, the indices, the dashboards, and both skills are independent of the
coach.

## Conventions

- Effort is one scale: **RPE** (10 = max). Reps-in-reserve converts as RPE = 10 − RIR.
- Every session carries its `program` context: block, phase (hypertrophy / strength /
  peaking), week, day of N, and the meet date. The indexer adds prev / next session links,
  streak day, and days to meet; never write those by hand.
- The `.iron` shorthand is the only thing written by hand. The JSON and the markdown are
  generated, so they cannot drift apart.
- Meets are logged in **kg** (the source of truth); pounds are derived.
- Carries log as `walks` with `distance_ft`; holds as `seconds`; bodyweight work as
  `weight_lb: 0`.
- Location is **coarse by design** — town or city only. Traveling? Log the city and
  `travel: true`, and "how did I feel in Vegas?" becomes answerable.
- Mindset notes carry tags from a small taxonomy (`felt-strong`, `body-awareness:<area>`,
  `grip`, `cue`, …) so themes trend over time.
- An exercise name that isn't in `config/exercises.json` is an error, not a warning. A lift
  that silently becomes a new name splits its own history in two.

## Design principles

1. **Your data is yours.** Public skills, private data. Your repo is the source of truth;
   Elasticsearch is a rebuildable projection of it.
2. **Claude is the interface.** Capture conversationally, recall conversationally. Dashboards
   are the glanceable layer.
3. **One rule, one place.** The load ceiling is in [CEILING.md](CEILING.md) and every surface
   that suggests a weight cites it. Two copies of a rule are two rules.
4. **AI-first, gracefully optional.** Semantic search over your notes (ELSER `semantic_text`)
   is designed in from day one, and everything degrades cleanly to structured and full-text
   search where it isn't available.
5. **No cost barrier.** Runs on Elastic Cloud Serverless *or* a free self-hosted Elastic.
6. **Partner, not programmer or doctor.** Honest encouragement and in-the-moment lift cues,
   yes. Programs and injury advice, never.

## License

MIT, like the rest of The Loadout. Fork it, learn from it, make it yours.

---

*Part of [The Loadout](../README.md) · [Mission Built](https://missionbuilt.io). Real strength is lifting others.*
