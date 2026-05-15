# The Warmup

> A daily intelligence brief for the first coffee. Know what moved before you
> open your inbox.

Part of [The Loadout](https://github.com/missionbuilt/loadout) — a growing
kit of open-source skills from the [*Mission Built*](https://missionbuilt.io)
ecosystem.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/missionbuilt/loadout/blob/main/warmup/LICENSE)

By [H. Michael Nichols](https://www.linkedin.com/in/hmichaelnichols)

---

## What this is

You do not go under the bar cold. In the gym, the warmup is the ten minutes
that makes the next ninety honest. It tells you what is tight, what needs
adjustment, and whether today's plan needs to change before the work begins.

The Warmup does the same thing for your workday. Before the first meeting,
before the first decision — you know what threat actors are active, what
vulnerabilities dropped overnight, what your vendors are doing. You start
informed instead of catching up for the first hour.

The Warmup reads your sources, synthesizes what matters, and delivers it as
a single live document you pull with your first coffee. Every item is labeled
with its source and trust tier. You always know what you are reading and where
it came from.

---

## Three modes

### CISO Mode

Built for cybersecurity executives. Tell the Warmup your sector and it loads
a pre-curated source suite: CISA advisories, the CISA Known Exploited
Vulnerabilities catalog, MITRE ATT&CK, CrowdStrike, Palo Alto Unit 42,
Elastic Security Labs, Google Mandiant, Microsoft MSTIC, Cisco Talos, and
more — plus sector-specific sources for Healthcare, Financial Services, Energy,
Government, Manufacturing/OT, and others.

Each brief covers five sections:

- **Threat Landscape** — Active threat actors, targeted sectors, MITRE-mapped
  TTPs. CrowdStrike taxonomy (SCATTERED SPIDER, COZY BEAR, VOLT TYPHOON).
- **Emerging Threats** — New CVEs, CISA KEV additions, zero-days, new malware
  families. Sorted by exploitation urgency.
- **Research Digest** — New publications from Tier 1 and Tier 2 sources.
  Substantive research only, not vendor marketing.
- **Industry Intel** — M&A, product launches, leadership changes, regulatory
  moves (SEC, HIPAA, DORA, CMMC). Flagged by type.
- **Social Signal** — High-signal community discussion, clearly labeled
  as unverified. Omitted when there is nothing worth your time.

### Product Leader Mode

Built for product managers, CPOs, and product-oriented executives. Tell the
Warmup your product area, vertical, and build type and it loads a source
suite tuned for competitive and market intelligence: competitor newsrooms,
analyst firms (Gartner, Forrester, CB Insights), AI model release trackers,
funding and M&A feeds, and the voices worth following in your space.

Each brief covers five sections:

- **Company Intel** — News, earnings, product launches, and leadership moves
  from your own org. SEC filings flagged when relevant.
- **Competitor Moves** — Product announcements, pricing changes, hiring
  signals, and positioning shifts from your named competitor set.
- **AI & Tooling** — Model releases, capability updates, and developer
  tooling changes relevant to your roadmap.
- **Market & Funding** — VC rounds, M&A, analyst reports, and regulatory
  moves in your vertical.
- **Social Signal** — High-signal community discussion, clearly labeled
  as unverified. Omitted when there is nothing worth your time.

### Custom Mode

Describe your morning interests in plain language and the Warmup builds your
source suite from scratch. Stocks, industry news, competitor blogs, AI model
releases, policy changes, local business news — whatever you need to start
the day in the loop.

Every recommended source comes with a tier rating (Authoritative / Research /
News / Vendor) so you know exactly what weight to give each item.

---

## Source transparency

The bottom of every brief shows a full list of every source consulted: which
were active, which were quiet, which you have excluded. You always know what
built your brief.

You can add, remove, or exclude any source at any time. The config lives in
a plain `WARMUP.md` file at your project root — readable, editable, yours.

---

## Install

Clone the Loadout and copy the Warmup skill into your project:

```bash
git clone https://github.com/missionbuilt/loadout.git /tmp/loadout
mkdir -p .claude/skills
cp -r /tmp/loadout/warmup .claude/skills/
```

Or install the `.plugin` file directly in Claude Code or Cowork from
[the Loadout releases page](https://github.com/missionbuilt/loadout/releases).

---

## Usage

### First run

```
warmup setup
```

Walks you through four questions for CISO mode (sector, optional company
name, region, vendors to track) or an open-form description for Custom mode.
Builds your source suite, shows it for review, saves your config, and runs
a test brief.

Your config is saved to `WARMUP.md` at your project root. This file is
personal — it contains your company, sources, and interests. Copy
`WARMUP.example.md` from the repo root to see the full schema. `WARMUP.md`
is gitignored and never leaves your machine.

### Run the brief

```
warmup
```

or

```
morning brief
```

Reads your config, fetches live intelligence from each active source,
synthesizes it into sections, and renders an Iron Log-branded HTML artifact.
One summary line in chat. The brief is the artifact.

### Manage your sources

```
warmup config
show my warmup sources
add [source name] to my warmup
exclude [source name] from warmup
```

---

## Output

The brief is a live HTML artifact that stays open and refreshes each time
you run it. It follows the Iron Log design language from
[missionbuilt.io](https://missionbuilt.io) — charcoal background, oxblood
accents, JetBrains Mono instrument-panel labels, no rounded corners, no
drop shadows. It reads like a field document, not a dashboard.

---

## Customizing for your team

The Warmup is designed to stay generic. The config that makes it yours —
your sector, your vendors, your added sources — lives in `WARMUP.md` at your
project root. Pull updates to the skill without touching your config.

---

## License

MIT. Use it, fork it, adapt it for your organization. Attribution per the MIT
terms is appreciated.

---

*Part of the [Mission Built](https://missionbuilt.io) ecosystem. The book
teaches the principles. The Loadout puts the principles into operation.*
