# The Approach

A pre-call intelligence brief for sellers and technical sellers. Know the room before you walk in.

Part of [The Loadout](https://github.com/missionbuilt/loadout) — a growing kit of open-source skills from the Mission Built ecosystem.

By H. Michael Nichols

---

## What this is

In powerlifting, the approach to the bar is not incidental — it is deliberate. You know your opener. You know your second and your third. You have studied the competition. You walk up already inside the lift.

The Approach does the same thing before a sales call. Before the deck. Before the discovery script. Before the awkward first silence. You know who is in the room, what they have said in public, what has already hit their stack, and what the three moves are before you dial in.

You give it a company name and a line of context. It researches the target across nine concurrent source batches — incidents, filings, earnings, leadership signals, tech stack, social posts, competitor footprint — and renders a structured field brief with two acts: business intelligence for the AE above the fold, technical depth for the SE below. Both halves travel in one document. Both get read before the call.

---

## What you get

**The brief renders as a live HTML artifact** following the Iron Log design language from [missionbuilt.io](https://missionbuilt.io): cream paper, oxblood accents, Oswald/Merriweather/JetBrains Mono typography. No rounded corners, no drop shadows. Reads like a field document, not a CRM.

**Sections covered:**

- **Scouting summary** — three-column card: who they are, what's changing this quarter, how you play it
- **Company snapshot** — founding, ownership, headcount, revenue signal, key products, motion this quarter
- **Leadership & org signals** — named contact bios, prior stack, recent public statements, buying signal vocabulary
- **Financial posture** — public filings (SEC 10-K/10-Q/8-K) or private triangulation from trade press
- **Industry context** — competitor incidents, regulatory moves, analyst sentiment, sector tailwinds
- **Social signal** — what the contact posted this week; verbatim quotes with engagement context
- **Tech stack & integrations** — inferred from job postings, BuiltWith, blogs; fit table with evidence
- **Security events** — known breaches, active CVEs on their stack, CISA KEV hits, SEC cyber disclosures
- **Plays** — 2–4 ranked demo/moment recommendations tied to specific findings, with *run when* and *audible if* footers
- **Risk flags** — RED/AMBER flags for procurement complexity, timing, stakeholder gaps, integration difficulty
- **The opener** — scripted first 2 minutes, grounded in a real public signal from the contact
- **Discovery questions** — 5–6 ranked questions for the AE, 5–6 for the SE, drawn from what the research surfaced

**Every source cited** is labeled with its trust tier (d1–d4). The brief footer shows a full list of sources scanned and a link safety summary.

---

## Install

**Option A — Hosted MCP (recommended)**

Connect the Loadout MCP server once and The Approach is available immediately:

```bash
# Claude Code
claude mcp add loadout https://mcp.missionbuilt.io/sse
```

Then say `"run the approach on [company]"` and follow the intake questions.

**Option B — Local skill file**

```bash
git clone https://github.com/missionbuilt/loadout.git /tmp/loadout
mkdir -p .claude/skills
cp -r /tmp/loadout/the-approach .claude/skills/
```

---

## Usage

### First call with a new target

```
approach for Rogue Fitness — I'm an AE at Sightline meeting with their VP of IT tomorrow at 2pm
```

or

```
prep me for my call with Acme Financial — we're at Elastic, talking agentic security ops, call is Friday 14:30 ET
```

The skill collects four quick inputs (company, contacts, context, date/time) and then runs. You'll see a single status line in chat as it researches, then the full brief renders as a persistent artifact.

### Repeat run (same target, updated intel)

```
refresh the approach for Rogue Fitness
```

The artifact updates in place with fresh intelligence. Sources are re-scanned; the countdown timer resets to the new meeting time.

### Saving your seller context

After your first run, say:

```
save approach config
```

The skill writes your name, company, and product to `APPROACH.md` in your workspace. Repeat runs skip those intake questions. See `APPROACH.example.md` for the full schema.

---

## Trigger phrases

Any of these will start The Approach:

- `approach`
- `run the approach`
- `run the approach on [company]`
- `brief me on [company]`
- `prep me for my call with [company]`
- `research for my call`
- `build the approach for [company]`
- `the approach for [company]`

---

## Config: APPROACH.md

Your personal context — seller name, company, product, default SE — lives in `APPROACH.md` at your project root. The skill reads it automatically on startup and skips those intake questions.

Copy `APPROACH.example.md` from this directory to your project root as `APPROACH.md` and fill in your fields. It is gitignored and never leaves your machine.

---

## Output

The brief is a live HTML artifact that stays open across runs. It follows the Iron Log design language from missionbuilt.io — cream paper background, oxblood accents, JetBrains Mono instrument-panel labels, no rounded corners, no drop shadows. It reads like a field document, not a dashboard.

Key V2 quirks layered into the V1 cream-paper base:

- **Rotated stamp** — "The Approach / Field Brief" in the masthead corner
- **T-minus countdown** — time until the call, counting down live
- **Scouting summary card** — three-column cut-in card above the fold: who they are / what's changing / how you play it
- **Run when / audible if** — every play has a run condition and an audible fallback, V2 coach's-playbook style

---

## License

MIT. Use it, fork it, adapt it for your organization. Attribution per the MIT terms is appreciated.

---

Part of the Mission Built ecosystem. The book teaches the principles. The Loadout puts the principles into operation.