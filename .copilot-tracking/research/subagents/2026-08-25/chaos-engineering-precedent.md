# Research: Chaos Engineering Precedent for ARISE-X "Chaos Plane" / Agent Chaos Catalog

## Scope

Validate the "Chaos Plane" and 6-level "Agent Chaos Catalog" (Infrastructure, Tool, Data,
Agent, Multi-Agent, Model) proposed in intial analysis and requirement.md against (1)
classic infrastructure chaos engineering principles and (2) emerging chaos-engineering /
fault-injection work specifically targeting LLM and agent systems.

The exact taxonomy under test (from intial analysis and requirement.md, "The Chaos Plane"
section):

* Level 1 — Infrastructure: Latency, Timeout, Packet loss, Service unavailable, Rate limiting
* Level 2 — Tool: Wrong schema, Partial response, Incorrect response, Tool unavailable, Tool version change
* Level 3 — Data: Stale data, Missing data, Contradictory data, Corrupted data, Poisoned data
* Level 4 — Agent: Planning failure, Loop, Goal drift, Context overflow, Memory corruption, Wrong tool selection
* Level 5 — Multi-Agent: Agent disagreement, Deadlock, Message loss, Conflicting objectives, Cascading failure, Malicious agent
* Level 6 — Model: Model degradation, Model migration, Model latency, Model behavior change

---

## 1. Classic Chaos Engineering Principles

### 1.1 Principles of Chaos Engineering (manifesto)

Source: https://principlesofchaos.org/ (Chaos Community manifesto, last updated 2019)

Core practice (4 steps):
1. Define steady state as a measurable output (throughput, error rate, latency percentiles).
2. Hypothesize the steady state holds for both control and experimental group.
3. Introduce variables reflecting real-world events (crashed servers, severed network
   connections, malformed responses, traffic spikes).
4. Try to disprove the hypothesis by looking for a difference in steady state between
   control and experimental groups.

Advanced principles:
* **Build a hypothesis around steady-state behavior** — focus on measurable system output, not
  internal implementation.
* **Vary real-world events** — prioritize by potential impact / estimated frequency; include
  hardware failures, software failures (malformed responses), and non-failure events (traffic
  spikes, scaling events).
* **Run experiments in production** — traffic patterns and environment differ enough that
  production is the only reliable place to validate resilience.
* **Automate experiments to run continuously** — manual chaos doesn't scale; build
  orchestration + analysis automation.
* **Minimize blast radius** — the Chaos Engineer must contain fallout; this is an explicit
  responsibility, not an afterthought.

### 1.2 Netflix Chaos Monkey / Simian Army

Source: https://github.com/Netflix/chaosmonkey

Chaos Monkey randomly terminates VM instances/containers in production to force teams to
build resilient services; explicitly cites the Principles of Chaos Engineering as its
foundation. It integrates with Spinnaker and targets infrastructure-layer failure only
(instance/container termination) — it does not model application-semantic faults.

### 1.3 Gremlin — history, principles, practice

Source: https://www.gremlin.com/community/tutorials/chaos-engineering-the-history-principles-and-practice/

Key points relevant to ARISE-X:
* Chaos experiments follow: form a hypothesis → design smallest possible experiment → measure
  impact at each step.
* Failure taxonomy grounded in the "Fallacies of Distributed Systems" (network is reliable,
  latency is zero, bandwidth is infinite, network is secure, topology doesn't change, one
  administrator, transport cost is zero, network is homogeneous) — these fallacies are the
  conceptual ancestor of "Infrastructure" fault categories (latency, packet loss, partition).
* Experiment prioritization ladder: **Known-Knowns → Known-Unknowns → Unknown-Knowns →
  Unknown-Unknowns** — a maturity model for choosing which faults to inject first. ARISE-X's
  chaos catalog does not currently reference this maturity/rollout ordering; it is a candidate
  process addition (not a new fault category) for how the Chaos Plane sequences experiments.
* Always requires a rollback/abort plan and blast-radius containment — directly parallels the
  `AbortCondition` concept later seen in the Microsoft agent-governance-toolkit (Section 2.4).

