/**
 * The Loadout — Full Test Suite Runner
 *
 * Runs all skill compliance tests and exits with a non-zero code on failure.
 * Used for CI and post-deploy verification.
 *
 * Usage:
 *   cd tests && node run-all.mjs
 *
 * MIT License — https://github.com/missionbuilt/loadout
 */

import { summarize } from "./harness.mjs";

console.log("The Loadout — Agent Compliance Tests");
console.log("Model:", process.env.LOADOUT_TEST_MODEL ?? "claude-haiku-4-5-20251001");
console.log("======================================");

// Import each test file. They run their suites on import and export allResults.
const { allResults: spotterReview } = await import("./spotter-review.test.mjs");
const { allResults: spotterBuild  } = await import("./spotter-build.test.mjs");
const { allResults: warmup        } = await import("./warmup.test.mjs");

const combined = [...spotterReview, ...spotterBuild, ...warmup];
process.exit(summarize(combined));
