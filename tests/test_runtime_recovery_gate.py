"""Regression for actual queue entry point, no native COMSOL needed."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from server.runtime import Runtime
from server.case_clock import CaseClock

class RuntimeRecoveryGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.r=Runtime(output_root=self.root)
        self.addCleanup(self.r.executor.shutdown)
    def job(self):
        return {"job_id":"new","status":"queued","operation_id":"new-op",
                "request":{"kind":"study"},"task_case_id":"case"}
    def test_unresolved_blocks_new_submission(self):
        self.r.jobs["prior"]={"job_id":"prior","status":"recovery_pending"}
        self.assertEqual(self.r._queue_job(self.job(),lambda:None)["error"],"UNRESOLVED_RECOVERY_JOBS")
        self.assertNotIn("new",self.r.jobs)
    def test_unreadable_journal_blocks_even_without_operation_id(self):
        self.r.journal_errors.append({"error":"bad manifest"})
        j=self.job();j["operation_id"]=None
        self.assertEqual(self.r._queue_job(j,lambda:None)["error"],"OPERATION_JOURNAL_UNCERTAIN")
    def test_original_receipt_still_available(self):
        j=self.job();self.r.jobs["new"]=dict(j,status="recovery_pending")
        self.r.operations["new-op"]="new"
        self.assertTrue(self.r._queue_job(j,lambda:None)["existing_job"])
    def test_required_clock_missing(self):
        self.r.case_clock_required=True
        self.assertEqual(self.r._queue_job(self.job(),lambda:None)["error"],"CASE_CLOCK_UNAVAILABLE")
    def test_closed_clock_blocks(self):
        c=CaseClock(self.r.case_clock_path)
        c.start("case",14400,1800,9000,900,False);c.close("case","TASK_COMPLETE")
        self.assertEqual(self.r._queue_job(self.job(),lambda:None)["error"],"CASE_CLOCK_EXIT")
    def test_hard_clock_cannot_be_bypassed_by_flag(self):
        CaseClock(self.r.case_clock_path).start("case",14400,1800,9000,900,True)
        self.assertEqual(self.r._queue_job(self.job(),lambda:None)["error"],"HARD_DEADLINE_UNSUPPORTED")
    def test_case_id_required(self):
        CaseClock(self.r.case_clock_path).start("case",14400,1800,9000,900,False)
        j=self.job();j["task_case_id"]=None
        self.assertEqual(self.r._queue_job(j,lambda:None)["error"],"CASE_CLOCK_ID_MISMATCH")
if __name__=="__main__": unittest.main()
