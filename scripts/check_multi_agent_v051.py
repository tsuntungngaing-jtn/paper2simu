"""Offline v0.5.1 policy decisions. Reported snapshots are not authenticated live authority."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "agent-knowledge" / "registry.json"
FAULT_ROUTES = {
    "F1": ["recovery_agent", "documentation_expert"],
    "F2": ["recovery_agent", "documentation_expert"],
    "F3": ["recovery_agent", "documentation_expert", "physics_reviewer"],
    "F4": ["recovery_agent", "documentation_expert"],
    "F5": ["physics_reviewer", "recovery_agent"],
    "F6": ["paper_reader", "acceptance_agent", "experiment_designer"],
    "F7": ["orchestrator", "supervisor"],
}

def decision(action, reason):
    return dict(action=action, reason=reason, native_verified=False,
                execution_authorized=False)

def positive(v):
    return type(v) in (int, float) and math.isfinite(v) and v > 0

def utc(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.utcoffset() is None or d.utcoffset().total_seconds() != 0:
        raise ValueError("UTC required")
    return d

def knowledge_check(role, receipts, root=ROOT):
    registry = json.loads((root / "agent-knowledge/registry.json").read_text(encoding="utf-8"))
    if role not in registry["roles"] or not isinstance(receipts, dict):
        return decision("BLOCK", "unknown role or receipts")
    paths = ["agent-knowledge/registry.json", "agent-knowledge/"+role+"/ROLE.md"] + registry["roles"][role]["docs"]
    for name in paths:
        item = receipts.get(name, {})
        path = root / name
        if not path.is_file() or not isinstance(item, dict) or not isinstance(item.get("locator"), str) or not item["locator"].strip():
            return decision("BLOCK", "missing knowledge receipt: "+name)
        if item.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            return decision("BLOCK", "knowledge revision mismatch: "+name)
    return decision("CONTRACT_PASS", "declared core receipts match bundled bytes; reading comprehension unverified")

def route_fault(code):
    return dict(decision("FREEZE_DEPENDENT_SUBMISSIONS", "diagnose original fault without duplicate job"),
                roles=FAULT_ROUTES.get(code, ["supervisor", "recovery_agent"]))

def recovery_next(s):
    if not s.get("original_identity_verified") is True or not s.get("submission_reconciled") is True:
        return decision("RECONCILE", "original operation unresolved")
    if s.get("job") not in ("IDLE", "TERMINAL", "RUNNING", "ISOLATED"):
        return decision("HOLD", "unknown job status")
    if not positive(s.get("remaining_seconds")):
        if s["job"] not in ("IDLE", "TERMINAL", "ISOLATED"):
            return decision("MONITOR_OR_AUTHORIZED_STOP", "cutoff; no new submits")
        return decision("CLOSE_CASE", "cutoff; no new submits")
    if s.get("verified_recovery") is True and s.get("current_provider_verified") is True:
        return decision("RESUME_MONITOR" if s["job"] == "RUNNING" else "RESUME_REVIEW", "reconciled recovery")
    if s["job"] == "RUNNING":
        return decision("OBSERVE", "no mutation during active job")
    if s.get("official_source_verified") is not True or not positive(s.get("remaining_retries")):
        return decision("HOLD", "need official basis and retry budget")
    return decision("DIAGNOSE", "prepare authorized reversible repair, not permission")

def current_review(s, role, verdict, now):
    item = s.get("reviews", {}).get(role, {})
    try:
        same = all(isinstance(s.get(k), str) and s[k] and item.get(k) == s[k] for k in
                   ("task_id", "case_id", "revision", "spec_hash", "snapshot_hash", "stage", "action_id"))
        return (same and item.get("verdict") == verdict and item.get("role") == role
                and isinstance(item.get("worker_id"), str) and bool(item["worker_id"])
                and item["worker_id"] not in (s.get("executor_id"), s.get("orchestrator_id"), s.get("proposer_id"))
                and item.get("evidence_verified") is True and item.get("knowledge_verified") is True
                and item.get("evidence_refs") and utc(item["deadline_utc"]) > now)
    except (KeyError, TypeError, ValueError):
        return False

def admit(s, now=None):
    now = now or datetime.now(timezone.utc)
    if s.get("mode") != "MULTI_AGENT":
        return decision("BLOCK", "explicit fallback uses separate baseline rules")
    if s.get("actor_role") != "executor" or not s.get("executor_id") or s.get("actor_id") != s["executor_id"] or not s.get("orchestrator_id") or s["executor_id"] == s["orchestrator_id"]:
        return decision("BLOCK", "sole distinct Executor required")
    for k in ("actual_isolation_verified", "writer_lease_verified", "scope_authorized", "native_capability_verified",
              "criteria_frozen", "original_identity_verified", "submission_reconciled", "checkpoint_verified",
              "rollback_supported", "executor_knowledge_verified"):
        if s.get(k) is not True:
            return decision("BLOCK", "missing "+k)
    if s.get("job") != "IDLE" or s.get("unresolved_operation") is not False:
        return decision("RECONCILE", "not verified idle or operation unresolved")
    if s.get("active_veto") is not False:
        return decision("BLOCK", "supervisory veto unresolved")
    try:
        if utc(s["deadline_utc"]) <= now or not positive(s.get("remaining_seconds")):
            return decision("CLOSE_SUBMISSION", "deadline reached")
    except (KeyError, TypeError, ValueError):
        return decision("BLOCK", "unknown cutoff")
    if s.get("hard_deadline_required") is True and s.get("hard_deadline_supported") is not True:
        return decision("BLOCK", "hard cutoff unsupported")
    action = s.get("action")
    if action not in ("BUILD", "MUTATE", "SOLVE", "REPAIR"):
        return decision("BLOCK", "unknown action")
    if action == "SOLVE" and not positive(s.get("remaining_solves")):
        return decision("CLOSE_SUBMISSION", "solve budget exhausted")
    if action == "REPAIR" and (not positive(s.get("remaining_retries")) or s.get("official_source_verified") is not True or s.get("new_evidence") is not True):
        return decision("BLOCK", "repair needs official basis, new evidence and budget")
    level = s.get("parameter_level")
    if level not in ("NONE", "L1", "L2", "L3"):
        return decision("BLOCK", "locked or unknown parameter level")
    if level in ("L2", "L3") and not all(s.get(k) is True for k in ("tentative_scope_authorized", "hypothesis_frozen", "range_evidenced", "validation_plan_frozen")):
        return decision("BLOCK", "conditional trial missing prerequisites")
    if not current_review(s, "supervisor", "ALLOW", now):
        return decision("BLOCK", "fresh independent Supervisor clearance required")
    if action in ("SOLVE", "REPAIR") or level in ("L2", "L3"):
        if not current_review(s, "physics_reviewer", "ALLOW", now):
            return decision("BLOCK", "fresh independent physics clearance required")
        if s["reviews"]["supervisor"]["worker_id"] == s["reviews"]["physics_reviewer"]["worker_id"]:
            return decision("BLOCK", "distinct reviewers required")
    return decision("ADMISSION_CANDIDATE", "declared gates met; actual provider enforcement and live recheck required")

def acceptance(s, now=None):
    now = now or datetime.now(timezone.utc)
    if s.get("reproduction") is not True:
        return decision("NOT_APPLICABLE", "execution is not reproduction")
    if not current_review(s, "acceptance_agent", "PASS", now):
        return decision("HOLD", "independent fresh acceptance required")
    if s.get("active_veto") is not False or s.get("criteria_frozen") is not True:
        return decision("HOLD", "veto or unfrozen criteria")
    required = set(s.get("required_gates", []))
    if not {"G1", "G2", "G3", "G4"}.issubset(required) or not required.issubset({"G1", "G2", "G3", "G4", "G5"}):
        return decision("HOLD", "invalid frozen gate scope")
    if s.get("desktop_promised") is True and "G5" not in required:
        return decision("HOLD", "promised native delivery missing gate")
    for key in required:
        g = s.get("gates", {}).get(key, {})
        if g.get("status") != "PASS" or g.get("snapshot_hash") != s.get("snapshot_hash") or not g.get("evidence_refs") or g.get("evidence_verified") is not True:
            return decision("HOLD", "required gate lacks fresh evidence: "+key)
    return decision("DECLARED_ACCEPTANCE_CANDIDATE", "all reported gates pass; scientific truth not independently established by code")

def promote(s):
    if s.get("dataset_split") not in ("experience", "development"):
        return decision("BLOCK", "held-out or unknown split")
    if s.get("status") not in ("VALIDATED", "GENERALIZED") or s.get("revoked") is not False:
        return decision("HOLD", "not validated or revoked")
    for k in ("source_hashes_verified", "repeat_evidence_verified", "applicability_verified",
              "redaction_verified", "regression_passed"):
        if s.get(k) is not True:
            return decision("HOLD", "missing "+k)
    ids = [s.get(k) for k in ("author_id", "supervisor_id", "acceptance_id")]
    if not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != 3:
        return decision("BLOCK", "independent promotion review required")
    if s.get("status") == "GENERALIZED" and (type(s.get("independent_cases")) is not int or s["independent_cases"] < 2):
        return decision("HOLD", "generalization requires independent cases")
    return decision("PROMOTION_CANDIDATE", "reviewed declarations only; no sync or automatic merge")

def pr_ready(s):
    if not all(s.get(k) is True for k in ("isolated_branch", "validated_experience", "offline_regression_passed", "privacy_review_passed", "independent_review", "baseline_pinned")):
        return decision("HOLD", "PR prerequisites missing")
    return decision("PR_CANDIDATE" if s.get("native_integration_passed") is True else "DRAFT_PR_CANDIDATE", "no auto merge, release or deployment")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=["knowledge", "admit", "fault", "recovery", "acceptance", "promote", "pr"])
    p.add_argument("input", type=Path)
    a = p.parse_args()
    s = json.loads(a.input.read_text(encoding="utf-8"))
    fn = {"knowledge": lambda x: knowledge_check(x["role"], x["receipts"]),
          "admit": admit, "fault": lambda x: route_fault(x.get("fault_class")),
          "recovery": recovery_next, "acceptance": acceptance, "promote": promote, "pr": pr_ready}
    print(json.dumps(fn[a.kind](s), indent=2))

if __name__ == "__main__":
    main()
