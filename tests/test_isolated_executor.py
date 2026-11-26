from contextlib import contextmanager
import json
import os

import pytest

from server import isolated_batch
from server.case_clock import CaseClock


def test_status_is_platform_independent(tmp_path):
    assert isolated_batch.status(tmp_path)["status"] == "unknown_incomplete_manifest"


@pytest.mark.parametrize("observed, expected", [
    (100, "running"), (101, "unknown_supervisor_lost"), (None, "unknown_supervisor_lost"),
])
def test_running_status_checks_supervisor_birth_identity(tmp_path, monkeypatch, observed, expected):
    request = {"operation_id": "operation", "job_id": "job", "deadline_at_unix": 150}
    (tmp_path / "request.json").write_text(json.dumps(request), encoding="utf-8")
    state = dict(request, status="running", native_status="RUNNING", supervisor_pid=123,
                 supervisor_created_at=100)
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(isolated_batch, "process_identity", lambda pid: observed, raising=False)
    result = isolated_batch.status(tmp_path)
    assert result["status"] == expected
    if expected == "unknown_supervisor_lost":
        assert result["previous_status"] == "running"
        assert result["native_status"] == "UNKNOWN"
    assert result["native_stop_verified"] is False
    assert json.loads(path.read_text()) == state


def test_uncertain_spawn_retains_manifest_and_is_never_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(isolated_batch, "platform_check", lambda: None, raising=False)
    calls = []

    def spawn(*args, **kwargs):
        calls.append(args)
        raise OSError("spawn receipt unavailable")

    monkeypatch.setattr(isolated_batch.subprocess, "Popen", spawn)
    request = {"operation_id": "operation", "job_id": "job", "deadline_at_unix": 150}
    with pytest.raises(OSError, match="receipt unavailable"):
        isolated_batch.launch(tmp_path, request)
    assert json.loads((tmp_path / "request.json").read_text()) == request
    assert isolated_batch.launch(tmp_path, request)["status"] == "unknown_launch"
    assert len(calls) == 1


class Time:
    wall = 100
    monotonic = 0
    on_sleep = None

    def now(self):
        return self.wall

    def tick(self):
        return self.monotonic

    def sleep(self, seconds):
        self.wall += seconds
        self.monotonic += seconds
        if self.on_sleep:
            self.on_sleep()


class Claim:
    current = "reserved"
    proof = None
    unavailable = False
    request = {}

    def get(self, *, job_id):
        if self.unavailable:
            raise RuntimeError("coordination read failed")
        return {"state": self.current, "owner": "owner", "released": False, "request": self.request}

    def transition(self, job_id, owner, state, details=None):
        allowed = {"reserved": "launching", "launching": "running", "running": "stopping"}
        if allowed.get(self.current) != state:
            raise RuntimeError("claim already consumed")
        self.current = state

    def release(self, job_id, owner, proof):
        assert proof["native_stopped"] is True
        self.proof = proof


class OwnedJob:
    pid = 25
    created_at = 100
    terminated = False
    closed = False
    natural_exit = False
    active_error = False
    stop_confirmed = True
    resume_error = False

    def resume(self):
        if self.resume_error:
            raise OSError("resume failed")

    def active(self):
        if self.active_error:
            raise OSError("native query unavailable")
        return int(not (self.natural_exit or (self.terminated and self.stop_confirmed)))

    def terminate(self):
        self.terminated = True

    def exit_code(self):
        return 124 if self.terminated else 0

    def close(self):
        self.closed = True


@pytest.fixture
def supervisor(tmp_path):
    from server import isolated_worker

    clock = Time()
    claim = Claim()
    native = OwnedJob()
    calls = []
    clock_path = tmp_path / "clock.db"
    CaseClock(clock_path, clock.now).start("case", total=100, wrap=10, solve=50, stall=20)
    request = {
        "operation_id": "operation",
        "job_id": "job",
        "owner": "owner",
        "case_id": "case",
        "case_clock_path": str(clock_path),
        "case_deadline_at_unix": 200,
        "new_work_cutoff_unix": 190,
        "deadline_at_unix": 150,
    }
    (tmp_path / "request.json").write_text(json.dumps(request), encoding="utf-8")

    def factory(command, folder, before_create):
        before_create()
        calls.append(command)
        return native

    def run(**options):
        options.setdefault("verifier", lambda request, folder: None)
        isolated_worker.supervise(
            tmp_path,
            coordinator=claim,
            job_factory=factory,
            command_factory=lambda request, folder: ["controlled-double"],
            wall=clock.now,
            monotonic=clock.tick,
            sleep=clock.sleep,
            **options,
        )
        return isolated_batch.status(tmp_path)

    return run, clock, claim, native, calls, clock_path


