# Research plan and Codex handoff

Use this workflow for a multi-stage or recurring COMSOL or Fluent task. Keep records in the existing task output directory. The task card remains the specification for inputs, allowed changes, QoIs, acceptance and authorization. Reuse its `QOI_CONTRACT`, `INPUT_LEDGER` and `TRIAL_MATRIX`. The plan references those records and supplies the order of work and stage exit conditions.

## Start or adopt a plan

Save a `task-plan.json` in the existing task directory. Use its real task ID, host, solver, task-card location, scorer version and stage budgets. Write a dated revision and rationale in the journal when a material plan or scorer change is authorized. Preserve historical stage IDs and consumed budget. Keep the task's existing time, RAM, cutoff and repair constraints in the task card. A stage budget is a ceiling within the task budget.

```json
{
  "task_id": "example-saved-solution-audit",
  "host": "simulation-host",
  "solver": "COMSOL",
  "task_card": "reproduction-task.md",
  "scorer_version": "Q1",
  "budget": {"max_new_solves": 0, "prior_solve_attempts": 0},
  "phases": [
    {"id": "inputs", "title": "Inputs and QoIs", "done_when": "Document sources and freeze QoI definitions", "first_action": "Read the task card and source ledger", "max_new_solves": 0, "prior_solve_attempts": 0},
    {"id": "baseline", "title": "Saved baseline", "done_when": "Identify and score the saved baseline", "first_action": "Match the saved run, solution and dataset", "max_new_solves": 0, "prior_solve_attempts": 0},
    {"id": "trials", "title": "Discriminating trials", "done_when": "Record what the evidence resolves and any open hypotheses", "first_action": "Compare the existing saved solutions using Q1", "max_new_solves": 0, "prior_solve_attempts": 0},
    {"id": "holdout", "title": "Independent verification", "done_when": "Record the holdout result or why it remains unverified", "first_action": "Check the availability of untouched holdout evidence", "max_new_solves": 0, "prior_solve_attempts": 0},
    {"id": "delivery", "title": "Delivery", "done_when": "Deliver evidence and unresolved items", "first_action": "Export the task dashboard from the trial records", "max_new_solves": 0, "prior_solve_attempts": 0}
  ]
}
```

This example uses an explicitly read-only solve budget. Set `prior_solve_attempts` to the number of already charged attempts **not represented by `submission_started` entries in the selected journal**, at task and phase levels. If any required number is unknown, write `null` and continue evidence work while reconciling the allowance. With an older task, keep the original trial files, point to the existing task-level JSONL if it fits, or index relevant historical records in the same trial directory by reference. Carry over the last accepted checkpoint and each outstanding or ambiguous submission with sourced events. Missing historical evidence stays unknown. Use `NOT_APPLICABLE` for the scorer only for an execution-only task.

## Record each attempt in the existing trial journal

For a new plan, create `trials/events.jsonl` in the task directory, initially empty. For an existing task-level JSONL, set the plan's optional `journal` to its path (relative to the task directory or absolute) so scheduled and manual refreshes use the same file. Keep one writer per task and append a complete JSON object per line. Every entry includes `event` and `timestamp_utc`. Add `trial_id` to trial events. These entries reference the existing detailed trial records and MCP or native evidence rather than duplicating them.

| Event | Record in the existing journal |
|---|---|
| `phase_entered` | `phase_id`, evidence of prior stage outcome, `next_action` when it differs from the plan. An open hypothesis or a `NOT_RUN` test remains visible at delivery. |
| `planned` | Parent checkpoint and trial ID, one hypothesis, the single intervention or justified joint intervention, expected signed response, what would disconfirm it, and the cheapest useful check. Link the trial record. |
| `submission_started` | Write and flush **before** the authorized solver submit call. Record `trial_id`, stable unique `operation_id`, and `phase_id`. Pass that ID to the COMSOL submit tool when its schema exposes it. This charges one attempt even when the reply is lost. A read-only saved-solution audit does not write this event. |
| `submitted` | Record the returned `job_id` or stable runner `run_id`, connector `runtime_id` when available, and evidence for the original operation. If the reply was lost, keep the existing operation unresolved. |
| `job_observed` | Record `QUEUED`, `RUNNING`, `UNKNOWN`, `TERMINAL` or `NOT_SUBMITTED`, known IDs including the observed `runtime_id` when available, and `evidence_refs` from the current registered provider or native records. A vanished job, empty queue or readable checkpoint alone does not justify `TERMINAL` or `NOT_SUBMITTED`. |
| `evaluated` | Link actual setting readback, QoI and check results, scorer version, and trial evidence. Record `decision`, `reason`, and `next_action` explaining which hypothesis gained or lost support and what evidence to inspect next. Include `accepted_checkpoint` (path and/or hash as a string) only for a supported `KEEP`. |

