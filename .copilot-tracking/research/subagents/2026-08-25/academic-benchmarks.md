# Subagent Research: Academic Benchmarks for Long-Horizon, Tool-Use, and Multi-Agent AI Systems

## Research Topics / Questions

1. tau-bench (Sierra) — long-horizon tool-use agent benchmark, policy compliance metrics.
2. AgentBench — multi-environment agent benchmark dimensions.
3. GAIA benchmark — general AI assistants, task complexity levels.
4. WebArena / VisualWebArena — long-horizon web agent tasks, trajectory evaluation methodology.
5. ToolBench / API-Bank — tool-use evaluation.
6. Papers on agent reliability, agent trustworthiness scoring, LLM agent robustness to environment
   perturbation, agent behavioral drift, chaos engineering for LLM agents.
7. Papers on multi-agent coordination metrics/scoring (MultiAgentBench, coordination failure
   taxonomies).

For each: metrics defined, whether faults/perturbations are injected, trajectory-level vs.
final-answer-only evaluation, and comparison to ARISE-X proposed metrics (Goal Success,
Resilience, Behavioral Stability Index, Recovery, Efficiency, Autonomy Efficiency Score,
Multi-Agent Coordination Score, composite multiplicative Agent Reliability Index — see
"intial analysis and requirement.md" lines 459-655 for full ARISE-X metric definitions).

## Status: Complete

## Findings

### 1. tau-bench (Sierra) — τ-bench

