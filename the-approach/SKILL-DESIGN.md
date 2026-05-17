# The Approach — Artifact Design Spec (v0.1.0 · Field Brief)

The output is a single-file HTML artifact — a scrolling page, not tabbed, not paginated. The v0.1.0 template is a V1/V2 blend: V1 cream-paper Morning Edition base with V2 Scout Sheet quirks layered in.

Follow these specifications exactly. Do not approximate colors or substitute fonts. The visual identity is the trust signal.

---

## Design lineage

The Approach builds on the same Iron Log design system as The Warmup but with a distinct job: the Warmup is a morning read, The Approach is a pre-game card. The V2 quirks (stamp, countdown, scouting summary cut-in, run-when/audible footers) signal that this is a performance document, not a digest.

**V1 (Field Brief)** is the base — cream paper, editorial leads, two-act structure, interlude separator, sources panel.

**V2 (Scout Sheet)** contributes the quirks — rotated stamp in the masthead corner, T-minus countdown pill, scouting summary card with `::before` cut-in label, `run when / audible if` footers on every play, Permanent Marker handwritten annotations.

The agent writes only `window.APPROACH_DATA`. All CSS, layout, renderer logic, and countdown timer live in `approach-template.html` and must not be reconstructed or modified per-run.

---

## Color tokens

All tokens live in `:root`. The agent never touches CSS.

```css
:root {
  color-scheme: light;

  /* Paper surfaces */
  --paper:        #f3ecdc;   /* Page background — cream newsprint */
  --paper-warm:   #ebe2cf;   /* Signal bar, interlude, opener script */
  --paper-card:   #ede5d2;   /* Scouting summary, person cards, play cards */
  --paper-soft:   #efe8d6;   /* Deep-dive panels */

  /* Ink */
  --ink:          #1a1612;   /* Primary text */
  --ink-soft:     #3a342d;   /* Body summaries, lead body text */
  --ink-dim:      #6a5f50;   /* Metadata, source names, act-marker sub */
  --ink-faint:    #968974;   /* Captions, quiet states, dotted separators */

  /* Rules */
  --rule:         #c8bea7;   /* Borders, dividers */
  --rule-soft:    #d8cfb8;   /* Inner item separators, play-intel dashes */

  /* Accents */
  --blood:        #8a2017;   /* Primary accent — headings, stamps, drop caps, play nums */
  --blood-bright: #a8281e;   /* Hover states, tag fills */
  --blood-soft:   #f0d8d4;   /* Risk flag backgrounds (RED) */
  --army:         #5f6e26;   /* Secondary accent — callouts, run-when text, scan badge */
  --army-soft:    #dfe3c4;   /* Callout backgrounds, risk flag backgrounds (AMBER) */

  /* Fonts */
  --font-display: 'Oswald', sans-serif;      /* Headlines, masthead, section labels */
  --font-serif:   'Merriweather', Georgia, serif;  /* Body text, decks, quotes */
  --font-mono:    'JetBrains Mono', monospace;     /* Kickers, meta, labels, pills */
  --font-hand:    'Permanent Marker', sans-serif;  /* Stamps, margin notes, hand annotations */
}
```

---

## Fonts

Four families, four jobs, no exceptions.

| Variable | Family | Job |
|---|---|---|
| `--font-display` | Oswald | Title, section headlines, act markers, play titles, demo ordinals |
| `--font-serif` | Merriweather | Body text, decks, quotes, discovery questions |
| `--font-mono` | JetBrains Mono | Kickers, metadata, source names, scan pill, countdown, run-when/audible labels |
| `--font-hand` | Permanent Marker | Stamps, margin notes, hand annotations on plays, scouting hand note |

---

## Global reset

```css
*, *::before, *::after {
  box-sizing: border-box; margin: 0; padding: 0;
  border-radius: 0; box-shadow: none !important;
}
body {
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 16px;
  line-height: 1.7;
}
a { color: var(--ink); text-decoration: none; }
a:hover { color: var(--blood); }
::selection { background: rgba(138,32,23,0.18); color: var(--ink); }
```

---

## Layout — top to bottom

### 1. Masthead

Background: `--paper`. Bottom border: `3px double var(--ink)` (nameplate double rule). Padding: `36px 56px 24px`.

**Top row (np-row1):**
- Vol/issue identifier · date · scan time · *Ferrum Sumus* italic
- Scan pill: `border: 1px solid var(--rule)`, army dot, source count
- Countdown pill: `border: 1px solid var(--blood)`, blood text — "T-MINUS Xh Ym", live countdown. Hidden if no meeting date provided.

**Masthead body (grid: stamp left + title center):**

