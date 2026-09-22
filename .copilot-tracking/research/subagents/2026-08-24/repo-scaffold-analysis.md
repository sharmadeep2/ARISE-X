<!-- markdownlint-disable-file -->
# Subagent Research: ARISE-X Repository Scaffold Analysis

## Research Topics / Questions

* Full file inventory of the local ARISE-X repository (excluding `.git` internals).
* Contents and purpose of every file under `src/arise_x/`, `tests/`, `configs/`, `docs/`, plus `pyproject.toml`, `ruff.toml`, `README.md`, root `.env.example`/`.gitignore`, and `.copilot-tracking/mve/**`.
* Structured inventory per module: responsibility, key functions/classes, maturity level.
* Explicit gaps/simplifications versus the full 7-plane ARISE-X vision (scenario definitions, 6-level chaos taxonomy, full trajectory capture, behavioral fingerprinting/drift, multiplicative ARI, CI/CD regression gate + production feedback loop).
* Naming/structure/convention choices worth preserving for continuity.

## Research Executed

### File Inventory (excluding `.git/`)

```text
ARISE-X/
├── .env.example
├── .gitignore
├── intial analysis and requirement.md
├── pyproject.toml
├── README.md
├── ruff.toml
├── .copilot-tracking/
│   ├── mve/2026-08-24/arise-x-reliability-engine/
│   │   ├── context.md
│   │   ├── hypotheses.md
│   │   ├── vetting.md
│   │   ├── experiment-design.md
│   │   └── mve-plan.md
│   └── research/2026-08-24/
│       └── arise-x-agent-reliability-platform-research.md   (parent task-research doc; scaffold section still "Pending")
├── configs/
│   └── experiment.yaml
├── docs/
│   └── architecture.md
├── src/arise_x/
│   ├── __init__.py                (package version marker)
│   ├── config.py                  (Settings dataclass + load_settings)
│   ├── main.py                    (Typer CLI entry point)
│   ├── agents/
│   │   ├── __init__.py
│   │   └── base.py                (AgentResponse, AgentUnderTest Protocol)
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py                 (FastAPI app: /health, /run)
│   ├── chaos/
│   │   ├── __init__.py
│   │   └── injector.py            (DisruptionProfile, 3 profiles, sample_failure)
│   ├── drift/
│   │   ├── __init__.py
│   │   └── detector.py            (DriftResult, compute_drift_score, detect_drift)
│   ├── evaluation/
│   │   ├── __init__.py
│   │   └── runner.py              (IterationResult, run_reliability_loop)
│   ├── storage/
│   │   ├── __init__.py
│   │   └── repository.py          (write_results — JSON file writer)
│   ├── telemetry/
│   │   ├── __init__.py
│   │   └── events.py               (RunEvent dataclass)
│   └── trust/
│       ├── __init__.py
│       └── scorer.py               (TrustDecision, score_trust)
└── tests/
    ├── test_runner.py             (2 tests for run_reliability_loop)
    └── test_trust.py              (2 tests for score_trust)
```

Total non-git files found via search: 34.

### File-by-File Summary

**Root docs**

