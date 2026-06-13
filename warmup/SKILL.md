---
name: warmup
description: "The Warmup. A daily intelligence brief for the first coffee, in CISO, Product Leader, or Custom mode. Triggers: \"run my warmup\", \"warmup\", \"set up my warmup\", \"what's in the brief today\"."
license: MIT
author: H. Michael Nichols
version: 0.9.4
part_of: The Loadout
---

# The Warmup

## Full description

The Warmup. A daily intelligence brief for the first coffee. CISO mode delivers a structured cybersecurity digest — active threat actors mapped to MITRE ATT&CK, emerging CVEs with exploitation status, research from CrowdStrike, Palo Alto Unit 42, Red Canary, and others, plus vendor M&A and regulatory movement. Product Leader mode delivers a product intelligence brief for GMs, PMs, and anyone steering a product — company signal, competitor moves, AI in product, funding and M&A, platform risk, regulatory pressure, analyst sentiment, and a vertical-specific section that adapts to what they build and who they build for. Custom mode lets any user describe their morning interests — stocks, industry news, competitor moves, policy, social signal — and maps them to a curated source suite. Output: a live Iron Log-branded HTML artifact, transparent about every source used, pulled on demand with your first coffee. Trigger phrases: "warmup", "run warmup", "run the warmup", "start my warmup", "give me my warmup", "warmup setup", "set up the warmup", "configure the warmup", "warmup config", "add source to warmup", "remove source from warmup", "show my warmup sources".


## Why "The Warmup"

In the gym, a warmup is not optional. You do not walk under the bar cold.
A warmup primes your nervous system, surfaces what is tight, and tells you
whether today's session needs to be adjusted before the work begins. It is
the ten minutes that makes the next ninety honest.

The Warmup does the same thing for your workday. Before you open your inbox,
before you take the first meeting, before you have the conversation that shapes
the next quarter — you know what moved. You know who is active. You know what
the field looks like this morning.

You do not go under the bar cold.

The name comes from *Mission Built*, where the principle is: prepare like the
result matters, because it does.

---

## When to use this skill

Activate this skill when the user asks you to do any of the following:

- Run their warmup
- Get today's warmup
- Set up the warmup for the first time
- Reconfigure their sources
- Add or remove a source from their brief
- See what sources are in use

**Trigger phrases include:** *"warmup"*, *"run warmup"*, *"run the warmup"*,
*"start my warmup"*, *"give me my warmup"*, *"what's in the brief today"*,
*"warmup setup"*, *"set up the warmup"*, *"configure the warmup"*,
*"warmup config"*, *"add [source] to my warmup"*, *"remove [source] from warmup"*,
*"show my warmup sources"*, *"exclude [source] from warmup"*.

---

## Philosophy

**Signal over noise. Every source labeled. Every claim attributed.**

The Warmup has a point of view: authoritative sources first, flagged sources
clearly marked, nothing buried in volume. A brief that forces you to sort
through noise is not a brief — it is a second inbox.

Four principles:

**1. Tier before topic.** Every item in the brief carries its source's trust
tier visually. A Tier 1 government advisory and a Tier 3 community post are
not the same weight of evidence. The brief treats them differently because
they are different. The user always knows what they are reading.

**2. Absence is information.** If a source returns nothing today, that is
reported. If a source is unavailable, that is reported. A blank section is
never padded. Silence from a source that usually speaks is itself a signal.

**3. The source panel is not optional.** Every run of the brief ends with a
full disclosure of every source that was consulted — active, quiet, or
excluded. The user must always be able to audit what their brief was built on.
This is the contract.

**4. Recommendations, not mandates.** When the skill recommends sources,
it explains why. When it flags a source as lower tier, it says so and says why.
The user decides what goes in their brief. The skill's job is to make sure
those decisions are informed.

---

## Modes

Three modes. Each is triggered by a natural phrase.

| Mode | When | What this skill does |
|---|---|---|
| **SETUP** | First time, or reconfiguring from scratch | Establish the user's profile, build their source suite, save to `WARMUP.md`, run a test brief |
| **RUN** | Any time the user wants their brief | Read `WARMUP.md`, fetch live intelligence from each active source, synthesize sections, render the Iron Log artifact |
| **CONFIGURE** | Modifying sources without full re-setup | Show active sources, apply changes (add / remove / exclude), update `WARMUP.md` |

**Brief types available at SETUP:**

| Brief type | Who it's for | Core focus |
|---|---|---|
| **CISO** | Security executives | Threat actors, CVEs, research, vendor market, regulatory |
| **Product Leader** | GMs, PMs, anyone steering a product | Company signal, competitors, AI in product, funding, platform risk, vertical-specific |
| **Custom** | Anyone | User-defined interests, fully flexible source suite |

If no `WARMUP.md` exists in the project root and the user asks to RUN, prompt
for SETUP first: *"No Warmup config found. Run 'warmup setup' to build your
source suite — it takes about two minutes."*

---

## SETUP Mode

**Trigger:** "warmup setup", "set up the warmup", "configure the warmup for the
first time"

### Step 1 — Choose a starting mode

Ask the user: *"Three brief types to choose from — which fits you best?
  · CISO — cybersecurity executive brief
  · Product Leader — GM / PM intelligence brief
  · Custom — describe your own interests and I'll build a source suite around them"*

- **CISO** is the flagship configuration. Pre-loaded with an authoritative
  source suite curated for security executives. Provide your company name
  and sector, region, and peer vendors are looked up automatically — one
  confirmation and you're done.
- **Product Leader** is built for GMs, PMs, and anyone steering a product.
  Provide your company name and competitors, vertical, region, and model
  are researched automatically. Confirm what's right, answer two quick
  follow-ups, and the brief is ready.
- **Custom** builds a source suite from scratch around the user's described
  interests. Takes a few more questions.
- The user can toggle between modes at any time via CONFIGURE.

### Step 1b — Get the user's name

Once the mode is chosen, ask: *"What's your name? I'll use it in your brief header."*
Examples: *"Mike"*, *"Sarah"*, *"Alex"* — or they can skip with anything like *"doesn't matter"* or *"just leave it blank"*.
Stored only in the local WARMUP.md, never sent anywhere. Save as `name:` in the profile. If skipped, leave blank.

### Step 2a — If CISO mode

**Lead with company name. Auto-fill everything derivable. Ask only what can't be looked up.**

Ask: *"What's your company name? I'll look up your sector, region, and typical peer vendors automatically. Or say 'skip' and I'll ask instead."*

**If the user provides a company name:**

Call the **WebSearch tool** with query: `"[Company]" company overview industry sector headquarters cybersecurity`

From the results, determine:
- **Sector** — map to one of the Sector Sources table values below (Healthcare, Financial Services, Energy / Utilities, Technology, Government, Manufacturing / OT, Retail, Critical Infrastructure, or the user's own phrasing if it doesn't map cleanly)
- **Region** — infer from HQ location. Map to: United States, European Union, APAC, Latin America, or Global if multinational
- **Peer vendors** — based on the company's sector and known competitive landscape, suggest 3–5 security vendors they likely watch (e.g., a healthcare org watches CrowdStrike, Palo Alto, Microsoft Sentinel; a fintech watches Wiz, SentinelOne, Lacework)

