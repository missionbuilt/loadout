# Warmup Config
# Copy this file to WARMUP.md and fill in your details.
# WARMUP.md is gitignored and never leaves your machine.

## Profile
mode: ciso                  # ciso | product_leader | custom
company: Your Company
sector: Your Sector
region: your-region         # e.g. united-states, european-union, apac
vendors:                    # CISO: vendor stack to track; Product Leader: competitor list
special_interests:          # optional: personal topics (e.g. Formula 1, NBA)
name: Your Name             # optional: enables personal greeting in the brief
showQuote: true             # true | false
updated:                    # set automatically at SETUP
last_run:                   # set automatically after each successful run
window_override:            # optional: fixed lookback in days (e.g. 14); leave blank for adaptive
daily_mode: false           # set to true if you run the brief every day; enables 2-day lookback fast-path
source_check_days: 30       # days between source emergence checks (default: 30)

# Product Leader fields (leave blank if mode is ciso or custom)
product_area:               # e.g. "security platform", "creator tools", "developer SDK"
build_type:                 # b2b | b2c | platform | marketplace | hybrid
vertical:                   # e.g. security | fintech | healthcare | developer_tools | ecommerce
competitors:                # comma-separated list; auto-generated at SETUP, editable anytime
ai_vendors:                 # comma-separated AI vendors/tools relevant to your roadmap
track_people:               # optional: exec, analyst, investor, or journalist names to watch

## Active Sources
# Add your sources here. Claude builds this list during SETUP.
# Format: - Name | URL | active
# "quiet" is a runtime state computed per-run, not written here.
# To exclude a source, move it to ## Excluded Sources with: - Name | URL | excluded

### Tier 1 — Authoritative
# (Claude populates this at SETUP based on your mode and sector)

### Tier 2 — Research
# (Claude populates this at SETUP based on your mode and sector)

### Tier 3 — News
# (Claude populates this at SETUP based on your mode and sector)

### Tier 4 — Vendor & Market Intel
# (Claude populates this at SETUP based on your mode and sector)

## Excluded Sources
(none)

## Notes
(none)