* `README.md` — Frontmatter-styled overview (title/description/author/ms.date). States ARISE-X is "a continuous reliability engineering system... to evaluate long-horizon behavior, inject controlled disruption, detect drift, and produce trustworthiness decisions for release gating." Documents repo layout, a Quick Start using `uv` (`uv init`, `uv add fastapi pydantic typer uvicorn ipykernel ipywidgets ruff tqdm pytest`, `uv sync`, `uv run arise-x run-loop --iterations 3`), and an explicit **Scope Note**: "This scaffold is intentionally experiment-first... for speed of learning and evidence generation, not production hardening."
* `intial analysis and requirement.md` — The original founder write-up (not yet renamed/typo-fixed: "intial"). Contains the full product vision: naming rationale (Agent Reliability & Intelligence System for Experimentation), problem framing (today's flat agent testing vs. ARISE-X's long-horizon chaos-aware pipeline), the procurement-agent example scenario, the "Agent Behavioral Drift"/fingerprint concept, the **7-plane architecture**, the **Chaos Plane taxonomy (6 levels)**, the **Long-Horizon Engine** trajectory model, the **Agent Reliability Vector** and multiplicative **ARI** formula, the CI/CD gate narrative, the production feedback loop, and 5 proposed IP metrics (ARS, ARS-R, BSI, AES, MACS). This is the authoritative vision document the scaffold should be compared against.
* `docs/architecture.md` — Much smaller, current-state architecture: describes only **5 functional layers** (Evaluation Orchestrator, Chaos Layer, Drift Layer, Trust Layer, Storage/API Layer) and a 5-step linear data flow (orchestrator runs → telemetry event emitted → drift score computed → trust score computed → results persisted/served). This is a simplified architecture describing what's actually implemented, not the 7-plane vision.
* `pyproject.toml` — `arise-x` v0.1.0, Python `>=3.11`. Deps: `fastapi`, `pydantic`, `typer`, `uvicorn`, `ipykernel`, `ipywidgets`, `ruff`, `tqdm`, `pytest` (all runtime deps, not split into dev-only except `pytest-cov` under `[project.optional-dependencies].dev`). `[project.scripts]` registers `arise-x = "arise_x.main:main"`. Build backend is `setuptools` (not `hatchling`/`uv_build`). Pytest config sets `testpaths = ["tests"]` and `pythonpath = ["src"]` (src-layout).
* `ruff.toml` — Minimal: `line-length = 100`, `target-version = "py311"`, lint select `["E", "F", "I", "UP", "B"]` (pycodestyle errors, pyflakes, isort, pyupgrade, bugbear). No per-file ignores, no docstring/complexity rules configured yet.
* `.env.example` — Documents 5 env vars consumed by `config.py`: `ARISE_ENV`, `ARISE_TELEMETRY_BACKEND`, `ARISE_TRUST_THRESHOLD`, `ARISE_DRIFT_THRESHOLD`, `ARISE_OUTPUT_DIR`.
* `.gitignore` — Standard Python ignores plus project-specific `logs/`, `artifacts/`, `reports/` (matches `output_dir` default of `artifacts/`), and `.env*`.
* `configs/experiment.yaml` — Declares an `experiment` named `arise-x-baseline` with `horizons: [24h, 7d]`, `disruptions: [baseline, latency_spike, tool_degradation]`, and `thresholds: {trust: 0.75, drift: 0.30}`. **This file is not read anywhere in `src/`** — thresholds are actually sourced independently from env vars in `config.py` (`ARISE_TRUST_THRESHOLD=0.75`, `ARISE_DRIFT_THRESHOLD=0.30`, matching values but no code path loads the YAML). The 24h/7d horizons and named experiment are also not consumed by any runner logic — `run_reliability_loop` takes a plain `iterations: int` with no horizon concept.

**`.copilot-tracking/mve/2026-08-24/arise-x-reliability-engine/` (5-phase MVE plan for a scoped experiment, distinct from the full product vision)**

* `context.md` (Phase 1) — Problem statement: teams can validate agents in short curated benchmarks but lack confidence in long-horizon production behavior under volatility. Names primary customer (platform/reliability engineering teams), secondary stakeholders (model governance, safety, product), constraints (experiment-speed over production-hardening, synthetic/replayable scenarios for cost control), assumptions, key unknowns (which disruption types predict real failures, which drift signals correlate with trust loss, what evidence threshold triggers downgrade), and open next-context questions (target agent domain, which production constraints matter most, target time horizon).
* `hypotheses.md` (Phase 2) — Three prioritized hypotheses:
  * **H1** (P1): targeted disruptions reveal reliability weaknesses invisible in static benchmarks; validated via reproducible degradation across ≥3 disruption classes.
  * **H2** (P1): behavioral drift features (goal divergence, policy-violation rate, escalating interventions, output-consistency drop) can detect trust degradation early; success = ≥0.80 precision / ≥0.75 recall vs. labeled trust events.
  * **H3** (P2): composite trust score can drive release decisions; success = ≥85% agreement with expert review. H1/H2 must stabilize before H3 finalizes.
