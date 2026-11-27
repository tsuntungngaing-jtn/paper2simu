import hashlib
import json
import subprocess
from pathlib import Path
import pytest
from server.scheduled_cli import tick, validate, inspect_state, _completed


def config(tmp_path):
    for name in ("workspace","home","state"):
        (tmp_path/name).mkdir()
    work = tmp_path/"workspace"
    files = {"codex_executable":tmp_path/"codex.exe",
             "migration_receipt":tmp_path/"migration.txt",
             "task_prompt":work/"task.txt","resume_file":work/"resume.md",
             "skill_entry":tmp_path/"SKILL.md"}
    for path in files.values():
        path.write_text("approved",encoding="utf-8")
    s = {k:str(v) for k,v in files.items()}
    for key,target in (("migration_receipt","migration_receipt_sha256"),
                       ("task_prompt","task_prompt_sha256"),("skill_entry","skill_sha256")):
        s[target]=hashlib.sha256(files[key].read_bytes()).hexdigest()
    s.update(schema="paper2simu-scheduled-cli/1", workspace=str(work),
             codex_home=str(tmp_path/"home"), state_dir=str(tmp_path/"state"),
             profile="approved", observation_timeout_seconds=30,
             desktop_schedule_disabled=True, exclusive_writer_verified=True,
             provider_permissions_verified=True, migration_authorized=True)
    return s


def fake(mode, calls):
    class Child:
        pid = 123
        def wait(self, timeout):
            if mode == "exception":
                raise OSError("synthetic wait failure")
            if mode == "timeout":
                raise subprocess.TimeoutExpired("codex", timeout)
            return 1 if mode == "fail" else 0
    def launch(argv, **kw):
        assert kw["shell"] is False
        assert argv[-3:] == ["exec","--json","-"]
        assert b"existing resume record" in kw["stdin"].read()
        calls.append(argv)
        if mode == "ok":
            kw["stdout"].write(b'{"type":"thread.started","thread_id":"t"}\n{"type":"turn.started"}\n{"type":"turn.completed"}\n')
        if mode == "bad":
            kw["stdout"].write(b'{"type":"turn.failed"}\n')
        kw["stdout"].flush()
        return Child()
    return launch


def test_two_fresh_turns(tmp_path):
    c = config(tmp_path)
    calls = []
    for _ in range(2):
        result = tick(c, fake("ok",calls))
        assert result["status"] == "CLI_COMPLETED"
        assert not result["native_execution_authorized"]
    assert len(calls) == 2
    assert len(list(Path(c["state_dir"]).glob("*.jsonl"))) == 2


@pytest.mark.parametrize("mode",["fail","timeout","bad","empty"])
def test_ambiguous_turn_blocks_relaunch(tmp_path,mode):
    c = config(tmp_path)
    calls = []
    first = tick(c,fake(mode,calls))
    assert first["status"].endswith("UNRESOLVED")
    second = tick(c,fake("ok",calls))
    assert second["status"] == "PREVIOUS_TURN_UNRESOLVED"
    assert len(calls) == 1


def test_migration_and_hash_gates(tmp_path):
    c = config(tmp_path)
    with pytest.raises(ValueError):
        validate(dict(c,desktop_schedule_disabled=False))
    Path(c["task_prompt"]).write_text("changed")
    with pytest.raises(ValueError):
        validate(c)

def test_exception_keeps_pid_and_blocks(tmp_path):
    c = config(tmp_path)
    result = tick(c, fake("exception", []))
    row = inspect_state(c["state_dir"])["unresolved"][0]
    assert row["pid"] == 123 and row["spawn_receipt_exists"]
    assert row["turn_id"] == result["turn_id"]
    assert tick(c, fake("ok", []))["status"] == "PREVIOUS_TURN_UNRESOLVED"


@pytest.mark.parametrize("tail", [
    [{"type":"turn.completed"}],
    [{"type":"turn.started"},{"type":"item.started","item":{"id":"a"}},{"type":"turn.completed"}],
    [{"type":"turn.started"},{"type":"turn.completed"},{"type":"turn.started"}],
    [{"type":"turn.started"},{"type":"turn.completed"},{"type":"error"}],
])
def test_reject_invalid_lifecycle(tmp_path, tail):
    path = tmp_path/"turn.jsonl"
    events = [{"type":"thread.started","thread_id":"t"}] + tail
    path.write_text("".join(json.dumps(e)+"\n" for e in events))
    assert not _completed(path)


def test_config_shape_does_not_require_false_attestation(tmp_path):
    c = dict(config(tmp_path), migration_authorized=False)
    validate(c, admit=False)
    with pytest.raises(ValueError):
        validate(c)
