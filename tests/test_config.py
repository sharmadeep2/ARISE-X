"""Unit tests for ARISE-X scenario and evaluation-suite configuration loading."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from arise_x.config import ConfigurationError, load_settings

_VALID_EXPERIMENT_YAML = """\
scenario:
  name: procurement-baseline
  version: 1
  objective: "Purchase 500 laptops within budget and ensure delivery before September 15."
  constraints:
    - "Total spend must not exceed the approved budget."
  expected_outcome: "Purchase order created and shipment confirmed within budget and schedule."
  seed: 20260825
  horizons:
    - 24h
    - 7d
  disruptions:
    - baseline
    - latency_spike
  thresholds:
    trust: 0.75
    drift: 0.30
  suite_ref:
    suite_id: procurement-baseline-suite
    version: 1
  cluster_refs:
    - cluster_id: vendor-comparison
      family: procurement
"""

_VALID_SUITE_YAML = """\
suite:
  suite_id: procurement-baseline-suite
  version: 1
  owner: arise-x-eval-team
  rotation_deadline: "2099-12-31"
  access_policy: restricted-eval-team-only
  protected_payload_locator: "configs/protected/procurement-baseline-suite/held_out/"
  partitions:
    development:
      description: Tuning-visible tasks.
      tasks:
        - task_id: procurement-dev-001
          family: procurement
          cluster: vendor-comparison
    held_out:
      description: Protected tasks.
      tasks:
        - task_id: procurement-held-001
          family: procurement
          cluster: vendor-comparison
          fingerprint: "sha256:deadbeef"
"""


def _write_manifests(
    tmp_path: Path,
    experiment_yaml: str = _VALID_EXPERIMENT_YAML,
    suite_yaml: str = _VALID_SUITE_YAML,
) -> tuple[Path, Path]:
    """Write experiment and suite manifests under tmp_path and return their paths."""

    experiment_path = tmp_path / "experiment.yaml"
    suite_path = tmp_path / "evaluation-suite.yaml"
    experiment_path.write_text(experiment_yaml, encoding="utf-8")
    suite_path.write_text(suite_yaml, encoding="utf-8")
    return experiment_path, suite_path


def test_given_valid_manifests_when_load_settings_then_returns_populated_settings(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    settings = load_settings(experiment_path, suite_path)

    # Assert
    assert settings.scenario.name == "procurement-baseline"
    assert settings.evaluation_suite.suite_id == "procurement-baseline-suite"


def test_given_env_override_when_load_settings_then_env_takes_precedence(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ARISE_TRUST_THRESHOLD", "0.9")

    # Act
    settings = load_settings(experiment_path, suite_path)

    # Assert
    assert settings.trust_threshold == pytest.approx(0.9)


def test_given_malformed_yaml_when_load_settings_then_raises_configuration_error(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path = tmp_path / "experiment.yaml"
    suite_path = tmp_path / "evaluation-suite.yaml"
    experiment_path.write_text("scenario: [unclosed", encoding="utf-8")
    suite_path.write_text(_VALID_SUITE_YAML, encoding="utf-8")
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act & Assert
    with pytest.raises(ConfigurationError, match="malformed YAML"):
        load_settings(experiment_path, suite_path)


def test_given_threshold_out_of_range_when_load_settings_then_raises_configuration_error(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    invalid_experiment_yaml = _VALID_EXPERIMENT_YAML.replace("trust: 0.75", "trust: 1.5")
    experiment_path, suite_path = _write_manifests(
        tmp_path, experiment_yaml=invalid_experiment_yaml
    )
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act & Assert
    with pytest.raises(ConfigurationError, match="Threshold"):
        load_settings(experiment_path, suite_path)


def test_given_unknown_suite_reference_when_load_settings_then_raises_configuration_error(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    mismatched_experiment_yaml = _VALID_EXPERIMENT_YAML.replace(
        "suite_id: procurement-baseline-suite", "suite_id: unknown-suite"
    )
    experiment_path, suite_path = _write_manifests(
        tmp_path, experiment_yaml=mismatched_experiment_yaml
    )
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act & Assert
    with pytest.raises(ConfigurationError, match="unknown-suite"):
        load_settings(experiment_path, suite_path)


def test_given_valid_manifests_when_load_settings_twice_then_seed_is_deterministic(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    first = load_settings(experiment_path, suite_path)
    second = load_settings(experiment_path, suite_path)

    # Assert
    assert first.scenario.seed == second.scenario.seed == 20260825


def test_given_valid_manifests_when_load_settings_then_suite_partitions_are_accessible(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    settings = load_settings(experiment_path, suite_path)

    # Assert
    development = settings.evaluation_suite.partition("development")
    held_out = settings.evaluation_suite.partition("held_out")
    assert development.tasks[0].task_id == "procurement-dev-001"
    assert held_out.tasks[0].task_id == "procurement-held-001"


def test_given_held_out_partition_when_load_settings_then_only_identifiers_are_exposed(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    settings = load_settings(experiment_path, suite_path)
    held_out_task = settings.evaluation_suite.partition("held_out").tasks[0]

    # Assert
    field_names = {held_field.name for held_field in dataclasses.fields(held_out_task)}
    assert field_names == {"task_id", "family", "cluster", "fingerprint"}


def test_given_expired_rotation_deadline_when_load_settings_then_raises_configuration_error(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    expired_suite_yaml = _VALID_SUITE_YAML.replace(
        'rotation_deadline: "2099-12-31"', 'rotation_deadline: "2020-01-01"'
    )
    experiment_path, suite_path = _write_manifests(tmp_path, suite_yaml=expired_suite_yaml)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act & Assert
    with pytest.raises(ConfigurationError, match="rotation deadline"):
        load_settings(experiment_path, suite_path)