For a `KEEP`, preserve the existing acceptance rules. Check that compared runs use the same QoI definitions and that required physics and numerics pass. For heat-transfer cases, consider the applicable mass and energy balances, local temperature bounds, and whether the improvement exceeds observed mesh or extraction variation. Use `HOLD` when evidence cannot discriminate. Preserve `REVERT` and `FAILED` trial evidence. Select any new checkpoint only from a verified result. Corrections append a replacement observation or evaluation with a pointer to the old record. When correcting an identity, preserve the original record and document the identity reconciliation before reusing the operation. A case-level `KEEP` advances that task's checkpoint. Shared policy promotion follows [independent RSI evaluation](context-retrieval-rsi-evaluation.md).

## Track independent work in the same plan

Add an optional `work_nodes` list at the top level of `task-plan.json`. Use stable IDs and list the prerequisites for each node. For example:

```json
{
  "work_nodes": [
    {"id": "physics", "action": "Specify the dry and wet balance equations offline"},
    {"id": "build", "action": "Assemble and verify the defined branches", "depends_on": ["physics"], "requires_idle_solver": true},
    {"id": "solve", "action": "Run the verified model under the task budget", "depends_on": ["build"], "requires_submission": true},
    {"id": "qoi", "action": "Freeze the paper comparison dataset and normalization"}
  ]
}
```

Append work events to the same journal. Use `node_id`, `timestamp_utc` and `evidence_refs` for `work_completed`, `work_blocked` and `work_unblocked`. For `work_blocked`, also supply `blocker_type` from the [dependency-scoped progress guide](dependency-scoped-progress.md), `last_attempt`, `actual_return`, `resume_when`, and `next_action`. For example, scope a missing hard deadline capability to `solve`; the offline physics and QoI tasks can advance. Complete a node after recording evidence that its prerequisites were met.

The renderer defers `requires_idle_solver` and `requires_submission` nodes while original jobs are unreconciled. An unknown or exhausted task or phase solve budget also defers `requires_submission` nodes. Confirm real task authorization and native readiness before acting on any `READY` entry. The journal and existing task card remain the authority for evidence and authorization.

## Resume a task or read the four-machine board

Generate the one-page handoff after a phase transition, job-state change, evaluation, or before giving up control. Run from the package checkout or pass the installed script's path. Use the same command from a fresh Codex chat or a scheduled turn if the summary is missing or stale.

```text
python scripts/research_resume.py refresh <task-output-directory>
python scripts/research_resume.py refresh <task-output-directory> --journal <existing-trial-journal.jsonl>
python scripts/research_resume.py board <host1/resume.md> <host2/resume.md> <host3/resume.md> <host4/resume.md>
```

The renderer reads the task plan and trial events, then atomically replaces only `resume.md`. Use `--journal` for a one-time override. The board reads supplied summaries and makes missing hosts visible. Keep native job and evidence files with their owning task. Compare the snapshot and job observation times to check freshness. If refresh fails, treat the old summary as historical and read the journal and job state directly. Never infer permission or live job state from a summary.

At handoff, read `resume.md` first, then the referenced task card and evidence needed for the next action. Recover and reconcile recorded operation, runtime, job and run identities through the [current registered MCP and native records](scheduled-connection-recovery.md). Recheck remaining task/phase allowance and the submission cutoff. If an original submission remains unknown, keep monitoring and do not issue a replacement or advance the checkpoint. If filesystem writes are temporarily unavailable, continue authorized read-only work and report where the durable record stopped.

Design references: [Karpathy Autoresearch experiment loop](https://github.com/karpathy/autoresearch/blob/master/program.md), [Auto-Codex recovery from on-disk state](https://github.com/hyq718/Auto-Codex#recovery-is-for-future-workers), [Codex Autoresearch state and decision projections](https://github.com/TheGreenCedar/codex-autoresearch/blob/main/plugins/codex-autoresearch/docs/control-plane.md).
