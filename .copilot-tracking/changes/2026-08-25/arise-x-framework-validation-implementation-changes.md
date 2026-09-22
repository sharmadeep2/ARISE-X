<!-- markdownlint-disable-file -->
# Release Changes: ARISE-X Framework Validation Roadmap

**Related Plan**: arise-x-framework-validation-implementation-plan.instructions.md
**Implementation Date**: 2026-08-25

## Summary

Tracks phase-by-phase implementation of the ARISE-X evidence-first reliability framework: deterministic execution, trajectories, reliability vector, verified chaos, statistical drift, release gating, and multi-agent coordination.

## Revalidation 2026-09-09

The user requested phase-wise execution and selected verification of the existing phases with repair of confirmed in-scope gaps. The prior completion summary below is historical, not evidence of current validation. Preserve existing implementation while auditing Phases 0-6 against their success criteria, then repeat Phase 7 validation. Do not start provider integration, production calibration, or other follow-on expansion without a separate plan.

* Phase audit: complete; all eight phases are partial against original acceptance criteria. See the [audit](../../research/subagents/2026-09-09/phase-completion-audit.md).
* Repairs: Phase 0 bounded persistence and Phase 5 fail-closed boundary repairs complete
* Final validation: repaired slice passed lint, tests, staged sync/build, installed-wheel imports and fail-closed CLI/API smoke; full roadmap acceptance remains partial

Baseline revalidation: 205 tests passed; Ruff, imports, OpenAPI and explicit run-loop smoke passed. Negative probes reproduced overwritten run IDs, read-path escape, raw payload persistence, synthetic no-fault failures, and gate acceptance without independent production budget. Historical completion claims below are superseded by this audit. Existing green tests lack these acceptance cases.

### Phase 0 persistence repair

* Modified src/arise_x/storage/repository.py: exclusive-create immutable run writes; ID validation and path confinement on reads/lookup/exists; legacy summary filtering; supported nested schema, run identity and evidence alignment checks. Metadata-only runs and legacy write_results remain compatible.
* Modified tests/test_repository.py: negative acceptance coverage for overwrite races, invalid Windows/path-traversal identifiers, symlink escape, legacy coexistence, corrupt schemas and evidence correlation; corrected the inconsistent historical round-trip fixture.
* Validation: focused repository/runner/API tests 142 passed, 8 skipped; full suite 316 passed, 8 skipped; full Ruff passed; editor diagnostics clear.
* Limitation: eight real-symlink tests require unavailable Windows symlink privileges. Deterministic guard tests passed. Vector correlation remains positional because existing vector contracts contain no task/run identifiers. No schema revision introduced.
* Original Phase 0 remains partial: configuration/governance and protected-resolver requirements are unresolved. This bounded repair does not complete all of Step 0.2's future provenance requirements.

### Phase 5 fail-closed boundary repair

* Modified src/arise_x/trust/gate.py and src/arise_x/drift/statistics.py: block absent/insufficient independent production budgets, empty comparisons, missing critical/required dimensions, incomplete coverage and insufficient power; reject incompatible task/repeat, seed, cluster, suite, scenario, schema, normalization and mixed partition evidence. Binary validation precedes McNemar selection. Matched development diagnostics remain supported.
* Modified src/arise_x/main.py and src/arise_x/api/app.py: invalid inputs receive CLI 2/HTTP 422, missing runs receive HTTP 404, and blocking verdicts receive CLI 1. No current CLI/API gate can pass without the future independent production-input contract.
* Modified tests/test_gate.py, tests/test_drift.py and tests/test_api.py: regression coverage, actual HTTP negative tests and bounded responses. Modified README.md and docs/architecture.md to describe current fail-closed behavior and the working run-loop invocation.
* Validation: focused tests 120 passed; full suite 377 passed, 8 skipped; full Ruff passed; changed-file diagnostics clear; all 13 detected signature callers compatible. CLI execution and missing-run exit smoke passed.
* Limits: the two-task/two-cluster guard prevents degenerate acceptance only; it is not calibrated statistical sufficiency. No statistical power algorithm, integer budget formula, production backend, decision schema or gate bypass was introduced. Full Phase 5 remains partial.

