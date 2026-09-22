<!-- markdownlint-disable-file -->
# Task Research: ARISE-X Agent Reliability Engineering Framework Validation

Validate, vet, and streamline the ARISE-X project vision (`intial analysis and requirement.md`) against the current codebase state, the existing agent-evaluation/observability landscape, chaos engineering practice, ML/LLM drift detection practice, and SRE/CI-CD gating precedent. Produce a decisive, evidence-linked assessment of what is genuinely novel, what overlaps with existing tools, what is underspecified, and a recommended path to formalize the framework.

## Task Implementation Requests

* Validate the ARISE-X problem statement and core philosophy against real-world agent evaluation practice.
* Vet the proposed 7-plane architecture and the Chaos Catalog taxonomy for completeness and feasibility.
* Vet the proposed metrics (ARS, ARS-R, BSI, AES, MACS, composite ARI) for measurability, novelty, and mathematical soundness.
* Compare against existing frameworks/products (LangSmith, Arize Phoenix, Galileo, Braintrust, AgentOps, DeepEval, RAGAS, tau-bench, AgentBench, GAIA, WebArena) to identify differentiation and overlap.
* Assess current codebase (`src/arise_x/*`) maturity against the vision and identify gaps.
* Streamline the requirement into an actionable, prioritized scope.

## Scope and Success Criteria

* Scope: Conceptual/product validation plus current-repo alignment check. Excludes writing new implementation code; excludes deep infra/deployment design.
* Assumptions: The document `intial analysis and requirement.md` reflects the user's authoritative intent as of 2026-08-25. The `src/arise_x` package is an early scaffold, not a finished product.
* Success Criteria:
  * Every major concept in the requirement doc (planes, chaos levels, metrics, CI/CD loop) is checked against at least one external precedent or the current codebase.
  * A clear verdict is given on which parts of ARISE-X are novel vs. which already exist in some form elsewhere.
  * A streamlined, prioritized MVP scope is proposed with rationale.
  * All claims are evidence-linked (file+line or URL).

## Outline

1. Current repository state (what exists today in `src/arise_x`)
2. External landscape: agent evaluation & observability platforms
3. External landscape: long-horizon / tool-use agent benchmarks (academic)
4. Chaos engineering precedent and its applicability to agents
5. ML/LLM drift detection precedent and applicability to behavioral drift
6. SRE / CI-CD gating precedent (error budgets, canary, regression gates)
7. Metric-by-metric validation (ARS, Resilience, BSI, AES, MACS, ARI)
8. Consolidated gap analysis and streamlined MVP recommendation

## Potential Next Research

* Deep-dive on MultiAgentBench's milestone-KPI formula and MARBLE's coordination-protocol evaluation code to draft a concrete MACS formula.
  * Reasoning: MACS is currently a name without a formula; MultiAgentBench is the closest grounded precedent.
  * Reference: `.copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md`, arXiv:2503.01935
* Composite-indicator methodology critique literature (OECD/JRC handbook, HDI critiques) to rigorously ground the multiplicative-ARI sensitivity risk.
  * Reasoning: current risk #4 on multiplicative sensitivity is reasoned from first principles, not directly cited.
  * Reference: `.copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md`
* Adjacent guardrail/red-team vendors (Patronus AI, Giskard, PromptFoo) as closer commercial analogs to "chaos for agents."
  * Reasoning: may already cover adversarial/robustness fault injection under different branding.
  * Reference: `.copilot-tracking/research/subagents/2026-08-25/agent-eval-landscape.md`
* Microsoft `agent-governance-toolkit` deep dive (ChaosEngine, SLOEngine, cost/prompt-injection fault templates).
  * Reasoning: closest found large-vendor precedent combining chaos + SLO + governance for agents; directly informs the Chaos Plane and CI/CD Plane designs.
  * Reference: `.copilot-tracking/research/subagents/2026-08-25/chaos-engineering-precedent.md`