### 1.4 LitmusChaos

Source: https://litmuschaos.io/

CNCF-hosted, Kubernetes-native chaos platform. Core abstractions: ChaosHub (catalog of
experiments), Litmus Experiments (chained sequentially/parallel into scenarios), **Litmus
Probes** (used to create and verify the steady-state hypothesis close to real application
behavior), and Chaos Observability (Prometheus-based metrics/impact quantification). Notably
ships an MCP server (`litmus-mcp-server`) enabling natural-language-triggered chaos
experiments — evidence that the "chaos via conversational/agentic interface" pattern is
already emerging in the classic tooling ecosystem, not only in agent-target chaos tools.

### 1.5 Chaos Mesh

Source: https://chaos-mesh.org/docs/ and https://chaos-mesh.org/docs/basic-features/

Kubernetes CRD-based platform with three fault tiers:
* **Basic resource faults**: PodChaos (pod restart/kill), NetworkChaos (latency, packet loss,
  packet disorder, partition), DNSChaos (resolution failure, wrong IP), HTTPChaos (HTTP-layer
  latency/errors), StressChaos (CPU/memory pressure), IOChaos (I/O delay, read/write failure),
  TimeChaos (clock skew), KernelChaos (memory allocation exceptions).
* **Platform faults**: AWSChaos, GCPChaos (cloud-provider-specific node restarts, etc.).
* **Application faults**: JVMChaos (function call delay/exception injection at the application
  runtime level).

Chaos Mesh also formalizes **Chaos Workflows** — chained experiments with escalating blast
radius/failure-type breadth, matching ARISE-X's implicit need for a Chaos Plane orchestration
layer (not just single-fault injection).

### 1.6 Distilled classic taxonomy

Across all four ecosystems, classic chaos engineering fault types cluster into:
* **Resource/process faults**: instance/pod kill, resource exhaustion (CPU/memory/disk stress).
* **Network faults**: latency, packet loss/disorder, partition, DNS failure, bandwidth limits.
* **Protocol/application faults**: HTTP error injection, malformed response, JVM-level
  exception injection.
* **Platform/infrastructure-provider faults**: cloud node restarts, AZ failure.
* **Time faults**: clock skew/jump.
* **Non-failure perturbations**: traffic spikes, scaling events (explicitly called out in the
  manifesto as valid "chaos variables" — this is often missed in agent-chaos taxonomies).

This maps cleanly onto ARISE-X **Level 1 — Infrastructure** (latency, timeout, packet loss,
service unavailable, rate limiting). ARISE-X's Level 1 is a reasonable, if compressed, restatement
of the classic Chaos Mesh/Gremlin infrastructure fault set. It omits resource-exhaustion
(CPU/memory/disk stress on the serving infrastructure) and clock-skew/time faults, both
long-standing classic categories (see Section 4).

---

## 2. LLM / Agent-Specific Chaos Engineering and Fault Injection (existing work)

### 2.1 AgentChaos (2026) — closest direct precedent

Source: https://arxiv.org/abs/2608.06790 (accepted ASE 2026), code:
https://github.com/IntelligentDDS/AgentChaos

"AgentChaos: Chaos Engineering for Agent Systems via Programmatic Fault Injection" (Tan, Sun,
Shi, Zhang, He, Wu, Liang, Sun, He et al.) is explicitly framed as chaos engineering applied
to LLM agent systems. Key design:

* **Injection point**: patches the HTTP client at runtime to intercept/modify LLM API
  responses — non-intrusive, no source-code modification, works with any agent framework
  because "all agent systems access LLMs through the same HTTP interface."
* **Fault taxonomy** (adapted from classical distributed-systems fault classification): 3
  fault classes × 2 target response fields (content, tool-call) × injection strategy:
  * **Crash** → Error (server overload/5xx/rate limiting), Timeout (network congestion/API
    latency)
  * **Omission** → Empty (safety filter/content policy rejection), Truncate (token limit/TCP
    interruption/incomplete completion)
  * **Value** → Corrupt (encoding error/garbled characters), Schema (parsing error/schema
    mismatch)
  * = 6 fault types × 2 fields × 4 injection strategies + position/compound experiments = 65
    fault configurations.
