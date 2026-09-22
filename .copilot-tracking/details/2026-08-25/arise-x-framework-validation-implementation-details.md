<!-- markdownlint-disable-file -->
# Implementation Details: ARISE-X Framework Validation Roadmap

## Context Reference

Sources:

* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md
* .copilot-tracking/research/subagents/2026-08-25/planning-anchor-verification.md
* .copilot-tracking/research/subagents/2026-08-25/codebase-analysis.md
* .copilot-tracking/research/subagents/2026-08-25/agent-eval-landscape.md
* .copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md
* .copilot-tracking/research/subagents/2026-08-25/chaos-engineering-precedent.md
* .copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md
* intial analysis and requirement.md
* .copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/mve-plan.md

The implementation follows the research sequence but divides contract creation from shared integration. Research Stage 0 maps to Implementation Phases 0-1, Stage 1 maps to Phases 2-3, and Stages 2-4 map to Phases 4-6. Phase 7 is final validation.

## Planning Defaults

The following defaults resolve implementation-blocking decisions identified by research. They are configuration defaults and replaceable framework contracts, not permanent product constraints.

* Use `PyYAML` for typed experiment/scenario input, `scipy` for nonparametric statistical tests, and development-only `httpx` for FastAPI `TestClient`. Add runtime packages through `uv add` and `httpx` through `uv add --dev httpx`, preserving the uv-managed dependency workflow.
* Use a deterministic in-process scripted agent adapter to prove the `AgentUnderTest` execution contract. Use the procurement workflow from the original requirement as the first versioned example scenario. External model/provider adapters remain outside the core MVP.
* Identify the golden baseline by an explicit `baseline_run_id`. Persist agent version, scenario version, configuration fingerprint, seed, and source revision as baseline metadata so comparisons are auditable.
* Treat goal success and safety as critical auto-fail dimensions. Compare baseline and candidate on the same held-out tasks and seeds. Use a 98% confidence level, target power of at least 0.80, and per-dimension minimum detectable effects. Derive the required sample size from baseline variance/rates and the selected test; a 30-pair fixture floor validates plumbing but never proves deployment-gate power.
* Version an evaluation-suite manifest with development and held-out partitions, task-family cluster identifiers, owner, rotation deadline, and a protected payload locator. Keep held-out task payloads outside tuning-visible repository content and persist only task IDs, fingerprints, and evaluation evidence.
* Define the reliability SLI as the proportion of eligible episodes that achieve the goal, avoid critical safety violations, and recover when a configured fault is verified. The example SLO is configurable and evaluated over a trailing 28-day or bounded-episode window; release policy combines baseline/candidate regression, evidence sufficiency, and remaining production error budget.
* Use a star coordinator-worker topology for the first multi-agent implementation. Measure milestones for assignment, information exchange, handoff, verification, and objective completion before evaluating other topologies.
* Preserve current public functions and response keys through defaulted fields and compatibility facades. Schedule deliberate wrapper removal separately before 1.0.

## Implementation Phase 0: Scenario And Persistence Contracts

<!-- parallelizable: true -->

Phase 0 contains two independent tracks. Scenario/configuration work and versioned persistence work can be assigned in parallel because they modify disjoint modules and tests. Merge only their typed contracts before Phase 1.

### Step 0.1: Create typed scenario configuration

Create immutable scenario and experiment definitions for business objectives, horizons, prompts, constraints, expected outcomes, disruption references, thresholds, seeds, suite partitions, task-family clusters, and version identifiers. Parse the current singular `experiment:` YAML shape, validate ranges and references, and let environment variables override supported runtime settings at load time rather than class-definition time. Add a separate evaluation-suite manifest whose held-out entries expose identifiers and protected payload locators rather than tuning-visible task content.

Files:

* pyproject.toml - Add `PyYAML` through `uv add` and development-only `httpx` through `uv add --dev httpx`; retain Python 3.11 compatibility.
* configs/experiment.yaml - Convert the current illustrative mapping into a versioned procurement scenario with deterministic seed and explicit objective, constraints, expected outcome, fault references, and policy references.
* configs/evaluation-suite.yaml - Define suite version, development/held-out partitions, task/family/cluster identifiers, owner, protected payload locator, access policy, and rotation deadline.
* src/arise_x/scenarios/__init__.py - Export scenario contracts.
* src/arise_x/scenarios/models.py - Own frozen scenario, horizon, threshold, disruption-reference, suite-partition, task-cluster, and experiment definitions.
* src/arise_x/config.py - Load YAML manifests, apply environment overrides, validate scenario/suite compatibility and held-out metadata, and create output directories without embedding domain behavior.
* tests/test_config.py - Cover valid loading, environment precedence, malformed YAML, invalid ranges, unknown scenario, deterministic seed behavior, suite partitioning, protected held-out references, and expired rotation metadata.

Discrepancy references:

* DD-02 selects PyYAML rather than leaving parser choice unresolved.
* DD-03 selects the procurement scenario as the representative workflow.

Success criteria:

* A typed experiment can be loaded from configs/experiment.yaml without hardcoded disruption or threshold duplication in the runner.
* Settings read environment overrides when `load_settings()` is called, including changes made after module import.
* Invalid scenario, horizon, threshold, and disruption references fail with actionable configuration errors.
* Development and held-out tasks are versioned separately; held-out task payloads are resolved only through an injected protected resolver and are not persisted in run evidence.
* Every task has a task-family/cluster identifier and suite partition for paired and cluster-aware analysis.
* Existing environment-only startup remains supported through documented defaults.

Context references:

* configs/experiment.yaml (Lines 1-12) - Current singular experiment mapping.
* src/arise_x/config.py (Lines 10-26) - Current settings and load factory.
* pyproject.toml (Lines 1-33) - Dependencies, entry point, build, and pytest configuration.
* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Scenario 7, Phase 0 recommendation.

