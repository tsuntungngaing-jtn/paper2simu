import copy
from datetime import datetime, timezone
import unittest
from scripts.check_agent_handoff import check_handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        identity = dict(assignment_id="a1", task_id="t1", case_id="c1",
                        role="physics_reviewer", stage="precheck", revision="r1",
                        spec_hash="a"*64, snapshot_hash="b"*64)
        self.task = dict(identity, schema_version="agent-task/1", evidence_refs=["snapshot1"],
                         question="Review boundary bindings", deadline_utc="2030-01-01T00:00:00Z")
        self.result = dict(identity, schema_version="agent-result/1", status="COMPLETE",
                           findings=[dict(statement="Check inlet", severity="WARNING",
                                          evidence_refs=["snapshot1"])], limitations=[])
        self.now = datetime(2029, 1, 1, tzinfo=timezone.utc)

    def check(self):
        return check_handoff(self.task, self.result, self.now)

    def test_valid_contract_not_native_proof(self):
        r = self.check()
        self.assertEqual(r["contract_status"], "PASS")
        self.assertFalse(r["native_verified"])
        self.assertFalse(r["execution_authorized"])

    def test_reject_stale_cross_case_and_wrong_role(self):
        for key, val in [("revision", "r2"), ("case_id", "other"),
                         ("role", "paper_reader"), ("snapshot_hash", "c"*64)]:
            with self.subTest(key=key):
                original = copy.deepcopy(self.result)
                self.result[key] = val
                self.assertEqual(self.check()["contract_status"], "FAIL")
                self.result = original

    def test_reject_unscoped_evidence(self):
        self.result["findings"][0]["evidence_refs"] = ["unassigned"]
        self.assertEqual(self.check()["contract_status"], "FAIL")

    def test_reject_late_result(self):
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(self.check()["contract_status"], "FAIL")

    def test_reject_worker_self_authorization(self):
        self.result["execution_authorized"] = True
        self.assertEqual(self.check()["contract_status"], "FAIL")

    def test_incomplete_requires_limitation(self):
        self.result.update(status="BLOCKED", findings=[])
        self.assertEqual(self.check()["contract_status"], "FAIL")
        self.result["limitations"] = ["missing snapshot"]
        self.assertEqual(self.check()["contract_status"], "PASS")
