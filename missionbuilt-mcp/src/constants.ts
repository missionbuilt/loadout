/**
 * Single source of truth for all version constants.
 *
 * Bump rules:
 *   SERVER_VERSION        — Worker deploy version (semver)
 *   WARMUP_VERSION        — Warmup skill version; bump when SKILL.md changes
 *   WARMUP_ENGINE_VERSION — warmup-template.html engine marker; bump when the
 *                           template's internal version comment changes (drives
 *                           the Path A / Path B decision in warmup_run)
 *   SPOTTER_VERSION       — Spotter skill version; bump when SKILL.md or areas change
 *   THE_APPROACH_VERSION  — The Approach skill version; bump when SKILL.md or template changes
 */

export const SERVER_VERSION        = "1.0.1";
export const WARMUP_VERSION        = "0.3.17";
export const WARMUP_ENGINE_VERSION = "v0.3.17";
export const SPOTTER_VERSION       = "0.6.0";
export const THE_APPROACH_VERSION  = "0.1.0";

/** Total number of registered MCP tools. Update when adding/removing tools. */
export const TOOL_COUNT = 20;