Present all findings in a single confirmation message:

*"Here's what I found for [Company]:
  · Sector: [X]
  · Region: [Y]
  · Peer vendors to track: [A, B, C]
Does that look right? Edit anything or say 'looks good' to continue."*

Accept natural-language edits. Update any field the user corrects. Save company, sector, and region to WARMUP.md.

**Then ask these two follow-up questions — do not skip them:**

**Follow-up 1 — People to follow:**
*"Anyone in the security world you want to follow closely — executives, CISOs, researchers, threat intel voices? I can suggest a few based on [Company]'s space."*
Suggest 2–3 relevant names based on sector and company (e.g., known CISOs at peer companies, prominent threat researchers, security journalists). Present as: *"People like [A], [B], [C] are worth following if you're in [sector]. Anyone to add, or skip this?"*
Save confirmed names to `track_people:` in WARMUP.md. If skipped, leave blank.

**Follow-up 2 — Personal interests:**
*"Last one — anything you want at the end of your brief that's not work? Sports, markets, a hobby, a team?"*
Save to `special_interests:` in WARMUP.md. If skipped, omit the section. Accept any answer — "skip", "nothing", or an actual interest. Do not pressure.

**If the user skips the company name:**

Ask these four questions one at a time:

1. *"What industry or sector is your organization in?"*
   Examples: *"Healthcare"*, *"Financial Services"*, *"Energy / Utilities"*, *"Technology"*, *"Government"*, *"Manufacturing / OT"*, *"Retail"*, *"Critical Infrastructure"*
   Accept open-form. Map to the Sector Sources table below.

2. *"What region are you primarily operating in?"*
   Examples: *"United States"*, *"European Union"*, *"APAC"*, *"Latin America"*, *"Global"*

3. *"Any specific vendors or competitors you want to track?"*
   Examples: *"Palo Alto, CrowdStrike, Wiz"*, *"Microsoft Sentinel, Splunk, SentinelOne"*, *"skip"*

4. *"Anything you want to stay current on outside of work? Totally optional."*

Build the source suite from the CISO Source Suite tables below.
Add sector-specific sources from the Sector Sources table.

### Step 2b — If Product Leader mode

**Lead with company name. Auto-fill sector, region, and competitors. Ask only what can't be looked up.**

Ask: *"What's your company name — and what product or area are you responsible for? I'll look up your sector, region, and top competitors automatically. Or describe it yourself and I'll go from there."*

Examples: *"Acme Corp, security platform"*, *"Blue Yonder, supply chain"*, *"skip — I'll describe it"*

**If the user provides a company name:**

Call the **WebSearch tool** with query: `"[Company]" product overview market competitors B2B B2C industry`

From the results, determine:
- **Product focus** — what the company primarily builds and sells
- **B2B / B2C / platform** — infer from business model. Map to: `b2b` / `b2c` / `platform` / `marketplace` / `hybrid`. If ambiguous, note it and ask.
- **Vertical / customer industry** — who the company sells to. Map to the vertical source options below (Security, Fintech, Healthcare, Enterprise SaaS, Developer tools, E-commerce, Logistics, etc.)
- **Region** — infer from HQ location
- **Top competitors** — identify 3–5 direct competitors from search results

Present all findings in a single confirmation message:

*"Here's what I found for [Company]:
  · Product: [what they build]
  · Model: [B2B / B2C / platform]
  · Vertical: [customer industry]
  · Region: [Y]
  · Top competitors: [A, B, C, D]
Does that look right? Edit anything or say 'looks good' to continue."*

Accept natural-language edits. If B2B/B2C is still unclear after the search, ask: *"One quick one — are you selling to businesses, consumers, or is it a platform other developers build on?"*

If the user's vertical doesn't map cleanly, ask: *"What does a bad week look like for your business — what external event would most disrupt your roadmap?"* Use the answer to infer the right vertical section.

**Then ask these three follow-up questions — do not skip them:**

**Follow-up 1 — AI vendors:**
*"Which AI vendors or tools matter most to your roadmap? I'd default to OpenAI, Anthropic, Google DeepMind, and Meta AI — plus any tools your team uses (Copilot, Cursor, Mistral). Anything to add or drop?"*
Save confirmed list to `ai_vendors:` in WARMUP.md. If skipped, use the default set.

**Follow-up 2 — People to follow:**
*"Anyone you want to track closely — executives, investors, analysts, journalists, or researchers? I can suggest a few based on [Company]'s space."*
Suggest 2–3 relevant names based on vertical and company (e.g., for a security platform: relevant VCs, CISOs at peer companies, prominent analysts). Present: *"People like [A], [B], [C] are worth following if you're in [vertical]. Anyone to add, or skip this?"*
Save confirmed names to `track_people:` in WARMUP.md. If skipped, leave blank.

**Follow-up 3 — Personal interests:**
*"Last one — anything you want at the end of your brief that's not work? Sports, markets, a hobby, a team?"*
Save to `special_interests:` in WARMUP.md. If skipped, omit the section. Do not pressure.

**If the user skips the company name:**

Ask these five questions one at a time:

1. *"What are you building and who are you building it for?"*
   Accept open-form. Infer product focus, B2B/B2C, and vertical from the answer.

2. *"What industry or vertical is your customer in — or, if B2C, who is your user?"*
   Map to the vertical source options below.

3. *"Who are your top three to five direct competitors?"*
   Generate a suggested list based on what they've described. Present: *"Based on what you've told me, I'd start with: [A, B, C]. Does that look right?"*

4. *"Which AI vendors or tools matter most to your roadmap?"*
   Suggest the standard default set and let them edit.

5. *"Any execs or analysts to track personally? Any non-work interests?"*

### Step 2c — If Custom mode

Ask: *"Describe what you want in your warmup. Be specific — topics,
companies, industries, markets, regions, anything that matters to how you start
your day."*

From the described interests, map each to one or more recommended sources
using the Custom Mode Source-Building Rules below.

For each mapped source, state:
- What you are recommending and why
- Its trust tier
- A flag if it is Tier 3 or lower: *"[Source] is Tier 3 (Community/Unverified).
  Items from it will be labeled in the brief. Worth including?"*

Recommend any sources the user likely wants but did not mention.

### Step 3 — Present the source list for review

Show the full proposed source suite before saving. Format:

```
Tier 1 — Authoritative
  ● CISA Alerts & Advisories
  ● CISA Known Exploited Vulnerabilities (KEV)
  ● NVD / CVE Database
  ...

Tier 2 — Research
  ◉ CrowdStrike Intelligence Blog
  ◉ Palo Alto Unit 42
  ...

Tier 3 — News
  ○ Krebs on Security
  ...

Excluded from this run: (none)

Special Interests  (if provided)
  ○ [Interest 1] — list the 1–3 sources that will cover it
    e.g. "Formula 1 → motorsport.com, ESPN F1, AP Sports"
    e.g. "SEC football → ESPN, 247Sports, AP Sports"
    e.g. "Bourbon releases → Whisky Advocate, BourbonBlog.com"
    e.g. "Markets → Reuters Markets, Yahoo Finance"
  ○ [Interest 2] — same format
```

If special interests were provided, always list them here. The user deserves to see what sources their brief will pull from — this section is not optional when interests exist.

