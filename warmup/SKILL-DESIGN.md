# Warmup — Artifact Design Spec (v0.3.0 · Morning Edition)

The output is a single-file HTML artifact — a scrolling page, not tabbed, not
paginated. Think a morning newspaper. The v0.3.0 template is a cream-paper light
variant of the Iron Log system.

Follow these specifications exactly. Do not approximate colors or substitute
fonts. The visual identity is the trust signal.

---

## Color tokens

The template defines all tokens in `:root`. Do not override them per-report.
The agent only writes `WARMUP_DATA` — it never touches CSS.

```css
:root {
  color-scheme: light;

  /* Paper surfaces */
  --paper:        #f3ecdc;   /* Page background */
  --paper-warm:   #ebe2cf;   /* Signal bar background */
  --paper-card:   #ede5d2;   /* Pill / button backgrounds */
  --paper-soft:   #efe8d6;   /* Deep-dive panel background */

  /* Ink */
  --ink:          #1a1612;   /* Primary text */
  --ink-soft:     #3a342d;   /* Body summaries */
  --ink-dim:      #6a5f50;   /* Metadata, source names */
  --ink-faint:    #968974;   /* Captions, off states */

  /* Rules */
  --rule:         #c8bea7;   /* Borders, dividers */
  --rule-soft:    #d8cfb8;   /* Inner item separators */

  /* Accents */
  --blood:        #8a2017;   /* THE one fill accent. Deepened from #a8211a for paper. */
  --blood-bright: #a8281e;   /* Tag fill on dark-on-light variants */
  --blood-soft:   #f0d8d4;   /* Selection / alert tag background */
  --army:         #5f6e26;   /* Micro-accent: CVE tags, scan badge */
  --army-soft:    #dfe3c4;   /* CVE tag fill */
}
```

Legacy aliases (maintained for renderer compatibility — map to new tokens):
```css
  --color-bg:          var(--paper);
  --color-panel:       var(--paper-card);
  --color-chalk:       var(--ink);
  --color-chalk-dim:   var(--ink-soft);
  --color-chalk-faint: var(--ink-dim);
  --color-steel:       var(--ink-faint);
  --color-blood:       var(--blood);
  --color-blood-dim:   var(--blood-soft);
  --color-army:        var(--army);
```

> **v0.3.0 from v0.2.x:** Charcoal → cream paper. Oxblood deepened from `#c8281e`
> to `#8a2017`. Army darkened from `#92a844` to `#5f6e26`. `color-scheme: light`.
> Full `--paper-*` and `--ink-*` token families replace `--color-bg` / `--color-chalk`.

---

## Fonts

Three families, three jobs, no exceptions.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Merriweather:ital,wght@0,300;0,400;0,700;1,400&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
```

| Variable | Family | Job |
|---|---|---|
| `--font-display` | Oswald | Title, section headlines, item headlines |
| `--font-serif` | Merriweather | Body summaries, italic decks, quotes |
| `--font-mono` | JetBrains Mono | Kickers, dates, source names, pills, metadata |

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
  font-size: 18px;
  line-height: 1.6;
}
a { color: var(--ink); text-decoration: none; }
a:hover { color: var(--blood); }
::selection { background: rgba(138,32,23,0.18); color: var(--ink); }
:focus-visible { outline: 2px solid var(--blood); outline-offset: 2px; }
```

---

## Layout — top to bottom

### 1. Masthead

Background: `--paper`. Bottom border: `3px double var(--ink)` (nameplate double rule).
Padding: `clamp(28px,4vw,48px) clamp(22px,4vw,64px) 28px`.

Top row (controls bar): Configure + Save PDF buttons, right-aligned above the nameplate.

Title block:
- Date row: JetBrains Mono 400, 12px, `--ink-dim`, uppercase. Format: `"Thursday · 15 May 2026"`. Scan time right of date (`--ink-dim`), Company · Mode identifier right-aligned (`--ink-dim`).
- **THE WARMUP** in Oswald 700, fluid: `clamp(56px, 10vw, 132px)`. Color: `--ink`. Inline brand square: 7px solid `--blood`, `vertical-align: middle`, `margin-left: 8px`.
- Pills row: Mode / Sector / Company buttons (`border: 1px solid var(--army)`, text `--army`). Scan badge right-aligned (`--army` text + underline).