def test_verified_native_exit_releases_and_restart_cannot_launch_again(supervisor):
    run, _, claim, native, calls, _ = supervisor
    native.natural_exit = True
    state = run()
    assert state["status"] == "process_completed"
    assert state["scientific_status"] == "NOT_EVALUATED"
    assert state["native_stop_verified"] is True
    assert claim.proof and native.closed
    assert run() == state
    assert len(calls) == 1


def test_stall_watch_does_not_refresh_progress(supervisor):
    run, time, claim, native, _, _ = supervisor
    state = run()
    assert state["stop_reason"] == "NO_VERIFIED_PROGRESS"
    assert time.wall < 121
    assert native.terminated and claim.proof


def test_duplicate_verified_progress_does_not_extend_stall(supervisor):
    run, time, _, native, _, path = supervisor
    evidence = "a" * 64
    seen = []

    def replay():
        seen.append(CaseClock(path, time.now).observe("case", evidence, time.now())["progress_accepted"])

    time.wall = 101
    replay()
    time.on_sleep = replay
    assert run()["stop_reason"] == "NO_VERIFIED_PROGRESS"
    assert seen[0] and not any(seen[1:])
    assert 121 <= time.wall < 122
    assert native.terminated


def test_frozen_deadline_stops_owned_job(supervisor, tmp_path):
    run, time, claim, native, _, path = supervisor
    time.on_sleep = lambda: CaseClock(path, time.now).observe(
        "case", f"{round(time.monotonic * 1000):064x}", time.now()
    )
    state = run()
    assert state["status"] == "deadline_terminated"
    assert state["stop_requested_at_unix"] <= 150
    assert native.terminated and claim.proof


def test_stop_unconfirmed_keeps_exclusive_claim(supervisor):
    run, _, claim, native, calls, _ = supervisor
    native.stop_confirmed = False
    state = run()
    assert state["status"] == "unknown_stop_unconfirmed"
    assert state["native_stop_verified"] is False
    assert claim.proof is None
    assert native.closed and native.terminated
    assert run() == state
    assert len(calls) == 1


@pytest.mark.parametrize("fault", ["clock_corruption", "wall_regression", "ledger_unavailable"])
def test_monitor_failure_stops_owned_job(supervisor, fault):
    run, time, claim, native, _, clock_path = supervisor

    def fail():
        time.on_sleep = None
        if fault == "clock_corruption":
            clock_path.write_bytes(b"not a database")
        elif fault == "wall_regression":
            time.wall -= 10
        else:
            claim.unavailable = True

    time.on_sleep = fail
    state = run()
    assert native.terminated and native.closed
    assert state["native_stop_verified"] is True
    assert state["stop_reason"] in {
        "CASE_CLOCK_UNAVAILABLE", "CLOCK_REGRESSION", "COORDINATION_UNAVAILABLE"
    }


def test_resume_failure_stops_owned_job(supervisor):
    run, _, claim, native, _, _ = supervisor
    native.resume_error = True
    state = run()
    assert state["stop_reason"] == "SUPERVISOR_ERROR"
    assert state["native_stop_verified"] is True
    assert native.terminated and native.closed and claim.proof


def test_crash_after_consuming_launch_cannot_restart(supervisor):
    run, _, claim, _, calls, _ = supervisor
    claim.current = "launching"
    assert run()["status"] == "unknown_starting"
    assert not calls and claim.proof is None


def test_independent_deadline_guard_terminates_during_blocked_monitor(supervisor, monkeypatch):
    from server import isolated_worker

    run, time, claim, native, _, _ = supervisor
    timers = []

    class Timer:
        def __init__(self, seconds, callback):
            self.seconds = seconds
            self.callback = callback

        def start(self):
            timers.append(self)

        def cancel(self):
            pass

        def join(self):
            pass

    monkeypatch.setattr(isolated_worker, "Timer", Timer, raising=False)
    original_get = claim.get

    def blocked_get(*, job_id):
        snapshot = original_get(job_id=job_id)
        if snapshot["state"] == "running" and not native.terminated:
            assert timers[0].seconds == 50
            time.wall = 150
            time.monotonic = 50
            timers[0].callback()
            assert native.terminated
        return snapshot

    claim.get = blocked_get
    assert run()["status"] == "deadline_terminated"