* **Injection strategies**: Single (once, first match), Persistent (every matching call),
  Intermittent (probability 0.3 per call), Burst (first 3 consecutive calls).
* **Compound scenarios** (named, realistic composites): API degradation (delay→error), Content
  filter (strip tool calls + filter message), Max tokens (truncate + finish_reason=length),
  Proxy HTML (replace with HTML error page), Stale cache (replay previous response), Stale
  data (wrong tool-call arguments), Wrong entity (ambiguous tool-call arguments), Slow
  response (delay only).
* **Trigger verification**: checks execution traces post-hoc to confirm a fault was actually
  triggered, filtering untriggered tasks so fault impact isn't underestimated — a methodological
  point ARISE-X's Chaos Plane should adopt (fault injected ≠ fault triggered/observed).
* **Findings**: All tested agent systems (AutoGen, MAD, MapCoder, EvoMAC, Mini-SE) degrade
  under fault injection, pass@1 drops up to 50 points; robustness ranking is consistent across
  backbone LLMs, i.e., **robustness is a property of agent-system implementation, not model
  capability** — directly validates ARISE-X's premise that reliability engineering is a
  distinct discipline from model evaluation. Existing fault-diagnosis methods achieve <53%
  accuracy identifying fault type and <56% identifying fault step — underscoring a real gap in
  root-cause/failure-classification tooling (relevant to ARISE-X's Intelligence Plane / RCA
  ambitions).

This is the single closest academic precedent to ARISE-X's Chaos Plane concept, but it only
covers what ARISE-X calls **Level 1 (Infrastructure: timeout, rate limit) and Level 2 (Tool:
schema, partial/corrupt response)** — it operates purely at the LLM-API-response layer and
does not address Data poisoning, Agent-level planning/memory faults, Multi-Agent
coordination faults, or Model-migration faults as first-class categories.

### 2.2 Microsoft agent-governance-toolkit — Agent SRE chaos module

Source: https://deepwiki.com/microsoft/agent-governance-toolkit/6.2-chaos-engineering-and-fault-injection
(repo: https://github.com/microsoft/agent-governance-toolkit)

Ships a `ChaosEngine`/`ChaosExperiment` abstraction directly modeled on classic chaos
engineering (target, duration, abort conditions, fault list) but with **9 built-in fault
templates spanning categories ARISE-X's taxonomy does not fully cover**:
* `tool_timeout` — Tool-layer delay (maps to ARISE-X Level 2/Level 1 overlap).
* `llm_latency` — Model-layer latency (maps to ARISE-X Level 6: Model latency).
* `cost_spike` — **Cost/budget fault**: simulates expensive tool/token usage to validate
  CostGuard and per-task budget enforcement / kill-switch. **Not present in ARISE-X's 6
  levels.**
* `prompt_injection` — **Security/adversarial fault**: injects adversarial payloads to
  validate kernel-level defenses against injection. **Not present in ARISE-X's 6 levels.**
* `trust_failure` — Infrastructure/identity fault: expired/revoked credentials, tests
  token-refresh and fail-closed logic (an auth/identity fault category not explicit in
  ARISE-X Level 1).
* `policy_violation` — Governance fault: compliance-rate drop triggering circuit breaker.
* Also documents a **hallucination-injection** adversarial-rollout fault used to test canary
  rollout defenses (Agent v1 vs v2 comparison) — relevant to ARISE-X's CI/CD gate concept.

`AbortCondition` (stop experiment if `error_rate` breaches threshold) is a direct, explicit
implementation of "minimize blast radius" from the classic manifesto, and `ChaosEngine` +
`SLOEngine` + `Incident Manager` mirror the classic chaos-engineering lifecycle
(hypothesize → inject → measure → correlate → report) applied to agents. This is strong
evidence that **cost faults and security/adversarial faults are being treated as first-class
chaos categories in production-oriented agent governance tooling**, independent of ARISE-X.

### 2.3 MAST — Multi-Agent System Failure Taxonomy (empirical, non-injection)

Source: https://arxiv.org/abs/2503.13657 ("Why Do Multi-Agent LLM Systems Fail?", Cemri et
al., UC Berkeley) and https://multi-agent-systems-failure-taxonomy.github.io/MAST/

