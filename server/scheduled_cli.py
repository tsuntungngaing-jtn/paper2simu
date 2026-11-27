"""Opt-in local scheduler entrypoint; fresh Codex process per durable turn.

This is a separate, explicitly migrated host lane, never a Desktop socket
workaround. The runner does not call a native solver, change permissions, reset
case clocks or infer job outcomes. Native admission remains in the provider.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import uuid
from contextlib import closing


def _path(value, directory=False):
    p = Path(value)
    if not p.is_absolute() or not (p.is_dir() if directory else p.is_file()):
        raise ValueError("invalid absolute path")
    return p.resolve(strict=True)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(config, *, admit=True):
    if config.get("schema") != "paper2simu-scheduled-cli/1":
        raise ValueError("unsupported config")
    for k in ("desktop_schedule_disabled", "exclusive_writer_verified",
              "provider_permissions_verified", "migration_authorized"):
        if admit and config.get(k) is not True:
            raise ValueError("migration not admitted: " + k)
    receipt = _path(config["migration_receipt"])
    if _sha(receipt.read_bytes()) != config["migration_receipt_sha256"]:
        raise ValueError("migration receipt changed")
    exe = _path(config["codex_executable"])
    if os.name == "nt" and exe.suffix.lower() != ".exe":
        raise ValueError("use the actual Codex executable, not a shell shim")
    work = _path(config["workspace"], True)
    home = _path(config["codex_home"], True)
    state = _path(config["state_dir"], True)
    prompt = _path(config["task_prompt"])
    resume = _path(config["resume_file"])
    skill = _path(config["skill_entry"])
    for p in (prompt, resume):
        if not p.is_relative_to(work):
            raise ValueError("task input outside approved workspace")
    if state.is_relative_to(work) or work.is_relative_to(state):
        raise ValueError("private state must be separate from workspace")
    if _sha(prompt.read_bytes()) != config["task_prompt_sha256"]:
        raise ValueError("task prompt changed")
    if _sha(skill.read_bytes()) != config["skill_sha256"]:
        raise ValueError("skill entry changed")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", config["profile"]):
        raise ValueError("invalid profile")
    wait = config.get("observation_timeout_seconds", 900)
    if type(wait) is not int or not 30 <= wait <= 14400:
        raise ValueError("invalid observation timeout")
    return exe, work, home, state, prompt, resume, skill, wait


def _completed(events):
    """Conservative single-turn CLI lifecycle check, not native evidence."""
    phase = "NEW"
    active = set()
    seen = set()
    with events.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            if not line.endswith("\n"):
                return False
            item = json.loads(line)
            if not isinstance(item, dict) or phase == "COMPLETE":
                return False
            kind = item.get("type")
            if kind == "thread.started" and phase == "NEW":
                if not isinstance(item.get("thread_id"), str) or not item["thread_id"]:
                    return False
                phase = "THREAD"
            elif kind == "turn.started" and phase == "THREAD":
                phase = "TURN"
            elif kind in ("item.started", "item.updated", "item.completed") and phase == "TURN":
                payload = item.get("item")
                ident = payload.get("id") if isinstance(payload, dict) else None
                if not isinstance(ident, str) or not ident:
                    return False
                if kind == "item.started":
                    if ident in seen:
                        return False
                    seen.add(ident)
                    active.add(ident)
                elif kind == "item.updated":
                    if ident not in active:
                        return False
                elif ident in active:
                    active.remove(ident)
                elif ident in seen:
                    return False
                else:
                    seen.add(ident)
            elif kind == "turn.completed" and phase == "TURN" and not active:
                phase = "COMPLETE"
            else:
                return False
    return phase == "COMPLETE"


def inspect_state(state):
    """Read-only inspection; never clear a CLI or native claim."""
    state = _path(state, True)
    path = state / "turns.sqlite3"
    if not path.is_file():
        return {"status": "NO_LEDGER", "native_execution_authorized": False}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        records = db.execute("SELECT id, started, status, pid FROM turns "
                             "WHERE status != 'CLI_COMPLETED' ORDER BY started").fetchall()
    rows = []
    for ident, started, status, pid in records:
        if not re.fullmatch(r"[0-9a-f]{32}", ident):
            raise ValueError("invalid turn identity in ledger")
        events = state / (ident + ".jsonl")
        rows.append({"turn_id": ident, "started": started, "status": status,
                     "pid": pid, "intent_exists": (state/(ident+".intent.json")).is_file(),
                     "spawn_receipt_exists": (state/(ident+".spawn.json")).is_file(),
                     "event_bytes": events.stat().st_size if events.is_file() else None,
                     "exit_receipt_exists": (state/(ident+".exit.json")).is_file(),
                     "native_state": "UNKNOWN"})
    return {"status": "INSPECTION_ONLY", "unresolved": rows,
            "native_execution_authorized": False}


def _write_receipt(path, payload):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _creation_identity(child):
    """On Windows query the owned process handle, never reopen a recycled PID."""
    if os.name != "nt" or not isinstance(child, subprocess.Popen):
        return None
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        query = kernel.GetProcessTimes
        query.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        query.restype = wintypes.BOOL
        creation, exit_time, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not query(int(child._handle), ctypes.byref(creation), ctypes.byref(exit_time),
                     ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None
        return {"source":"windows_owned_process_handle",
                "creation_filetime":(creation.dwHighDateTime << 32) | creation.dwLowDateTime}
    except (AttributeError, OSError, ValueError, TypeError):
        return None


def tick(config, popen=subprocess.Popen):
    exe, work, home, state, prompt, resume, skill, wait = validate(config)
    turn = uuid.uuid4().hex
    # Store one persistent active turn for this host/resource domain. Never use
    # TTL release. A crash or ambiguous CLI termination retains the record.
    with closing(sqlite3.connect(state/"turns.sqlite3", timeout=5)) as db:
        db.execute("CREATE TABLE IF NOT EXISTS turns (id TEXT PRIMARY KEY, "
                   "started REAL NOT NULL, status TEXT NOT NULL, pid INTEGER)")
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT id FROM turns WHERE status != 'CLI_COMPLETED' LIMIT 1").fetchone()
        if existing:
            db.rollback()
            return {"status":"PREVIOUS_TURN_UNRESOLVED","turn_id":existing[0],
                    "native_execution_authorized":False}
        db.execute("INSERT INTO turns VALUES (?, ?, 'RESERVED', NULL)",(turn,time.time()))
        db.commit()
        def mark(status, pid=None):
            db.execute("UPDATE turns SET status=?, pid=COALESCE(pid, ?) WHERE id=?",(status,pid,turn))
            db.commit()
            return {"status":status,"turn_id":turn,"native_execution_authorized":False}
        child = None
        try:
            # Pass the pinned task through stdin, never via shell interpolation.
            # Every turn is fresh; resume.md and the original task journals,
            # not the Desktop tool catalog, are the continuation state.
            original = prompt.read_bytes()
            if _sha(original) != config["task_prompt_sha256"]:
                raise ValueError("task prompt changed after validation")
            if _sha(skill.read_bytes()) != config["skill_sha256"]:
                raise ValueError("skill changed after validation")
            task = original.decode("utf-8")
            header = (
                "Paper2Simu scheduled CLI turn. Load the pinned canonical Skill at "
                + str(skill) + ". Read the existing resume record at " + str(resume)
                + " before any work. Preserve original IDs, deadlines, queue and output roots. "
                  "Verify actual MCP discovery, Executor permissions and existing native/history "
                  "admission before any mutation; never infer success from CLI completion. "
                  "No duplicate submission, permission changes or solver restarts.\n\n")
            inp = state/(turn+".prompt.txt")
            events = state/(turn+".jsonl")
            errors = state/(turn+".stderr.txt")
            with inp.open("x", encoding="utf-8") as h:
                h.write(header+task)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(home)
            argv = [str(exe), "--profile", config["profile"], "exec", "--json", "-"]
            _write_receipt(state/(turn+".intent.json"), {
                "turn_id": turn, "created_at": time.time(),
                "executable_sha256": _sha(exe.read_bytes()),
                "prompt_sha256": _sha(inp.read_bytes()),
                "phase": "SPAWN_INTENT", "native_state": "UNKNOWN"})
            with inp.open("rb") as stdin, events.open("xb") as stdout, errors.open("xb") as stderr:
                child = popen(argv, cwd=str(work), env=env, stdin=stdin,
                              stdout=stdout, stderr=stderr, shell=False)
                _write_receipt(state/(turn+".spawn.json"), {
                    "turn_id": turn, "pid": child.pid, "observed_at": time.time(),
                    "process_creation_identity": _creation_identity(child), "native_state": "UNKNOWN"})
                mark("RUNNING",child.pid)
                try:
                    code = child.wait(timeout=wait)
                except subprocess.TimeoutExpired:
                    # No process-tree kill; native children may still be alive.
                    return mark("CLI_TIMEOUT_UNRESOLVED",child.pid)
            _write_receipt(state/(turn+".exit.json"), {
                "turn_id":turn, "pid":child.pid, "exit_code":code,
                "observed_at":time.time(), "event_sha256":_sha(events.read_bytes()),
                "native_state":"UNKNOWN"})
            if code != 0 or not _completed(events):
                return mark("CLI_OUTCOME_UNRESOLVED",child.pid)
            return mark("CLI_COMPLETED",child.pid)
        except Exception:
            # Never retry an ambiguous launch automatically. Logs are private.
            return mark("CLI_OUTCOME_UNRESOLVED", getattr(child, "pid", None))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--check-config", action="store_true")
    p.add_argument("--inspect", action="store_true")
    args = p.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.inspect:
        print(json.dumps(inspect_state(config["state_dir"])))
        return 0
    if args.check_config:
        validate(config, admit=False)
        print(json.dumps({"status":"CONFIG_SHAPE_VALID_ONLY","native_execution_authorized":False}))
        return 0
    result = tick(config)
    print(json.dumps(result))
    return 0 if result["status"] == "CLI_COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