Ask: *"Any sources to add or remove before I save this?"*

### Step 4 — Ask about the lookback window

Before saving, ask: *"Last thing — how far back should I look for your first
brief? The default is 1 day, but since this is your first run I'd recommend
7 days to get up to speed, or 30 days for a full month of context. What works
for you?"*

Accept any natural phrasing: *"7 days"*, *"go back two weeks"*, *"just today"*,
*"one month"*. Save the answer as `window_override` in WARMUP.md if the user
wants a persistent window, or use it only for this run if they say so.
If the user says *"default"* or *"1 day"*, use adaptive lookback (no override).
Remind them: *"You can always override this at run time — just say 'warmup,
go back 2 weeks' and I'll use that window for that run only."*

**Also ask about search depth:**

*"One more setting — search depth. By default I cap each search batch to 5 results and 200 words per article. This keeps the brief fast and token-efficient (typically 40–60K tokens for the fetch phase). If you have more token budget, 'deep' mode doubles both — 10 results per batch, 400 words per article — for broader coverage at roughly 2× the fetch cost. Standard is what I'd recommend for daily use. Which do you prefer?"*

Save as `search_depth: standard` or `search_depth: deep` in WARMUP.md. If the user skips or has no preference, default to `standard`.

### Step 5 — Save WARMUP.md

Save the config file at the project root using the WARMUP.md Config Format
defined below.

### Step 6 — Run a test brief

Immediately run a RUN cycle. If any sources return nothing, report:
*"[Source] returned no signal in the test run. It may be temporarily
unavailable or the search found nothing recent. I've kept it in your config —
it will be checked each run."*

Do not remove sources from config due to a single empty result.

---

## RUN Mode

**Trigger:** "warmup", "run warmup", "run the warmup", "start my warmup",
"give me my warmup", "what's in the brief today"

**Override trigger:** The user can specify a custom lookback at run time:
*"run the warmup one month back"*, *"run warmup since April 15"*,
*"give me the last two weeks"*, *"warmup — go back 30 days"*.
If a lookback phrase is detected, use that window instead of the computed
window and note it in the chat summary line.

### Step 1 — Find workspace root, read config, compute lookback window

**First: find workspace root** — the folder where `WARMUP.md` and `warmup.html`
live across runs:
- In Claude Code / Cowork: the project root the user has open.
- In a chat-only environment: the conversation's persistent output area.
- An existing `warmup.html` or `WARMUP.md` marks the root — prefer their location.

**Validate** — if the workspace root contains any of these strings, you have the WRONG path:
`"Application Support"` · `"sessions"` · `"outputs"` · `"uploads"` · `"local-agent"` · `"tmp"`

A correct workspace root looks like: `/Users/mike/Projects/loadout`

If you cannot determine a valid workspace root, stop and ask the user to confirm their workspace folder.

Then use the **Read file tool** (not bash) to read `[workspace-root]/WARMUP.md`. If WARMUP.md does not exist, stop and prompt for SETUP.

Note: mode (CISO or Custom), user profile, active source list, excluded
sources, `last_run` date, `window_override` if set.

**Compute the lookback window:**

```
today         = current date (YYYY-MM-DD)
last_run_date = parsed from WARMUP.md `last_run` field (YYYY-MM-DD)
gap_days      = (today - last_run_date) in calendar days

# Override checks — apply first, skip the rest if matched
if user stated a lookback phrase in this run (e.g. "go back 30 days", "since April 15"):
  window = user-specified value   # note in summary line, skip remaining logic
elif window_override is set in WARMUP.md:
  window = window_override
elif last_run is missing or empty:
  window = 30   # first run — bootstrap with a month of context
elif gap_days == 1 AND daily_mode: true in WARMUP.md:
  window = 2    # daily fast-path: skip re-fetching a full 7-day window
elif gap_days <= 7:
  window = 7    # standard — always covers at least a week
else:
  window = min(gap_days, 30)   # catch-up run, capped at 30 days

# Weekend bridge (run after computing window above)
region = WARMUP.md `region` field (default: Sat+Sun weekend; IL/Israel: Fri+Sat)
if today == first working day after regional weekend AND gap_days <= 2:
  window = max(window, gap_days + 2)   # cover full weekend
  note in summary: "Lookback extended to cover weekend"
if gap_days > 7 AND interval spans a user-declared holiday (Notes: "holiday: YYYY-MM-DD"):
  note in summary: "Catch-up run — verify holiday coverage manually if needed"

# Search date parameter
search_after_date = today - (window + 1) days  # +1 catches late-yesterday and early-today
```

Note the computed window in the summary line. **Hard date filter:** every item in the brief MUST have a publication date within the lookback window — no exceptions. If a source has no in-window items, mark it `"status": "quiet"`.

### Step 2 — Fetch phase

Before starting any searches, output this line in chat:
*"🔍 Gathering intelligence from [N] sources · [M] search batches · lookback [X] days — this takes a few minutes."*

**Run all batches concurrently.** Do not wait for one batch to complete before starting the next — they are independent. Fire all batches in a single parallel pass, then synthesize after all return.

For each active source, search for recent content using WebSearch.

Search using compound batch queries — not one query per source. This cuts fetch volume from ~38 calls to ~10 without losing coverage. Run batches concurrently where possible; they do not depend on each other.

**Batch query table (CISO mode):**

| Batch | Sources covered | Query pattern |
|---|---|---|
| Gov pulse | CISA + NSA + FBI + FTC | `(site:cisa.gov OR site:nsa.gov OR site:ic3.gov OR site:ftc.gov) advisory alert after:YYYY-MM-DD` |
| Research | MSTIC + CrowdStrike + Red Canary + Wiz + Unit 42 | `(site:microsoft.com/security OR site:crowdstrike.com/blog OR site:redcanary.com/blog OR site:wiz.io/blog OR site:unit42.paloaltonetworks.com) [sector] threat after:YYYY-MM-DD` |
| CVE sweep | NVD + CISA KEV | `(site:nvd.nist.gov OR site:cisa.gov/known-exploited-vulnerabilities) CVE critical after:YYYY-MM-DD` |
| News | BleepingComputer + SecurityWeek + Krebs + THN + Dark Reading | `(site:bleepingcomputer.com OR site:securityweek.com OR site:krebsonsecurity.com OR site:thehackernews.com OR site:darkreading.com) [sector] after:YYYY-MM-DD` |
| Market | Reuters + Bloomberg + sector vendors | `[company OR sector] acquisition OR breach OR regulatory site:reuters.com OR site:bloomberg.com after:YYYY-MM-DD` |
| Social | X + r/netsec + LinkedIn | `[sector] security debate OR disclosure site:reddit.com/r/netsec after:YYYY-MM-DD` |
| Interests | One per special interest | Targeted query per interest (e.g., `Ironman 70.3 results 2026`) |

Replace `YYYY-MM-DD` with the computed lookback start date. Adapt queries to the user's sector and profile (e.g., a Healthcare CISO adds `site:hhs.gov hc3` to the gov batch). Run Gov, Research, CVE, News, Market, and Interests batches **all concurrently** — fire all batches in a single parallel pass, then synthesize after all return. Do not wait for one batch before starting the next.