### Phase 7 repair-slice validation

* Original workspace: full Ruff passed; pytest 377 passed, 8 skipped; package/API imports passed. Repeated deterministic CLI/API runs matched results and vectors.
* Temporary staged copy: uv sync and uv build passed using the configured package source after offline cache misses. Full lint/tests passed again. Built wheel and source distribution; installed-wheel imports covered all 27 submodules and matched all 28 source files.
* Original and installed-wheel gate smoke: valid comparison without independent production budget produced CLI 1/HTTP 200 block; invalid comparison CLI 2/HTTP 422; missing IDs CLI 2/HTTP 404; malformed request HTTP 422. Direct unit tests demonstrated PASS only with independent synthetic production-budget evidence.
* Eight Windows real-symlink tests remain skipped; existing Starlette/httpx deprecation warning remains. Editor diagnostics clear. The validation-only phase changed no original workspace files, confirmed by hashes across 149 files.
* Packaging limitation: distributions omit YAML configuration. Installed-wheel execution passed with external configuration present; execution without configuration exits 1. Resolve the distribution/configuration contract separately rather than silently bundling protected or user-specific inputs.

### Revalidation release summary

The resumed task modified 11 product/test/documentation files (2 persistence, 7 gate code/tests, 2 product documents), added one audit report and updated four existing tracking artifacts: 1 added / 15 modified / 0 removed in this session. No dependencies, schemas or deployments changed. Counts describe this session, not Git changes; the repository is unborn and all project content is untracked.

Two bounded repair slices completed. All eight original phases remain partial; acceptance checkboxes were corrected to reflect the audit rather than historical claims. Final validation passes for the repaired slice with the stated skips. Current CLI/API gates intentionally cannot PASS until independent production evidence is supported. Next implementation requires bounded plans for truthful local execution/redaction, production-history and decision provenance, statistical design, and durable star integration.

## Changes

### Added

* configs/evaluation-suite.yaml - Versioned development/held-out suite manifest for the procurement scenario with owner, rotation deadline, access policy, protected payload locator, and task/cluster identifiers.
* src/arise_x/scenarios/__init__.py - Public exports for scenario and evaluation-suite contracts.
* src/arise_x/scenarios/models.py - Frozen `Scenario`, `Horizon`, `Threshold`, `DisruptionReference`, `TaskCluster`, `SuiteReference`, `SuiteTask`, `SuitePartition`, and `EvaluationSuite` dataclasses with validation.
* tests/test_config.py - Covers valid loading, environment precedence, malformed YAML, invalid thresholds, unknown suite reference, deterministic seed, suite partition access, held-out payload non-leakage, and expired rotation deadline.
* tests/test_repository.py - Covers versioned run round-trip, metadata persistence, generated run IDs, deterministic listing, missing-run/corrupt/unsupported-schema errors, and legacy `write_results` compatibility.

### Modified