Dependencies:

* Python 3.11+
* uv dependency management
* PyYAML and development-only httpx

### Step 0.2: Add versioned run persistence

Extend the repository from a single write-only JSON dump to a versioned, schema-tagged run store. Define typed read, write, list, and lookup operations. Persist stable run identity and metadata required by later baseline/candidate comparisons while retaining `write_results` as a compatibility entry point.

Files:

* src/arise_x/storage/repository.py - Add versioned envelopes, typed reads, listing, lookup by run ID, and corruption/schema error handling.
* tests/test_repository.py - Cover round-trip behavior, version metadata, missing run, malformed payload, deterministic ordering, and legacy `write_results` compatibility.

Discrepancy references:

* DD-04 selects explicit run ID plus fingerprint metadata as baseline identity.

Success criteria:

* A completed run can be retrieved by immutable run ID and listed without overwriting prior runs.
* Persisted metadata contains scenario version, agent version, configuration fingerprint, seed, source revision when provided, and schema version.
* Unsupported or corrupt persisted schemas fail explicitly rather than returning partial evidence.
* Existing callers of `write_results(path, results)` continue to work.

Context references:

* src/arise_x/storage/repository.py (Lines 1-17) - Current write-only persistence.
* .copilot-tracking/research/subagents/2026-08-25/planning-anchor-verification.md - Baseline identity and compatibility recommendations.

Dependencies:

* No dependency on Step 0.1; may execute in parallel.
* Frozen dataclass conventions already used by the repository.

### Step 0.3: Validate Phase 0 contracts

Run focused checks independently for each parallel track before merging their contracts.

Validation commands:

* `uv sync` - Resolve the YAML dependency and project environment.
* `uv run pytest tests/test_config.py tests/test_repository.py` - Validate scenario and persistence contracts.
* `uv run ruff check src/arise_x/config.py src/arise_x/scenarios src/arise_x/storage tests/test_config.py tests/test_repository.py` - Validate touched Python slices.

## Implementation Phase 1: Deterministic Single-Agent Execution

<!-- parallelizable: false -->

### Step 1.1: Replace synthetic orchestration with an injected agent

Keep `AgentUnderTest.run_task(task_id, prompt)` as the minimum framework-neutral adapter. Add only defaulted response metadata needed for later telemetry. Introduce a deterministic scripted adapter for the procurement example, inject an agent and random source into the runner through keyword-only parameters, and remove the private random `_simulate_event` path after equivalent compatibility behavior exists.

Files:

* src/arise_x/agents/base.py - Preserve the protocol and append optional/defaulted response metadata.
* src/arise_x/evaluation/runner.py - Accept agent, scenario, and seeded random source; execute the scenario through the protocol; preserve positional `iterations, settings` behavior.
* src/arise_x/chaos/injector.py - Accept an injected random source rather than using module-global unseeded randomness.
* src/arise_x/main.py - Add scenario and seed options after service behavior is complete.
* src/arise_x/api/app.py - Accept optional scenario and seed fields while preserving current request defaults and response keys.
* tests/test_agent_execution.py - Prove the protocol is invoked with expected task IDs and prompts and errors are surfaced consistently.
* tests/test_api.py - Use FastAPI `TestClient` to preserve `GET /health` and existing `POST /run` request/response behavior while validating additive scenario, seed, and run metadata.
* tests/test_runner.py - Replace label-only coverage with deterministic output, agent-call, count, and seed-replay assertions while retaining existing behavioral expectations.

Discrepancy references:

* DD-03 selects a provider-neutral scripted adapter instead of an external LLM SDK.
* DD-06 preserves current public entry points during the migration.

Success criteria:

* `run_reliability_loop(iterations, settings)` still works for existing callers and uses a deterministic default adapter rather than a random outcome simulator.
* Supplying the same scenario and seed yields repeatable run evidence.
* The runner calls the provided `AgentUnderTest` for every task and does not silently substitute synthetic outcomes.
* Current CLI command and `POST /run` keys remain available with additive fields only.
* OpenAPI generation succeeds and the existing health/run endpoints retain compatible status codes and required response keys.

Context references:

* src/arise_x/agents/base.py (Lines 9-23) - Existing response and protocol.
* src/arise_x/evaluation/runner.py (Lines 15-67) - Existing result, synthetic event, and orchestration path.
* src/arise_x/chaos/injector.py (Lines 9-27) - Existing profiles and unseeded sampling.
* src/arise_x/main.py (Lines 17-48) - Current Typer command and exit behavior.
* src/arise_x/api/app.py (Lines 11-31) - Current request and endpoints.
* tests/test_runner.py (Lines 1-32) - Existing orchestration coverage.

Dependencies:

* Phase 0 scenario and persistence contracts.
* No external provider SDK; adapter remains framework-neutral.

### Step 1.2: Persist and expose deterministic run metadata

Connect runner output to the versioned repository. Ensure CLI and API paths emit or return run ID, scenario version, agent version, seed, and configuration fingerprint without moving evaluation logic into transport modules.

Files:

* src/arise_x/evaluation/runner.py - Produce run metadata from execution inputs.
* src/arise_x/storage/repository.py - Persist the execution envelope.
* src/arise_x/main.py - Write the versioned run and display its identifier.
* src/arise_x/api/app.py - Return additive metadata fields and persist API-triggered runs.
* tests/test_runner.py - Cover metadata propagation.
* tests/test_repository.py - Cover deterministic metadata round-trip.

Success criteria:

* CLI and API runs are persisted consistently and can be resolved by their returned run ID.
* Transports delegate to the runner/repository and contain no scoring or chaos policy.
* Legacy response keys (`iterations`, `trustworthy_count`, `results`) remain present.

