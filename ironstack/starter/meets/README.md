# meets/

One file per competition, named by date (`2024-11-16.json`), validated against `schema/meet.schema.json`.

Kilograms are the source of truth; `ingest/index_meets.py` derives pounds and marks the best made attempt per lift. The two files here are real, already-public meet results that seed the Meets dashboard and the meet-max reference line on Overview. Replace them with your own.