* pyproject.toml - Added `pyyaml` runtime dependency and `httpx` development-only dependency via `uv add`.
* configs/experiment.yaml - Converted to a versioned procurement scenario with objective, constraints, expected outcome, deterministic seed, and suite/cluster references.
* src/arise_x/config.py - Loads and validates scenario/suite YAML manifests, applies environment overrides at load time, checks scenario/suite compatibility, and enforces held-out rotation deadlines.
* src/arise_x/storage/repository.py - Added `RunRepository` with versioned per-run persistence, typed metadata, read/list/lookup operations, and corruption/schema error handling; `write_results` behavior preserved unchanged.
* src/arise_x/agents/base.py - Added an optional, defaulted `success` field to `AgentResponse`; the `AgentUnderTest.run_task` protocol signature is unchanged.
* src/arise_x/agents/__init__.py - Export `AgentResponse`, `AgentUnderTest`, and `ScriptedAgent`.
* src/arise_x/chaos/injector.py - `sample_failure` now accepts an injected `random.Random` instance instead of using the global `random` module, enabling reproducible chaos sampling.
* src/arise_x/evaluation/runner.py - Calls the injected `AgentUnderTest` for every task, derives outcomes from the real `AgentResponse` plus seeded chaos sampling, reads disruptions from the scenario, and adds `execute_and_persist_run` to compute run metadata (run ID, scenario version, agent version, config fingerprint, seed) and persist through `RunRepository`; existing `IterationResult` fields and positional `run_reliability_loop(iterations, settings)` calls are unchanged.
* src/arise_x/main.py - Added optional `--scenario`/`--seed` CLI options, persists runs through `RunRepository`, and prints the run ID; existing CLI behavior is preserved.
* src/arise_x/api/app.py - `RunRequest` gained optional `scenario`/`seed` fields; `POST /run` persists through `RunRepository` and returns additive `run_id`, `scenario_version`, `agent_version`, `config_fingerprint`, and `seed` fields alongside the original response keys.

### Added (Phase 1)

* src/arise_x/agents/scripted.py - Deterministic, provider-neutral `ScriptedAgent` implementing `AgentUnderTest` for the procurement scenario.
* tests/test_agent_execution.py - Covers `ScriptedAgent` invocation with expected task IDs/prompts and deterministic output across repeated seeded calls.
* tests/test_api.py - FastAPI `TestClient` coverage for `GET /health`, default `POST /run` legacy-key compatibility, and additive scenario/seed/run-metadata behavior.

### Added (Phase 2)

* src/arise_x/telemetry/trajectory.py - Immutable `Step`, `Trajectory`, `ToolInvocation`, `FaultTrigger`, `UsageMetrics`, and `Outcome` evidence model with `TrajectoryValidationError`; nothing yet calls it (integration lands in Phase 3).
* src/arise_x/trust/vector.py - `VectorDimension` enum, frozen `DimensionScore`, and `ReliabilityVector` for the eight-dimension Agent Reliability Vector; no composite/ARI logic in this file.
* tests/test_trajectory.py - 37 tests covering construction, step ordering/uniqueness, correlation identifiers, invariant validation, redaction-friendly optional fields, immutability, and the `RunEvent` summary projection.
* tests/test_vector.py - 12 tests covering full-vector construction, dimension lookup, out-of-range rejection, missing-evidence handling (unavailable is never a perfect score), dimension independence, and behavioral-stability unavailability.

### Modified (Phase 2)

* src/arise_x/telemetry/events.py - Added `RunEvent.from_trajectory` classmethod projecting a `Trajectory` to the existing flat `RunEvent`; the five existing fields are unchanged.
* src/arise_x/telemetry/__init__.py - Exported the new trajectory symbols alongside the existing `RunEvent` export.

### Modified (Phase 3)

* src/arise_x/evaluation/runner.py - Builds one `Trajectory` per task from the real agent response and seeded chaos sampling, derives `RunEvent` via `RunEvent.from_trajectory`, and computes a per-task `ReliabilityVector` (behavioral_stability left unavailable pending Phase 5 baseline comparison); `RunOutcome` extended with additive trajectories/vectors fields, `IterationResult` and `run_reliability_loop`'s return contract unchanged.
* src/arise_x/storage/repository.py - Bumped schema version to persist trajectories and vectors under the run envelope; old-schema payloads raise `UnsupportedSchemaVersionError`.
* src/arise_x/api/app.py - Added a bounded `reliability_vectors` summary field to `POST /run` and a new `GET /runs/{run_id}` endpoint for explicit detailed trajectory retrieval; existing response keys unchanged.
* src/arise_x/main.py - Prints a reliability-vector summary line alongside the existing run ID output.
* README.md - Documents real scenario execution, deterministic seeded replay, the working CLI invocation, and the reliability vector summary.
* docs/architecture.md - Replaced the five-layer description with the seven-plane target, marking implemented vs. planned planes.

