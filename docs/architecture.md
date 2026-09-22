---
title: ARISE-X Architecture
description: High-level architecture for ARISE-X reliability experimentation
author: ARISE-X Team
ms.date: 2026-08-27
ms.topic: reference
keywords:
  - architecture
  - reliability
  - agentic-ai
estimated_reading_time: 4
---

## System View

ARISE-X targets a seven-plane architecture. Each plane below is marked
Implemented (real, tested code exists today), Partial (a slice exists but
the plane's full scope is not built), or Planned (no implementation yet).

* Scenario Plane (Implemented): typed, versioned business scenarios and
  evaluation-suite manifests (`scenarios/`, `config.py`) define the
  procurement objective, constraints, disruption references, thresholds,
  seed, and task-family clusters used to run and gate an episode.
* Agent Execution Plane (Partial): a deterministic, provider-neutral
  scripted agent (`agents/`) implements the minimum `AgentUnderTest`
  protocol. Tool use, retrieval, memory, and multi-agent coordination are
  not built.
* Chaos Plane (Partial): a typed fault catalog (`chaos/catalog.py`) defines
  four primary levels - Infrastructure, Tool, Data, Agent - plus three
  cross-cutting families - Cost, Security/Adversarial, Human-in-the-loop -
  that apply across levels instead of being modeled as a separate level.
  Only three cataloged faults are actually dispatched today:
  `baseline` and `latency_spike` (Infrastructure) and `tool_degradation`
  (Tool), all still driven by the pre-existing probability-boost/latency
  model. `chaos/injector.py`'s `dispatch_fault` samples whether a fault
  fires and additionally verifies the sample actually caused an observable
  effect versus a fault-free control response, rather than crediting a
  fault's configured probability alone (AgentChaos's trigger-verification
  methodology); `evaluation/runner.py` also exposes
  `run_control_and_experiment` to pair a no-fault control execution with a
  faulted experiment execution for the same task. Every Data- and
  Agent-level fault, and the Cost/Security-Adversarial/Human-in-the-loop
  families, are real, correctly classified catalog entries cataloged for
  future dispatch: they have no runtime sampling logic yet because the
  runner still builds exactly one step per task and has no tool-call or
  multi-step pipeline to inject them against. Level 5 (Multi-Agent) and
  Level 6 (Model) remain fully deferred to later phases.
* Telemetry Plane (Implemented): every task execution produces an
  immutable, correlated `Trajectory` (`telemetry/trajectory.py`) capturing
  state transitions, tool calls, faults, recovery, and usage; `RunEvent`
  (`telemetry/events.py`) remains a flat compatibility projection for the
  drift and trust layers.
* Intelligence Plane (Planned): drift detection today (`drift/detector.py`)
  is a heuristic score from a single flat event, not the statistical,
  baseline-aware drift detection or failure classification/root-cause
  analysis the plane targets.
* Reliability Plane (Partial): the Agent Reliability Vector
  (`trust/vector.py`) reports goal success, resilience, recovery, safety,
  efficiency, cost, and autonomy per task from trajectory evidence.
  `behavioral_stability` is always reported unavailable because no
  historical baseline exists yet, and the gating Agent Reliability Index is
  not computed. The additive `score_trust` (`trust/scorer.py`) remains a
  temporary diagnostic compatibility projection, not the primary artifact.
* CI/CD + Production Plane (Planned): release-gating policy, regression
  comparison against a golden baseline, and continuous production
  monitoring are not built; `storage/repository.py` persists versioned run
  evidence but does not gate deployments.

## Data Flow

1. The evaluation runner (`evaluation/runner.py`) resolves a scenario and
   agent, then executes each task through the agent under a chosen
   disruption profile using a seeded random source.
2. Each task's execution evidence, including the agent's response and the
   catalog fault dispatch's trigger-verification outcome, is captured as an
   ordered `Trajectory` (its `FaultTrigger` step evidence records the
   catalog `fault_id` and whether the trigger was verified) and projected
   into a compatibility `RunEvent`.
3. The drift layer computes a drift score and verdict from the projected
   event; the trust layer computes a diagnostic trust score and pass/fail
   status from the same event.
4. The runner derives a per-task `ReliabilityVector` from the trajectory's
   outcome, fault, timing, and usage evidence.
5. `storage/repository.py` persists the run's metadata, iteration results,
   trajectories, and vectors together under one schema-versioned envelope,
   retrievable by an immutable run ID.
6. Results are exposed through the CLI (`main.py`) and API (`api/app.py`):
   both report the run ID and a bounded reliability-vector summary, and the
   API additionally exposes full trajectory/vector detail through an
   explicit, opt-in `GET /runs/{run_id}` endpoint.