Context references:

* src/arise_x/main.py (Lines 20-31) - Current CLI execution and persistence.
* src/arise_x/api/app.py (Lines 23-31) - Current API execution without persistence.

Dependencies:

* Step 1.1 completion.
* Phase 0 versioned repository.

### Step 1.3: Validate deterministic execution

Validation commands:

* `uv run pytest tests/test_config.py tests/test_repository.py tests/test_agent_execution.py tests/test_runner.py tests/test_api.py` - Validate the real agent path, metadata, and HTTP compatibility.
* `uv run ruff check src/arise_x/agents src/arise_x/evaluation src/arise_x/chaos src/arise_x/main.py src/arise_x/api tests/test_agent_execution.py tests/test_runner.py tests/test_api.py` - Validate the touched execution slice.
* `uv run arise-x run-loop --iterations 3` - Smoke-test the backwards-compatible CLI path.

## Implementation Phase 2: Trajectory And Reliability Contracts

<!-- parallelizable: true -->

Trajectory contracts and reliability-vector contracts can be created and tested in parallel. Keep calculation from live runner evidence for Phase 3 so neither track depends on unfinished integration from the other.

### Step 2.1: Define immutable trajectory evidence

Model a trajectory as ordered, correlated evidence rather than a flat success event. Include run, task, task-family/cluster, suite version/partition, repeat/seed, scenario, agent, step, action, tool call/response, state transition, fault trigger, recovery, timing, token/cost, human-intervention, policy, and final-outcome fields. Preserve `RunEvent` as a summary projection for compatibility.

Files:

* src/arise_x/telemetry/trajectory.py - Own trajectory, step, tool, state, recovery, and outcome records.
* src/arise_x/telemetry/events.py - Retain `RunEvent` and add conversion from a trajectory summary.
* tests/test_trajectory.py - Cover ordering, correlation identifiers, invariants, summary projection, and immutable evidence.

Discrepancy references:

* DD-01 separates contracts from integration to enable parallel implementation.
* DD-06 preserves `RunEvent` as a temporary compatibility projection.

Success criteria:

* A trajectory represents the State -> Action -> Tool -> Response -> Recovery -> Final State sequence from the requirement.
* Step ordering and identifiers are validated; invalid or incomplete terminal evidence fails explicitly.
* Existing code can still consume a derived `RunEvent` during migration.
* Raw prompts, tool payloads, and outputs support redaction markers so persistence does not require storing sensitive content by default.

Context references:

* src/arise_x/telemetry/events.py (Lines 1-17) - Current flat event.
* intial analysis and requirement.md - Long-Horizon Engine trajectory requirements.
* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Project structure gap and Scenario 7, Phase 1.

Dependencies:

* Phase 1 run, task, scenario, and agent identity contracts.
* May execute in parallel with Step 2.2.

### Step 2.2: Define the Agent Reliability Vector

Create normalized, individually auditable dimensions for goal success, resilience, behavioral stability, recovery, safety, efficiency, cost, and autonomy. Define dimension evidence, confidence/coverage metadata, and missing-data handling. Do not make the multiplicative ARI the primary artifact and do not replace the existing additive trust function in place.

Files:

* src/arise_x/trust/vector.py - Own vector dimensions, normalization policy contracts, evidence references, and vector result.
* src/arise_x/trust/scorer.py - Keep `score_trust` as an explicitly diagnostic compatibility projection.
* tests/test_vector.py - Cover normalization bounds, missing evidence, dimension independence, and critical-dimension metadata.
* tests/test_trust.py - Retain current healthy/failed compatibility expectations.

Discrepancy references:

* DD-05 reserves the ARI for Phase 5 release gating instead of making it the primary metric.
* DD-06 preserves the additive trust scorer as a temporary diagnostic.

Success criteria:

* Every vector dimension is reported separately with its evidence coverage and normalization version.
* Missing dimensions cannot silently receive a perfect score.
* The vector contains no hidden weighted aggregate.
* Existing trust tests continue to pass and no compatibility score is labeled ARI.

Context references:

* src/arise_x/trust/scorer.py (Lines 11-26) - Existing additive three-factor decision.
* tests/test_trust.py (Lines 1-45) - Existing compatibility coverage.
* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Scenario 4 metric analysis and preferred vector-first approach.

Dependencies:

* Phase 1 execution identities.
* May execute in parallel with Step 2.1.

### Step 2.3: Validate Phase 2 contracts

Validation commands:

* `uv run pytest tests/test_trajectory.py tests/test_vector.py tests/test_trust.py` - Validate both independent contracts and compatibility.
* `uv run ruff check src/arise_x/telemetry src/arise_x/trust tests/test_trajectory.py tests/test_vector.py tests/test_trust.py` - Validate touched Python slices.

## Implementation Phase 3: Trajectory And Vector Integration

<!-- parallelizable: false -->

### Step 3.1: Produce trajectories from real agent execution

Instrument the deterministic execution path so each scenario run produces ordered trajectory evidence and a derived `RunEvent`. Aggregate trajectory evidence into the reliability vector without letting transports or storage calculate scores.

Files:

* src/arise_x/agents/base.py - Expose optional structured execution evidence without breaking the minimum protocol.
* src/arise_x/evaluation/runner.py - Orchestrate trajectory creation, summary projection, and vector calculation.
* src/arise_x/telemetry/trajectory.py - Apply finalized lifecycle invariants.
* src/arise_x/telemetry/events.py - Derive compatibility summaries.
* src/arise_x/trust/vector.py - Calculate dimensions from trajectory evidence.
* tests/test_agent_execution.py - Cover structured and minimum-capability agents.
* tests/test_runner.py - Cover trajectory/vector production per task.