- Source: Yao, Shinn, Razavi, Narasimhan. "τ-bench: A Benchmark for Tool-Agent-User Interaction
  in Real-World Domains." arXiv:2406.12045 (2024). https://arxiv.org/abs/2406.12045
  Code: https://github.com/sierra-research/tau-bench
  Successor: τ²-bench (arXiv:2506.07982, dual-control/conversational), now τ³-bench
  (https://github.com/sierra-research/tau2-bench, adds a `banking` domain and voice modality).
- Domain: emulates dynamic multi-turn conversations between a simulated user (LLM) and a language
  agent equipped with domain-specific API tools and written policy/guideline documents (airline,
  retail domains).
- Metrics:
  - Primary correctness metric compares the **database end-state** after the conversation against
    an annotated goal state (state-based, not text-similarity-based grading) — a form of
    trajectory/outcome verification rather than pure final-text-answer grading.
  - **pass^k**: a novel reliability metric — the probability that all k independent trials of the
    same task succeed. This explicitly targets consistency/reliability of agent behavior across
    repeated attempts, not just single-run success rate. Best models achieve <50% task success and
    pass^8 <25% on retail, showing sharp reliability decay as k increases.
  - Auto error identification tool: classifies failures by **fault assignment** (user, agent,
    environment) and **fault type** (goal_partially_completed, used_wrong_tool,
    used_wrong_tool_argument, took_unintended_action) — a lightweight failure taxonomy similar in
    spirit to ARISE-X's chaos/failure catalog.
  - Policy compliance is implicit: the agent must follow domain policy documents (e.g., refund
    rules) and the state-based grading penalizes policy-violating actions that changed the DB
    incorrectly, but there is no separate "policy compliance score" distinct from goal success.
- Fault/perturbation injection: **No deliberate environment chaos injection.** The main stressor is
  a simulated *user* (which can be adversarial/confused via different user strategies: llm, react,
  verify, reflection) rather than injected tool/data faults. This is a difference from ARISE-X's
  Chaos Plane, which explicitly injects tool/data/model/agent faults.
- Trajectory vs. final-answer: Uses **end-state equivalence** (final DB state) rather than raw
  final textual answer, which is closer to "goal achievement" than full trajectory-level behavior
  scoring (no explicit path-efficiency, recovery-time, or step-count metrics in the core benchmark).
  pass^k is a trajectory-set-level reliability signal (multiple independent trajectories), not a
  within-trajectory behavioral metric.

### 2. AgentBench

- Source: Liu et al. "AgentBench: Evaluating LLMs as Agents." ICLR 2024. arXiv:2308.03688.
  https://arxiv.org/abs/2308.03688 Code: https://github.com/THUDM/AgentBench
- Domain: multi-dimensional benchmark spanning **8 distinct interactive environments** (e.g.,
  OS, Database, Knowledge Graph, Digital Card Game, Lateral Thinking Puzzles, House-Holding
  (ALFWorld), Web Shopping, Web Browsing) to assess reasoning and decision-making of LLMs acting
  as agents.
- Metrics: primarily **task success / reward per environment**, aggregated into an overall score
  across environments. The paper's main analytic contribution is a **qualitative failure-mode
  taxonomy** (poor long-term reasoning, poor decision-making, weak instruction-following as the
  main causes of agent failure) rather than a formal composite reliability index. No explicit
  resilience/recovery/behavioral-stability sub-metrics are defined; the benchmark is a snapshot,
  single-run evaluation per task/environment.
- Fault/perturbation injection: **None** — environments are fixed/deterministic simulators; no
  chaos or noise injection is part of the benchmark design.
- Trajectory vs. final-answer: Interactive multi-round environments are used (so agents act over
  multiple turns), but grading is by final task success/reward per episode; no formal
  trajectory-level metrics (path efficiency, plan-change count, etc.) are reported in the paper.

### 3. GAIA benchmark

- Source: Mialon, Fourrier, Swift, Wolf, LeCun, Scialom. "GAIA: a benchmark for General AI
  Assistants." arXiv:2311.12983 (2023). https://arxiv.org/abs/2311.12983
  Leaderboard: https://huggingface.co/gaia-benchmark
- Domain: 466 real-world questions requiring reasoning, multi-modality handling, web browsing, and
  tool use, that are "conceptually simple for humans yet challenging for AI" (humans 92% vs. GPT-4
  + plugins 15% at publication).
- Metrics: **Final-answer exact-match / accuracy only.** GAIA questions are designed with a single
  unambiguous, easily verifiable answer, explicitly to keep grading simple and non-fuzzy. It does
  **not** score trajectories, tool-call efficiency, or recovery.
- Task complexity levels: GAIA defines **3 difficulty levels** based on the number of reasoning
  steps and tools/skills required to answer (Level 1 = simplest/fewest steps and tools; Level 3 =
  requires long sequences of actions, multiple tool types, and robust multi-step planning). This
  is the closest analog in GAIA to "long-horizon" grading, but it is a static task-difficulty
  label, not a runtime trajectory measurement.
- Fault/perturbation injection: **None.**
- Trajectory vs. final-answer: **Final-answer only.** GAIA is explicitly the "final answer,
  fully automated grading" end of the spectrum — the opposite pole from ARISE-X's trajectory-level
  philosophy.

### 4. WebArena / VisualWebArena

- WebArena: Zhou et al. "WebArena: A Realistic Web Environment for Building Autonomous Agents."
  arXiv:2307.13854 (NeurIPS 2024 Oral). https://arxiv.org/abs/2307.13854, https://webarena.dev/
- VisualWebArena: Koh et al. "VisualWebArena: Evaluating Multimodal Agents on Realistic Visual Web
  Tasks." ACL 2024. arXiv:2401.13649. https://arxiv.org/abs/2401.13649, https://jykoh.com/vwa
- Related follow-ons from the same project family (webarena.dev): **WebArena-Infinity**
  ("continuous and scalable web agent evaluation in evolving environments" — directly relevant to
  behavioral drift/continuous monitoring) and **TheAgentCompany** (ICML 2025 — long-horizon agent
  tasks in a simulated company).
- Domain: fully functional, self-hosted websites across four domains (e-commerce, social forum,
  collaborative software dev, content management), enriched with tools (maps) and knowledge bases
  (manuals), designed for **long-horizon, realistic, internet-style tasks**.
- Metrics: grading is by **functional correctness of the end task outcome** (programmatic checks
  against the resulting web/application state — e.g., correct DB record, correct posted content),
  not by string-matching a final text answer, and not by a full trajectory-level rubric. Best GPT-4
  agent achieved 14.41% end-to-end success vs. 78.24% human performance, illustrating the gap on
  long-horizon tasks.
- Fault/perturbation injection: **No adversarial/chaos fault injection** in the base benchmark;
  environments are realistic but static/deterministic. VisualWebArena adds the multimodal
  (visually grounded) dimension but keeps the same success-based grading approach.
- Trajectory vs. final-answer: **Outcome/end-state based**, similar to tau-bench and WebArena's own
  successor work — richer than pure text-answer grading (because it requires actually manipulating
  a live web app across many steps) but not a first-class trajectory-behavior scoring scheme (no
  official path-efficiency / recovery / stability sub-scores).

### 5. ToolBench / ToolLLM and API-Bank

- ToolBench / ToolLLM: Qin et al. "ToolLLM: Facilitating Large Language Models to Master 16000+
  Real-world APIs." arXiv:2307.16789. https://arxiv.org/abs/2307.16789
  - ToolBench: instruction-tuning + evaluation dataset built from 16,464 real RESTful APIs (49
    categories, RapidAPI Hub), covering single-tool and multi-tool (tool-chain) scenarios, with
    solution paths generated via a DFS-based decision-tree search (DFSDT) to allow backtracking.
  - **ToolEval**: automatic evaluator with two primary metrics — **Pass Rate** (whether the model
    completes the instruction within a limited number of steps) and **Win Rate** (pairwise
    preference comparison of one model's solution path vs. a reference, judged by an LLM on
    criteria like whether it accomplishes the task, quality/succinctness of the path). Win Rate is
    the closest published precedent to "path/behavioral quality" scoring, but it is a relative
    (pairwise) LLM-judged score, not an absolute trajectory-efficiency metric.
  - Fault injection: none — real RapidAPI calls can fail at runtime (rate limits, downtime) but
    this is incidental infra noise, not designed chaos.
  - Trajectory vs. final-answer: Partial trajectory awareness (DFSDT allows exploring/backtracking
    over multiple candidate paths; Win Rate judges the *path*, not just the final text), but no
    quantitative step-count/cost/recovery metrics are defined.
- API-Bank: Li et al. "API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs." EMNLP 2023.
  arXiv:2304.08244. https://arxiv.org/abs/2304.08244
  - Domain: 73 runnable API tools; 314 annotated multi-turn tool-use dialogues (753 API calls)
    testing **planning, retrieval, and calling** of APIs.
  - Metrics: accuracy of correctly identifying when/which API to call and correctness of the API
    call parameters/response handling — essentially step-level tool-selection and
    argument-correctness accuracy, plus overall dialogue completion. No resilience/recovery
    metrics; a "runnable evaluation system" gives closer-to-execution grading than static QA.
  - Fault/perturbation injection: **None.**
  - Trajectory vs. final-answer: **Step-level metrics** (each API call judged), which is more
    granular than "final answer only" but still short of full behavioral/efficiency scoring.

### 6. Agent reliability, trustworthiness, robustness-to-perturbation, behavioral drift, and chaos
   engineering for LLM agents

This is the richest and most directly relevant cluster for ARISE-X. Findings grouped by theme:

**a) Chaos engineering explicitly applied to LLM agents/multi-agent systems** (arXiv search
"chaos engineering LLM agent" returned exactly 6 hits total — this remains a small, emerging
niche, which is notable in itself):

