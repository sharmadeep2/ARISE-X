<!-- markdownlint-disable-file -->

# ARISE-X Hypotheses

## Phase 2 Summary

Hypotheses are prioritized by risk and unblock value. Each hypothesis tests one core assumption.

## H1: Disruption Coverage Predicts Reliability Regressions

We believe targeted environment disruptions (dependency outages, latency spikes, tool response corruption) reveal reliability weaknesses that are not visible in static benchmark runs.
We will test this by running matched agent tasks across baseline and disrupted environments over repeated long-horizon cycles.
We will know we are right when disrupted runs show statistically significant degradation in trust metrics compared with baseline, with reproducible patterns across at least 3 disruption classes.

* Priority: P1
* Risk if wrong: high, because the chaos program would fail to surface practical failure modes.
* Unblock impact: high, because it validates the core ARISE-X premise.

## H2: Drift Signals Can Reliably Detect Trust Degradation

We believe behavioral drift features (goal divergence, policy violation rate, escalating intervention frequency, and output consistency drop) can detect trust degradation early.
We will test this by generating controlled drift scenarios and evaluating detector precision and recall against labeled trust events.
We will know we are right when drift detection achieves at least 0.80 precision and 0.75 recall on held-out scenarios.

* Priority: P1
* Risk if wrong: high, because trust decisions would lack early-warning capability.
* Unblock impact: high.

## H3: Composite Trust Scoring Can Drive Release Decisions

We believe a composite trust score combining reliability, safety, and drift stability can serve as a production gate.
We will test this by comparing score-triggered decisions with expert review on the same evaluation runs.
We will know we are right when score-based verdicts agree with expert assessments in at least 85% of cases.

* Priority: P2
* Risk if wrong: medium-high.
* Unblock impact: high, because this enables operational adoption.

## Dependency Notes

* H1 and H2 inform H3.
* H3 should not be finalized until disruption and drift evidence is stable.
