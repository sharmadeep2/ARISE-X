---
title: ARISE-X Planning Anchor Verification
description: Verified implementation-planning anchors for the ARISE-X framework validation roadmap
ms.date: 2026-08-25
ms.topic: reference
---

## Research Scope

* Verify exact Phase 0-4 change surfaces, owning symbols, responsibilities, and dependencies
* Identify minimal new models, scoring, drift, release-gate, and test files
* Verify repository validation commands
* Assess phase ordering, parallel work, and shared-file constraints
* Identify compatibility decisions, existing plan artifacts, and stale research claims

## Findings

Status: Complete.

Recommended task slug: `arise-x-framework-validation-implementation`.

The implementation should use five phases, numbered Phase 0 through Phase 4. The
default dependency order is Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4.

## Verified Change Surfaces

* pyproject.toml:1-33. The current owners are `[project]` and its dependencies at
  lines 1-17, `[project.optional-dependencies]` at lines 19-22, `[project.scripts]`
  at lines 24-25, `[build-system]` at lines 27-29, and pytest configuration at
  lines 31-33. Phase 0 should add the YAML parser dependency; Phase 3 should add
  the statistical dependency selected for distribution tests. The file remains
  the dependency, packaging, CLI entry-point, and test-discovery authority. Phase
  3 dependency changes rely on the Phase 1 fingerprint and vector contracts.
* configs/experiment.yaml:1-12. The current owner is the singular `experiment`
  mapping, with horizons at lines 3-5, disruptions at lines 6-9, and thresholds
  at lines 10-12. Phase 0 should make it a validated scenario input, Phase 2 should
  add fault definitions and trigger policy, Phase 3 should add release-gate policy,
  and Phase 4 should add optional multi-agent topology. Each extension depends on
  the scenario models and parser established in Phase 0.
* src/arise_x/config.py:1-26. `Settings` owns environment defaults at lines 10-18;
  `load_settings` owns construction and output-directory creation at lines 21-26.
  Phase 0 should load typed experiment configuration, preserve environment
  overrides, and carry a deterministic seed. Later phases should expose typed
  chaos, drift, gate, and multi-agent policies without moving domain behavior into
  configuration. This depends on the Phase 0 scenario models and YAML dependency.
* src/arise_x/agents/base.py:1-23. `AgentResponse` owns the current result contract
  at lines 9-16, and `AgentUnderTest.run_task` owns the synchronous integration
  protocol at lines 19-23. Phase 0 should make this protocol part of the runner's
  real execution path. Phase 1 may add optional trajectory metadata, and Phase 4
  should introduce multi-agent composition without changing the single-agent
  method. Those changes depend on the scenario and trajectory contracts.
* src/arise_x/evaluation/runner.py:1-67. `IterationResult` owns the public run
  summary at lines 15-23, `_simulate_event` owns the synthetic path at lines 26-42,
  and `run_reliability_loop` owns orchestration at lines 45-67. Phase 0 should inject
  an agent and seeded random source, Phase 1 should orchestrate trajectories and
  vectors, Phase 2 should apply verified faults, Phase 3 should compare windows and
  emit gate inputs, and Phase 4 should orchestrate multiple agents. This is the main
  integration point and must follow the contracts delivered by every prior phase.
* src/arise_x/telemetry/events.py:1-17. `RunEvent` owns the flat compatibility event
  at lines 8-17. Phase 1 should retain it as a summary or adapter while detailed
  trajectory models move to a new module. Phase 2 should add fault-trigger evidence,
  Phase 3 should expose fingerprint dimensions, and Phase 4 should include agent and
  correlation identifiers. These changes depend on the Phase 1 trajectory contract.
* src/arise_x/chaos/injector.py:1-27. `DisruptionProfile` owns the current disruption
  shape at lines 9-15, the three profiles are at lines 18-20, and `sample_failure`
  owns unseeded sampling at lines 23-27. Phase 0 should accept an injected random
  source. Phase 2 should dispatch catalog faults and return trigger evidence. Phase
  4 should support Level 5 coordination faults. Phase 2 depends on scenario injection
  points and trajectory events from Phases 0 and 1.
* src/arise_x/drift/detector.py:1-34. `DriftResult` owns the current verdict at lines
  10-15, `compute_drift_score` owns the single-event heuristic at lines 18-27, and
  `detect_drift` owns thresholding at lines 30-34. Phase 3 should turn this module
  into a facade over baseline-versus-window statistical results while preserving a
  temporary legacy wrapper. It depends on Phase 0 historical reads, Phase 1
  fingerprint data, Phase 2 trigger evidence, and the new statistics module.