- **AgentChaos** — Tan et al., "AgentChaos: Chaos Engineering for Agent Systems via Programmatic
  Fault Injection," ASE 2026. arXiv:2608.06790. https://arxiv.org/abs/2608.06790
  - Directly analogous to ARISE-X's Chaos Plane. Injects **crash, omission, and value faults** on
    LLM API content and tool-call fields at the shared HTTP layer (no source modification needed),
    verifies each fault actually triggered (to avoid underestimating impact — a methodological
    point ARISE-X should adopt), and evaluates across agent systems/benchmarks/backbone LLMs under
    65 fault configurations.
  - Metric: **pass@1 degradation** under fault injection (drops up to 50 percentage points).
    Finds robustness ranking is **consistent across models** — i.e., robustness is a property of
    system *implementation*, not the underlying LLM's capability. This is strong external evidence
    supporting ARISE-X's core thesis that agent reliability is architecturally determined, separate
    from raw model quality.
  - Also studies automated **fault diagnosis** (attributing failures to fault type/step) —
    accuracy is low (<53% fault-type, <56% fault-step), showing automatic root-cause analysis (an
    ARISE-X Intelligence Plane goal) is still an open, hard problem.
- **ReliabilityBench** — Gupta, "ReliabilityBench: Evaluating LLM Agent Reliability Under
  Production-Like Stress Conditions," arXiv:2601.06112. https://arxiv.org/abs/2601.06112
  - This is the single closest academic precedent to ARISE-X's overall approach found in this
    research. Defines a **unified reliability surface R(k, ε, λ)** across three axes:
    (i) **consistency under repeated execution** via **pass^k** (same metric family as tau-bench),
    (ii) **robustness to semantically-equivalent task perturbations** at intensity ε, and
    (iii) **fault tolerance under controlled tool/API failures** (timeouts, rate limits, partial
    responses, schema drift) at intensity λ — a chaos-engineering-style fault injector.
  - Introduces **"action metamorphic relations"**: correctness is defined via **end-state
    equivalence** rather than text similarity — directly analogous to ARISE-X's "Goal
    Preservation"/"State Consistency" concept and to tau-bench/WebArena's outcome-state grading.
  - Empirical finding: perturbations alone reduced success from 96.9% (ε=0) to 88.1% (ε=0.2); rate
    limiting was the most damaging fault type; agent *architecture* (ReAct vs. Reflexion) mattered
    more than which model backed it — reinforcing AgentChaos's finding above.
  - This paper is essentially a peer/precursor to ARISE-X's Resilience + Efficiency + Recovery
    axes, but scoped to a single quantitative "reliability surface" rather than a full
    multi-dimensional vector + composite index.
