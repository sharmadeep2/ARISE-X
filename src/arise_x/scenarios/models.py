"""Immutable scenario and evaluation-suite contracts for ARISE-X.

An "experiment" manifest (for example ``configs/experiment.yaml``) parses into
a :class:`Scenario`: a versioned business objective plus the horizons,
disruption references, thresholds, seed, and suite/cluster references needed
to run and gate it. An "evaluation-suite" manifest (for example
``configs/evaluation-suite.yaml``) parses into an :class:`EvaluationSuite`:
a versioned set of development and held-out task partitions.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Protocol

_VALID_HORIZON_SUFFIXES = ("h", "d")
_VALID_PARTITIONS = frozenset({"development", "held_out"})
_SHA256_FINGERPRINT_PATTERN = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


class ScenarioValidationError(ValueError):
    """Raised when a scenario or evaluation-suite definition fails validation."""


@dataclass(frozen=True)
class Horizon:
    """A long-horizon evaluation window, for example ``"24h"`` or ``"7d"``."""

    label: str

    def __post_init__(self) -> None:
        suffix = self.label[-1:] if self.label else ""
        magnitude = self.label[:-1]
        if suffix not in _VALID_HORIZON_SUFFIXES or not magnitude.isdigit() or int(magnitude) <= 0:
            raise ScenarioValidationError(
                f"Horizon '{self.label}' must be a positive number followed by "
                f"'h' (hours) or 'd' (days), for example '24h' or '7d'."
            )


@dataclass(frozen=True)
class Threshold:
    """A named pass/fail threshold bounded to the unit interval."""

    name: str
    value: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ScenarioValidationError("Threshold name must not be empty.")
        if not 0.0 <= self.value <= 1.0:
            raise ScenarioValidationError(
                f"Threshold '{self.name}' must be within [0.0, 1.0], got {self.value}."
            )


@dataclass(frozen=True)
class DisruptionReference:
    """A named reference to a chaos/disruption profile.

    ``name`` preserves the pre-Phase-4 bare-name shape used by existing
    scenario manifests (for example ``configs/experiment.yaml``); it
    resolves through :func:`arise_x.chaos.catalog.resolve_fault` exactly as
    before. ``fault_id`` optionally references a typed catalog fault
    (:mod:`arise_x.chaos.catalog`) directly when a scenario needs to name a
    fault distinct from its bare disruption label; when omitted,
    :attr:`resolved_fault_id` falls back to ``name`` so no existing scenario
    file needs to change.
    """

    name: str
    fault_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ScenarioValidationError("Disruption reference name must not be empty.")
        if self.fault_id is not None and (
            not isinstance(self.fault_id, str) or not self.fault_id
        ):
            raise ScenarioValidationError(
                f"Disruption reference '{self.name}' has an invalid fault_id."
            )

    @property
    def resolved_fault_id(self) -> str:
        """Return the catalog fault_id this reference resolves to."""

        return self.fault_id if self.fault_id is not None else self.name


@dataclass(frozen=True)
class TaskCluster:
    """A task-family cluster identifier used for cluster-aware analysis."""

    cluster_id: str
    family: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.cluster_id, str)
            or not self.cluster_id
            or not isinstance(self.family, str)
            or not self.family
        ):
            raise ScenarioValidationError(
                "Task cluster requires both a non-empty cluster_id and family."
            )


@dataclass(frozen=True)
class SuiteReference:
    """A scenario's reference to a specific evaluation-suite identity and version."""

    suite_id: str
    version: int

    def __post_init__(self) -> None:
        if not self.suite_id:
            raise ScenarioValidationError("Suite reference requires a non-empty suite_id.")
        if self.version <= 0:
            raise ScenarioValidationError(
                f"Suite reference version must be positive, got {self.version}."
            )


@dataclass(frozen=True)
class SuiteTask:
    """A single evaluation task identity within a suite partition.

    Only identifiers, family/cluster attribution, and an optional fingerprint
    are modeled here. Held-out task payload content is intentionally never
    represented so it cannot leak into tuning-visible repository content.
    """

    task_id: str
    family: str
    cluster: str
    fingerprint: str | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value
            for value in (self.task_id, self.family, self.cluster)
        ):
            raise ScenarioValidationError(
                f"Task '{self.task_id}' requires task_id, family, and cluster."
            )
        if self.fingerprint is not None and not _SHA256_FINGERPRINT_PATTERN.fullmatch(
            self.fingerprint
        ):
            raise ScenarioValidationError(
                f"Task '{self.task_id}' fingerprint must use 'sha256:' plus 64 hex characters."
            )
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0
        ):
            raise ScenarioValidationError(
                f"Task '{self.task_id}' seed must be a non-negative integer."
            )