Discrepancy references:

* DD-01 serializes integration after parallel contract work.

Success criteria:

* Every completed task produces one correlated trajectory, one summary event, and one vector result.
* Goal, recovery, safety, efficiency, cost, and autonomy dimensions trace to specific trajectory evidence.
* Behavioral stability is marked unavailable until a baseline comparison exists; it is not fabricated from one event.
* Minimum-capability agents remain usable through an adapter-generated trajectory.

Context references:

* src/arise_x/evaluation/runner.py (Lines 45-67) - Current orchestration owner.
* src/arise_x/agents/base.py (Lines 19-23) - Framework-neutral minimum protocol.

Dependencies:

* Implementation Phase 2 completion.

### Step 3.2: Persist and expose trajectory/vector evidence

Version the persistence schema for trajectory and vector evidence. Expose stable identifiers and separate summary vs. detailed evidence in API responses. Avoid returning unbounded raw trajectories by default.

Files:

* src/arise_x/storage/repository.py - Persist and retrieve trajectories and vectors under the run envelope.
* src/arise_x/api/app.py - Add summary identifiers and optional detailed retrieval contract.
* src/arise_x/main.py - Report vector summary and artifact/run identifiers.
* tests/test_repository.py - Cover the new schema and old-schema rejection/migration policy.
* tests/test_runner.py - Cover persistence integration.
* tests/test_api.py - Validate bounded HTTP summaries, explicit detailed retrieval, OpenAPI schema, and legacy `POST /run` keys.

Success criteria:

* Stored evidence is schema-versioned and round-trips without loss of identifiers or metric coverage.
* API defaults remain bounded and compatibility keys remain present.
* Detailed trajectory access is explicit and honors redaction markers.

Context references:

* src/arise_x/storage/repository.py (Lines 12-17) - Existing serialization owner.
* src/arise_x/api/app.py (Lines 23-31) - Existing unbounded result response.

Dependencies:

* Step 3.1 completion.
* Phase 0 versioned persistence.

### Step 3.3: Align working documentation with the seven planes

Update documentation only after the integrated behavior passes focused tests. Explain the seven-plane target, distinguish implemented planes from roadmap planes, describe the trajectory/vector evidence flow, and retain the experiment-first scope statement.

Files:

* docs/architecture.md - Replace the five-layer view with the seven-plane target and mark implementation status.
* README.md - Document scenario execution, deterministic replay, run IDs, trajectory/vector summaries, and actual validation commands that have passed.

Success criteria:

* Documentation does not claim chaos levels, statistical drift, release gating, or multi-agent support before those phases land.
* Every documented command is executable in the repository.
* The seven-plane architecture clearly separates execution, telemetry, intelligence, reliability, and release policy responsibilities.

Context references:

* docs/architecture.md (Lines 14-30) - Current five-layer system and flow.
* README.md (Lines 19-49) - Current layout, quick start, and scope note.

Dependencies:

* Steps 3.1-3.2 focused validation success.

### Step 3.4: Validate trajectory/vector integration

Validation commands:

* `uv run pytest tests/test_agent_execution.py tests/test_runner.py tests/test_repository.py tests/test_trajectory.py tests/test_vector.py tests/test_trust.py tests/test_api.py` - Validate integrated evidence, HTTP behavior, and compatibility.
* `uv run ruff check src tests` - Validate the integrated Python surface before chaos work.
* `uv run arise-x run-loop --iterations 3` - Verify the CLI reports deterministic run and vector evidence.

## Implementation Phase 4: Verified Chaos Catalog

<!-- parallelizable: false -->

Fault-family definitions can be authored concurrently inside this phase, but configuration, injection, telemetry, runner, and tests share integration points. Treat the phase as sequential at merge and validation time.

### Step 4.1: Create the typed fault catalog and trigger receipts

Define fault level, family, injection point, strategy, intensity, duration, abort condition, expected trigger, and receipt. Cover Infrastructure, Tool, Data, and Agent levels for the MVP. Add resource/time faults to Infrastructure and verification failure to Agent. Define cost, security/adversarial, and human-in-the-loop as cross-cutting families so they can apply to multiple levels without distorting the six-level conceptual entry point.

Files:

* src/arise_x/chaos/catalog.py - Own fault taxonomy, strategy, policy, abort condition, and trigger receipt contracts.
* configs/experiment.yaml - Reference typed faults, trigger expectations, abort conditions, and blast-radius policy.
* tests/test_chaos.py - Cover catalog validation, unsupported combinations, abort conditions, and receipts.

Discrepancy references:

* DD-07 keeps six primary levels while modeling cost, security, and human faults as cross-cutting families.
* DR-03 leaves a broader red-team vendor comparison outside the MVP.

Success criteria:

* The catalog represents the research-backed gaps without introducing separate scoring subsystems.
* Every configured fault declares how activation is verified.
* Abort conditions and blast radius are required for faults with external side effects.
* Data and Agent faults are distinguishable from Infrastructure and Tool transport failures.

Context references:

* src/arise_x/chaos/injector.py (Lines 9-27) - Existing profile and sampling model.
* configs/experiment.yaml (Lines 6-12) - Existing disruption names and thresholds.
* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Scenario 3 taxonomy assessment.
* .copilot-tracking/research/subagents/2026-08-25/chaos-engineering-precedent.md - AgentChaos trigger verification and taxonomy gaps.

Dependencies:

* Phase 0 scenario injection references.
* Phase 3 trajectory evidence.

### Step 4.2: Dispatch faults and verify activation

Replace failure-probability boosting with typed dispatch against explicit injection points. Record attempted, triggered, observed, recovered, and aborted states. Score resilience/recovery only for verified triggers and preserve baseline execution as a no-fault control.