- **Assessing and Enhancing the Robustness of LLM-based Multi-Agent Systems Through Chaos
  Engineering** — Owotogbe, arXiv:2505.03096. https://arxiv.org/abs/2505.03096
  - Proposes a chaos-engineering framework specifically for **LLM-MAS** to proactively surface
    vulnerabilities from hallucinations, agent failures, and inter-agent communication failures,
    and to "assess and build resilience" — conceptually a near-exact one-paper precedent for
    ARISE-X's "Level 5 — Multi-Agent" chaos taxonomy (disagreement, deadlock, message loss,
    conflicting objectives, cascading failure). Abstract-level description; limited public detail
    on concrete metrics beyond framing "resilience."
- **ChaosEater** / **LLM-Powered Fully Automated Chaos Engineering** — Kikuta, Ikeuchi, Tajiri.
  arXiv:2501.11107 and arXiv:2511.07865 (ASE 2025 NIER). These use LLMs *to perform* chaos
  engineering on general software systems (not LLM agents themselves) — relevant as prior art on
  "LLM-driven chaos engineering tooling" but not on agent-reliability metrics per se.
- **AgentNoiseBench** — Wang et al., arXiv:2602.11348. https://arxiv.org/abs/2602.11348
  - Directly relevant to "LLM agent robustness to environment perturbation." Introduces an
    automated pipeline that injects **controllable noise** into existing agent benchmarks while
    preserving task solvability, split into **user-noise** and **tool-noise** categories. Finds
    consistent, model-independent performance degradation under noise — reinforcing that
    perturbation robustness is a distinct axis from raw capability, matching ARISE-X's premise that
    Resilience ≠ Goal Success.
- **"Learning to Act under Noise: Enhancing Agent Robustness via Noisy Environments"** — Chen et
  al., arXiv:2605.27209. A training-side response to the same problem (improving robustness rather
  than only measuring it) — relevant as a complementary "remediation" angle to ARISE-X's
  diagnose/remediate loop.

**b) Agent behavioral drift**

- **"How is ChatGPT's behavior changing over time?"** — Chen, Zaharia, Zou. arXiv:2307.09009.
  https://arxiv.org/abs/2307.09009
  - Landmark empirical study showing GPT-3.5/GPT-4 accuracy and behavior shifted substantially
    (in some cases regressed) between March 2023 and June 2023 snapshots across math, sensitive
    Q&A, opinion surveys, multi-hop QA, code generation, medical licensing, and visual reasoning
    tasks — with instruction-following ability identified as a common underlying driver of drift.
    This is the most-cited direct precedent for "model behavior drift over time" and validates
    ARISE-X's premise that "Model change" is a first-class drift trigger requiring continuous
    monitoring — but it measures **task accuracy drift for a raw LLM**, not an **agent's full
    behavioral fingerprint** (tool-selection distribution, step count, recovery rate, escalation
    rate) as ARISE-X proposes. No agent-specific behavioral-fingerprint paper with that exact
    multi-signal composition was found; ARISE-X's fingerprint concept (tool-mix %, avg steps,
    recovery rate, escalation rate, goal deviation, cost/task, tracked over time) appears **novel**
    in its specific combination, though each individual signal has precedent elsewhere (see below).
