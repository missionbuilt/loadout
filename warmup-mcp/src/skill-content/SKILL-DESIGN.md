# Warmup — Artifact Design Spec

The output is a single-file Iron Log-branded HTML artifact. It is a scrolling
page — not tabbed, not paginated. Think a morning newspaper, not a dashboard.

Follow these specifications exactly. Do not approximate colors or substitute
fonts. The visual identity is the trust signal.

## Artifact Design Spec — Iron Log

### Color tokens

Embed these as CSS custom properties in the artifact's `<style>` block.

```css
:root {
  color-scheme: dark;
  --color-bg:          #171513;
  --color-panel:       #1f1c19;
  --color-rule:        #2a2622;
  --color-rule-soft:   #2e2b27;
  --color-chalk:       #f0ead9;
  --color-chalk-dim:   #ccc5b5;
  --color-chalk-faint: #9e9688;
  --color-blood:       #c8281e;
  --color-blood-dim:   #5e1e1c;
  --color-army:        #92a844;
  --color-army-dim:    #4a5527;
  --color-steel:       #7a7873;
}
```

> **v0.2.0 change:** chalk tones lightened for WCAG AA compliance, blood and army
> raised for better contrast. `color-scheme: dark` added for browser-level dark mode.
> `--color-rule-soft` changed from `#221f1c` to `#2e2b27` (visible dashed rules).

### Fonts

Load from Google Fonts with `display=swap`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Merriweather:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

Apply as CSS variables:
```css
--font-display: 'Oswald', 'Archivo Narrow', Arial, sans-serif;
--font-serif:   'Merriweather', Georgia, serif;
--font-mono:    'JetBrains Mono', 'Courier New', monospace;
```

### Global reset

```css
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  border-radius: 0 !important;
  box-shadow: none !important;
}
body {
  background: var(--color-bg);
  color: var(--color-chalk);
  font-family: var(--font-serif);
  font-size: 18px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
a {
  color: var(--color-chalk);
  text-decoration: underline;
  text-underline-offset: 3px;
}
a:hover {
  color: var(--color-blood);
}
::selection {
  background: var(--color-blood-dim);
  color: var(--color-chalk);
}
:focus-visible {
  outline: 2px solid var(--color-blood);
  outline-offset: 2px;
}
```

### Layout — top to bottom

**1. Masthead**

Background: `--color-panel`. Bottom border: `1px solid var(--color-rule)`.
Padding: 22px 56px desktop, 22px 24px mobile.

Left side, stacked:
- Title row: "THE WARMUP" in Oswald 700, uppercase, `letter-spacing: 0.08em`,
  `--color-chalk`, immediately followed by a 7×7px inline square in
  `--color-blood` (the brand mark, styled as `display: inline-block;
  width: 7px; height: 7px; background: var(--color-blood); margin-left: 8px;
  vertical-align: middle;`).
- Subtitle row: JetBrains Mono 400, 11px, `letter-spacing: 0.2em`,
  `--color-chalk-faint` — the date formatted as "THU · 14 MAY 2026".
  Then one or two mode/profile pills (see Pills below).

Pills:
- Mode: "CISO" or "CUSTOM" — border `1px solid var(--color-army)`,
  color `--color-army`, background transparent.
- Sector: the user's sector (e.g., "HEALTHCARE") — same pill style.
- JetBrains Mono, 10px, `letter-spacing: 0.14em`, padding: 2px 8px.
- No filled pill backgrounds. Border and text only.

**2. Signal Bar**

`border-top: 1px solid var(--color-rule);`
`border-bottom: 1px solid var(--color-rule);`
Padding: 14px 56px desktop, 14px 24px mobile.
Background: none (transparent, shows `--color-bg`).

Four stat cells displayed inline:
- "SOURCES ACTIVE" / count
- "ITEMS" / count
- "SECTIONS" / count
- "GENERATED" / time (e.g., "07:14")

Each cell: label in JetBrains Mono 400, 10px, `letter-spacing: 0.2em`,
`--color-chalk-faint`, uppercase; value in Oswald 600, 20px, `--color-chalk`.
Cells separated by `1px solid var(--color-rule)` vertical rules.
Do not use a colored background on the signal bar.

**3. Body — Sections**

Padding: 0 56px desktop, 0 24px mobile. No max-width constraint on the
content column — let it breathe.

Each section follows this exact rhythm:

```
[section eyebrow]
[thin rule]
[items, separated by dashed rules]
[spacer before next section]
```

**Section eyebrow (v0.2.0 — three switchable variants via body class):**

The eyebrow style is controlled by a class on `<body>`. Three variants are supported:

- `body.eyb-bracketed` (default, recommended): `▮▮▮ LABEL ▮▮▮` — matches the
  missionbuilt.io website hero pattern. Bars in `--color-blood`, label in `--color-chalk`.
- `body.eyb-numbered`: `▮▮▮ 01 LABEL · N items` — editorial / run-sheet style with
  a section index and item count. Bars in `--color-blood`.
- `body.eyb-original`: Single `▮` prefix — the original single-square style.

The renderer injects this structure for every section:

```html
<h2 class="s-eyebrow">
  <span class="eb-bars eb-lead">▮▮▮</span>
  <span class="accent"></span>
  <span class="eb-num">01</span>
  <span class="eb-label">THREAT LANDSCAPE</span>
  <span class="eb-bars eb-tail">▮▮▮</span>
  <span class="eb-count">3 · items</span>
</h2>
```

The Tweaks panel (floating FAB) lets the user toggle variants, summary size, and
Merriweather weight live — persisted to `localStorage`. Ship with `eyb-bracketed` as default.

**Thin rule after eyebrow:**
`1px solid var(--color-rule)`. Margin-bottom: 22px.

**Each item:**
No card background. No border. No shadow.
Items are separated from each other by `1px dashed var(--color-rule-soft)`.
Padding: 18px 0.

Item structure, top to bottom:

a. Meta row — inline, small, above the headline:
   - Trust dot: `● ◉ ○ ◈` character, colored per tier
     (Tier 1: `--color-blood`; Tier 2/3: `--color-chalk-dim`;
     Tier 4: `--color-army`)
   - Source badge: JetBrains Mono 400, 10px, `letter-spacing: 0.14em`,
     `--color-chalk-faint`, uppercase. The source name.
   - Tags (optional, inline after source): pills for CVE IDs, MITRE IDs,
     content-type flags.
     - CVE tags: border `1px solid var(--color-army)`, text `--color-army`
     - MITRE tags: background `var(--color-blood-dim)`, text `--color-chalk-dim`
     - [NEWS] / [VENDOR] / [COMMUNITY] / [REGULATORY] / [M&A] / [EXEC] tags:
       border `1px solid var(--color-steel)`, text `--color-chalk-faint`
   - All pills: JetBrains Mono, 10px, padding: 1px 6px, no border-radius.

b. Headline:
   Oswald 500, 16px, `--color-chalk`. Wrapped in `<a>` linking to the
   source URL. No underline default; underline on hover.
   Line-height: 1.3.

c. Summary:
   Merriweather 400, 15px, `--color-chalk-dim`, `line-height: 1.55`.
   2–3 sentences. Margin-top: 6px.

**4. Source Transparency Panel**

After all sections. Always present. Never omit.

Eyebrow: `▮ SOURCES USED TODAY` — same style as section eyebrows.
Thin rule below eyebrow.

A simple list (not a `<table>` — lists are lighter and don't break on mobile):
One line per source:
- Trust dot + source name (JetBrains Mono 500, 12px, `--color-chalk`)
- Domain (JetBrains Mono 400, 11px, `--color-chalk-faint`)
- Item count contributed (JetBrains Mono 400, 11px, `--color-chalk-faint`)
- Status: "ACTIVE" in `--color-army` or "EXCLUDED" in `--color-chalk-faint`
  with strikethrough on the source name

Group by tier. Show a tier label above each group in JetBrains Mono 10px,
`--color-chalk-faint`, uppercase.

**5. Footer**

Minimal. One line. Padding: 36px 56px 48px.
`border-top: 1px solid var(--color-rule)`.

```html
MISSION <span style="display:inline-block;width:5px;height:5px;
background:var(--color-blood);vertical-align:middle;margin:0 2px;"></span>
BUILT · THE WARMUP · [ISO timestamp]
```

JetBrains Mono 400, 10px, `letter-spacing: 0.16em`, `--color-chalk-faint`.

### Responsive behavior

At viewport width ≤ 720px:
- Padding drops to 24px horizontal.
- Signal bar cells stack 2×2 or wrap naturally.
- Masthead subtitle and pills wrap to new lines as needed.

### Five rules that must not break

1. **No rounded corners.** The global reset applies `border-radius: 0 !important`
   to everything.
2. **No box shadows.** The global reset applies `box-shadow: none !important`.
3. **No pure white or pure black.** Use `--color-chalk` and `--color-bg` only.
4. **One filled oxblood element.** The `--color-blood` appears as a fill
   in exactly one place: the 7×7px brand square in the masthead.
   Everywhere else — section eyebrows, MITRE tags, focus rings — it is text
   color or border color, not a filled background.
5. **Army green never fills a large area.** Pills and dots only.
   Never a section background or a wide banner.