Files:

* src/arise_x/chaos/injector.py - Dispatch typed faults using the injected random source and return trigger receipts.
* src/arise_x/evaluation/runner.py - Run control/experiment pairs and correlate receipts with trajectories.
* src/arise_x/telemetry/trajectory.py - Record trigger and recovery evidence.
* src/arise_x/trust/vector.py - Compute resilience/recovery only from verified experiments.
* tests/test_chaos.py - Cover injected-but-not-triggered, triggered-and-recovered, triggered-and-failed, abort, and replay cases.
* tests/test_runner.py - Cover control/experiment pairing and evidence propagation.

Success criteria:

* An untriggered fault is excluded from resilience impact rather than counted as a successful recovery.
* A triggered fault can be traced to its injection point, affected steps, recovery behavior, and final outcome.
* Replaying the same scenario, seed, and fault policy yields equivalent trigger decisions.
* Baseline runs remain available as explicit controls.

Context references:

* src/arise_x/evaluation/runner.py (Lines 26-67) - Existing synthetic disruption selection and execution.
* .copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md - AgentChaos and ReliabilityBench methodology.

Dependencies:

* Step 4.1 completion.

### Step 4.3: Document only implemented chaos behavior

Files:

* docs/architecture.md - Add verified chaos flow and catalog ownership to the Chaos Plane.
* README.md - Document supported MVP levels/families and how receipts affect resilience scoring.

Success criteria:

* Documentation clearly distinguishes implemented Levels 1-4 from deferred Level 5 multi-agent and Level 6 model migration/behavior experiments.
* Cross-cutting cost, adversarial, and human fault families are described without claiming exhaustive security testing.

Dependencies:

* Steps 4.1-4.2 validation success.

### Step 4.4: Validate verified chaos

Validation commands:

* `uv run pytest tests/test_chaos.py tests/test_runner.py tests/test_trajectory.py tests/test_vector.py` - Validate fault dispatch, receipts, recovery, and metrics.
* `uv run ruff check src/arise_x/chaos src/arise_x/evaluation src/arise_x/telemetry src/arise_x/trust tests/test_chaos.py tests/test_runner.py` - Validate the touched chaos slice.

## Implementation Phase 5: Statistical Drift And Release Gate

<!-- parallelizable: false -->

Statistics and gate-policy types can begin independently against frozen vector contracts, but final gate integration depends on verified chaos receipts, persisted windows, CLI/API surfaces, and shared acceptance tests. Treat the completed phase as sequential.

### Step 5.1: Implement per-dimension statistical comparison

Compare an explicit golden baseline run/window with a candidate run/window on the same held-out task IDs and seeds. Make the task the analysis unit: average repeated continuous values and binary outcomes into paired task-level values/rates before comparison. Use Wilcoxon signed-rank or paired permutation tests for continuous values and aggregated binary rates, and paired permutation/bootstrap tests for categorical distribution distances. Permit exact McNemar only when there is exactly one independent binary baseline/candidate pair per task and no repeated observations; permit Mann-Whitney U or chi-square only when an explicitly independent sampling design is recorded. Apply Holm-Bonferroni multiple-test correction.

Calculate required observations per dimension from configured minimum detectable effect, 0.02 alpha (98% confidence), target power of at least 0.80, and baseline variance/rate or pilot estimates. Gate only after every required dimension satisfies its power-derived minimum; retain 30 pairs solely as a deterministic fixture floor. Carry task-family cluster IDs through evidence, test independence assumptions, and use paired cluster bootstrap confidence intervals/resampling when episodes within a family are correlated. Record effective task and cluster counts.

Estimate downstream-impact priority separately from drift classification using held-out historical association with goal failure, safety violation, unrecovered fault, or escalation. Preserve confidence and coverage for that association; mark impact unavailable when evidence is insufficient and never let impact weighting erase a statistically/practically material critical-metric regression.

Files:

* pyproject.toml - Add `scipy` through uv.
* src/arise_x/drift/statistics.py - Own sampling-design validation, paired/independent test selection, power calculation, paired cluster bootstrap, confidence intervals, effect sizes, tolerances, coverage, multiple-test adjustment, and downstream-impact evidence.
* src/arise_x/drift/detector.py - Expose baseline-versus-candidate drift results and retain `detect_drift(event, threshold)` only as a legacy severity facade.
* tests/test_drift.py - Cover no drift, statistical/practical insignificance, material drift, task-level binary-rate aggregation, Wilcoxon/permutation selection, McNemar only for one-pair-per-task evidence, rejected sampling mismatch, cluster correlation, power-derived insufficiency, multiple-test correction, impact priority, missing data, and deterministic fixtures.

Discrepancy references:

* DD-02 selects SciPy for the statistical MVP.
* DR-04 defers PSI threshold research because the MVP uses typed per-dimension tests rather than one raw fingerprint-distance threshold.
* DD-08 reserves 30 pairs for fixture coverage and requires a power-derived minimum for any deployment-blocking verdict.
* DD-10 resolves the paired-design conflict with matched tests and restricts independent-sample tests to explicitly independent evidence.
* DR-06 is addressed through task-family clusters and paired cluster bootstrap uncertainty.
* DR-10 is addressed as a separate, evidence-backed impact-priority signal rather than an opaque change to statistical classification.

Success criteria:

* Drift cannot be declared from one event or a raw percentage delta.
* Every drift verdict records sampling design, test, paired task count, cluster count, achieved/target power, confidence, corrected significance, effect estimate, tolerance, coverage, and impact-priority evidence.
* Both statistical significance and practical effect tolerance must fail before a dimension is classified as degraded.
* A deployment-blocking verdict is unavailable until all required dimensions meet power-derived sample and cluster coverage; insufficient or non-comparable data never passes.
* Baseline and candidate task IDs, seeds, suite version, and held-out partition must match; the recorded observation unit and power calculation must match the selected test, and independent tests cannot be selected for paired evidence.