- Recent related work (2026, via arXiv search, indicating an active but still nascent area):
  "A Graph-Based Reinforcement Learning Framework for Structured Drift Diagnosis and Recovery in
  Autonomous LLM Agents" (arXiv:2608.14109) and "Measuring What Persists: Conditioning Mechanisms
  and a Geometric Framework for AI Agent Identity" (arXiv:2606.21843) — both target
  agent-level behavioral/identity drift detection and recovery, confirming the space is emerging
  but fragmented, with no single dominant "behavioral fingerprint" standard yet.

**c) Agent trustworthiness / safety-risk scoring**

- **R-Judge** — Yuan et al., "R-Judge: Benchmarking Safety Risk Awareness for LLM Agents," EMNLP
  Findings 2024. arXiv:2401.10019. https://arxiv.org/abs/2401.10019
  - 569 multi-turn agent interaction records across 27 risk scenarios / 5 categories / 10 risk
    types, with annotated safety labels. Measures whether an LLM-as-judge can **identify** risk in
    an agent trajectory (best model 74.42% accuracy) — a "safety/trust judge" benchmark rather than
    a live agent-performance metric. Relevant to ARISE-X's "Safety" dimension in its Reliability
    Vector R = {GoalSuccess, Resilience, BehavioralStability, Recovery, Safety, Efficiency, Cost,
    Autonomy}.
- **AgentHarm** — Andriushchenko et al., ICLR 2025. arXiv:2410.09024.
  https://arxiv.org/abs/2410.09024 — measures whether jailbroken agents both (a) comply with
  malicious multi-step tasks and (b) *retain task capability* after an attack; relevant precedent
  for "does robustness/resilience trade off against safety" style composite reasoning, but focused
  on adversarial harm, not general operational reliability.
- **ToolEmu** — Ruan et al., "Identifying the Risks of LM Agents with an LM-Emulated Sandbox."
  arXiv:2309.15817. https://arxiv.org/abs/2309.15817 — LM-emulated tool sandbox + automatic safety
  evaluator that quantifies risk severity of agent failures (even the safest agent fails 23.9% of
  the time). Relevant as a scalable alternative to ARISE-X's "Digital Twin / Synthetic world"
  simulation plane, and as another precedent for automatically scored trust/safety.

**d) General multi-metric ("no single score") evaluation critique — relevant to ARISE-X's
   composite ARI**

- **HELM** — Liang, Bommasani et al., "Holistic Evaluation of Language Models." TMLR 2023.
  arXiv:2211.09110. https://arxiv.org/abs/2211.09110 — explicitly measures 7 orthogonal metrics
  (accuracy, calibration, robustness, fairness, bias, toxicity, efficiency) per scenario and
  deliberately avoids collapsing them into one score, "to ensure metrics beyond accuracy don't fall
  to the wayside, and that trade-offs are clearly exposed." This is the standard-bearer counter
  philosophy to ARISE-X's ARI: HELM's stance is that composite/aggregate scores hide trade-offs,
  which is the same concern ARISE-X's own document raises informally ("I'd avoid a single
  simplistic score initially... Create a vector").
- **Underspecification** — D'Amour et al., "Underspecification Presents Challenges for Credibility
  in Modern Machine Learning." arXiv:2011.03395. https://arxiv.org/abs/2011.03395 — shows that
  models with equivalent held-out/benchmark performance can behave arbitrarily differently after
  deployment-domain shift; supports ARISE-X's premise that "Goal Success in test conditions"
  under-specifies real-world reliability and that stress/shift testing (chaos, drift) is required
  to distinguish genuinely robust agents from ones that merely score well in-distribution.

### 7. Multi-agent coordination metrics / failure taxonomies

