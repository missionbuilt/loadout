#!/usr/bin/env python3
"""
inject.py — local replacement for the approach_get_template MCP tool.

Replicates the server-side render step of The Approach with no network
and no MCP server:

  1. Validates APPROACH_DATA is well-formed JSON.
  2. Escapes </script> sequences so intel text cannot break out of the
     data <script> block (XSS / breakage safety).
  3. Replaces the __APPROACH_DATA__ placeholder in the template.
     Python str.replace is literal, so $&, $', $` and backslashes in the
     data are safe by construction (no regex/replacer expansion pitfall).
  4. Writes the complete, self-contained approach-brief.html.

Usage:
  python3 inject.py <approach-data.json> <template.html> <output.html>

Exit codes: 0 = success, 1 = bad arguments, 2 = invalid JSON,
            3 = placeholder missing in template.
"""
import json
import re
import sys
from pathlib import Path

PLACEHOLDER = "__APPROACH_DATA__"


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__.strip(), file=sys.stderr)
        return 1

    data_path, template_path, out_path = map(Path, sys.argv[1:4])

    raw = data_path.read_text(encoding="utf-8")
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[inject] ERROR: approach data is not valid JSON — {e}. "
              f"Fix the APPROACH_DATA object and retry.", file=sys.stderr)
        return 2

    # Safety layer 1: prevent </script> in content from terminating the data block.
    safe = re.sub(r"</script>", r"<\\/script>", raw, flags=re.IGNORECASE)

    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        print(f"[inject] ERROR: placeholder {PLACEHOLDER} not found in template. "
              f"Wrong or modified template file.", file=sys.stderr)
        return 3

    # Safety layer 2: literal replacement — no $-expansion semantics in Python.
    filled = template.replace(PLACEHOLDER, safe, 1)

    out_path.write_text(filled, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"[inject] OK — wrote {out_path} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
