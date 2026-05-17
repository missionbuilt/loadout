# The Loadout — Agent Compliance Tests

Automated tests that verify the Loadout MCP server's instruction text produces **correct agent behavior** — right tool call sequence, no forbidden tools, clean workspace paths.

Tests run against the **real Anthropic API** with all MCP and file tools mocked locally. No deployed server, no OAuth, no Cloudflare account needed.

## What gets tested

| Suite | What it checks |
|---|---|
| Spotter Review · PATH B | `list_artifacts → spotter_get_skill → spotter_get_template → Write → create_artifact` |
| Spotter Review · PATH B (mismatch) | Engine version mismatch still triggers full template rewrite |
| Spotter Review · PATH A | Engine match uses `Edit → update_artifact`, never calls `spotter_get_template` |
| Spotter Build | Framework loaded before questions, no artifact created, handoff line in output |
| Warmup · PATH B | `list_artifacts → warmup_get_template → Write → create_artifact` |
| Warmup · PATH B (stale) | Stale engine triggers template reload, uses `update_artifact` |
| Warmup · PATH A | Engine match uses `Edit → update_artifact`, never calls `warmup_get_template` |

All suites also check: no `bash` calls, no web fetch calls, no banned strings in Write paths, no grades in chat before the artifact is registered.

## Setup

```bash
cd tests
npm install
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Running tests

```bash
# All tests
npm test

# Per skill
npm run test:spotter-review
npm run test:spotter-build
npm run test:warmup
```

## Options

```bash
# Use a different model (default: claude-haiku-4-5-20251001)
LOADOUT_TEST_MODEL=claude-sonnet-4-6 npm test

# Increase turn limit for complex scenarios (default: 30)
LOADOUT_TEST_MAX_TURNS=50 npm test
```

## How it works

Each test file:
1. Builds the instruction text from `instructions.mjs` (mirrors `index.ts`)
2. Sends it to the Anthropic API as a user message (simulating what the agent receives after calling a Loadout tool)
3. Mocks every subsequent tool call with responses from `mocks.mjs`
4. Asserts on the resulting tool call sequence using helpers from `harness.mjs`

```
run-all.mjs
├── spotter-review.test.mjs  ← PATH A + PATH B + mismatch
├── spotter-build.test.mjs   ← build mode conversation flow
└── warmup.test.mjs          ← PATH A + PATH B + stale engine

harness.mjs       ← Anthropic API loop, TestRun class, assertions
mocks.mjs         ← mock tool responses and scenario builders
instructions.mjs  ← instruction templates (keep in sync with index.ts)
```

## Keeping instructions in sync

`instructions.mjs` mirrors the instruction text in `index.ts`. When you update `index.ts`, update the matching function in `instructions.mjs` and bump the version constants at the top of that file.

If the version constants in `instructions.mjs` diverge from `constants.ts`, your tests are running against stale instructions and will not catch regressions introduced by the update.

## Adding a new test

1. Add a test case object `{ name, async fn() }` to the relevant test file
2. `fn` should call `runAgent(...)`, then return an `assert.*` result
3. Export the case in the suite array

```js
{
  name: "PATH B · calls my_new_tool before Write",
  async fn() {
    const r = await run(spotterReviewMocks());
    return assert.calledBefore(r, "my_new_tool", "Write");
  },
},
```

## Adding a new skill

1. Add instruction template to `instructions.mjs`
2. Add mock responses to `mocks.mjs`
3. Add tool schemas to `harness.mjs` SCHEMAS
4. Create `my-skill.test.mjs` following the existing patterns
5. Import and spread `allResults` in `run-all.mjs`

## License

MIT — https://github.com/missionbuilt/loadout