- **MultiAgentBench** — Zhu et al., "MultiAgentBench: Evaluating the Collaboration and Competition
  of LLM Agents." arXiv:2503.01935. https://arxiv.org/abs/2503.01935
  Code: https://github.com/MultiagentBench/MARBLE
  - Directly the closest academic precedent to ARISE-X's **Multi-Agent Coordination Score
    (MACS)**. Measures not only task completion but **quality of collaboration and competition**
    using **novel, milestone-based Key Performance Indicators (KPIs)** — i.e., progress toward
    intermediate milestones, not just final task success.
  - Evaluates multiple **coordination protocols/topologies** (star, chain, tree, graph) and
    strategies (group discussion, cognitive planning), finding e.g. graph topology performs best in
    a research scenario and cognitive planning improves milestone achievement by ~3%. This
    milestone-KPI approach is a concrete, validated way to operationalize "how effectively do
    multiple agents collaborate" — the same goal as MACS — but MultiAgentBench does not propose a
    single named "coordination score" formula; ARISE-X's MACS as a *named, standardized metric*
    still appears to be a novel packaging of this idea.
- **MAST (Multi-Agent System Failure Taxonomy)** — Cemri et al., "Why Do Multi-Agent LLM Systems
  Fail?" arXiv:2503.13657. https://arxiv.org/abs/2503.13657
  - The most rigorous multi-agent **failure taxonomy** found. Built from 1,600+ annotated traces
    across 7 popular MAS frameworks; via expert annotation (inter-annotator κ=0.88) identifies
    **14 failure modes** clustered into **3 categories**: (i) system design issues, (ii)
    inter-agent misalignment, (iii) task verification failures. Includes an LLM-as-judge pipeline
    to scale annotation.
  - This taxonomy is a strong candidate to **ground/validate ARISE-X's "Level 5 — Multi-Agent"
    chaos catalog** (agent disagreement, deadlock, message loss, conflicting objectives, cascading
    failure, malicious agent) — MAST's empirically-derived categories (especially
    "inter-agent misalignment" and "task verification") map closely onto ARISE-X's proposed fault
    types and could be used to validate/extend that taxonomy with real observed failure data rather
    than an a priori list.
- **AgentBoard** — Ma et al., NeurIPS 2024 (Oral). arXiv:2401.13178.
  https://arxiv.org/abs/2401.13178
  - Not multi-agent-specific but highly relevant methodologically: explicitly critiques that
    "current evaluation frameworks mostly focus on the final success rate, revealing few insights
    during the process," and introduces a **fine-grained progress rate metric** that captures
    incremental advancement toward the goal (partial credit for partial progress), plus a
    multi-faceted analysis toolkit. This is close in spirit to ARISE-X's "Goal Achievement" +
    "Path Efficiency" trajectory-level ambitions and is one of the few benchmarks that explicitly
    argues for trajectory-level (not just outcome-level) insight — a good citation to justify
    ARISE-X's Long-Horizon Engine philosophy.

## ARISE-X Metric Mapping

