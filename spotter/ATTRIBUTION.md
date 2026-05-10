# Attribution

This skill draws structural patterns and conceptual framings from open-source PM-skill libraries and from published product-management writers. None of the borrowed material is reproduced verbatim. Where ideas were adapted, this document credits the source.

All cited open-source repositories were checked for license compatibility prior to publication. Repositories cited below carry licenses (MIT, Apache 2.0) that are compatible with this skill's MIT license, or with this skill's stance of conceptual citation without content reproduction. Repositories whose licenses introduced friction without corresponding borrowing have not been cited — citation should reflect actual debt, not citation theater.

If you fork this skill, please preserve this file and add your own contributions and attributions in the same format.

---

## Structural patterns

### Aakash Gupta — `aakashg/pm-claude-skills` (MIT)

Source: <https://github.com/aakashg/pm-claude-skills>

Adopted: the five-section SKILL.md structure (Trigger / Context / Instructions / Output Format / Examples / Anti-patterns), the "examples beat instructions" teaching philosophy, and the recommendation that company-specific context lives in `CLAUDE.md` while the skill stays generic.

The Anti-patterns section pattern in particular — explicit *"things this skill should NOT do"* — is borrowed directly from Aakash's framework and is one of the strongest teaching mechanisms in the open-source skill ecosystem.

### product-on-purpose — `product-on-purpose/pm-skills` (Apache 2.0)

Source: <https://github.com/product-on-purpose/pm-skills>

Inspiration for organizing skill content around a coherent product-thinking framework rather than as a flat list of disconnected utilities.

### Sachin Rekhi — *Claude Code for Product Managers*

Source: <https://www.sachinrekhi.com/p/claude-code-for-product-managers>

The conceptual framing of skills as "AI-powered systems and workflows that automate the work we do every day" — rather than as one-off prompts — informs the design of this skill's three modes (build / iterate / review). Sachin's published thinking on the design of PM-oriented skills is paywalled in detail, but the public framing is credited here.

---

## Lens-specific framings

The nine lenses absorbed conceptual influence from several product-management writers. None of the lens descriptions in `SKILL.md` reproduce these writers' prose; their frameworks shaped how the lenses are organized and what passing-grade looks like.

### Lens 1 — The user & the problem (not the solution)

**Marty Cagan / Silicon Valley Product Group.** The "outcome over output" tradition and Cagan's "product creator" framing inform the no-solutioning sub-check. The principle that PMs describe problems and engineering innovates solutions has been a Cagan throughline for two decades.

Source: *Inspired*, *Empowered*, *Transformed* — Marty Cagan / SVPG.

**John Cutler ("The Beautiful Mess").** Cutler's framing of AI-era product work — *"AI gives teams the illusion of seeing everything while understanding nothing"* — informs the skill's insistence that the empathy sub-check requires lived experience, not abstractions or AI-summarized personas.

Source: <https://cutlefish.substack.com/>

### Lens 2 — Competitive landscape

**Shreyas Doshi.** Doshi's *Deep thinking is your edge* framework and his teaching on rigorous competitive analysis on Maven informed the lens structure of "name three, summarize each in one to three sentences, surface trade-offs, position the work honestly."

Source: Shreyas Doshi's writing and Maven course content.

### Lens 4 — Solution approach (AI decision)

**Melissa Perri.** Her framing — *"AI excels at the how; you own the why"* — is the conceptual anchor for the explicit AI decision sub-check. The skill's requirement that AI use be justified, not assumed, owes Perri's framework directly.

Source: Liveblocks interview with Melissa Perri, *Rethinking product strategy in the age of AI* (paraphrased and credited in *Mission Built*, second edition).

**Pawel Brodzinski.** His essays *AI Won't Generate a Good Product Idea* and *Conway's Law Teaches a Grim Lesson About AI in Product Development* informed the skill's stance that AI-generated work tends toward the median of the distribution and that originality requires human judgment.

Sources:
- <https://pawelbrodzinski.substack.com/p/ai-wont-generate-a-good-product-idea>
- <https://brodzinski.com/2026/04/conways-law-ai-product-development.html>

### Lens 8 — Post-launch ownership

**Teresa Torres.** Her eval-driven discovery framework — log model traces, human-tag a sample, identify error classes, write evals, A/B test fixes — shaped the post-launch sub-checks for AI-driven epics. Torres's documentation of how product discovery shifts when outputs are non-deterministic informed the *"what alerts fire if the AI agent's confidence drops"* sub-check.

Source: <https://www.producttalk.org/> and Teresa Torres's *Continuous Discovery Habits*.

### Lens 9 — Trust, governance & auditability

**Lenny Rachitsky's AI-Native PM curriculum and Tomer Cohen's Full-Stack Builders thesis.** The competitive context for B2B AI features — where multiple players are collapsing into similar capabilities — informs why governance is its own lens. Trust is the differentiator when the underlying capability has been commoditized.

Sources:
- <https://www.lennysnewsletter.com/p/how-ai-will-impact-product-management>
- <https://www.lennysnewsletter.com/p/why-linkedin-is-replacing-pms>

---

## Voice and orientation

The skill's review prose voice — direct, warm, peer-to-peer; *critique not criticism* — is drawn from the *Mission Built* series:

**H. Michael Nichols.** *Mission Built: A Field Guide for Building Things That Matter*, second edition (2026). Specifically, Chapter 4 (*Feedback Is a Superpower*) and the through-line motto — *give a shit* — from Chapter 1 onward.

Source: <https://missionbuilt.io>

The closing line of the book — *"real strength is lifting others"* — is the orientation that underpins this skill's existence. Reviews that feel like gatekeeping fail the test. Reviews that lift the PM and produce stronger work pass it.

---

## How to add new attributions

If you build on this skill or fork it, add new attributions to this file in the same format:

1. Source name and link
2. What was adopted, adapted, or inspired
3. Original source license (where applicable)

The MIT license does not require this. Professional courtesy does.
