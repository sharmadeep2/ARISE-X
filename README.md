---
title: ARISE-X
description: Agentic AI reliability engineering scaffold for long-horizon trust evaluation
author: ARISE-X Team
ms.date: 2026-09-22
ms.topic: overview
keywords:
  - agentic-ai
  - reliability
  - drift-detection
  - trust-scoring
estimated_reading_time: 6
---

## Overview

ARISE-X is an experiment-first reliability framework for autonomous agents.
The current executable path runs deterministic single-agent tasks, records
redacted trajectory evidence, projects compatibility events, derives an
eight-dimension Agent Reliability Vector, and persists each run under an
immutable identifier.

## Repository Layout

```text
ARISE-X/
├── .copilot-tracking/mve/...
├── configs/
├── docs/
├── src/arise_x/
│   ├── agents/
│   ├── api/
│   ├── chaos/
│   ├── drift/
│   ├── evaluation/
│   ├── scenarios/
│   ├── storage/
│   ├── telemetry/
│   └── trust/
└── tests/
```

## Quick Start

```bash
uv sync
uv run arise-x run-loop --iterations 3
```

Each run executes the procurement scenario defined in
[configs/experiment.yaml](configs/experiment.yaml) against the evaluation
configuration in [configs/evaluation-suite.yaml](configs/evaluation-suite.yaml)
using the deterministic scripted agent. Loop-generated tasks currently use
the development partition identity; they are not selected from protected
held-out payloads. Supplying the same scenario and seed produces identical
results. A successful run prints its persisted run ID, the count of
trustworthy iterations, and a bounded summary of the eight-dimension Agent
Reliability Vector for the last task:

```text
Run ID: 1ff0abff48d049049be53e127d460bff
Scenario: procurement-baseline@1
Agent: scripted-agent-v1
Seed: 20260825
Configuration fingerprint: <sha256>
Thresholds: trust=0.75, drift=0.3
Saved 3 iterations to artifacts\latest-run.json
Trustworthy runs: 3/3
Reliability vector (last task): goal_success=1.00, resilience=n/a, behavioral_stability=n/a, recovery=n/a, safety=1.00, efficiency=n/a, cost=n/a, autonomy=1.00
```

`behavioral_stability` remains unavailable until a valid baseline comparison
exists. Resilience and recovery remain unavailable without a verified fault
effect. Efficiency and cost remain unavailable unless the agent adapter
supplies measured latency and cost. See
[docs/architecture.md](docs/architecture.md) for what each dimension
measures. The same evidence is available over HTTP:
`POST /run` returns a bounded per-dimension vector summary alongside the
legacy response keys and run metadata. `GET /runs/{run_id}` is the explicit
detail endpoint for compatibility events, trajectories, and vectors. Prompt,
output, tool payload, and tool response fields are redaction markers, never
raw protected content.

## Bounded Fault Execution

The scripted reference agent supports genuine, deterministic local fault
execution for one representative fault at each of Levels 1 through 4. Each
fault changes a concrete stage in the local task pipeline, emits an observed
effect receipt, and either follows the configured recovery path or preserves
the failed outcome.

| Level | Representative fault | Bounded local effect |
|-------|----------------------|----------------------|
| Infrastructure | `latency_spike` | Local dependency readiness is delayed |
| Tool | `tool_degradation` | Local tool output is marked incomplete |
| Data | `stale_data` | Local data freshness is invalidated |
| Agent | `verification_failure` | Local output verification is skipped |

Fault definitions own typed intensity, activation window, abort policy, blast
radius, expected observation, and runtime-capability fields. The runner
prepares a fault before execution and verifies it only when the agent reports
the matching injection point, observation signal, and evidence references.
A probability draw or successful control run does not verify a fault.

Control and experiment executions use independent agent instances and random
number generators. Their persisted receipts carry pair identifiers, roles,
the control outcome, and a control evidence reference. All current injected
effects are local to one task. They do not use a network, external service,
credential, subprocess target, destructive file operation, or live
infrastructure.

## Release Gate