* `vetting.md` (Phase 3) — Overall status "viable with caution flags." Business sense and problem crispness pass. RAI status is "conditional pass" (needs segmented fairness analysis, telemetry scrubbing/synthetic data, auditable score composition, named accountable owner). Red-flag checklist mostly clear except caution items: no named sponsor yet, no confirmed owning-team execution plan, risk that stakeholders over-assume production readiness from prototype code. Mitigations: explicit non-production disclaimer, named decision owner, data-handling policy before trace collection.
* `experiment-design.md` (Phase 4) — Defines experiment type (architectural/agent feasibility + reliability validation + E2E prototyping). Scope: **one** representative agent workflow, 3–5 disruption classes, 24h/7d-equivalent long-horizon simulation, composite trust score prototype. Explicitly **out of scope**: production hardening, full multi-agent orchestration, broad UI. 4-week timeline (harness/baseline → disruption injectors → drift/trust evaluation → analysis/calibration). Named team: 1 reliability engineer, 1 ML/agent engineer, 1 domain reviewer.
* `mve-plan.md` (Phase 5) — Consolidates the above into one execution artifact with the same hypotheses/success-criteria/timeline, plus a mixed-outcome branch (if H1 succeeds but H2/H3 underperform, keep the disruption harness as a standalone layer while iterating drift/trust in a second MVE cycle).

This MVE suite confirms the current scaffold is deliberately scoped as a **narrow, single-workflow feasibility experiment** (not the full 7-plane platform), consistent with the README's "experiment-first... not production hardening" note.

**`.copilot-tracking/research/2026-08-24/arise-x-agent-reliability-platform-research.md`** — A parent task-research document that explicitly lists "Existing repo scaffold analysis" as a still-pending subtask ("Pending repo scaffold analysis") and references this exact scaffold as something to assess against broader research findings. This subagent document fulfills that specific pending piece.

### Module-by-Module Maturity Inventory

