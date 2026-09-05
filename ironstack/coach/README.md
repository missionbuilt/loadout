# Ironstack Coach

The coach is the agent behind the ASK THE COACH button on the dashboards. It is a Kibana
Agent Builder agent with read-only tools over your seven Ironstack indices: it answers what
you did, what a stretch of training looks like, what to start with today, and what fixed a
lift last time, all from your own journal.

It is a training partner, not a program and not a doctor. It suggests loads only under the
ceiling defined in [../CEILING.md](../CEILING.md), it does not write blocks or weeks, and
anything that sounds like pain gets a note in your journal and a pointer to a professional.

```
coach/
├── SYSTEM-PROMPT.md   the agent's instructions, ready to paste
├── tools.md           the tools it gets, each with the query it runs
├── privileges.md      the read-only key it runs as
└── README.md          this
```

**Agent Builder availability varies by Elastic tier and version.** Everything else in
Ironstack works without the coach: the logs, the indices, the seven dashboards, and the
workout-partner and workout-recall skills are all independent of it. The dashboards ship
with no coach link at all, which is what `--no-coach` means in `kibana/build_dashboards.py`.
Build the coach when you have somewhere to put it.

## Setup

### 1. Create the agent

Kibana, Agent Builder, new agent. Name it whatever you will recognize in a URL.

### 2. Paste the prompt

Everything below the rule in [SYSTEM-PROMPT.md](SYSTEM-PROMPT.md) goes in the agent's
instructions, verbatim. The part above the rule is for you.

### 3. Add the tools

[tools.md](tools.md) has them: an ES|QL tool per query, plus two search tools over
`workout-notes` and `workout-sessions`. Add `lift_ceiling` and `ceiling_evidence` first;
they are what makes the load rule checkable rather than a promise in a prompt. Everything
else is recall and trend, and the agent is useful with a subset.

### 4. Create the key

[privileges.md](privileges.md) has the role descriptor. Read-only, seven indices named
literally, no cluster privileges.

### 5. Point the dashboards at it

Copy the agent's URL out of Agent Builder, then rebuild and reimport from your instance
repo's checkout of the Loadout:

```bash
export IRONSTACK_COACH_URL="https://<your-kibana>/app/agent_builder/conversations/new?agentId=<id>"
python kibana/build_dashboards.py --allow-private-coach
python kibana/import.py
```

Every dashboard now carries an ASK THE COACH panel in its brand bar. `--allow-private-coach`
is required because the URL is your own deployment's hostname; the flag exists so such a URL
cannot be committed here by accident. Do not commit the regenerated `dashboards.ndjson`.

`IRONSTACK_COACH_URL` is one of three build-time values; `IRONSTACK_MEET_MAX_LB` and
`IRONSTACK_TZ` are documented in [../kibana/README.md](../kibana/README.md).

## Checking it

Ask it three things before you trust it:

1. **"What did I squat on <a date you remember>?"** It should answer with the sets and the
   date, or say the log has nothing for that day. Either is right. An invented session is
   not.
2. **"What should I open with on bench today?"** It should name a number, name the ceiling
   it checked, and say which session that ceiling came from.
3. **"Write me a twelve-week peaking block."** It should decline and say why, then offer
   what it can: what the log says about how the last block went.

If the second answer arrives with no ceiling cited, the `lift_ceiling` tool is not wired up.
Fix that before you use it to pick weights.
