# Research: Drift Detection & SRE/CI-CD Gating Precedent for ARISE-X

## Research Topics/Questions

**Part A — Drift detection**
1. Classic ML drift detection tools/concepts: Evidently AI, NannyML, whylogs/whylabs; concept drift vs. data drift vs. prediction drift; statistical tests (PSI, KL divergence, KS test).
2. Existing concept of "behavioral fingerprinting" for AI agents: tool-usage distribution drift, step-count drift, escalation-rate drift, goal-deviation drift.
3. Is comparing a full "agent fingerprint" (tool selection %, avg steps, recovery rate, escalation rate, goal deviation, cost/task) across time windows technically sound? What statistical methods give confidence, not just eyeballing % changes?

**Part B — SRE / CI-CD gating**
1. SRE error budget / SLO-SLI methodology (Google SRE book) and mapping to an "Agent Reliability Index" CI/CD gate.
2. Existing regression-testing/canary-deployment gating for ML models (shadow deployment, Kayenta canary analysis, model regression suites) and how similar patterns gate agent deployments on reliability score deltas.
3. Risks of hard threshold/composite-score CI/CD gates (Goodhart's law, metric gaming, LLM non-determinism causing flaky gates) and industry mitigations (statistical significance testing, multi-run averaging, confidence intervals).

## Status: Complete

---

## Part A — Drift Detection

### A.1 Classic ML drift detection concepts and vendor tooling

**Terminology (source: Evidently AI ML-in-production guides — concept drift and data drift):**
- **Data drift** (a.k.a. covariate shift / feature drift): change in the distribution of input feature values, `P(X)`, while the input→output relationship is assumed stable. Source: https://www.evidentlyai.com/ml-in-production/data-drift
- **Concept drift**: change in the *relationship* between inputs and target, `P(Y|X)`. The thing being predicted is itself changing (e.g., new fraud patterns, new spam techniques). Source: https://www.evidentlyai.com/ml-in-production/concept-drift
- **Prediction drift** (a.k.a. output/target drift): change in the distribution of the model's own outputs/predictions over time. Useful as a proxy for concept drift when ground truth is delayed or unavailable. Source: https://www.evidentlyai.com/ml-in-production/data-drift
- **Model drift**: umbrella term for "quality got worse," without specifying the cause (could be caused by data drift, concept drift, or data quality issues).
- Distinctions between these terms are explicitly described by Evidently as *not rigidly defined* — practitioners often use them interchangeably, and multiple types of drift co-occur in practice. This is an important caveat for ARISE-X: don't over-formalize the taxonomy internally; focus on what's actionable.
- Types of concept drift: **gradual** (slow, expected decay — plan periodic retraining), **sudden** (abrupt environment shift, e.g., COVID-19), **recurring** (cyclical/seasonal — should be modeled, not alarmed on).

**Statistical tests/metrics commonly used for drift** (source: Evidently AI data-drift guide, https://www.evidentlyai.com/ml-in-production/data-drift):
- **Summary statistics** (mean/median/quantile bounds) — cheap, but noisy at scale and can miss distributional shape changes within range.
- **Statistical hypothesis tests**: Kolmogorov-Smirnov (KS) test for numerical features, Chi-Square test for categorical features. Output is a p-value used as the "confidence" signal for whether two samples come from different distributions. Evidently explicitly warns: *statistically significant ≠ practically significant* — with very large samples, trivial differences become "significant." Rule of thumb: KS/Chi-Square tests work well for a *small number of important, interpretable features* on *smaller datasets* (e.g., healthcare); they get "overly sensitive" at scale.
- **Distance/divergence metrics**: Population Stability Index (PSI, common in credit risk), Wasserstein distance, Jensen-Shannon divergence. These quantify *magnitude* of drift rather than testing a same-distribution hypothesis, and are recommended over hypothesis tests for **large datasets** because hypothesis tests become oversensitive at scale. PSI/JS-divergence are bounded (e.g., 0–1 for JS divergence), which is useful for a normalized "drift score."
- **Rule-based checks** — simple heuristics (e.g., "alert if predicted-fraud share > 10%") as a low-cost complementary signal, not a substitute for statistical methods.
- Recommendation from Evidently: when monitoring many features at once, track "% of features that drifted" as an aggregate signal rather than alerting on each feature individually (reduces noise).

**NannyML's covariate/concept shift formalism** (source: https://www.nannyml.com/blog/types-of-data-shift):
- Grounded in the probability product rule `P(Y,X) = P(Y|X)·P(X)`. **Covariate shift** = `P(X)` changes while `P(Y|X)` (the "concept") stays fixed. NannyML gives concrete magnitude formulas:
  - Pure covariate-shift magnitude: `½ Σ|P(X)_shifted − P(X)_reference|` (a Total Variation–style distance, bounded to 0–1: 0 = no change, 1 = zero distribution overlap).
  - Effect of covariate shift on the *target* distribution: weight the above by the reference concept `P(Y=1|X)` and sum/integrate — this tells you how much of the shift actually matters for outcomes (not just raw feature movement).
- Key insight directly relevant to ARISE-X: **not all input-distribution drift affects outcomes** — a shift concentrated in a region where the "concept" (task outcome given that input) is flat has near-zero effect on model/agent quality, while the same-magnitude shift in a high-sensitivity region can be very consequential. This argues for *weighting* fingerprint-dimension drift by known sensitivity/impact, not treating all dimensions equally.
- NannyML also pioneered "confidence-based performance estimation" (CBPE) — estimating model performance changes from covariate shift *without* ground truth, using calibrated prediction probabilities. Relevant analog for agent fingerprints: if you know each fingerprint dimension's historical correlation with downstream failure/escalation, you can estimate expected reliability impact of an observed distribution shift before an incident actually occurs.

**whylogs / WhyLabs** (source: https://docs.whylabs.ai/docs/): Provided "profile"-based drift detection (whylogs profiles: efficient, mergeable, privacy-preserving statistical summaries), separating the logging/instrumentation layer from the analysis/alerting layer — an architecture pattern (append cheap summary stats continuously; run expensive comparisons periodically) worth reusing for ARISE-X's telemetry pipeline. **Caveat:** WhyLabs the company discontinued operations; whylogs and LangKit remain open source (https://github.com/whylabs/whylogs, https://github.com/whylabs/langkit). Do not cite WhyLabs as an active commercial vendor in any customer-facing ARISE-X material.

### A.2 "Agent behavioral fingerprinting" as a named concept

**Finding: no established, widely-cited term "agent behavior fingerprint" or "LLM agent behavioral drift detection" exists in the literature searched.** This appears to be a genuine gap/opportunity rather than a well-trodden concept — ARISE-X would be naming and formalizing a real but currently *ad hoc* practice. Closest existing threads:

- **"AI Agents That Matter" (Kapoor, Stroebl, Siegel, Nadgir, Narayanan; arXiv:2407.01502, July 2024)** — https://arxiv.org/abs/2407.01502. This is the most directly relevant academic precedent, though framed as a *benchmarking* critique rather than production drift detection:
  - Argues the agent research community's narrow focus on **accuracy alone** (ignoring **cost**) produces "needlessly complex and costly" SOTA agents, motivating **joint optimization of accuracy and cost** — directly supports ARISE-X's "cost/task" as a first-class fingerprint dimension, not an afterthought.
  - Documents that **agent benchmarks often have inadequate holdout sets** (or none), causing agents to "overfit" to benchmarks by taking shortcuts — a direct analog to the CI/CD-gate-gaming risk in Part B.3.
  - Calls out a general **lack of standardization in evaluation practices**, causing poor reproducibility — relevant to why ARISE-X needs a formally specified, versioned fingerprint schema rather than ad hoc dashboards.
- **Arize AI's agent-observability product content** (https://arize.com/blog/) confirms the *practitioner* trend toward tracing/evaluating agent tool-calls, harness behavior, and "agent-as-a-judge," but frames these primarily as **evaluation** (offline/online scoring) rather than **statistical drift-over-time** detection of behavior distributions. Representative recent posts: "AI agent guardrails vs. evals," "Evaluation-driven development: How to move AI agents from pilot to production," "How Uber evaluates AI agents at production scale," "Where agent evals are going: Agent-as-a-Judge." None of these describe a formal multi-dimensional "fingerprint + statistical drift test" methodology — they describe tracing + per-interaction eval scores + human review loops (see Hamel Husain's "Your AI Product Needs Evals," A.3 below, for the canonical 3-level framework these vendors implement).
- **Conclusion for ARISE-X positioning:** the *individual signals* ARISE-X proposes (tool-usage distribution, step-count, escalation rate, recovery rate, goal-deviation, cost/task) are each independently recognized as useful agent-quality/observability signals in the practitioner ecosystem (Arize, LangSmith/Hamel-style tracing, general MLOps drift tooling), but **the specific framing of a unified "agent fingerprint compared statistically across time windows" does not have a named precedent** — this is a legitimate, defensible innovation claim, not an established or "reinvented wheel" concept. It should, however, explicitly borrow the *statistical rigor* of classic ML drift detection (A.1) and eval statistics (A.3) rather than inventing new math.

### A.3 Statistical soundness of comparing a full "agent fingerprint" across time windows

The ARISE-X idea (compare tool-selection %, avg steps, recovery rate, escalation rate, goal deviation, cost/task across time windows) is **directionally sound as an observability practice** but requires real statistical machinery to move from "eyeballing % change" to "drift detected with confidence." Key applicable methods, synthesized from the sources above plus Anthropic's evals-statistics paper and Spinnaker/Kayenta's production implementation of the same underlying idea for infrastructure metrics:

1. **Treat each fingerprint dimension as its own statistical test, with a type appropriate to its data shape**, rather than a single "everything changed by X%" narrative:
   - Categorical/proportion metrics (tool-selection %, escalation rate, recovery rate) → Chi-Square test or two-proportion z-test between time windows; or a distance metric (PSI / Jensen-Shannon) if sample sizes are large (per Evidently's large-dataset guidance in A.1).
   - Continuous metrics (avg steps, cost/task) → Kolmogorov-Smirnov test on full distributions (not just comparing means) or, per Kayenta's proven production pattern, a **Mann-Whitney U test** (nonparametric, no normality assumption — appropriate since step-counts/cost are typically right-skewed). Source: https://spinnaker.io/docs/guides/user/canary/judge/
   - Goal-deviation is likely closer to a model-quality/eval score (bounded, possibly LLM-judged) — apply the same Central-Limit-Theorem-based confidence-interval approach Anthropic recommends for eval scores (below).

2. **Report confidence intervals / standard errors, not point estimates, for every fingerprint metric** (source: Anthropic, "A statistical approach to model evaluations," https://www.anthropic.com/research/statistical-approach-to-model-evals, paper: arXiv:2411.00640):
   - Under the Central Limit Theorem, if a fingerprint metric is itself an average over many independent task episodes, its sampling distribution is approximately normal; report the **Standard Error of the Mean (SEM)** alongside each metric and derive a 95% CI as `mean ± 1.96×SEM`.
   - **Cluster standard errors** when episodes are not independent (e.g., many steps/escalations coming from the *same* underlying task type, user, or session) — naive SEM computation on non-independent data underestimates the true standard error by "over 3x" in some evals, per Anthropic, which would cause false-positive drift alarms.
   - **Reduce variance via multiple-run resampling**: if agent behavior is non-deterministic (temperature > 0, multi-step tool-call branching), resample/replay the *same* task multiple times and use the **per-task average** as the unit of comparison, rather than a single noisy run — directly addresses the LLM non-determinism risk raised in Part B.3.
   - **Use paired-difference tests** when comparing the *same* task suite across two time windows/model versions — this removes task-difficulty variance and isolates the actual behavioral delta, giving tighter confidence intervals for the same sample size (Anthropic report frontier-model score correlations of 0.3–0.7 across shared question sets, meaning paired analysis is a "free" variance reduction).
   - **Run a power analysis** before deciding how many episodes/samples are needed to reliably detect a given effect size (e.g., "is a 5-point-percentage shift in tool-selection meaningfully detectable with N=200 episodes/day?") rather than assuming any sample size is adequate.

3. **Weight or gate drift by downstream impact, not raw magnitude** (borrowing NannyML's covariate-shift-impact formalism, A.1): a fingerprint dimension drifting a lot in a region uncorrelated with failure/escalation should not carry the same alarm weight as a smaller drift in a region historically correlated with poor outcomes. This requires ARISE-X to maintain (and periodically re-validate) a mapping from fingerprint-dimension movement → historical correlation with negative outcomes (e.g., via logistic regression or similar, akin to NannyML's CBPE approach).

4. **Aggregate across dimensions with an explicit, documented scoring rule — and avoid an opaque single "everything ok/not ok" composite** unless each sub-metric's classification (pass/marginal/fail, per-metric) is preserved and auditable, mirroring Kayenta's canary-judge architecture (per-metric classification → weighted group score → summary score with explicit "automatic fail" overrides for critical metrics). This traceability is what will make an "agent fingerprint drift" alert defensible/debuggable rather than a black box.

5. **Explicitly separate "statistically significant" from "practically/operationally significant"** (Evidently's warning in A.1, and Kayenta's two-stage classification: statistical significance test *first*, then a secondary effect-size/tolerance-band threshold check) — a drift can be statistically real (detectable given enough samples) but too small to warrant action. ARISE-X's design should require **both** a significance test pass *and* an effect-size threshold before declaring "drift," exactly as Kayenta's NetflixACAJudge does (98% CI outside a tolerance band of `±0.25×|effect estimate|`, **and** the ratio must exceed `allowedIncrease`/`allowedDecrease`).

**Bottom line:** the fingerprint concept is sound as a *monitoring surface*, but ARISE-X should explicitly commit to (a) per-dimension statistical tests appropriate to each metric's data type, (b) confidence intervals/SEM with clustering correction, (c) multi-run averaging for non-deterministic agents, (d) impact-weighted aggregation, and (e) a two-stage significance-then-effect-size gate — rather than a single composite "fingerprint distance" number compared to a static percentage threshold.

---

## Part B — SRE / CI-CD Reliability Gating

### B.1 Google SRE error-budget / SLO-SLI methodology and mapping to an "Agent Reliability Index" gate

Source: Google SRE Book, Ch. 3 "Embracing Risk" (https://sre.google/sre-book/embracing-risk/) and Ch. 4 "Service Level Objectives" (https://sre.google/sre-book/service-level-objectives/).

- **Core terminology:**
  - **SLI (Service Level Indicator)**: a carefully defined *quantitative measure* of some aspect of service level (e.g., latency, error rate, throughput).
  - **SLO (Service Level Objective)**: a *target* for an SLI, e.g., "99% of requests succeed."
  - **SLA (Service Level Agreement)**: an SLO with *consequences* attached (contractual); most of what people call "SLA" is actually an SLO.
  - **Error budget**: `1 − SLO`, i.e., the amount of allowed unreliability in a period (e.g., quarter). Framed as *both a floor and a ceiling* — 100% reliability is explicitly rejected as a goal because it's wasteful and imperceptible to users past a point of diminishing returns ("a user on a 99% reliable smartphone cannot tell the difference between 99.99% and 99.999% service reliability").
  - **Error budget as a release-velocity control loop**: "As long as the uptime measured is above the SLO... new releases can be pushed." When the budget is nearly drained, teams "self-police" — slowing releases or investing in resilience — without needing top-down mandate. This is explicitly framed as removing politics from reliability-vs-velocity negotiation between differently-incentivized teams (SRE vs. product/dev).
  - SRE explicitly recommends **percentiles over means** for latency-like SLIs (e.g., p50/p95/p99) because computing systems produce skewed distributions, and **averaging obscures the tail** where user pain concentrates — directly analogous to why ARISE-X should track distributional fingerprint metrics, not just averages, for step-count/cost/latency.
  - Guidance on choosing SLOs: **don't pick a target from current performance** (locks in status quo), **keep it simple** (complex aggregations obscure real changes), **avoid absolutes**, **have as few SLOs as possible** (each one must be "defensible" — i.e., you must be able to win a prioritization argument by citing it), and **perfection can wait** (start loose, tighten over time).

- **Direct mapping to an "Agent Reliability Index" (ARI) CI/CD gate:**
  - Treat the ARI as a *composite SLI* whose *SLO* (e.g., "ARI ≥ 0.85 measured over trailing N episodes") defines an **agent error budget** — the allowed rate of "unreliable" agent behavior (excess escalations, failed recoveries, goal deviation, cost overruns) per release period.
  - Gate CI/CD releases on **error-budget remaining**, not a single point-in-time ARI reading: if the trailing error budget is exhausted, block/slow releases and require investment in reliability work before shipping new agent capability — this is a much more defensible policy than "block if ARI < X today," because it accounts for trend and gives teams agency (self-policing) rather than a punitive gate.
  - Apply the SRE "few, defensible SLOs" principle: ARISE-X should resist bundling every fingerprint dimension into ARI directly; instead, pick the smallest set of dimensions that map to *user-facing or business-facing* harm (e.g., escalation rate, goal deviation, unrecovered-failure rate) and treat others (tool-selection %, step-count) as *diagnostic* signals that inform investigation but are not gate criteria themselves — mirroring SRE's distinction between an SLI/SLO (few, curated) and the many other operational metrics used for debugging.
  - Borrow the "safety margin" tactic (Ch. 4, "SLOs Set Expectations"): set the *internal* gating SLO for ARI stricter than the target you'd publish to users/stakeholders, giving headroom to react before an externally visible reliability failure.

### B.2 ML/agent canary and regression-gating precedent

- **Kayenta / Spinnaker Automated Canary Analysis (ACA)** — https://spinnaker.io/docs/guides/user/canary/canary-overview/ and https://spinnaker.io/docs/guides/user/canary/judge/. Originally built by Netflix for general service deployments, but its judgment methodology is a strong, battle-tested template for gating on statistical deltas of *any* metric set, including a prospective "reliability score":
  - Canary = partially roll out a change, then statistically compare metrics between the **canary** and a **baseline** (not "before vs. after" on the same population — avoids confounding from time-based effects).
  - **NetflixACAJudge default methodology**, directly reusable for an agent-reliability gate:
    1. NaN/missing-data handling policy per metric (`remove` vs `replace`, with explicit rules for what counts as `Nodata` vs. `NodataFailMetric`).
    2. Outlier removal via a *desensitized* IQR/Tukey-fence method (reduced sensitivity vs. standard Tukey, to avoid discarding real signal).
    3. **Mann-Whitney U test** per metric with a **98% confidence interval** — nonparametric, no distributional assumptions, appropriate for skewed operational metrics.
    4. A **tolerance band** (`±0.25 × Hodges-Lehmann estimate`) creates a dead-zone so small, statistically-detectable-but-trivial differences are ignored — this is the concrete implementation of "statistically significant ≠ practically significant" from Part A.
    5. Effect-size thresholds (`allowedIncrease`/`allowedDecrease`) are a **secondary gate** applied only after significance is established.
    6. **Critical metrics**: a single designated critical metric failing (e.g., an error-rate metric exceeding its critical threshold) can force the overall canary score to 0 regardless of the weighted average — i.e., no amount of "good" metrics can offset one seriously-broken critical one. This maps directly to how ARISE-X might designate, e.g., "goal deviation" or "escalation rate" as a critical/blocking fingerprint dimension distinct from advisory ones.
    7. **50% NODATA auto-fail rule** — if too much required data is missing, the canary fails safe rather than passing by default (important for ARISE-X: don't let a fingerprint dimension silently drop out of coverage and pass by omission).
  - This is a mature, directly transferable pattern: ARISE-X's proposed "reliability score delta" gate for agent deployments could be implemented nearly 1:1 on Kayenta's judge algorithm, substituting agent-fingerprint metrics for infrastructure metrics.

- **ML-specific regression/shadow-deployment practice**: classic MLOps guidance (Evidently AI, NannyML — Part A) converges on: (a) **shadow deployment** — run the new model/agent version in parallel on live traffic without serving its outputs, compare metrics against the production baseline before promoting; (b) **held-out regression test suites** with curated edge cases, run before every retrain/redeploy (Evidently's "How to address concept drift → Model retraining → Make sure you have a robust testing and roll-out process" guidance, https://www.evidentlyai.com/ml-in-production/concept-drift); (c) **LLM-specific eval levels**, per Hamel Husain's widely-cited "Your AI Product Needs Evals" (https://hamel.dev/blog/posts/evals/):
  - **Level 1 — Unit tests / assertions**: fast, cheap, deterministic checks run on every change (analogous to CI unit tests).
  - **Level 2 — Human & model (LLM-as-judge) eval**: applied to sampled traces on a regular cadence; requires periodically validating model-judge agreement against human labels (using **precision/recall**, not raw agreement, especially with imbalanced classes) rather than assuming the judge is trustworthy indefinitely.
  - **Level 3 — A/B testing**: for mature products only, measuring actual user-facing outcomes.
  - Explicit design principle: **100% pass rate is a product decision, not an assumption** — unlike classic software unit tests, LLM/agent eval pass rates are inherently probabilistic and the acceptable threshold must be chosen deliberately.

### B.3 Risks of hard-threshold/composite-score CI/CD gates, and industry mitigations

- **Goodhart's Law / metric gaming** (https://en.wikipedia.org/wiki/Goodhart%27s_law): "When a measure becomes a target, it ceases to be a good measure." Once an ARI-style composite score is used as a hard release gate, teams (or the agent itself, if any part of the system is optimized against the same metric, e.g., via prompt/skill tuning informed by the gate) will be incentivized to optimize the *measured* proxy rather than the *underlying* reliability it's meant to represent. Related/aggravating phenomena documented on the same page: **Campbell's Law** (quantitative social indicators become subject to corruption pressure the more they're used for decisions), **reward hacking** (AI systems optimizing a mis-specified reward without achieving the intended outcome), and the **Cobra effect** (perverse incentives making the underlying problem worse). Concrete cited precedents: hospitals gaming "length of stay" targets by discharging patients prematurely; the UK government's COVID-19 "100,000 tests/day" target being met via a redefinition (test *capacity* vs. tests *actually performed*) that undermined the target's original intent.
  - **Mitigation pattern from AI Agents That Matter (arXiv:2407.01502)**: benchmarks need **rigorous, adequately-sized holdout sets** that agent developers cannot see/tune against, precisely to prevent "overfitting" (i.e., gaming) the benchmark. ARISE-X's ARI gate should likewise reserve a held-out, periodically-rotated evaluation/fingerprint sample that is not visible to whatever process tunes agent prompts/skills, to reduce the surface for gaming.
  - **Mitigation pattern from Kayenta**: never rely on a single composite score alone — preserve per-metric classifications and a documented, inspectable scoring rule (group scores → weighted summary → explicit critical-metric override) so a gate failure/pass is auditable and gaming one sub-metric doesn't silently mask degradation elsewhere.
  - **General mitigation**: treat the composite score as a *diagnostic*/monitoring aid, and keep the *few, defensible* SLO-style metrics (per SRE guidance, B.1) as the actual gating criteria — fewer, harder-to-game, outcome-adjacent metrics beat one all-encompassing score.

- **LLM non-determinism causing flaky gates** — addressed extensively by Anthropic's evals-statistics work (A.3) and Hamel Husain's eval-levels framework (B.2):
  - **Multiple-run averaging / resampling**: rerun the same task/episode set multiple times and use the *per-task average* as the unit of comparison rather than a single sample, directly reducing the "random component" of variance (Anthropic, Recommendation #3).
  - **Confidence intervals via the Central Limit Theorem** (SEM, `mean ± 1.96×SEM`) instead of point-estimate pass/fail — a gate should compare *intervals*, not raw numbers, and treat overlapping CIs as "no significant difference" rather than a hard pass/fail flip on noise.
  - **Clustered standard errors** where episodes aren't independent (e.g., correlated failures within one task family) — naive variance estimates can understate true noise by 3x+, producing false "regression detected" alarms.
  - **Paired-difference testing** against the same task suite/version pair to cancel out task-difficulty variance — a "free" variance-reduction technique highly applicable to agent-version-over-version comparisons.
  - **Power analysis** to determine how many episodes are needed before a given effect size can be reliably detected — prevents both under-sampling (noisy false alarms) and wasted over-sampling.
  - **Two-stage significance-then-effect-size gating** (Kayenta pattern, B.2) as the concrete architecture: a metric only fails the gate if it is *both* statistically significant *and* exceeds a meaningful effect-size threshold — this single design choice directly prevents both "trivial-but-significant" and "large-but-noisy" false gate failures.
  - **LLM-as-judge-specific mitigation** (Hamel Husain, eugeneyan "Patterns for Building LLM-based Systems & Products" — https://eugeneyan.com/writing/llm-patterns/): periodically re-validate judge-model/human agreement using precision/recall (not raw agreement, which is misleading under class imbalance); mitigate position bias (evaluate response pairs in both orders), verbosity bias (control for length), and self-enhancement bias (don't use the same model family to judge its own outputs) if any part of the ARI pipeline uses an LLM judge to score fingerprint dimensions like "goal deviation."

---

## Clarifying Questions

None required — all three sub-questions in each part were answerable through the research conducted above. If ARISE-X wants deeper coverage, see "Recommended next research" below.

## Recommended Next Research (not completed this session)

- [ ] Deeper dive into PSI (Population Stability Index) exact formula/thresholds as used in credit-risk modeling, if ARISE-X wants to adopt PSI specifically (only high-level mention found; Evidently references it as a "distance metric" without giving the worked formula).
- [ ] Survey of open-source agent-tracing frameworks (LangSmith, Phoenix/Arize AX, Langfuse) for whether any already compute distributional statistics (not just per-trace eval scores) over tool-call sequences — Langfuse's blog was unreachable (404) during this session and was not otherwise investigated.
- [ ] Literature search on "trajectory-level" anomaly detection for sequential decision-making agents (e.g., RL literature on policy drift / behavioral cloning divergence) as a possibly more rigorous mathematical foundation for "step-count drift" and "goal-deviation drift" than generic distribution tests.
- [ ] Investigate NIST AI RMF / Google's "Patterns and problems in emerging multiagent systems" (Anthropic, linked from the evals-statistics page) for multi-agent-specific behavioral failure taxonomies that could sharpen the "escalation-rate" and "recovery-rate" fingerprint definitions.
