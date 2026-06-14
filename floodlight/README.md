# Floodlight — Self-Contained Edition (v0.1.0)

A visibility-first security posture overview. Floodlight takes three quick inputs —
company name, industry and region, and the shape of your environment — and builds an
**ATT&CK Tactic Coverage** map: tactic by tactic, where you could watch an attacker move
and where you're blind.

It runs **disconnected**. No MCP server, no account, no telemetry — nothing leaves the
room beyond the public web research it does to find who targets your sector. A security
posture is exactly the kind of thing you should be able to run with your data staying put.

## What it is

The thesis: *the first step to security is visibility.* Before you buy another tool or
write another detection, you find out which corners of the room are already lit and which
are black. Floodlight produces:

- A **Tactic Coverage strip** across the ATT&CK tactics an attacker has to pass through
  (Initial Access → Impact), each cell green / amber / red by threat-weighted visibility.
  Amber means a source exists but quality or retention isn't enough — blind vs. not-good-enough.
- **Choke-point tactics badged** — the convergence points an attacker can't avoid. The
  #1 fix is a red cell that is also a choke point.
- A **quick-wins roadmap** ranked by how much coverage each added log source buys you.
- Per-source **quality and retention** flags, with the specific fields each source provides.
- **Live in-report toggles** — mark what you have today, watch the map recolor, export.

What it is **not**: a CISO, a maturity grade, a peer benchmark, or confident "APT-X is
attacking you" attribution. It reasons from sector and region, shows every assumption it
made, and invites you to correct and re-run. A modest, correct map beats a confident,
wrong one.

## How it works

Two layers, sourced differently on purpose:

1. **Baked framework** (`floodlight-catalog.json`) — tactics, choke points, log sources,
   the exact fields and event types each provides, retention-by-regulation, and the
   technique→source mappings. Curated and version-stamped so the report never hallucinates
   a plausible-but-wrong event ID or field. Grounded in MITRE ATT&CK v18, the CTID Top
   ATT&CK Techniques, DeTT&CT, and Red Canary prevalence data.
2. **Live company layer** — sector/region adversaries, verified public breaches, and
   applicable regulations, researched at runtime and cited. Assembled into `FLOODLIGHT_DATA`.

The skill assembles `FLOODLIGHT_DATA`, then `scripts/inject.py` fills both layers into the
bundled template and writes a single self-contained `floodlight-posture.html`.

## Install

Claude Code / Cowork:

    cp -r floodlight .claude/skills/

Claude.ai: upload this folder as a user skill.

## Run

Say "run floodlight for [company]" or "build my security posture." The skill collects
three inputs, researches the threat landscape for your sector and region, assembles the
data, and renders `floodlight-posture.html` locally. Open it in any browser, toggle the
log sources you actually have, and watch the coverage map recolor. Export to HTML or print
to PDF.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The skill — intake, research, the two-layer model, `FLOODLIGHT_DATA` schema, render, rules |
| `floodlight-catalog.json` | Baked framework catalog (ATT&CK v18): tactics, choke points, log sources + fields, technique mappings, retention |
| `floodlight-template.html` | Interactive posture template with `__FLOODLIGHT_DATA__` and `__FLOODLIGHT_CATALOG__` placeholders |
| `scripts/inject.py` | Local render step — validates JSON, escapes `</script>`, fills both placeholders |
| `SKILL-DESIGN.md` | Design spec and rationale (template/catalog maintenance only) |

## Caveat

Floodlight is a **starting overview**, not a security program and not professional advice.
Event IDs and field names reflect common Windows / Sysmon / cloud telemetry and vary by
platform and configuration. Choke-point and prevalence flags are directional. Use it to
find the darkest corner first — then bring in the people and tools to light it properly.

MIT. Part of The Loadout · missionbuilt.io