### Added (Phase 4)

* src/arise_x/chaos/catalog.py - Typed fault taxonomy: `FaultLevel` (Infrastructure/Tool/Data/Agent), cross-cutting `FaultFamily` (Cost/Security-Adversarial/Human-in-the-loop per DD-07), `InjectionPoint`, `InjectionStrategy`, and a `CATALOG` registry of `FaultDefinition` entries; documents which faults are runtime-dispatched today vs. cataloged for future dispatch.
* tests/test_chaos.py - 29 tests covering catalog classification validity, seeded deterministic fault dispatch, verified-vs-unverified trigger distinction, and control-vs-experiment outcome comparison.

### Modified (Phase 4)

* src/arise_x/chaos/injector.py - Added `FaultDispatchResult` and `dispatch_fault(...)`, which verifies a fault's effect actually manifested (not just that it was sampled/configured) against a control outcome; existing `DisruptionProfile`/`BASELINE`/`LATENCY_SPIKE`/`TOOL_DEGRADATION`/`sample_failure` behavior is unchanged.
* src/arise_x/evaluation/runner.py - Wires typed catalog fault dispatch into `_execute_task`/`_build_trajectory` so `Step.fault` reflects a real catalog fault ID and verified-trigger status; `_build_reliability_vector`'s recovery dimension credits only verified triggers.
* src/arise_x/scenarios/models.py - Extended disruption references to optionally resolve to a catalog `fault_id` while preserving backward compatibility with existing bare-name references.
* docs/architecture.md - Chaos Plane section now documents the fault catalog structure, dispatched-vs-cataloged faults, trigger-verification methodology, and that Levels 5-6 remain deferred.

### Added (Phase 5)

* src/arise_x/drift/statistics.py - Task-level paired statistical comparison: Wilcoxon signed-rank/paired-permutation for continuous dimensions, exact McNemar restricted to one binary pair per task, Holm-Bonferroni correction, power/sample-size analysis, paired cluster bootstrap confidence intervals, significance-and-effect-size material-drift gating, and a separate downstream-impact-priority signal that never suppresses critical-dimension verdicts.
* src/arise_x/trust/gate.py - Vector-first release policy: geometric-mean ARI over available dimensions (never a raw product), critical goal-success/safety overrides, episode-level SLI classification, trailing error-budget window with allowed/consumed/remaining-budget formula, held-out-suite enforcement (rejects development-only, expired, or mismatched suites), and a `GateVerdict` combining drift, critical, held-out, and error-budget reasons independently.
* tests/test_drift.py - 18 tests covering no-drift, statistical-vs-practical significance, material drift, test-method selection (including the corrected task-level McNemar restriction), sampling-design mismatch rejection, cluster-correlation CI widening, power-derived insufficiency, multiple-test correction, and independent downstream-impact reporting.
* tests/test_gate.py - 34 tests covering episode SLI classification, error-budget arithmetic (including zero-eligible/zero-allowed-bad no-data states), geometric ARI correctness and non-collapsing behavior, held-out-suite rejection scenarios, and pass/warn/block verdicts with independently reported critical/held-out/error-budget reasons.

### Modified (Phase 5)

