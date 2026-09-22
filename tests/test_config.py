"""Unit tests for ARISE-X scenario and evaluation-suite configuration loading."""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import pytest

from arise_x.config import ConfigurationError, load_settings
from arise_x.scenarios import ScenarioValidationError

_HELD_OUT_PAYLOAD = b"protected procurement task"
_HELD_OUT_FINGERPRINT = f"sha256:{hashlib.sha256(_HELD_OUT_PAYLOAD).hexdigest()}"
_DEVELOPMENT_TASK_YAML = (
    "{task_id: procurement-dev-001, family: procurement, "
    "cluster: vendor-comparison, seed: 101}"
)
_HELD_OUT_TASK_YAML = (
    "{task_id: procurement-held-001, family: procurement, "
    "cluster: vendor-comparison, seed: 201, "
    f'fingerprint: "{_HELD_OUT_FINGERPRINT}"}}'
)

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

_VALID_SUITE_YAML = f"""\
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
            tasks: [{_DEVELOPMENT_TASK_YAML}]
        held_out:
            description: Protected tasks.
            tasks: [{_HELD_OUT_TASK_YAML}]
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
    assert field_names == {"task_id", "family", "cluster", "fingerprint", "seed"}


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


def test_given_legacy_experiment_root_when_load_settings_then_remains_compatible(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_yaml = _VALID_EXPERIMENT_YAML.replace("scenario:\n", "experiment:\n", 1)
    experiment_path, suite_path = _write_manifests(tmp_path, experiment_yaml=experiment_yaml)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    settings = load_settings(experiment_path, suite_path)

    # Assert
    assert settings.scenario.name == "procurement-baseline"


def test_given_unknown_disruption_when_load_settings_then_rejects_reference(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_yaml = _VALID_EXPERIMENT_YAML.replace("    - latency_spike", "    - unknown-fault")
    experiment_path, suite_path = _write_manifests(tmp_path, experiment_yaml=experiment_yaml)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act & Assert
    with pytest.raises(ConfigurationError, match="unknown-fault"):
        load_settings(experiment_path, suite_path)


def test_given_structured_disruption_when_load_settings_then_resolves_catalog_fault(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_yaml = _VALID_EXPERIMENT_YAML.replace(
        "    - latency_spike", "    - name: slow-upstream\n      fault_id: latency_spike"
    )
    experiment_path, suite_path = _write_manifests(tmp_path, experiment_yaml=experiment_yaml)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act
    settings = load_settings(experiment_path, suite_path)

    # Assert
    assert settings.scenario.disruptions[1].resolved_fault_id == "latency_spike"


@pytest.mark.parametrize("value", ["invalid", "nan", "1.1", "-0.1"])
def test_given_invalid_environment_threshold_when_load_settings_then_error_is_actionable(
    tmp_path, monkeypatch, value
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ARISE_TRUST_THRESHOLD", value)

    # Act & Assert
    with pytest.raises(ConfigurationError, match="ARISE_TRUST_THRESHOLD"):
        load_settings(experiment_path, suite_path)


@pytest.mark.parametrize(
    ("suite_yaml", "message"),
    [
        (
            _VALID_SUITE_YAML.replace("procurement-held-001", "procurement-dev-001"),
            "unique",
        ),
        (
            _VALID_SUITE_YAML.replace("cluster: vendor-comparison", "cluster: unknown", 1),
            "unknown cluster",
        ),
        (_VALID_SUITE_YAML.replace("seed: 101", "seed: -1"), "seed"),
        (_VALID_SUITE_YAML.replace("held_out:", "validation:"), "partition"),
        (
            _VALID_SUITE_YAML.replace(_HELD_OUT_FINGERPRINT, "sha256:short"),
            "fingerprint",
        ),
    ],
)
def test_given_invalid_suite_governance_when_load_settings_then_rejects_manifest(
    tmp_path, monkeypatch, suite_yaml, message
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path, suite_yaml=suite_yaml)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))

    # Act & Assert
    with pytest.raises(ConfigurationError, match=message):
        load_settings(experiment_path, suite_path)


def test_given_held_out_task_when_resolving_then_injected_resolver_is_verified(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    suite = load_settings(experiment_path, suite_path).evaluation_suite

    class Resolver:
        def __init__(self) -> None:
            self.calls = []

        def resolve(self, locator, task):
            self.calls.append((locator, task.task_id))
            return _HELD_OUT_PAYLOAD

    resolver = Resolver()

    # Act
    payload = suite.resolve_held_out_payload("procurement-held-001", resolver)

    # Assert
    assert payload == _HELD_OUT_PAYLOAD
    assert resolver.calls == [
        ("configs/protected/procurement-baseline-suite/held_out/", "procurement-held-001")
    ]


def test_given_non_held_out_task_when_resolving_then_rejects_without_calling_resolver(
    tmp_path, monkeypatch
) -> None:
    # Arrange
    experiment_path, suite_path = _write_manifests(tmp_path)
    monkeypatch.setenv("ARISE_OUTPUT_DIR", str(tmp_path / "artifacts"))
    suite = load_settings(experiment_path, suite_path).evaluation_suite

    class Resolver:
        def resolve(self, locator, task):
            raise AssertionError("resolver must not be called")

    # Act & Assert
    with pytest.raises(ScenarioValidationError, match="held_out"):
        suite.resolve_held_out_payload("procurement-dev-001", Resolver())