| Module | Responsibility (current) | Key types/functions | Maturity |
|---|---|---|---|
| `agents/base.py` | Defines the integration contract for any agent under test | `AgentResponse` (frozen dataclass: `task_id`, `output_text`, `policy_violations`, `interventions`); `AgentUnderTest` (Protocol with `run_task(task_id, prompt) -> AgentResponse`) | **Stub / interface-only.** No concrete agent implementation exists anywhere in the repo; nothing implements `AgentUnderTest`. `AgentResponse` fields are also unused by the actual runner (which builds `RunEvent` directly from a random simulation, not from an agent call). |
| `chaos/injector.py` | Provides disruption profiles and a failure-sampling function | `DisruptionProfile` (frozen dataclass: `name`, `failure_boost`, `latency_multiplier`); 3 constants (`BASELINE`, `LATENCY_SPIKE`, `TOOL_DEGRADATION`); `sample_failure(base_failure_rate, profile) -> bool` (pure RNG threshold check) | **Minimal working prototype.** Only 3 named profiles, no chaos taxonomy/levels, no tool/data/agent/multi-agent/model fault types, disruption effect is a single scalar boost to a Bernoulli failure probability plus a latency multiplier — no structured fault injection into an actual agent execution path. |
| `drift/detector.py` | Computes a bounded heuristic drift score and threshold verdict per event | `DriftResult` (frozen dataclass: `score`, `is_drifting`); `compute_drift_score(event) -> float` (weighted sum of failure flag, policy violations, interventions, latency, each capped); `detect_drift(event, threshold) -> DriftResult` | **Stub / minimal heuristic.** Single-event drift score, not a fingerprint comparison over time or across versions. No baseline-vs-current comparison, no embedding/statistical drift methods, no behavioral fingerprint concept, no historical trend/aggregation. |
| `evaluation/runner.py` | Orchestrates iterations across a fixed disruption rotation and computes drift/trust per iteration | `IterationResult` (frozen dataclass: `task_id`, `disruption`, `drift_score`, `trust_score`, `trustworthy`); `_simulate_event(...)` (private, pure random simulation — no real agent call); `run_reliability_loop(iterations, settings) -> list[IterationResult]` | **Minimal working prototype, fully synthetic.** No real agent execution (uses `random.uniform`/`random.random` to fabricate outcomes), no trajectory/step-level capture, no long-horizon concept (just a loop of N independent iterations cycling through 3 hardcoded disruption names), no scenario objects (no objectives/constraints/forbidden behaviors). |
| `trust/scorer.py` | Computes a weighted composite trust score and pass/fail verdict | `TrustDecision` (frozen dataclass: `score`, `trustworthy`); `score_trust(event, drift, threshold) -> TrustDecision` (weighted sum: `0.45*reliability + 0.30*safety + 0.25*stability`) | **Stub / minimal heuristic.** This is an **additive weighted-sum** model, not the vision's **multiplicative** ARI (`GoalSuccess × Resilience × BehavioralStability × Safety × Recovery × Efficiency`). Only 3 of the ~6-8 vision dimensions are represented (reliability≈goal success, safety, stability≈drift-derived); no resilience/recovery/efficiency/cost/autonomy dimensions exist. Additive scoring also lacks the "catastrophic weakness can't be hidden" property the vision calls out. |
| `storage/repository.py` | Persists iteration results to disk | `write_results(path, results) -> None` (dataclass→dict via `asdict`, JSON dump with indent) | **Stub.** Single function, JSON file only, no read/query path, no repository abstraction/interface, no database or structured artifact store, no historical run comparison support (needed for drift/fingerprint-over-time). |
| `telemetry/events.py` | Defines the single telemetry unit emitted per run | `RunEvent` (frozen dataclass: `task_id`, `disruption`, `success`, `policy_violations`, `interventions`, `latency_ms`) | **Stub.** Flat, single-step event — no trajectory (no state/action/tool-call/tool-response/recovery/final-state sequence), no per-step timeline, no multi-agent or tool-level fields. |
| `api/app.py` | Exposes the reliability loop over HTTP | FastAPI `app`; `RunRequest` (pydantic model, `iterations: int` 1-200); `GET /health`; `POST /run` (calls `run_reliability_loop`, returns counts + raw `__dict__` results) | **Minimal working prototype.** Two endpoints only; no scenario/config endpoints, no historical query, no auth, uses `item.__dict__` directly (works because dataclasses expose `__dict__`, but bypasses `pydantic` response models — inconsistent with the `pydantic` dependency already present). |
| `main.py` | CLI entry point | Typer `app`; `run-loop` command (`iterations` option 1-1000); `main()` wrapper mapping exceptions/`KeyboardInterrupt` to exit codes (0/1/130) | **Minimal working prototype.** Single command; writes to a fixed `latest-run.json` path (overwrites prior runs, no run history/versioning); solid exit-code handling for a CLI stub. |
| `config.py` | Centralized settings from environment variables | `Settings` (frozen dataclass with `os.getenv`-derived defaults for env/backend/thresholds/output_dir); `load_settings()` (instantiates + ensures output dir exists) | **Minimal working prototype.** Straightforward and correctly typed, but does not read `configs/experiment.yaml` at all — the YAML config file and env-var config are two disconnected mechanisms describing overlapping concepts (thresholds), which is a latent inconsistency. |
| `__init__.py` (package root) | Package export surface | `__version__ = "0.1.0"` | **Stub.** |
| Tests (`tests/test_runner.py`, `tests/test_trust.py`) | Unit tests | 2 tests for `run_reliability_loop` (count matches iterations; disruption names are a subset of known set); 2 tests for `score_trust` (healthy event → trustworthy; failed/high-drift event → untrustworthy) | **Minimal but present**, follow Arrange/Act/Assert commenting convention. No tests for `chaos/injector.py`, `drift/detector.py` directly, `storage/repository.py`, `api/app.py`, or `main.py` CLI behavior. No coverage config wired into CI (no CI workflow files exist in the repo at all — confirmed no `.github/workflows` present in the file search results). |

### Overall Architecture Realized vs. Documented

The actual code implements a **single linear pipeline** matching `docs/architecture.md`'s 5-layer description:

```
CLI/API → run_reliability_loop → (_simulate_event, pure RNG)
                                → detect_drift(event, threshold)
                                → score_trust(event, drift, threshold)
                                → write_results(JSON)
```

There is no branching into 7 planes, no scenario objects, no agent execution against a real or simulated environment (the "agent" is entirely simulated by `random.random()`/`random.uniform()` calls inside `_simulate_event`), and no persistence of historical runs for trend/fingerprint comparison.

## Gaps vs. Full ARISE-X Vision (7-Plane Architecture)