* pyproject.toml - Added `scipy` runtime dependency for the statistics module.
* src/arise_x/drift/detector.py - Added a `compare_baseline_to_candidate` re-export/wrapper delegating to `drift/statistics.py`; legacy `DriftResult`/`compute_drift_score`/`detect_drift` behavior is byte-for-byte unchanged.
* src/arise_x/config.py - Added minimal additive parsing for an optional `gate_policy` scenario section; existing scenario fields and validation are unchanged.
* configs/experiment.yaml - Added an illustrative, clearly-labeled example `gate_policy` section (critical metrics, alpha, target power, per-dimension minimum detectable effects/tolerances, SLO target, error-budget window).
* src/arise_x/main.py - Added a `gate --baseline-run-id ... --candidate-run-id ...` command with distinct exit codes (0 pass/warn, 1 block, 2 configuration/held-out-suite error).
* src/arise_x/api/app.py - Added a bounded `POST /gate` endpoint reusing the same comparison/evaluation path; `GET /health`, `POST /run`, and `GET /runs/{run_id}` are unchanged.
* tests/test_api.py - Extended with `POST /gate` coverage (pass-shaped response, unknown-run-id error) alongside existing endpoint tests.

### Added (Phase 6)

* src/arise_x/agents/multi_agent.py - Framework-neutral star-topology `Coordinator` composing existing single-agent `AgentUnderTest` workers; correlates assignment, information-exchange, handoff, verification, and objective-completion evidence per episode; defines MACS as a standalone diagnostic type (five milestone components + an explicitly unweighted, uncalibrated aggregate) kept separate from `ReliabilityVector`.
* tests/test_multi_agent.py - Coverage for sub-task assignment/correlation, individually observable milestone components, failure isolation (one failed milestone does not mark others as successful), MACS diagnostic aggregation with missing-component handling, and verifiable `message_loss`/`information_withholding` fault trigger receipts.

### Modified (Phase 6)

* src/arise_x/chaos/catalog.py - Added a `MULTI_AGENT` `FaultLevel` member and Level 5 fault definitions (`agent_disagreement`, `deadlock`, `message_loss`, `conflicting_objectives`, `cascading_failure`, `malicious_agent`) plus MAST-grounded soft-coordination-failure entries (`information_withholding`, `unrequested_clarification_missing`, `reasoning_action_mismatch`); `message_loss` and `information_withholding` are runtime-dispatched, the rest are cataloged-but-not-yet-dispatched.
* src/arise_x/chaos/injector.py - Added `dispatch_message_loss`/`dispatch_information_withholding` for the two runtime-dispatched Level 5 faults, reusing the `FaultDispatchResult` receipt pattern from Phase 4.
* tests/test_chaos.py - Additive coverage for the new `MULTI_AGENT` catalog entries' classification validity; existing Phase 4 coverage unchanged.

### Removed

## Additional or Deviating Changes

