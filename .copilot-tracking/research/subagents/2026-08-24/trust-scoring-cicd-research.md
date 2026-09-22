# Research: Composite Trust/Reliability Scoring Design and CI/CD Regression-Gating Patterns for AI/ML and Agentic Systems

## Research Topics / Questions

1. Composite scoring methodologies (multiplicative vs weighted-additive): HDI, series-system reliability theory, FMEA RPN.
2. AI/ML trustworthiness standards: NIST AI RMF 1.0, ISO/IEC 42001, ISO/IEC 23894, EU AI Act risk categories, Model Cards, Datasheets for Datasets — do any prescribe composite scoring formulas?
3. CI/CD regression gating for ML: model regression testing, shadow deployment, canary release, champion/challenger, MLflow Model Registry gating, Azure ML validation gates, promptfoo CI integration.
4. Existing frameworks defining metrics analogous to: Agent Reliability Score, Agent Resilience Score, Behavioral Stability Index, Autonomy Efficiency Score, Multi-Agent Coordination Score.
5. Classical software reliability engineering theory (Musa models, MTTF/MTBF) applicable to "Resilience" and "Recovery" dimensions.

## Status: Complete

---

## 1. Composite Scoring Methodologies: Multiplicative vs. Weighted-Additive

### Human Development Index (HDI) — geometric mean (multiplicative), not arithmetic weighted sum

Source: https://en.wikipedia.org/wiki/Human_Development_Index, https://hdr.undp.org/data-center/human-development-index

- **Old method (pre-2010):** HDI was a simple **arithmetic (weighted) mean** of three normalized sub-indices (Life Expectancy Index, Education Index, Income/GDP Index), each weighted 1/3: `HDI = (1/3)·LEI + (1/3)·EI + (1/3)·II`.
- **New method (2010 onward):** UNDP switched explicitly to the **geometric mean**: `HDI = (LEI · EI · II)^(1/3)`.
- **Why UNDP switched:** The stated rationale (UNDP "Composite indices — HDI and beyond", Kovacevic 2010 "Review of HDI Critiques and Potential Improvements") was that the arithmetic mean allows **perfect substitutability** across dimensions — a very high score in income can fully compensate for a very low score in health or education. The geometric mean penalizes imbalance: it rewards a more *equal* distribution of achievement across dimensions and cannot be pushed up by excellence in only one dimension while another is near zero. This is conceptually the same argument ARISE-X is making for the multiplicative ARI formula.
- **Key mathematical property:** For normalized sub-scores in [0,1], the geometric mean is always ≤ the arithmetic mean (AM-GM inequality), and the gap widens as the sub-scores become more dispersed/unequal. A geometric mean of n terms goes to 0 as any single term goes to 0, whereas an arithmetic mean only drops by 1/n of that term's contribution. This is the formal way to describe "a catastrophic weakness in one dimension cannot be hidden by excellence elsewhere" — it applies to geometric mean, and applies even more strongly to a raw product (which is a geometric mean without the root normalization).
- **Documented criticism of HDI (useful as counter-argument material for ARISE-X to pre-empt):** Wolff, Chong & Auffhammer (2011, *Economic Journal*) showed HDI's formula changes and data-error propagation cause large numbers of countries to be misclassified across tiers — a caution about instability/sensitivity of composite indices to formula and normalization choices. Reviewers have also noted the change from arithmetic to geometric mean was itself controversial and re-ranked many countries, illustrating that the *choice* of aggregation function is a first-order design decision with large downstream consequences — directly relevant to justifying/documenting ARISE-X's choice.

### Reliability engineering: series-system reliability = product of component reliabilities

Source: https://en.wikipedia.org/wiki/Reliability_engineering, https://en.wikipedia.org/wiki/Reliability_block_diagram

- Reliability is formally a probability: `R(t) = Pr{T > t} ∈ [0,1]`.
- For a **series system** (all components must work for the system to work — the classic "weakest link" topology), Reliability Block Diagram (RBD) theory gives:
  `R_system(t) = R_1(t) × R_2(t) × ... × R_n(t)`
  This is an exact probabilistic identity under the assumption of statistical independence of failure modes: the system only succeeds if *every* component succeeds, so probabilities multiply.