| Vision element | Current scaffold state | Gap |
|---|---|---|
| **1. Scenario Plane** — scenarios with business objective, initial state, tools, knowledge, constraints, expected outcome, allowed strategies, forbidden behaviors, injection points, recovery opportunities, success criteria | `configs/experiment.yaml` only names an experiment + horizons + disruption list + 2 thresholds. No `Scenario` type/dataclass anywhere in `src/`. | **Not implemented.** No structured scenario model at all; nothing captures objectives, constraints, or forbidden behaviors. |
| **2. Agent Execution Plane** — real Agent/Multi-Agent/Tools/RAG/Memory execution | `agents/base.py` defines only a `Protocol` (`AgentUnderTest`) and response shape; no concrete agent, no tool-calling loop, no memory/RAG integration, no multi-agent support. | **Interface stub only.** The evaluation runner does not call any `AgentUnderTest` implementation — it fabricates outcomes via RNG, so the "agent" is not actually executed. |
| **3. Chaos Plane** — 6-level taxonomy (Infrastructure, Tool, Data, Agent, Multi-Agent, Model) | `chaos/injector.py` has 3 flat profiles (`baseline`, `latency_spike`, `tool_degradation`) with 2 numeric knobs each (`failure_boost`, `latency_multiplier`). No level/category taxonomy, no data/agent/multi-agent/model fault types, no tool-schema corruption, no memory corruption, no cascading/agent-disagreement faults. | **~1 of 6 levels partially represented** (crude Infrastructure/Tool-style latency & failure boost only). No taxonomy structure, no per-level fault catalog. |
| **4. Telemetry Plane** — full trajectory capture (state/action/tool-call/tool-response/recovery/final-state per step) | `telemetry/events.py` has one flat `RunEvent` per run with 6 scalar fields (no step sequence). | **Not implemented.** No trajectory/step model; only a single aggregate event per iteration, so there is nothing resembling "State 0 → Action 1 → Tool call → ... → Final state." |
| **5. Intelligence Plane** — behavioral fingerprinting, drift detection, failure classification, RCA | `drift/detector.py` computes a single-event heuristic score (not a fingerprint) with no historical baseline comparison, no failure-mode classification, no root-cause analysis. | **Minimal heuristic only.** No fingerprint vector (tool-selection distribution, avg steps, recovery rate, escalation rate, goal deviation, cost/task as in the vision's example), no comparison across time/versions, no RCA. |
| **6. Reliability Plane** — Agent Reliability Vector (GoalSuccess, Resilience, BehavioralStability, Recovery, Safety, Efficiency, Cost, Autonomy) and **multiplicative** ARI | `trust/scorer.py` computes an **additive weighted sum** of 3 proxies (reliability=success flag, safety=1 - violations*0.1, stability=1 - drift score). | **Wrong aggregation model + missing dimensions.** No resilience, recovery, efficiency, cost, or autonomy dimensions; the additive formula does not have the vision's "catastrophic weakness can't be hidden" multiplicative property; no reliability vector object at all. |
| **7. CI/CD + Production Plane** — regression gates comparing ARI across versions, blocked-deploy reasoning, production feedback loop (unexpected trajectory → failure classification → new benchmark scenario → regression → redeploy) | No CI/CD workflow files found anywhere in the repo (no `.github/workflows/`). No version-to-version ARI comparison logic. No production telemetry ingestion path. | **Not implemented at all.** Nothing in the scaffold compares two runs/versions, gates a deploy, or closes the production feedback loop. |
| **Long-Horizon Engine** — trajectory-level metrics (Goal Achievement, Path Efficiency, Recovery Efficiency, Planning Stability, Goal Preservation, Tool Efficiency, State Consistency, Cost Efficiency) | `run_reliability_loop` is a loop of N *independent* iterations (default disruption rotation of 3), each producing one scalar `IterationResult`. `configs/experiment.yaml` declares `horizons: [24h, 7d]` but no code reads or simulates a time horizon. | **Not implemented.** "Long-horizon" is asserted in config/docs only; the runner has no multi-step task concept, no horizon parameter, no per-step trajectory metrics. |
| **5 IP metrics** (ARS, ARS-R/Resilience, BSI, AES, MACS) | None of these named metrics exist as distinct computations; only the blended `trust_score`/`drift_score` exist. | **Not implemented** as separate named/reusable metrics. |
| **Config/experiment file usage** | `configs/experiment.yaml` is unread by any Python code — a structural disconnect between declared experiment config and actual runtime settings (`config.py` env vars). | **Latent gap/inconsistency**, not vision-scale but worth flagging for continuity work. |

## Conventions Worth Preserving

* **Package name**: `arise_x` (import name) / `arise-x` (PyPI/project name) — snake_case internal package, kebab-case distribution name; CLI script name also `arise-x`.
* **src-layout**: `src/arise_x/...` with `pythonpath = ["src"]` in `[tool.pytest.ini_options]` — keep this layout for any new modules.
* **CLI**: `typer` for `main.py`, `app = typer.Typer(add_completion=False, no_args_is_help=True)`, commands registered via `@app.command("name")`, explicit `EXIT_SUCCESS`/`EXIT_FAILURE` constants and a `main() -> int` wrapper with `sys.exit(main())`.
* **API**: `FastAPI` + `pydantic` `BaseModel` request models in `api/app.py`; simple `/health` and verb-based routes (`/run`).
* **Domain models**: `@dataclass(frozen=True)` used consistently across `agents`, `chaos`, `drift`, `evaluation`, `telemetry`, `trust` for immutable value objects — no ORM/pydantic models used for internal domain types (pydantic is reserved for the API boundary only). This dataclass-first convention should be preserved for new domain types (e.g., future `Scenario`, `Trajectory`, `FingerprintVector`, `ReliabilityVector`).
* **Config pattern**: single `Settings` frozen dataclass in `config.py` sourced from `os.getenv(...)` with a `load_settings()` factory that also ensures side effects (creating `output_dir`). Any new settings should extend this dataclass rather than introducing a second config mechanism (and ideally reconcile with `configs/experiment.yaml`, which is currently unused).
* **Testing**: `pytest`, test files under `tests/`, `test_given_<condition>_when_<action>_then_<expected>` naming style, explicit `# Arrange` / `# Act` / `# Assert` comments, `from __future__ import annotations` in every module.
* **Lint**: `ruff` with `select = ["E", "F", "I", "UP", "B"]`, 100-char line length, `py311` target — keep this baseline and extend rule sets deliberately rather than replacing.
* **Dependency management**: `uv` + `pyproject.toml` is the documented workflow (`uv init`, `uv add ...`, `uv sync`, `uv run ...`) even though the `[build-system]` still uses `setuptools`/`wheel` rather than `uv_build`/`hatchling` — worth noting as a minor inconsistency if migrating fully to `uv`'s native build backend later.
* **Docs style**: Markdown files use a YAML frontmatter block (`title`, `description`, `author`, `ms.date`, `ms.topic`, `keywords`, `estimated_reading_time`) in `README.md` and `docs/architecture.md` — follow this pattern for new docs.
* **Env vars**: `ARISE_*` prefix (`ARISE_ENV`, `ARISE_TELEMETRY_BACKEND`, `ARISE_TRUST_THRESHOLD`, `ARISE_DRIFT_THRESHOLD`, `ARISE_OUTPUT_DIR`) documented in `.env.example` — extend with the same prefix for new settings.
* **MVE/tracking structure**: `.copilot-tracking/mve/{date}/{slug}/` with the 5 canonical phase files (`context.md`, `hypotheses.md`, `vetting.md`, `experiment-design.md`, `mve-plan.md`) — this is a process artifact convention (HVE-Core MVE skill), separate from source code conventions, and should be preserved if further MVE cycles are run for this project.

## Follow-on Questions (Not Yet Answered by Local Research)

* Which single representative agent workflow will Week 1 of the MVE plan target (the MVE plan says "one representative autonomous agent workflow" but does not name it — `context.md`'s "Next Context Questions" still asks this)?
* Should `configs/experiment.yaml` become the single source of truth (loaded by `config.py`/`main.py`) instead of the current disconnected env-var-only settings, or is the YAML file intended as documentation/future-use only?
* Is the `setuptools` build backend intentional, or should the project migrate to `uv_build`/`hatchling` given the `uv`-centric Quick Start?
* No CI workflow exists yet — is CI/CD gating (Plane 7) planned for a later MVE cycle, and if so, against which git hosting (GitHub Actions implied by `.copilot-tracking/mve` conventions, but not confirmed for this repo)?

## Clarifying Questions for the User

* None required to complete this specific file-analysis task — all requested files were locally readable and sufficient to answer the assigned inventory/gap-analysis questions. The four "Follow-on Questions" above are recommended as inputs to a subsequent planning phase, not blockers for this research task.