* Phase 0 Step 0.2 validation was initially run through the local `.venv` interpreter directly instead of `uv run` due to a transient offline environment; a subsequent `uv sync` succeeded normally and all Phase 0 validation commands now pass through `uv run` as planned.
* Four Ruff `E501` line-length findings from Step 0.1 (docstrings/one test line exceeding 100 characters) were corrected immediately after the phase-implementor report; no behavior changed.
* Phase 5 Step 5.2's error-budget `allowed_bad` calculation initially omitted the epsilon its own docstring described for floating-point rounding safety (`(1.0 - 0.9) * 20` evaluates to `1.9999999999999996`, which floored to `1` instead of `2`), causing two test failures. Added the documented `+ 1e-9` epsilon before flooring; all 34 gate tests and the full 176-test suite pass afterward.
* Manually verified the `gate` CLI command's exit-code contract end-to-end: block (critical-dimension/held-out-suite failure) exits `2` for configuration/held-out-suite errors and `1` for a critical-dimension regression block, distinct from `0` for pass/warn, confirming the plan's requirement that block and configuration-error exit codes never collide.
* Phase 1's `execute_and_persist_run` lives in `runner.py` rather than being duplicated in `main.py`/`api/app.py`, so config-fingerprint and version logic exists once; both transports delegate to it, matching the plan's requirement that transports contain no scoring or chaos policy.
* `RunRepository` is imported under `TYPE_CHECKING` in `runner.py` to avoid a circular import, since `storage/repository.py` already imports `IterationResult` from `runner.py`.
* The CLI validation command `uv run arise-x run-loop --iterations 3` does not work because Typer flattens a single-command app so the command name is not required; this is pre-existing behavior unrelated to Phase 1 (the app had exactly one registered command before and after this phase's changes). The equivalent `uv run arise-x --iterations 3` succeeds and was used for validation instead. Flagged as a pre-existing CLI/documentation follow-up for Phase 7.
* Phase 7 follow-up resolution: Phase 3 added a second CLI command (`@app.command("run-loop")` explicitly, alongside the later Phase 5 `gate` command), so the app is no longer single-command and Typer no longer flattens it. `uv run arise-x run-loop --iterations 3` now works exactly as originally documented; this was reverified during Phase 7 final validation.
* Follow-on scope note (not a blocker): CLI- and API-generated runs are always tagged with `suite_partition="development"` (per the Phase 3 documented default, since suite-driven task selection is not yet wired). This means the `gate` command/endpoint will always correctly `block` on held-out-suite grounds for runs produced by `run-loop`/`POST /run` today; a genuine `pass` verdict is reachable only with directly-constructed held-out-partition evidence (as exercised in `tests/test_gate.py`). This is the intended fail-safe behavior, not a defect, and is tracked as follow-on work item WI-01 (production gate calibration) in the Planning Log.

## Historical Release Summary Superseded by Revalidation

All 8 implementation phases (0-7) are complete. 205 tests pass across 12 test files (`test_agent_execution.py`, `test_api.py`, `test_chaos.py`, `test_config.py`, `test_drift.py`, `test_gate.py`, `test_multi_agent.py`, `test_repository.py`, `test_runner.py`, `test_trajectory.py`, `test_trust.py`, `test_vector.py`), the full repository lints cleanly, the package builds successfully, module/API imports succeed, and CLI/HTTP smoke checks (including the `gate` command/endpoint's pass/block/config-error exit-code and status-code contract) all behave as specified.

**Files created:** `src/arise_x/scenarios/__init__.py`, `src/arise_x/scenarios/models.py`, `src/arise_x/agents/scripted.py`, `src/arise_x/telemetry/trajectory.py`, `src/arise_x/trust/vector.py`, `src/arise_x/chaos/catalog.py`, `src/arise_x/drift/statistics.py`, `src/arise_x/trust/gate.py`, `src/arise_x/agents/multi_agent.py`, `configs/evaluation-suite.yaml`, and 9 new test files.

**Files modified:** `pyproject.toml` (added `pyyaml`, `scipy`, dev-only `httpx`), `configs/experiment.yaml` (versioned procurement scenario plus example gate policy), `src/arise_x/config.py`, `src/arise_x/agents/base.py`, `src/arise_x/chaos/injector.py`, `src/arise_x/evaluation/runner.py`, `src/arise_x/storage/repository.py`, `src/arise_x/drift/detector.py`, `src/arise_x/main.py`, `src/arise_x/api/app.py`, `README.md`, `docs/architecture.md`, and the corresponding modified test files.

**Dependency changes:** Added `pyyaml` and `scipy` as runtime dependencies and `httpx` as a development-only dependency, all via `uv add`.

**Deployment notes:** The synthetic coin-flip runner has been fully replaced by deterministic, seed-reproducible execution of a real `AgentUnderTest` (the scripted procurement agent). The Agent Reliability Vector, verified chaos catalog (Levels 1-4 plus Level 5 multi-agent additions), statistical drift comparison, and geometric-ARI release gate are all functional end-to-end via both the CLI (`run-loop`, `gate`) and the API (`POST /run`, `GET /runs/{run_id}`, `POST /gate`). Production use requires domain-specific calibration of gate thresholds/power targets and suite-driven held-out task selection (see Planning Log follow-on items WI-01 through WI-07) before the release gate can produce a non-`block` verdict against real held-out evidence.