* PSI (Population Stability Index) exact formula/thresholds, and a survey of LangSmith/Phoenix/Langfuse for existing distributional tool-call statistics.
  * Reasoning: needed to finalize the concrete statistical test per fingerprint dimension.
  * Reference: `.copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md`

## Research Executed

### File Analysis

* `pyproject.toml` (28 lines)
  * `arise-x` v0.1.0, Python `>=3.11`; deps: `fastapi`, `pydantic`, `typer`, `uvicorn`, `ipykernel`, `ipywidgets`, `ruff`, `tqdm`, `pytest`; no LLM/agent SDKs, no `numpy`/`scipy` for statistics, no `pyyaml`.
* `ruff.toml` (4 lines) — lint rules `E,F,I,UP,B` only; no security (`S`) or docstring (`D`) enforcement.
* `README.md` — self-describes as "intentionally experiment-first... not production hardening."
* `configs/experiment.yaml` (11 lines) — defines `horizons`, `disruptions`, `thresholds`; **dead config**, never parsed by any Python code (no YAML dependency exists).
* `docs/architecture.md` (~26 lines) — describes "five functional layers," a simplified subset of the vision's seven planes; omits Scenario Plane, Agent Execution Plane, and CI/CD + Production Plane entirely.
* `src/arise_x/agents/base.py` (23 lines) — `AgentUnderTest` protocol + `AgentResponse` dataclass; defined but never invoked anywhere (dead code from a runtime perspective).
* `src/arise_x/chaos/injector.py` (24 lines) — `DisruptionProfile` + `sample_failure()`; 3 hardcoded profiles (`baseline`, `latency_spike`, `tool_degradation`); unseeded `random`.
* `src/arise_x/drift/detector.py` (27 lines) — `compute_drift_score()` is a per-event weighted-sum heuristic, not a statistical/baseline comparison; no `test_drift.py` exists.
* `src/arise_x/evaluation/runner.py` (56 lines) — `run_reliability_loop()` is the only fully wired end-to-end path (chaos → telemetry → drift → trust → result), but entirely synthetic (`_simulate_event` coin-flips); ignores `horizons` from config.
* `src/arise_x/trust/scorer.py` (23 lines) — `score_trust()` computes an **additive** weighted composite (`0.45*reliability + 0.30*safety + 0.25*stability`), contradicting the vision's multiplicative ARI requirement.
* `src/arise_x/telemetry/events.py` (13 lines) — `RunEvent` is a flat single-outcome record, not a trajectory/trace.
* `src/arise_x/storage/repository.py` (16 lines) — write-only JSON dump, no read/query/history API.
* `tests/test_runner.py`, `tests/test_trust.py` — shallow; validate only iteration counts, disruption-label whitelist, and the two extreme trust cases; no drift tests exist; no borderline-threshold tests.
  * Full analysis: `.copilot-tracking/research/subagents/2026-08-25/codebase-analysis.md`

### Code Search Results

* `TODO|FIXME|NotImplementedError|placeholder` across `src/**` — zero matches; immaturity is expressed via absent modules, not in-code markers (per codebase-analysis.md).

### External Research

* Agent evaluation/observability landscape (LangSmith, Arize AX/Phoenix, Galileo, Braintrust, AgentOps, DeepEval, RAGAS, W&B Weave) and explicit chaos/drift product search.
  * Full findings: `.copilot-tracking/research/subagents/2026-08-25/agent-eval-landscape.md`
* Academic long-horizon/tool-use/multi-agent benchmarks (tau-bench, AgentBench, GAIA, WebArena, ToolBench/API-Bank) plus reliability, drift, and composite-scoring literature.
  * Full findings: `.copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md`
