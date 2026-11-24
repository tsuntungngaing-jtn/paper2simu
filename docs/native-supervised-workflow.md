# Native CFD workflow and supervision (shared 0.4.5 / 0.5.0 baseline)

The native execution and acceptance rules are inherited from the single-agent control baseline. In 0.5.0 use the [multi-agent orchestration](multi-agent-orchestration.md) for read-only reasoning and independent review; the parent remains sole executor. The host agent executes this procedure through the existing configured MCP; no new GUI driver, daemon or provider. Native solver and live Desktop verification NOT_RUN. Read-only tasks stay read-only. Use one authorized solver/session, one writer, installed-version documentation and actual provider schemas.

## Native-first
Execute supported typed MCP operations against editable native objects, not code blocks for the human to paste. Java/Python inside an authorized connector is an implementation detail; arbitrary operator code retains existing explicit opt-in. Preserve calls and Copy as Code for audit. No shell/GUI bypass.

COMSOL: inspect comsol_status/comsol_doctor, model identity, inspect_current_model, geometry_accept, selection_bind_checked, study_solve_async and native save/evaluation tools when exposed. Preserve named parameters, Geometry, Materials, Physics, Mesh, Study, Results. Desktop connection and exact displayed model identity are separate from MCP attachment. comsol_open_desktop only if exposed/authorized. Process launch does not prove display identity; if not verified provide .mph checkpoint to reopen. No concurrent editing. See [observability](comsol-observability-and-desktop.md).
Fluent: discover official PyFluent MCP schema/build; map native Models, Materials, Cell Zone Conditions, Boundary Conditions, Solution, Report Definitions. Discover Meshing, Workbench and SpaceClaim independently. Preserve matching .cas.h5/.dat.h5 and dependencies; for geometry/mesh editability retain source CAD, reproducible meshing recipe or Workbench archive. Solver case alone proves neither upstream capability nor displayed identity. Never invent tools.

## Stage workflow
Record task/case/run, input/spec/model revisions, native path, manual/build, expected result, effective readback, criterion/status, artifact/hash, invalidated downstream checks and next action per stage. Reuse task, input ledger, QoI and journal. Follow [stage contracts](stage-contracts.md) and [staged solve](staged-solve-contract.md). Statuses refer only to task criteria.

| Stage | Operations and readback |
| --- | --- |
| 0 Specification | Freeze sources, units, geometry, physics, QoI, acceptance and repair budgets; estimate Re, Ma, mass flow, pressure drop, temperature rise, timescale where relevant. Unknown paper facts stay conditional. |
| 1 Geometry | Parameterized fluid/solid domains; native Boolean or supported extraction. Verify volumes, centroids, roles, normals, adjacency, connectivity and CHT interface. Rebind after rebuild; reject equal-area wrong face. |
| 2 Materials | Effective domain properties, formulas, units, valid T/p range; independent low/mid/high checks, K vs Celsius and absolute vs gauge. |
| 3 Physics | Effective equations, enabled nodes, BC coverage, reference pressure, backflow, initialization, coupling; integrate applied heat/source. |
| 4 Mesh | Editable sequence, local sizing, quality, thin gaps, near-wall layers, element counts. Adapt only within authorization and capability; recheck bindings. |
| 5 Reverse precheck | Restate actual equations/BCs from native reads; authorized perturbation on copy with predicted propagation; checkpoint and verify session/jobs/budget. |
| 6 Solve | Async where supported; observe native termination, logs, residuals, QoI drift and task conservation. Transient: actual steps, times, initialization. |
| 7 Evaluate | Current mesh/solution/dataset/run, native reports with signs, selections, units, averaging. Matching control-volume balances including storage. Separate convergence, mesh/time sensitivity and paper comparison. |
| 8 Deliver | Native files, independent reopen, zero-iteration readback, editable scope and separate fresh replay; preserve failed/partial work. |

Fixed source input is not a tuning knob. Low-Mach or symmetry simplification needs evidence and authorized reference comparison. Inconsistent initial state: inspect constraints first; continuation, initialization and time-step changes are bounded numerical trials, not silent changes of physics.

