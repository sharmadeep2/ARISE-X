---
title: ARISE-X phase completion audit
description: Read-only acceptance audit and baseline validation of implementation Phases 0 through 7
ms.date: 2026-09-09
---

## Executive finding

Audit status: Complete. Product acceptance status: Partial for every phase.
Do not interpret the 205 passing tests or historical completion checkboxes as
proof of the original success criteria. No product code, tests, configuration,
or parent tracking files were edited. This report is the only intentional
workspace addition.

The highest-risk findings are fabricated single-agent fault evidence, a gate
that can pass incompatible or empty evidence without production-budget data,
mutable persisted run identity, and absent default redaction. These are
original commitments, not production calibration or provider integration.

Inputs reviewed: the [plan](.copilot-tracking/plans/2026-08-25/arise-x-framework-validation-implementation-plan.instructions.md),
[details](.copilot-tracking/details/2026-08-25/arise-x-framework-validation-implementation-details.md),
[research](.copilot-tracking/research/2026-08-25/arise-x-framework-validation-research.md),
[changes](.copilot-tracking/changes/2026-08-25/arise-x-framework-validation-implementation-changes.md),
and [planning log](.copilot-tracking/plans/logs/2026-08-25/arise-x-framework-validation-implementation-log.md).
All product modules and the tests relevant to each acceptance area were inspected.
Python scripting, testing, uv, Markdown, writing-style, foundational Python,
and fact-grounded coding instructions were loaded.

## Phase and step disposition

Complete validation steps below mean their existing automated checks passed,
not that missing acceptance cases are implemented. No phase is externally
blocked from inspection; architectural decisions block its acceptance instead.

| Phase | Status | Exact step disposition | Evidence and remaining acceptance gap |
| --- | --- | --- | --- |
| 0: Scenario and persistence | Partial | 0.1 Partial; 0.2 Partial; 0.3 Partial | YAML dependencies, frozen models, runtime environment precedence, suite identity/rotation checks, read/list/lookup and legacy writes exist. Original singular experiment shape, invalid disruption rejection, protected resolver, suite uniqueness/fingerprint/seed governance, immutable writes and strict schema integrity are missing. Focused tests pass through the full suite; explicit sync was not rerun. Findings A03, A04, A06 |
| 1: Deterministic execution | Partial | 1.1 Partial; 1.2 Partial; 1.3 Partial | Agent protocol is invoked once per task; seeded replay and legacy keys work. Outcomes, latency, interventions and violations are still synthetically modified. API scenario is ignored; configuration fingerprint omits effective runtime thresholds and gate policy. No exception-path acceptance test. Findings A01, A06, A10 |
| 2: Trajectory/vector contracts | Partial | 2.1 Partial; 2.2 Partial; 2.3 Complete for existing tests | Ordered frozen steps, identity checks, eight independent dimensions, unavailable factory and normalization label exist. Terminal/recovery/type invariants, confidence/coverage denominator and evidence references are absent; available scores can have zero evidence. Optional raw fields are not a redaction policy. Findings A04, A05 |
| 3: Evidence integration | Partial | 3.1 Partial; 3.2 Partial; 3.3 Partial; 3.4 Partial | One trajectory/vector per task, transient RunEvent projection, unavailable behavioral stability, schema-2 storage and bounded default HTTP summaries exist. Agent structured evidence is unavailable; usage and outcome evidence are synthetic, raw text is persisted, and documentation commands are stale. Findings A01, A03, A05, A10 |
| 4: Verified chaos | Partial | 4.1 Partial; 4.2 Partial; 4.3 Partial; 4.4 Partial | Taxonomy, seeded receipt objects and an explicit pairing helper exist. No genuine single-agent fault dispatch, no working Level 3/4 or cross-cutting dispatch, no executed abort/blast-radius policy, no recovered single-agent fault path, and no persisted control pairing. Findings A01, A02 |
| 5: Drift and release gate | Partial | 5.1 Partial; 5.2 Partial; 5.3 Partial; 5.4 Not complete; 5.5 Partial | Paired task averaging, Wilcoxon/permutation/McNemar branches, Holm correction, bootstrap intervals, geometric ARI, critical regressions and isolated SLI arithmetic exist. Comparability, required coverage, valid power/cluster sufficiency, independent production input/windowing, policy versioning, persisted decisions and shared gate service do not. No automated gate HTTP tests exist. Findings A07, A08, A09, A10 |
| 6: Multi-agent and MACS | Partial | 6.1 Partial; 6.2 Partial; 6.3 Not complete; 6.4 Partial | Real coordinator composition, five diagnostic components, message loss/context withholding and an in-memory runner are implemented and tested. No topology/role configuration, CLI/API selection or coordination persistence; other Level 5 faults silently do nothing. Recovery/state evidence can contradict verification. Finding A11 |
| 7: Validation and handoff | Partial | 7.1 Partial; 7.2 Partial; 7.3 Not attempted by audit scope; 7.4 Audit findings supplied | Ruff, full pytest, imports, OpenAPI, local HTTP and CLI probes ran. Explicit sync/build were not rerun. Compatibility largely remains, but README smoke fails and decisions are not reconstructable. Repairs require parent authorization; historical completion statements need qualification. |

