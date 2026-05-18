/**
 * Single source of truth for all version constants.
 *
 * Bump rules:
 *   SERVER_VERSION        — Worker deploy version (semver)
 *   WARMUP_VERSION        — Warmup skill version; bump when SKILL.md changes
 *   WARMUP_ENGINE_VERSION — warmup-shell.rawjs engine marker; bump on any change
 *                           to the shell (CSS, HTML, JS). Agents use it to decide
 *                           Path A (data edit only) vs Path B (full template write).
 *   SPOTTER_VERSION       — Spotter skill version; bump when SKILL.md or areas change
 *   THE_APPROACH_VERSION  — The Approach skill version; bump when SKILL.md or template changes
 */

export const SERVER_VERSION        = "1.0.47";
export const WARMUP_VERSION        = "0.7.3";
export const WARMUP_ENGINE_VERSION = "v0.7.3";
export const SPOTTER_VERSION       = "0.7.17";
export const THE_APPROACH_VERSION  = "0.1.4";

/** Total number of registered MCP tools. Update when adding/removing tools. */
export const TOOL_COUNT = 20;
