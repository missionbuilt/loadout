# Area Examples

This file holds worked examples for every area — strong (✓), needs work (⚠️), and missing (✗) — with teaching notes explaining why each example earns its grade.

All examples are excerpts from B2B product epics. They're anchored against the synthetic epic in `examples/synthetic-epic.md` (an agentic incident response feature for a B2B endpoint security platform), with empathy framing drawn from Mike Nichols' first-person SOC analyst experience.

When the agent loads this file, it should learn the *contrast* between strong and weak prose for each sub-check — the contrast is the teaching, not the rules. If the rules contradicted the examples, trust the examples.

---

## Area 1 — The user & the problem (not the solution)

**The most important area. The one that separates good PMs from great ones.** Most epic failures originate here, and the most consequential failures are subtle: unexamined assumptions, single-path thinking, and epics written with the conclusion already in mind. Eight sub-checks: empathy, current state, why-not-solved, no-solutioning, problem scope and value framing, assumptions surfaced, alternatives considered, and epistemic openness.

### Sub-check A: Empathy

> Does the epic show real understanding of the user's role? Specific moments, lived experience, not abstractions or job descriptions.

**✓ Strong**

> Alert fatigue is real. It's also overused by marketers, and saying it doesn't capture what's actually happening on the floor. Retention rates among Tier 1 analysts are low for a reason. Most of the job is the grind of summarizing alerts and passing them up. The occasional adrenaline hit when a real issue surfaces is what keeps people going. It isn't enough. It isn't fulfilling work for someone who chose this career to make a difference. The aspirational shift this feature unlocks: letting a Tier 1 analyst operate as a Tier 2 or 3. Not by promoting them. By giving them the support of an AI responder that handles the toil and surfaces the work that actually grows them.

*Teaching note: This passes because the prose names lived experience that no template would write. The honest acknowledgment that "alert fatigue" is overused signals a PM who's actually been in the room. The triplet rhythm (the grind, the high, the not-enough) lands the reality. The closing reframe — Tier 1 operating as Tier 2/3 — names the aspiration the feature exists to deliver, not just the symptom it addresses.*

**⚠️ Needs work**

> Tier 1 SOC analysts experience significant alert fatigue due to high alert volumes and repetitive triage work. Industry data shows that retention rates for these roles are below 50% at 18 months. This feature aims to reduce the manual burden on analysts by automating routine response actions, leading to improved job satisfaction and retention.

*Teaching note: Hits the right topics — fatigue, retention, manual burden — but reads like a McKinsey deck. Stripped of voice and lived experience, the prose becomes interchangeable with any other security feature's epic. The skill flags: "You could strengthen this by bringing in what it actually feels like, not what the metrics say. Where's the moment? Where's the specific frustration?"*

**✗ Missing**

> User: Tier 1 SOC analysts at mid-to-large enterprises (>500 endpoints) running our endpoint security platform. They work 12-hour shifts, handle 30–80 alerts per shift, and have 2–5 years of experience.

*Teaching note: This is the user paragraph from the synthetic epic. It's a persona, not empathy. Specific demographics with no interior life. The skill flags: "You've described who they are. The area needs you to describe what their day feels like."*

### Sub-check B: Current state

> How is this solved today? What workarounds exist? What do other products do? Where do users hit walls?

**✓ Strong**

> Analysts cope today through a mix of personal heuristics and informal tooling. The most common workaround we've seen in customer interviews is a shared Slack channel where analysts post screenshots of suspicious alerts and ask "is this anything?" before escalating. Some teams maintain personal spreadsheets tracking which alert types tend to be false positives. Others lean on Splunk searches written by senior analysts months ago, searches that are rarely updated as the threat landscape shifts. Adjacent products customers also run: SOAR platforms like Tines, Torq, and Splunk SOAR for codified runbooks; SIEMs like Sentinel, Splunk, and Elastic for the alert routing layer. The pattern across all of these: today's tooling scales senior judgment to junior analysts only as effectively as the senior analysts have time to write and maintain the rules.

*Teaching note: Specific workarounds (Slack channel, spreadsheets, stale Splunk searches), specific adjacent products by name (Tines, Torq, Sentinel), and a synthesis that names the underlying pattern. The reader can picture it. The PM has clearly done customer interviews.*

**⚠️ Needs work**

> Analysts currently use a combination of manual triage and existing platform playbooks. Some teams have built custom integrations to streamline their workflow.

*Teaching note: Two sentences of generic. No named workarounds, no adjacent products, no diagnosis. The skill flags: "You're acknowledging current state exists, but not describing it. What do customers actually do today, in detail?"*

**✗ Missing**

> [No current state described. The epic moves from "alert volume is too high" directly to "we will solve this with autonomous mode" without describing how analysts cope today, what tools they lean on, or what other products they evaluate.]

*Teaching note: When the current state is missing, the PM is implicitly assuming there's nothing today — which is almost never true. Skipping this section means the team will rebuild capabilities customers already have access to, and miss the workarounds users will continue to lean on if the new feature falls short.*

### Sub-check C: Why isn't this solved already?

> What barriers prevent this from being solved today? Product gaps. Trust gaps. Skill gaps. Tech gaps. Process gaps.

**✓ Strong**

> The capability to automate response exists in this product today. Most customers don't use it. Two barriers explain why. The first is a product gap. Static playbooks break on novel signals, and attackers operate in patterns no playbook anticipates. When the playbook fails, the cost is operational, and every failure erodes trust further. The second is a trust gap, and it's the larger one. Security users are skeptical by trade. That's the job. Their mission is asymmetric: a breach is worst case, but a wrongful CEO-laptop isolation from a false-positive automation is almost as bad. They've been burned, or they've watched colleagues get burned. The cost of a mistake shows up in the post-mortem and in the analyst's career. Until both barriers are addressed together, automation stays a feature with the box checked but the toggle off.

*Teaching note: The product gap and trust gap framing is the conceptual gravity well of Area 1. A PM who reaches this depth has done the work — they've talked to customers, they understand why prior automation efforts have failed, and they know the trust gap is the bigger one. The asymmetric-cost insight (CEO-laptop equivalent to breach) is the kind of line that earns the rest of the epic.*

**⚠️ Needs work**

> Existing playbooks can automate response when the signals are clean, so customers theoretically have this capability today. They mostly don't use it. We believe better AI capabilities and improved UX will drive higher adoption.

