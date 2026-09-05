# Ironstack Coach — privileges

The coach reads. It never writes, never indexes, never deletes, and never touches an index
that is not yours. Give its API key exactly that and nothing more.

## The role descriptor

```json
{
  "ironstack-coach-read": {
    "cluster": [],
    "indices": [
      {
        "names": [
          "workout-sessions",
          "workout-sets",
          "workout-notes",
          "workout-meets",
          "workout-daily",
          "workout-weekly",
          "ironstack-signals"
        ],
        "privileges": ["read", "view_index_metadata"],
        "allow_restricted_indices": false
      }
    ]
  }
}
```

- `read` is what runs a query, ES|QL included.
- `view_index_metadata` is what lets the agent see which fields exist, so it can fall back
  when a semantic field is not there instead of erroring at the lifter.
- No cluster privileges. Nothing the coach does needs one.
- The seven indices are named literally rather than as `workout-*`. A wildcard would quietly
  pick up whatever else lands in the cluster later, and `ironstack-signals` would not match
  it anyway.
- No `write`, `create`, `index`, `delete`, `manage`, or `all`. If a tool ever appears to
  need one of those, the tool is wrong.

## Creating the key

```bash
curl -X POST "$ES_ENDPOINT/_security/api_key" \
  -H "Authorization: ApiKey $ES_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d @coach-key.json
```

where `coach-key.json` is:

```json
{
  "name": "ironstack-coach",
  "expiration": "365d",
  "role_descriptors": { "...": "the object above" }
}
```

Or in Kibana: Stack Management, API keys, Create API key, restrict privileges, paste the
role descriptor.

The response contains the key once. Put it where Agent Builder asks for it and nowhere
else. It does not belong in `dashboards.ndjson`, in this repo, or in a link. The dashboards
carry a URL to the coach and never a credential.

Set an expiration and rotate. A read-only key over a training log is not a catastrophe if
it leaks, but it is still your body's whole record: where you train, when, how you slept,
and what you were worried about that day.

## If the coach only needs part of it

The tools in [tools.md](tools.md) read all seven indices. If you build a narrower agent,
narrow the `names` list to match it. Removing an index the tools use produces a permission
error mid-answer, which reads to the lifter as the coach not knowing something.