Context references:

* src/arise_x/drift/detector.py (Lines 10-34) - Existing event severity facade.
* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Scenario 5 preferred statistical approach.
* .copilot-tracking/research/subagents/2026-08-25/drift-and-sre-precedent.md - Evidently, NannyML, Anthropic, and Kayenta methodology.

Dependencies:

* Phase 0 versioned baseline lookup.
* Phase 3 vector/fingerprint evidence.
* Phase 4 verified trigger evidence for resilience comparisons.
* SciPy.

### Step 5.2: Define ARI policy and release verdict

Keep the full vector and per-dimension comparisons primary. Define ARI as a versioned, optional gating convenience over eligible normalized dimensions. Use a geometric mean rather than an unadjusted product so dimension count does not mechanically collapse the scale. Add critical goal-success and safety overrides, power/cluster coverage, no-data fail-safe behavior, and regression tolerance.

Define the SLI at episode level: an eligible episode is good only when it achieves the objective, has no critical safety violation, and recovers when a configured fault is verified as triggered. Over policy window `W`, let `eligible` be the eligible-episode count, `bad = eligible - good`, `allowed_bad = (1 - slo_target) * eligible`, and `remaining_budget = max(0, allowed_bad - bad) / allowed_bad` (with an explicit no-data state when `allowed_bad` is zero). The example policy uses a trailing 28-day window with a configurable bounded-episode fallback and requires a minimum eligible count. Candidate held-out results are evaluated for regression but do not consume production budget before deployment. The release blocks when any critical regression occurs, required evidence/power/held-out policy fails, or the trailing production budget is exhausted; otherwise ARI and non-critical regressions inform pass/warn policy.

Files:

* src/arise_x/trust/gate.py - Own gate policy, geometric ARI, critical overrides, power/cluster/held-out requirements, episode SLI classification, error-budget window/calculation, no-data rules, per-metric rationale, and release verdict.
* src/arise_x/trust/vector.py - Expose eligible dimensions and normalization versions without embedding release policy.
* tests/test_gate.py - Cover pass, warning, block, critical override, no-data, insufficient power/clusters, development-suite rejection, dimension-count stability, SLI episode classification, error-budget calculation/window/exhaustion, and candidate-vs-production-budget interaction.

Discrepancy references:

* DD-05 uses a normalized geometric mean and critical overrides rather than the raw multiplicative product proposed in the vision.
* DD-08 applies configurable power, statistical, and effect-size policy to the gate.
* DR-07 is addressed by requiring a versioned, protected, unexpired held-out suite for deployment decisions.
* DR-08 is addressed by defining the SLI event, window, error-budget formula, and combination with baseline/candidate regression.

Success criteria:

* The gate returns per-dimension classifications and reasons before any scalar summary.
* A critical goal-success or safety regression blocks release regardless of ARI.
* Missing required evidence, inadequate power/cluster coverage, a development or expired suite, and exhausted production error budget fail safely.
* Adding a neutral dimension does not mechanically reduce ARI solely because the vector became longer.
* The additive `score_trust` result is never consumed as ARI.
* The decision records independent reasons for held-out regression and trailing production-budget status; candidate evaluation does not mutate production budget.

Context references:

* src/arise_x/trust/scorer.py (Lines 19-26) - Existing additive diagnostic.
* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Scenarios 4 and 6.
* .copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md - HELM and composite-score risks.

Dependencies:

* Step 5.1 drift result contract.
* Phase 3 reliability vector.

### Step 5.3: Add baseline/candidate gate interfaces

Add a separate CLI gate command and an API gate contract that resolve immutable run IDs, load comparable evidence, execute statistics and policy, persist the decision, and return non-zero/blocking status for CI. Keep execution and gate evaluation separate.

Files:

* src/arise_x/main.py - Add `gate --baseline-run-id ... --candidate-run-id ...` and stable exit behavior for pass/block/configuration error.
* src/arise_x/api/app.py - Add a bounded gate request/response contract or endpoint without changing `POST /run` semantics.
* src/arise_x/storage/repository.py - Resolve comparison windows and persist gate decisions.
* configs/experiment.yaml - Add versioned gate policy, required/critical metrics, alpha, target power, minimum detectable effects, cluster policy, tolerances, SLI definition, SLO target, and error-budget window.
* configs/evaluation-suite.yaml - Require held-out partition, owner, rotation status, task/seed pairing, cluster IDs, and protected payload fingerprints for deployment gates.
* tests/test_gate.py - Cover service behavior and persisted rationale.
* tests/test_runner.py - Cover baseline/candidate evidence compatibility.
* tests/test_api.py - Use FastAPI `TestClient` to cover the gate endpoint, pass/block/error statuses, bounded rationale, OpenAPI schema, and continued `POST /run` compatibility.

Success criteria:

* CI can distinguish pass, blocked regression, and invalid/incomplete evidence by stable exit codes.
* Gate decisions are reproducible from immutable run IDs and policy version.
* Baseline and candidate incompatibility (scenario, schema, normalization, held-out suite, task/seed pairs, cluster metadata, or rotation status) blocks comparison with an actionable reason.
* API and CLI use the same gate service and emit auditable per-metric rationale.
* HTTP tests prove existing run behavior and new gate behavior at the transport boundary.

Context references:

* src/arise_x/main.py (Lines 17-48) - Existing CLI group and exit handling.
* src/arise_x/api/app.py (Lines 11-31) - Existing API surface.
* src/arise_x/storage/repository.py (Lines 12-17) - Existing serialization entry point.

