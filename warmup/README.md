# The Warmup — Self-Contained Edition (v0.9.4)

A daily intelligence brief for the first coffee. This is the fully local
edition of The Warmup: no MCP server, no KV store, no network dependency
beyond the web research itself. The output works offline — fonts embedded.

## What changed from the MCP edition (v0.8)

The MCP server did five jobs for this skill. All five are now local:

1. **Skill delivery** (`warmup_run` / `warmup_get_skill` section gating).
   The SKILL.md loads directly. The heavy reference content (source suites,
   report section structures, custom-mode rules) moved to `references/` and
   is read on demand — same token efficiency, no round trips.
2. **Template delivery** (`warmup_get_template`, 900-line chunks, sentinel
   stitching, engine version checks). The fully assembled engine ships as
   `warmup-template.html` in this folder. Chunking existed only because the
   template traveled through MCP responses; a local file has no such limit.
3. **Data persistence** (`warmup_save_data` / `warmup_get_data` via
   Cloudflare KV, fetched by the artifact at boot). Replaced by build-time
   injection via `scripts/inject.py` — the same pattern the shell's own
   Export function already used for offline files. Each run rebuilds
   `warmup.html` from template + `warmup-data.json`. Corrections edit the
   JSON and re-inject; no new searches.
4. **Auto-refresh** (visibilitychange polling against KV). Dormant by design
   (the data tool is empty). The masthead Refresh button now reloads the
   page from disk, which picks up the latest run.
5. **Font delivery** (`warmup_get_fonts`). The full font set (Oswald,
   Merriweather, JetBrains Mono, Permanent Marker) is baked into the
   template as data-URI @font-face rules. The brief renders identically
   offline, on locked-down networks, everywhere.

Four small shell edits were made (fonts-present check ordering, stale-cache
guard so old localStorage never overrides injected data, empty-state copy,
Refresh button behavior). Everything else — renderer, deep dives, section
done-toggles, export, print/PDF, configure modal — is byte-identical to the
v0.8 engine.

## Install

Claude Code / Cowork:

    cp -r the-warmup .claude/skills/

Claude.ai: upload this folder as a user skill.

## Run

First time: say "set up my warmup" — the skill walks the SETUP flow and
writes WARMUP.md. Daily: say "run my warmup". The brief lands in
warmup.html; open it in any browser.

**Deep Dive** (an on-demand AI expansion of any item) needs a live AI bridge,
so it only appears when the brief is opened as a Cowork artifact. Opened as a
plain file the brief is fully readable — the Deep Dive buttons simply stay
hidden rather than showing a dead control.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The skill — setup, run, configure, schema, rules |
| `warmup-template.html` | Full render engine with fonts baked in (placeholders: `__WARMUP_DATA__`, `__WARMUP_SAVED_AT__`) |
| `scripts/inject.py` | Local render step (replaces save/get KV flow) |
| `references/sources.md` | CISO / Product Leader / sector source suites |
| `references/sections.md` | Report section structures + batch query tables |
| `references/custom-mode.md` | Custom mode rules + source trust framework |
| `WARMUP.example.md` | User config example |
| `SKILL-DESIGN.md` | Design spec (for template maintenance only) |

MIT. Part of The Loadout · missionbuilt.io
