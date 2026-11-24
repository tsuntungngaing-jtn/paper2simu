import hashlib
import json
import unittest
from datetime import datetime, timezone
from scripts.check_multi_agent_v051 import (ROOT, REGISTRY, admit, acceptance, knowledge_check,
    recovery_next, route_fault, promote, pr_ready)

NOW = datetime(2029, 1, 1, tzinfo=timezone.utc)

def fixture():
    s = dict(mode="MULTI_AGENT", actor_role="executor", actor_id="ex", executor_id="ex",
             orchestrator_id="host", proposer_id="proposer", job="IDLE", unresolved_operation=False,
             active_veto=False, deadline_utc="2030-01-01T00:00:00Z", remaining_seconds=60,
             remaining_solves=1, remaining_retries=1, action="SOLVE", parameter_level="NONE",
             task_id="t", case_id="c", revision="r", spec_hash="a", snapshot_hash="b",
             stage="solve", action_id="op")
    for k in ("actual_isolation_verified", "writer_lease_verified", "scope_authorized",
              "native_capability_verified", "criteria_frozen", "original_identity_verified",
              "submission_reconciled", "checkpoint_verified", "rollback_supported",
              "executor_knowledge_verified"):
        s[k] = True
    s["reviews"] = {}
    for role, worker, verdict in [("supervisor", "sup", "ALLOW"), ("physics_reviewer", "phy", "ALLOW"), ("acceptance_agent", "acc", "PASS")]:
        s["reviews"][role] = dict({k:s[k] for k in ("task_id", "case_id", "revision", "spec_hash", "snapshot_hash", "stage", "action_id", "deadline_utc")},
            role=role, worker_id=worker, verdict=verdict, evidence_verified=True,
            knowledge_verified=True, evidence_refs=["receipt"])
    return s

class V051Tests(unittest.TestCase):
    def test_knowledge_files_and_receipts(self):
        registry = json.loads(REGISTRY.read_text())
        self.assertEqual(len(registry["roles"]), 10)
        for role, info in registry["roles"].items():
            receipts = {}
            for name in ["agent-knowledge/registry.json", "agent-knowledge/"+role+"/ROLE.md"]+info["docs"]:
                receipts[name] = dict(sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), locator="section")
            self.assertEqual(knowledge_check(role, receipts)["action"], "CONTRACT_PASS")
            receipts.pop(info["docs"][0])
            self.assertEqual(knowledge_check(role, receipts)["action"], "BLOCK")

    def test_admission_fails_closed(self):
        s = fixture()
        self.assertEqual(admit(s, NOW)["action"], "ADMISSION_CANDIDATE")
        self.assertFalse(admit(s, NOW)["execution_authorized"])
        for k,v in [("actor_role","orchestrator"), ("active_veto",True), ("writer_lease_verified",False),
                    ("actual_isolation_verified",False), ("parameter_level","L0"), ("parameter_level","L2"),
                    ("revision","old"), ("hard_deadline_required",True), ("remaining_solves",0),
                    ("unresolved_operation",True), ("job","RUNNING")]:
            with self.subTest(k=k):
                self.assertNotEqual(admit(dict(s, **{k:v}), NOW)["action"], "ADMISSION_CANDIDATE")
        s["reviews"]["supervisor"]["worker_id"]="ex"
        self.assertEqual(admit(s, NOW)["action"], "BLOCK")

    def test_fault_and_cutoff(self):
        for i in range(1,8):
            self.assertTrue(route_fault("F"+str(i))["roles"])
        self.assertEqual(recovery_next(dict(job="RUNNING"))["action"], "RECONCILE")
        s = dict(original_identity_verified=True, submission_reconciled=True, job="RUNNING", remaining_seconds=0)
        self.assertEqual(recovery_next(s)["action"], "MONITOR_OR_AUTHORIZED_STOP")
        self.assertEqual(recovery_next(dict(s, job="TERMINAL"))["action"], "CLOSE_CASE")

    def test_acceptance_no_false_pass(self):
        s = fixture()
        s.update(reproduction=True, required_gates=["G1","G2","G3","G4","G5"], desktop_promised=True)
        s["gates"] = {g:dict(status="PASS", snapshot_hash="b", evidence_verified=True, evidence_refs=["e"]) for g in s["required_gates"]}
        self.assertEqual(acceptance(s,NOW)["action"], "DECLARED_ACCEPTANCE_CANDIDATE")
        s["gates"]["G3"]["status"]="NOT_RUN"
        self.assertEqual(acceptance(s,NOW)["action"], "HOLD")

    def test_experience_and_pr(self):
        self.assertEqual(promote(dict(dataset_split="held_out"))["action"], "BLOCK")
        s = dict(dataset_split="development", status="VALIDATED", revoked=False, author_id="a", supervisor_id="b", acceptance_id="c")
        for k in ("source_hashes_verified","repeat_evidence_verified","applicability_verified","redaction_verified","regression_passed"):
            s[k]=True
        self.assertEqual(promote(s)["action"], "PROMOTION_CANDIDATE")
        self.assertEqual(promote(dict(s, acceptance_id="a"))["action"], "BLOCK")
        self.assertEqual(pr_ready({})["action"], "HOLD")
        self.assertEqual(pr_ready(dict(isolated_branch=True,validated_experience=True,offline_regression_passed=True,privacy_review_passed=True,independent_review=True,baseline_pinned=True))["action"],"DRAFT_PR_CANDIDATE")