| ARISE-X Metric | Closest Academic Precedent | Notes |
|---|---|---|
| **Goal Success / Goal Achievement** | GAIA final-answer accuracy; WebArena/VisualWebArena functional-correctness end-state; tau-bench end-state match; AgentBoard "progress rate" (partial-credit variant) | Well-established across nearly every benchmark; ARISE-X's contribution is combining it with the other axes rather than treating it standalone. |
| **Resilience (ARS-R)** | ReliabilityBench's fault-tolerance axis λ (timeouts, rate limits, schema drift); AgentChaos pass@1-under-fault degradation; AgentNoiseBench noise robustness; "Assessing and Enhancing Robustness of LLM-MAS Through Chaos Engineering" (Owotogbe) | Strong, fairly direct precedent — this cluster of 2025-2026 papers is converging on the exact concept ARISE-X calls Resilience, using controlled fault/noise injection. |
| **Behavioral Stability Index (BSI)** | "How is ChatGPT's behavior changing over time?" (Chen et al.); emerging 2026 drift/identity papers (arXiv:2608.14109 structured drift diagnosis; arXiv:2606.21843 geometric agent-identity drift) | Partial precedent for *model*-level behavior drift; no paper found with an equivalent multi-signal *agent behavioral fingerprint* (tool-mix %, steps, recovery rate, escalation rate, goal deviation, cost) tracked as one composite index — **this specific fingerprint packaging appears novel.** |
| **Recovery** | tau-bench/ReliabilityBench implicitly via repeated-trial pass^k and fault-recovery scenarios; AgentBoard progress-after-setback (partial); no paper found with an explicit named "recovery efficiency/time" metric | **Largely novel as a named, standalone metric** — recovery is implied in reliability-under-fault results but not isolated and reported as its own number in the literature reviewed. |
| **Efficiency (Path/Tool/Cost Efficiency)** | ToolEval Win Rate (path-quality judgment); AgentBoard progress rate; general agent papers reporting steps/cost as secondary stats | Partial precedent — efficiency-adjacent numbers are commonly *reported* (steps, cost, API calls) but rarely formalized as a first-class scored metric the way ARISE-X proposes. |
| **Autonomy Efficiency Score (AES)** (useful work per token/$/step/second/human intervention) | No single paper found combining all these denominators into one score; closest partial analogs: ToolEval efficiency-style reporting, cost-per-task stats in various agent papers, and "human-on-the-bridge" style human-intervention-rate framing (arXiv:2606.16871) | **Appears novel** as a unified named metric; individual components (cost/task, human-escalation rate) exist piecemeal in different papers. |
| **Multi-Agent Coordination Score (MACS)** | MultiAgentBench's milestone-based KPIs for collaboration/competition quality (arXiv:2503.01935) | Closest and strongest precedent found — MultiAgentBench operationalizes "collaboration quality" with milestone KPIs across coordination topologies; ARISE-X's MACS as a single named score is a plausible synthesis/rebrand of this line of work rather than an entirely new idea. |
| **Composite multiplicative Agent Reliability Index (ARI)** | No direct academic precedent for a *multiplicative* composite found. Closest conceptual neighbors: ReliabilityBench's "reliability surface R(k, ε, λ)" (multi-axis but not stated as multiplicative); HELM's explicit *rejection* of single-score aggregation in favor of a metric vector | **Appears to be ARISE-X's most novel and most contested proposal.** The vector-of-metrics idea (R = {GoalSuccess, Resilience, ...}) has precedent (HELM, ReliabilityBench); collapsing it into one multiplicative index does not, and runs counter to the dominant "holistic/multi-metric, no single score" position in the evaluation literature (see Risks below). |
| **Chaos/fault taxonomy (Levels 1-6: Infra/Tool/Data/Agent/Multi-Agent/Model)** | AgentChaos's crash/omission/value fault taxonomy on LLM API fields; MAST's 14-mode/3-category multi-agent failure taxonomy; AgentNoiseBench's user-noise/tool-noise split | Good empirical grounding exists per-level but no single paper spans all 6 of ARISE-X's levels in one unified taxonomy — ARISE-X's full-stack taxonomy (infra→model) appears to be a novel synthesis across several narrower published taxonomies. |

## Risks/Criticisms of Composite Scoring (from literature)

