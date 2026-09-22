"""Centralized runtime configuration for ARISE-X."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from arise_x.drift.statistics import DEFAULT_ALPHA, DEFAULT_TARGET_POWER, DimensionTestConfig
from arise_x.scenarios import (
    DisruptionReference,
    EvaluationSuite,
    Horizon,
    Scenario,
    ScenarioValidationError,
    SuitePartition,
    SuiteReference,
    SuiteTask,
    TaskCluster,
    Threshold,
)
from arise_x.trust.gate import GatePolicyConfig
from arise_x.trust.vector import VectorDimension

DEFAULT_EXPERIMENT_PATH = Path("configs/experiment.yaml")
DEFAULT_SUITE_PATH = Path("configs/evaluation-suite.yaml")
_DEFAULT_GATE_SLO_TARGET = 0.95


class ConfigurationError(Exception):
    """Raised when configuration manifests are missing, malformed, or incompatible."""


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables and, optionally, scenario manifests."""  # noqa: E501

    environment: str = field(default_factory=lambda: os.getenv("ARISE_ENV", "local"))
    telemetry_backend: str = field(
        default_factory=lambda: os.getenv("ARISE_TELEMETRY_BACKEND", "file")
    )
    trust_threshold: float = field(
        default_factory=lambda: float(os.getenv("ARISE_TRUST_THRESHOLD", "0.75"))
    )
    drift_threshold: float = field(
        default_factory=lambda: float(os.getenv("ARISE_DRIFT_THRESHOLD", "0.30"))
    )
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("ARISE_OUTPUT_DIR", "artifacts"))
    )
    scenario: Scenario | None = None
    evaluation_suite: EvaluationSuite | None = None
    gate_policy: GatePolicyConfig | None = None


def _read_yaml_mapping(path: Path) -> dict:
    """Read and parse a YAML file into a mapping, raising ConfigurationError on failure."""

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Unable to read configuration file '{path}': {exc}") from exc

    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Configuration file '{path}' contains malformed YAML: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise ConfigurationError(f"Configuration file '{path}' must contain a top-level mapping.")

    return document


def _parse_scenario(document: dict, path: Path) -> Scenario:
    """Build a Scenario from a parsed experiment manifest."""

    try:
        body = document["scenario"]
        suite_ref_body = body["suite_ref"]
        return Scenario(
            name=body["name"],
            version=int(body["version"]),
            objective=body["objective"],
            constraints=tuple(body.get("constraints", [])),
            expected_outcome=body["expected_outcome"],
            seed=int(body["seed"]),
            horizons=tuple(Horizon(label=value) for value in body["horizons"]),
            disruptions=tuple(DisruptionReference(name=value) for value in body["disruptions"]),
            thresholds=tuple(
                Threshold(name=name, value=float(value))
                for name, value in body["thresholds"].items()
            ),
            suite_ref=SuiteReference(
                suite_id=suite_ref_body["suite_id"], version=int(suite_ref_body["version"])
            ),
            cluster_refs=tuple(
                TaskCluster(cluster_id=item["cluster_id"], family=item["family"])
                for item in body.get("cluster_refs", [])
            ),
        )
    except KeyError as exc:
        raise ConfigurationError(
            f"Experiment manifest '{path}' is missing required field {exc}."
        ) from exc
    except ScenarioValidationError as exc:
        raise ConfigurationError(f"Experiment manifest '{path}' is invalid: {exc}") from exc


def _parse_suite_task(body: dict) -> SuiteTask:
    """Build a SuiteTask from a parsed task entry."""

    return SuiteTask(
        task_id=body["task_id"],
        family=body["family"],
        cluster=body["cluster"],
        fingerprint=body.get("fingerprint"),
    )


def _parse_evaluation_suite(document: dict, path: Path) -> EvaluationSuite:
    """Build an EvaluationSuite from a parsed suite manifest."""

    try:
        body = document["suite"]
        partitions = tuple(
            SuitePartition(
                name=name,
                description=partition_body.get("description", ""),
                tasks=tuple(_parse_suite_task(task) for task in partition_body.get("tasks", [])),
            )
            for name, partition_body in body["partitions"].items()
        )
        return EvaluationSuite(
            suite_id=body["suite_id"],
            version=int(body["version"]),
            owner=body["owner"],
            rotation_deadline=body["rotation_deadline"],
            access_policy=body["access_policy"],
            protected_payload_locator=body["protected_payload_locator"],
            partitions=partitions,
        )
    except KeyError as exc:
        raise ConfigurationError(
            f"Evaluation suite manifest '{path}' is missing required field {exc}."
        ) from exc
    except ScenarioValidationError as exc:
        raise ConfigurationError(f"Evaluation suite manifest '{path}' is invalid: {exc}") from exc


