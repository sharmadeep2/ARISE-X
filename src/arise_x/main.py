"""CLI entry point for ARISE-X reliability experiments."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from arise_x.config import ConfigurationError, load_settings
from arise_x.drift.statistics import SamplingDesignError
from arise_x.evaluation.runner import execute_and_persist_run
from arise_x.storage.repository import (
    RepositoryError,
    RunNotFoundError,
    RunRepository,
    write_results,
)
from arise_x.trust.gate import GateService, HeldOutSuiteError
from arise_x.trust.vector import DimensionScore, VectorDimension

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
# Missing run IDs and held-out-suite validation failures (suite/scenario
# mismatch, expired rotation, development-only evidence) are configuration
# problems, not release-regression verdicts, and always exit distinctly from
# EXIT_FAILURE's "the gate blocked release on the merits" meaning.
EXIT_CONFIGURATION_ERROR = 2

app = typer.Typer(add_completion=False, no_args_is_help=True)

_ITERATIONS_OPTION = typer.Option(5, min=1, max=1000)
_SCENARIO_OPTION = typer.Option(
    None, "--scenario", help="Path to an alternate experiment manifest."
)
_SEED_OPTION = typer.Option(None, "--seed", help="Override the scenario's deterministic seed.")
_BASELINE_RUN_ID_OPTION = typer.Option(
    ..., "--baseline-run-id", help="Immutable run ID of the golden baseline."
)
_CANDIDATE_RUN_ID_OPTION = typer.Option(
    ..., "--candidate-run-id", help="Immutable run ID of the candidate being gated."
)
_PRODUCTION_HISTORY_RUN_ID_OPTION = typer.Option(
    None,
    "--production-history-run-id",
    help="Immutable run ID containing independent production episodes.",
)


def _format_dimension(score: DimensionScore) -> str:
    """Format a dimension score for terse CLI output; unavailable dimensions print as "n/a"."""

    return f"{score.value:.2f}" if score.available else "n/a"


@app.command("run-loop")
def run_loop(
    iterations: int = _ITERATIONS_OPTION,
    scenario_path: Path | None = _SCENARIO_OPTION,
    seed: int | None = _SEED_OPTION,
) -> None:
    """Run baseline plus disruption simulations and write a versioned report."""

    settings = load_settings(experiment_path=scenario_path) if scenario_path else load_settings()
    repository = RunRepository(settings.output_dir)
    outcome = execute_and_persist_run(iterations, settings, repository, seed=seed)

    report_path = Path(settings.output_dir) / "latest-run.json"
    write_results(report_path, outcome.results)

    trustworthy = sum(1 for result in outcome.results if result.trustworthy)
    typer.echo(f"Run ID: {outcome.run_id}")
    typer.echo(f"Scenario: {outcome.scenario_version}")
    typer.echo(f"Agent: {outcome.agent_version}")
    typer.echo(f"Seed: {outcome.seed}")
    typer.echo(f"Configuration fingerprint: {outcome.config_fingerprint}")
    typer.echo(
        f"Thresholds: trust={outcome.trust_threshold}, drift={outcome.drift_threshold}"
    )
    typer.echo(f"Saved {len(outcome.results)} iterations to {report_path}")
    typer.echo(f"Trustworthy runs: {trustworthy}/{len(outcome.results)}")
    if outcome.vectors:
        latest_vector = outcome.vectors[-1]
        summary = ", ".join(
            f"{dimension.value}={_format_dimension(latest_vector.dimension(dimension))}"
            for dimension in VectorDimension
        )
        typer.echo(f"Reliability vector (last task): {summary}")


@app.command("gate")
def gate(
    baseline_run_id: str = _BASELINE_RUN_ID_OPTION,
    candidate_run_id: str = _CANDIDATE_RUN_ID_OPTION,
    production_history_run_id: str | None = _PRODUCTION_HISTORY_RUN_ID_OPTION,
    scenario_path: Path | None = _SCENARIO_OPTION,
) -> None:
    """Compare a baseline and candidate run and print a release-gate verdict.

    Exit codes: 0 = pass or warn (warn is advisory-only and does not fail CI
    by default -- check the printed "Verdict:" line to distinguish them); 1 =
    the gate blocked release on a critical-dimension regression or an
    exhausted production error budget; 2 = a configuration/lookup error --
    an unknown run ID, or a held-out-suite validation failure (suite/
    scenario mismatch, expired rotation, or development-only evidence).
    Held-out-suite failures always exit 2, even though the underlying
    `GateVerdict.outcome` is "block", so CI can distinguish "the release
    regressed on the merits" from "the gate could not be trusted to
    evaluate this comparison".
    """

    try:
        settings = (
            load_settings(experiment_path=scenario_path)
            if scenario_path
            else load_settings()
        )
        service = GateService(
            RunRepository(settings.output_dir),
            scenario=settings.scenario,
            suite=settings.evaluation_suite,
            policy=settings.gate_policy,
        )
        decision = service.evaluate(
            baseline_run_id,
            candidate_run_id,
            production_history_run_id=production_history_run_id,
        )
    except RunNotFoundError as error:
        typer.echo("Gate input run was not found.", err=True)
        raise typer.Exit(code=EXIT_CONFIGURATION_ERROR) from error
    except (
        ConfigurationError,
        RepositoryError,
        SamplingDesignError,
        HeldOutSuiteError,
        ValueError,
    ) as error:
        typer.echo("Gate evidence or configuration is invalid.", err=True)
        raise typer.Exit(code=EXIT_CONFIGURATION_ERROR) from error

    for result in decision.dimension_rationale:
        typer.echo(
            f"{result['dimension']}: effect_size={result['effect_size']}, "
            f"significant={result['significant']}, "
            f"material_drift={result['material_drift']}, "
            f"has_sufficient_data={result['has_sufficient_data']}"
        )
    typer.echo(f"Decision ID: {decision.decision_id}")
    typer.echo(f"Agent Reliability Index (geometric): {decision.geometric_ari}")
    for reason in decision.critical_override_reasons:
        typer.echo(f"CRITICAL: {reason}")
    for reason in decision.held_out_suite_reasons:
        typer.echo(f"HELD-OUT SUITE: {reason}")
    for reason in decision.required_evidence_reasons:
        typer.echo(f"EVIDENCE: {reason}")
    for reason in decision.error_budget_reasons:
        typer.echo(f"PRODUCTION BUDGET: {reason}")
    for reason in decision.non_critical_warning_reasons:
        typer.echo(f"WARN: {reason}")
    typer.echo(f"Verdict: {decision.verdict}")

    if decision.verdict == "block":
        raise typer.Exit(code=EXIT_FAILURE)
    raise typer.Exit(code=EXIT_SUCCESS)


def main() -> int:
    """Main entry point with script-friendly exit codes."""

    try:
        app()
        return EXIT_SUCCESS
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