1. **Aggregation hides trade-offs (HELM's core argument).** HELM (arXiv:2211.09110) explicitly
   designed a *multi-metric, non-aggregated* evaluation specifically "to ensure metrics beyond
   accuracy don't fall to the wayside, and that trade-offs are clearly exposed" — i.e., the
   evaluation-research mainstream treats single-score aggregation as something to actively avoid,
   not a best practice to adopt by default. A multiplicative ARI would need strong justification
   for why agent reliability engineering is an exception to this norm.
2. **Underspecification / benchmark performance ≠ deployment credibility.** D'Amour et al.
   (arXiv:2011.03395) show that models/pipelines with equivalent aggregate benchmark scores can
   behave arbitrarily differently after deployment/domain shift. A single ARI number computed
   under one test distribution risks the same failure: it can look stable while hiding brittleness
   that only appears under a different chaos profile or population shift — reinforcing the need
   for the drift/continuous-monitoring loop ARISE-X already plans, and arguing against treating a
   point-in-time ARI as a durable certification.
3. **Metric gaming / Goodhart-style strategic response.** "Scoring Rules! Statistical and
   Strategic Alignment for Text Evaluation Metrics" (arXiv:2608.01423) explicitly studies how, once
   a metric is used as an optimization target, agents/developers can strategically game it even if
   it is well correlated with human judgment in the undirected case. A single named ARI used as a
   CI/CD gate is a natural target for this kind of gaming (e.g., optimizing whichever sub-metric is
   cheapest to inflate, especially if the multiplication is not perfectly calibrated across scales).
4. **Multiplicative composites are extremely sensitive to weak sub-scores and scale/normalization
   choices**, a mathematical property, not just an empirical one: because a product of several
   probabilities-in-[0,1] shrinks rapidly with each additional factor (n factors each at 0.9 already
   multiply to ~0.59 at n=5, ~0.53 at n=6), the *number* of dimensions chosen to include in the ARI
   and how each is normalized will dominate the resulting score more than genuine reliability
   differences — a form of arbitrary "aggregation sensitivity" flagged generally in the
   composite-indicator/HDI-style-index critique literature (this is a well-known general critique
   of composite indices, e.g., in the composite-indicator methodology literature, though a
   dedicated LLM-agent-specific paper on multiplicative index sensitivity was not found in this
   search — flagged as a reasoning-from-first-principles risk rather than a directly cited one).
5. **No agreed ground truth for weighting/inclusion.** None of the reviewed papers that build
   multi-axis agent evaluations (ReliabilityBench's R(k,ε,λ), HELM's 7-metric grid, MultiAgentBench's
   milestone KPIs) collapse to a single index; several implicitly argue (by design choice) that
   preserving the vector/surface is more useful for diagnosis than any scalar summary — i.e., the
   published state of the art favors ARISE-X's own "Reliability Vector" R over its "ARI" scalar,
   suggesting ARI should be treated as a communication/gating convenience layered on top of the
   vector, not the primary analytic artifact.

## Clarifying Questions

- Should recovery time/efficiency and the multi-signal behavioral fingerprint be treated in the
  ARISE-X spec as explicitly **novel, patent/IP-relevant contributions** (since no direct precedent
  was found), or should the spec instead cite MAST/AgentChaos/ReliabilityBench more tightly to
  ground them as extensions of existing work? This affects how "IP" claims in the original vision
  doc should be worded.
- Does ARISE-X want the ARI to be positioned as a **CI/CD gate convenience score** layered on top
  of the full Reliability Vector (consistent with how HELM/ReliabilityBench treat multi-metric
  results), or as the primary headline metric? The literature more strongly supports the former.
- Would it be useful to have a follow-up research pass specifically on **composite-indicator
  methodology critique literature** (e.g., OECD/JRC handbook on constructing composite indicators,
  Human Development Index critiques) to more rigorously ground risk #4 above with dedicated
  citations, since this pass found that risk primarily via general ML-evaluation papers (HELM,
  underspecification) rather than dedicated index-methodology papers?
- MAST and MultiAgentBench are both 2025 papers with public code/datasets
  (https://github.com/MultiagentBench/MARBLE); would the ARISE-X team want a deeper technical dive
  into their milestone-KPI / failure-taxonomy schemas (rather than abstract-level summaries) to
  directly inform the MACS metric definition and the Level-5 multi-agent chaos catalog?

## Recommended Next Research (not completed this session)

- [ ] Deep-dive on MultiAgentBench's exact milestone-KPI formula and MARBLE's coordination-protocol
      evaluation code to extract a concrete MACS formula proposal.
- [ ] Deep-dive on MAST's 14 failure modes (full paper/appendix) to cross-map each mode to ARISE-X's
      Level 4/5 chaos taxonomy entries.
- [ ] Read ReliabilityBench and AgentChaos full papers (not just abstracts) for exact formulas of
      R(k, ε, λ) and the fault-injection taxonomy, to compare directly against ARISE-X's Resilience
      Engine and Chaos Plane taxonomy.
- [ ] Search dedicated composite-indicator-methodology literature (OECD/JRC Handbook on
      Constructing Composite Indicators, HDI critique papers) for a more rigorous grounding of the
      multiplicative-aggregation risk section.
- [ ] Check for a formal published "agent behavioral fingerprint" concept beyond the drift papers
      found here (arXiv:2608.14109, arXiv:2606.21843) to confirm/refute novelty of ARISE-X's BSI
      fingerprint design.