Not a fault-injection framework — an **empirically derived failure taxonomy** from 200+
annotated execution traces across 7 MAS frameworks (MetaGPT, ChatDev, HyperAgent, AppWorld,
AG2, Magentic-One, OpenManus), validated via inter-annotator agreement (Cohen's Kappa 0.88).
14 fine-grained failure modes in 3 categories:

* **FC1 — Specification Issues** (41.77% of observed failures): FM-1.1 Disobey task
  specification, FM-1.2 Disobey role specification, FM-1.3 Step repetition (loop), FM-1.4 Loss
  of conversation history (context truncation), FM-1.5 Unaware of termination conditions.
* **FC2 — Inter-Agent Misalignment** (36.94%): FM-2.1 Conversation reset, FM-2.2 Fail to ask
  for clarification, FM-2.3 Task derailment, FM-2.4 Information withholding, FM-2.5 Ignored
  other agent's input, FM-2.6 Reasoning-action mismatch.
* **FC3 — Task Verification** (21.30%): FM-3.1 Premature termination, FM-3.2 No/incomplete
  verification, FM-3.3 Incorrect verification.

Mapping to ARISE-X Level 4 (Agent) / Level 5 (Multi-Agent):
* FM-1.3 (Step repetition) ≈ ARISE-X Level 4 "Loop".
* FM-1.4 (Loss of conversation history) ≈ ARISE-X Level 4 "Context overflow" / "Memory
  corruption" — but MAST frames it as a *specification/design* failure (design decision about
  context window management), not purely an injected environmental fault.
* FM-2.3 (Task derailment) ≈ ARISE-X Level 4 "Goal drift", but MAST locates it in the
  *inter-agent* category, since derailment in MAS is often produced by agent-to-agent
  interaction, not a single agent's isolated planning failure — suggesting ARISE-X's placement
  of "Goal drift" solely in Level 4 (single-agent) may be incomplete; it also has a genuine
  multi-agent variant.
* FM-2.1 (Conversation reset), FM-2.4 (Information withholding), FM-2.5 (Ignored input), FM-2.6
  (Reasoning-action mismatch) have **no direct counterpart** in ARISE-X Level 5 (Agent
  disagreement, Deadlock, Message loss, Conflicting objectives, Cascading failure, Malicious
  agent). These are naturally-occurring coordination failure modes (not necessarily
  externally injected faults), but they are exactly the kind of failure a Multi-Agent chaos
  experiment should be able to *provoke and detect*. ARISE-X's Level 5 catalog is
  infrastructure/adversarial-flavored (deadlock, message loss, malicious agent) but under-covers
  the "soft" coordination failure modes MAST found to be the single largest observed category
  after specification issues (36.94% of all failures).
* **FC3 (Task Verification)** has no equivalent anywhere in ARISE-X's 6-level catalog. Given
  MAST found verification failures account for ~21% of MAS failures and are a distinct,
  low-correlation (0.17–0.32) category from the other two, "inadequate/incorrect
  verification" is arguably a 7th first-class fault dimension, or at minimum a required
  companion evaluation axis, not just a chaos-injection target — it is something the *agent
  under test* fails to do, which chaos engineering can provoke (e.g., by injecting subtly
  wrong tool results and checking whether the agent's own verification step catches it) but
  which isn't itself a fault category in the classic sense (it's an assurance-mechanism gap).

MAST also explicitly notes (Section 4.4, "Open Challenges Beyond Correctness") that
**efficiency, cost, robustness, scalability, and security were deliberately pruned** from
their taxonomy during refinement to keep it focused on correctness — the authors flag these
as important future work, which corroborates that a broader reliability engineering system
(like ARISE-X) needs a place for cost/robustness/security dimensions beyond MAST's scope.

### 2.4 Practitioner synthesis — "Chaos Engineering for AI Agents" (tianpan.co, Apr 2026)