* Chaos engineering precedent (Principles of Chaos, Chaos Monkey, Gremlin, LitmusChaos, Chaos Mesh) and agent-specific chaos work (AgentChaos, MAST, Microsoft agent-governance-toolkit, tianpan.co practitioner synthesis).
  * Full findings: `.copilot-tracking/research/subagents/2026-08-25/chaos-engineering-precedent.md`
* Drift detection (Evidently AI, NannyML, whylogs) and SRE/CI-CD gating (Google SRE book, Kayenta/Spinnaker canary judge, Anthropic eval-statistics paper).
  * Full findings: `.copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md`

### Project Conventions

* No `.github/copilot-instructions.md` present in this repository; markdown/writing-style conventions applied per the global instructions attached to this session.
* Research files placed under `.copilot-tracking/research/2026-08-25/` and `.copilot-tracking/research/subagents/2026-08-25/` per Task Researcher mode conventions.

## Key Discoveries

### Project Structure

The repo (`c:\Users\sharmadeep\ARISE-X`) is a ~350-line Python scaffold implementing a narrow, synthetic slice of the vision: `evaluation/runner.py` orchestrates `chaos/injector.py` → `telemetry/events.py` → `drift/detector.py` → `trust/scorer.py` → `storage/repository.py`, exposed via `main.py` (Typer CLI) and `api/app.py` (FastAPI). Of the vision's 7 planes, only fragments of Chaos (Level 1 partial, Level 2 label-only), Telemetry (single-event, not trajectory), Intelligence (heuristic, not statistical drift), and Reliability (3 of 8 vector dimensions, additive not multiplicative) exist. Scenario Plane, Agent Execution Plane (multi-agent/tools/RAG/memory), and CI/CD + Production Plane have zero code. See the full vision-to-code mapping table in `.copilot-tracking/research/subagents/2026-08-25/codebase-analysis.md`.

### Implementation Patterns

* `frozen=True` dataclasses used consistently for value objects (`RunEvent`, `DriftResult`, `TrustDecision`, `IterationResult`, `DisruptionProfile`, `AgentResponse`) — a good, idiomatic pattern worth preserving as the framework grows.
* Settings loaded from environment variables via a single `load_settings()` factory (`config.py`) — reasonable starting point but has no config-file (YAML/scenario) loading path yet.
* `random` module used unseeded in both `chaos/injector.py` and `evaluation/runner.py` — a reproducibility risk that will block any future CI/CD regression-gating feature (Kayenta-style canary judges and paired-difference statistical tests both require reproducible/replayable runs; see `.copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md`, Part A.3 and B.3).

### Complete Examples

Current end-to-end flow (`src/arise_x/evaluation/runner.py`, conceptually):

```python
for i in range(iterations):
    disruption = ["baseline", "latency_spike", "tool_degradation"][i % 3]
    event = _simulate_event(task_id, disruption)      # random pass/fail
    drift = detect_drift(event, settings.drift_threshold)   # per-event heuristic
    decision = score_trust(event, drift, settings.trust_threshold)  # additive composite
    results.append(IterationResult(task_id, disruption, drift.score, decision.score, decision.trustworthy))
```

This has no real agent invocation, no trajectory, and no historical/statistical comparison — it is a coin-flip simulator that exercises the plumbing, not the reliability-engineering logic described in the vision document.

### API and Schema Documentation

* `POST /run` (`src/arise_x/api/app.py`, lines 21-28) accepts `{iterations: int}` (1-200) and returns `{iterations, trustworthy_count, results}`; no auth, no persistence-on-request, no historical/comparison endpoints.
* `GET /health` returns `{"status": "ok"}`.

### Configuration Examples

`configs/experiment.yaml` (aspirational, not wired in):

```yaml
experiments:
  - name: arise-x-baseline
    horizons: ["24h", "7d"]
    disruptions: ["baseline", "latency_spike", "tool_degradation"]
    thresholds:
      trust: 0.75
      drift: 0.30
```

## Technical Scenarios

### Scenario 1 — Is the ARISE-X philosophy and problem statement valid?

