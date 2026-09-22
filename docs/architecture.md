---
title: ARISE-X Architecture
description: High-level architecture for ARISE-X reliability experimentation
author: ARISE-X Team
ms.date: 2026-09-22
ms.topic: reference
keywords:
  - architecture
  - reliability
  - agentic-ai
estimated_reading_time: 4
---

## System View

ARISE-X targets a seven-plane architecture. Implemented means an executable,
tested product contract exists. Partial means code exists but does not yet
satisfy the plane's production or integration contract.

* Scenario Plane (Implemented): typed, versioned business scenarios and
  evaluation-suite manifests (`scenarios/`, `config.py`) define the
  procurement objective, constraints, disruption references, thresholds,
  seed, and task-family clusters. Loop-generated tasks currently carry the
  development partition identity and are not selected from protected
  held-out payloads.
* Agent Execution Plane (Partial): a deterministic, provider-neutral
  scripted agent (`agents/`) implements the minimum `AgentUnderTest`
  protocol. Optional measurements can be supplied through `AgentResponse`
  without requiring an external SDK or tool runtime. Star-topology
  coordination code exists, but it is not integrated into the product API,
  CLI, or durable run contract.
* Chaos Plane (Partial): a typed fault catalog (`chaos/catalog.py`) defines
  Infrastructure, Tool, Data, and Agent levels plus Cost,
  Security/Adversarial, and Human-in-the-loop cross-cutting families. The
  deterministic scripted adapter implements one bounded local fault at each
  of the four primary levels. Faults are prepared before execution at an
  explicit injection point and verified only from a matching observed effect.
  Receipts record trigger, observation, recovery, abort, blast-radius, and
  control-pair provenance. Other catalog entries remain unsupported at
  runtime, and cross-cutting families do not constitute exhaustive security
  testing. Level 5 durable multi-agent fault integration and Level 6 provider
  or model experiments remain deferred.
* Telemetry Plane (Implemented): every task execution produces an
  immutable, correlated `Trajectory` (`telemetry/trajectory.py`) capturing
  state transitions, fault and recovery evidence, usage, and explicit
  content-redaction markers. Exactly one `RunEvent` compatibility projection
  is retained beside each trajectory and vector. Raw prompt, output, tool
  payload, and tool response content is not persisted.
* Intelligence Plane (Implemented): `drift/detector.py` preserves the legacy
  per-event heuristic, while `drift/statistics.py` owns the release comparison
  contract. It validates paired task identity, reports coverage and confidence,
  derives required observations and achieved power, applies cluster-aware
  paired permutation inference for correlated task families, and corrects
  dimension-level significance with Holm-Bonferroni. Numeric policy values
  remain illustrative until calibrated against representative evidence.
* Reliability Plane (Partial): the Agent Reliability Vector
  (`trust/vector.py`) reports goal success, resilience, recovery, safety,
  efficiency, cost, and autonomy per task from specific trajectory evidence
  references. Behavioral stability is explicitly unavailable for a single
  run. Resilience and recovery are unavailable without verified fault
  evidence. The additive `score_trust` remains a compatibility diagnostic,
  not the primary vector or a release decision.
* CI/CD + Production Plane (Partial): `trust/gate.py` implements a shared gate
  service for the API and CLI, fail-closed required evidence, critical-metric
  overrides, geometric ARI, and an independent trailing production error
  budget. `storage/repository.py` persists versioned immutable decisions with
  policy, suite, statistical rationale, window, and budget snapshots. Automatic
  deployment enforcement, calibrated production thresholds, and provenance
  attestation beyond distinct immutable run identity remain deferred, so a
  gate verdict is not standalone deployment authorization.

## Data Flow

1. The evaluation runner (`evaluation/runner.py`) resolves a scenario and
  agent, prepares the selected bounded local fault before its injection point,
  and executes isolated control/experiment agent instances when required.
2. The adapter reports a typed observation from the injection point. The
  injector verifies the receipt, executes abort policy, and records recovery
  without inferring effects from probability or control success alone.
3. Each task produces one ordered, redacted `Trajectory`, one derived
  compatibility `RunEvent`, and one `ReliabilityVector` under the same task
  and run correlation identifiers.
4. The drift layer computes a drift score and verdict from the projected
   event; the trust layer computes a diagnostic trust score and pass/fail
   status from the same event.
5. The runner derives each available vector dimension from explicit outcome,
  recovery, policy-violation, usage, or intervention references. No transport
  or repository computes scores.
6. `storage/repository.py` validates and persists metadata, iteration results,
  compatibility events, trajectories, and vectors under one strict
  schema-versioned envelope. Incompatible older schemas are rejected, and
  immutable run identifiers address the artifacts.
7. `trust/gate.py` validates paired held-out baseline and candidate records,
  runs per-dimension statistical comparisons, and evaluates critical
  regressions and required evidence without consuming production history.
8. A separate production-history run supplies timestamped episode outcomes.
  The service selects the configured trailing window and computes the exact
  fractional error budget before combining it with candidate evidence.
9. The gate service fingerprints policy and suite snapshots, derives a stable
  decision identity, and writes one immutable decision under `decisions/`.
  Repeated evaluation with the same inputs returns that persisted decision.
10. Results are exposed through the CLI (`main.py`) and API (`api/app.py`):
  the CLI prints the persisted run ID and a bounded vector summary;
  `POST /run` preserves legacy keys and bounded vector summaries; and
  `GET /runs/{run_id}` explicitly returns redacted event, trajectory, and
  vector detail. Both `arise-x gate` and `POST /gate` delegate to the same
  service and return the same decision identity and rationale.

## Release Decision Boundary

The release path separates three evidence classes:

* Baseline and candidate runs provide paired held-out reliability vectors
* The versioned policy and evaluation suite define required dimensions,
  statistical thresholds, clusters, critical metrics, SLI, and budget window
* A different immutable run provides production episode outcomes for the
  trailing error budget

The persisted decision stores identifiers plus canonical policy and suite
snapshots, their SHA-256 fingerprints, per-dimension rationale, categorized
block or warning reasons, selected window inputs, and computed budget state.
It does not store protected task payloads. Repository path confinement,
symlink rejection, strict schema validation, and exclusive creation prevent a
decision from being redirected or overwritten through the persistence API.

## Multi-Agent Boundary

`agents/multi_agent.py` and the in-memory multi-agent runner implement a
star-topology experiment and diagnostic MACS components. They do not have a
durable product API, CLI selector, or persistence schema. Multi-agent evidence
therefore remains outside the current durable run contract.
