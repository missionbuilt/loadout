#!/usr/bin/env python3
"""
inject.py — local renderer for Floodlight. No network, no MCP server.

Fills two placeholders in the bundled template:
  __FLOODLIGHT_CATALOG__  <- the static, version-stamped framework catalog
  __FLOODLIGHT_DATA__     <- the per-run company data the agent assembles

Steps:
  1. Validate both inputs are well-formed JSON.
  2. Escape </script> so content cannot break out of the data/catalog blocks.
  3. Replace each placeholder literally (Python str.replace — no $-expansion,
     so $&, $', $` and backslashes in the data are safe by construction).
  4. Write the complete, self-contained floodlight-posture.html.

Usage:
  python3 inject.py <floodlight-data.json> <floodlight-catalog.json> <template.html> <output.html>

Exit codes: 0 = success, 1 = bad arguments, 2 = invalid JSON,
            3 = a placeholder is missing from the template.
"""
import json
import re
import sys
from pathlib import Path

P_DATA = "__FLOODLIGHT_DATA__"
P_CAT = "__FLOODLIGHT_CATALOG__"


def _load_json(path: Path, label: str):
    raw = path.read_text(encoding="utf-8")
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[inject] ERROR: {label} is not valid JSON — {e}. "
              f"Fix it and retry.", file=sys.stderr)
        sys.exit(2)
    # Safety: prevent </script> in content from terminating the block.
    return re.sub(r"</script>", r"<\\/script>", raw, flags=re.IGNORECASE)


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__.strip(), file=sys.stderr)
        return 1

    data_path, cat_path, template_path, out_path = map(Path, sys.argv[1:5])

    safe_data = _load_json(data_path, "Floodlight data")
    safe_cat = _load_json(cat_path, "Floodlight catalog")

    template = template_path.read_text(encoding="utf-8")
    for ph in (P_CAT, P_DATA):
        if ph not in template:
            print(f"[inject] ERROR: placeholder {ph} not found in template. "
                  f"Wrong or modified template file.", file=sys.stderr)
            return 3

    # Literal replacement — no regex/replacer $-expansion pitfalls.
    filled = template.replace(P_CAT, safe_cat, 1).replace(P_DATA, safe_data, 1)

    out_path.write_text(filled, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"[inject] OK — wrote {out_path} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
