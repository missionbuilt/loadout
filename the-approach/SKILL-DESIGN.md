# The Approach — Artifact Design Spec (C1 Editorial · v0.3.1)

The output is a single-file HTML artifact — a scrolling page, not tabbed, not
paginated. The current template is the **C1 editorial design**: cream-paper
newsprint, a three-font type system, a full MEDDPICC scorecard, an act divider
between the AE and SE halves, and an editorial section rhythm (TL;DR → prose →
action footer).

Follow these specifications exactly. Do not approximate colors or substitute
fonts. The visual identity is the trust signal.

> This spec is for **template maintenance only**. A normal run never reads it —
> every brief is rendered by injecting `APPROACH_DATA` into the bundled
> `approach-template.html`, which already embeds every token below.

---

## Design lineage

The Approach shares the Iron Log design language with The Warmup but does a
different job: the Warmup is a morning read, The Approach is a pre-call field
brief. The C1 redesign (skill v0.2.1) retired the earlier V1/V2 "Scout Sheet"
treatment — the rotated stamp, the live countdown pill, the Permanent Marker
hand annotations, and the run-when/audible play cards are **gone**. C1 is calmer
and more editorial: it reads like the front section of a newspaper, not a coach's
clipboard.

The agent writes only `window.APPROACH_DATA`. All CSS, layout, renderer logic,
scroll spy, and toolbar/export live in `approach-template.html` and must not be
reconstructed or modified per run.

---

## Build contract

The template contains one placeholder, `__APPROACH_DATA__`, on this line:

```html
<script id="approach-data">
  window.APPROACH_DATA = __APPROACH_DATA__;
</script>
```

`scripts/inject.py` validates the assembled `APPROACH_DATA` JSON, escapes any
`</script>` inside it, and replaces the placeholder literally to produce
`approach-brief.html`. The export button re-serializes `window.APPROACH_DATA`
back into this same block so a saved copy stays self-contained. There is no MCP
bridge and no `config.fontToolName`.

---

## Color tokens

All tokens live in `:root`. The agent never touches CSS.

```css
:root {
  color-scheme: light;

  /* Paper surfaces */
  --paper:        #f3ecdc;   /* Page background — cream newsprint */
  --paper-warm:   #ebe2cf;   /* Opener box, warm panels */
  --paper-card:   #ede5d2;   /* TL;DR card, person/cell cards */
  --paper-soft:   #efe8d6;   /* Soft panels */

  /* Ink */
  --ink:          #1a1612;   /* Primary text, act-divider rules, TL;DR border */
  --ink-soft:     #3a342d;   /* Body summaries, lead body text */
  --ink-dim:      #3d332a;   /* Metadata, source names */
  --ink-faint:    #52473a;   /* Captions, quiet states, unknown pips */

  /* Rules */
  --rule:         #c8bea7;   /* Borders, dividers, facts strip */
  --rule-soft:    #d8cfb8;   /* Inner separators */

  /* Accents */
  --blood:        #8a2017;   /* Primary accent — headings, drop caps, pull-quote rule, MEDDPICC chips */
  --blood-bright: #a8281e;   /* Hover / emphasis */
  --army:         #5f6e26;   /* Secondary accent — action footer, scan badge, confirmed pips, regulatory dots */
  --army-soft:    #dfe3c4;   /* Action footer + AMBER risk backgrounds */

  /* Fonts */
  --font-display: 'Oswald', sans-serif;            /* Headlines, masthead, section titles */
  --font-serif:   'Merriweather', Georgia, serif;  /* Body text, decks, quotes */
  --font-mono:    'JetBrains Mono', 'Courier New', monospace;  /* Kickers, meta, labels, chips */
}
```

The MEDDPICC "partial" state uses a one-off half-fill `#946011` (amber) on the
ring pip — it is the only color outside the token set, and it exists only there.

---

## Fonts

**Three families, three jobs. No Permanent Marker — that was V2.** Loaded from
the Google Fonts CDN with a system fallback stack.

| Variable | Family | Job |
|---|---|---|
| `--font-display` | Oswald | Masthead title, section titles, headlines, MEDDPICC letters |
| `--font-serif` | Merriweather | Body text, decks, pull quotes, discovery questions |
| `--font-mono` | JetBrains Mono | Kickers, metadata, source names, chips, scan badge, table cells |

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
  line-height: 1.7;
}
a { color: var(--ink); text-decoration: none; }
a:hover { color: var(--blood); }
```

---

## Layout — top to bottom

### 1. Toolbar (`.toolbar-bar`)
Sticky control strip: configure / save / export buttons (`.tb-btn`, `.tb-export`,
`.tb-dropdown`, `.save`). Export re-serializes `window.APPROACH_DATA` into the
`#approach-data` block for a self-contained download. Not part of the printed brief.

