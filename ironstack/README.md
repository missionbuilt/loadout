# Ironstack

**Train with a partner. Own your data. See everything.**

Ironstack turns Claude into your training partner and Elasticsearch + Kibana into your training log. You log sessions conversationally — Claude asks the questions a good partner asks, writes the log, and keeps you honest and motivated. Your data lands in **your own** Elasticsearch, and Kibana dashboards show your training from every angle: what you lifted, how hard it was, where you were, and how it felt.

Then you can ask it things:

> *"What did I squat a couple weeks ago?"*
> *"How did I feel when I was traveling in Las Vegas?"*
> *"What cue fixed my bench setup last block?"*

Like the rest of [The Loadout](../README.md), the skills are plain markdown — no installer, no API key, no telemetry. And like Floodlight, Ironstack keeps your data where it belongs: **every rep you log lives in your own private repo and your own Elasticsearch.** Nothing here phones home.

> ⚠️ **Not medical advice.** Ironstack logs your training and encourages you. It does not build training programs, and it does not assess pain or injuries — it will point you to qualified professionals instead. Nothing in this project is a substitute for a doctor, physical therapist, or qualified coach.

## The two halves

```
ironstack/
├── skills/          ← the Claude skills (drop into .claude/skills/)
│   ├── workout-partner/    log + motivate: your training partner with a notebook
│   └── workout-recall/     ask your training history anything
├── starter/         ← the plumbing: copy this into your own PRIVATE repo
│   ├── schema/             JSON Schema for logs + Elasticsearch index mappings
│   ├── ingest/             setup_indices.py + index_workouts.py (idempotent)
│   ├── workflows/          GitHub Action → place at .github/workflows/index.yml
│   └── workouts/           where your logs go
├── examples/        ← one fictionalized session (md + json) showing the format
└── kibana/          ← dashboard saved objects for import
```

**Skills** are shared and public — they live here in the Loadout. **Your data** is private — it lives in a repo you create from `starter/`, plus your own Elasticsearch. The two meet in your Claude session.

## How it works

```
you + Claude (workout-partner skill)
        │  conversation during/after your session
        ▼
workouts/2026/2026-09-01.md + .json     ← your private repo (source of truth)
        │  git push → GitHub Action validates & indexes
        ▼
your Elasticsearch (workout-sessions / workout-sets / workout-notes)
        │
        ├─ Kibana dashboards: Overview → Session drill-down → Mindset
        └─ you + Claude (workout-recall skill): ask your history anything
```

## Get started

### 1. Stand up Elasticsearch

Pick one:

- **Elastic Cloud Serverless** — create an **Elasticsearch** project ([docs](https://www.elastic.co/docs/solutions/elasticsearch-solution-project/get-started)). ELSER semantic search over your notes works out of the box.
- **Free self-hosted** — `curl -fsSL https://elastic.co/start-local | sh` or your own Docker setup. The full core app runs on the free tier; the semantic layer switches on automatically wherever it's supported (`ES_SEMANTIC=auto`).

Create an API key with write access and note your Elasticsearch endpoint URL.

### 2. Make your private instance repo

Copy `starter/` into a new **private** repo (see [starter/README.md](starter/README.md) for the commands), and move `workflows/index.yml` to `.github/workflows/index.yml`. Then add two Actions secrets:

- `ES_ENDPOINT` — your Elasticsearch URL
- `ES_API_KEY` — the write API key

Every push that touches `workouts/**` now validates and indexes automatically. No CI? Run `python ingest/setup_indices.py` and `python ingest/index_workouts.py` by hand — both are idempotent.

### 3. Import the dashboards

Kibana → Stack Management → Saved Objects → Import → `kibana/dashboards.ndjson`. Three dashboards: **Overview**, **Session Drill-down**, **Mindset**. (See `kibana/README.md`.)

### 4. Train with Claude

Add the two skills from `skills/` to Claude (Claude Code, Cowork, or claude.ai skills):

- **workout-partner** — log sessions conversationally; it produces the `.md` + `.json` pair in your private repo.
- **workout-recall** — connect Claude to your Elasticsearch (e.g. the [Elasticsearch MCP server](https://github.com/elastic/mcp-server-elasticsearch)) with a **read-only** API key and ask your history anything.

See `examples/` for what a logged session looks like.

## Conventions

- Effort is one scale: **RPE** (10 = max). Reps-in-reserve converts as RPE = 10 − RIR.
- Carries log as `walks` with `distance_ft`; holds as `seconds`; bodyweight work as `weight_lb: 0`.
- Location is **coarse by design** — town/city only. Traveling? Log the city and `travel: true`, and "how did I feel in Vegas?" becomes answerable.
- Mindset notes carry tags from a small taxonomy (`felt-strong`, `body-awareness:<area>`, `grip`, `cue`, …) so themes trend over time.

## Design principles

1. **Your data is yours.** Public skills, private data. Your repo is the source of truth; Elasticsearch is a rebuildable projection of it.
2. **Claude is the interface.** Capture conversationally, recall conversationally. Dashboards are the glanceable layer.
3. **AI-first, gracefully optional.** Semantic search over your notes (ELSER `semantic_text`) is designed in from day one — and everything degrades cleanly to structured + full-text search where it isn't available.
4. **No cost barrier.** Runs on Elastic Cloud Serverless *or* a free self-hosted Elastic.
5. **Partner, not programmer or doctor.** Honest encouragement and in-the-moment lift cues, yes. Programs and injury advice, never.

## License

MIT, like the rest of The Loadout. Fork it, learn from it, make it yours.

---

*Part of [The Loadout](../README.md) · [Mission Built](https://missionbuilt.io). Real strength is lifting others.*