Right rail (masthead-right): italic greeting + daily quote, right-aligned, `--ink-dim`.

### 2. Signal bar

Background: `--paper-warm`. Top and bottom: `1px solid var(--rule)`.
Padding: `14px clamp(22px,4vw,56px)`.

Five stat cells divided by `1px solid var(--rule)`: Items today / Sections / Sources active / Quiet today / Generated.

Label: JetBrains Mono 400, 11px, `letter-spacing: 0.2em`, `--ink-dim`, uppercase.
Value: Oswald 600, 22px, `--ink`. Generated cell: Merriweather italic 400, 18px, `--ink`.

### 3. Section nav

Sticky at top. Background: `--paper`. Bottom: `1px solid var(--rule)`.
Nav items: JetBrains Mono 500, 13px, `--ink-dim`, uppercase.
Active: `--ink` with `2px solid var(--blood)` bottom border.
Done: `--ink-faint`, opacity 0.6, ` ✓` suffix in `--army`.

### 4. Body — sections

Max-width: `1400px`. Padding: `0 clamp(22px,4vw,56px) 56px`. Section `padding-top: 56px`.

#### Section eyebrow (v0.3.0)

The renderer builds this from `sections[].id`, `.label`, `.sub`:

```html
<h2 class="s-eyebrow">
  <span class="sec-kicker">Section One</span>
  <span class="sec-label">Threat Landscape</span>
  <span class="sec-sub">Active campaigns and fresh exploitation…</span>
</h2>
```

- `sec-kicker`: JetBrains Mono 700, 10px, `letter-spacing: 0.28em`, `--blood`, uppercase. CSS-drawn horizontal lines before and after via `::before`/`::after`.
- `sec-label`: Oswald 700, 28px, `--ink`.
- `sec-sub`: Merriweather italic 400, 16px, `--ink-dim`. Populated from the `sub` field in WARMUP_DATA — always present, never null.

Thin rule after eyebrow: `1px solid var(--rule)`.

#### Editorial lead item — `items[0]`, class `.item-lead`

Full-width. Choose `items[0]` deliberately — the most important item in the section.

- Meta row: trust dot + source name + date badge + tags (same as grid items)
- Headline: Oswald 600, `clamp(28px, 3.5vw, 38px)`, `--ink`, links to article URL
- `deck` (optional but expected): Merriweather italic 400, 18px, `--ink-soft`. One sentence of "so what?" framing between headline and body.
- Body: Merriweather 400, 18px, `--ink-soft`. **Drop-cap on first letter**: Oswald 700, `3.6em`, `--blood`, floated left, 4px right margin.
- Bottom border: `1px solid var(--rule)`. Padding-bottom: 28px.

#### Grid items — `items[1..N]`, wrapped in `.items-grid`

Two-column grid (`grid-template-columns: 1fr 1fr`). Date-sorted descending. No `deck`.

- Headline: Oswald 600, 21px, `--ink`
- Body: Merriweather 400, 15.5px, `--ink-soft`
- Each item: padding-bottom 24px

#### Shared item meta row

Above the headline on every item (lead and grid):

- **Trust dot**: `● ◉ ○ ◈` — Tier 1 `--blood`, Tier 2/3 `--ink-dim`, Tier 4 `--army`
- **Source name**: JetBrains Mono 500, 12px, `letter-spacing: 0.14em`, `--ink-dim`, uppercase
- **Date badge**: calendar date in JetBrains Mono `--ink-dim`; relative label (TODAY / 2 DAYS AGO) in `--army` on `rgba(95,110,38,0.12)` background, JetBrains Mono 500, 11px
- **Tags** (optional): pills per type
  - CVE: background `--army-soft`, text `--army`
  - Alert: background `--blood`, text white
  - MITRE: background `--blood-soft`, text `--blood`
  - Type (NEWS / VENDOR / REGULATORY / M&A / COMMUNITY): background `--paper-card`, border `1px solid var(--rule-soft)`, text `--ink-dim`
  - All pills: JetBrains Mono 700, 11px, `letter-spacing: 0.06em`, padding 2px 8px

#### Deep Dive