### 2. Masthead
Background `--paper`, bottom border `3px double var(--ink)` (nameplate double
rule). Holds the brief title in Oswald with a trailing blood square (`.f-sq`),
the `meta.deck` in Merriweather italic, and the meta line (vol/issue · date ·
source count) in JetBrains Mono. No rotated stamp, no countdown pill.

### 3. MEDDPICC scorecard (`.meddpicc`, `.meddpicc-grid`)
The signature C1 element, rendered from `meddpicc.cells`. Eight lettered cells
(`.mp`) — letter, label, headline, evidence (`.ev`), and a `next` step. Each cell
carries a status chip (`.mp-chip`) in JetBrains Mono, blood. A summary ring
(`.ring`) of legend pips (`.leg .pip`) encodes status:

- `.confirmed` → filled `--army`
- `.partial`  → half-fill `#946011` (amber)
- `.unknown`  → transparent, `--ink-faint` border

A `.score` reads the confirmed/partial/unknown tally.

### 4. Sections (`.sec`)
Each section uses the eyebrow stack:
- `.sec-num` / `.kicker` — JetBrains Mono, blood, wide tracking
- `.sec-title` — Oswald 600, large clamp
- `.sec-subtitle` / `.sec-deck` — Merriweather italic, ink-soft

### 5. Prose item types (inside `.prose`)
| Item | Class | Treatment |
|---|---|---|
| Paragraph | `p` | Merriweather body; optional `.source` line with a tier `.dot` |
| Pull quote | `.pull` | `4px solid var(--blood)` left rule, Merriweather italic, `cite` line |
| Facts strip | `.facts` | top+bottom `1px solid var(--rule)`, mono `k`/`v` cells |
| Stack table | `.stack-table` | full-width mono table — layer · tool · status (`.gap`/`.unk`) · note |
| Opener | `.opener` | `--paper-warm` panel, italic script + mono stage `beats` |
| Questions | `.questions` | numbered discovery questions, optional status chip |

**Source tier dots (`.source .dot`):**
`company` = blood · `press` = ink · `social` = ink-faint · regulatory/third-party
(default, omit `tier`) = army.

### 6. TL;DR card (`.tldr`)
`--paper-card` background, `3px solid var(--ink)` left rule. One-card summary at
the top of a section.

### 7. Action footer (`.action`)
`--army-soft` background, `3px solid var(--army)` left rule. "What to do with
this" — action-specific to the company and contact. One per section that needs it.

### 8. Act divider (`.act-divider`)
Top+bottom `1px solid var(--ink)`, `80px` top margin. Renders automatically
before the first `"the SE"` section — the AE → SE handoff (`.for` = "For the SE").

### 9. Sources panel
Tier dot + source name + count. Quiet sources labeled accordingly.

### 10. Link safety panel (`.safety`)
`--army` border, `--army-soft` background, army check mark. Only verified domains
listed; clean state reads "No flagged domains."

### 11. Colophon (`.colophon`)
`3px double var(--ink)` top rule, centered, max-width 760px. Brand mark in Oswald
with a trailing blood square (`.f-sq`). Links to missionbuilt.io.

---

## Hard rules — do not break

1. **No rounded corners.** `border-radius: 0` reset is global.
2. **No drop shadows on content.** `box-shadow: none !important` is global.
3. **One filled oxblood element per major block.** Brand square in the masthead;
   otherwise `--blood` is text or border only.
4. **Army is accent-only.** Action footer, scan badge, confirmed pips, regulatory
   dots, AMBER risk backgrounds. Never a large fill elsewhere.
5. **Three fonts only.** Oswald + Merriweather + JetBrains Mono. No Permanent Marker.
6. **No dark backgrounds.** `color-scheme: light`. Do not override.
7. **Lead item always gets a deck.** One italic sentence; never omit on the lead.
8. **Risk flags are RED or AMBER only.** Never green.
9. **The MEDDPICC scorecard is required** and renders at the position defined by
   the template — do not relocate it per run.

---

## What the agent never does

The agent writes only the
`<script id="approach-data">window.APPROACH_DATA = …;</script>` block.

All CSS, layout, renderer, scroll spy, toolbar, and export logic live in
`approach-template.html`. The agent must not reconstruct, modify, or approximate
any of it per run.

---

## Version history

| Version | Change |
|---|---|
| 0.1.0 | V1 cream-paper base + V2 Scout Sheet quirks (stamp, countdown, play-foot, Permanent Marker). |
| 0.2.1 | C1 editorial redesign — three-font type scale, MEDDPICC scorecard, act divider, facts strip, pull quote, stack table, opener box, TL;DR card, action footer. |
| 0.3.1 | Spec rewritten to match the shipped C1 template and the self-contained build contract (`inject.py` + `__APPROACH_DATA__`). Removed stale V1/V2 (4-font / stamp / countdown / play-card) descriptions. |