def _validate_compatibility(scenario: Scenario, suite: EvaluationSuite, suite_path: Path) -> None:
    """Ensure a scenario references the loaded evaluation suite by ID and version."""

    if scenario.suite_ref.suite_id != suite.suite_id or scenario.suite_ref.version != suite.version:
        raise ConfigurationError(
            f"Scenario '{scenario.name}' references suite "
            f"'{scenario.suite_ref.suite_id}' v{scenario.suite_ref.version}, "
            f"but '{suite_path}' declares '{suite.suite_id}' v{suite.version}."
        )


def _validate_rotation(suite: EvaluationSuite) -> None:
    """Ensure the held-out evaluation suite has not passed its rotation deadline."""

    try:
        deadline = date.fromisoformat(suite.rotation_deadline)
    except ValueError as exc:
        raise ConfigurationError(
            f"Evaluation suite '{suite.suite_id}' rotation_deadline "
            f"'{suite.rotation_deadline}' is not an ISO 8601 date."
        ) from exc

    if date.today() > deadline:
        raise ConfigurationError(
            f"Evaluation suite '{suite.suite_id}' rotation deadline {deadline.isoformat()} "
            f"has passed; rotate the held-out partition before use."
        )


def _parse_gate_policy(document: dict, path: Path) -> GatePolicyConfig | None:
    """Build an optional GatePolicyConfig from an experiment manifest's `gate_policy:` section.

    Returns `None` when the manifest declares no `gate_policy` section at
    all, so manifests written before Step 5.2 keep loading unchanged.
    """

    body = document.get("gate_policy")
    if body is None:
        return None

    try:
        critical_dimensions = tuple(
            VectorDimension(value)
            for value in body.get(
                "critical_dimensions",
                [VectorDimension.GOAL_SUCCESS.value, VectorDimension.SAFETY.value],
            )
        )
        dimension_configs = tuple(
            (
                VectorDimension(name),
                DimensionTestConfig(
                    minimum_detectable_effect=float(dimension_body["minimum_detectable_effect"]),
                    tolerance=float(dimension_body["tolerance"]),
                    is_binary=bool(dimension_body.get("is_binary", False)),
                ),
            )
            for name, dimension_body in body.get("dimensions", {}).items()
        )
        return GatePolicyConfig(
            critical_dimensions=critical_dimensions,
            alpha=float(body.get("alpha", DEFAULT_ALPHA)),
            target_power=float(body.get("target_power", DEFAULT_TARGET_POWER)),
            dimension_configs=dimension_configs,
            slo_target=float(body.get("slo_target", _DEFAULT_GATE_SLO_TARGET)),
            error_budget_window_days=(
                int(body["error_budget_window_days"])
                if "error_budget_window_days" in body
                else None
            ),
            error_budget_window_episode_count=(
                int(body["error_budget_window_episode_count"])
                if "error_budget_window_episode_count" in body
                else None
            ),
        )
    except (KeyError, ValueError) as exc:
        raise ConfigurationError(
            f"Experiment manifest '{path}' has an invalid gate_policy section: {exc}"
        ) from exc


def load_settings(
    experiment_path: Path | str = DEFAULT_EXPERIMENT_PATH,
    suite_path: Path | str = DEFAULT_SUITE_PATH,
) -> Settings:
    """Load scenario/suite manifests, apply environment overrides, and ensure output dir exists."""

    experiment_path = Path(experiment_path)
    suite_path = Path(suite_path)

    experiment_document = _read_yaml_mapping(experiment_path)
    scenario = _parse_scenario(experiment_document, experiment_path)
    evaluation_suite = _parse_evaluation_suite(_read_yaml_mapping(suite_path), suite_path)
    gate_policy = _parse_gate_policy(experiment_document, experiment_path)

    _validate_compatibility(scenario, evaluation_suite, suite_path)
    _validate_rotation(evaluation_suite)

    trust_threshold = float(
        os.getenv("ARISE_TRUST_THRESHOLD", str(scenario.threshold("trust").value))
    )
    drift_threshold = float(
        os.getenv("ARISE_DRIFT_THRESHOLD", str(scenario.threshold("drift").value))
    )
    output_dir = Path(os.getenv("ARISE_OUTPUT_DIR", "artifacts"))
    output_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        environment=os.getenv("ARISE_ENV", "local"),
        telemetry_backend=os.getenv("ARISE_TELEMETRY_BACKEND", "file"),
        trust_threshold=trust_threshold,
        drift_threshold=drift_threshold,
        output_dir=output_dir,
        scenario=scenario,
        evaluation_suite=evaluation_suite,
        gate_policy=gate_policy,
    )