**WebSearch result budget:** Check `search_depth` from WARMUP.md:
- `standard` (default): top 5 results per batch · 200 words per article
- `deep`: top 10 results per batch · 400 words per article

Standard is recommended for daily use — keeps fetch-phase cost at 40–60K tokens. Deep roughly doubles that for broader coverage. If `search_depth` is not set or unrecognized, use standard.

**Record for each found item:** source name, trust tier, URL, headline, 2–3 sentence summary, relevant tags (CVE ID, MITRE TTP ID, vendor name, M&A flag, regulatory flag, community flag).

**skipScan fast-path:** If `skip_scan: true` is set in `WARMUP.md`, skip the URL safety check entirely. Set `config.skipScan: true`, `safety.domains: []`, and `safety.totalUrls: 0` in WARMUP_DATA. Do not call URLScan.io. Do not perform Step A allowlist checks. Proceed directly to synthesis. A friendly disclaimer will render in the artifact in place of the Link Safety panel.

**URL safety check — run before adding any item to the brief:**

For every URL returned by search, check it against the trusted-domain allowlist
and URLScan.io before including it in the report.

```
Step A — Allowlist check (instant, no API call):
  If the URL's registered domain matches the allowlist below → VERIFIED SAFE.
  This covers all known-good sources across CISO and Product Leader modes.

  CISO allowlist domains:
    cisa.gov, nsa.gov, ic3.gov, fbi.gov, ftc.gov, nvd.nist.gov, attack.mitre.org,
    crowdstrike.com, unit42.paloaltonetworks.com, redcanary.com, cloud.google.com,
    microsoft.com, blog.talosintelligence.com, secureworks.com, recordedfuture.com,
    wiz.io, krebsonsecurity.com, thehackernews.com, darkreading.com,
    securityweek.com, bleepingcomputer.com, arstechnica.com, scmagazine.com,
    crn.com, techcrunch.com, cybersecurityventures.com,
    hhs.gov, h-isac.org, fsisac.com, occ.gov, eisac.com, cio.gov,
    pcisecuritystandards.org, dragos.com, claroty.com, nozominetworks.com

  Product Leader allowlist domains:
    sec.gov, crunchbase.com, a16z.com, sequoiacap.com, cbinsights.com,
    gartner.com, forrester.com, producthunt.com,
    techcrunch.com, theverge.com, wired.com, fastcompany.com,
    reuters.com, bloomberg.com, lennysnewsletter.com, reforge.com,
    news.ycombinator.com, linkedin.com, g2.com, capterra.com, trustpilot.com,
    openai.com, anthropic.com, deepmind.google, ai.meta.com, research.facebook.com,
    mistral.ai, huggingface.co, arxiv.org,
    github.blog, github.com, stackoverflow.com, changelog.com,
    paymentsdive.com, pymnts.com, consumerfinance.gov,
    rockhealth.com, himss.org, cms.gov, fda.gov,
    socialmediatoday.com, saastr.com, chartmogul.com,
    digitalcommerce360.com, freightwaves.com, supplychaindive.com,
    nfx.com, bvp.com

  User-configured sources (from WARMUP.md `competitors:` and `ai_vendors:` fields):
    Extract the registered domain from each configured URL. These are user-chosen
    sources that passed their initial review at SETUP. Treat as allowlisted.
    Example: if competitors includes "https://www.splunk.com", splunk.com is allowlisted.

Step B — URLScan.io check (for domains not on the allowlist):
  Query: https://urlscan.io/search/#domain:<domain>
  If result exists AND verdict is explicitly clean → VERIFIED SAFE.
  All other outcomes → NOT VERIFIED: treat as flagged and exclude.

"All other outcomes" means: suspicious verdict, malicious verdict, no result
found, API timeout, API error, rate limit, ambiguous verdict, or any condition
where a clean result cannot be positively confirmed. There is no partial credit.
A URL is either verified safe or it does not appear in the report.
```

**If a URL is not verified safe (flagged, failed scan, or unknown):**
- Do not include the URL anywhere in the report. No hyperlink, no bare URL.
- Record it in a `flagged_urls` list: `{url, domain, verdict, source_name}`.
  For scan failures, set `verdict` to `"scan unavailable"`.
- The article's content may still appear in the brief as plain text without
  a link, attributed to the source name only, if the content is relevant
  (e.g., *"CrowdStrike reported X — link omitted, domain not verified"*).
- The `flagged_urls` list feeds into the safety WARMUP_DATA block and is
  surfaced in the scan badge and the Link Safety section at the bottom of
  the artifact. The scan badge text updates to: *"N links scanned · M not verified"*.
- If any URLs were excluded, add a brief note in the chat summary line:
  *"⚠ [M] URL(s) excluded — not verified safe (flagged or scan unavailable)."*
- The Link Safety section in the artifact must only list domains that passed
  verification. It must never show a domain that failed or was not checked.

After all batches complete, output in chat:
*"🔒 Running link safety verification on [N] URLs..."*

**Safety check is a Step 2 action — not a render-time assumption.** The `safety.domains` array in WARMUP_DATA must be built from the checks actually performed during this fetch phase. Do not copy verdicts from a previous run, do not assume all sources are clean, and do not fill in the array during synthesis or render. Every domain that appears in `safety.domains` must have been checked in Step 2 of this run. Verdict values: `"ALLOWLISTED"` (Step A match, no external call), `"CLEAN"` (Step B URLScan.io explicitly clean). Anything else is flagged and excluded.

**If a batch returns nothing:** mark those sources "no signal today." Do not invent content. A quiet source is reported honestly.

**Source prioritization:** Tier 1 and Tier 2 sources are fetched first and given the most depth. Tier 3 and Tier 4 are supplemental. If you run out of capacity, deprioritize Tier 3 and Tier 4 before cutting Tier 1 or 2.

### Step 3 — Synthesize phase

Output in chat before starting synthesis:
*"⚡ Synthesizing [N] items across [M] sections..."*

**DATE FILTER — MANDATORY GATE. No item enters WARMUP_DATA without passing this check.**

```
lookback_start = today - lookback_days

BEFORE WRITING EACH ITEM — run this check:
  1. Parse item.date as YYYY-MM-DD
  2. Is item.date ≥ lookback_start? → INCLUDE
  3. Is item.date < lookback_start? → DISCARD immediately. Do not include it "because it's relevant."

Real violations that MUST be caught (window = 7 days, today = 2026-05-16):
  lookback_start = 2026-05-09
  item.date = 2026-05-08  → 8 days old  → REJECT  ← one day over. Still REJECT.
  item.date = 2026-05-06  → 10 days old → REJECT  ← "only two weeks ago" is still REJECT.
  item.date = 2026-05-09  → 7 days old  → ACCEPT  (exactly at boundary = OK)
  item.date = 2026-05-10  → 6 days old  → ACCEPT
```

**No date = discard.** If a result has no parseable publication date, discard it. Do not guess or assume.

**"Relevant but old" = still discard.** An article can be highly relevant and still violate the date filter. Relevance does not override the date gate.

If after filtering a source has zero in-window items, mark it `"status": "quiet"` in `sources[]` and exclude it from `safety.domains`.

**Source status must match what appears in the brief.** A source is `"active"` only if
at least one of its items is included as a card in the brief. If you found articles
from a source but none make it into the brief (e.g. all outside the window), the source
is `"quiet"`. Never mark a source active when none of its articles are visible to the reader.

