"""Render a Paper2Simu task handoff from its local plan and trial events."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile


UNRESOLVED_STATES = {"UNKNOWN", "UNVERIFIED", "QUEUED", "RUNNING"}


def read_events(path):
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict) or not item.get("event"):
                raise ValueError("expected an event object")
        except ValueError as error:
            raise ValueError(f"{path}:{number}: {error}") from error
        events.append(item)
    return events


def remaining(limit, previously_used, reserved):
    if limit is None or previously_used is None:
        return "UNKNOWN"
    if type(limit) is not int or type(previously_used) is not int or min(limit, previously_used) < 0:
        raise ValueError("solve budgets and prior attempts must be nonnegative integers or null")
    return str(max(0, limit - previously_used - reserved))


def render_summary(plan, events, journal):
    phases = {phase["id"]: phase for phase in plan["phases"]}
    if not phases or len(phases) != len(plan["phases"]):
        raise ValueError("plan must have unique phase IDs")
    if not plan["scorer_version"]:
        raise ValueError("plan must identify its scorer, or use NOT_APPLICABLE")
    phase_id = next(iter(phases))
    next_action = phases[phase_id]["first_action"]
    action_evidence = []
    trials = {}
    reservations = {}
    last_attempt = None
    for position, event in enumerate(events):
        kind = event["event"]
        if kind == "phase_entered":
            phase_id = event["phase_id"]
            next_action = phases[phase_id]["first_action"]
            action_evidence = event.get("evidence_refs", [])
        if event.get("next_action"):
            next_action = event["next_action"]
            action_evidence = event.get("evidence_refs", [])

        trial_id = event.get("trial_id")
        if not trial_id:
            if kind in {"submission_started", "submitted", "job_observed", "evaluated"}:
                raise ValueError(f"{kind} requires trial_id")
            continue
        if kind == "planned" or trial_id not in trials:
            last_attempt = trial_id
        trial = trials.setdefault(trial_id, {})
        for key in ("job_id", "run_id", "operation_id"):
            if event.get(key):
                if trial.get(key) and trial[key] != event[key]:
                    raise ValueError(f"{trial_id}: changed {key}; use a new trial for a new execution")
                trial[key] = event[key]
        if kind in {"submitted", "job_observed"} and event.get("runtime_id"):
            trial["runtime_id"] = event["runtime_id"]
        if event.get("job_id") and kind != "submission_started":
            trial.setdefault("job_state", "UNVERIFIED")

        if kind == "submission_started":
            if trial.get("job_state"):
                raise ValueError(f"{trial_id}: duplicate submission; use a new trial after reconciliation")
            operation = event["operation_id"]
            if not operation or operation in reservations:
                raise ValueError("submission_started requires a unique operation_id")
            reserved_phase = event.get("phase_id", phase_id)
            if reserved_phase not in phases:
                raise ValueError(f"unknown submission phase: {reserved_phase}")
            reservations[operation] = reserved_phase
            trial["job_state"] = "UNKNOWN"
        elif kind == "submitted":
            trial["job_state"] = "UNVERIFIED" if trial.get("job_id") or trial.get("run_id") else "UNKNOWN"
        elif kind == "job_observed":
            state = event["job_status"]
            if state not in {"QUEUED", "RUNNING", "UNKNOWN", "TERMINAL", "NOT_SUBMITTED"}:
                raise ValueError(f"unknown job status: {state}")
            if state in {"TERMINAL", "NOT_SUBMITTED"} and not event.get("evidence_refs"):
                raise ValueError(f"{trial_id}: resolving a job requires evidence_refs")
            trial["job_state"] = state
        elif kind == "evaluated":
            trial["decision"] = event["decision"]
            trial["evaluation"] = event
            trial["evaluation_order"] = position
            trial["checkpoint_eligible"] = (
                not any(item.get("job_state") in UNRESOLVED_STATES for item in trials.values())
                and trial.get("job_state") in {None, "TERMINAL"}
            )
            if event["decision"] == "KEEP" and not trial["checkpoint_eligible"]:
                next_action = f"Re-evaluate {trial_id} after reconciling the original operations and jobs."
                action_evidence = event.get("evidence_refs", [])
        if kind in {"submission_started", "submitted", "job_observed"}:
            trial["observed_at"] = event.get("timestamp_utc", "UNKNOWN")
            if event.get("evidence_refs"):
                trial["job_evidence"] = event["evidence_refs"]

    pending = {key: trial for key, trial in trials.items()
               if trial.get("job_state") in UNRESOLVED_STATES}
    accepted = [trial for key, trial in trials.items() if key not in pending
                and trial.get("decision") == "KEEP"
                and trial["checkpoint_eligible"]
                and trial["evaluation"].get("scorer_version") == plan["scorer_version"]
                and trial["evaluation"].get("accepted_checkpoint")
                and trial["evaluation"].get("evidence_refs")]
    checkpoint = "UNKNOWN"
    if accepted:
        latest_keep = max(accepted, key=lambda trial: trial["evaluation_order"])
        checkpoint = latest_keep["evaluation"]["accepted_checkpoint"]
    if pending:
        next_action = "Reconcile the original operations and jobs through the configured MCP and native evidence before any new submission."
    phase = phases[phase_id]
    budget = plan.get("budget", {})
    total = remaining(budget.get("max_new_solves"), budget.get("prior_solve_attempts"), len(reservations))
    phase_budget = remaining(phase.get("max_new_solves"), phase.get("prior_solve_attempts"),
                             sum(value == phase_id for value in reservations.values()))
    if total in {"0", "UNKNOWN"} or phase_budget in {"0", "UNKNOWN"}:
        next_action += " New solves require a known, positive task and phase budget."
    last_decision = trials.get(last_attempt, {}).get("decision", "PENDING")
    lines = [f"# {plan['task_id']} — {plan['host']}",
             f"- Snapshot (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
             f"- Phase: {phase['title']} ({phase_id})",
             f"- Phase completion: {phase['done_when']}",
             f"- Latest attempt: {last_attempt or 'NONE'} ({last_decision if last_attempt else 'NOT_RUN'})",
             f"- Accepted checkpoint: {checkpoint}",
             f"- New solve attempts remaining: task {total}, phase {phase_budget}",
             f"- Next action: {next_action}",
             "- Evidence: " + ", ".join([plan["task_card"], str(journal), *action_evidence]),
             "- Outstanding operations and jobs (last recorded state):"]
    for trial_id, trial in pending.items():
        lines.append(f"  - {trial_id}: {trial['job_state']} | operation {trial.get('operation_id', 'UNKNOWN')}"
                     f" | job {trial.get('job_id', 'UNKNOWN')} | run {trial.get('run_id', 'UNKNOWN')}"
                     f" | last observed runtime {trial.get('runtime_id', 'UNKNOWN')}"
                     f" | event time {trial.get('observed_at', 'UNKNOWN')}")
        if trial.get("job_evidence"):
            lines.append("    - Source: " + ", ".join(trial["job_evidence"]))
    if not pending:
        lines.append("  - None in this journal. Verify live state before submitting.")
    return "\n".join(lines) + "\n"


def refresh(task_dir, journal=None):
    plan = json.loads((task_dir / "task-plan.json").read_text(encoding="utf-8-sig"))
    if journal is None:
        journal = task_dir / plan.get("journal", "trials/events.jsonl")
    summary = render_summary(plan, read_events(journal), journal)
    target = task_dir / "resume.md"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=task_dir, delete=False) as output:
            temporary = Path(output.name)
            output.write(summary)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    task = commands.add_parser("refresh", help="write the task's resume.md")
    task.add_argument("task_dir", type=Path)
    task.add_argument("--journal", type=Path, help="override the event journal path for this refresh")
    board = commands.add_parser("board", help="print a read-only view of existing resume.md files")
    board.add_argument("summaries", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        if args.command == "refresh":
            print(refresh(args.task_dir, args.journal))
        else:
            for path in args.summaries:
                if path.name != "resume.md":
                    parser.error("board inputs must be resume.md files")
                try:
                    print(path.read_text(encoding="utf-8").strip(), end="\n\n")
                except OSError as error:
                    print(f"# {path}\n\nSummary unavailable: {error}\n")
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(2, f"Unable to refresh handoff: {error}\n")


if __name__ == "__main__":
    main()