- For a **parallel/redundant system** (only one of n needs to work), unreliability multiplies instead: `Q_system = Q_1 × Q_2 × ... × Q_n` where `Q = 1 - R`.
- **This is the strongest, most directly transferable piece of prior art for ARISE-X.** If each ARI dimension (Goal Success, Resilience, Behavioral Stability, Safety, Recovery, Efficiency) is modeled as an independent "component" that must all be functioning for the agent to be considered "reliable" (a series/AND topology of trust), then the product-of-normalized-scores formula is the textbook reliability-engineering analog of RBD series-system math. This gives ARISE-X a rigorous engineering justification: "an agent is only as reliable as its weakest necessary capability," matching real reliability theory rather than being an ad hoc penalty function.
- Caveat for the research: reliability theory's product rule technically applies to *probabilities of independent binary success/failure events over a defined mission*, not to arbitrary [0,1]-normalized continuous quality scores. ARISE-X's ARI dimensions are more like continuous performance ratios than independent probabilities, so the analogy is a strong *design metaphor and defensible convention*, not a strict mathematical derivation. This distinction matters for how ARISE-X documentation frames the formula (motivated-by vs. derived-from).

### FMEA Risk Priority Number (RPN) — multiplicative risk scoring, with well-documented pitfalls

Source: https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis

- Classic formula: `RPN = Severity × Occurrence(Probability) × Detection`, each rated on an ordinal scale (commonly 1–10).
- This is the most widely cited **multiplicative composite risk score** in industrial/safety engineering (originating in MIL-STD-1629, used across aerospace, automotive, medical device industries since the 1960s).
- **Critical, well-documented limitation directly relevant to ARISE-X:** Because Severity/Occurrence/Detection are *ordinal* rankings (not ratio-scale measurements), multiplying them is mathematically improper — ordinal numbers don't support multiplication meaningfully, and this causes **rank reversals**: a less-severe failure mode can receive a higher RPN than a more severe one purely as an artifact of the multiplication (Kmenta & Ishii 2004, *J. Mechanical Design*). Proposed fixes include fuzzy-logic RPN alternatives (Jee, Tay & Lim 2015, *IEEE Trans. Reliability*) and, in the 2019 AIAG/VDA FMEA handbook, RPN itself was **replaced** by "Action Priority" (AP), a lookup-table-based ranking, specifically because of these multiplicative-scale problems.
- **Actionable implication for ARISE-X:** If ARI's six dimensions are normalized to a true ratio/interval [0,1] scale (e.g., actual success rate, actual latency ratio) rather than ordinal buckets (e.g., "1–5 severity rating"), the RPN rank-reversal critique does not directly apply — but ARISE-X's design documentation should explicitly state that sub-scores are ratio-scale (not ordinal Likert/bucket scores) to pre-empt this exact criticism, since it is the single most common critique leveled at multiplicative scoring schemes in the reliability/risk literature.

### Weighted-additive vs. multiplicative: general trade-offs (synthesized)

| Property | Weighted-additive (Σ wᵢxᵢ) | Multiplicative / geometric mean (Πxᵢ or (Πxᵢ)^(1/n)) |
|---|---|---|
| Compensability | Fully compensatory — a 0 in one dimension can be offset by high scores elsewhere | Non-compensatory (or only partially so) — a score near 0 in any dimension collapses the whole index toward 0 |
| Interpretability | Simple, linear, easy to explain and to attribute ("dimension X contributed Y points") | Less linearly interpretable; requires log-transform or per-dimension attribution to explain |
| Sensitivity to scale/units | Sensitive to weight choice, but tolerant of sub-score scale differences if normalized | Requires all sub-scores to be strictly positive and on comparable normalized scales; a literal 0 anywhere forces the whole product to 0 (may be desired or may be an availability/edge-case bug depending on intent) |
| Statistical/ordinal validity | Valid for any measurement level (ordinal, interval, ratio) with appropriate caveats | Strictly valid only for ratio-scale measurements; invalid/misleading for ordinal rankings (see FMEA RPN critique above) |
| Use case fit | Appropriate when dimensions are substitutable/tradeable (e.g., portfolio scoring, HDI pre-2010) | Appropriate when dimensions are jointly necessary/AND-conditions (e.g., series-system reliability, safety-gated release) |
| Precedent | HDI pre-2010, most credit-scoring/composite KPI systems | HDI 2010+, series-system RBD reliability, FMEA RPN (with caveats), and generally any "weakest-link" gating logic |