* src/arise_x/trust/scorer.py:1-26. `TrustDecision` owns the current score and verdict
  at lines 11-16, and `score_trust` owns the additive three-factor calculation at
  lines 19-26. Phase 1 should keep this only as a compatibility diagnostic while the
  vector becomes primary. Phase 3 should consume the vector through a separate gate,
  and Phase 4 should add MACS as an optional vector dimension or diagnostic. It
  depends on the Phase 1 vector and Phase 3 drift result contracts.
* src/arise_x/storage/repository.py:1-17. `write_results` owns JSON serialization at
  lines 12-17. Phase 0 should add typed read, list, and versioned-run operations;
  Phase 1 should persist trajectories and vectors; Phase 3 should retrieve baseline
  and candidate windows plus gate decisions; Phase 4 should retain multi-agent
  correlation data. Each schema change depends on the corresponding prior model.
* src/arise_x/main.py:1-48. The Typer application is declared at line 17,
  `run_loop` owns execution and persistence at lines 20-31, and `main` owns exit
  behavior at lines 34-48. Phase 0 should add scenario, seed, and agent selection;
  Phase 3 should add a `gate` command; Phase 4 may add topology selection. CLI work
  should follow service-layer completion and should not own evaluation logic.
* src/arise_x/api/app.py:1-31. The FastAPI application is at line 11, `RunRequest`
  owns the current request at lines 14-15, `health` owns `GET /health` at lines 18-20,
  and `run_loop` owns `POST /run` at lines 23-31. Phase 0 should accept scenario and
  seed inputs, Phase 1 should expose trajectory/vector identifiers without removing
  current response keys, Phase 3 may expose gate decisions, and Phase 4 may accept a
  topology identifier. API changes depend on runner and persistence contracts.
* tests/test_runner.py:1-32. The current owners are the count test at lines 9-17 and
  disruption-label test at lines 20-32. This remains the end-to-end orchestration
  suite: Phase 0 adds deterministic real-agent assertions, Phase 1 adds trajectory
  and vector assertions, Phase 2 adds verified-injection behavior, Phase 3 checks
  baseline/candidate integration, and Phase 4 covers multi-agent orchestration. It
  depends on each phase's stable public contract.
* tests/test_trust.py:1-45. The healthy-case test owns lines 10-26 and the failed-case
  test owns lines 29-45. Phase 1 should preserve these legacy expectations and add
  vector-specific coverage in a new file. Phase 3 should move gate and critical-metric
  override coverage to a dedicated gate suite. It depends on compatibility wrappers
  in `trust/scorer.py`.
* README.md:1-49. Repository layout is owned at lines 19-36, Quick Start at lines
  38-45, and the experiment-first scope statement at lines 47-49. Update it after
  each phase to document only working commands and contracts: scenario execution in
  Phase 0, vector outputs in Phase 1, verified chaos in Phase 2, release gating in
  Phase 3, and multi-agent support in Phase 4. Documentation depends on validated
  behavior and should land after code and tests in each phase.
* docs/architecture.md:1-30. `System View` owns the five-layer description at lines
  14-22, and `Data Flow` owns the current five-step flow at lines 24-30. Phase 1
  should establish the seven-plane target and trajectory/vector flow; Phases 2-4
  should fill in verified chaos, statistical intelligence and gating, then
  multi-agent execution. Each update depends on the corresponding tested behavior.

## New Files

The package layout supports small domain modules without introducing a framework or
service layer.

* Phase 0 should create src/arise_x/scenarios/__init__.py and
  src/arise_x/scenarios/models.py. The models module should own frozen scenario,
  threshold, horizon, disruption-reference, and experiment definitions. YAML I/O
  stays in `config.py` to avoid an unnecessary loader abstraction.
* Phase 1 should create src/arise_x/telemetry/trajectory.py for immutable trajectory
  and step records, and src/arise_x/trust/vector.py for the eight normalized Agent
  Reliability Vector dimensions and vector calculation. `RunEvent` and
  `TrustDecision` remain compatibility projections.
* Phase 2 should create src/arise_x/chaos/catalog.py for typed fault definitions,
  injection points, levels, and trigger receipts. `injector.py` remains the runtime
  dispatcher. This split permits fault-family work without turning the injector into
  a schema registry.