Per-item button: JetBrains Mono 700, 12px, `--ink-dim`, border `1px solid var(--rule-soft)`.
Result pane: `border-left: 2px solid var(--blood)`, background `--paper-soft`, Merriweather 400, 18px.

### 5. Sources panel

After all sections. ID `sources`, class `src-panel`.
Eyebrow follows sec-kicker / sec-label pattern.
Rows: name (`--ink`), domain (`--ink-dim`), count (`--ink`), status (ACTIVE `--army` / QUIET `--ink-faint`).
Quiet sources in a collapsible `<details>` block, opacity 0.55.

### 6. Link safety panel

After sources. Domain grid with verdict per domain.
Clean verdict: `--army`. Caution: amber. Flagged: `--blood`.

### 7. Footer

Padding: `28px clamp(22px,4vw,56px) 44px`. Top: `1px solid var(--rule)`.
JetBrains Mono 400, 12px, `letter-spacing: 0.16em`, `--ink-faint`, uppercase.

Format: `MISSION [■] BUILT · THE WARMUP · [date] · [mode]`

---

## PDF export

The "Save PDF" button calls `buildBriefPDF()` — a zero-dependency PDF/1.4 writer
embedded in the template. It walks the live DOM and produces selectable A4 text.
This is a typographic rendering, not a pixel capture. The agent never calls this
directly — it's triggered by the user from within the artifact.

### Core font mapping (PDF)

| Core font | Stands in for |
|---|---|
| Times-Roman | Merriweather (body summaries) |
| Helvetica-Bold | Oswald (headlines, masthead title) |
| Courier | JetBrains Mono (meta lines, source rows, kickers) |
| Times-Italic | Italic decks, taglines, greeting line |

### Morning Edition PDF layout (v0.3.0)

Page: A4 (595.28 × 841.89pt), margins 54pt left/right, 62pt top, 54pt bottom.

- Masthead: centered "THE WARMUP" in Helvetica-Bold 20pt; subheader line in sans 9pt (Company · Mode · Date · Time); greeting right-aligned in italic; 1.5pt horizontal rule below
- Section headings: 6×8pt oxblood accent square (`rgb(0.541, 0.125, 0.090)` = `#8a2017`) + Helvetica-Bold 9.5pt label; 0.5pt rule below
- Lead item: Helvetica-Bold 14pt headline, Courier 7.5pt meta, Times-Roman 9.5pt body
- Grid items: Helvetica-Bold 12.5pt headline, Courier 7.5pt meta, Times-Roman 9.5pt body; hairline separator between items
- Sources panel: Courier 7.5pt rows, four columns (name / domain / count / status)
- Running footer per page: brand mark + URL + page number
- Colophon appended after sources

### Two export modes

- **With Deep Dives** — includes any analysis panels the user expanded on screen
- **Articles Only** — sections and sources only, no deep-dive panels

Both modes include the Sources Used panel and the link safety report.

### `pdfTheme` config field

`pdfTheme` is **legacy from the old dark variant and ignored in v0.3.0**. The Morning Edition
is always light paper. Include it in WARMUP_DATA for backward compat if needed; it has no effect.

---

## Hard rules — do not break

1. **No rounded corners.** `border-radius: 0` reset is global.
2. **No drop shadows on content.** `box-shadow: none !important` reset is global.
3. **One filled oxblood element on screen.** The brand square in the masthead. Everywhere else `--blood` is text or border color only.
4. **Army green is accent-only.** Pills, CVE tags, dots, scan badge. Never a large fill.
5. **Three fonts only.** Oswald + Merriweather + JetBrains Mono.
6. **No dark backgrounds.** The template sets `color-scheme: light`. Do not override.
7. **Lead item always gets a `deck`.** One italic sentence. Never omit on `items[0]`.

---

## Responsive behavior

At viewport ≤ 768px:
- Horizontal padding drops via `clamp()`
- Two-column item grid collapses to single column
- Signal bar cells wrap naturally
- Masthead right rail (quote / greeting) hides below 720px

---

## What the agent never does

The agent writes only the `<script id="warmup-data">` block. All CSS, JS, layout,
PDF builder, modal code, and renderer logic live in the canonical template and
must not be modified per-report.