Left — the V2 stamp (cream/blood variant):
```
border: 3px solid var(--blood)
background: rgba(138,32,23,0.04)
transform: rotate(-2.5deg)
```
- Top: "The Approach" in `--font-hand`, blood
- Middle: "FIELD BRIEF" in Oswald 700, blood, 28px
- Bottom: "Pre-Call Intel" in JetBrains Mono, 9px, blood

Center — masthead title block:
- `THE APPROACH` in Oswald 700, `clamp(56px, 9vw, 120px)`, ink — with trailing blood square `■`
- Deck (np-deck): Merriweather italic 300, 18px, ink-soft — "A field brief on **[Target Company]** — [context]"

**Bottom row (np-row2):**
- Left: "Walk in heavy, [FirstName]." in Permanent Marker, 26px, blood, -1.2deg rotation
- Right: selling meta · briefed-for label · link safety

### 2. Signal bar

Background: `--paper-warm`. Borders: top + bottom `1px solid var(--rule)`. Padding: `14px 56px`.

Six stat cells in a grid, separated by `1px solid var(--rule)`. Maps to `companyFacts[0..5]`.

Label: JetBrains Mono 400, 9px, `--ink-faint`, uppercase, letter-spacing 0.22em.
Value: JetBrains Mono 500, `--ink`.

### 3. Scouting summary (V2 cut-in card, cream theme)

Border: `1px solid var(--rule)`. Background: `--paper-card`. Margin: `28px 56px`.

`::before` pseudo-element: "SCOUTING SUMMARY" — JetBrains Mono 700, 10px, blood, letter-spacing 0.32em. Positioned `top: -10px; left: 24px`, `background: var(--paper)`, `padding: 0 12px`.

Three-column grid (`summary-grid`), each column separated by `1px solid var(--rule-soft)`:
- **Who They Are** — `whoTheyAre`
- **What's Changing** — `whatIsChanging`
- **How We Play It** — `howWePlayIt` + hand note in Permanent Marker, blood

### 4. People strip

Full-width, `padding: 0 56px`. Hidden if `people` array is empty.

Person cards are horizontal-scrolling flex cards. Each card:
- `background: --paper-card`, `border: 1px solid var(--rule)`
- Initials block: 42×42px, `background: --blood`, `color: --paper`, Oswald 700
- Name: Oswald 600, 18px, uppercase
- Title: JetBrains Mono, 10px, ink-dim
- Recent signal: Merriweather italic, 14px, ink-soft — left-border `2px solid var(--blood)`
- Role stamp: Permanent Marker, 13px, blood — absolute top-right

### 5. Sticky scroll nav (secnav)

`position: sticky; top: 0; z-index: 50`. Background: `rgba(243,236,220,0.96)` with `backdrop-filter: blur(8px)`.

Group labels in blood. Section links in ink-dim; active `.on` state: `border-bottom: 1px solid var(--blood)`.

### 6. Act markers

```
margin: 56px 0 0
border-top + border-bottom: 1px solid var(--rule)
padding: 18px 0 14px
grid: 1fr auto 1fr
```

Center label: JetBrains Mono 700, 11px, letter-spacing 0.34em. Flanked by `height: 1px; background: var(--ink)` rule spans.

Format: `ACT I · The Read` with `— what the AE needs above the fold` in Merriweather italic below.

### 7. Sections

Each `section.sec` has `padding-top: 48px`. Adjacent sections separated by `1px solid var(--rule)`.

**Section eyebrow:**
- Kicker: JetBrains Mono 700, 10px, blood, letter-spacing 0.28em
- Label: Oswald 600, `clamp(28px, 4vw, 40px)`, ink
- Sub: Merriweather italic 300, 16px, ink-soft

**Lead item (`.lead`):**
- Item meta: tier dot + source + date + tags — JetBrains Mono 400, 10px
- Tier dots: d1 = army, d2 = blood, d3 = ink, d4 = ink-faint
- Headline (`.hl`): Oswald 600, `clamp(28px, 3.4vw, 40px)`, ink
- Deck: Merriweather italic, 18px, ink-soft
- Body: Merriweather 400, 16.5px, ink-soft
- Drop cap on first letter: Oswald 700, 3.4em, blood — floated left
- Margin note: Permanent Marker, 18px, blood, `-1deg` rotation

**Grid items (`.grid`):**
- Two-column grid
- Each item: Oswald 500, 21px headline + Merriweather body

**Callout (`.callout`):**
- `border-left: 3px solid var(--army)`, `background: --army-soft`
- Label "WHAT TO DO WITH THIS": JetBrains Mono 700, 9.5px, army

### 8. Interlude (ACT I → ACT II separator)

