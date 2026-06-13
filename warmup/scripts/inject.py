#!/usr/bin/env python3
"""
inject.py — local render step for The Warmup (self-contained edition).

Replaces the entire v0.8 server pipeline (warmup_save_data -> KV ->
warmup_get_data fetch at artifact boot) with build-time data injection,
the same pattern the shell's own Export function uses for offline files:

  1. Validates WARMUP_DATA is well-formed JSON.
  2. Escapes </script> sequences (XSS / breakage safety).
  3. Replaces __WARMUP_DATA__ in the bundled template (literal replace —
     Python str.replace has no $-expansion semantics, so $&, $', $` and
     backslashes in content are safe by construction).
  4. Stamps __WARMUP_SAVED_AT__ with the current UTC ISO timestamp so the
     masthead "generated at" clock renders accurately in the viewer's
     timezone (same priority-1 path the KV savedAt used to feed).
  5. Writes the complete warmup.html. Fonts are already baked into the
     template — the output works fully offline.

Usage:
  python3 inject.py <warmup-data.json> <warmup-template.html> <warmup.html>

Exit codes: 0 = success, 1 = bad arguments, 2 = invalid JSON,
            3 = placeholder missing in template.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_PLACEHOLDER = "__WARMUP_DATA__"
SAVED_AT_PLACEHOLDER = "__WARMUP_SAVED_AT__"


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__.strip(), file=sys.stderr)
        return 1

    data_path, template_path, out_path = map(Path, sys.argv[1:4])

    raw = data_path.read_text(encoding="utf-8")
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[inject] ERROR: warmup data is not valid JSON — {e}. "
              f"Fix the WARMUP_DATA object and retry.", file=sys.stderr)
        return 2

    safe = re.sub(r"</script>", r"<\\/script>", raw, flags=re.IGNORECASE)

    template = template_path.read_text(encoding="utf-8")
    if DATA_PLACEHOLDER not in template or SAVED_AT_PLACEHOLDER not in template:
        print(f"[inject] ERROR: placeholder(s) missing in template. "
              f"Wrong or modified template file.", file=sys.stderr)
        return 3

    saved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    filled = template.replace(DATA_PLACEHOLDER, safe, 1)
    filled = filled.replace(SAVED_AT_PLACEHOLDER, saved_at, 1)

    out_path.write_text(filled, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"[inject] OK — wrote {out_path} ({size_kb:.0f} KB, savedAt {saved_at})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