## Confirmed findings

### A01 Single-agent execution still fabricates fault outcomes

High severity; Steps 1.1, 3.1 and 4.2.
[Task execution](src/arise_x/evaluation/runner.py#L308-L355) calls the agent
before dispatch, samples latency, forces success false on a sampled trigger,
and adds random policy violations/interventions. Nothing reaches an agent,
tool, data source or recovery handler as a fault.
[Dispatch verification](src/arise_x/chaos/injector.py#L63-L105) is
`triggered and control_success`, not an observed injection receipt.

Probe P01/P02 used an always-successful local agent and seed 31. The no-fault
control reported `goal_achieved=False`, no fault record, but recovery available.
The experiment reported a verified failure and one intervention absent from
the agent response. Baseline still samples the runner's 0.08 failure rate.
[Resilience](src/arise_x/evaluation/runner.py#L254-L271) is available for every
task, including untriggered/no-fault tasks. Verified single-agent recovery can
never succeed: verification implies a trigger, and a trigger forces failure.
The pairing helper runs twice but does not reset stateful agents, control
agent RNG, or persist the pair. Seed replay proves repeatable fabrication,
not a measured reliability experiment.

### A02 Catalog coverage and abort semantics are metadata only

High severity; Steps 4.1-4.4 and 6.2.
[Catalog contract](src/arise_x/chaos/catalog.py#L101-L168) lacks intensity,
duration and blast-radius fields; abort is a descriptive string. Strategies
and abort strings are never executed by dispatch. Only baseline, latency
spike and tool degradation enter the single-agent sampler. Every Data/Agent
and cross-cutting entry is unsupported at runtime, explicitly documented in
the [catalog](src/arise_x/chaos/catalog.py#L11-L38).

[Existing chaos tests](tests/test_chaos.py#L97-L144) assert that only those
three dispatch and that Data/Agent faults remain undispatched. They do not
test actual abort, recovered execution, or external-side-effect containment.
Unsupported Level 6/provider experiments are deferred; completing all of
Phase 4 as taxonomy alone was not an original plan decision. A bounded local
fault-capable scripted/tool adapter needs a parent-approved design, not live
infrastructure faults or external services.

### A03 Persistence is not immutable or path-confined

High severity; Steps 0.2, 3.2, 5.3 and 7.2.
[write_run](src/arise_x/storage/repository.py#L174-L210) overwrites an existing
run ID with `write_text`. Probe P04 wrote the same ID twice and read seed 2
instead of seed 1. There is no exclusive-create or atomic publication.
[Read/lookup paths](src/arise_x/storage/repository.py#L263-L274) do not call
the ID validator. Probe P05 read `../audit-neighbor` from another disposable
directory, proving confinement failure without reading any user data.

[list_runs](src/arise_x/storage/repository.py#L263-L267) reads every JSON file,
including the CLI's [legacy latest result](src/arise_x/main.py#L78-L79).
P06/P23 reproduced `CorruptRunError` after an ordinary CLI-style write.
These are isolated repair candidates with focused repository/CLI tests.

### A04 Schema acceptance is weaker than typed evidence claims

High severity for gate inputs; Steps 0.2, 2.1, 2.2, 3.2 and 7.2.
[Repository reconstruction](src/arise_x/storage/repository.py#L135-L160)
accepts arbitrary vector schema/normalization labels and silently supplies
missing labels. [read_run](src/arise_x/storage/repository.py#L212-L261) checks
only the envelope schema, not filename versus metadata identity, trajectory
run identity, results/trajectory/vector alignment or per-task correlation.
P20 accepted inner run ID `different-inner-id` and nested `unsupported-v99`.
An existing [round-trip fixture](tests/test_repository.py#L221-L237) itself
uses inconsistent run identity and evidence counts.

P07 accepted `outcome=None`, `recovered=True` without a fault, NaN latency,
and an available perfect dimension with zero evidence. See
[trajectory validation](src/arise_x/telemetry/trajectory.py#L54-L111),
[terminal checks](src/arise_x/telemetry/trajectory.py#L155-L181), and
[score validation](src/arise_x/trust/vector.py#L56-L62).
Frozen dataclasses do not validate runtime types or recursively freeze a
caller-supplied list. Confidence, coverage denominator, policy provenance,
and step-level evidence references also have no contract fields.

### A05 Raw payloads persist and return without redaction

High severity; Steps 2.1, 3.2, 6.3 and 7.2.
[Single-agent trajectory construction](src/arise_x/evaluation/runner.py#L190-L205)
stores prompts/output; [multi-agent construction](src/arise_x/evaluation/runner.py#L648-L676)
stores worker prompts and responses. Repository serialization and
[detail retrieval](src/arise_x/api/app.py#L106-L126) return those fields
unchanged. P03 persisted a synthetic non-secret sentinel verbatim.
Tests only prove raw fields may be omitted by a caller; they do not prove
default omission/redaction. No protected payload resolver enforces separation.
This is an original data-handling commitment, distinct from WI-03's full
security threat model. Preserve correlation while omitting payloads by
default; approve any detailed-content opt-in separately.

### A06 Configuration and governance validation are incomplete

Medium/high severity; Steps 0.1, 1.2 and 5.3.
[Scenario parsing](src/arise_x/config.py#L80-L112) accepts only `scenario:`,
not the planned original singular `experiment:` shape. P09 confirmed rejection.
Disruption entries are not validated against supported catalog capabilities;
P08 accepted an unknown name that [silently became baseline](src/arise_x/chaos/catalog.py#L760-L769).
The typed `fault_id` option is not parsed from structured YAML references.
Conversion/type errors and invalid environment threshold ranges are not
consistently wrapped as actionable configuration errors.

[Suite models](src/arise_x/scenarios/models.py#L112-L142) do not require
held-out fingerprints, validate digest syntax, prohibit duplicate/overlapping
task IDs, constrain partition names, or represent per-task seeds. Owner,
access policy and protected locator are strings, not enforced resolution.
[Runner selection](src/arise_x/evaluation/runner.py#L114-L125) uses the first
scenario cluster; generated tasks never come from suite entries (WI-08).

[Policy parsing](src/arise_x/config.py#L185-L243) has no policy version,
required-dimension, cluster, minimum eligible or SLI-definition contract.
P10 accepted target power 0.1 and both window forms; mutual exclusion is
validated only if the unused policy conversion method is called. Unknown
policy keys are ignored. [Fingerprinting](src/arise_x/evaluation/runner.py#L507-L514)
covers scenario/suite, not effective environment thresholds, gate policy or
the effective seed override. Seed is separately recorded, but reconstruction
still lacks the full effective configuration. Source revision is supported
by repository writes but is not supplied by the runner.

### A07 Drift comparisons permit invalid pairs and unsupported power claims

High severity; Step 5.1.
[Pairing](src/arise_x/drift/statistics.py#L479-L512) compares task-ID sets only.
It ignores seed/repeat identity, suite ID/version/partition, candidate cluster
and scenario identity, normalization compatibility, repeated-record duplication
and incomplete pair coverage. Missing values are dropped without a coverage
requirement. Binary selection does not validate actual 0/1 observations;
McNemar thresholds continuous values at 0.5. Independent designs are explicitly
rejected, which is safe; categorical-distance support is absent.

[Power](src/arise_x/drift/statistics.py#L563-L582) uses current candidate-minus-
baseline sample SD and a normal approximation regardless of selected test.
The [required_sample_size function](src/arise_x/drift/statistics.py#L212-L249)
has no callers (Pylance references returned its declaration only). One
identical task has SD zero and achieved power 1.0. Cluster count is descriptive,
not enforced. Bootstrap changes intervals only; significance/power remain
task-independent, and a single cluster falls back to naive bootstrap.
[Material classification](src/arise_x/drift/statistics.py#L428-L456) does not
require sufficient power or a negative effect. Target power, confidence,
required sample count, coverage and method-specific assumptions are not all
persisted in the comparison contract.

P11 compared one task with different repeat/seed, suite/version, cluster,
scenario version and normalization; the comparison accepted it with one
cluster and power 1.0. Rejecting invalid pairings and insufficient clusters is
a bounded fix. Selecting defensible method-specific pilot/power and clustered
tests needs statistical design review; WI-01 numeric calibration cannot fix
these algorithmic gaps.

### A08 Release gating fails open on missing required evidence and budget

High severity; Steps 5.2 and 5.3.
[evaluate_release](src/arise_x/trust/gate.py#L603-L713) iterates only dimensions
present in the comparison. Missing critical dimensions and missing/underpowered
non-critical required dimensions are not rejected. Empty comparisons can pass.
[Held-out validation](src/arise_x/trust/gate.py#L145-L153) only requires that
the union of partition labels contain `held_out`; mixed development/candidate
evidence passes without verifying actual task membership or fingerprints.

Production budget is not derived from the candidate, but it is not provided
at all: [API](src/arise_x/api/app.py#L175-L198) and
[CLI](src/arise_x/main.py#L148-L161) omit it. `evaluate_release` permits both
omitted and no-data budgets because only `exhausted` blocks. P11 passed both;
P12 passed an empty drift comparison with no ARI or budget. P13 obtained HTTP
200 / `pass` for the incompatible one-task fixture, with `error_budget=null`.

[Budget arithmetic](src/arise_x/trust/gate.py#L342-L397) expects already-windowed
episodes; no caller selects a trailing calendar or bounded window, and episode
SLI records lack timestamp/source identity. P22 passed 15 episodes to a 10-episode
policy and all 15 were counted. Flooring allowed bad episodes is also a
documented implementation deviation from the plan's fractional formula:
15 at SLO 0.9 yields allowed bad 1 rather than 1.5, exhausting at one failure
instead of retaining one third. Independent production evidence and no-data
blocking are original requirements, not WI-01 calibration.

### A09 Gate service, decision persistence and transport errors are incomplete

High severity; Steps 5.3, 5.5 and 7.2.
API and CLI independently orchestrate statistics/policy rather than delegate
to one service. The repository has no decision store, policy snapshot or
decision read contract. P13 produced no decision artifact. Gates use current
configuration, not immutable policy and suite evidence from the runs; changing
configuration can change a verdict without an auditable policy identity.

P14 returned HTTP 500 for mismatched task sets; P19 CLI task mismatch exited 1,
colliding with a regression block. Missing IDs correctly produce CLI exit 2;
valid fixture pass/block exits are 0/1. The [entire API test module](tests/test_api.py#L1-L114)
has only seven health/run/detail tests, no gate, topology, redaction or OpenAPI
tests, contrary to historical log claims. Add service-level and actual
transport-boundary acceptance tests, not only direct gate function fixtures.

### A10 Documentation and compatibility claims are stale

Medium severity; Steps 1.3, 3.3, 5.4, 6.3 and 7.1-7.2.
[README quick start](README.md#L39-L53) uses the flattened single-command
invocation; it exits 2 now. The explicit `run-loop` subcommand exits 0.
The README still calls drift/gating/multi-agent planned, and
[architecture status](docs/architecture.md#L20-L67) denies code that exists.
Neither documents gate invocation, independent production evidence, calibration
limits in operation, nor multi-agent invocation. README also claims suite-based
execution despite generated development tasks. API `scenario` is documented
as unused and is ignored; P15 accepted a nonexistent scenario with HTTP 200.
No topology field exists. [Trust scorer wording](src/arise_x/trust/scorer.py#L1-L20)
still describes release-gate-style decisions, although the gate correctly does
not consume this additive score as ARI.

### A11 Multi-agent integration exists only as an in-memory Python path

High/medium severity; Steps 6.1-6.4.
[run_multi_agent_reliability_loop](src/arise_x/evaluation/runner.py#L703-L767)
has only three test call sites and no product caller (Pylance references).
It returns episodes, trajectories, vectors and diagnostic MACS, so this is
more than isolated coordinator unit code. However,
[MultiAgentRunOutcome](src/arise_x/evaluation/runner.py#L595-L610) explicitly
leaves episodes unpersisted; configuration, API and CLI cannot select topology,
roles, workers or faults. No schema stores exchanges, handoffs, verifications
or MACS. Generic trajectory conversion discards causal details and worker
versions and only embeds worker identity in the tool name.

Message loss really skips worker execution and withholding really changes
the prompt. Other catalog faults are silently ignored by the
[coordinator](src/arise_x/agents/multi_agent.py#L388-L500); P17 requested
agent disagreement and received no dispatch receipts or rejection. Worker
exceptions abort the episode rather than produce terminal failure evidence.
P16 used an always-successful response with unrelated output under verified
withholding: trajectory step said recovered, objective failed verification,
and recovery vector was zero. Any response is treated as step recovery,
regardless of verification. The actual context sent to the worker is not
represented in its generic trajectory prompt. Calibration and non-star
topologies remain deferred; durable star integration was explicitly in Phase 6.

## Deferred scope versus missed commitments

| Work item | Explicit deferral retained | Does not excuse |
| --- | --- | --- |
| WI-01 | Representative population studies and domain-specific numeric policy calibration | Invalid power claims, missing required evidence checks, absent production-budget input/window or versioned decision persistence |
| WI-02 | Provider/framework adapters | Fault-capable local scripted execution and truthful telemetry |
| WI-03 | Full agentic threat model | Default redaction, read-path confinement and declared abort controls |
| WI-04 | MACS weighting calibration and chain/tree/graph comparison | Configured star execution, durable correlation and API/CLI exposure |
| WI-05 | Level 6 provider-controlled model experiments | Levels 1-4 verified local chaos and Phase 6's stated Level 5 slice |
| WI-06 | Removing compatibility wrappers | Correct diagnostic labels and stable existing entry points |
| WI-07 | Dashboards, RCA and analysis UX | Required bounded evidence and gate rationale APIs |
| WI-08 | Suite-driven protected held-out task selection in runner | Gate-side validation of supplied held-out evidence and production budget |

WI-08 explicitly acknowledges a feature originally promised in Steps 0.1
and 5.3. Respect the later recorded deferral; do not silently implement it in
repairs or pretend original phase acceptance was complete. The changes log
misattributes this deferral to WI-01 in one paragraph; the planning log has
the explicit WI-08 entry. Parent should reconcile scope and completion markers.

## Validation results and reproduction record

Python environment was configured before Python execution: selected project
venv, Python 3.11.15. No packages were installed intentionally and no external
service was called; uv commands used offline mode with existing project state.

| Check | Result |
| --- | --- |
| Initial Git status | Unborn main, no commits; origin/main reported gone. Entire project is untracked. No reset, stash, stage or commit used. A Git diff cannot establish content integrity here. |
| `uv run ruff check .` | Exit 0, all checks passed |
| `uv run pytest` | Exit 0, 205 passed, one Starlette/httpx deprecation warning, 4.85 seconds |
| Repeated `uv run pytest` | Exit 0, same 205 passed and warning, 5.06 seconds |
| `uv run arise-x run-loop --iterations 3` | Exit 0; versioned run and legacy summary written only to audit temporary storage |
| Python module imports and `app.openapi()` | Passed; health, run, run-detail and gate paths generated |
| Temporary FastAPI TestClient probes | Mismatched evidence passed gate; task mismatch produced 500; unknown scenario accepted; no decision file persisted |
| Temporary CLI subprocess probes via selected Python `-m arise_x.main` | Explicit run-loop 0; manually constructed gate pass 0; critical regression block 1; missing run 2; incompatible task sets 1; README flattened command 2 |
| P01-P23 temporary behavioral probes | Confirmed findings above, executed successfully; these are audit probes, not new committed regression tests |
| Explicit `uv sync`, `uv build`, built-package installation smoke | Not run during this baseline-only audit; historical success is not revalidated. Avoided build-generated changes to source metadata and additional resolution. |

Fixtures used only synthetic strings and disposable directories. No held-out
payloads or secrets were accessed. Initial pytest `PYTEST_ADDOPTS` backslashes
were parsed as escapes, briefly placing the uniquely named audit test directory
under the workspace. Only that audit-created directory was removed; rerunning
with forward-slash paths kept fixtures outside the workspace. Final pre-report
Git status matched the initial top-level untracked entries. Future Windows
pytest environment options should use forward slashes or properly quoted paths.

## Recommended bounded repair order

1. Add focused negative acceptance tests for A01 and A03-A09 before changing
   behavior. Preserve compatibility tests, but do not preserve tests that
   assert unknown faults silently become baseline as the new default policy.
2. Repair isolated boundaries: immutable exclusive run writes, ID confinement
   on reads/exists, legacy-file listing separation, schema/identity validation,
   configuration error wrapping, finite numeric/terminal/recovery invariants,
   and accurate CLI/documentation behavior.
3. Add fail-closed gate checks first: required/critical dimensions, all evidence
   held-out and comparable, missing/insufficient production budget, minimum
   clusters/coverage, and stable incomplete-evidence transport errors. Do not
   substitute candidate episodes for production episodes to make tests pass.
4. Approve one evidence contract revision for structured local execution,
   redaction, verified fault receipts, recovery and control-pair provenance.
   Implement only a bounded in-process fault set with observed effects and
   abort semantics. Unsupported capabilities must reject, not fabricate.
5. Approve a shared gate service with immutable policy/suite snapshots,
   independent timestamped production episode input, defined windowing and
   persisted reproducible decisions. Decide fractional versus floored budget
   arithmetic explicitly. No production backend is required for local tests.
6. Review statistical design before trusting gate power: baseline/pilot inputs,
   test-specific sample requirements, binary independence, clustered inference,
   missingness/coverage and directional regression classification. Calibration
   studies remain WI-01; implementation correctness does not.
7. Complete the chosen star-only integration after single-agent evidence and
   gate contracts stabilize: scenario roles, durable episode/MACS schema,
   bounded redacted CLI/API evidence and unsupported-fault errors. Keep MACS
   diagnostic and WI-04 out of scope.
8. Rerun focused and full tests, Ruff, explicit offline sync/build in temporary
   staging, imports, documented CLI and HTTP pass/block/error checks, then
   let the parent update tracking markers based on actual acceptance.

Steps 2-3 contain isolated repairs; steps 4-7 need explicit bounded design
approval because they cross execution, statistics or evidence schemas. Do not
hide these architectural gaps inside Phase 7 formatting fixes.

## Clarifications for parent authorization

* Keep WI-08 deferred and mark original suite execution criteria partial, or
  explicitly reopen the protected-resolver/held-out runner work?
* Which representative in-process faults satisfy the repaired Phase 4/6 scope,
  and which catalog entries must remain explicitly unsupported?
* Approve independent local production-history input and a schema revision
  before gate integration? Existing schema-2 evidence cannot supply all needed
  receipt, governance, redaction and policy provenance.
* Retain the plan's fractional error budget or explicitly approve the current
  conservative integer policy? What required dimensions and minimum coverage
  should be enforced before domain calibration?

No clarification was needed to finish this read-only audit. These decisions
are prerequisites for repairs, not permission to expand deferred work.