**Conclusion for ARISE-X's framing:** The multiplicative ARI design is well-precedented (HDI's post-2010 shift, RBD series-system theory) specifically *because* the explicit design goal is non-compensability — preventing a highly efficient-but-unsafe agent from scoring well. This should be framed as a deliberate choice for an AND/series-reliability topology across dimensions, and the design documentation should address the FMEA RPN ordinal-scale pitfall by confirming sub-scores are ratio/interval measurements, not ordinal buckets.

---

## 2. AI/ML Trustworthiness Standards and Frameworks

### NIST AI Risk Management Framework (AI RMF 1.0, Jan 2023)

Source: https://www.nist.gov/itl/ai-risk-management-framework, https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/

NIST AI RMF 1.0 defines **seven characteristics of trustworthy AI** (Section 3):

1. **Valid and Reliable** — treated as the *foundational* characteristic (shown as the base of the trustworthiness diagram); reliability defined per ISO/IEC TS 5723:2022 as "ability of an item to perform as required, without failure, for a given time interval, under given conditions." Encompasses accuracy and robustness/generalizability.
2. **Safe** — AI should not, under defined conditions, endanger human life, health, property, or environment.
3. **Secure and Resilient** — NIST explicitly distinguishes **security** (confidentiality/integrity/availability, protection against adversarial examples/data poisoning/exfiltration) from **resilience** (ability to withstand/recover from unexpected adverse events, "degrade safely and gracefully"). Resilience relates to robustness but extends to adversarial/unexpected misuse.
4. **Accountable and Transparent** — transparency about how/when decisions were made; treated as a cross-cutting characteristic (spans all others) rather than a peer dimension.
5. **Explainable and Interpretable** — explainability = mechanism ("how"); interpretability = meaning/context ("why").
6. **Privacy-Enhanced** — autonomy, identity, and dignity safeguards; tension/tradeoffs with accuracy and fairness noted explicitly.
7. **Fair — with Harmful Bias Managed** — three bias categories: systemic, computational/statistical, human-cognitive.

**Key finding directly relevant to ARISE-X's Q1:** NIST AI RMF 1.0 **does not prescribe any composite scoring formula** (additive, multiplicative, or otherwise) across these seven characteristics. The framework explicitly states: *"trustworthiness is a social concept that ranges across a spectrum and is only as strong as its weakest characteristics"* and *"human judgment should be employed when deciding on the specific metrics... and precise threshold values."* This "weakest characteristic" framing is qualitative but directly echoes the philosophy behind a multiplicative/non-compensatory ARI — NIST's own prose gestures at a "weakest-link" mental model without formalizing it mathematically, which ARISE-X could cite as conceptual (not formulaic) support. NIST deliberately leaves aggregation/weighting as an organizational risk-management judgment call rather than standardizing a formula, likely because trade-offs between characteristics are context-dependent (e.g., interpretability vs. privacy).

### ISO/IEC 42001:2023 (AI Management System)

Source: https://www.iso.org/standard/81230.html

- World's first AI management system standard (management-system format like ISO/IEC 27001 for information security), published Dec 2023.
- Specifies requirements for establishing/implementing/maintaining/improving an **AI Management System (AIMS)** — organizational governance processes, not technical scoring metrics.
- Benefits stated: "framework for managing risk and opportunities," "traceability, transparency and reliability." It is process/governance-oriented (Plan-Do-Check-Act style), analogous to how ISO 27001 governs security programs rather than defining a security score.
- **No composite scoring formula defined.** It's a certifiable management-system standard, not a metrics/formula standard. (Could not access ISO/IEC 23894 full text directly — it is ISO's AI risk-management guidance, structurally analogous to ISO 31000 risk management applied to AI; treat as a gap — see Recommended Next Research below.)

### EU AI Act (Regulation (EU) 2024/1689)

Source: https://en.wikipedia.org/wiki/Artificial_Intelligence_Act, https://artificialintelligenceact.eu/high-level-summary/

- Defines **four risk tiers + one cross-cutting category**, not a continuous score:
  1. **Unacceptable risk** — banned (e.g., social scoring, manipulative AI, most real-time biometric ID in public).
  2. **High-risk** — subject to conformity assessment, risk-management system, data governance, technical documentation, human oversight, accuracy/robustness/cybersecurity requirements (Annex III use-case list: employment, credit, law enforcement, education, critical infrastructure, etc.).
  3. **Limited risk** — transparency obligations only (e.g., disclose AI interaction, label deepfakes).
  4. **Minimal risk** — unregulated (most applications).
  5. **General-Purpose AI (GPAI)** — separate transparency/documentation regime; models trained with >10^25 FLOPs face additional "systemic risk" evaluation, adversarial testing, and incident reporting obligations.
