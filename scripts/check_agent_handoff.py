"""Validate declared specialist handoff. Does not authenticate evidence or grant authority."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("assignment_id", "task_id", "case_id", "role", "stage",
        "spec_hash", "revision", "snapshot_hash")


def check_handoff(task, result, now=None):
    errors = []
    for name, value in (("agent-task", task), ("agent-result", result)):
        schema = json.loads((ROOT / "schemas" / (name + ".schema.json")).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors.extend(name + ": " + e.message for e in validator.iter_errors(value))
    if not errors:
        for key in KEYS:
            if task[key] != result[key]:
                errors.append("identity mismatch: " + key)
        allowed = set(task["evidence_refs"])
        for finding in result["findings"]:
            if set(finding["evidence_refs"]) - allowed:
                errors.append("finding cites evidence outside assignment")
        if result["status"] == "COMPLETE" and not result["findings"]:
            errors.append("complete result requires findings")
        if result["status"] != "COMPLETE" and not result["limitations"]:
            errors.append("incomplete result requires limitations")
        deadline = datetime.fromisoformat(task["deadline_utc"].replace("Z", "+00:00"))
        if deadline.utcoffset() is None or deadline.utcoffset().total_seconds() != 0:
            errors.append("deadline must be UTC")
        elif (now or datetime.now(timezone.utc)) >= deadline:
            errors.append("assignment expired")
    return {"contract_status": "FAIL" if errors else "PASS", "errors": errors,
            "native_verified": False, "execution_authorized": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("task", type=Path)
    p.add_argument("result", type=Path)
    a = p.parse_args()
    report = check_handoff(json.loads(a.task.read_text(encoding="utf-8")),
                           json.loads(a.result.read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2))
    raise SystemExit(report["contract_status"] != "PASS")
