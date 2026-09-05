# The derived numbers, and their limits

Every number here is computed at index time by `ingest/metrics.py` and written by
`ingest/derive.py`. They are estimates with known edges. Say the edge out loud when you use
the number.

## `est_e1rm`, `e1rm_method`, `e1rm_confidence`

An estimated one-rep max, from Tuchscherer's RPE table where an RPE was logged
(`e1rm_method: "rpe"`) and from Epley where one was not (`e1rm_method: "epley"`).

`e1rm_confidence` is keyed off reps performed: `high` at 6 or fewer, `medium` at 7 to 9,
`low` at 10 to 12. Above 12 reps there is no estimate at all. An Epley estimate is never
better than `medium`, because no RPE means no information about proximity to failure.

**Exclude `low` from any best or personal record.** A ten-rep set at RPE 6 is an
extrapolation across nine reps of accumulating fatigue.

## `intensity_pct` and `intensity_ref`

The set's weight against that lift's best estimate *at the time*, taken from a trailing 90
days. `intensity_ref` says which reference was used:

- `recent` — a best inside the window.
- `all-time` — nothing in the window, so an older best was used. The percentage is against
  something they may be months detrained from.
- `self` — no history at all, so the set was measured against its own estimate. This is not
  relative intensity and must not be read as it.

Most `self` sets are accessories. Do not guess the share: compute it before leaning on the
field.

```esql
FROM workout-sets
| WHERE set_type == "working" AND intensity_ref IS NOT NULL
| STATS sets = COUNT(*) BY intensity_ref
| SORT sets DESC
```

## `inol` and `prilepin_zone`

Main-lift metrics. `inol` is only written on sets whose `exercise.category` is `main`.

INOL bands are **per exercise**, never per session total and never per week total:

| Scope | Band |
|---|---|
| Per session | 0.4 to 1 optimal, 1 to 2 loading, above 2 brutal, below 0.4 low |
| Per week | under 2 easy, 2 to 3 loading, 3 to 4 brutal, above 4 excessive |

`prilepin_zone` is the intensity band a set landed in (`0-69`, `70-79`, `80-89`, `90+`), and
`prilepin_reps` on the session and rollup documents counts reps in each.

## `projected_total_lb` and `dots`

Competition lifts only. A high-bar squat or a wide-grip bench shares a `lift_family` with
the competition version and does not transfer to the platform.

## `acwr`, `monotony`, `strain`

`acwr` is the 7-day load over the 28-day daily average. It is a trend flag, not a
prediction; the ratio has taken real methodological criticism. Treat a spike as a prompt to
look, never as a verdict.

The load unit is **tonnage**, not session RPE times duration, because duration is logged on
almost no session. `monotony` counts rest days as zeros, which is the point of the metric: a
week where every day looks the same scores high.

## `bodyweight_source`

`"carried"` means the figure was carried forward from the last known weigh-in, possibly
months earlier. Any DOTS built on it is approximate. Say so.

## `load_estimated`

True when the session's `load_au` was estimated rather than computed from a logged duration.