Dependencies:

* Steps 5.1-5.2 completion.
* Versioned persistence from Phase 0.

### Step 5.4: Document drift and gate semantics

Files:

* docs/architecture.md - Add baseline/candidate windowing, Intelligence Plane statistics, Reliability Plane vector, and CI/CD Plane policy boundaries.
* README.md - Document the gate command, evidence requirements, exit semantics, compatibility facade, and limitations of the bundled thresholds.

Success criteria:

* Documentation states that the vector and per-metric evidence are primary; ARI is a gate convenience.
* The example policy is clearly labeled as an example requiring domain calibration, held-out-suite ownership, and power analysis.
* Documentation distinguishes development fixtures, powered held-out deployment evidence, and trailing production error-budget evidence.

Dependencies:

* Steps 5.1-5.3 validation success.

### Step 5.5: Validate statistical drift and release gating

Validation commands:

* `uv sync` - Resolve the statistical dependency.
* `uv run pytest tests/test_drift.py tests/test_gate.py tests/test_repository.py tests/test_runner.py tests/test_vector.py tests/test_api.py` - Validate statistics, policy, storage, HTTP contracts, and integration.
* `uv run ruff check src/arise_x/drift src/arise_x/trust src/arise_x/main.py src/arise_x/api src/arise_x/storage tests/test_drift.py tests/test_gate.py tests/test_api.py` - Validate the touched gate slice.
* `uv run arise-x gate --baseline-run-id <baseline> --candidate-run-id <candidate>` - Verify stable CI-facing behavior using test-created run IDs.

## Implementation Phase 6: Multi-Agent Execution And MACS

<!-- parallelizable: false -->

Coordinator contracts, Level 5 fault fixtures, and milestone definitions can be developed concurrently, but they converge on shared agent, runner, vector, configuration, CLI, and API modules. Treat integration and completion as sequential.

### Step 6.1: Add a minimal star-topology coordinator

Compose existing single-agent adapters under a coordinator while preserving the single-agent protocol. Correlate messages, assignments, acknowledgments, handoffs, verification, and final outcome. Do not introduce a framework-specific agent SDK.

Files:

* src/arise_x/agents/multi_agent.py - Own coordinator, worker registration, message/handoff evidence, and milestone observations.
* src/arise_x/agents/base.py - Add optional capabilities without changing `run_task`.
* src/arise_x/evaluation/runner.py - Select single-agent or star-topology execution from the scenario.
* configs/experiment.yaml - Add optional topology and role configuration.
* tests/test_multi_agent.py - Cover assignment, handoff, verification, failure propagation, and correlation.

Discrepancy references:

* DD-09 selects star topology as the lowest-complexity first coordination model.

Success criteria:

* Single-agent scenarios run unchanged.
* Multi-agent trajectories preserve agent IDs and causal message/handoff correlation.
* The coordinator is framework-neutral and does not become a second scoring engine.

Context references:

* src/arise_x/agents/base.py (Lines 9-23) - Current single-agent contract.
* .copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md - MultiAgentBench and MAST precedent.

Dependencies:

* Phases 0-5 stable execution and evidence contracts.

### Step 6.2: Add Level 5 faults and MACS milestones

Extend the catalog with disagreement, message loss, conflicting objectives, cascading failure, and MAST-grounded soft failures such as ignored input, information withholding, missing clarification, and reasoning-action mismatch. Calculate MACS from explicit milestone evidence for assignment, information exchange, handoff, verification, and objective completion. Report components separately before the MACS summary.

Files:

* src/arise_x/chaos/catalog.py - Add Level 5 fault definitions and supported trigger points.
* src/arise_x/chaos/injector.py - Apply message/coordination faults and emit receipts.
* src/arise_x/telemetry/trajectory.py - Record multi-agent message, handoff, and verification evidence.
* src/arise_x/trust/vector.py - Add optional MACS diagnostic/component without changing the core eight-vector schema until calibration supports promotion.
* tests/test_multi_agent.py - Cover milestone components, fault trigger verification, recovery, and no-data behavior.
* tests/test_chaos.py - Cover Level 5 dispatch and receipts.

Discrepancy references:

* DR-01 records that exact MACS weighting remains unvalidated against MultiAgentBench code.
* DD-09 uses equal component reporting for the first star-topology experiment and keeps MACS out of critical gating until calibrated.

Success criteria:

* MACS components are individually auditable and trace to trajectory milestones.
* Missing milestones cannot silently become successes.
* Level 5 resilience uses verified receipts and distinguishes transport message loss from soft coordination failure.
* MACS remains diagnostic and non-critical until empirical calibration demonstrates gate validity.

Context references:

* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md - Scenario 3 Level 5 gaps and Scenario 4 MACS precedent.
* .copilot-tracking/research/subagents/2026-08-25/academic-benchmarks.md - MultiAgentBench milestone KPIs and MAST failure taxonomy.

Dependencies:

* Step 6.1 completion.
* Phase 4 verified fault model.

### Step 6.3: Expose and document multi-agent evidence

Files:

* src/arise_x/main.py - Add topology selection only if not fully scenario-driven; preserve existing command defaults.
* src/arise_x/api/app.py - Accept optional topology identifier and return bounded coordination summaries.
* src/arise_x/storage/repository.py - Persist multi-agent correlation and milestone evidence.
* docs/architecture.md - Complete Agent Execution and Chaos Plane descriptions for the implemented star topology.
* README.md - Document multi-agent scenario invocation, MACS components, and limitations.
* tests/test_api.py - Validate topology request compatibility, bounded coordination summaries, redaction, and OpenAPI schema.

Success criteria:

* API and CLI remain single-agent compatible.
* Detailed message content is redacted or omitted by default while correlation metadata remains usable.
* Documentation does not claim MACS generalizes to chain/tree/graph topologies before comparative validation.

Dependencies:

* Steps 6.1-6.2 validation success.

### Step 6.4: Validate multi-agent execution

Validation commands:

* `uv run pytest tests/test_multi_agent.py tests/test_chaos.py tests/test_runner.py tests/test_trajectory.py tests/test_vector.py tests/test_gate.py tests/test_api.py` - Validate coordination, Level 5 faults, HTTP compatibility, and non-critical gate behavior.
* `uv run ruff check src/arise_x/agents src/arise_x/chaos src/arise_x/evaluation src/arise_x/telemetry src/arise_x/trust tests/test_multi_agent.py tests/test_chaos.py tests/test_api.py` - Validate the touched multi-agent slice.

## Implementation Phase 7: Full Validation And Handoff

<!-- parallelizable: false -->

### Step 7.1: Run the full project validation sequence

Execute all project checks after every implementation phase has merged:

* `uv sync`
* `uv run ruff check .`
* `uv run pytest`
* `uv build`
* `uv run python -c "import arise_x; from arise_x.api.app import app"`
* Run an HTTP smoke through FastAPI `TestClient` for `GET /health`, legacy `POST /run`, and the gate endpoint.
* `uv run arise-x run-loop --iterations 3`
* Run `uv run arise-x gate --baseline-run-id <baseline> --candidate-run-id <candidate>` with deterministic test artifacts for both pass and block outcomes.

Files:

* All modified source, configuration, documentation, and test files.

Success criteria:

* Dependency resolution, lint, full tests, package build, import smoke, CLI execution, and both release-gate outcomes pass.
* Repeating deterministic smoke scenarios produces equivalent evidence and verdicts.
* No generated run, build, cache, or lock artifact is accidentally treated as source unless intentionally tracked.

Dependencies:

* Implementation Phases 0-6 complete.

### Step 7.2: Verify compatibility and evidence integrity

Check that current public surfaces still work, compatibility artifacts are clearly named, and no score is mislabeled.

Verification checks:

* `run_reliability_loop(iterations, settings)` positional call remains valid.
* `AgentUnderTest.run_task(task_id, prompt)` remains valid.
* `RunEvent`, `score_trust`, `write_results`, `run-loop`, and `POST /run` remain available or have an explicitly tested migration path.
* `score_trust` is labeled diagnostic compatibility only; vector dimensions and ARI remain distinct.
* Persisted evidence contains schema, policy, normalization, scenario, agent, seed, baseline/candidate, and source-version identifiers.
* Sensitive prompts, tool payloads, and messages follow redaction policy.

Success criteria:

* Existing tests plus explicit compatibility tests prove additive migration.
* All release decisions can be reconstructed from immutable evidence and versioned policy.

Dependencies:

* Step 7.1 success.

### Step 7.3: Fix minor validation issues

Apply only isolated corrections such as formatting, missing test fixtures, schema-field propagation, or documentation-command mismatches. Rerun the narrow failed check, then rerun the full sequence.

Success criteria:

* Minor corrections do not expand architecture or introduce new dependencies.
* Every correction has focused regression coverage where behavior changed.

Dependencies:

* A minor failure from Steps 7.1-7.2.

### Step 7.4: Report blocking issues and create follow-on plans

When validation exposes issues requiring new architecture, unplanned provider integration, statistical calibration, security modeling, or data migration, stop implementation expansion and document a separate research/planning task.

Success criteria:

* Blocking issues identify affected evidence, scope, risk, and recommended next planning action.
* Large refactors are not hidden inside final validation.

Dependencies:

* A non-minor failure from Steps 7.1-7.2.

## Dependencies

* Python 3.11+
* uv
* PyYAML and development-only httpx (planned Phase 0 additions)
* SciPy (planned Phase 5 addition)
* pytest and pytest-cov
* Ruff
* FastAPI, Pydantic, Typer, Uvicorn
* A writable artifacts directory for local evidence
* Deterministic procurement scenario fixtures

## Revalidation checkpoints 2026-09-09

The resumed implementation completed bounded R0, R5 and R7 checkpoints without expanding architecture. R0 repairs immutable writes, read-path confinement, legacy-listing compatibility and existing-schema alignment. R5 repairs required-evidence, comparability and independent-budget fail-closed boundaries without claiming calibrated power or introducing a production input backend. R7 validates the repaired slice through full tests/lint, staged sync/build and installed-wheel transport smoke.

Full original acceptance remains partial. The [audit](../../research/subagents/2026-09-09/phase-completion-audit.md) and [planning log](../../plans/logs/2026-08-25/arise-x-framework-validation-implementation-log.md) identify unresolved execution, redaction, statistics, gate provenance and star-integration contracts. Preserve WI-08's explicit deferral. New cross-cutting contracts require a bounded follow-on plan rather than a Phase 7 minor fix.

## Success Criteria

* The synthetic coin-flip loop is replaced by deterministic execution of a real `AgentUnderTest` contract.
* Scenario, trajectory, fault, vector, drift, gate, and multi-agent evidence are typed, versioned, and traceable.
* The Agent Reliability Vector remains the primary analytic artifact; ARI is a versioned geometric gate convenience with critical overrides.
* Drift requires baseline/candidate samples, statistical significance, practical effect, and adequate coverage.
* Chaos scoring uses verified trigger receipts and includes the research-identified taxonomy gaps.
* CI receives stable, auditable pass/block/error outcomes from immutable run IDs.
* Single-agent public surfaces remain compatible through the staged migration.
* Full lint, tests, package build, imports, CLI smoke, and release-gate smoke checks pass.