This gate runs **before** you organize items into sections. Do not route stale items into sections intending to remove them later — discard at first sight, before any further processing.

Organize fetched items into sections using the Section Structure below
(CISO mode) or the user's defined interest categories (Custom mode).

**Inclusion rule — the date gate is the only filter.**
Every item that passes the lookback window check appears in the brief as its own card.
Do not cap by volume. Do not fold a distinct story into another item's body copy.
Do not drop an item because a "better" item covers the same theme. Do not editorially
select a subset. If the agent found it and it is within the window, the reader sees it.
The brief may have more items on active news days and fewer on quiet ones — that variance
is correct and honest. Within a section, order items by recency (newest first),
with the most recent item as the section lead.

### Step 3b — Special Interests (optional)

If `special_interests` is set in `WARMUP.md`, the Interests batch was already fetched concurrently in Step 2. Do not run a second fetch here.

Render the results from the Step 2 Interests batch as a **Special Interests** section in the artifact, positioned after AI Intelligence (or Industry Intel if the AI section is not present) and before Social Signal. Use general news and sports/topic sources — label all items with `○` (Tier 3 / Community/News).

Tag format: use `[NBA]`, `[SEC FOOTBALL]`, `[F1]`, etc. — whatever matches
the interest. Keep summaries conversational — this is the coffee reading, not
an intelligence item. Two to four sentences is enough.

If `special_interests` is not set or is empty, omit the section entirely.
Do not add a placeholder or ask about it during RUN.

### Step 4 — Render phase

**ABSOLUTE RULE — NO EXCEPTIONS:**
The brief HTML is ALWAYS built from the bundled `warmup-template.html` in this
skill folder. **Never write the HTML from scratch. Never use training-data
memory of what the brief looks like.** The CSS, layout, typography, embedded
fonts, renderer, and PDF builder exist only in that template — reproducing
them from memory will produce the wrong design.

**Self-contained architecture — data is injected at build time.**

The template carries the full render engine with fonts baked in, plus two
placeholders: `__WARMUP_DATA__` and `__WARMUP_SAVED_AT__`. Each run rebuilds
`warmup.html` from template + today's data. There is no engine version check,
no chunk stitching, no Path A vs Path B, and no server round trip.

**The flow:**

1. Write the assembled WARMUP_DATA object as JSON to
   `[workspace-root]/warmup-data.json`. Keep this file — it is the editable
   record of the current brief and the input for corrections.

2. Run the bundled injection script:
   `python3 [skill_dir]/scripts/inject.py warmup-data.json [skill_dir]/warmup-template.html warmup.html`
   The script validates the JSON, escapes `</script>` sequences, injects the
   data, and stamps the generation timestamp. It prints `[inject] OK` on
   success and a specific error on failure — fix the data and re-run.

3. FALLBACK — no shell available: read the template with file tools, replace
   every `</script>` inside the JSON string with `<\/script>`, swap the
   literal `__WARMUP_DATA__` token for the escaped JSON and
   `__WARMUP_SAVED_AT__` for the current UTC ISO timestamp (literal string
   swaps — no regex), and write the result to `warmup.html`.

4. Surface `warmup.html` to the user.

   - **In Cowork:** deliver it as a live artifact with `create_artifact`
     (`html_path` = the built `warmup.html`). This is the preferred path — the
     Cowork artifact viewer injects the `window.cowork` bridge, which is what
     powers the **Deep Dive** buttons (they call `window.cowork.askClaude` for
     an on-demand AI expansion of any item). No `mcp_tools` are required for
     Deep Dive — `askClaude` is a built-in. On a re-run, use `update_artifact`
     with the same id.
   - **Anywhere else (Claude Code, chat, or a downloaded file):** present
     `warmup.html` with the environment's file mechanism. It is fully
     self-contained — fonts embedded, zero network — and works offline in any
     browser.

   **Deep Dive degrades gracefully:** the buttons are hidden unless the live
   `askClaude` bridge is detected at runtime, so a brief opened as a plain file
   (or exported with "Save as HTML") never shows a non-functional Deep Dive
   button. Deep Dive is therefore a Cowork-artifact feature; the offline brief
   is otherwise identical.

   If the brief is already open from a prior run, the user reloads the page (or
   taps Refresh in the masthead) to pick up the new brief.

**User requests a correction to the existing brief (no new searches):**

Triggered when the user asks to change something in the current report — fix a headline, correct a date, add or remove an item, rewrite a body — without running fresh fetches.

1. Read `[workspace-root]/warmup-data.json`.
2. Apply the user's requested change to the relevant field(s). Touch nothing else.
3. Re-run the injection script (Step 4.2) to rebuild `warmup.html`, then tell
   the user to reload the page.

No new searches. No template edits — only the data file changes.

**When an engine bug is fixed:**
1. Apply the fix to `warmup-template.html` in this skill folder.
2. Every run rebuilds `warmup.html` from the template, so the next daily run
   picks up the fix automatically — no version bump mechanics needed.

**`WARMUP_DATA` schema (v0.3.0 — Morning Edition):**

> **Config field accuracy rule:** `mode`, `sector`, `company`, and `region` MUST be copied verbatim from `WARMUP.md`. Do not infer, generalize, abbreviate, or replace. If the user said "Security", sector = "Security". If the user said "Global", region = "Global". These values appear as pills the user sees on every run.