- **No composite trust/reliability score is defined anywhere in the Act.** It is a categorical/binary compliance regime (pass/fail conformity assessment against enumerated requirements), not a continuous scoring system. This is a notable contrast to ARISE-X's continuous [0,1] ARI — regulatory frameworks to date use discrete risk *tiers* and binary conformity gates, not continuous composite indices. ARISE-X's continuous ARI could be framed as complementary tooling that could feed evidence into (but does not replace) tier-based regulatory conformity assessments.

### Model Cards for Model Reporting (Mitchell et al., 2018/2019, FAT* '19)

Source: https://arxiv.org/abs/1810.03993

- Proposes short structured documents accompanying released ML models: benchmarked evaluation across demographic/phenotypic/intersectional subgroups, intended use context, evaluation methodology, and caveats.
- **No aggregate score** — deliberately disaggregated, multi-slice reporting (the opposite design philosophy from a single composite index). The explicit goal is to *prevent* collapsing multi-dimensional performance into one number, to avoid hiding subgroup disparities — arguably the same underlying concern ARISE-X addresses via non-compensability, but solved by *not aggregating at all* rather than aggregating non-compensatorily. Worth noting as an alternative philosophy: full disaggregation (Model Cards) vs. non-compensatory aggregation (ARISE-X's multiplicative ARI). These are complementary rather than conflicting — ARISE-X could report both the composite ARI *and* the disaggregated per-dimension/per-scenario "card."

### Datasheets for Datasets (Gebru et al., 2018/2021, CACM)

Source: https://arxiv.org/abs/1803.09010

- Analogous documentation standard for datasets (motivation, composition, collection process, recommended uses) — electronics-industry-datasheet analogy. No scoring formula; purely documentation/transparency artifact. Relevant to ARISE-X mainly as precedent for "structured artifact accompanying an AI asset" documentation patterns (could inspire an "Agent Card" alongside the ARI score).

**Overall Q2 finding:** None of the surveyed standards (NIST AI RMF, ISO/IEC 42001, EU AI Act, Model Cards, Datasheets) prescribe a composite scoring formula. They converge on **qualitative multi-dimensional characteristics** and/or **discrete compliance tiers**, leaving quantitative aggregation as an open, unstandardized problem space — which is exactly the gap ARISE-X's ARI is positioned to fill. NIST's "only as strong as its weakest characteristic" language is the closest qualitative precedent for a non-compensatory/multiplicative design philosophy.

---

## 3. CI/CD Regression Gating for ML Models

### MLOps principles and automation levels

Source: https://ml-ops.org/content/mlops-principles

- Three MLOps automation maturity levels: (1) manual process, (2) ML pipeline automation (continuous training), (3) full CI/CD pipeline automation.
- Relevant CI/CD-adjacent concepts: **Continuous Integration** (test/validate code, data, *and models*), **Continuous Delivery** (auto-deploy training pipeline → model prediction service), **Continuous Training** (auto-retrain on new data), **Continuous Monitoring** (production model/business-metric tracking).
- **"ML Test Score" rubric** (Breck et al. 2017, Google) — a widely cited scoring rubric for ML production-readiness across four sections: Data Tests, Model Tests, ML Infrastructure Tests, Monitoring. Score = minimum across the four section scores (another **non-compensatory, "weakest section"** design — same philosophy as ARISE-X's multiplicative ARI, implemented via `min()` instead of a product). This is strong precedent: an industry-recognized, widely cited ML production-readiness score is explicitly **non-compensatory by design** (using min, the most extreme form of non-compensability), reinforcing that "weakest-link" scoring is an accepted, precedented approach in ML engineering, not a novel or risky choice.
- Explicit regression-relevant testing practices called out in ML Test Score / MLOps literature:
  - "Setting a threshold and testing for **slow degradation** in model quality over many versions on a validation set."
  - "Setting a threshold and testing for **sudden performance drops** in a new version of the model."
  - "ML models are **canaried** before serving."
  - Model Change Failure Rate = "difference in currently deployed model performance metrics to the previous model's metrics" (precision/recall/F1/accuracy/AUC/false-positive-rate) — directly analogous to what ARISE-X would compute as an ARI regression delta.

### MLflow Model Registry — gating primitives

Source: https://mlflow.org/docs/latest/ml/model-registry/

- Core registry concepts: **Registered Model → Model Version → Model Alias → Tags**.
- **Model Aliases** (e.g., `@champion`) are MLflow's built-in champion/challenger mechanism: a mutable named pointer to a specific model version; production traffic targets the alias URI (`models:/MyModel@champion`), and promotion = reassigning the alias to a new version.
- **Tags** are the native mechanism for gating: e.g., `validation_status:pending` vs `validation_status:approved`, or `pre_deploy_checks:"PASSED"`. This is how MLflow supports a validation-gate workflow without a dedicated "gate" API — CI/CD pipelines are expected to (a) register a new model version, (b) run automated validation, (c) tag the version pass/fail, (d) only reassign the `@champion`/`production` alias if the tag indicates pass.
- No built-in statistical regression-detection is provided by MLflow itself — that logic lives in the surrounding CI/CD pipeline (exactly the gap ARISE-X's ARI regression gate would fill for agentic systems).

### Champion/Challenger pattern

- Could not retrieve a dedicated reference page (Wikipedia article does not exist under that title), but the pattern is corroborated via MLflow's alias mechanism and general MLOps literature: champion = current production model; challenger = candidate new version; promotion happens only after the challenger meets/exceeds champion on defined metrics (often via shadow traffic or A/B test), directly analogous to what ARISE-X would need for gating a new agent/prompt/model version against the previously-deployed ARI baseline.

### promptfoo — CI/CD integration for LLM apps (closest existing analog to an "ARI CI gate" in production)

Source: https://www.promptfoo.dev/docs/integrations/ci-cd/

- Explicit stated goals: "Catch regressions early," "Quality gates - Enforce minimum performance thresholds," "Compliance - Generate reports for OWASP, NIST."
- Concrete quality-gate pattern used in GitHub Actions/Jenkins examples:
  ```
  FAILURES=$(jq '.results.stats.failures' results.json)
  if [ "$FAILURES" -gt 0 ]; then exit 1; fi
  ```
  and a pass-rate threshold gate:
  ```
  PASS_RATE=$(jq '.successes / (.successes + .failures) * 100' results.json)
  if (( $(echo "$PASS_RATE < 95" | bc -l) )); then echo "Quality gate failed"; exit 1; fi
  ```
- Supports `--fail-on-error`, JUnit XML output (native CI test-report integration), tagging evals with CI metadata (`--tag ci.run-id=...`, `--tag git.sha=...`), and scheduled red-team/security scans as separate CI jobs from functional eval.
- This is the most directly analogous existing tool to what ARISE-X would need to build for CI/CD-gating an ARI score: a CLI eval step producing a machine-readable score artifact, a threshold comparison step, and a non-zero exit code to fail the pipeline/block merge. ARISE-X's novelty over promptfoo is (a) the multiplicative multi-dimension composite score itself (promptfoo's gates are typically single-metric pass-rate/threshold checks, not a formal multi-dimensional non-compensatory index) and (b) explicit baseline-vs-candidate regression comparison rather than only absolute-threshold gating.

### Azure ML — not directly retrieved in this pass (see Recommended Next Research)

---

## 4. Existing Frameworks with Analogous Metrics (Agent Reliability / Resilience / Stability / Efficiency / Coordination)

Searched via arXiv API (`export.arxiv.org/api/query`) for exact/near-exact terminology.

### Closest direct analog: "Towards a Science of AI Agent Reliability" (Rabanser, Kapoor, Utpala, Narayanan et al.)

Source: https://arxiv.org/abs/2602.16666 (accepted ICML 2026; interactive dashboard at hal.cs.princeton.edu/reliability)

- **This is the single most important prior-art hit for ARISE-X.** The paper argues that "compressing agent behavior into a single success metric obscures critical operational flaws" and proposes **twelve concrete metrics decomposing agent reliability along four key dimensions: consistency, robustness, predictability, and safety.**
- Directly validates ARISE-X's core thesis (single scalar success metrics are insufficient) and independently arrives at a multi-dimensional decomposition of "agent reliability," though with different named dimensions (consistency/robustness/predictability/safety vs. ARISE-X's Goal Success/Resilience/Behavioral Stability/Safety/Recovery/Efficiency). Notably this paper does **not** appear (from the abstract) to propose a single composite index/formula — it reports the twelve metrics as a "holistic performance profile" rather than collapsing them into one number, which is a meaningful contrast/gap ARISE-X's ARI could fill (going from a *diagnostic dashboard* to a *single CI/CD-gateable score*).
- Finding: "recent capability gains have only yielded small improvements in reliability" — i.e., benchmark accuracy improvements do not translate to reliability improvements, reinforcing the case for reliability-specific (not just accuracy-based) gating.

### "Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended Interactions" (Rath, 2026)

Source: https://arxiv.org/abs/2601.04170

- Defines **"Agent Stability Index (ASI)"** — explicitly named "a novel composite metric framework for quantifying drift across twelve dimensions, including response consistency, tool usage patterns, reasoning pathway stability, and inter-agent agreement rates."
- Decomposes "agent drift" into three types: **semantic drift** (deviation from original intent), **coordination drift** (breakdown in multi-agent consensus), **behavioral drift** (emergence of unintended strategies). This maps closely onto ARISE-X's "Behavioral Stability Index" naming and concept — ASI is the closest known named-metric precedent to ARISE-X's proposed Behavioral Stability Index. Worth noting ARISE-X should differentiate its BSI clearly from this ASI (composite methodology, dimension count, whether multiplicative) since the name space is close.

### "AI Agents Do Not Fail Alone: The Context Fails First" (Bousetouane, 2026)

Source: https://arxiv.org/abs/2607.14275

- Introduces **ProofAgent-Harness**, evaluating context quality across seven criteria including **"token efficiency"** as one of the scored dimensions feeding into agent reliability prediction — a direct precedent for treating token/cost efficiency as a first-class reliability-adjacent dimension (supporting ARISE-X's "Autonomy Efficiency Score" concept), and for isolating a context/efficiency score from behavioral outcome metrics ("context score is isolated from behavioral metrics and release decisions, enabling non-circular validation") — a methodological point relevant to how ARISE-X should structure ARI's efficiency sub-score independent of goal-success sub-score to avoid circularity.

### "Kamiwaza Agentic Merit Index (KAMI)" (Roig, 2025)

Source: https://arxiv.org/abs/2511.08042

- An enterprise-focused benchmark/index ("Towards a Standard, Enterprise-Relevant Agentic AI Benchmark") explicitly branded as an "index," evaluated over 5.5B tokens across 35 model configs, reporting cost-performance tradeoffs and token efficiency alongside task success. This is the closest branded "index" precedent by naming convention (`[X] Agentic/Reliability Index`) though it is a benchmark leaderboard rather than a CI/CD gating mechanism, and its aggregation methodology was not visible from the abstract (flagged for deeper follow-up if needed).

### Multi-Agent Coordination Score

Source: arXiv search `abs:"coordination score" AND abs:"multi-agent"` (2 results)

- "Language-Driven Coordination and Learning in Multi-Agent Simulation Environments" (LLM-MARL) reports **"coordination score"** as one of several evaluation metrics (alongside win rate, zero-shot generalization) in game-environment multi-agent RL, benchmarked against MAPPO/QMIX baselines.
- A second paper (decentralized energy markets) reports a numeric "coordination score of 91.7% relative to the theoretical centralized benchmark," used as a ratio-to-optimal metric.
- **No paper defines a standardized, widely adopted "Multi-Agent Coordination Score" as a named formal metric class** comparable to, e.g., F1-score or BLEU. Usage found is ad hoc/paper-specific. This is a genuine naming/methodology gap ARISE-X's proposed Multi-Agent Coordination Score could occupy, but ARISE-X should not claim to be building on an established, standardized "MACS" — none exists yet in the literature surveyed.

### Exact-term searches with zero results (naming-space is open)

- `"agent reliability index"` (arXiv full-text, all fields): **0 results** — the exact term "Agent Reliability Index (ARI)" does not appear to be already in use in arXiv-indexed literature, suggesting ARISE-X's name is likely available/novel in the academic literature (should still be checked against industry blogs/trademark, not covered by this search).
- `ti:"reliability index" AND abs:agent`: **0 results.**
- `"agent reliability" AND "composite score"`: **0 results** for the exact composite-score framing paired with agent reliability.

**Overall Q4 finding:** No existing paper defines a metric suite/composite index with exactly ARISE-X's five/six named dimensions (Goal Success, Resilience, Behavioral Stability, Safety, Recovery, Efficiency, Multi-Agent Coordination) or an "Agent Reliability Index" by that name. The closest and most citation-worthy prior art is (a) Rabanser/Kapoor/Narayanan's 12-metric/4-dimension reliability decomposition (ICML 2026) as the strongest academic validation of "don't collapse agent quality into one metric, but do decompose it rigorously," and (b) the "Agent Stability Index (ASI)" in the Agent Drift paper as the closest named analog to Behavioral Stability Index specifically.

---

## 5. Classical Software Reliability Engineering Theory (Musa Models, MTTF/MTBF)

Source: https://en.wikipedia.org/wiki/Software_reliability_testing, https://en.wikipedia.org/wiki/List_of_software_reliability_models, https://en.wikipedia.org/wiki/Reliability_engineering (Software reliability section)

- **Core quantities:**
  - `MTTF` (Mean Time To Failure) — average operating time before a failure.
  - `MTTR` (Mean Time To Repair) — average time to restore service after failure.
  - `MTBF = MTTF + MTTR` (Mean Time Between Failures).
  - `Availability A = MTTF / MTBF = MTTF / (MTTF + MTTR)`.
  - `Failure rate λ = 1 / MTBF`; reliability decays as `R(t) = e^(−λt)` under the (simplifying) exponential/constant-failure-rate assumption.
- **John Musa's software reliability engineering (SRE)** — foundational reference: Musa, *Software Reliability Engineering: More Reliable Software, Faster and Cheaper* (2nd ed., 2004). Musa-style **Software Reliability Growth Models (SRGMs)** (exponential, logarithmic, S-shaped, Goel-Okumoto, etc.) model cumulative failure counts/failure intensity as a function of test/execution time, used to project MTTF improvements as testing continues and defects are removed. Key nuance directly relevant to ARISE-X: **software does not fail from "wear," it fails from unanticipated input/state combinations triggering latent defects** — this is a crucial conceptual bridge to why "Resilience" (withstanding unexpected conditions) and "Recovery" (MTTR-like restoration) are the right *classical* reliability-theory analogs for the two dimensions the user named, since classical hardware MTBF assumptions (wear-out, bathtub curve) don't apply, but the failure-rate/repair-rate (MTTF/MTTR) framing translates well to agent "time between failures in a session" and "time/turns to recover from a failure."
- **Direct mapping for ARISE-X dimension grounding:**
  - **Resilience** ≈ classical "robustness"/"withstand adverse/unexpected conditions and degrade gracefully" (this is literally NIST AI RMF's definition of resilience, itself adapted from ISO/IEC TS 5723:2022) + can be operationalized via an MTTF-like metric: mean number of turns/tasks/tool-calls between agent-observed failures under perturbation or adversarial conditions.
  - **Recovery** ≈ classical MTTR / repair-rate concept: given a failure occurs, how quickly (in turns, wall-clock time, or tokens) does the agent self-correct, roll back, or escalate to a human, and does it recover to a *correct* state (not just *any* state)? Availability-style formulas (`MTTF/(MTTF+MTTR)`) could inspire a normalized "uptime-equivalent" sub-score for Recovery.
- **Software Reliability Growth Models** are also relevant to CI/CD regression gating conceptually: SRGMs are used in classical practice to decide **when testing has reduced the defect rate enough to ship** — i.e., they are historically *the* quantitative basis for a release/regression gate in software engineering, directly precedent-setting for using a reliability metric (like ARI) as a CI/CD ship/no-ship gate rather than only a monitoring dashboard metric.
- **Caveat:** Musa-style SRGMs assume a *single deployed artifact accumulating execution time/test cases*, and a monotonically improving (or at least trackable) defect-discovery curve. LLM-based agents are non-deterministic, don't have "defects" being incrementally patched in the same sense, and behavior can vary run-to-run for the same "version" — so the direct SRGM curve-fitting math (e.g., Goel-Okumoto NHPP model) likely does not transfer as-is to agent reliability; the *concepts* (MTTF/MTTR framing, failure-rate-based gating, reliability growth over iterations) transfer better than the *specific parametric models*. This nuance should be stated explicitly if ARISE-X cites Musa/SRGM as grounding, to avoid overclaiming direct applicability.

---

## Summary Table: Key Sources

| # | Topic | Key Source(s) |
|---|---|---|
| 1 | HDI geometric mean methodology | https://en.wikipedia.org/wiki/Human_Development_Index ; https://hdr.undp.org/data-center/human-development-index |
| 2 | Series-system reliability (product rule) | https://en.wikipedia.org/wiki/Reliability_block_diagram ; https://en.wikipedia.org/wiki/Reliability_engineering |
| 3 | FMEA RPN multiplicative scoring + rank-reversal critique | https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis |
| 4 | NIST AI RMF 1.0 trustworthiness characteristics | https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/ ; https://www.nist.gov/itl/ai-risk-management-framework |
| 5 | ISO/IEC 42001 AI management system | https://www.iso.org/standard/81230.html |
| 6 | EU AI Act risk tiers | https://en.wikipedia.org/wiki/Artificial_Intelligence_Act ; https://artificialintelligenceact.eu/high-level-summary/ |
| 7 | Model Cards | https://arxiv.org/abs/1810.03993 |
| 8 | Datasheets for Datasets | https://arxiv.org/abs/1803.09010 |
| 9 | MLOps principles / ML Test Score | https://ml-ops.org/content/mlops-principles |
| 10 | MLflow Model Registry (aliases/tags as gating) | https://mlflow.org/docs/latest/ml/model-registry/ |
| 11 | promptfoo CI/CD quality gates | https://www.promptfoo.dev/docs/integrations/ci-cd/ |
| 12 | "Towards a Science of AI Agent Reliability" (12 metrics / 4 dims) | https://arxiv.org/abs/2602.16666 |
| 13 | "Agent Drift" — Agent Stability Index (ASI) | https://arxiv.org/abs/2601.04170 |
| 14 | Context quality incl. token efficiency as reliability predictor | https://arxiv.org/abs/2607.14275 |
| 15 | Kamiwaza Agentic Merit Index (KAMI) | https://arxiv.org/abs/2511.08042 |
| 16 | Multi-agent "coordination score" usage | http://export.arxiv.org/abs/2506.04251 ; http://export.arxiv.org/abs/2602.16062 |
| 17 | Software reliability testing (MTTF/MTBF/MTTR, SRGM) | https://en.wikipedia.org/wiki/Software_reliability_testing ; https://en.wikipedia.org/wiki/List_of_software_reliability_models |

---

## Recommended Next Research (Not Completed This Session)

- [ ] Full text of **ISO/IEC 23894** (AI risk management guidance) — only inferred by analogy to ISO 31000; could not access primary source in this session.
- [ ] **Azure ML model validation/deployment gates** (e.g., managed online endpoint safe rollout, model monitoring integration) — not retrieved in this pass; user's research question explicitly asked for this.
- [ ] Deeper dive into **Kamiwaza KAMI's actual aggregation formula** (is it additive, multiplicative, or a leaderboard rank?) — abstract didn't disclose methodology.
- [ ] Full text of the **"Towards a Science of AI Agent Reliability"** paper (beyond abstract) to confirm whether/how its 12 metrics are aggregated, and whether it discusses CI/CD gating use cases.
- [ ] Full text of the **"Agent Drift" / Agent Stability Index** paper to compare ASI's exact aggregation formula (weighted-sum vs. multiplicative) against ARISE-X's proposed formula — important for differentiation/citation.
- [ ] Search **industry engineering blogs** (not just arXiv) for "Agent Reliability Index," "AI regression gate," "LLMOps release gate" — arXiv-only search may miss practitioner blog posts (e.g., from LangChain, Anthropic, OpenAI Cookbook, Weights & Biases, Galileo, Arize) that could be closer industry prior art than academic papers.
- [ ] Investigate **shadow deployment** and **canary release** as distinct named patterns with dedicated sources (a dedicated Wikipedia "Champion/challenger" article does not exist; a canary-release-specific and shadow-deployment-specific source pass would strengthen Q3 coverage).
- [ ] Check whether **Musa's original book / IEEE Software Reliability Engineering standard (IEEE 1633)** has been explicitly adapted by any recent paper for LLM/agent reliability (only the general Wikipedia summary was consulted, not primary Musa text or IEEE 1633).

## Clarifying Questions

- Should the research also cover **non-English-language** or **preprint-only** sources (e.g., Chinese AI safety literature, which has active agent-reliability research)? This pass was English/arXiv/Wikipedia-centric.
- Is there a target publication/pitch venue for ARISE-X (e.g., an academic workshop paper vs. an internal engineering doc vs. a public blog post)? This would change which of the "Recommended Next Research" items are highest priority — e.g., academic-venue framing would prioritize the ICML 2026 paper's full text and formal differentiation, while an internal engineering doc would prioritize Azure ML / promptfoo / MLflow gating mechanics.
