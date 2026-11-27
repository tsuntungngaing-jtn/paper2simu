"""Render a Paper2Simu task handoff from its local plan and trial events."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from graphlib import TopologicalSorter
import json
from pathlib import Path
import tempfile
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


UNRESOLVED_STATES = {"UNKNOWN", "UNVERIFIED", "QUEUED", "RUNNING"}
WORK_EVENTS = {"work_completed", "work_blocked", "work_unblocked"}
BLOCKER_TYPES = {"input_missing", "physics_unresolved", "model_incomplete", "capability_missing",
                 "deployment_mismatch", "transport_error", "native_solver_failure", "comparison_ambiguous"}


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


def work_progress(plan, events, pending_jobs, can_submit, *, review_context=None, state_only=False):
    from server.task_liveness import validate_nodes, recovery_candidates, verify_completion_receipt
    strict = validate_nodes(plan)
    entries = plan.get("work_nodes", [])
    nodes = {entry["id"]: entry for entry in entries}
    if len(nodes) != len(entries):
        raise ValueError("work_nodes must have unique IDs")
    dependencies = {}
    for node_id, node in nodes.items():
        parents = node.get("depends_on", [])
        if not isinstance(parents, list) or any(parent not in nodes for parent in parents):
            raise ValueError(f"{node_id}: depends_on must list known work node IDs")
        if not node.get("action"):
            raise ValueError(f"{node_id}: work node requires an action")
        dependencies[node_id] = parents
    order = list(TopologicalSorter(dependencies).static_order())
    completed = set()
    blockers = {}
    for event in events:
        kind = event["event"]
        if kind not in WORK_EVENTS:
            continue
        node_id = event["node_id"]
        if node_id not in nodes or not event.get("evidence_refs"):
            raise ValueError(f"{kind} requires a known work node and evidence_refs")
        if kind == "work_blocked":
            if event.get("blocker_type") not in BLOCKER_TYPES or not all(
                event.get(key) for key in ("timestamp_utc", "last_attempt", "actual_return", "resume_when", "next_action")
            ):
                raise ValueError(f"{node_id}: incomplete scoped blocker")
            if node_id in completed:
                raise ValueError(f"{node_id}: use a new work node for work after a completed revision")
            blockers[node_id] = event
        elif kind == "work_unblocked":
            blockers.pop(node_id, None)
        elif node_id in blockers or not set(dependencies[node_id]).issubset(completed):
            raise ValueError(f"{node_id}: resolve its blockers and dependencies before marking it complete")
        else:
            if strict and (event.get("revision_binding") != nodes[node_id]["revision_binding"]
                           or not event.get("review_receipt")):
                raise ValueError(f"{node_id}: completion requires current revision and review receipt")
            if strict:
                if review_context is None:
                    raise ValueError(f"{node_id}: independently approved review index required")
                verify_completion_receipt(plan,event,*review_context)
            completed.add(node_id)

    waiting = {}
    ready = []
    for node_id in order:
        if node_id in completed:
            continue
        if node_id in blockers:
            waiting[node_id] = "recorded blocker"
            continue
        unfinished = [parent for parent in dependencies[node_id] if parent not in completed]
        if unfinished:
            waiting[node_id] = "needs " + ", ".join(unfinished)
            continue
        node = nodes[node_id]
        if pending_jobs and (node.get("requires_submission") or node.get("requires_idle_solver")):
            waiting[node_id] = "reconcile original jobs through MCP first"
        elif node.get("requires_submission") and not can_submit:
            waiting[node_id] = "requires a known positive solve budget"
        else:
            ready.append(node_id)

    if state_only:
        return {"ready":ready,"completed":sorted(completed),"waiting":waiting}
    lines = []
    if nodes:
        lines.append("- Work by dependency:")
        lines.extend(f"  - READY (verify authorization): {key} | {nodes[key]['action']}" for key in ready)
        lines.extend(f"  - WAITING: {key} | {reason}" for key, reason in waiting.items())
        lines.extend(f"  - COMPLETED: {key}" for key in order if key in completed)
        for key, item in blockers.items():
            lines.append(f"  - {key} | {item['blocker_type']} at {item['timestamp_utc']}"
                         f" | tried: {item['last_attempt']} | observed: {item['actual_return']}"
                         f" | resumes when: {item['resume_when']} | check next: {item['next_action']}"
                         f" | evidence: {', '.join(item['evidence_refs'])}")
    for key, item in blockers.items():
        if not item.get("incident_id") or not nodes[key].get("resource_domain"):
            lines.append("  - RECOVERY MAPPING REQUIRED: " + key
                         + " | record reviewed resource_domain and stable incident_id; no inferred authorization")
    for candidate in recovery_candidates(plan, blockers, events=events):
        lines.append("  - RECOVERY CANDIDATE (verify authorization): " + candidate["id"]
                     + " | " + candidate["status"] + " | " + candidate["action"] + " | proposed: " + candidate["proposed_next_action"])
    return (nodes[ready[0]]["action"] if ready else None), bool(waiting), lines


def render_summary(plan, events, journal, *, review_context=None):
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
    can_submit = total not in {"0", "UNKNOWN"} and phase_budget not in {"0", "UNKNOWN"}
    ready_action, work_waiting, progress_lines = work_progress(plan, events, pending, can_submit, review_context=review_context)
    if ready_action:
        next_action = ready_action
        if pending:
            next_action += " | Reconcile original jobs before any new submission."
    elif work_waiting and not pending:
        next_action = "Resolve the listed work dependencies or collect the next discriminating evidence."
    if not can_submit:
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
    lines.extend(progress_lines)
    return "\n".join(lines) + "\n"


def refresh(task_dir, journal=None, *, review_context=None):
    plan = json.loads((task_dir / "task-plan.json").read_text(encoding="utf-8-sig"))
    if journal is None:
        journal = task_dir / plan.get("journal", "trials/events.jsonl")
    summary = render_summary(plan, read_events(journal), journal, review_context=review_context)
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
    preview = commands.add_parser("legacy-preview", help="audit legacy lines without replay or writes")
    preview.add_argument("plan", type=Path)
    preview.add_argument("journal", type=Path)
    board = commands.add_parser("board", help="print a read-only view of existing resume.md files")
    board.add_argument("summaries", type=Path, nargs="+")
    args = parser.parse_args()
    try:
        if args.command == "refresh":
            print(refresh(args.task_dir, args.journal))
        elif args.command == "legacy-preview":
            plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
            print(json.dumps(legacy_journal_preview(plan,args.journal),ensure_ascii=False))
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


# Legacy logs are evidence sources, never authoritative trial journals.
def legacy_journal_preview(plan, path):
    """Read-only line audit; preserve physical lines and overlapping flags."""
    import hashlib
    nodes = {n["id"] for n in plan.get("work_nodes",[])}
    rows = []
    native = {"submission_started","submitted","job_observed","evaluated"}
    markers = {"job_id","operation_id","run_id","trial_id","runtime_id",
               "original_job_id","original_operation_id","original_deadline",
               "deadline","deadline_utc","case_clock","case_clock_id","hard_deadline",
               "job_status","native_state","native_job_id"}
    def fields(value):
        if isinstance(value,dict):
            return ({k for k,v in value.items() if k in markers and v is not None}
                    | set().union(*(fields(v) for v in value.values())))
        if isinstance(value,list):
            return set().union(*(fields(v) for v in value))
        return set()
    for number, raw in enumerate(Path(path).read_bytes().splitlines(keepends=True),1):
        status = "REVIEW_MAPPING_REQUIRED"
        flags = set()
        found = set()
        if not raw.strip():
            status = "BLANK_ROW"
        else:
            try:
                item = json.loads(raw.decode("utf-8-sig"))
                found = fields(item)
                if not isinstance(item,dict) or not item.get("event"):
                    status = "MISSING_EVENT_TYPE"
                elif item["event"] in WORK_EVENTS and item.get("node_id") not in nodes:
                    status = "UNKNOWN_NODE"
                elif item["event"] in WORK_EVENTS and not item.get("evidence_refs"):
                    status = "MISSING_EVIDENCE"
                elif item["event"] in WORK_EVENTS:
                    status = "REVIEW_WORK_EVENT"
                elif item["event"] in native:
                    status = "RECONCILE_NATIVE_EVENT"
                if found or status == "RECONCILE_NATIVE_EVENT":
                    flags.add("POSSIBLE_NATIVE_RECONCILIATION")
            except (ValueError,UnicodeError,TypeError):
                status = "INVALID_ROW"
                flags.add("UNCLASSIFIED_CONTENT")
        rows.append({"line":number,"sha256":hashlib.sha256(raw).hexdigest(),
                     "status":status,"flags":sorted(flags),"native_markers":sorted(found)})
    return {"status":"PREVIEW_ONLY","rows":rows,
            "unresolved_native":[row["line"] for row in rows if row["flags"]],
            "native_execution_authorized":False}


if __name__ == "__main__":
    main()