Source: https://tianpan.co/blog/2026-04-12-chaos-engineering-ai-agents-injecting-failures-before-production

Argues classic chaos engineering assumptions break down for agents:
* **Idempotent retries don't apply** — retrying an LLM call after failure can produce a
  different reasoning chain/plan, not the same output with a delay.
* **Circuit breakers protect the wrong thing** — the risk isn't call volume/cascade, it's *what
  the agent decides to do* when a call fails (it improvises: hallucinates missing data,
  substitutes a wrong tool, delivers incomplete answers without flagging them).
* **Failures are semantic, not just operational** — a 500 error is easy to detect; a
  syntactically valid but factually wrong tool response or partial LLM response is not. Cites
  "ReliabilityBench" findings that semantic failures (partial responses, schema drift, stale
  data) are harder to catch and more damaging than crashes.

Proposes six failure modes to inject, useful as an independent cross-check against ARISE-X's
catalog:
1. LLM-level failures (rate limit/5xx/timeout/stream interruption/slow token delivery) — maps
   to ARISE-X Level 1/Level 6.
2. Tool call failures (API errors, timeouts, malformed responses, **data mutation** with the
   agent *not validating* tool results and treating errors as ground truth) — maps to ARISE-X
   Level 2, but foregrounds a distinct failure axis: whether the agent validates/challenges
   tool output at all, not just whether the tool output itself is malformed.
3. **Context degradation** — slow erosion of instruction-following over a long-running task
   (formal tone drifting to casual by turn 15, output constraints eroding as context window
   fills) — overlaps ARISE-X Level 4 "Context overflow" but frames it as a *gradual drift*
   phenomenon requiring long-horizon measurement, not a single injectable event, which aligns
   directly with ARISE-X's own "Long-Horizon Engine" concept.
4. Cascading failures across agent boundaries (error in agent A becomes a wrong assumption in
   agent B becomes a confident wrong recommendation in agent C) — maps to ARISE-X Level 5
   "Cascading failure", but emphasizes it is specifically the *hardest failure type to trace to
   its origin* — a diagnosability requirement for the Chaos Plane / telemetry design.
