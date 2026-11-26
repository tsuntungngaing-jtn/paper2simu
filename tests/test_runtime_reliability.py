import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server.case_clock import CaseClock, admission
from server.reliability import diagnose, compare_live, loopback_probe

class ClockTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"clock.sqlite3"
        self.t=1000.
        self.c=CaseClock(self.db,lambda:self.t)
    def start(self,hard=False):
        return self.c.start("P008-c1",240,30,150,15,hard)
    def test_resume_no_reset(self):
        self.start();self.t+=10
        c=CaseClock(self.db,lambda:self.t)
        self.assertEqual(c.start("P008-c1",240,30,150,15,False)["started_at_unix"],1000)
        with self.assertRaises(ValueError): c.start("P008-c1",300,30,150,15,False)
        with self.assertRaises(ValueError): c.start("next",240,30,150,15,False)
    def test_stall_latches_and_replay_cannot_refresh(self):
        self.start();self.t=1005
        self.assertTrue(self.c.observe("P008-c1","a"*64,1005)["progress_accepted"])
        self.t=1010
        self.assertFalse(self.c.observe("P008-c1","a"*64,1010)["progress_accepted"])
        self.t=1020
        self.assertEqual(self.c.status()["reason"],"NO_VERIFIED_PROGRESS")
        self.assertFalse(self.c.observe("P008-c1","b"*64,1020)["progress_accepted"])
        self.assertFalse(admission(self.db,"P008-c1",lambda:self.t)["allowed"])
    def test_wrap_and_next_case(self):
        self.c.start("P008-c1",240,30,150,240,False)
        self.t=1210
        self.assertEqual(self.c.status()["reason"],"WRAP_WINDOW")
        self.c.start("next",240,30,150,15,False)
        self.assertEqual(self.c.status()["case_id"],"next")
        self.assertEqual(admission(self.db,"P008-c1",lambda:self.t)["error"],"CASE_CLOCK_ID_MISMATCH")
    def test_clock_rollback_and_hard_gate(self):
        self.start(True)
        self.assertEqual(admission(self.db,"P008-c1",lambda:self.t)["error"],"HARD_DEADLINE_UNSUPPORTED")
        self.t=999
        self.assertEqual(self.c.status()["reason"],"CLOCK_REGRESSION")
    def test_missing_clock_fails_closed(self):
        self.assertEqual(admission(self.db,"P008-c1",lambda:self.t)["error"],"CASE_CLOCK_UNAVAILABLE")
    def test_soft_scope_and_deadline(self):
        self.c.start("P008-c1",240,30,150,240,False)
        self.assertTrue(admission(self.db,"P008-c1",lambda:self.t)["allowed"])
        self.t=1240
        self.assertEqual(self.c.status()["reason"],"CASE_DEADLINE")
    def test_bad_observation_and_manual_close(self):
        self.start()
        with self.assertRaises(ValueError): self.c.observe("P008-c1","bad",1001)
        self.assertFalse(self.c.observe("P008-c1","b"*64,1001)["progress_accepted"])
        self.assertEqual(self.c.close("P008-c1","TASK_COMPLETE")["phase"],"EXIT")

class ReliabilityTests(unittest.TestCase):
    def fixture(self):
        expected={"paper2simu_version":"0.6.1","runtime_root":"root","python_executable":"python",
                  "output_root":"out","runtime_source_sha256":"a"*64,"require_hard_deadline":False}
        identity={k:v for k,v in expected.items() if k!="require_hard_deadline"}
        identity["runtime_id"]="r1"
        receipt={"observed_at_unix":100,"read_only_ok":True,"tool_count":143,
                 "queue":dict(identity,success=True,active_jobs=[],journal_errors=[],recovery_pending=[],submission_budget={"can_submit":True}),
                 "capabilities_response":dict(identity,capabilities={"deadline_enforcement":{"state":"unsupported"}}),
                 "native_identity_verified":True,"native_evidence_ref":"local-readback"}
        return expected,receipt
    def test_502_evidence(self):
        self.assertEqual(diagnose(502,405,True,0,False),"PROXY_MISROUTE_EVIDENCE")
        self.assertEqual(diagnose(502,405,False,0,False),"HTTP_502_CAUSE_UNCONFIRMED")
        self.assertEqual(diagnose(None,None,False,143,True),"MCP_READONLY_REACHED")
    def test_loopback_rejects_nonlocal_and_credentials(self):
        for u in ("http://example.com/mcp","http://user:pass@127.0.0.1/mcp","http://127.0.0.1/mcp?token=x","https://127.0.0.1"):
            with self.assertRaises(ValueError): loopback_probe(u)
    def test_http_reachability_is_not_mcp(self):
        with patch("server.reliability.http.client.HTTPConnection") as conn:
            conn.return_value.getresponse.return_value.status=405
            self.assertFalse(loopback_probe("http://127.0.0.1:8000/mcp")["mcp_verified"])
    def test_version_and_stale_evidence(self):
        e,r=self.fixture()
        self.assertEqual(compare_live(e,r,100)["status"],"METADATA_CANDIDATE")
        r["queue"]["paper2simu_version"]="0.5.1"
        self.assertIn("FINGERPRINT_MISMATCH:paper2simu_version",compare_live(e,r,100)["reasons"])
        self.assertIn("STALE_OR_INVALID_OBSERVATION",compare_live(e,r,161)["reasons"])
    def test_hard_deadline_not_inferred_from_version(self):
        e,r=self.fixture();e["require_hard_deadline"]=True
        self.assertIn("HARD_DEADLINE_UNSUPPORTED",compare_live(e,r,100)["reasons"])
    def test_unknown_operation_and_restart(self):
        e,r=self.fixture();r["original_operation_id"]="op"
        r["queue"]["recovery_pending"]=["job"]
        r["capabilities_response"]["runtime_id"]="new"
        reasons=compare_live(e,r,100)["reasons"]
        self.assertIn("ORIGINAL_OPERATION_UNRESOLVED",reasons)
        self.assertIn("UNRESOLVED_JOURNAL",reasons)
        self.assertIn("RUNTIME_ID_CHANGED_OR_UNKNOWN",reasons)
if __name__=="__main__": unittest.main()
