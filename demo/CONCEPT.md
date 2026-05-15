# Demo Skill — Concept

Navattic-style interactive click-through demos, embeddable on missionbuilt.io.

## Core constraint

The demo pulls from the **live, published skill output** — the real artifact, not invented content, not screenshots, not mocks. If the Warmup produces a brief, the demo shows that brief. The player wraps what the skill actually generates.

## How it works

A player shell overlays a guided hotspot system on top of the real skill HTML artifact. Each step highlights a CSS selector, dims everything else, and shows a tooltip. Click to advance.

**Player components:**
- Spotlight overlay (dim everything except the highlighted element)
- Pulsing oxblood hotspot ring on the target element
- Monospace tooltip bubble (Iron Log style — dark, sharp corners, no shadows)
- Step counter top-right, prev/next nav bottom
- Skip tour link for users who want to see the full brief unguided

## Step config (per skill, `tour.json`)

```json
{
  "skill": "warmup",
  "steps": [
    {
      "selector": ".masthead",
      "heading": "Know what moved.",
      "body": "Before the first meeting, before the first decision.",
      "tip_position": "below"
    },
    {
      "selector": ".item:first-child",
      "heading": "Every item is sourced and tiered.",
      "body": "Source name, trust tier, and date on every entry.",
      "tip_position": "right"
    }
  ]
}
```

## Proposed Warmup tour steps

1. Masthead — "Know what moved before you open your inbox"
2. High-severity item with tags — "Every item is sourced and tiered"
3. Deep Dive button — "One click for the full context"
4. Sources panel — "You always see what built the brief"
5. Link safety badge — "Every URL scanned before the brief renders"
6. Save PDF — "Take it into your first meeting"

## Proposed Spotter tour steps

1. Epic in review (weak version)
2. Lens scores revealed
3. Flagged criterion with coaching note
4. Iterate flow
5. Strong version comparison

## Where it lives

- `missionbuilt.io/loadout` — each skill card embeds its demo
- `missionbuilt.io/loadout/warmup` — full demo above the feature list
- `missionbuilt.io/loadout/spotter` — same pattern
- Each skill ships with its own `tour.json`; the player shell is shared

## Implementation notes

- Single HTML file player (no external dependencies)
- Uses Mission Built design system tokens
- Embeds via `<iframe>` or inline
- Player shell is generic; `tour.json` is skill-specific
- Build the Warmup tour first once warmup skill is complete