5. **Specification drift under pressure** — when a fault forces improvisation, the agent fills
   gaps with statistically likely but incorrect completions, potentially exceeding its
   authority (e.g., promising refunds it can't approve) — this is a **safety/authorization**
   failure mode triggered by chaos, distinct from "goal drift" (Level 4) because it's about
   exceeding granted authority, not just deviating from the stated goal.
6. **Silent failures** — task completes, looks plausible, raises no error, but is wrong; the
   article states chaos engineering for agents "must include semantic validation" as part of
   the experiment, not just availability/latency measurement.

### 2.5 Adjacent related work (lower relevance, cataloged for completeness)

* GoldenTransformer (https://arxiv.org/pdf/2509.10790) — hardware/bit-level fault injection
  into transformer internals (weights/activations) to study LLM resiliency to *hardware*
  faults; relevant to Level 6 "Model degradation" only in the narrow hardware-fault sense, not
  to application-level model behavior change.
* LLTFI (https://github.com/DependableSystemsLab/LLTFI) — LLVM-IR-level fault injection for
  ML frameworks (TensorFlow/PyTorch); same hardware/numerical-fault lineage as GoldenTransformer.
* "Demystifying the Resilience of LLM Inference" (ACM, quantization-related resilience study)
  — studies serving-layer resilience (e.g., GPTQ quantization) rather than agent/application
  faults.
* AWS Fault Injection Service — general-purpose cloud infra chaos tool (not agent-specific);
  confirms Level 1 (Infrastructure) fault types are well-served by existing commodity tooling
  and do not need bespoke agent-specific research.
* IEEE paper on resilience against prompt injection attacks (10487667) — frames prompt
  injection specifically as a *resilience/robustness* evaluation dimension for LLM-integrated
  applications, reinforcing that security/adversarial-prompt faults are being treated by the
  research community as legitimate resilience-testing targets, not purely a security team's
  concern.

---

## 3. Mapping: Classic Chaos Categories → Proposed 6-Level Agent Chaos Catalog

| Classic chaos category (Chaos Mesh / Gremlin / AgentChaos) | ARISE-X level | Fit |
|---|---|---|
| NetworkChaos (latency, packet loss, partition), HTTPChaos, rate limiting | Level 1 — Infrastructure | Direct, well-covered |
| StressChaos (CPU/memory), IOChaos, KernelChaos, TimeChaos (clock skew) | *(none)* | **Gap** — resource exhaustion / clock skew on the serving/agent-host infrastructure has no home in ARISE-X's catalog |
| AgentChaos Crash/Omission/Value faults on tool-call field | Level 2 — Tool | Direct, well-covered (AgentChaos's taxonomy is essentially a superset/formalization of Level 2) |
| Data-plane faults (stale/corrupt/missing, e.g., AgentChaos "stale data"/"wrong entity" compound scenarios) | Level 3 — Data | Direct; "poisoned data" (Level 3) additionally maps to security/adversarial data-poisoning literature, not just classic chaos |
| MAST FM-1.3 (step repetition/loop), FM-1.4 (context loss) | Level 4 — Agent (Loop, Context overflow) | Direct, but MAST treats these as *design* failures discoverable via trace analysis, not only externally injectable faults — ARISE-X should treat Level 4 partly as "provoke-and-observe" rather than pure injection |
| MAST FC3 Task Verification (premature termination, no/incorrect verification) | *(none — closest: Level 4 "Planning failure")* | **Gap** — verification/self-checking failure is a distinct, empirically large (21%) failure category with no explicit Level 4 sub-type |
| MAST FC2 (conversation reset, information withholding, ignored input, reasoning-action mismatch) | Level 5 — Multi-Agent | Partially covered; ARISE-X Level 5 items (disagreement, deadlock, message loss, conflicting objectives, cascading failure, malicious agent) skew toward infra/adversarial framing and miss the "soft" coordination failures MAST found most common |
| agent-governance-toolkit `trust_failure` (expired/revoked credentials) | Level 1 or Level 5 (ambiguous) | **Partial gap** — identity/credential faults for agent-to-agent or agent-to-tool auth aren't explicit anywhere |
| agent-governance-toolkit `cost_spike` | *(none)* | **Gap** — no cost-fault category |
| agent-governance-toolkit `prompt_injection`, IEEE prompt-injection resilience paper | *(none)* | **Gap** — no adversarial/security fault category |
| GoldenTransformer / LLTFI (hardware bit-flip faults) | Level 6 — Model (Model degradation, narrowly) | Loosely related; ARISE-X's "Model degradation/migration/behavior change" is really about *version/deployment* drift, not hardware fault injection — different mechanism, same rough label |
| tianpan.co "specification drift under pressure" (agent exceeds authority under stress) | *(none — adjacent to Level 4 "Goal drift")* | **Gap** — authorization/safety-boundary violation under fault-induced improvisation is distinct from goal drift |
| tianpan.co "silent failures" (semantic correctness failure with no operational signal) | *(cross-cutting, not a level)* | **Gap in methodology, not taxonomy** — every level needs a semantic-correctness check, not just availability/latency measurement |

---

## 4. Gaps and Recommended Additions

1. **No cost/budget fault category.** Both the Microsoft agent-governance-toolkit
   (`cost_spike`) and ARISE-X's own requirement document (elsewhere in the same file, "Cost
   Efficiency" is listed as a Long-Horizon Engine metric, and "Cost" appears in the Agent
   Reliability Vector) treat cost as a first-class reliability dimension, yet the Chaos Plane
   taxonomy has no corresponding fault (e.g., token-price spike, quota exhaustion mid-task,
   forced expensive-model fallback). Recommend adding cost-based faults, either as a 7th level
   or as a cross-cutting fault dimension applied within existing levels (e.g., "Model: cost
   spike", "Tool: metered/expensive-call throttling").

2. **No security/adversarial fault category (prompt injection, malicious tool output,
   data poisoning as an attack rather than as accidental corruption).** ARISE-X's Level 3
   already includes "Poisoned data," but that is the only adversarial fault in the whole
   catalog, and it is filed under Data rather than treated as a distinct security dimension.
   The Microsoft toolkit's `prompt_injection` fault template and the IEEE resilience-against-
   prompt-injection framework both treat adversarial input as a resilience-testing target in
   its own right. Recommend either promoting "adversarial/security faults" (prompt injection,
   tool-response injection, malicious agent payloads, jailbreak attempts) to an explicit
   sub-category spanning Tool/Data/Multi-Agent, or adding a 7th catalog level.

3. **No human-in-the-loop fault category.** Neither classic chaos engineering nor most
   agent-chaos literature reviewed here treats human approval/escalation steps as an
   injectable fault surface, but ARISE-X's own architecture implies human escalation exists
   (see "Human escalation: 5%" in the Agent Fingerprint example in the requirement doc).
   Faults such as delayed human approval, incorrect human input, human unavailability, or
   escalation-channel failure are absent from the 6-level catalog. This is a genuine gap
   relative to production agent systems that mix autonomous and human-gated steps.

4. **Task-verification / self-checking failure is under-represented.** MAST found
   verification failures (premature termination, no/incomplete verification, incorrect
   verification) to be a large (21.3%), statistically distinct failure category, but ARISE-X's
   Level 4 only lists "Planning failure" as a loosely adjacent item. Recommend either adding
   an explicit "Verification failure" fault type to Level 4 (e.g., "skips/short-circuits
   self-check", "accepts invalid output as valid") or treating it as a required evaluation
   probe applied across all six levels (i.e., every injected fault experiment should also
   measure whether the agent's own verification/guardrail step caught the induced problem).

5. **Resource exhaustion and clock/time faults are missing from Level 1.** Every classic
   chaos platform reviewed (Chaos Mesh: StressChaos/IOChaos/KernelChaos/TimeChaos; Gremlin:
   CPU/memory/disk attacks) includes resource-exhaustion and time-skew fault types alongside
   network/latency faults. ARISE-X's Level 1 list (Latency, Timeout, Packet loss, Service
   unavailable, Rate limiting) omits CPU/memory/disk pressure on the agent runtime or
   supporting infrastructure (vector DB, orchestrator) and clock skew — both are
   well-established classic categories with plausible agent-relevant impact (e.g., timestamp-
   dependent tool calls, session-expiry logic).

6. **Multi-Agent level under-covers "soft" coordination failures found empirically to be
   common.** MAST's FC2 category (conversation reset, failure to ask for clarification,
   information withholding, ignoring other agents' input, reasoning-action mismatch) is the
   second-largest failure category observed (36.94%) in real MAS traces, yet ARISE-X's Level 5
   list (disagreement, deadlock, message loss, conflicting objectives, cascading failure,
   malicious agent) is weighted toward infrastructure/adversarial-style faults and does not
   include information-withholding, unrequested-clarification, or reasoning-action-mismatch as
   injectable/observable fault targets. Recommend enriching Level 5 with MAST-derived
   coordination-failure probes (can be operationalized as chaos *provocations*, e.g.,
   deliberately give one sub-agent incomplete information to see whether it withholds/asks/
   fabricates).

7. **Level 6 (Model) conflates two different fault mechanisms.** "Model degradation" /
   "Model latency" describe the model *as a black box responding differently or slower* (well
   covered by AgentChaos's Crash/Omission/Value taxonomy at the API layer), whereas "Model
   migration" / "Model behavior change" describe *version/deployment* drift, which is a
   change-management concern closer to canary-rollout/regression testing (see the Microsoft
   toolkit's `CanaryRollout` chaos pattern) than to runtime fault injection. This is not
   necessarily wrong, but worth flagging: Level 6 may need to be split conceptually into
   "runtime model faults" (inject via HTTP layer, same mechanism as Level 1/2) versus "model
   change events" (deliberately swap model version/prompt/weights between control and
   experimental runs, closer to A/B regression testing than fault injection).

---

## 5. Assessment Summary (for main response)

* The 6-level taxonomy is a **reasonable and largely sound first-generation catalog**,
  directly consistent with the one existing close academic precedent (AgentChaos, ASE 2026)
  for Levels 1–2, and broadly consistent with empirical MAS failure research (MAST) for
  Levels 4–5, though MAST's empirical failure distribution suggests different emphasis within
  those levels than currently listed.
* It is **not complete** relative to (a) classic chaos-engineering practice, which always
  includes resource-exhaustion and time faults, and (b) contemporary agent-governance/chaos
  tooling, which treats cost and security/adversarial faults as first-class categories
  alongside infrastructure/tool/data faults.
* The most defensible near-term action is not to abandon the 6-level structure (it maps well
  onto agent system architecture: infra → tool → data → single agent → multi-agent → model)
  but to (a) fill in the missing sub-types identified above within existing levels where they
  fit naturally (resource/time faults → Level 1; verification failures → Level 4; soft
  coordination failures → Level 5) and (b) decide explicitly whether cost, security/adversarial,
  and human-in-the-loop faults deserve a 7th+ level or a cross-cutting fault dimension applied
  across all six levels, since none of the three fit cleanly inside the existing per-layer
  structure.

---

## Sources

* https://principlesofchaos.org/
* https://github.com/Netflix/chaosmonkey
* https://www.gremlin.com/community/tutorials/chaos-engineering-the-history-principles-and-practice/
* https://litmuschaos.io/
* https://chaos-mesh.org/docs/
* https://chaos-mesh.org/docs/basic-features/
* https://arxiv.org/abs/2608.06790 (AgentChaos, ASE 2026)
* https://github.com/IntelligentDDS/AgentChaos
* https://arxiv.org/abs/2503.13657 / https://arxiv.org/html/2503.13657v2 (MAST, "Why Do
  Multi-Agent LLM Systems Fail?")
* https://multi-agent-systems-failure-taxonomy.github.io/MAST/
* https://deepwiki.com/microsoft/agent-governance-toolkit/6.2-chaos-engineering-and-fault-injection
  (https://github.com/microsoft/agent-governance-toolkit)
* https://tianpan.co/blog/2026-04-12-chaos-engineering-ai-agents-injecting-failures-before-production
* https://arxiv.org/pdf/2509.10790 (GoldenTransformer)
* https://github.com/DependableSystemsLab/LLTFI
* https://ieeexplore.ieee.org/document/10487667 (resilience against prompt injection)
* https://aws.amazon.com/fis/ (AWS Fault Injection Service, general infra chaos baseline)

---

## Recommended Follow-On Research (not completed this session)

* [ ] Fetch and review the Microsoft `agent-governance-toolkit` `agent-sre/README.md` in full
  (only excerpts were available via DeepWiki) to get exact fault-template parameter schemas.
* [ ] Investigate "ReliabilityBench" (cited by tianpan.co but not independently located/verified
  in this session) as a possible additional benchmark precedent for semantic-failure
  measurement.
* [ ] Check `github.com/deepankarm/agent-chaos` (referenced in tianpan.co's citation list but
  not fetched) — appears to be a second, possibly independent, open-source agent chaos tool.
* [ ] Review arxiv 2601.06112, 2505.03096, 2511.07865 (cited by tianpan.co, not fetched in this
  session) for additional agent-fault-taxonomy or resilience-benchmark evidence.
* [ ] Investigate cost-fault and human-in-the-loop fault precedents more directly (this
  session found them only as single data points in the Microsoft toolkit and inferred from
  ARISE-X's own document, not from dedicated literature).

## Clarifying Questions

* Should cost-based faults and security/adversarial faults become a 7th+ Chaos Catalog level,
  or be modeled as a cross-cutting "fault dimension" applied within each of the existing six
  levels (e.g., every level can have a "cost" and "adversarial" variant)? This affects the
  Chaos Plane's schema design.
* Does ARISE-X intend the Chaos Plane to only *inject* faults (like AgentChaos, at the
  HTTP/API boundary) or also to *provoke-and-observe* naturally-occurring coordination failures
  identified by MAST (e.g., deliberately withholding information from one sub-agent to see if
  it asks for clarification)? The two require different instrumentation (fault injection
  wrapper vs. scenario/environment design).