```json
{
  "config": {
    // Required
    "name": "Mike",
    "mode": "CISO",
    "company": "Acme Corp",
    "sector": "Cybersecurity",
    "reportDate": "Thursday, 15 May 2026",   // REQUIRED — full display string for the masthead date (e.g. "Friday, 15 May 2026").
                                               // Format: "{Weekday}, {DD} {Month} {YYYY}". Use today's date in the user's timezone.
                                               // Without this field the masthead date falls back to template placeholder text.
    "updated": "15 May 2026",                // Footer display string
    "lastRun": "2026-05-14",                 // ISO date — drives issue number
    "dateRange": "May 8 – May 15, 2026",     // Lookback window display string
    "sourcesActive": 12,
    "sourcesQuiet": 4,
    "showQuote": true,   // REQUIRED — must be true (JSON boolean). Omitting or setting false hides the daily quote.
    "scanTime": "",  // Leave EMPTY ("") unless you have a reliable clock source.
                     // Do NOT invent or guess a time — the renderer will use the user's local
                     // browser clock when this is blank, which is always accurate.
                     // Only write a value (e.g. "06:14 ET") if a tool explicitly returned the
                     // current wall-clock time. Writing a fabricated time is worse than omitting.
    "timezone": "ET",   // REQUIRED — copy verbatim from WARMUP.md `timezone` field (e.g. "ET", "PT", "UTC").
                        // CRITICAL: this is the USER'S local timezone — NOT the company's headquarters timezone.
                        // Read it from WARMUP.md. Do not infer from the company location. Write "UTC" if not set.
                        // Without this field the time display in the masthead is missing timezone context.
    // Optional fields — include even if blank (write "" not omit)
    "region": "Global",
    "vendors": "CrowdStrike, Palo Alto",  // Copy verbatim from WARMUP.md vendors field. Write "" if blank — do not omit.
    "interests": "",
    "totalLinks": 18,  // Count of verified-safe clickable URLs in the rendered brief. Must equal safety.totalUrls.
    "skipScan": false,  // Optional — set true if skip_scan: true in WARMUP.md. Hides scan badge, skips safety panel, shows friendly disclaimer instead.
    "searchDepth": "standard"  // "standard" | "deep" — copy from WARMUP.md search_depth. Drives depth indicator in sources panel and configure modal.
  },
  "sections": [
    {
      "id": "threat",
      "label": "Threat Landscape",
      "sub": "Active campaigns and fresh exploitation. What your stack should be watching for today.",
      // sub: ALWAYS populated — the section's standing editorial deck, one sentence.
      //      This renders visibly in the brief as italic text under the section heading.
      //      NEVER put lookback computation text, agent instructions, or meta-commentary here.
      //      WRONG: "1-day lookback (first run). Say 'warmup, go back 7 days' for context."
      //      RIGHT: "Active campaigns and fresh exploitation. What your stack should be watching for today."
      //      Write it as editorial voice — a standing description of what this section covers.
      // note: null unless there is a today-only run caveat (e.g. "Source X was down"). Never repeat sub here.
      "note": null,
      "items": [
        {
          // items[0] is the EDITORIAL LEAD — rendered full-width with a large
          // headline and an oxblood drop-cap on the first letter of body.
          // Choose it deliberately: most important item in the section.
          "dot": "d1", "src": "CISA",
          "tags": [{"cls": "t-alert", "text": "KEV ADDED"}, {"cls": "t-mitre", "text": "T1190"}],
          "url": "https://...",
          "hl": "Article headline.",
          "deck": "Federal agencies have until June 4 to patch.",
          // deck: LEAD ITEMS ONLY. One short italic sentence — the 'so what?'.
          // Omit entirely on non-lead items (items[1..N]).
          "body": "2–3 sentence summary in plain prose.",
          "date": "YYYY-MM-DD"
          // CRITICAL: date is the article's actual publication date, not today's date
          // and not a recycled date from a prior run. The renderer filters out items
          // older than 7 days (10 for deep mode, or window_override if set) — stale
          // dates make items invisible while still inflating the ITEMS TODAY count.
          // If you cannot determine the publication date, use today's date rather
          // than guessing or recycling.
        },
        {
          // items[1..N] render in a two-column grid. No deck field. Date-sorted.
          "dot": "d2", "src": "Source Name",
          "tags": [],
          "url": "https://...",
          "hl": "Article headline",
          "body": "2–3 sentence summary.",
          "date": "YYYY-MM-DD"
        }
      ]
    }
  ],
  "sources": [
    // status: "active" | "quiet" | "excluded" — exact strings only, no other values permitted.
    // ct: "N items" for active sources (e.g. "2 items"), "—" for quiet sources, "excluded" for excluded sources.
    {"nm": "CISA Alerts & Advisories", "dom": "cisa.gov", "dot": "d1", "ct": "2 items", "status": "active"},
    {"nm": "NSA Advisories", "dom": "nsa.gov", "dot": "d1", "ct": "—", "status": "quiet"}
  ],
  "safety": {
    // domains: REQUIRED — one entry per active source. Populated from Step 2 checks — never fabricated.
    // Empty array = safety panel does not render. This field must not be omitted or left empty.
    // verdict values (exact strings):
    //   "ALLOWLISTED"   — domain matched the Step A allowlist (no external call made)
    //   "CLEAN"         — domain passed URLScan.io Step B check (explicitly clean verdict)
    // Flagged domains do NOT appear here — they go in flagged_urls and are excluded from the brief.
    // INTEGRITY RULE: domains.length MUST equal the number of active sources exactly.
    "domains": [{"domain": "cisa.gov", "verdict": "ALLOWLISTED"}],
    "totalUrls": 12,   // REQUIRED — count of verified-safe clickable URLs in the rendered brief. Must equal config.totalLinks.
    "flagged": 0,
    "scannedAt": ""   // Empty string — renderer uses scanTime. Fill only to override.
  },
  // dates: REQUIRED — one entry per item using the item's hl string (or a unique prefix) as the key.
  // Used by the template to render per-item publication dates. Empty object = no dates rendered.
  "dates": {"Article headline prefix": "YYYY-MM-DD"}
}
```

**Editorial lead rules:**
- `items[0]` is the lead for every section. It renders full-width with a large Oswald headline and an oxblood drop-cap on the first letter of `body`.
- Always use `deck` on lead items — one italic sentence that adds the "so what?" framing.
- The lead is never re-sorted. Choose it deliberately — most important item in the section.
- Items 1..N render in a two-column grid, date-sorted descending. No `deck` field on these.

