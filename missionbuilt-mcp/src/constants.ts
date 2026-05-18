/**
 * Single source of truth for all version constants.
 *
 * Bump rules:
 *   SERVER_VERSION        — Worker deploy version (semver)
 *   WARMUP_VERSION        — Warmup skill version; bump when SKILL.md changes
 *   WARMUP_ENGINE_VERSION — skeleton structure marker; bump when the HTML skeleton
 *                           layout changes (not when warmup-shell.rawjs changes —
 *                           the remote shell is fetched by the browser automatically).
 *                           Agents use it to decide Path A (data edit only) vs Path B.
 *   SPOTTER_VERSION       — Spotter skill version; bump when SKILL.md or areas change
 *   THE_APPROACH_VERSION  — The Approach skill version; bump when SKILL.md or template changes
 */

export const SERVER_VERSION        = "1.0.39";
export const WARMUP_VERSION        = "0.5.0";
export const WARMUP_ENGINE_VERSION = "v0.5.0";
export const SPOTTER_VERSION       = "0.7.17";
export const THE_APPROACH_VERSION  = "0.1.4";

/** Total number of registered MCP tools. Update when adding/removing tools. */
export const TOOL_COUNT = 20;
