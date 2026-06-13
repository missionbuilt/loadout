# The Approach — Self-Contained Edition (v0.3.1)

A pre-call intelligence brief for sellers and technical sellers. This is the
fully local edition of The Approach: no MCP server, no network dependency
beyond the web research itself.

## What changed from the MCP edition

The MCP server (mcp.missionbuilt.io) did three jobs for this skill. All three
are now local:

1. **Skill delivery** (`approach_run` / `approach_get_skill`). Moot — the
   SKILL.md loads directly from this folder.
2. **Template injection** (`approach_get_template`). Replaced by
   `scripts/inject.py`, which replicates both server-side safety layers:
   `</script>` escaping and literal (non-expanding) placeholder replacement.
   A manual file-tool fallback is documented in SKILL.md for environments
   without a shell.
3. **Font delivery** (`warmup_get_fonts`). The MCP font loader existed only
   because Cowork's CSP blocked font CDNs. This edition uses the Google Fonts
   CDN link in the template head, with system-font fallback when the CDN is
   unreachable. The brief is fully readable either way.

Nothing else changed. Research workflow, APPROACH_DATA schema (minus the now
unnecessary `config.fontToolName`), editorial rules, MEDDPICC scorecard,
renderer, and export are identical to the MCP edition at 0.2.4.

## Install

Claude Code / Cowork:

    cp -r the-approach .claude/skills/

Claude.ai: upload this folder as a user skill.

## Run

Say "run the approach for [company]" or "brief me on [company]". The skill
collects intake, researches, assembles APPROACH_DATA, and renders
`approach-brief.html` locally. Open the file in any browser.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The skill — intake, research, schema, render, rules |
| `approach-template.html` | C1 editorial template with `__APPROACH_DATA__` placeholder |
| `scripts/inject.py` | Local render step (replaces `approach_get_template`) |
| `APPROACH.example.md` | Seller config example |
| `SKILL-DESIGN.md` | C1 artifact design spec (template maintenance only) |
| `ARCH.md` | Architecture + data-flow diagram for the self-contained edition |

MIT. Part of The Loadout · missionbuilt.io