@dataclass(frozen=True)
class SuitePartition:
    """A named partition (``development`` or ``held_out``) of evaluation tasks."""

    name: str
    description: str
    tasks: tuple[SuiteTask, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.name not in _VALID_PARTITIONS:
            raise ScenarioValidationError(
                f"Suite partition name must be one of {sorted(_VALID_PARTITIONS)}, "
                f"got {self.name!r}."
            )


@dataclass(frozen=True)
class Scenario:
    """An immutable, versioned business scenario definition.

    This is the typed shape an experiment manifest (such as
    ``configs/experiment.yaml``) is parsed into.
    """

    name: str
    version: int
    objective: str
    constraints: tuple[str, ...]
    expected_outcome: str
    seed: int
    horizons: tuple[Horizon, ...]
    disruptions: tuple[DisruptionReference, ...]
    thresholds: tuple[Threshold, ...]
    suite_ref: SuiteReference
    cluster_refs: tuple[TaskCluster, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name:
            raise ScenarioValidationError("Scenario name must not be empty.")
        if self.version <= 0:
            raise ScenarioValidationError(f"Scenario version must be positive, got {self.version}.")
        if not self.objective:
            raise ScenarioValidationError("Scenario objective must not be empty.")
        if not self.expected_outcome:
            raise ScenarioValidationError("Scenario expected_outcome must not be empty.")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ScenarioValidationError(
                f"Scenario seed must be a non-negative integer, got {self.seed!r}."
            )
        if not self.horizons:
            raise ScenarioValidationError("Scenario must declare at least one horizon.")
        if not self.disruptions:
            raise ScenarioValidationError(
                "Scenario must declare at least one disruption reference."
            )
        if not self.thresholds:
            raise ScenarioValidationError("Scenario must declare at least one threshold.")
        if len({horizon.label for horizon in self.horizons}) != len(self.horizons):
            raise ScenarioValidationError("Scenario horizon labels must be unique.")
        if len({item.resolved_fault_id for item in self.disruptions}) != len(
            self.disruptions
        ):
            raise ScenarioValidationError("Scenario disruption references must be unique.")
        if len({threshold.name for threshold in self.thresholds}) != len(self.thresholds):
            raise ScenarioValidationError("Scenario threshold names must be unique.")
        if len({cluster.cluster_id for cluster in self.cluster_refs}) != len(
            self.cluster_refs
        ):
            raise ScenarioValidationError("Scenario cluster identifiers must be unique.")

    def threshold(self, name: str) -> Threshold:
        """Return the named threshold, raising if it is not declared."""

        for candidate in self.thresholds:
            if candidate.name == name:
                return candidate
        raise ScenarioValidationError(f"Scenario '{self.name}' has no threshold named '{name}'.")


@dataclass(frozen=True)
class EvaluationSuite:
    """An immutable, versioned evaluation-suite manifest.

    This is the typed shape a suite manifest (such as
    ``configs/evaluation-suite.yaml``) is parsed into.
    """

    suite_id: str
    version: int
    owner: str
    rotation_deadline: str
    access_policy: str
    protected_payload_locator: str
    partitions: tuple[SuitePartition, ...]

    def __post_init__(self) -> None:
        if not self.suite_id:
            raise ScenarioValidationError("Evaluation suite requires a non-empty suite_id.")
        if self.version <= 0:
            raise ScenarioValidationError(
                f"Evaluation suite version must be positive, got {self.version}."
            )
        if not self.owner:
            raise ScenarioValidationError("Evaluation suite requires a non-empty owner.")
        if not self.rotation_deadline:
            raise ScenarioValidationError(
                "Evaluation suite requires a non-empty rotation_deadline."
            )
        if not self.access_policy:
            raise ScenarioValidationError("Evaluation suite requires a non-empty access_policy.")
        if not self.protected_payload_locator:
            raise ScenarioValidationError(
                "Evaluation suite requires a non-empty protected_payload_locator."
            )
        partition_names = [partition.name for partition in self.partitions]
        if set(partition_names) != _VALID_PARTITIONS or len(partition_names) != len(
            _VALID_PARTITIONS
        ):
            raise ScenarioValidationError(
                "Evaluation suite must declare exactly one 'development' and one "
                "'held_out' partition."
            )
        task_ids = [task.task_id for partition in self.partitions for task in partition.tasks]
        if len(set(task_ids)) != len(task_ids):
            raise ScenarioValidationError(
                "Evaluation suite task_id values must be unique across all partitions."
            )

    def partition(self, name: str) -> SuitePartition:
        """Return the named partition, raising if it is not declared."""

        for candidate in self.partitions:
            if candidate.name == name:
                return candidate
        raise ScenarioValidationError(
            f"Evaluation suite '{self.suite_id}' has no partition named '{name}'."
        )

    def resolve_held_out_payload(
        self,
        task_id: str,
        resolver: ProtectedPayloadResolver,
    ) -> bytes:
        """Resolve and verify one protected held-out payload through an injected boundary."""

        task = next(
            (
                candidate
                for candidate in self.partition("held_out").tasks
                if candidate.task_id == task_id
            ),
            None,
        )
        if task is None:
            raise ScenarioValidationError(
                f"Task '{task_id}' is not declared in suite '{self.suite_id}' held_out partition."
            )
        if task.fingerprint is None:
            raise ScenarioValidationError(
                f"Held-out task '{task_id}' requires a fingerprint before payload resolution."
            )
        payload = resolver.resolve(self.protected_payload_locator, task)
        if not isinstance(payload, bytes):
            raise ScenarioValidationError(
                f"Protected resolver must return bytes for held-out task '{task_id}'."
            )
        expected_digest = task.fingerprint.removeprefix("sha256:").lower()
        if hashlib.sha256(payload).hexdigest() != expected_digest:
            raise ScenarioValidationError(
                f"Protected payload fingerprint mismatch for held-out task '{task_id}'."
            )
        return payload


class ProtectedPayloadResolver(Protocol):
    """Injected boundary capable of retrieving bytes for a protected suite task."""

    def resolve(self, locator: str, task: SuiteTask) -> bytes:
        """Return protected bytes without adding task content to suite metadata."""

        ...