```
margin: 80px 0 12px
border-top + border-bottom: 3px double var(--ink)
background: --paper-warm
grid: auto 1fr auto
```

Left: "Below the fold" kicker + "Technical" in Oswald 700 `clamp(40px, 5vw, 64px)` + italic deck.

Right: Permanent Marker stamp, blood border `3px solid`, `-3deg` rotation — "For your SE".

### 9. Stack table (`.integ-table`)

Full-width table. Columns: Layer · Tool · Fit · Evidence.

Fit values and colors:
- `SUPPORTED / INTEGRATED`: `--army`
- `CUSTOM / PARTIAL`: `--blood`
- `UNCONFIRMED`: `--ink-faint`

### 10. Plays grid (V2 run-when/audible on cream)

Two-column grid. P1 spans full width.

**Play card (`.play`):**
- Border: `1px solid var(--rule)`, background: `--paper-card`
- P1: border `1px solid var(--blood)`, slightly warmer card background
- Play number badge: Oswald 700, 20px, blood — `border: 1.5px solid var(--blood)`, `padding: 3px 8px`
- P1 badge: `background: var(--blood)`, `color: var(--paper)`
- Title: Oswald 600, 17px (P1: 23px), uppercase
- Category: JetBrains Mono, 9px, ink-faint
- Finding: Merriweather italic, 15px, ink-soft
- Intel bullets: JetBrains Mono ▮ markers in blood; source line in ink-faint

**Run-when / audible-if footer (`.play-foot`) — V2 signature:**
```
border-top: 1px solid var(--rule-soft)
font-family: --font-mono; font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase
```
- `▸ RUN WHEN` label in ink-faint + run condition in army
- `↺ AUDIBLE` label in ink-faint + audible condition in blood, `margin-left: auto`

**Hand note (`.play-hand`):** Permanent Marker, 13px, blood — `position: absolute; bottom: 8px; right: 12px`, `-2deg` rotation.

### 11. Risk flags

```css
.risk {
  border-left: 3px solid var(--blood);
  background: var(--blood-soft);
  display: grid;
  grid-template-columns: 90px 1fr;
}
.risk.amber { border-left-color: var(--army); background: var(--army-soft); }
```

### 12. Closing (opener + discovery)

Separated from above by `3px double var(--ink)`.

**Opener script (`.opener-script`):**
- Background: `--paper-warm`, border: `1px solid var(--rule)`
- Quotes: Merriweather italic, 19px, ink
- Beats: Merriweather italic, ink-dim
- Stage direction: JetBrains Mono, 9.5px, ink-faint
- Hand note: Permanent Marker, 19px, blood, `-1deg`

**Discovery (`.discovery`):** Two-column grid. `Q1, Q2…` counter in JetBrains Mono, blood. Questions in Merriweather, 16px, ink-soft.

### 13. Sources panel

Three-column grid. Tier dot + source name + count (right-aligned). Quiet sources labeled `— quiet`.

### 14. Link safety panel (`.safety`)

`border: 1px solid var(--army)`, `background: var(--army-soft)`, army text. Army ▮ check mark. Clean verdict: "No flagged domains."

### 15. Colophon

`border-top: 1px solid var(--rule)`. Merriweather italic, 14px, ink-dim. Brand mark in Oswald 600 with trailing blood square.

---

## Hard rules — do not break

1. **No rounded corners.** `border-radius: 0` reset is global.
2. **No drop shadows on content.** `box-shadow: none !important` reset is global.
3. **One filled oxblood element** per major block. The brand square in the masthead. Play P1 badge. Everywhere else, `--blood` is text or border only.
4. **Army is accent-only.** Callouts, run-when labels, scan badge, callout borders. Never a large fill.
5. **Four fonts only.** Oswald + Merriweather + JetBrains Mono + Permanent Marker.
6. **No dark backgrounds.** `color-scheme: light`. Do not override.
7. **Lead item always gets a deck.** One italic sentence. Never omit on the lead.
8. **Run-when / audible on every play.** No play card without both fields.
9. **Permanent Marker is sparingly used.** Stamp, hand note, margin note, scouting hand. Not for section labels or body text.
10. **The countdown is live.** The JavaScript updates every 30 seconds while the artifact is open.

---

## What the agent never does

The agent writes only the `<script id="approach-data">window.APPROACH_DATA = …;</script>` block.

All CSS, layout, renderer, countdown logic, scroll spy, and any future PDF builder live in `approach-template.html`. The agent must not reconstruct, modify, or approximate any of this per-run.

---

## Version history

| Version | Change |
|---|---|
| 0.1.0 | Initial release — V1 cream paper base + V2 stamp/countdown/scouting summary/play-foot quirks |