**Assessment: Yes, and it is well-timed.** The premise — "don't just evaluate what an agent does, engineer how reliably it behaves" — is directionally aligned with a real, fast-moving 2025-2026 research and product trend, not a fabricated problem. Multiple independent 2025-2026 papers converge on the same thesis:

* AgentChaos (arXiv:2608.06790, ASE 2026) empirically shows agent robustness ranking is **consistent across backbone LLMs** — i.e., reliability is a property of system *architecture*, not raw model capability, directly validating "engineer how reliably it behaves" as a distinct discipline from model evaluation.
* ReliabilityBench (arXiv:2601.06112) independently proposes a near-identical framing: a reliability surface across consistency (pass^k), perturbation robustness, and fault tolerance.
* D'Amour et al.'s "Underspecification" (arXiv:2011.03395) shows benchmark-equivalent models/pipelines can behave arbitrarily differently after deployment shift — supporting the vision's claim that "Goal Success in test conditions" alone under-specifies production reliability.

However, the vision document's competitive framing ("nobody is doing this") is **not fully accurate** — see Scenario 2. The real differentiator is integration breadth, not any single pillar.

### Scenario 2 — Competitive landscape: what already exists

**Requirements:** Determine whether Chaos Plane, Drift Detection, and the composite Reliability Index are novel.

**Findings (from `.copilot-tracking/research/subagents/2026-08-25/agent-eval-landscape.md` and `academic-benchmarks.md`):**

