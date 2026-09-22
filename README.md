---
title: ARISE-X
description: Agentic AI reliability engineering scaffold for long-horizon trust evaluation
author: ARISE-X Team
ms.date: 2026-08-27
ms.topic: overview
keywords:
  - agentic-ai
  - reliability
  - drift-detection
  - trust-scoring
estimated_reading_time: 6
---

## Overview

ARISE-X is a continuous reliability engineering system for autonomous agents. This repository provides a practical starter structure to evaluate long-horizon behavior, inject controlled disruption, detect drift, and produce trustworthiness decisions for release gating.

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
uv init
uv add fastapi pydantic typer uvicorn ipykernel ipywidgets ruff tqdm pytest pyyaml
uv sync
uv run arise-x --iterations 3
```

> [!NOTE]
> The CLI exposes a single Typer command (`run-loop`). Typer flattens
> single-command apps into the top-level invocation, so pass options directly
> after `arise-x` without the `run-loop` token, for example
> `uv run arise-x --iterations 3 --seed 20260825`.

Each run executes the procurement scenario defined in
[configs/experiment.yaml](configs/experiment.yaml) against the evaluation
suite in [configs/evaluation-suite.yaml](configs/evaluation-suite.yaml),
using the deterministic scripted agent. Supplying the same scenario and seed
produces identical results, so runs are reproducible for debugging and
regression comparison. A successful run prints its persisted run ID, the
count of trustworthy iterations, and a summary of the eight-dimension Agent
Reliability Vector for the last executed task:

```text
Run ID: 9650e213715e4292af1ab65d9eea7efe
Saved 3 iterations to artifacts\latest-run.json
Trustworthy runs: 2/3
Reliability vector (last task): goal_success=1.00, resilience=1.00, behavioral_stability=n/a, recovery=n/a, safety=1.00, efficiency=0.73, cost=0.97, autonomy=1.00
```

`behavioral_stability` and `recovery` report `n/a` when no historical
baseline exists yet or no fault triggered for that task; see
[docs/architecture.md](docs/architecture.md) for what each dimension
measures and which planes still need to land before every dimension is
always available. The same run and vector evidence is available over HTTP:
`POST /run` returns a bounded per-dimension vector summary alongside the
existing run metadata, and `GET /runs/{run_id}` returns the full persisted
trajectory and vector detail for one run.

## Scope Note

This scaffold is experiment-first rather than production-hardened. Scenario
execution, deterministic seeded replay, versioned persistence, trajectory
capture, and the reliability vector are real and tested today. A typed
fault catalog (`chaos/catalog.py`) now covers Infrastructure, Tool, Data,
and Agent levels plus Cost, Security/Adversarial, and Human-in-the-loop
cross-cutting families, and dispatch verifies whether a sampled fault
actually caused an observed effect rather than crediting its configured
probability alone; only the baseline, `latency_spike`, and
`tool_degradation` faults are wired into task execution today, and the
remaining catalog entries, statistical drift detection, release-gating
policy, and multi-agent coordination remain planned. See
[docs/architecture.md](docs/architecture.md) for the full seven-plane
target and current implementation status.