* Phase 3 should create src/arise_x/drift/statistics.py for per-dimension tests,
  effect sizes, confidence/tolerance checks, and multiple-test policy. It should also
  create src/arise_x/trust/gate.py for `GatePolicy`, critical-metric overrides,
  no-data handling, ARI calculation, and the final release verdict.
* Phase 4 should create src/arise_x/agents/multi_agent.py for a minimal coordinator
  and milestone observations. MACS should be calculated through `trust/vector.py`
  rather than a separate scoring subsystem.
* Phase 0 tests should add tests/test_config.py, tests/test_agent_execution.py, and
  tests/test_repository.py. Phase 1 should add tests/test_trajectory.py and
  tests/test_vector.py. Phase 2 should add tests/test_chaos.py. Phase 3 should add
  tests/test_drift.py and tests/test_gate.py. Phase 4 should add
  tests/test_multi_agent.py. Existing runner and trust tests remain integration and
  compatibility coverage.

## Validation Commands

The following commands are the exact repository validation sequence supported by
the current metadata:

```bash
uv sync
uv run pytest
uv run ruff check .
uv build
uv run arise-x run-loop --iterations 3
uv run python -c "import arise_x; from arise_x.api.app import app"
```

`uv sync` and the CLI smoke command are stated verbatim in README.md:43-44. The
pytest command follows the declared pytest dependency and configuration in
pyproject.toml:16 and pyproject.toml:31-33. The Ruff command follows the declared
dependency at pyproject.toml:14 and ruff.toml. `uv build` follows the setuptools
build backend at pyproject.toml:27-29. The final command is the recommended explicit
package/API import smoke check; it is not currently documented. No `uv.lock` exists,
so the first `uv sync` can create one. The README's `uv init` and `uv add ...` lines
are repository bootstrap commands, not repeatable validation commands.

These commands were verified from repository metadata but not executed, because
`uv sync`, `uv build`, the CLI, and imports can create lock, build, artifact, or cache
files and this task is research-only.

## Phase Ordering And Parallel Work

1. Phase 0 establishes scenario configuration, deterministic execution, a real
   single-agent call path, and readable/versioned storage. Scenario/configuration,
   agent/random-source plumbing, and repository operations can proceed in parallel.
   Runner integration must wait for the scenario and agent contracts; CLI, API, and
   integration tests follow the runner. No earlier implementation phase is required.
2. Phase 1 establishes trajectories and the reliability vector. The trajectory and
   vector modules can proceed in parallel after Phase 0 contracts freeze. Runner,
   persistence, and response integration touch shared files and should be merged only
   after both model tracks pass focused tests. Phase 1 depends on Phase 0.
3. Phase 2 establishes the expanded chaos catalog and trigger verification. Data-fault
   and agent-fault definitions plus their tests can proceed in parallel in the catalog,
   but `injector.py`, `runner.py`, configuration, and telemetry are shared merge points.
   Phase 2 depends on scenario injection points and trajectory evidence from Phases 0-1.
4. Phase 3 establishes statistical drift and release gating. Statistical-test code and
   gate-policy types can begin in parallel after Phase 1, and the statistics track may
   overlap Phase 2 if the telemetry contract is frozen. Gate evaluation, runner/CLI/API
   integration, and acceptance tests must wait for Phase 2 trigger receipts and final
   drift/vector outputs. Phase 3 is not complete until Phases 0-2 are integrated.
5. Phase 4 establishes multi-agent execution, Level 5 chaos, and MACS. Coordinator,
   Level 5 fault definitions, and MACS fixtures can proceed in parallel against frozen
   contracts. Changes to `agents/base.py`, `runner.py`, `trust/vector.py`, configuration,
   CLI, and API are shared integration points and should be serialized. Phase 4 depends
   on the release-evidence pipeline from Phases 0-3 and should not overlap its integration.

## Backwards Compatibility

The default path should be an additive migration with short-lived compatibility
projections. The project is version 0.1.0 and explicitly experiment-first, so it does
not need permanent legacy architecture, but preserving low-cost public entry points
will keep each phase independently testable.

* Keep `run_reliability_loop(iterations, settings)` positional behavior and add
  keyword-only `agent`, `scenario`, and random-source inputs with deterministic
  defaults. Remove `_simulate_event` once the default test agent exists; it is private.
* Keep the five current `IterationResult` fields and append optional/defaulted
  trajectory, vector, run, and gate identifiers. Do not add required fields to the
  existing frozen dataclass.
