"""Offline conservative recommendation; does not connect, mutate or enforce a deadline."""
import argparse
import json
import math
from pathlib import Path


def decide(s):
    def yes(k):
        return s.get(k) is True
    def positive(k):
        v = s.get(k)
        return type(v) in (int, float) and math.isfinite(v) and v > 0
    def result(action, reason):
        return {"action": action, "reason": reason, "native_verified": False,
                "execution_authorized": False}
    if not yes("identity_verified") or s.get("job") not in {"idle", "running", "terminal"} or not yes("submission_reconciled"):
        return result("RECONCILE", "original identity or job unresolved")
    if not positive("remaining_seconds") or not positive("remaining_retries") or (yes("retest_required") and not positive("remaining_solves")):
        return result("CLOSE_SUBMISSION", "budget exhausted or unknown")
    if s.get("job") == "running":
        return result("OBSERVE", "no mutation during running job")
    if yes("hard_deadline_required") and not yes("hard_deadline_supported"):
        return result("HOLD", "hard deadline not enforceable")
    if s.get("job") != "idle":
        return result("RECONCILE", "verify idle before mutation")
    if not yes("anomaly_observed"):
        return result("OBSERVE", "no verified anomaly reported")
    if not yes("new_evidence"):
        return result("HOLD", "no new evidence for repair")
    if s.get("repair_class") not in {"implementation", "numerical"}:
        return result("HOLD", "outside routine repair scope")
    required = ("scope_authorized", "checkpoint_verified", "rollback_supported",
                "native_capability_verified", "one_mechanism", "criteria_frozen",
                "writer_verified")
    if not all(yes(k) for k in required):
        return result("HOLD", "missing precondition")
    return result("APPLY_CANDIDATE", "reported preconditions met; recheck live before action")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("snapshot", type=Path)
    args = p.parse_args()
    print(json.dumps(decide(json.loads(args.snapshot.read_text(encoding="utf-8"))), indent=2))