**`scanTime` — only write it if you actually know the time.** If a tool returned the current wall-clock time, write it as `"HH:MM TZ"` (24-hour, user's timezone, e.g. `"06:14 ET"`). If you don't have a reliable clock source, leave it as `""` — the renderer falls back to the user's local browser clock, which is accurate. A fabricated timestamp is worse than no timestamp. Do not write separate timestamp values anywhere else.

**Never build the artifact HTML from scratch.** Always start from the bundled
`warmup-template.html`. Building from scratch risks re-introducing fixed bugs
and diverging from the canonical engine.

### Step 5 — Summary line

After rendering, output a single summary line in the chat:
*"[N] items across [N] sections · [N] sources active · [N] sources quiet today · Lookback: [N] days"*

If this was a catch-up run, append the reason:
*"… · Lookback: 12 days (catch-up from [last_run_date])"*

Nothing else in chat. The brief is the artifact. Do not duplicate its content
in the chat response.

### Step 5b — Source emergence check (periodic)

**When to run:** After any successful RUN where `(today - updated) >= 30 days`.
The `updated` field in WARMUP.md records when the source list was last configured.
If it has been 30+ days since the user last touched their source config, scan
for new sources that have emerged since then.

**How to run:**

During the fetch phase, note any domains that appeared in search results but are
**not** in the user's active or excluded source list. After synthesis, evaluate
each against the Source Trust Framework. Surface only sources that meet at least
one of these bars:
- Tier 1 or Tier 2 by the framework criteria
- A Tier 3 source with demonstrated sector relevance (it appeared in multiple
  fetched items, not just once) and strong editorial reputation
- A sector-specific source that didn't exist or wasn't notable 30 days ago
  (new research arm, new government advisory feed, etc.)

**Cap at 3 recommendations per run.** Do not recommend sources already in the
config (active or excluded). Do not recommend a source the user has previously
excluded — they made that call deliberately.

**Output format** — append after the summary line in chat, separated by a blank line:

```
💡 New source worth adding:
  [Source Name] · Tier N · domain.com
  [One sentence: what it covers and why it's relevant to the user's sector/profile.]
  Say "add [source name] to warmup" to include it.
```

If more than one recommendation: list them as a short block under a single
`💡 New sources worth adding:` header.

If nothing new qualifies: output nothing. Do not add a "no new sources found"
line — silence is the correct signal.

**Frequency note:** 30 days is the default check interval because a month is
roughly how long it takes for a new source to establish a track record worth
recommending. If the user wants tighter checks (e.g., weekly), they can add
`source_check_days: 7` to the Notes section of WARMUP.md and this step will
use that value instead.

### Step 6 — Update last_run in WARMUP.md

After a successful render, update the `last_run` field in `WARMUP.md` to
today's date in `YYYY-MM-DD` format. This is the record the next run uses
to compute its lookback window.

Do not update `last_run` if the run failed, produced no items, or produced fewer than 3 items total across all sections — treat these as degraded runs and preserve the window so the next run has a wider lookback to recover missing content.

---

## CONFIGURE Mode

**Trigger:** "warmup config", "update my warmup", "add source to warmup",
"remove source from warmup", "show my warmup sources",
"exclude [source] from warmup", "what sources is the warmup using"

### Show sources

Display the current source list in a compact table:

```
Source              | Tier | Domain                    | Status
--------------------|------|---------------------------|--------
CISA Alerts         |  1   | cisa.gov                  | Active
CISA KEV            |  1   | cisa.gov                  | Active
CrowdStrike Blog    |  2   | crowdstrike.com/blog       | Active
...
Krebs on Security   |  3   | krebsonsecurity.com       | Excluded
```

### Add a source

1. Assign a trust tier using the Source Trust Framework.
2. If Tier 3 or lower, flag it explicitly.
3. Add to `WARMUP.md` under the appropriate tier.
4. Confirm: *"Added [source] as Tier [N]. It will appear in your next brief."*

### Remove or exclude a source

Move from active list to Excluded Sources in `WARMUP.md`. The source remains
in the config but is skipped at runtime and shown in the Source Transparency
Panel as excluded.

### Recommend additional sources

If the user asks for recommendations: suggest 3–5 sources relevant to their
profile that they do not already have. For CISO mode, look for gaps in
sector-specific coverage or missing Tier 2 research firms.

### Switch mode

If the user wants to switch between CISO, Product Leader, and Custom modes,
run the appropriate branch of SETUP Step 2 and rebuild the source suite.
Carry over any manually-added sources the user wants to keep.

### Ask about lookback after any configuration change

After any meaningful config change (new sector, new sources, switched mode,
changed company), ask: *"How far back should the next brief look? Default is
1 day — or tell me a different window for this run."* This catches the case
where a config change means the user wants a fresh sweep to see how the new
sources perform. Do not ask after minor changes (typo fixes, timezone updates).

---

## Source suites

The CISO, Product Leader, and Sector-Specific source suites live in
`references/sources.md` in this skill folder. Read that file when entering
Product Leader or Custom mode, or when adding sector sources.

## Report section structures

The CISO and Product Leader report section structures (including the Product
Leader batch query table) live in `references/sections.md`. Read that file
during the synthesize phase.

## Custom mode & source trust

Custom-mode source-building rules and the Source Trust Framework live in
`references/custom-mode.md`. Read that file when the user runs Custom mode.

## Artifact Design Spec

The full design spec — color tokens, fonts, layout, component patterns, and the five rules — is in `SKILL-DESIGN.md`. It is not needed during normal operation: every artifact build starts from the bundled `warmup-template.html`, which already embeds all design tokens. Read SKILL-DESIGN.md only when modifying the template itself.

---

## WARMUP.md Config Format

Saved at the project root when SETUP runs. Updated in place when CONFIGURE
makes changes. Claude reads this file at the start of every RUN.

```markdown
# Warmup Config

## Profile
mode: ciso                  # ciso | product_leader | custom
sector: healthcare
company: Example Health System
region: united-states
vendors: Palo Alto Networks, CrowdStrike, SentinelOne   # CISO: vendors to track; Product Leader: AI vendors
special_interests: SEC football, NBA
name: Sam
updated: 2026-05-14
last_run: 2026-05-14        # set automatically after each successful run
window_override:            # optional: set a fixed lookback in days (e.g. 14); leave blank for adaptive
daily_mode: true            # set to true if you run the brief every day; enables 2-day lookback fast-path
source_check_days:          # optional: days between source emergence checks (default: 30)
skip_scan: false            # set to true to skip URL safety checks — saves tokens, but links are unverified. Recommended: false.
# ── Search Depth ────────────────────────────────────────────────────────────
# Controls how many results per batch and how much article text is extracted.
# Why we cap it: at standard depth the fetch phase uses ~40–60K tokens.
# Deep mode doubles that for broader coverage — useful when your budget allows.
#   standard (default)  5 results per batch · 200 words/article  ← recommended for daily use
#   deep                10 results per batch · 400 words/article  ← ~2× fetch cost, broader coverage
# Switch at any time: say "use deep search" or "use standard search" in chat.
search_depth: standard

# Product Leader fields (populated when mode: product_leader)
product_area:               # e.g. "Security product line", "creator tools", "developer platform"
build_type:                 # b2b | b2c | platform | marketplace | hybrid
vertical:                   # e.g. security | fintech | healthcare | consumer_social | enterprise_saas | developer_tools | ecommerce | logistics | marketplace
competitors:                # comma-separated list; auto-generated at SETUP, editable anytime
ai_vendors:                 # comma-separated AI vendors/tools relevant to roadmap
track_people:               # optional: exec, analyst, investor, journalist names to watch

## Active Sources

### Tier 1 — Authoritative
- CISA Alerts | https://www.cisa.gov/news-events/cybersecurity-advisories | active
- CISA KEV | https://www.cisa.gov/known-exploited-vulnerabilities-catalog | active
- NVD CVE | https://nvd.nist.gov | active
- MITRE ATT&CK | https://attack.mitre.org | active
- FBI Cyber | https://www.ic3.gov | active
- NSA Advisories | https://www.nsa.gov/Press-Room/Cybersecurity-Advisories-Guidance | active
- HHS HC3 | https://www.hhs.gov/about/agencies/asa/ocio/hc3 | active

### Tier 2 — Research
- CrowdStrike Blog | https://www.crowdstrike.com/blog | active
- Palo Alto Unit 42 | https://unit42.paloaltonetworks.com | active
- Red Canary | https://redcanary.com/blog | active
- Google Mandiant | https://cloud.google.com/blog/topics/threat-intelligence | active
- Microsoft MSTIC | https://www.microsoft.com/en-us/security/blog | active
- Cisco Talos | https://blog.talosintelligence.com | active
- Secureworks CTU | https://www.secureworks.com/blog | active
- Recorded Future | https://www.recordedfuture.com/blog | active

### Tier 3 — News
- Krebs on Security | https://krebsonsecurity.com | active
- The Hacker News | https://thehackernews.com | active
- Dark Reading | https://www.darkreading.com | active
- SecurityWeek | https://www.securityweek.com | active
- BleepingComputer | https://www.bleepingcomputer.com | active

### Tier 4 — Vendor Intel
- CRN | https://www.crn.com | active
- TechCrunch Security | https://techcrunch.com/category/security | active

## Excluded Sources
(none)

## Notes
(none)
```

---

## Anti-Patterns

Do not do these. Each one was added because it is a real failure mode.

**1. Do not invent items.**
If a source search returns nothing, mark it "no signal today." The worst
version of this skill is a brief that feels complete because it made things up.

**2. Do not skip the Source Transparency Panel.**
The user must always be able to see what built their brief. This is the
contract. Omitting it is a trust failure.

**3. Do not run without reading WARMUP.md.**
If the config doesn't exist, ask for SETUP. Guessing at sources produces
a brief that is not the user's brief.

**4. Do not mix Tier 3 items into sections without labels.**
A community post should not appear in Threat Landscape without a [COMMUNITY]
tag. Tier unlabeled is Tier 1 by implication. That is a lie.

**5. Do not pad sections with low-signal items.**
Ten mediocre items from Tier 3 news do not substitute for three sharp Tier 2
findings. When the well is dry, say so. "No new research from Tier 2 sources
this week" is an honest and useful line.

**6–8. CSS visual contract (handled automatically)**
The template CSS reset enforces zero rounded corners, zero box shadows, and correct oxblood usage. These constraints are built into the engine — no decisions needed during a normal run.

**9. Do not echo the brief content in chat.**
After rendering the artifact, output one summary line and stop. The brief is
the artifact. Repeating it in chat is noise.

**10. Do not include Social Signal unless it is warranted.**
This section exists for the days when the community produces something genuinely
consequential. It does not exist to pad the brief. If you are not finding
substantive community signal, omit the section header entirely.

**11. Do not include any URL that is not verified safe — ever.**
Verified safe means: on the allowlist, OR URLScan returned an explicit clean
verdict. Anything else — flagged, scan failed, no result, API error, ambiguous
— is excluded. There is no "include with a warning" path. The Link Safety
table in the artifact must contain only verified domains. If you cannot confirm
it is safe, it does not appear. This is a hard rule with no exceptions.

**12. Do not skip the lookback question on first run or config change.**
The user has no intuition about what "1 day" means until they see a brief.
Ask. Remind them the default is 1 day. Let them choose. A 30-day first run
costs nothing and prevents the "why is this so thin?" complaint on day one.

**13. Do not assume a Monday brief only needs 1 day of lookback.**
Monday morning covers Friday afternoon, Saturday, and Sunday. If the user
ran on Friday, gap_days=3. The weekend bridge logic handles this automatically —
but do not override it with a daily fast-path that would collapse it back to
2 days. The fast-path only applies when gap_days==1 AND daily_mode is true.

**14. Do not recommend sources on every run.**
The emergence check runs only when it has been 30+ days since `updated`.
Running it more often produces noise, not signal. A source that appeared
once in a single search result batch does not qualify — it needs multi-item
presence or clear sector fit. When in doubt, don't recommend.

**15. Do not let the competitor list go stale.**
In Product Leader mode, if `competitors:` in WARMUP.md hasn't been updated
in 90+ days, note it in chat after the summary line: *"Competitor list last
updated [date] — say 'update my competitors' to refresh it."* Markets move.
A stale list is a blind brief.

**16. Do not skip auto-generating the competitor list at Product Leader SETUP.**
This is one of the highest-value moments in the setup flow. A generic
*"who are your competitors?"* gets a lazy answer. A specific, credible suggestion
(*"Based on [their company and sector], I'd start with: [2–4 named competitors] — does that look right?"*) gets a useful one.
Always generate the suggestion before asking for confirmation.

---

## Voice

The Warmup is direct and unhurried. It does not sell the user on the brief —
the brief sells itself.

**In chat interactions (SETUP, CONFIGURE):**
- Ask one question at a time. Do not list-dump five questions.
- Use plain language. *"What industry are you in?"* — not *"In order to
  calibrate the threat actor prioritization framework, could you describe
  your organization's primary vertical?"*
- Acknowledge what the user said before asking the next thing.
- When something is flagged (a Tier 3 source, a quiet source), be plain
  about it. *"This source is community-level — less vetted, but worth having
  if you want that signal. Your call."*

**In the artifact itself:**
- Headlines: direct. What happened, who was involved, what it means.
  Not *"A sophisticated threat actor may be potentially targeting organizations."*
  Say *"VOLT TYPHOON targeting US critical infrastructure via living-off-the-land
  techniques (CISA advisory)."*
- Summaries: 2–3 sentences that complete the thought. No filler.
  *"Researchers identified..."* not *"In a fascinating development that
  highlights the evolving threat landscape..."*
- Section headers: JetBrains Mono all-caps labels. Not question-form,
  not clever — just the category. THREAT LANDSCAPE. EMERGING THREATS.
  RESEARCH DIGEST. INDUSTRY INTEL. SOCIAL SIGNAL.
- The footer is the only place the brand speaks. Keep it minimal.

**On source trust:**
When recommending or flagging a source, say what you see.
*"Dark Reading is reputable news — solid for situational awareness,
not primary research. Tier 3."* That is the complete description.
No hedging, no over-explanation.

---

## Attribution

Part of [The Loadout](https://github.com/missionbuilt/loadout).
MITRE ATT&CK® is a registered trademark of The MITRE Corporation.
Source tiers and curation are the author's judgment, not endorsements.

## License

MIT. See `LICENSE` in the Loadout repository.


---

## Version history (self-contained edition)

| Version | Change |
|---|---|
| 0.9.0 | Self-contained release. KV data flow (warmup_save_data / warmup_get_data) replaced by build-time injection via scripts/inject.py against the bundled warmup-template.html. Fonts baked into the template (offline-capable). MCP font loader and KV auto-refresh dormant (dataTool empty); masthead Refresh reloads from disk. Source suites, section structures, and custom-mode rules moved to references/ for on-demand loading. No MCP server dependency anywhere in the skill. |
| 0.9.1 | QA pass for open-source release. Removed all third-party-employer references: the former Tier-2 vendor "security labs" research source was replaced with "Red Canary" (behavioral detection research, open-source detection rules) across the description, batch query table, allowlist, source suite, and WARMUP.md example; schema example company genericized to "Acme Corp"; template subdomain-match comment updated. No functional or renderer changes. |
| 0.9.4 | Section-collapse duplication fix. The "Done / Expand" pass appended a count badge and toggle button to each section eyebrow with no idempotency or export guard. In a downloaded/exported brief it re-ran on open and stacked a second set — two "N items" labels and two overlapping buttons (the garbled "Done"+"Expand" overlay), visible when a section was marked Done. The pass now removes any prior count/toggle before creating exactly one of each, and initializes the button from the section's existing collapsed state. Engine v0.9.4-local. |
| 0.9.3 | Date-duplication fix. The "Article Dates & Sort" pass rendered a second `.item-date` after each headline (renderItem already renders one inline before it) and had no export guard — so a downloaded/exported brief re-ran the pass on open and showed the date three times. That pass is now sort-only: it never inserts a date element and only backfills `data-date` for the recency sort when renderItem didn't already set it. One date per item in the live artifact and the downloaded file. Engine v0.9.3-local. |
| 0.9.2 | Deep Dive fix. The Deep Dive button needs the Cowork `askClaude` bridge, which only exists in the Cowork artifact viewer — opened as a plain file it showed a dead "requires the Cowork app" button. Buttons are now hidden by default (`display:none`) and revealed only when `window.cowork.askClaude` is detected at runtime (`body.cowork-on`), and the reveal class is stripped on Export so offline copies stay clean. RENDER phase updated: in Cowork, deliver via `create_artifact` (where Deep Dive works); elsewhere, present the self-contained file. Engine bumped to v0.9.2-local. Validated with a live CISO research run (Blue Yonder). |
