"""HTTP contract tests for the ARISE-X FastAPI application."""

from __future__ import annotations

import importlib
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from arise_x.api.app import app
from arise_x.config import load_settings
from arise_x.evaluation.runner import IterationResult
from arise_x.main import app as cli_app
from arise_x.scenarios import SuitePartition, SuiteTask
from arise_x.storage.repository import RunRepository
from arise_x.telemetry.trajectory import Outcome, Step, Trajectory
from arise_x.trust.vector import DimensionScore, ReliabilityVector, VectorDimension

client = TestClient(app)


def test_given_health_endpoint_when_get_then_returns_status_ok() -> None:
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_given_default_when_post_run_then_legacy_keys_present(tmp_path, monkeypatch) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    response = client.post("/run", json={})

    # Assert
    body = response.json()
    assert response.status_code == 200
    assert body["iterations"] == 3
    assert "trustworthy_count" in body
    assert "results" in body
    assert len(body["results"]) == 3


def test_given_explicit_scenario_and_seed_when_post_run_then_returns_run_metadata(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    payload = {"iterations": 2, "scenario": "procurement-baseline", "seed": 7}

    # Act
    response = client.post("/run", json=payload)

    # Assert
    body = response.json()
    assert response.status_code == 200
    assert body["iterations"] == 2
    assert body["seed"] == 7
    assert "run_id" in body
    assert "scenario_version" in body
    assert "config_fingerprint" in body
    assert "agent_version" in body


def test_given_same_seed_when_run_twice_then_results_match(tmp_path, monkeypatch) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    payload = {"iterations": 3, "seed": 42}

    # Act
    first = client.post("/run", json=payload).json()
    second = client.post("/run", json=payload).json()

    # Assert
    assert first["results"] == second["results"]


def test_given_default_when_post_run_then_reliability_vectors_are_bounded_per_task(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    response = client.post("/run", json={"iterations": 2})

    # Assert
    body = response.json()
    assert response.status_code == 200
    assert len(body["reliability_vectors"]) == 2
    goal_success = body["reliability_vectors"][0]["goal_success"]
    assert set(goal_success) == {"value", "available"}


def test_given_persisted_run_when_get_run_then_returns_trajectory_and_vector_detail(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    run_id = client.post("/run", json={"iterations": 1}).json()["run_id"]

    # Act
    response = client.get(f"/runs/{run_id}")

    # Assert
    body = response.json()
    assert response.status_code == 200
    assert body["run_id"] == run_id
    assert len(body["trajectories"]) == 1
    assert len(body["vectors"]) == 1


def test_given_unknown_run_id_when_get_run_then_returns_404(tmp_path, monkeypatch) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    response = client.get("/runs/does-not-exist")

    # Assert
    assert response.status_code == 404


@pytest.fixture()
def gate_runs(tmp_path, monkeypatch):
    """Persist structurally valid evidence through the repaired repository, not a read mock."""
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path))
    settings = load_settings()
    tasks = tuple(SuiteTask(f"held-{i}", "procurement", f"cluster-{i % 2}") for i in range(20))
    suite = replace(settings.evaluation_suite, partitions=(
        settings.evaluation_suite.partition("development"),
        SuitePartition("held_out", "test", tasks),
    ))
    settings = replace(settings, evaluation_suite=suite)
    monkeypatch.setattr(
        importlib.import_module("arise_x.api.app"), "load_settings", lambda: settings
    )
    monkeypatch.setattr(importlib.import_module("arise_x.main"), "load_settings", lambda: settings)
    repository = RunRepository(tmp_path)

    def persist(run_id, change=None):
        trajectories = []
        vectors = []
        results = []
        for i, task in enumerate(tasks):
            trajectory = Trajectory(
                run_id=run_id, task_id=task.task_id, family=task.family, cluster_id=task.cluster,
                suite_id=suite.suite_id, suite_version=suite.version, suite_partition="held_out",
                repeat_id="seed-7", scenario_name=settings.scenario.name, scenario_version=1,
                agent_id="fixture", agent_version="v1",
                steps=(Step(index=0, action="decide", state_transition="done",
                            prompt_text="PRIVATE-GATE-SENTINEL"),),
                outcome=Outcome(goal_achieved=True, label="done"),
            )
            if change in {"task_id", "repeat_id", "cluster_id", "suite_id", "scenario_name"}:
                trajectory = replace(trajectory, **{change: f"other-{i}"})
            elif change in {"suite_version", "scenario_version"}:
                trajectory = replace(trajectory, **{change: 2})
            elif change == "mixed" and i == 0:
                trajectory = replace(trajectory, suite_partition="development")
            elif change == "development":
                trajectory = replace(trajectory, suite_partition="development")
            scores = {dim.value: DimensionScore(dim, 1.0, True, 1) for dim in VectorDimension}
            if change == "regression":
                scores["goal_success"] = DimensionScore(VectorDimension.GOAL_SUCCESS, 0.0, True, 1)
            elif change == "binary":
                scores["goal_success"] = DimensionScore(VectorDimension.GOAL_SUCCESS, 0.7, True, 1)
            elif change == "unavailable":
                scores["efficiency"] = DimensionScore.unavailable(VectorDimension.EFFICIENCY)
            trajectories.append(trajectory)
            vectors.append(ReliabilityVector(**scores))
            results.append(IterationResult(trajectory.task_id, "baseline", 0.0, 1.0, True))
        repository.write_run(
            results, run_id=run_id, seed=8 if change == "seed" else 7,
            trajectories=trajectories, vectors=vectors,
        )
        if change in {"schema", "normalization", "corrupt"}:
            path = tmp_path / f"{run_id}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            if change == "schema":
                payload["metadata"]["schema_version"] = 99
            elif change == "normalization":
                payload["vectors"][0]["safety"]["normalization_version"] = "v99"
            else:
                payload["trajectories"][0]["run_id"] = "wrong-envelope"
            path.write_text(json.dumps(payload), encoding="utf-8")

    persist("baseline")
    return persist


@pytest.mark.parametrize("change", [None, "regression", "unavailable"])
def test_given_valid_evidence_without_budget_when_http_gate_then_blocks(gate_runs, change) -> None:
    # Arrange
    gate_runs("candidate", change)

    # Act
    response = client.post(
        "/gate", json={"baseline_run_id": "baseline", "candidate_run_id": "candidate"}
    )

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "block"
    assert body["error_budget"] is None
    assert body["error_budget_reasons"]
    assert "PRIVATE-GATE-SENTINEL" not in response.text
    assert "prompt_text" not in response.text
    if change == "regression":
        assert any("critical regression" in reason for reason in body["critical_override_reasons"])


@pytest.mark.parametrize("change", [
    "task_id", "repeat_id", "cluster_id", "suite_id", "suite_version", "scenario_name",
    "scenario_version", "seed", "mixed", "development", "binary", "schema",
    "normalization", "corrupt",
])
def test_given_invalid_evidence_when_http_gate_then_returns_422(gate_runs, change) -> None:
    # Arrange
    gate_runs("candidate", change)

    # Act
    response = client.post(
        "/gate", json={"baseline_run_id": "baseline", "candidate_run_id": "candidate"}
    )

    # Assert
    assert response.status_code == 422
    assert "PRIVATE-GATE-SENTINEL" not in response.text


@pytest.mark.parametrize(("change", "expected"), [
    (None, 1), ("regression", 1), ("task_id", 2), ("seed", 2), ("mixed", 2),
    ("binary", 2), ("schema", 2), ("normalization", 2), ("corrupt", 2),
])
def test_given_gate_evidence_when_cli_then_stable_exit(gate_runs, change, expected) -> None:
    # Arrange
    gate_runs("candidate", change)

    # Act
    result = CliRunner().invoke(cli_app, [
        "gate", "--baseline-run-id", "baseline", "--candidate-run-id", "candidate",
    ])

    # Assert
    assert result.exit_code == expected, result.output
    if expected == 1:
        assert "Verdict: block" in result.output
        assert "production" in result.output.lower()


def test_given_unknown_run_when_http_gate_then_returns_404(tmp_path, monkeypatch) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path))

    # Act
    response = client.post(
        "/gate", json={"baseline_run_id": "missing", "candidate_run_id": "missing"}
    )

    # Assert
    assert response.status_code == 404


