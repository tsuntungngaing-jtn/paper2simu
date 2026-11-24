import unittest
from scripts.supervision_decision import decide


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.s = dict(identity_verified=True, submission_reconciled=True, job="idle",
                      remaining_seconds=60, remaining_retries=1, remaining_solves=1,
                      retest_required=True, anomaly_observed=True, new_evidence=True,
                      repair_class="numerical", scope_authorized=True,
                      checkpoint_verified=True, rollback_supported=True,
                      native_capability_verified=True, one_mechanism=True,
                      criteria_frozen=True, writer_verified=True)

    def test_advisory_not_authorization(self):
        result = decide(self.s)
        self.assertEqual(result["action"], "APPLY_CANDIDATE")
        self.assertFalse(result["native_verified"])
        self.assertFalse(result["execution_authorized"])

    def test_fail_closed(self):
        for key, value, action in [
            ("job", "unknown", "RECONCILE"), ("submission_reconciled", False, "RECONCILE"),
            ("job", "running", "OBSERVE"), ("job", "terminal", "RECONCILE"),
            ("remaining_seconds", 0, "CLOSE_SUBMISSION"), ("remaining_retries", True, "CLOSE_SUBMISSION"),
            ("remaining_solves", 0, "CLOSE_SUBMISSION"), ("repair_class", "physics", "HOLD"),
            ("new_evidence", False, "HOLD"), ("checkpoint_verified", False, "HOLD"),
            ("writer_verified", False, "HOLD"), ("hard_deadline_required", True, "HOLD"),
        ]:
            with self.subTest(key=key):
                self.assertEqual(decide(dict(self.s, **{key: value}))["action"], action)
