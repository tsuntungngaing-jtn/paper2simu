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


def validate(config):
    if config.get("schema") != "paper2simu-scheduled-cli/1":
        raise ValueError("unsupported config")
    for k in ("desktop_schedule_disabled", "exclusive_writer_verified",
              "provider_permissions_verified", "migration_authorized"):
        if config.get(k) is not True:
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
    """Strictly a CLI lifecycle receipt, not native evidence."""
    thread = None
    complete = 0
    with events.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                return False
            kind = item.get("type")
            if kind in ("error", "turn.failed"):
                return False
            if kind == "thread.started":
                if thread is not None or not isinstance(item.get("thread_id"), str) or not item["thread_id"]:
                    return False
                thread = item["thread_id"]
            elif kind == "turn.completed":
                if thread is None:
                    return False
                complete += 1
    return bool(thread and complete == 1)


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
            db.execute("UPDATE turns SET status=?, pid=? WHERE id=?",(status,pid,turn))
            db.commit()
            return {"status":status,"turn_id":turn,"native_execution_authorized":False}
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
            with inp.open("rb") as stdin, events.open("xb") as stdout, errors.open("xb") as stderr:
                child = popen(argv, cwd=str(work), env=env, stdin=stdin,
                              stdout=stdout, stderr=stderr, shell=False)
                mark("RUNNING",child.pid)
                try:
                    code = child.wait(timeout=wait)
                except subprocess.TimeoutExpired:
                    # No process-tree kill; native children may still be alive.
                    return mark("CLI_TIMEOUT_UNRESOLVED",child.pid)
            if code != 0 or not _completed(events):
                return mark("CLI_OUTCOME_UNRESOLVED",child.pid)
            return mark("CLI_COMPLETED",child.pid)
        except Exception:
            # Never retry an ambiguous launch automatically. Logs are private.
            return mark("CLI_OUTCOME_UNRESOLVED")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--check-config", action="store_true")
    args = p.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.check_config:
        validate(config)
        print(json.dumps({"status":"CONFIG_SHAPE_VALID_ONLY","native_execution_authorized":False}))
        return 0
    result = tick(config)
    print(json.dumps(result))
    return 0 if result["status"] == "CLI_COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