def test_given_invalid_environment_when_gate_transports_then_configuration_error(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("ARISE_TRUST_THRESHOLD", "invalid")

    # Act
    response = client.post(
        "/gate", json={"baseline_run_id": "missing", "candidate_run_id": "missing"}
    )
    cli = CliRunner().invoke(cli_app, [
        "gate", "--baseline-run-id", "missing", "--candidate-run-id", "missing",
    ])

    # Assert
    assert response.status_code == 422
    assert cli.exit_code == 2


@pytest.mark.parametrize("issue", ["missing-seed", "outside-manifest", "wrong-scenario", "expired"])
def test_given_matching_but_invalid_release_records_when_http_gate_then_rejected(
    gate_runs, tmp_path, monkeypatch, issue
) -> None:
    # Arrange: both runs match one another, but not the release boundary requirements.
    gate_runs("candidate")
    for run_id in ("baseline", "candidate"):
        path = tmp_path / f"{run_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if issue == "missing-seed":
            payload["metadata"]["seed"] = None
        elif issue == "outside-manifest":
            payload["trajectories"][0]["task_id"] = "unknown-task"
            payload["results"][0]["task_id"] = "unknown-task"
        elif issue == "wrong-scenario":
            for trajectory in payload["trajectories"]:
                trajectory["scenario_name"] = "other-scenario"
        path.write_text(json.dumps(payload), encoding="utf-8")
    if issue == "expired":
        module = importlib.import_module("arise_x.api.app")
        settings = module.load_settings()
        settings = replace(settings, evaluation_suite=replace(
            settings.evaluation_suite, rotation_deadline="2000-01-01"
        ))
        monkeypatch.setattr(module, "load_settings", lambda: settings)

    # Act
    response = client.post(
        "/gate", json={"baseline_run_id": "baseline", "candidate_run_id": "candidate"}
    )

    # Assert
    assert response.status_code == 422


def test_given_manifest_configuration_error_when_gate_transports_then_stable_error(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    from arise_x.config import ConfigurationError

    def invalid_settings():
        raise ConfigurationError("PRIVATE-GATE-SENTINEL")

    monkeypatch.setattr(
        importlib.import_module("arise_x.api.app"), "load_settings", invalid_settings
    )
    monkeypatch.setattr(importlib.import_module("arise_x.main"), "load_settings", invalid_settings)

    # Act
    response = client.post(
        "/gate", json={"baseline_run_id": "missing", "candidate_run_id": "missing"}
    )
    cli = CliRunner().invoke(cli_app, [
        "gate", "--baseline-run-id", "missing", "--candidate-run-id", "missing",
    ])

    # Assert
    assert response.status_code == 422
    assert cli.exit_code == 2
    assert "PRIVATE-GATE-SENTINEL" not in response.text + cli.output
