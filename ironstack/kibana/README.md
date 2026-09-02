# kibana/

`dashboards.ndjson` (coming with the first release) holds the exported saved objects for the three Ironstack dashboards:

1. **Overview** — program progress, tonnage and top-set trends, RPE distribution, time-of-day comparison, watch items.
2. **Session Drill-down** — click any session on the Overview: map, weather, full set tables, RPE by set, all notes in order.
3. **Mindset** — every note searchable (full-text, plus semantic where ELSER is enabled), tag trends, phase breakdown.

Import via Kibana → Stack Management → Saved Objects → Import. The dashboards are built against the `workout-sessions`, `workout-sets`, and `workout-notes` indices created by `ingest/setup_indices.py`.
