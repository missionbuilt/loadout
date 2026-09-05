# Workout Recall

Ask your training history anything. Workout Recall is the reading half of
[Ironstack](../../README.md): it queries the seven Elasticsearch indices your logs are
indexed into and answers from them, with the session date on every fact.

> *"What did I squat a couple weeks ago?"*
> *"How did I feel when I was traveling in Las Vegas?"*
> *"When was my grip last a problem?"*

It answers from your log or it says the log does not have it. It does not write programs, it
does not assess pain, and it does not carry a statistic from anywhere but your own data.

## Prerequisites

- An Ironstack instance repo with sessions indexed. See
  [starter/README.md](../../starter/README.md).
- A connection from Claude to **your** Elasticsearch, with a **read-only** API key — the
  [Elasticsearch MCP server](https://github.com/elastic/mcp-server-elasticsearch) or any
  configured Elasticsearch tool.

Without the connection the skill has nothing to read, and it will say so rather than
answering from memory.

## Install

Claude Code / Cowork:

    cp -r workout-recall .claude/skills/

Claude.ai: upload this folder as a user skill.

## Run

Ask. "What did I bench last week", "how is this block loading", "summarize the block so
far", "when did my lower back last bother me". The skill picks structured, semantic or
hybrid retrieval to match the question.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The skill: prerequisites, retrieval mode, how to answer, boundaries |
| `references/indices.md` | Every field in all seven indices, and the semantic siblings |
| `references/metrics.md` | What the derived numbers mean and where each one breaks down |
| `references/queries.md` | ES\|QL recipes to start from |
| `SKILL-DESIGN.md` | Why the skill is shaped this way (maintenance only) |
| `LICENSE` | MIT |

## Caveat

Not medical advice, and not a coach. Workout Recall recalls what you logged. Programming
belongs to your coach or your program, and anything that sounds like pain or injury belongs
to a qualified professional.

MIT. Part of The Loadout · missionbuilt.io