*Teaching note: Names the symptom (low adoption of existing automation) but not the diagnosis. "Better AI and improved UX will drive higher adoption" is faith, not analysis. The skill flags: "You've named what's broken. You haven't named why. What are the actual barriers customers cite when asked why they don't automate today?"*

**✗ Missing**

> [The epic describes alert fatigue and MTTR latency as the problem without ever asking why customers haven't already addressed these with tools they already own.]

*Teaching note: When the why-not-solved diagnosis is absent, the epic implicitly assumes the problem is greenfield. It almost never is. Without diagnosing the barriers, the team will likely repeat the patterns that haven't worked, and the feature will join the long list of capabilities customers technically have access to and don't use.*

### Sub-check D: No solutioning

> Does the epic describe the problem space without prescribing implementation? Engineering must retain room to innovate.

**✓ Strong**

> Operators need a way to apply trusted response actions without remaining glued to the screen. The trade-offs across control surface, granularity, and trust mechanics are open questions for engineering and design. Possible directions worth exploring include in-line approve-to-execute panels embedded in the alert detail view, chat-driven trust grants where the user converses with the agent about what to permit, and observable agentic workflows where the agent shows its reasoning before acting. Each direction has implications for visibility, latency, and operator workflow disruption that engineering should weigh.

*Teaching note: Names the problem precisely, names the open questions, gestures at possible directions without prescribing one, and explicitly hands trade-off resolution to engineering. The PM is doing their job — naming what good looks like — and not doing engineering's job.*

**⚠️ Needs work**

> We will solve this by adding an "autonomous mode" toggle that lets the platform act on its own confidence threshold. Operators set the threshold, the playbooks, and the scope. The agent does the work.

*Teaching note: This is the synthetic epic's actual language. The PM has prescribed a UX (toggle), a control mechanism (confidence threshold), a data model (playbooks), and a scope-setting model. Engineering's room to reason is gone. The skill flags: "Reframe to leave engineering room. What's the problem the toggle is solving? Describe that, and let engineering propose the surface."*

**✗ Missing** (the most extreme case — full prescription)

> The solution is a three-panel dashboard: (1) "Active Agent Actions" showing real-time agent activity, (2) "Pending Approvals" where the analyst can click Approve or Deny, and (3) "Trust Settings" where the user configures granular permissions. Mockups attached. UX team to refine for v1, but the core IA is locked.

*Teaching note: Solutioning in its most prescriptive form: locked information architecture, named panels, attached mockups, declared "core IA." The PM has effectively designed the feature and asked engineering to build it. The skill flags: "Engineering and design have no room to innovate. The strongest version describes the user need and the trade-offs, not the IA."*

### Sub-check E: Problem scope and value framing

> Is the problem scope appropriately bounded? Is the value the work delivers — not just the symptom relieved — clearly named? Many problem domains look monolithic on the surface and decompose into very different sub-problems underneath. A coverage map is a means; a prioritized recommendation is the value.

**✓ Strong**

> This feature targets MITRE ATT&CK Enterprise specifically. We are explicitly not addressing Mobile, ICS, or Atlas in v1 — those are separate problem spaces with different data shapes, different adversary models, and different customer personas, and each deserves its own epic. Within Enterprise, we are scoping to detection-rule coverage (custom and vendor-supplied), not data-source coverage and not adversary emulation coverage. The value the customer receives is not "see a coverage map." Coverage maps are table stakes. The value is *prioritized detection investment*: given the customer's vertical (e.g., financial services), the adversary groups most likely to target them (FIN7, Carbanak, Lazarus subgroups), and the data sources they currently ingest, where should they build next? The map is the means. The prioritized recommendation is the value.

*Teaching note: Names the explicit scope boundary at two levels — which MITRE matrix (Enterprise, not Mobile/ICS/Atlas) and which coverage dimension (rules, not data-source). Distinguishes the means (a coverage view) from the value (prioritized investment by vertical and adversary group). The PM has thought about why the work matters, not just what it does. This is the highest-leverage sub-check on Area 1 because it forces the team to commit to a narrow problem space and explicit value proposition before downstream areas can be evaluated.*

**⚠️ Needs work**

> The feature covers MITRE ATT&CK. Customers get visibility into their coverage gaps so they can prioritize detection rule development.

*Teaching note: Treats "MITRE ATT&CK" as a monolithic problem domain when it isn't — there are at least five distinct matrices (Enterprise, Mobile, ICS, Atlas, Containers) with different customer relevance. And "visibility into coverage gaps" is symptom-relief framing, not value framing. The skill flags: "Which MITRE matrix are you scoping to? And what does the customer DO with visibility — what decision does the coverage data inform, what action does it drive? Visibility alone is not value. Name the scope and name the decision the work enables."*

**✗ Missing**

> [The epic does not address what specific problem space the feature targets within a broader domain, and does not articulate the value the customer gets beyond the immediate functional benefit.]

*Teaching note: When scope and value are both unaddressed, the epic is implicitly committing the team to ship something blurry. The team will spend cycles arguing about edges that should have been decided in the problem statement. The skill flags: "Name the scope explicitly — what's in v1, what's not, why. Name the value explicitly — what decision does the work let the customer make that they couldn't make before."*

### Sub-check F: Assumptions surfaced

> Does the epic name the load-bearing assumptions the problem framing depends on, and identify which are settled, which are testable, and which are open? Or are beliefs presented as facts?

**✓ Strong**

> We are assuming three things that should be tested before the team commits at scale. First: SOC operators will actually grant autonomous trust above the recommend-mode level — that the trust gradient gets used, not just configured. We have eight customer interviews that say yes; we do not have a paid pilot that proves it. Second: the operator persona we are designing for (the SOC manager who grants trust on behalf of the team) has the structural authority to do so in mid-market shops, where the role often blurs with the CISO function. Anecdotally yes, formally unclear. Third: the latency from agent decision to action is acceptable below one second and unacceptable above five. Operators have not been tested at the boundary. The first two will be validated in the design partner program. The third will be instrumented post-launch with a kill-switch if real telemetry shows the latency tolerance is tighter than we think.

*Teaching note: Names three load-bearing assumptions. Categorizes each by validation status — interviews versus paid pilot, anecdotal versus formal, untested. Names the path to confirm each. This is what assumption surfacing looks like when the PM has thought epistemically about their own work. The reader walks away knowing exactly what could break and how the team will know if it does.*

**⚠️ Needs work**

> We believe customers want autonomous response based on extensive customer interviews and our understanding of the SOC analyst workflow.

*Teaching note: "Believe" is doing the work that "test" should do. "Extensive customer interviews" is asserted, not specified (how many? what kind? with what selection bias?). "Our understanding" presents inference as data. The skill flags: "Walk this back to the assumptions the conclusion rests on. What about trust? About authority? About latency? About cost-of-mistakes? Name which are settled, which are testable, which are open — and how you'll know."*

**✗ Missing**

> [The epic does not name the assumptions the problem statement depends on. Beliefs are presented as facts; the path from research to conclusions is implicit.]

*Teaching note: A common failure mode in epics from PMs who have done their customer research but skipped the step of articulating what they assume. The skill flags: "Name the assumptions. Even one paragraph naming the three or four things that have to be true for this problem framing to hold up — and how you would know if they don't — separates a defensible epic from one that gets re-litigated mid-flight."*

### Sub-check G: Alternatives considered

> Does the epic name two or three alternative framings, scopes, or approaches the PM considered and rejected — and why? A single-path epic invites mid-flight re-litigation when stakeholders surface alternatives the PM should have surfaced.

**✓ Strong**

> We considered three alternative framings before landing on autonomous response. First: "Faster manual response" — give Tier 1 analysts a one-click incident response surface that performs the cleanup but requires confirmation. Rejected because the bottleneck is human attention, not click count. Even with optimal UX, the analyst has to read, decide, and confirm in the time window the attacker is using. Second: "Better detection so fewer alerts" — invest in detection-engine improvements to reduce false positives upstream. Rejected because the volume problem dominates the precision problem at our customers' scale. Even at 80% precision, the absolute alert count overwhelms Tier 1 capacity. Third: "AI-assisted triage without action" — recommend without acting. Rejected because operators told us the recommendation often already exists in their head; the latency they care about is between decision and action, not analysis and decision. Autonomous response is the framing that addresses the actual constraint, but each rejected alternative remains a real pivot path the team could take if pilot data invalidates current assumptions.

*Teaching note: Three named alternatives, each with rejection rationale and underlying reasoning. The closing line — that rejected alternatives remain viable pivot paths — signals the PM treats this as a working hypothesis, not a settled answer. The reader can see the option space the PM searched and where the chosen path sits within it.*

**⚠️ Needs work**

> We considered several other approaches but found autonomous response was the best path forward based on customer feedback and competitive analysis.

*Teaching note: "Several other approaches" is unspecified. "Best path forward" is conclusion-as-evidence. "Customer feedback and competitive analysis" is hand-wave. The skill flags: "Name two or three alternative framings. For each, name what you rejected and why. The point isn't to prove the chosen path right; it's to show the team the option space and what could change which way the team should go."*

**✗ Missing**

> [The epic presents one path forward as if it were the only path. No alternatives named, no rejections rationaled.]

*Teaching note: A single-path epic invites mid-flight re-litigation. When stakeholders see only one option, they often start surfacing alternatives the PM should have surfaced — and the conversation shifts from "let's ship this" to "let's reconsider the framing." The skill flags: "Name the alternatives you considered. Even three sentences naming three different paths makes the framing more defensible than the strongest single-path argument."*

### Sub-check H: Epistemic openness

> Does the epic leave explicit room for the team to learn something that changes direction? *What could you discover in the next six months that would change what you ship?*

**✓ Strong**

> Three things we don't know yet could change the shape of this. First: whether SOC operators will actually grant autonomous trust above the recommend-mode level. If design partner data shows they configure it but don't enable it, we would reframe as "better recommendation" rather than "autonomous action" and ship a simpler product. Second: whether the cross-product cascade — what happens in adjacent tools when the agent isolates a host — creates more friction than the autonomous action saves. If integration testing shows operators having to do significant manual cleanup of state in other tools, we would defer autonomous mode in favor of cleaner manual workflows. Third: whether the trust gradient is too complex for actual customer SOC teams to configure. If our design partners need more than a half-day of customer success time to configure it, we would simplify dramatically — even at the cost of granularity. Each of these would change what ships. The team should expect to learn at least one of them.

*Teaching note: Three named uncertainties, each with the specific signal that would update the framing and the specific change that signal would trigger. The closing line — "the team should expect to learn at least one of them" — is honest about the brittle nature of forward planning in product work. This is what epistemic openness looks like. It is the single biggest differentiator between a PM with strong product instinct and one with weak product instinct.*

**⚠️ Needs work**

> We will iterate based on customer feedback during the design partner program.

*Teaching note: "Iterate" is the polite word for "things will change but we have not named which things." Customer feedback is the source; the response to it is not specified. The skill flags: "What's the specific learning that would change the shape of this work? Name two or three. If you can't, the epic is either correct in every detail (unlikely) or you haven't thought through where it's brittle (common)."*

**✗ Missing**

> [The epic presents a settled plan with no acknowledgment that downstream learnings could change the framing.]

*Teaching note: A closed epic is a fragile epic. When stakeholders find ambiguity or risk that the PM hasn't surfaced, the conversation shifts from execution to re-planning — and execution time is lost. The skill flags severely: "There is no plausible discovery in the next six months that would change what you ship? That's almost never true. Name two or three things that could change the framing, and how you would know they're changing it. This isn't weakness — it's the discipline that makes the rest of the epic execute well."*

---

## Area 2 — Competitive landscape

How do leading competitors handle this problem? Is the proposed work novel, catch-up, or somewhere in between? *And — critically — what do we do differently?*

**✓ Strong**

> Three competitors define the autonomous response space and each handles it differently. **CrowdStrike Falcon's Charlotte AI** offers natural-language investigation and recommends response actions but stops short of autonomous execution for most signal classes — strong on insight, conservative on action. In the operator workflow, an analyst gets a chat-style recommendation panel they can act on manually; the autonomous-action loop isn't closed (see [CrowdStrike's Charlotte AI overview](https://www.crowdstrike.com/) for their published workflow). **SentinelOne Singularity's Storyline** auto-mitigates a narrow set of high-confidence threats (process kill, file quarantine) and emits detailed reasoning afterward — the strongest current product on operational trust, but the autonomy is signal-specific and the gradient is coarse: customers either trust the auto-mitigations or they don't, with limited per-signal tunability. **Microsoft Defender for Endpoint's Automated Investigation and Response (AIR)** is the deepest integration into the Microsoft stack and handles cleanup at scale, but the operator surface is opinionated to the M365 admin experience and difficult to adapt for non-Microsoft shops; in mid-market deployments without M365 saturation, the workflow forces operators to context-switch between AIR and their primary SIEM.
>
> Our positioning: **parity-with-twist**. We match the field on the underlying capability and lead on the **granular trust gradient** — earning trust action-by-action, signal-by-signal, with a transparency model the field treats as roadmap rather than table stakes. *Specifically, what we're betting will win:* the operator's ability to grant autonomy at the level of *"for endpoint ransomware at confidence above 0.9, isolate; for credential dumping at any confidence, show me first"* — not at the level of *"autonomous mode: on / off."* That gradient, with reasoning shown on every action and revocability per signal, is the differentiator the competitive set has structurally chosen not to ship.

*Teaching note: Three competitors named with workflow specifics — what the operator's actual experience looks like in each, not just abstract feature claims. Linked references invite the reader to verify the analysis. Strengths and weaknesses surfaced. Position claim explicit ("parity-with-twist"). The closing paragraph names — explicitly — what we're betting will win, with the specific user moment where the differentiation shows. This is the bar: a reader can finish this section and say, "I know what this team is betting on and why."*

**⚠️ Needs work**

> CrowdStrike Falcon and SentinelOne Singularity already offer autonomous response for some threat classes. Microsoft Defender for Endpoint has automated investigation and response (AIR). We are behind.

*Teaching note: From the synthetic epic. Three competitors named, but no analysis. "We are behind" is honest but it's not strategy. The skill flags: "Naming a competitor is not analysis. For each one, name how they handle it, where they're strong, where they fall short. Then state the position claim explicitly — novel, catch-up, or parity-with-twist."*

**✗ Missing**

> [The epic does not address how competitors handle this problem space. No competitor analysis is included.]

*Teaching note: Missing entirely. The PM has implicitly assumed either that the work is greenfield or that competitive context doesn't matter. Neither is usually true in B2B. The skill flags: "In a market with established competitors, an epic without competitive analysis defaults the team's positioning. Name three competitors, summarize each, position the work."*

## Area 3 — Strategic differentiation (moat)

What makes this special in your company? Why does someone get this from you rather than a competitor? Sometimes there is no moat — being explicit about that is also passing.

**✓ Strong (defensible moat named)**

> Our moat on autonomous response is the granular trust gradient. The field is converging on similar underlying capabilities — every major player can isolate hosts, kill processes, and emit forensic snapshots. What none of them have built is the operational trust surface: per-signal, per-confidence, per-identity-class trust grants with role-bounded authorization, immutable audit, and reasoning transparency on every action. This is not a feature we can build because we're smart. This is a feature we can build because we have eight years of signal data per customer and the operator workflow context to know what trust grants actually map to real-world decisions. A competitor starting today would need our customer base and our signal corpus to design the same gradient, and they don't have either.

*Teaching note: Names a specific differentiator (trust gradient design). Anchors it in something the company actually has (signal data plus operator context). Makes the moat defensible by naming what a competitor would need to replicate it. This is what a moat looks like when the PM has thought about why customers can't get this elsewhere — not by aspiration, but by accumulated structural advantage.*

**✓ Strong (no moat, explicit)**

> We do not have a moat on the underlying capability. CrowdStrike, SentinelOne, and Microsoft can all build autonomous response — they already are. We are building this work for two reasons unrelated to differentiation. First, it is table stakes for renewal in the mid-market and above; our customers will not renew the platform if their threat response stack is missing autonomous capabilities the competitors offer. Second, it gives us a credible position to ship the trust gradient (Area 9) once the underlying capability is in place — that's where we may eventually establish differentiation, but not on day one. Building this without a moat is the right call. The team should know that's what they're doing.

*Teaching note: This also passes. The PM has thought about whether there's a moat and concluded there isn't — and named the strategic reason for building anyway (renewal table stakes plus setup for future differentiation). This is the area being honest. PMs often invent moats because they feel obligated to. The skill should treat "no moat but explicit" as ✓, not as ⚠️.*

**✗ Missing**

> [The epic does not address what makes this work specially differentiated in our product, or why a customer chooses this from us versus a competitor. Differentiation is not discussed.]

*Teaching note: Missing entirely. In a competitive market, this gap is consequential — the PM is implicitly committing the team to ship a feature without a stance on why customers should adopt it from this vendor. The skill flags: "Name a defensible differentiator, or be explicit that there isn't one and the work is justified on other grounds (table stakes, defense, positioning). Don't leave this implicit."*

### The press-release test (Sub-check on outside-in framing)

> Can the PM write the press-release sentence (or short paragraph) they want to say when this ships? Forcing the customer's perspective into a quotable line surfaces what the work is actually about — not what we built, but what changed for the customer.

**✓ Strong**

> *"Today we're announcing Adversary-Informed Vulnerability Prioritization for our security platform. Where vulnerability management teams used to spend half their week reordering CVSS-sorted lists by hand against threat intel, they now open Monday morning to a queue of 20 patches their platform has already prioritized — refreshed daily with current threat intel, weighted by their actual asset criticality, and explained in language they can paste into a leadership report. Early customers report patching 40% more high-risk vulnerabilities in the same shift they used to spend triaging. The work hasn't changed. The inputs have."*

*Teaching note: Names the customer's before and after concretely. Quantifies the change. Surfaces the specific moment in the customer's week that's different. The PM has committed to a transformation, not a feature list. If a PM can write this paragraph cleanly, the value proposition is sharp. If they can't, the work isn't ready for prime time regardless of how clever the underlying tech is.*

**⚠️ Needs work**

> *"Today we're announcing Adversary-Informed Vulnerability Prioritization, our new capability for fusing threat intel with asset inventory to deliver smarter patch prioritization decisions."*

*Teaching note: Feature-talk in press-release clothing. Names what we built, not what changes for the customer. The skill flags: "Reframe in terms of what the customer experiences differently on Monday morning. What's their before/after? What's the moment they notice the change? Press releases that announce capabilities die; press releases that announce customer outcomes get quoted."*

**✗ Missing**

> [The epic does not include a press-release sentence or any outside-in customer framing. Value is described in internal terms throughout.]

*Teaching note: When the press-release test is skipped, the PM hasn't been forced into outside-in framing. The epic may have strong moat and competitive analysis but lack a sharp customer-facing value statement — which means sales, marketing, and customer success will each invent their own when the time comes, and they will not agree. The skill prompts: "Write the press release sentence. Even one sentence. If it's hard to write, the value isn't sharp enough yet — and that's information worth surfacing now, not after the team has been building for three months."*

## Area 4 — Solution approach

The HOW the team will build, with explicit choices about AI, reusability, and UI. Four sub-checks: explicit AI decision, agentic-not-static, skills-first reusability, UI restraint.

### Sub-check A: Explicit AI decision

> One of: *AI accelerated*, *AI considered and declined*, or *AI not applicable* — each with a one-line justification. Implicit AI assumptions do not pass.

**✓ Strong (AI accelerated)**

> AI accelerated. This work cannot be done well without LLM reasoning. Static rule-based matching fails the moment attackers operate in patterns outside the rule set, and they do, constantly. The LLM evaluates the signal in context (what's normal for this endpoint, this user, this time of day), reasons about candidate actions, and selects the right response from the pre-approved category. The agent's reasoning is shown to the operator before execution, except where the operator has explicitly granted autonomy for that signal class at that confidence level. AI is not an enhancement here. It is the mechanism.

*Teaching note: Declares AI as core. Justifies why (static rules fail on novel attacks). Names the LLM's specific role (evaluate context, reason, select). Names the human-on-the-loop pattern in the same breath. The PM is not hand-waving "AI-powered" — they've thought through the why.*

**✓ Strong (AI considered and declined)**

> AI considered and declined. The proposed work is a UX refinement to the existing alert detail view, surfacing existing detection metadata in a cleaner layout. The capabilities the user needs are already deterministic — confidence scores, alert categorization, MITRE technique mapping — and have been correctly classified by our detection engine for two years. Adding an LLM layer here would introduce non-determinism and latency without changing the user outcome. We are not using AI for this work, and that is the right call.

*Teaching note: This is also a passing answer. The PM has thought about AI and explicitly chosen not to use it. The reasoning is grounded (existing data is already deterministic, latency cost outweighs benefit). This is how Area 4 passes for non-AI work. The skill should treat this as ✓, not ⚠️.*

**⚠️ Needs work (AI declined for the narrow case only)**

> AI considered and declined. We evaluated whether to use LLMs to auto-classify our existing detection rules against MITRE ATT&CK techniques, but found that our static analysis of rule logic produces deterministic, auditable mappings without LLM cost or latency. AI is not the right tool for this work.

*Teaching note: This is the trickiest failure mode on Area 4 and the most common in B2B epics that touch evolving domains. The PM made an explicit decision and gave reasoning. The reasoning is even correct for the one use case considered (auto-classifying existing rules). The failure is that AI was only evaluated for that one narrow case. The PM didn't ask whether AI is valuable for related use cases the epic implies: keeping the mapping current as MITRE evolves twice a year and adds new techniques; identifying which coverage gaps are most consequential given the customer's vertical or recent threat intel; recommending which detections to build to close gaps; helping users interpret the coverage data conversationally. Any of these is a strong AI use case the decline doesn't address. The skill flags: "Strong that the decision is explicit and the reasoning is sound for the case you considered. Worth checking: did you also consider AI for (a) keeping mappings current as the domain evolves, (b) prioritizing gaps by adversary relevance to the customer's vertical, (c) recommending which detections to build, (d) conversational interpretation of the data? If you considered each and declined, name why. If you didn't consider them, the decision may need revisiting." A declined decision that names only the narrow case is incomplete.*

**⚠️ Needs work (implicit AI)**

> We'll build an AI-driven decision engine that reads detection signals, scores confidence, matches against pre-approved playbooks, and executes.

*Teaching note: From the first synthetic epic. "AI-driven" is used as adjective rather than declaration. Is this AI-accelerated? Are we using LLMs? Rule-based ML? Why this over deterministic engines? The PM has assumed AI without justifying it. The skill flags: "You've used AI as a label rather than a decision. Make the explicit choice: accelerated, considered-and-declined, or not applicable. With one line of why."*

### Sub-check B: Agentic, not static (when AI is in use)

> If AI is part of the solution, is the work agentic — *the LLM reasons the right action from the situation* — or static? Static rules and hardcoded playbooks should be flagged in any AI-driven epic; novel inputs will break them.

**✓ Strong**

> The agent reasons about each signal dynamically. Pre-approved categories of action — isolate host, terminate process, roll back file changes, collect forensic snapshot — define the bounds of what the agent may do. Within those bounds, the LLM selects the right combination based on signal context, attacker pattern, blast radius, and what the operator has pre-granted for this confidence level. Static playbook matching is the failure mode we're explicitly avoiding. When ransomware encryption fires from a service account on a domain controller versus a workstation, the right response is not the same playbook, and a static rule set cannot capture the difference at scale.

*Teaching note: Names the architectural difference (categories of action, not scripts). Names the failure mode being avoided (static playbook matching). Gives a concrete example (service account on DC vs. workstation) showing why dynamic reasoning is necessary. The PM has thought through why agentic. Without this depth, the epic risks shipping a static automation system with an AI label on it.*

**⚠️ Needs work**

> The system matches incoming signals against pre-approved playbooks. Each playbook contains a sequence of response actions optimized for a specific attack pattern. When a signal matches a playbook, the system executes the corresponding actions.

*Teaching note: This is what the synthetic epic implies. Pre-approved playbook matching is the recognized failure mode — it works on textbook attacks and breaks on everything else. The skill flags: "Static playbooks will fail on novel signals. If AI is in this solution, the LLM should reason about responses dynamically, not execute pre-written scripts. Reframe to pre-approved categories of action, not pre-approved sequences."*

### Sub-check C: Skills-first reusability

> Can the capability be exposed as a skill, an API, or an MCP tool — so it lives beyond the app's UI and can be composed into other agentic workflows? Or is this fundamentally an in-app-only feature?

**✓ Strong**

> The autonomous response capability is exposed two ways. First, inside the product as an integrated experience for analysts running the platform UI. Second, as a skill callable from any MCP-compatible client. Customers who run security operations through their own agentic workflows — increasingly common in mid-market and above — can compose this capability with their existing tools (their SIEM, their case management agent, their on-call routing) without locking into our UI. Skills-first delivery extends the addressable use cases without requiring us to build every integration ourselves.

*Teaching note: The PM has thought about reusability. The capability lives in two places. The argument for skills-first is named (customers compose their own workflows; we don't have to build every integration). This is the rare Area 4 sub-check that most epics ignore entirely, and it's the one that makes the difference between a feature locked into one tool and a capability that travels with the customer's agent stack.*

**⚠️ Needs work**

> The autonomous response capability lives in the product's web UI. Operators access it through the new Autonomous Response dashboard. API access for the capability is on the long-term roadmap but not part of this epic.

*Teaching note: The capability is locked inside one surface. Customers can only use it if they're running this product's UI — they can't compose it into their own agent workflows. "API access on the roadmap" defers reusability indefinitely. The skill flags: "Can this be exposed as a skill or MCP tool so it composes into customer workflows? Locking capability inside the app limits where users can reach it and forecloses customer-side composition that's increasingly the default in B2B."*

### Sub-check D: UI restraint

> Does the epic default to a new dashboard, page, or section before considering whether existing flows or chat-first delivery would serve the user better? *New UI is the most expensive way to deliver a capability.*

**✓ Strong**

> No new dashboard. The autonomous response capability surfaces in three existing places: the alert detail view, where the agent's reasoning and recommended actions appear inline; the analyst's chat assistant, where the user can converse with the agent about what to permit; and the existing case management workflow, where post-action records land automatically. The reason for restraint is operational. SOC analysts already navigate seven tools per shift. A new dashboard means a new place to learn, a new context to switch into, and a new surface that competes with the work the analyst actually needs to do.

*Teaching note: Names the restraint explicitly ("no new dashboard"). Names the three existing surfaces. Names the reason restraint matters (operator workflow already fragmented). The PM has thought about where users naturally live, not where engineering would find it easiest to ship. This is the highest-leverage UI decision an epic can make.*

**⚠️ Needs work**

> The UI is a new "Autonomous Response" dashboard with a real-time feed of agent actions, override controls, and post-action review.

*Teaching note: From the synthetic epic. The default is to add a new screen — a recognized failure mode in B2B contexts where users already context-switch between many tools. The skill flags: "Before adding a new dashboard, ask whether this can live in existing surfaces. New UI is the most expensive way to deliver a capability. Where would the user naturally encounter this?"*

**✗ Missing** (prescriptive new IA)

> The solution requires a three-panel dashboard with a left navigation expansion: (1) "Active Agent Actions" panel showing real-time agent activity, (2) "Pending Approvals" panel where the analyst clicks Approve or Deny, and (3) "Trust Settings" panel where the user configures granular permissions. Mockups attached. The core IA is locked for v1.

*Teaching note: Compound failure — this crosses two area lines (Area 1 D no-solutioning and Area 4 D UI restraint). The PM has not just added a new dashboard, they've prescribed its information architecture, named its panels, and attached mockups. Engineering and design have no room to innovate, and there was no consideration of whether existing surfaces could carry the capability. The skill flags both gaps and points the PM at the strong UI restraint example.*

## Area 5 — Holistic impact

The work's full scope across the product — not just the team's piece. Cross-product cascade, adjacent areas, side effects.

**✓ Strong**

> When the agent isolates a host, six things change downstream. (1) The SIEM updates the host status; an alert that depends on the host being online may suppress incorrectly without explicit logic for this case. (2) The case management tool gets a new event in the active case; the agent attaches reasoning trace and forensic snapshot. (3) The on-call rotation system suppresses subsequent alerts for the same host until manually re-enabled, to prevent alert storms from a quarantined system. (4) The identity provider's session tokens for the affected user are flagged for review but not auto-revoked (that's a separate trust grant). (5) The endpoint inventory marks the host as "isolated by agent" with traceback; this affects compliance reports that count active endpoints. (6) The customer's third-party EDR integration receives a webhook with the action context for cross-platform correlation. Each downstream change is either in scope for this epic or explicitly deferred — and the four that are deferred (identity session handling, third-party EDR webhook schema changes, compliance report logic, on-call suppression duration) have linked tickets and an owner.

*Teaching note: Six concrete downstream effects, each named, each with disposition (in scope or deferred with owner). The PM has mapped the cascade. The implicit message: when this ships, nothing will silently break in adjacent areas because every adjacency was considered. This is what holistic thinking looks like — not a paragraph of "we'll integrate" but an itemized list of what changes and who owns each.*

**⚠️ Needs work**

> The autonomous response capability will integrate with our existing alert and case management systems. Other platform components will continue to function normally.

*Teaching note: Two sentences of confident hand-waving. "Will integrate" is not a plan. "Continue to function normally" is faith. The skill flags: "Name the downstream effects. When the agent acts, what changes in the SIEM? The case management tool? The on-call rotation? The identity systems? The endpoint inventory? Each integration is either in scope or explicitly deferred — name which, and assign an owner to the deferred items."*

## Area 6 — Packaging & pricing

Tier, model fit, competitor pricing benchmarks, escalation flag.

**✓ Strong**

> Packaging: autonomous response (the full agent capability with autonomous-with-notification trust level) lives in our Enterprise tier. Recommendation and approve-to-execute trust levels are included in our Premium tier. Observation-mode and configuration view are included in all tiers, including Standard. The reason for this split: observation-mode in Standard exposes Standard customers to the capability and creates an obvious upgrade path; Premium captures the customers who want operator-supervised automation; Enterprise captures the customers who can support the operational and compliance posture autonomous action requires. Competitor pricing benchmark: CrowdStrike charges $24/endpoint/month for Falcon Insight (which includes equivalent autonomous capabilities); SentinelOne's Complete tier is $36/endpoint/month and includes Storyline auto-mitigation; Microsoft Defender for Endpoint Plan 2 is included with E5 at roughly $57/user/month all-in. Our Enterprise tier ($31/endpoint/month) prices below CrowdStrike's equivalent and gives us room to bundle the trust gradient as the headline differentiator. This packaging requires no pricing committee escalation.

*Teaching note: Names the tier split AND the reason for it (observation in Standard as upgrade lure; Premium for supervised automation; Enterprise for full autonomy). Benchmarks against three named competitors with specific prices. Names the strategic intent (price below CrowdStrike, bundle trust gradient). Explicitly notes escalation status. This is what packaging analysis looks like when the PM has talked to revenue, finance, and sales — not just defaulted to "Premium tier."*

**⚠️ Needs work**

> We'll bundle this with our Premium tier. Customers on Standard get a read-only view of agent recommendations.

*Teaching note: From the synthetic epic. Tier named but no rationale, no benchmarks, no escalation flag. The skill flags: "Tier named without reasoning. Why Premium? Are competitors at this price point? Is there an upgrade-path argument for Standard's read-only view? Add competitor pricing benchmarks and the strategic intent behind the split."*

**✗ Missing**

> [The epic does not address pricing or packaging. Tier inclusion is not specified.]

*Teaching note: Defers the conversation entirely. In B2B, packaging is a product decision that affects launch readiness, sales enablement, and adoption mechanics. The skill flags: "Pricing and packaging cannot be deferred to post-launch. Even a one-line tier decision is better than nothing. Name the tier(s), benchmark against competitors, flag if cross-functional review is needed."*

## Area 7 — Launch readiness

Documentation, field enablement, content surfaces. *The launch is not over when you ship.*

**✓ Strong**

> Launch is a marquee release tied to our Q3 product event. Documentation: full module in the product docs (concept, configuration, RBAC setup, troubleshooting), in-app help articles for each trust-level transition, and an API reference for the skills-first endpoint. Field enablement: a 90-minute sales training session (with recording) plus a customer success training session, both delivered two weeks before GA; battle cards for the three named competitors; an ROI calculator that translates MTTR improvements into avoided breach cost; and reference architecture documents for the three most common SOC deployment patterns. PLG: in-product guides at three trigger points (first alert after install, first agent recommendation, first observed signal class without an existing trust grant); contextual tooltips on the configuration view; an empty-state tour for new operators. Field content: a five-minute walkthrough video, a longer technical deep-dive video, three blog posts (one author piece, one customer success story from a design partner, one engineering deep-dive), two power-hour sessions for top-100 accounts, and a launch-week customer comms plan covering in-product banner, email to admins, and customer success outreach to top accounts. Sequencing: GA after a four-week design partner program with five named customers; tier-restricted rollout to Enterprise tier first; marquee announcement at Q3 event.

*Teaching note: Hits every category SKILL.md names (docs, field enablement, PLG, content, sequencing) with specifics. The PM has thought about who needs what to make this land. This level of detail prevents the post-launch "we shipped it but no one knows" failure mode that kills B2B feature adoption.*

**⚠️ Needs work**

> Documentation: Update product docs with a new module section. Training: Sales team training session. Marketing: Blog post at launch.

*Teaching note: From the synthetic epic. Three placeholders. Each is a category, not a plan. The skill flags: "These are categories, not commitments. Name who writes what, by when. Add field enablement beyond a single sales training (customer success, demos, calculators, battle cards). Add PLG content (in-product guides, tooltips). Add video and customer comms. Name release sequencing — marquee, quiet, or design-partner-first?"*

## Area 8 — Post-launch ownership

Telemetry, adoption mechanics, success criteria. The work after the work.

**✓ Strong**

> Success criteria: 30% of eligible Enterprise accounts have enabled at least one autonomous-action trust grant within 90 days, with 60% retention of that grant at 30 days post-enablement. Median MTTR for high-severity endpoint events drops from 8 minutes to 90 seconds in accounts with autonomous mode enabled, measured at 30, 60, and 90 days. False-positive rate on autonomous actions stays below 0.5%; above 1% triggers automatic confidence-threshold review. Telemetry: every trust grant, agent action, override, and post-action review fires a structured event consumed by the product analytics pipeline. Dashboards for product (adoption funnel by tier), customer success (per-account adoption velocity, override rate as health signal), and engineering (action latency p50/p99, model confidence calibration drift). Alerts when agent confidence drops below threshold for any signal class for 24 consecutive hours; when override rate spikes 2× week-over-week (calibration drift indicator); when audit query latency exceeds two seconds (compliance team frustration indicator). Adoption mechanics: in-product guide promoting the capability in the alert detail view; chat assistant context that suggests trying observation mode for new signal classes; customer success outreach to top-50 Enterprise accounts within first 30 days of GA; one launched-customer case study per quarter for the first year. Ownership: PM reviews dashboards weekly for first 90 days, biweekly thereafter; quarterly post-launch review with VPs at 30, 90, 180 days.

*Teaching note: Specific metric thresholds (not "adoption rate" but "30% of eligible accounts within 90 days"). Telemetry events named. Three audience-specific dashboards. Three concrete alert conditions with named triggers. Adoption mechanics across product, customer success, and content. Explicit ownership cadence. The PM has thought through what watching this feature looks like for the next year — and what would trigger action if things go sideways.*

**⚠️ Needs work**

> We'll track adoption rate of the autonomous mode toggle and reduced MTTR.

*Teaching note: From the synthetic epic. Two metric categories without thresholds, telemetry plan, adoption mechanics, or ownership. The skill flags: "Set thresholds, not categories. Name what events get logged. Name how customers will discover this. Name who watches the dashboards and how often."*

**✗ Missing**

> [The epic does not address post-launch measurement, telemetry, adoption mechanics, or ownership. Shipping is treated as the finish line.]

*Teaching note: A common B2B failure mode — the PM treats GA as the end of the work. The skill flags: "Shipping is a milestone, not a finish line. The work after the work is what determines whether the feature delivers value. Name metrics with thresholds, telemetry plan, adoption mechanics, and ownership cadence."*

## Area 9 — Trust, governance & auditability

Required for B2B features. Especially required when AI is involved. Five sub-checks: granular trust model, human-on-the-loop pattern, RBAC, audit trail, transparency.

### Sub-check A: Granular trust model

> Trust isn't binary. Customers won't toggle into "autonomous mode" wholesale. They'll grant trust action-by-action, signal-by-signal.

**✓ Strong**

> Trust is earned action-by-action, signal-by-signal. There is no single "autonomous mode" toggle. Operators grant trust at the granularity that matches their risk tolerance: "for endpoint ransomware detection at confidence above 0.9, isolate the host automatically"; "for credential dumping detection at any confidence, show me the recommended response and wait for my approval"; "for lateral movement signals from this specific user identity, never act autonomously, always alert me first." Each grant is its own decision, scoped narrowly, revocable at any time, and visible in a single configuration view. The gradient is the design.

*Teaching note: Names the failure mode being avoided (single binary toggle). Shows three concrete trust grants at different granularities — these are the kinds of customer requirements security teams actually express. The closing principle ("the gradient is the design") makes the architectural commitment explicit. PMs reading this will internalize that trust is not a toggle but a configuration surface.*

**⚠️ Needs work (binary toggle)**

> Operators enable autonomous response through a toggle in the platform settings. Once enabled, the system acts on any detection above the operator's configured confidence threshold. Operators can disable autonomous response at any time.

*Teaching note: From the synthetic epic's implied model. The toggle is binary — on or off. Customers won't accept this. High-confidence ransomware on a workstation and medium-confidence anomaly on the CEO's laptop are entirely different decisions, and they need different trust grants. The skill flags: "Binary trust does not match how security teams reason about risk. Reframe to a gradient: trust granted per signal type, per confidence level, per identity or asset class."*

### Sub-check B: Human-on-the-loop pattern

> When AI takes action, the default should be show-before-do. Autonomy is earned per signal type, with a clear progression the user controls.

**✓ Strong**

> When the agent detects a signal it could act on, the default is observation — the agent watches but does not act. The user moves the relationship along a progression that they control: observation → recommendation (the agent suggests an action, the user takes it manually) → approve-to-execute (the agent prepares the action, the user clicks approve) → autonomous-with-notification (the agent acts immediately and reports what it did). The progression is per-signal-type. A customer might be at autonomous-with-notification for endpoint ransomware and still at observation for lateral-movement detection on identity systems. The user always knows where they are in the progression. The user moves backward (less autonomy) as easily as they move forward.

*Teaching note: Names the four-stage progression and makes movement bidirectional — forward toward more autonomy and backward toward less, with equal ease. Names that the progression is per-signal-type, not global. The user is always in control of where they are. This is what "human on the loop" actually means in operational practice.*

**⚠️ Needs work**

> The system supports both manual and autonomous response modes. In manual mode, the agent makes recommendations that the user reviews and approves. In autonomous mode, the agent acts directly. Users can switch between modes at any time.

*Teaching note: Two modes. No graduation between them. No per-signal granularity. The skill flags: "Two modes is still binary. The progression should have at least four states (observe, recommend, approve-to-execute, autonomous-with-notification), and each state should be assignable per signal type. Customers don't move from manual to autonomous wholesale — they move signal-by-signal."*

### Sub-check C: RBAC / permissions

> Who in the customer org can grant trust at each level? Map to real roles.

**✓ Strong**

> Trust grants require explicit permission and are bounded by role. The SOC manager can grant trust at any level for any signal class within their organization. The Tier 2 analyst can grant trust at the recommendation and approve-to-execute levels but cannot enable autonomous response. The Tier 1 analyst can configure observation thresholds but cannot grant any execution permission. CISOs and security architects can audit and revoke any trust grant regardless of who issued it. The role mappings align with the role structure security customers already use, so configuration does not require a new role taxonomy.

*Teaching note: Maps to real customer roles (SOC manager, Tier 2, Tier 1, CISO). Names what each role can do. Notes that the design aligns with existing customer role structures, not a new taxonomy. This is what RBAC looks like when the PM has talked to security teams about their org charts and asked, "who in your shop would actually grant this?"*

**✗ Missing**

> [The epic does not mention who in the customer organization can grant trust, configure response automation, or override agent actions. Permissions are not addressed.]

*Teaching note: A common omission. PMs often defer RBAC to "later" or assume the security team will figure it out. In B2B security, the permissions story is part of the buy decision — if a CISO can't show their auditor exactly who can authorize autonomous response and how that's logged, the feature does not ship. The skill flags: "RBAC is not a launch-day afterthought. Map to roles real customers will recognize. Name who can grant trust at each level, who can revoke, who can audit."*

### Sub-check D: Audit trail

> Every action — human-approved or autonomous — produces an auditable record.

**✓ Strong**

> Every action the agent takes produces an immutable audit record. The record names the trust grant that authorized the action (with traceback to the user who issued it and when), the signal that triggered the action, the agent's reasoning trace, the action taken, the evidence collected (process tree, file hashes, network connections), and the outcome (success, partial, failed, reverted). Records are retained for the customer's full compliance retention window and exported through their existing SIEM integration. The audit trail is queryable by case number, by user, by action class, and by time range without requiring engineering involvement.

*Teaching note: Specific record fields. Retention aligned to compliance requirement. Exportable through existing SIEM integration (not requiring customers to build new pipelines). Queryable along the dimensions security teams actually query. The PM has clearly talked to compliance teams about what they need.*

**⚠️ Needs work**

> All agent actions are logged. Logs are accessible to operators through the audit log view.

*Teaching note: Vague. What gets logged? In what format? For how long? Accessible how? Searchable how? The skill flags: "Specifics required. Name the record fields, the retention window, the export path, and the query dimensions. Compliance teams will require this; the epic should describe it."*

### Sub-check E: Transparency / no silent autonomy

> The AI is never a black box. Even autonomous actions report what they did and why.

**✓ Strong**

> The agent never acts silently. Even at the autonomous-with-notification level — where the agent executes without waiting for approval — the action is reported to the operator within seconds, with the full reasoning trace attached. The trace shows the signal that triggered the agent, the candidate actions the agent considered, the action selected, why it was selected over the alternatives, and the evidence that supported each step. Operators can request post-action review, mark actions as incorrect (which trains the agent's confidence calibration), or roll back if the action supports it. The principle: AI is never a black box.

*Teaching note: Names "AI is never a black box" as the principle (echoing the skill's own philosophy). The reasoning trace structure is specific. The post-action options (review, mark incorrect, roll back) close the loop on operator trust and create a feedback path for the agent itself. The PM has thought through what transparency means operationally, not just philosophically.*

**✗ Missing (silent autonomy)**

> [The epic does not specify whether autonomous actions are surfaced to the operator in real time, whether reasoning traces are available, or whether operators can review or reverse actions after the fact. The agent's internal behavior is treated as implementation detail.]

*Teaching note: Silent autonomy is the failure mode the strong example explicitly avoids. When the epic treats agent behavior as implementation detail rather than as a transparency commitment, customers will not deploy. The skill flags severely: "This is exactly what 'AI as black box' looks like. Every autonomous action must be reported to the operator in real time, with reasoning trace attached. No silent autonomy. Ever. This is the principle that determines whether the feature deploys or gets shelved."*

---

## How to use these examples

When the skill flags a gap on a sub-check, it can reference the corresponding strong example to show what passing-grade looks like. The examples are not the only path to passing — they're calibration anchors. A PM may write something different and still pass, as long as the prose demonstrates the same depth of thinking.

When in doubt about whether an excerpt passes, ask: *would I quote this in a 1:1 to teach a junior PM what good looks like?* If yes, it passes. If no, ⚠️.

---

## Voice notes for the strong examples

The strong examples in this file deliberately read in the voice and orientation of Mike Nichols (author of *Mission Built*, second edition). Short paragraphs. Active voice. Triplet rhythms where they earn their space. The honest acknowledgment that even widely-used framings (like "alert fatigue") are imprecise. A close that names the aspiration, not just the symptom.

When teaching by example to PMs adapting this skill for their own teams, the voice should match *their* leadership voice — not Mike's. Fork these examples and rewrite them in the voice your team will recognize. Keep the structure (specificity, lived experience, diagnosis, no-solutioning); change the prose.

The voice is the lift. The structure is the lesson.
