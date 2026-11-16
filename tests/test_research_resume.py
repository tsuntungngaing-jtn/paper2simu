import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.research_resume import refresh, render_summary


def plan():
    return {
        "task_id": "saved-heat-transfer-audit",
        "host": "lab-comsol",
        "task_card": "task.md",
        "scorer_version": "Q1",
        "budget": {"max_new_solves": 4, "prior_solve_attempts": 1},
        "phases": [
            {"id": "baseline", "title": "Baseline", "done_when": "Saved solution identified",
             "first_action": "Read baseline evidence", "max_new_solves": 0, "prior_solve_attempts": 0},
            {"id": "trials", "title": "Discriminating trials", "done_when": "Rank hypotheses",
             "first_action": "Compare the saved solutions", "max_new_solves": 2, "prior_solve_attempts": 0},
        ],
    }


def baseline():
    return {"event": "evaluated", "trial_id": "T0", "decision": "KEEP", "scorer_version": "Q1",
            "accepted_checkpoint": "baseline.mph", "evidence_refs": ["baseline-audit.json"]}


class ResearchResumeTests(unittest.TestCase):
    def test_lost_ack_survives_fresh_turn_and_reserves_budget(self):
        events = [baseline(), {"event": "phase_entered", "phase_id": "trials"},
                  {"event": "planned", "trial_id": "T1"},
                  {"event": "submission_started", "trial_id": "T1", "operation_id": "op-1"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / "historical-events.jsonl"
            (root / "task-plan.json").write_text(json.dumps(dict(plan(), journal=journal.name)), encoding="utf-8")
            original = "\n".join(map(json.dumps, events)) + "\n"
            journal.write_text(original, encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "scripts" / "research_resume.py"
            subprocess.run([sys.executable, str(script), "refresh", tmp],
                           check=True, capture_output=True, cwd=root)
            output = (root / "resume.md").read_text(encoding="utf-8")
            self.assertIn("Accepted checkpoint: baseline.mph", output)
            self.assertIn("Latest attempt: T1", output)
            self.assertIn("task 2, phase 1", output)
            self.assertIn("T1: UNKNOWN | operation op-1 | job UNKNOWN", output)
            self.assertIn("before any new submission", output)
            self.assertEqual(journal.read_text(encoding="utf-8"), original)

    def test_observations_require_evidence_and_wrong_scorer_cannot_replace_checkpoint(self):
        events = [baseline(), {"event": "planned", "trial_id": "T1"},
                  {"event": "submitted", "trial_id": "T1", "job_id": "job-1", "runtime_id": "rt-1"},
                  {"event": "job_observed", "trial_id": "T1", "job_status": "RUNNING"}]
        output = render_summary(plan(), events, Path("events.jsonl"))
        self.assertIn("job job-1", output)
        self.assertIn("last observed runtime rt-1", output)
        terminal = {"event": "job_observed", "trial_id": "T1", "job_status": "TERMINAL"}
        with self.assertRaisesRegex(ValueError, "requires evidence_refs"):
            render_summary(plan(), [*events, terminal], Path("events.jsonl"))
        terminal["evidence_refs"] = ["job-status.json"]
        candidate = dict(baseline(), trial_id="T1", accepted_checkpoint="candidate.mph", scorer_version="Q2")
        output = render_summary(plan(), [*events, terminal, candidate], Path("events.jsonl"))
        self.assertIn("Accepted checkpoint: baseline.mph", output)
        self.assertIn("None in this journal", output)

    def test_hold_preserves_checkpoint_and_supplies_next_action_with_zero_budget(self):
        data = plan()
        data["budget"] = {"max_new_solves": 0, "prior_solve_attempts": 0}
        events = [baseline(), {"event": "planned", "trial_id": "T1"},
                  {"event": "evaluated", "trial_id": "T1", "decision": "HOLD",
                   "next_action": "Locate the lowest-temperature region in the saved dataset",
                   "evidence_refs": ["saved-solution-audit.json"]}]
        output = render_summary(data, events, Path("events.jsonl"))
        self.assertIn("Latest attempt: T1 (HOLD)", output)
        self.assertIn("Accepted checkpoint: baseline.mph", output)
        self.assertIn("Locate the lowest-temperature region", output)
        self.assertIn("saved-solution-audit.json", output)
        self.assertIn("task 0, phase 0", output)

    def test_checkpoint_cannot_advance_until_unknown_submission_is_reconciled(self):
        candidate = dict(baseline(), trial_id="T2", accepted_checkpoint="candidate.mph")
        events = [baseline(), {"event": "submission_started", "trial_id": "T1", "operation_id": "op-1",
                               "evidence_refs": ["submit-request.json"]}, candidate]
        blocked = render_summary(plan(), events, Path("events.jsonl"))
        self.assertIn("Accepted checkpoint: baseline.mph", blocked)
        self.assertIn("Source: submit-request.json", blocked)
        events.append({"event": "job_observed", "trial_id": "T1", "job_status": "NOT_SUBMITTED",
                       "evidence_refs": ["provider-denial.json"]})
        reconciled = render_summary(plan(), events, Path("events.jsonl"))
        self.assertIn("Accepted checkpoint: baseline.mph", reconciled)
        self.assertIn("Next action: Re-evaluate T2", reconciled)
        reassessed = render_summary(plan(), [*events, candidate], Path("events.jsonl"))
        self.assertIn("Accepted checkpoint: candidate.mph", reassessed)

    def test_invalid_journal_does_not_replace_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "task-plan.json").write_text(json.dumps(plan()), encoding="utf-8")
            (root / "resume.md").write_text("previous snapshot", encoding="utf-8")
            journal = root / "broken.jsonl"
            journal.write_text('{"event":', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "broken.jsonl:1"):
                refresh(root, journal)
            self.assertEqual((root / "resume.md").read_text(encoding="utf-8"), "previous snapshot")
