#!/usr/bin/env python3
"""Unit tests for ingest/verify_index.py's clock handling. No Elasticsearch.

    python ingest/test_verify_index.py

verify_index compares documents the repo builds NOW against documents the indexer
built THEN, and several of those fields are functions of the date they were built on:
`computed_through` is literally the date, the drift window's cutoff moves with it,
`cadence_days` divides by a span ending today, and which week is "in-progress" changes
at midnight UTC.

Rebuilt against the runner's own clock, verifying on a different UTC day from the
indexing therefore reports the entire signals index as drifted - 275 rows of
"computed_through: '2026-09-06' locally, '2026-09-05' indexed", which says nothing
about whether any field is wrong. CI never sees it because both steps run seconds
apart. Anybody verifying an existing cluster by hand hits it immediately.

So the comparison is made against the date the cluster was actually indexed on, and
the clock difference is reported once, as itself. These cases are that decision.
"""

import contextlib
import io
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_index as vi

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        failures.append(label)


class fake_es:
    """A session whose _search returns the computed_through terms aggregation."""

    def __init__(self, stamps, ok=True):
        self.stamps, self.ok = stamps, ok

    def post(self, url, json=None, **kw):
        outer = self

        class resp:
            ok = outer.ok

            @staticmethod
            def json():
                return {"aggregations": {"stamps": {"buckets": [
                    {"key": s, "doc_count": 1} for s in outer.stamps]}}}
        return resp


def verdict(stamps, today, ok=True):
    """(the date rebuilt against, the failures noted, the messages noted)."""
    saved = (vi.ok, vi.bad, vi.warn)
    vi.ok, vi.bad, vi.warn = [], [], []
    try:
        # verify_index prints its own report as it goes; swallowed here so this file
        # reads as a test run rather than as a verification of a cluster that is not there.
        with contextlib.redirect_stdout(io.StringIO()):
            as_of = vi.as_of_date(fake_es(stamps, ok), "http://es", today)
        return as_of, list(vi.bad), list(vi.ok) + list(vi.bad)
    finally:
        vi.ok, vi.bad, vi.warn = saved


TODAY = date(2026, 9, 6)

print("Same day: nothing to say, and today is what is compared against")
as_of, bad, said = verdict(["2026-09-06"], TODAY)
check("rebuilt against today", as_of, TODAY)
check("and nothing fails", bad, [])
check("but the clock is still reported", len(said), 1)

print("\nA cluster indexed yesterday is stale, and says so once")
as_of, bad, said = verdict(["2026-09-05"], TODAY)
# The fix that matters: the comparison is made against the date the rows were built
# for, so what the rest of the run reports is field drift rather than clock drift.
check("rebuilt against the date the cluster was indexed on", as_of, date(2026, 9, 5))
check("exactly one failure is noted, not one per row", len(bad), 1)
check("and it names both dates",
      "2026-09-05" in bad[0] and "2026-09-06" in bad[0], True)
check("and says how old it is", "1 day(s) old" in bad[0], True)
check("and what to do about it", "index_workouts.py" in bad[0], True)
check("and that this is staleness rather than drift",
      "not field drift" in bad[0], True)

print("\nAn empty or unreadable signals index is its own message")
as_of, bad, _said = verdict([], TODAY)
check("falls back to today", as_of, TODAY)
check("and fails with a message about the index", len(bad), 1)
check("naming the index", vi.ix.derive.SIGNAL_INDEX in bad[0], True)
as_of, bad, _said = verdict(["2026-09-06"], TODAY, ok=False)
check("a query that fails is the same case", as_of, TODAY)
check("and is also a failure", len(bad), 1)

print("\nMore than one stamp live at once means a sweep did not finish")
as_of, bad, _said = verdict(["2026-09-06", "2026-09-04"], TODAY)
check("the newest is what the cluster is compared against", as_of, date(2026, 9, 6))
check("and the split is reported", len(bad), 1)
check("naming both stamps",
      "2026-09-06" in bad[0] and "2026-09-04" in bad[0], True)
check("and saying what it means",
      "sweep did not finish" in bad[0], True)

print("\ncluster_stamp reads the aggregation, newest first")
check("sorted newest first",
      vi.cluster_stamp(fake_es(["2026-09-04", "2026-09-06", "2026-09-05"]), "http://es"),
      ["2026-09-06", "2026-09-05", "2026-09-04"])
check("an unreadable index is no stamps at all",
      vi.cluster_stamp(fake_es(["2026-09-06"], ok=False), "http://es"), [])

print("\nmain() rebuilds against the cluster's date, not the runner's")

# as_of_date() can be right on its own and main() can still call
# datetime.now(timezone.utc).date() instead, which is exactly the line the bug was on.
# So the wiring is asserted rather than assumed: main() is run against a cluster
# stamped two days ago, with local_documents() replaced by a recorder.


class fake_requests:
    """Just enough of `requests` for main() to get through without a cluster."""

    def __init__(self, stamps):
        self.stamps = stamps

    def Session(self):
        outer = self

        class sess:
            headers = {}

            @staticmethod
            def update(*a, **k):
                pass

            def get(self, url, **kw):
                return fake_requests._resp(outer.stamps)

            def post(self, url, json=None, **kw):
                return fake_requests._resp(outer.stamps)
        s = sess()
        s.headers = dict()
        return s

    @staticmethod
    def _resp(stamps):
        class resp:
            ok = True
            status_code = 200
            text = ""

            @staticmethod
            def json():
                # The mapping key comes first on purpose: main() reads a _mapping
                # response as list(body.values())[0]["mappings"].
                return {
                    "an-index": {"mappings": {"properties": {}, "dynamic": "strict",
                                              "date_detection": False}},
                    "aggregations": {"stamps": {"buckets": [{"key": s} for s in stamps]},
                                     "bars": {"buckets": []}},
                    "count": 0,
                    "docs": [],
                    "hits": {"hits": []},
                }
        return resp()


def main_rebuilt_against(stamps, today):
    """The date main() handed to local_documents()."""
    seen = []
    saved = (vi.requests, vi.local_documents, vi.datetime, vi.ok, vi.bad, vi.warn)

    class frozen_datetime:
        @staticmethod
        def now(tz=None):
            class stamp:
                @staticmethod
                def date():
                    return today
            return stamp

    vi.requests = fake_requests(stamps)
    vi.datetime = frozen_datetime
    vi.local_documents = lambda as_of=None: (
        seen.append(as_of) or {"workout-sessions": {}, "workout-notes": {},
                               "workout-sets": {}})
    vi.ok, vi.bad, vi.warn = [], [], []
    import os
    env = {k: os.environ.get(k) for k in ("ES_ENDPOINT", "ES_API_KEY")}
    os.environ["ES_ENDPOINT"] = "https://example.invalid"
    os.environ["ES_API_KEY"] = "not-a-key"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            vi.main()
        return seen[0] if seen else None
    finally:
        (vi.requests, vi.local_documents, vi.datetime, vi.ok, vi.bad, vi.warn) = saved
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


check("a cluster indexed two days ago is what the repo is rebuilt against",
      main_rebuilt_against(["2026-09-04"], date(2026, 9, 6)), date(2026, 9, 4))
check("and on the same day it is simply today",
      main_rebuilt_against(["2026-09-06"], date(2026, 9, 6)), date(2026, 9, 6))
check("an unreadable stamp falls back to the runner's clock",
      main_rebuilt_against([], date(2026, 9, 6)), date(2026, 9, 6))

print()
if failures:
    print(f"{len(failures)} FAILED: " + ", ".join(failures))
    sys.exit(1)
print("all verify_index tests passed")