* Keep `AgentUnderTest.run_task(task_id, prompt)` for single-agent adapters. Add richer
  context through a new protocol or optional capabilities instead of changing the
  method in place. Append only defaulted fields to `AgentResponse`.
* Keep `RunEvent` as a summary derived from a trajectory for one transition period.
  New trajectory dataclasses should be the internal source of truth.
* Add a new statistical drift API that accepts baseline and candidate windows. Keep
  `detect_drift(event, threshold)` as a clearly marked legacy severity wrapper until
  callers migrate; do not pretend the old per-event score is statistical drift.
* Add vector scoring and release-gate APIs rather than changing
  `score_trust(event, drift, threshold)` in place. Keep the additive score only as a
  diagnostic compatibility projection, never as ARI.
* Preserve `write_results`, add typed read/list methods, and version persisted schemas.
  Preserve `POST /run` keys and `run-loop`; add fields and a separate `gate` command or
  endpoint. A deliberate breaking cleanup can remove wrappers before 1.0 after all
  in-repository callers and any confirmed external consumers migrate.

## Existing Tracking Artifacts

No `.copilot-tracking/plans/`, `.copilot-tracking/details/`, or
`.copilot-tracking/plans/logs/` directory exists, so there is no duplicate task name
in the requested planning namespaces.

The adjacent MVE already uses the slug `arise-x-reliability-engine` and overlaps the
experiment scope. A new implementation plan should reference, not recreate, these
artifacts:

* .copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/mve-plan.md
* .copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/context.md
* .copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/hypotheses.md
* .copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/vetting.md
* .copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/experiment-design.md

## Stale Or Inconsistent Research Claims

The architectural conclusions remain valid, but several concrete anchors in the
primary research and its codebase-analysis source are stale.

* Current file lengths are pyproject.toml 33 lines, config.py 26, runner.py 67,
  telemetry/events.py 17, chaos/injector.py 27, drift/detector.py 34,
  trust/scorer.py 26, storage/repository.py 17, README.md 49, and
  docs/architecture.md 30. Earlier claims cited 28, 24, 56, 13, 24, 27, 23, 16,
  approximately 34, and approximately 26 lines respectively.
* The primary research's YAML example uses an `experiments:` list. The current file
  uses one singular `experiment:` mapping at configs/experiment.yaml:1-12.
* The primary research places `POST /run` at lines 21-28. It is currently at
  src/arise_x/api/app.py:23-31; `RunRequest` is at lines 14-15 and `GET /health` is
  at lines 18-20.
* `Settings` values are described as loaded when `load_settings()` runs, but the
  `os.getenv` default expressions at src/arise_x/config.py:14-18 are evaluated when
  the module defines the dataclass. Environment changes after import are not re-read.
* The README does not document pytest, Ruff, build, or import validation. Those
  commands are supported by metadata but must be added after they are validated.
* The claims that experiment YAML is unwired, all runtime randomness is unseeded,
  `AgentUnderTest` is unused, storage is write-only, drift is per-event heuristic,
  trust is additive, and no drift test exists remain accurate in current code.

## Blocking Questions

There is no blocker to writing the phased implementation plan. Implementation requires
answers to these questions before the named phases can meet acceptance criteria:

* Which concrete agent adapter and representative business workflow should Phase 0
  execute instead of `_simulate_event`?
* What identifies a golden baseline: a run ID, agent version, Git commit, explicit
  artifact path, or a combination of these?
* Which vector dimensions are critical auto-fail metrics, and what practical effect
  tolerances and minimum sample sizes should Phase 3 use?
* Are PyYAML and SciPy acceptable dependencies, or must parsing and statistics use a
  different approved library set?
* Which Phase 4 coordination topology and milestone definition should ground MACS?

## References

* .copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md
* .copilot-tracking/research/subagents/2026-08-25/codebase-analysis.md
* intial analysis and requirement.md
* pyproject.toml
* README.md
* configs/experiment.yaml
* docs/architecture.md
* src/arise_x/
* tests/

## Follow-On Research

* Select the Phase 0 representative agent and scenario with the domain owner.
* Define Phase 3 baseline identity, sample-size policy, tolerances, and critical metrics.
* Ground Phase 4 MACS milestones in one chosen coordination topology.

## Clarifying Questions

The implementation-blocking questions are listed above. No additional research-only
clarification is required.
