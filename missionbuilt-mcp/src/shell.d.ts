/**
 * Type declarations for *.rawjs files imported as raw text strings.
 * Wrangler's Text rule (in wrangler.toml) handles the actual bundling.
 */
declare module '*.rawjs' {
  const content: string;
  export default content;
}