| ARISE-X Pillar | Market status |
|---|---|
| Long-horizon trajectory evaluation / observability | **Crowded, mature, commercial.** LangSmith, Arize AX/Phoenix, Galileo, Braintrust, AgentOps, W&B Weave, DeepEval (OSS) all offer tracing + evals; DeepEval explicitly supports trajectory-based evals and CI (`deepeval test run`); Braintrust has a mature GitHub Action for CI gating. |
| Chaos/fault injection for agents | **Genuine whitespace.** Only unfunded OSS (`agent-chaos`, 1 GitHub star) and 2025-2026 academic prototypes (AgentChaos/ASE 2026, ChaosLLM/ISSRE 2025, Owotogbe arXiv:2505.03096) exist. No commercial vendor productizes this. Microsoft's `agent-governance-toolkit` (OSS) is the closest large-vendor artifact, with a `ChaosEngine`/`ChaosExperiment` abstraction and 9 fault templates including `cost_spike` and `prompt_injection`. |
| Behavioral drift/fingerprinting | **Not a clean gap.** Three real, named competitors exist: **dedrift.ai** (AGPL open-core; statistically rigorous — BH-FDR, anytime-valid testing, config-fingerprint attribution — the closest conceptual analog to ARISE-X's fingerprint idea), **Tessary.ai** (production-trend drift, cause attribution), **Armalo Sentinel** (5-dimension drift + composite "Trust" score). A 2026 arXiv paper ("Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems," arXiv:2601.04170) is already cited by multiple vendors as formal grounding. |
| Composite **multiplicative** reliability index | **Confirmed gap.** No product or paper found describing a multiplicative composite reliability score for agents. |
| Full vertical integration (benchmark → chaos → recovery → drift → CI gate, one system) | **Not found anywhere.** Each capability exists as a point solution from a different vendor; no single product spans all of them. |

**Preferred Approach:** Position ARISE-X's differentiation explicitly as **the integration itself** — correlating deliberately-injected chaos with measured drift and gating CI/CD on the combined signal — not as any single pillar. Any pitch or README should cite dedrift/Tessary/Armalo as prior art for drift and explicitly explain why chaos-correlated drift (not passive production monitoring alone) is different.

#### Considered Alternatives

Claiming "behavioral drift detection" as ARISE-X's headline novel IP was considered but rejected: it would be immediately challengeable given dedrift's existing statistically-rigorous open-core implementation covering nearly the same concept (config-fingerprint attribution, canary prompt suites, anytime-valid testing).

### Scenario 3 — Is the 6-level Chaos Taxonomy complete and sound?

**Assessment: Sound first-generation structure, but incomplete.** Levels 1-2 (Infrastructure, Tool) are directly validated by AgentChaos's crash/omission/value fault taxonomy at the LLM-API/tool-call layer (arXiv:2608.06790). Levels 4-5 (Agent, Multi-Agent) are broadly consistent with MAST's empirically-derived 14-mode/3-category taxonomy from 200+ real multi-agent traces (arXiv:2503.13657), but MAST's actual failure distribution (Specification Issues 41.77%, Inter-Agent Misalignment 36.94%, Task Verification 21.30%) suggests different emphasis than ARISE-X currently lists.

**Concrete gaps identified** (full detail: `.copilot-tracking/research/subagents/2026-08-25/chaos-engineering-precedent.md`):

1. **No cost/budget fault category** — contradicts the vision's own "Cost Efficiency" metric and Cost dimension in the Reliability Vector. Microsoft's toolkit has a dedicated `cost_spike` template.
2. **No security/adversarial fault category** — prompt injection, malicious tool output, jailbreaks are first-class in Microsoft's toolkit (`prompt_injection`) and IEEE literature; ARISE-X buries only "poisoned data" in Level 3.
3. **No human-in-the-loop fault category** — despite the vision's own Agent Fingerprint example including "Human escalation: 5%."
4. **Task-verification/self-checking failure is under-represented** — MAST found this is ~21% of all MAS failures, statistically distinct, with no Level 4 equivalent.
5. **Level 1 is missing resource-exhaustion and clock-skew faults** (CPU/memory/disk/time) — present in every classic chaos platform reviewed (Chaos Mesh, Gremlin) but absent from ARISE-X's Infrastructure list.
6. **Level 5 under-covers "soft" coordination failures** (info withholding, unrequested clarification, reasoning-action mismatch) — MAST found these account for 36.94% of observed MAS failures, larger than the infra/adversarial-flavored faults ARISE-X currently lists (disagreement, deadlock, message loss, malicious agent).
7. **Level 6 conflates two different mechanisms** — "model degradation/behavior change" (a black-box API-response phenomenon, well covered by AgentChaos) versus "model migration" (a version/deployment-drift event) are mechanically different and need different injection/detection strategies.

**Preferred Approach:** Keep the 6-level structure as the entry point (it maps well onto existing precedent), but add **cost** and **security/adversarial** as either a 7th catalog level or a cross-cutting dimension applied within all six levels, add a **verification-failure** fault type to Level 4, add **resource/clock faults** to Level 1, and enrich Level 5 with MAST's "soft" coordination-failure probes. Adopt AgentChaos's **trigger-verification** methodology (confirm a fault actually fired before scoring impact, to avoid underestimating severity).

### Scenario 4 — Are the proposed metrics (ARS, Resilience, BSI, AES, MACS, ARI) sound and novel?

**Requirements:** For each metric, determine the closest academic/industry precedent (if any), and assess whether the metric is measurable as specified.

| ARISE-X Metric | Precedent | Verdict |
|---|---|---|
| Goal Success/Achievement | GAIA, WebArena/VisualWebArena end-state correctness, tau-bench end-state match, AgentBoard progress rate | Well-established; not novel, but necessary baseline. |
| Resilience (ARS-R) | ReliabilityBench's fault-tolerance axis λ, AgentChaos pass@1-under-fault, AgentNoiseBench, Owotogbe (arXiv:2505.03096) | Strong, direct 2025-2026 precedent; ARISE-X should adopt these papers' fault-injection methodology rather than reinvent it. |
| Behavioral Stability Index (BSI) | Chen et al. "How is ChatGPT's behavior changing over time?" (arXiv:2307.09009) for model-level drift; no paper found with an equivalent multi-signal *agent* fingerprint | Partial precedent at the model level; the specific multi-signal agent-fingerprint packaging (tool-mix %, steps, recovery rate, escalation rate, goal deviation, cost) **appears novel** — but note dedrift.ai already ships something similar commercially (Scenario 2), so "novel" should mean "novel combination," not "unprecedented." |
| Recovery | Implied in fault-tolerance results (ReliabilityBench, tau-bench pass^k) but never isolated as a named metric | **Largely novel as a standalone metric** — a genuine, low-risk opportunity to define precisely. |
| Efficiency (Path/Tool/Cost) | ToolEval Win Rate (path-quality, pairwise LLM-judged), AgentBoard progress rate | Partial precedent; rarely formalized as a first-class scored metric — safe to define. |
| Autonomy Efficiency Score (AES) | No single paper combines cost/step/time/human-intervention into one score | **Appears novel** as a unified metric; components exist piecemeal. |
| Multi-Agent Coordination Score (MACS) | MultiAgentBench's milestone-based KPIs across coordination topologies (arXiv:2503.01935) | Strongest precedent found; MACS is a plausible, well-grounded synthesis/rebrand rather than an unprecedented idea — cite MultiAgentBench explicitly. |
| Composite **multiplicative** ARI | No direct precedent found anywhere. HELM (arXiv:2211.09110) explicitly *rejects* single-score aggregation to avoid hiding trade-offs; ReliabilityBench and MultiAgentBench both preserve the metric vector/surface rather than collapsing to a scalar. | **Most novel AND most contested proposal.** Mathematically, a product of n factors each at 0.9 already shrinks to ~0.59 at n=5 dimensions — the ARI is hypersensitive to how many dimensions are included and how each is normalized, which can dominate the score more than genuine reliability differences. |

**Risks of the composite multiplicative score, from literature** (full detail: `.copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md`):

1. Aggregation hides trade-offs (HELM's explicit design rationale for *not* aggregating).
2. Underspecification: benchmark-equivalent scores can hide arbitrarily different deployment behavior (D'Amour et al., arXiv:2011.03395).
3. Metric gaming / Goodhart effects once a score becomes an optimization/CI-gate target (arXiv:2608.01423; Wikipedia's Goodhart's Law page documents concrete precedents such as hospital length-of-stay gaming and the UK COVID testing-target redefinition).
4. Multiplicative composites are mathematically hypersensitive to dimension count and normalization — a general critique of composite indicators, not agent-specific, but directly applicable.
5. No agreed ground truth for weighting/inclusion; every published multi-axis agent evaluation reviewed (ReliabilityBench, HELM, MultiAgentBench) preserves the vector rather than collapsing to one scalar.

**Preferred Approach:** Keep the **Agent Reliability Vector** `R = {GoalSuccess, Resilience, BehavioralStability, Recovery, Safety, Efficiency, Cost, Autonomy}` as the primary analytic artifact (per-dimension, auditable, diagnosable — this matches the state of the art: HELM, ReliabilityBench, MultiAgentBench all do this). Layer the multiplicative **ARI** on top **only as a CI/CD gating convenience**, never as the headline reported metric, and pair it with:

* A **critical-metric override** (Kayenta pattern): designate 1-2 dimensions (e.g., Safety, unrecovered-failure rate) whose failure force-fails the gate regardless of the multiplicative product, making catastrophic weaknesses impossible to hide by construction rather than relying solely on multiplication.
* Explicit, versioned documentation of which dimensions are included and how each is normalized, since this materially changes the ARI's sensitivity.

#### Considered Alternatives

* **Additive weighted composite** (what the current codebase actually implements in `trust/scorer.py`) — rejected as the primary reliability index because it lets strong dimensions mask a catastrophic one, directly contradicting the vision's own stated design goal. Acceptable only as an internal diagnostic sub-score, not as the release-gating artifact.
* **Pure vector, no scalar at all** (HELM's approach) — most defensible academically, but rejected as the *sole* output because CI/CD gates need a single pass/fail decision; the resolution is to keep the vector as the primary artifact and derive a gating scalar (ARI) from it with critical-metric overrides, not to eliminate the scalar entirely.

### Scenario 5 — Is "Behavioral Drift Detection via Agent Fingerprint" statistically sound as specified?

**Assessment: Directionally sound as an observability practice, but under-specified as a detection algorithm.** The vision's example ("Fingerprint v1 vs. six weeks later, then declare 'Behavioral Drift Detected'") relies on eyeballing percentage changes, which both classic ML-drift literature and canary-analysis practice explicitly warn against (statistically significant ≠ practically significant, and vice versa).

**Preferred Approach**, synthesized from Evidently AI, NannyML, Anthropic's eval-statistics paper, and Kayenta's canary judge (full detail: `.copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md`):

1. Treat each fingerprint dimension as its own statistical test matched to its data type: Chi-Square/two-proportion z-test for categorical/rate metrics (tool-selection %, escalation rate, recovery rate); Mann-Whitney U or KS test for continuous metrics (avg steps, cost/task).
2. Report confidence intervals (SEM via CLT), with **clustered standard errors** when episodes aren't independent — naive SEM can understate true variance by 3x+, causing false drift alarms.
3. Use **multi-run resampling** and **paired-difference tests** against the same task suite to cancel non-determinism and task-difficulty noise before declaring drift.
4. Require **both** statistical significance **and** an effect-size threshold (Kayenta's two-stage gate: 98% CI outside a tolerance band, plus a secondary allowed-increase/decrease ratio) before declaring "drift detected" — this is the concrete fix for the vision's current "eyeball the percentages" methodology.
5. Weight drift by downstream-impact correlation (NannyML's covariate-shift-impact formalism) rather than raw magnitude — a large shift in a historically low-impact dimension should alarm less than a small shift in a historically high-impact one.

```text
Baseline window (frozen "golden" fingerprint)
        │
        ▼
Current window (rolling N episodes)
        │
        ▼
Per-dimension test (Chi-Square / Mann-Whitney, matched to data type)
        │
        ▼
Effect-size + tolerance-band check (Kayenta-style dead-zone)
        │
        ▼
Both pass? ──No──▶ No drift declared (log for trend only)
        │Yes
        ▼
Impact-weighted aggregation, critical-dimension override
        │
        ▼
Drift Detected + attributed candidate cause (model/prompt/tool/RAG/memory/population/environment)
```

#### Considered Alternatives

* **Raw percentage-change threshold** (the vision's current worked example, and effectively what `drift/detector.py` implements today as a per-event heuristic) — rejected as the production detection method because it cannot distinguish statistically real drift from sampling noise, and does not scale safely once fingerprint dimensions grow (per Evidently AI's explicit warning that naive thresholding becomes "overly sensitive" at scale).

### Scenario 6 — CI/CD Reliability Gating: is the proposed ARI v1 vs. v2 gate design sound?

**Assessment: The concept (block deployment on reliability regression) is sound and has a mature, directly transferable precedent: Kayenta/Spinnaker's Automated Canary Analysis.** The vision's worked example ("ARI v1 = 91, ARI v2 = 84, Deployment BLOCKED") is a reasonable narrative but needs the same statistical rigor as Scenario 5 to avoid flaky gates, given LLM non-determinism.

**Preferred Approach** (full detail: `.copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md`, Part B):

* Frame the ARI as a **composite SLI** with an **SLO** (e.g., "ARI ≥ 0.85 over trailing N episodes") and gate on **trailing error-budget remaining**, not a single point-in-time reading — this is Google SRE's error-budget pattern and gives teams a self-policing release-velocity control loop instead of a punitive point gate.
* Reuse Kayenta's **NetflixACAJudge** methodology nearly 1:1: per-metric Mann-Whitney U test at 98% CI, a tolerance band (dead-zone) to ignore trivial-but-significant differences, a secondary effect-size threshold, a **critical-metric auto-fail** override, and a 50%-NODATA auto-fail rule (don't silently pass when data coverage drops).
* Mitigate Goodhart's-Law gaming by reserving a **held-out, periodically-rotated evaluation sample** invisible to whatever process tunes agent prompts/skills (per "AI Agents That Matter," arXiv:2407.01502, which documents exactly this failure mode in agent benchmarking today).
* Mitigate non-determinism via multi-run averaging, paired-difference testing against the same task suite, and power analysis to size the episode count needed to detect a given effect (Anthropic, arXiv:2411.00640).

#### Considered Alternatives

* **Hard point-threshold gate on a single ARI reading** (as literally described in the vision's worked example) — rejected as the sole mechanism because it is exactly the pattern Kayenta's own design evolved away from (single-sample comparisons are noise-prone); acceptable only as a simplified first-pass MVP gate with a documented "known limitation," to be replaced by the full statistical judge once episode volume is sufficient for power analysis.

### Scenario 7 — Current codebase readiness vs. the vision (streamlined MVP recommendation)

**Requirements:** Translate the above validation into a prioritized, buildable next step.

Given the codebase is a synthetic scaffold with **zero real agent invocation**, **zero trajectory capture**, **zero statistical drift**, **zero CI/CD gating**, and an **additive (not multiplicative) trust score**, attempting to build all 7 planes and 6 chaos levels at once would repeat the vision document's own risk of "underspecification." The evidence above supports a narrower, sequenced MVP:

```text
Phase 0 (foundation, low risk, high leverage):
  - Wire configs/experiment.yaml into a real Scenario model (add pyyaml, parse horizons/disruptions/thresholds)
  - Seed all `random` usage for reproducibility (required by every downstream statistical method above)
  - Wire `AgentUnderTest.run_task` into `evaluation/runner.py` so the loop calls something real, even a trivial echo agent
  - Add read/query API to storage/repository.py (needed for any v1-vs-v2 comparison)

Phase 1 (trajectory + vector, replaces synthetic single-event model):
  - Replace flat `RunEvent` with a trajectory/trace model (State/Action/Tool-call/Recovery/Final-state)
  - Compute the 8-dimension Agent Reliability Vector R per run (not just 3 factors)
  - Keep trust/scorer.py's composite as an internal diagnostic; do not treat it as ARI yet

Phase 2 (chaos taxonomy expansion + verified injection):
  - Extend chaos/injector.py from Level 1/2-only to at least Level 3 (Data) and Level 4 (Agent), the two most implementable without a multi-agent harness
  - Adopt AgentChaos's trigger-verification pattern (confirm fault actually fired before scoring)
  - Add cost and human-in-the-loop faults per Scenario 3 gaps

Phase 3 (statistically real drift + gating):
  - Replace drift/detector.py's per-event heuristic with the baseline-vs-window, per-dimension statistical test design from Scenario 5
  - Introduce the ARI as a gating convenience over the vector, with critical-metric override, per Scenario 4/6
  - Add a CI/CD gate command (e.g., `arise-x gate --baseline v1.json --candidate v2.json`) implementing the Kayenta-style two-stage significance+effect-size judge

Phase 4 (multi-agent + MACS):
  - Only after Phases 0-3 are solid: add multi-agent harness, Level 5 chaos, and MACS per MultiAgentBench's milestone-KPI precedent
```

**Preferred Approach:** Sequence Phase 0 → 3 before touching multi-agent/MACS (Phase 4). This matches both the codebase's actual maturity (multi-agent has zero code today) and the literature's own priority signal (MAST/MultiAgentBench are 2025 papers still maturing; single-agent resilience/drift precedent is stronger and more directly reusable right now).