## Event-driven supervision
For authorized unattended solves the host owns the next action without user re-asking. At every scheduled/resumed turn and between native operations reconcile task, original session/jobs/pending operation, elapsed cutoff and remaining budgets. Persist observation and next action in existing journal/resume.md. Ongoing polling requires active host or configured scheduler; otherwise monitoring is BLOCKED/NOT_RUN.

OBSERVE → CLASSIFY → DIAGNOSE → PLAN → ADMIT → APPLY → READBACK → RETEST → KEEP/REVERT/HOLD → OBSERVE. Running jobs remain OBSERVE; no mutation while active. Use job metadata/log tail when JVM busy. Unknown submit must reconcile original operation, disconnect follows scheduled recovery including 502. Missing monitoring is not solver failure.

| Observation | First response |
| --- | --- |
| MCP/502/license/launch | Reconcile provider/session/jobs/logs; configured preflight/recovery, no duplicate launch. |
| Invalid property, selection, stale dataset | Discover schema and effective identity; correct binding or report reference and verify. |
| Geometry/mesh failure | Inspect topology/quality and prerequisites, preserve spec, correct one supported mechanism and rebind. |
| Divergence/plateau/inconsistent initial state | Read native logs, termination, monitors, BC/material/mesh; competing hypotheses, bounded numerical trial. |
| Conservation fails or QoI off target | Audit definitions, signs, freshness, balance and discretization first, then conditional trials. Never lower criteria. |
| Budget exhausted/stop unsupported | Close new submission, preserve original job/checkpoint; follow deadline contract; no claim of stop without terminal evidence. |

Before APPLY record signature/evidence, hypothesis/falsifier, exact native path and old/new values, affected checks, checkpoint hash, authorization, remaining time/solve/retry budget. Single changed mechanism per trial; dependent rebuilds recorded. Auto implementation/numerical repairs only in preauthorized scope, verified idle, supported mutation and rollback. Fixed data, target physics/BC interpretation, new assumptions or resource/permission changes outside scope: HOLD affected branch, continue independent work. Authorized tentative ranges use conditional calibration. Do not weaken criteria, conceal failures, overwrite originals, kill unrelated jobs or alter licensing/security.

Use the offline decision helper before a candidate mutation: python scripts/supervision_decision.py INPUT.json . Input is a reported snapshot, not a native observation. Its APPLY_CANDIDATE is advisory only; recheck live state/authorization immediately before invoking discovered MCP. Save snapshot and decision in journal. After mutation read back and recheck dependencies. Submit authorized retest with stable operation ID once; verify original target and task checks. KEEP only on predeclared improvement without regression, REVERT on degradation or failed readback, HOLD incomplete evidence. Repeated failure without new evidence stops branch. Elapsed budget never resets on reconnect. Next case only under explicit queue policy after terminal/ownership reconciliation. Hard deadline requires verified enforcement per [deadline contract](job-deadline-contract.md); block hard-deadline submission otherwise. See [handoff](research-plan-and-handoff.md), [dependency progress](dependency-scoped-progress.md). Shared policy learning needs separate RSI review.

## Desktop acceptance
Separate backend mutation, displayed identity, archive restore, zero-iteration readback, editable setup/geometry/mesh and fresh solved replay. Engineer edits a copy after verified idle/handoff; agent reinspects lineage before resuming. Setup: change BC and read back. Geometry: edit driving dimension, verify actual domain/roles. Mesh: rebuild and inspect mesh/bindings; save/reopen copy. Declare promised and verified layers. Unsolved edited copy may have null solution/dataset; do not reuse old results. Receipt records actor, build, native path, expected/actual change, source/output/reopen artifact references. See [portable contract](portable-workflow-contract.md).

## Verification plan (NOT_RUN)
COMSOL first: parameterized straight-channel CHT, steady/short transient if authorized, save/reopen, independent BC and dimension edit; equal-area wrong heater, empty selection, temperature unit error and stale dataset on isolated copies. Fluent independently maps same physical spec, verify Solver and available upstream stages. Mock nonconvergence and unknown-submit before native runs. Record build, logs, readbacks, checks, hashes. Synthetic tests are not solver proof.

References: [COMSOL Desktop server](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_running.38.20.html), [PyFluent settings](https://fluent.docs.pyansys.com/version/stable/user_guide/solver_settings/solver_settings_contents.html).
