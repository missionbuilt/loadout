/**
 * Type declarations for the files Wrangler's Text rule (see wrangler.toml) bundles
 * as raw strings at build time: the skill markdown and the artifact templates.
 *
 * Without these, `import WARMUP_SKILL_MD from "./skill-content/warmup/SKILL.md"`
 * is a TS2307 "cannot find module" and `npm run typecheck` can never go green —
 * which is what let an unrelated type error sit in index.ts unnoticed.
 */
declare module '*.md' {
  const content: string;
  export default content;
}

declare module '*.html' {
  const content: string;
  export default content;
}

declare module '*.css' {
  const content: string;
  export default content;
}
