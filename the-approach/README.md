# The Approach

A pre-call intelligence brief for sellers and technical sellers. Know the room before you walk in.

Part of [The Loadout](https://github.com/missionbuilt/loadout) — a growing kit of open-source skills from the Mission Built ecosystem.

By H. Michael Nichols

---

## What this is

In the gym, the approach to the bar is not incidental — it is deliberate. You know your opener. You know your second and your third. You have studied the competition. You walk up already inside the lift.

The Approach does the same thing before a sales call. Before the deck. Before the discovery script. Before the awkward first silence. You know who is in the room, what they have said in public, what has already hit their stack, and what the three moves are before you dial in.

Give it a company name and a line of context. It researches the target across nine concurrent source categories — company snapshot, leadership, financials, industry context, social signal, tech stack, security events, demo prep, and discovery — then renders a structured field brief with two acts: business intelligence for the AE above the fold, technical depth for the SE below. Both halves travel in one document. Both get read before the call.

---

## What you get

**The brief renders as a live HTML artifact** in the Mission Built editorial style: cream paper, oxblood accents, Oswald display type, Merriweather body, JetBrains Mono for labels and metadata. No rounded corners. No drop shadows. Reads like a field document, not a CRM screen.

**Brief structure:**

- **Header** — company name, eyebrow with brief number and call date, meta row showing who it's for, source count, generated date, and reading time
- **Table of contents** — numbered jump links to all nine sections
- **Nine sections across two acts:**

| # | Section | Act |
|---|---|---|
| 01 | Company snapshot | AE |
| 02 | Leadership & the buyer | AE |
| 03 | Financial posture | AE |
| 04 | Industry context | AE |
| 05 | Recent signal | AE |
| 06 | Stack & integrations | SE |
| 07 | Public security events | SE |
| 08 | Demo prep | SE |
| 09 | Opener & discovery | Both |

An act divider separates the AE sections from the SE sections.

- **MEDDPICC scorecard** — eight qualification dimensions (Metrics, Economic Buyer, Decision Criteria, Decision Process, Paper Process, Identify Pain, Champion, Competition), each scored Confirmed / Partial / Unknown from public intel with a specific next action
- **Footer** — source count, generation date, Mission Built link

**Prose item types used within sections:**

- Paragraph with inline source attribution
- Pull quote with cite line and optional MEDDPICC chip
- Facts strip (key/value pairs)
- Tech stack table (layer → tool → status → note)
- Suggested opener script (~90 seconds, grounded in a real public signal)
- Discovery questions list with optional MEDDPICC chips

**Export:** The toolbar includes Export HTML (standalone file with all data baked in) and Print / PDF.

---

## Install

**Option A — Hosted MCP (recommended)**

Connect the Loadout MCP server once and The Approach is available immediately:

```bash
# Claude Code
claude mcp add loadout https://mcp.missionbuilt.io/sse
```

Or add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "loadout": {
      "url": "https://mcp.missionbuilt.io/sse"
    }
  }
}
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

The skill collects up to five quick inputs (company, contacts, context, date/time, seller name) then runs nine concurrent research batches. You'll see a single status line in chat as it works, then the full brief renders as a persistent artifact.

### Saving your seller context

After your first run, say:

```
save approach config
```

The skill writes your name, company, product, and default SE to `APPROACH.md` in your workspace. Repeat runs skip those intake questions automatically. See `APPROACH.example.md` for the full schema.

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

Your personal context — seller name, company, product, default SE — lives in `APPROACH.md` at your project root. The skill reads it on startup and skips any fields already defined there.

Copy `APPROACH.example.md` from this directory to your project root as `APPROACH.md` and fill in your fields. It is gitignored and stays on your machine.

---

## License

MIT. Use it, fork it, adapt it for your organization. Attribution per the MIT terms is appreciated.

---

*Part of the Mission Built ecosystem. The book teaches the principles. The Loadout puts the principles into operation.*