def test_supervisor_state_persistence_failure_stops_owned_job(supervisor, monkeypatch):
    from server import isolated_worker

    run, _, claim, native, _, _ = supervisor
    original_write = isolated_worker.atomic_write

    def fail_once(path, state):
        if state.get("native_status") == "RUNNING":
            raise OSError("output volume unavailable")
        original_write(path, state)

    monkeypatch.setattr(isolated_worker, "atomic_write", fail_once)
    state = run()
    assert state["stop_reason"] == "SUPERVISOR_ERROR"
    assert state["native_stop_verified"] is True
    assert native.terminated and native.closed and claim.proof


def test_expired_case_before_create_is_recorded_as_not_run(supervisor):
    run, time, claim, _, calls, _ = supervisor
    time.wall = 150
    state = run()
    assert state["status"] == "launch_rejected"
    assert state["native_status"] == "NOT_RUN"
    assert state["stop_reason"] == "FROZEN_DEADLINE"
    assert not calls and claim.proof is None


def test_job_accounting_failure_cannot_establish_stop_proof(supervisor):
    run, _, claim, native, _, _ = supervisor
    native.active_error = True
    state = run()
    assert state["status"] == "unknown_stop_unconfirmed"
    assert state["native_stop_verified"] is False
    assert native.terminated and native.closed and claim.proof is None


def test_snapshot_lock_survives_verification_through_native_close(supervisor):
    run, _, claim, native, _, _ = supervisor
    events = []
    native.natural_exit = True

    @contextmanager
    def guard(path):
        assert path.name == "input.mph"
        events.append("locked")
        try:
            yield
        finally:
            assert native.closed
            events.append("released")

    def verify(request, folder):
        assert events[0] == "locked"
        assert not native.closed
        events.append("verified")

    assert run(verifier=verify, input_guard_factory=guard)["status"] == "process_completed"
    assert events == ["locked", "verified", "verified", "released"]
    assert claim.proof


def test_expired_review_while_suspended_prevents_resume(supervisor):
    run, _, claim, native, _, _ = supervisor
    calls = []

    def verify(request, folder):
        calls.append(claim.current)
        if claim.current == "running":
            raise ValueError("verification expired while suspended")

    def resume():
        pytest.fail("expired review must block native resume")

    native.resume = resume
    state = run(verifier=verify)
    assert state["status"] == "owned_stop_confirmed"
    assert calls == ["launching", "running"]
    assert native.terminated and native.closed


@pytest.mark.skipif(os.name != "nt", reason="Windows file share modes required")
def test_windows_snapshot_lock_rejects_write_and_replace(tmp_path):
    pytest.importorskip("win32file")
    from server.windows_job import lock_input

    input_file = tmp_path / "input.mph"
    replacement = tmp_path / "replacement.mph"
    input_file.write_bytes(b"approved snapshot")
    replacement.write_bytes(b"replacement")
    with lock_input(input_file):
        assert input_file.read_bytes() == b"approved snapshot"
        with pytest.raises(PermissionError):
            input_file.write_bytes(b"mutated")
        with pytest.raises(PermissionError):
            replacement.replace(input_file)
    replacement.replace(input_file)
    assert input_file.read_bytes() == b"replacement"


@pytest.mark.skipif(os.name != "nt", reason="Windows process identity required")
def test_windows_process_birth_identity_reads_live_current_process():
    pytest.importorskip("win32api")
    created = isolated_batch.process_identity(os.getpid())
    assert created > 0
    assert isolated_batch.process_identity(os.getpid()) == created


@pytest.mark.parametrize("record_error", [False, True])
def test_worker_records_owned_failure_without_operator_poll(supervisor, tmp_path, monkeypatch, record_error):
    from server import isolated_runtime

    run, _, claim, _, _, _ = supervisor
    path = tmp_path / "request.json"
    request = json.loads(path.read_text(encoding="utf-8"))
    request["output_root"] = str(tmp_path)
    path.write_text(json.dumps(request), encoding="utf-8")
    claim.request = {"output_root": str(tmp_path)}
    records = []

    def record(output_root, row, observation):
        assert claim.proof
        assert json.loads((tmp_path / "state.json").read_text())["status"] == "owned_stop_confirmed"
        records.append((output_root, row["request"], json.loads(observation)["stop_reason"]))
        if record_error:
            raise OSError("recovery memory unavailable")

    monkeypatch.setattr(isolated_runtime, "record_failure", record)
    state = run()
    assert records == [(str(tmp_path), claim.request, "NO_VERIFIED_PROGRESS")]
    assert state["native_stop_verified"]
    assert ("recovery_memory_error" in state) is record_error