The release gate compares immutable baseline and candidate runs through one
shared application service used by both HTTP and CLI transports. Release
evidence must be paired by held-out task identity, use matching run seeds and
schemas, match the configured scenario and suite manifest, and preserve task
family, cluster, fingerprint, and repeat-seed metadata. Development evidence
is rejected.

Each configured reliability dimension reports coverage, confidence level,
paired task count, effective cluster count, required observations, achieved
power, practical effect size, confidence interval, and Holm-Bonferroni
corrected significance. Correlated tasks use cluster-aware paired permutation
inference. Missing required dimensions, insufficient independent clusters, or
insufficient power fail closed. Material regressions in critical dimensions
(`goal_success` and `safety` by default) block regardless of the geometric
Agent Reliability Index. Non-critical material drift produces an advisory
`warn` verdict.

The error budget uses a separate immutable production-history run. Candidate
evidence cannot provide or mutate production history. The configured trailing
calendar or episode-count window is selected before evaluation, and the
allowed bad-episode budget is calculated as the exact fractional value
`(1 - SLO target) * eligible episodes`. Missing, insufficient, exhausted, or
invalid production-budget evidence blocks release.

Run the gate from the CLI:

```bash
uv run arise-x gate \
  --baseline-run-id <baseline-run-id> \
  --candidate-run-id <candidate-run-id> \
  --production-history-run-id <production-run-id>
```

The command exits `0` for `pass` or `warn`, `1` for a completed blocking
decision, and `2` when evidence or configuration is invalid. The same workflow
is available through `POST /gate`:

```json
{
  "baseline_run_id": "<baseline-run-id>",
  "candidate_run_id": "<candidate-run-id>",
  "production_history_run_id": "<production-run-id>"
}
```

Completed evaluations return `pass`, `warn`, or `block` in the response body.
Unknown runs return HTTP 404, while invalid evidence or configuration returns
HTTP 422 without exposing repository or manifest exception text.

Every completed evaluation is persisted under
`artifacts/decisions/<decision-id>.json` with exclusive-create semantics. The
record contains input run IDs, policy and suite snapshots and fingerprints,
per-dimension rationale, independent reason groups, production-window inputs,
and error-budget state. Its deterministic identity reuses the existing record
when the same runs, policy, suite, and rationale version are evaluated again.
The numeric policy in [configs/experiment.yaml](configs/experiment.yaml) is an
illustrative contract and requires domain-specific calibration before
production use.

## Validation

```bash
UV_OFFLINE=true UV_NO_SYNC=true uv run pytest tests/test_agent_execution.py tests/test_runner.py tests/test_repository.py tests/test_trajectory.py tests/test_vector.py tests/test_trust.py tests/test_api.py -q -k 'not gate'
UV_OFFLINE=true UV_NO_SYNC=true uv run pytest tests/test_drift.py tests/test_gate.py tests/test_repository.py tests/test_runner.py tests/test_vector.py tests/test_api.py -q
uv run ruff check src tests
uv run arise-x run-loop --iterations 3
```

On PowerShell, set `UV_OFFLINE` and `UV_NO_SYNC` as environment variables
before the pytest command instead of using the POSIX inline assignment form.

## Scope Note

This repository is not production-hardened. Scenario loading, deterministic
single-agent execution, immutable versioned persistence, redacted trajectory
capture, compatibility events, and reliability vectors are implemented and
tested. Bounded local fault injection for representative Infrastructure, Tool,
Data, and Agent faults is implemented and tested. Level 5 durable multi-agent
fault integration remains deferred: star-topology coordination and diagnostic
MACS calculation exist only as in-memory Python paths, without a product API,
CLI selector, or persistence contract. Level 6 provider and model experiments
also remain deferred. Security/adversarial catalog entries are taxonomy
placeholders, not exhaustive security testing or proof of security. Statistical
comparison, policy evaluation, shared gate transports, and immutable decision
persistence are implemented and tested. The bundled thresholds remain
uncalibrated examples, independent production provenance is enforced only by
distinct immutable run identity, and no deployment system consumes the verdict
automatically. The gate is therefore evidence for a release workflow, not
standalone production authorization. See
[docs/architecture.md](docs/architecture.md) for the full seven-plane
target and current implementation status.
