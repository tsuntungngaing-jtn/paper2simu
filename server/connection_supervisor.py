"""Host-side, bounded MCP recovery; never grants native execution authority.

The caller is a trusted host adapter, not an LLM or MCP tool. The adapter owns
the actual scheduled thread and supplies its observed evidence and RPC method.
"""
import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

SCHEMA = "connection-supervisor/1"
RELOAD_METHOD = "config/mcpServer/reload"
COOLDOWN = 300
MAX_ATTEMPTS = 2
MAX_AGE = 60
FLAGS = ("registered", "transport_ok", "catalog_ok", "readonly_ok",
         "executor_ok", "runtime_ok", "native_ok", "history_ok",
         "policy_denied", "reload_supported", "reload_authorized",
         "refresh_safe")
IDENT = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z")


def _validate(s, now):
    if not isinstance(s, dict):
        raise ValueError("snapshot must be an object")
    for k in ("host_id", "provider_id", "thread_id", "turn_id", "incident_id"):
        if not isinstance(s.get(k), str) or not IDENT.fullmatch(s[k]):
            raise ValueError("invalid identity: " + k)
    for k in FLAGS:
        if k not in s or (s[k] is not None and type(s[k]) is not bool):
            raise ValueError("invalid tri-state: " + k)
    t = s.get("observed_at")
    if type(t) not in (int, float) or not 0 <= now - t <= MAX_AGE:
        raise ValueError("stale or future evidence")
    if s.get("context") != "actual_scheduled":
        raise ValueError("wrong execution context")
    if s.get("solver") not in ("COMSOL", "Fluent"):
        raise ValueError("unsupported solver")


def classify(s):
    """All prerequisites are tri-state; unknown never means healthy."""
    if s["policy_denied"] is not False:
        return "POLICY_BLOCKED"
    for k, status in (
        ("registered", "CONFIG_BLOCKED"),
        ("transport_ok", "TRANSPORT_BLOCKED"),
        ("catalog_ok", "CATALOG_BLOCKED"),
        ("readonly_ok", "MCP_CALL_BLOCKED"),
        ("executor_ok", "EXECUTOR_BLOCKED"),
        ("runtime_ok", "RUNTIME_BLOCKED"),
        ("native_ok", "NATIVE_BLOCKED"),
        ("history_ok", "HISTORY_BLOCKED"),
    ):
        if s[k] is not True:
            return status
    return "CONNECTION_VERIFIED"


def step(db_path, snapshot, rpc=None, now=None):
    """Observe one turn; reserve a refresh before calling the host RPC.

    rpc(method, params) must be a bounded, authenticated request against the
    SAME existing app-server. No arbitrary commands, socket discovery, or
    new clients. A return is an acknowledgement, not proof of recovery.
    The DB is private, shared by all tasks using that app-server. Its lock
    serializes reload requests across providers. It never replaces job ledgers.
    """
    now = time.time() if now is None else now
    s = snapshot
    _validate(s, now)
    status = classify(s)
    out = {"schema": SCHEMA, "status": status,
           "host_id": s["host_id"], "provider_id": s["provider_id"],
           "thread_id": s["thread_id"], "turn_id": s["turn_id"],
           "incident_id": s["incident_id"], "observed_at": s["observed_at"],
           "native_execution_authorized": False, "action": "NONE"}
    db_path = Path(db_path)
    if not db_path.is_absolute() or not db_path.parent.is_dir():
        raise ValueError("use absolute private database path")
    with closing(sqlite3.connect(db_path, timeout=5)) as db:
        db.execute("CREATE TABLE IF NOT EXISTS refreshes "
                   "(host TEXT, incident TEXT, turn TEXT, at REAL, "
                   "PRIMARY KEY(host, incident, turn))")
        db.execute("CREATE TABLE IF NOT EXISTS observations "
                   "(id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        if status in ("CATALOG_BLOCKED", "MCP_CALL_BLOCKED"):
            # A missing catalog must not mask an independent failed or unknown gate.
            # The host may obtain these observations from separately authorized,
            # current native records; otherwise stay blocked, never assume True.
            gates = ("executor_ok", "runtime_ok", "native_ok", "history_ok")
            blockers = [key for key in gates if s[key] is not True]
            if blockers:
                out["refresh_blockers"] = blockers
                out["action"] = "COMBINED_FAULT_BLOCKED"
            elif s["reload_supported"] is not True or rpc is None:
                out["action"] = "HOST_REFRESH_UNAVAILABLE"
            elif s["reload_authorized"] is not True or s["refresh_safe"] is not True:
                out["action"] = "HOST_REFRESH_NOT_ADMITTED"
            elif s["catalog_ok"] is None or (status == "MCP_CALL_BLOCKED" and s["readonly_ok"] is None):
                out["action"] = "COLLECT_ACTUAL_FAILURE"
            else:
                last = db.execute("SELECT MAX(at) FROM refreshes WHERE host=?",
                                  (s["host_id"],)).fetchone()[0]
                count = db.execute("SELECT COUNT(*) FROM refreshes WHERE host=? AND incident=?",
                                   (s["host_id"], s["incident_id"])).fetchone()[0]
                seen = db.execute("SELECT 1 FROM refreshes WHERE host=? AND turn=?",
                                  (s["host_id"], s["turn_id"])).fetchone()
                if count >= MAX_ATTEMPTS:
                    out["action"] = "ESCALATE_ATTEMPTS_EXHAUSTED"
                elif seen or (last is not None and now - last < COOLDOWN):
                    out["action"] = "WAIT_FRESH_TURN"
                else:
                    db.execute("INSERT INTO refreshes VALUES (?,?,?,?)",
                               (s["host_id"], s["incident_id"], s["turn_id"], now))
                    out["action"] = "REFRESH_RESERVED"
        elif status == "CONNECTION_VERIFIED":
            out["action"] = "RECHECK_EXISTING_ADMISSION"
        elif status == "TRANSPORT_BLOCKED":
            out["action"] = "DIAGNOSE_TRANSPORT"
        elif status == "EXECUTOR_BLOCKED":
            out["action"] = "VERIFY_ACTUAL_EXECUTOR_PERMISSION"
        elif status == "NATIVE_BLOCKED":
            out["action"] = "VERIFY_EXISTING_ATTACHMENT"
        elif status == "HISTORY_BLOCKED":
            out["action"] = "RECONCILE_ORIGINAL_JOB"
        else:
            out["action"] = "REPORT_MINIMAL_BLOCKER"
        db.execute("INSERT INTO observations(payload) VALUES (?)", (json.dumps(out),))
        db.commit()
        if out["action"] == "REFRESH_RESERVED":
            try:
                result = rpc(RELOAD_METHOD, {})
                out["action"] = ("REFRESH_ACK_WAIT_NEXT_TURN" if result == {}
                                 else "REFRESH_OUTCOME_UNKNOWN")
            except Exception:
                # Never persist credentials or arbitrary provider exception text.
                out["action"] = "REFRESH_OUTCOME_UNKNOWN"
            db.execute("INSERT INTO observations(payload) VALUES (?)", (json.dumps(out),))
            db.commit()
    return out


def main():
    """Local observation only; live host integration calls step with its RPC."""
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("database")
    p.add_argument("snapshot")
    args = p.parse_args()
    with open(args.snapshot, encoding="utf-8") as f:
        snapshot = json.load(f)
    print(json.dumps(step(args.database, snapshot), indent=2))


if __name__ == "__main__":
    main()
