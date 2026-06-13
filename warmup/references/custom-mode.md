# The Warmup — Custom Mode Rules & Source Trust Framework

Loaded on demand: read this file when the user runs Custom mode or asks about source trust tiers.

## Custom Mode — Source-Building Rules

When the user describes custom interests, map each interest to sources
using these rules. Be explicit about tier and rationale for each recommendation.

**Financial markets / equities:**
- Yahoo Finance (Tier 2), CNBC Markets (Tier 3), Reuters Markets (Tier 1 for
  primary data), Bloomberg (Tier 2 — note paywall). For individual stocks,
  search SEC EDGAR filings (Tier 1) alongside news.

**Company / competitor tracking:**
- Official company newsroom / IR pages (Tier 1 for that company's announcements).
- SEC EDGAR for public companies (Tier 1). Google News for aggregated coverage
  (Tier 3). LinkedIn company pages (Tier 3).
- Note: press releases from companies about themselves are Tier 4 (commercial
  interest context applies).

**Industry publications:**
- Identify the 2–3 most authoritative publications for that domain. Examples:
  - AI/ML: Hugging Face blog, Arxiv cs.AI recent papers, MIT Technology Review
  - Product Management: Lenny's Newsletter, Reforge blog
  - Enterprise Tech: Stratechery (Tier 2 — paywall), The Information (Tier 2 — paywall)
  - For paywalled sources, search for public excerpts and link to the source.

**Government / regulatory:**
- Official agency sources are Tier 1 (SEC, FDA, FTC, EU Commission, etc.).
- Think tanks (Brookings, RAND, CSIS) are Tier 2.
- News coverage of regulatory actions is Tier 3.

**Social media signals:**
- Flag all social sources as Tier 3. Include only if the user explicitly
  requests social signal.
- Recommend that the user define which platforms and communities matter to
  them: a security researcher's X feed is different from a startup founder's.

**Local / city news:**
- Local newspaper of record for the named city (Tier 2). AP/Reuters
  local coverage (Tier 1). Local business journals (Tier 2).

**In all cases:** present the recommended source list with tier and rationale
before saving. Do not assume approval — ask.

---

## Source Trust Framework

Every source in the brief carries a visible trust tier indicator.

| Tier | Label | Indicator | Color | Criteria |
|---|---|---|---|---|
| 1 | Authoritative | ● (filled circle) | oxblood (#a8211a) | Government agencies, official standards bodies, primary-source records. Content originates from or is authorized by the named institution. |
| 2 | Research | ◉ (circle-dot) | chalk (#ebe5d8) | Established research firms, major media with dedicated security or financial beats, peer-reviewed publications. Content is vetted, attributed, and editorially reviewed. |
| 3 | News / Community | ○ (open circle) | chalk-dim (#a8a094) | News outlets without specialized editorial review for the domain, community forums, social media, aggregators. May be accurate; independently verify before acting. |
| 4 | Vendor | ◈ (diamond) | army (#7a8b3a) | Content produced by vendors about their own products, market, or competitors. Accurate for product facts; read competitive claims with commercial interest context. |

This framework applies in both CISO and Custom modes. Every item in the
artifact carries its source's tier indicator. No exceptions.

---

