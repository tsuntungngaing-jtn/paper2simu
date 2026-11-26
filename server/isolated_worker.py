"""Independent supervisor with exclusive ownership of its native process tree."""
from contextlib import ExitStack, nullcontext
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from threading import Lock, Timer
import time

from .case_clock import CaseClock
from .isolated_batch import command_for, process_identity, read_json

POLL_SECONDS = .1
STOP_CONFIRM_SECONDS = 2.0


def atomic_write(path, value):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        for attempt in range(100):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt == 99:
                    raise
                time.sleep(.005)
    finally:
        temporary.unlink(missing_ok=True)


def supervise(
    folder, *, coordinator=None, job_factory=None, verifier=None,
    command_factory=command_for, identity=process_identity, input_guard_factory=None,
    wall=time.time, monotonic=time.monotonic, sleep=time.sleep
):
    folder = Path(folder).resolve()
    request = read_json(folder / "request.json")
    if coordinator is None:
        from .coordination import Coordinator
        coordinator = Coordinator(request["coordination_path"], request["resource_id"])
    if job_factory is None:
        from .windows_job import OwnedJob, lock_input
        job_factory = OwnedJob
        input_guard_factory = lock_input
    if input_guard_factory is None:
        input_guard_factory = nullcontext
    if verifier is None:
        from .isolated_runtime import verify_launch
        verifier = verify_launch

    job_id, owner = request["job_id"], request["owner"]
    case_id = request["case_id"]
    deadline = request["deadline_at_unix"]
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError("Isolated execution requires a finite frozen deadline")
    clock = CaseClock(request["case_clock_path"], wall)
    last_wall = wall()
    last_mono = monotonic()
    mono_deadline = last_mono + max(0, deadline - last_wall)
    pid = os.getpid()
    try:
        created = identity(pid)
    except (ImportError, NotImplementedError, OSError):
        created = None
    state = {
        "operation_id": request["operation_id"], "job_id": job_id, "case_id": case_id,
        "status": "starting", "deadline_at_unix": deadline,
        "supervisor_pid": pid, "supervisor_created_at": created,
        "native_status": "NOT_RUN", "scientific_status": "NOT_EVALUATED",
        "native_stop_verified": False, "stop_requested_at_unix": None,
        "native_stopped_at_unix": None,
    }
    state_path = folder / "state.json"

    def observe_clock():
        nonlocal last_wall, last_mono
        now, ticks = wall(), monotonic()
        if now < last_wall or ticks < last_mono:
            return "CLOCK_REGRESSION"
        last_wall, last_mono = now, ticks
        if now >= deadline or ticks >= mono_deadline:
            return "FROZEN_DEADLINE"
        try:
            case = clock.status(case_id)
        except Exception as exc:
            state["clock_error"] = repr(exc)
            return "CASE_CLOCK_UNAVAILABLE"
        state["case_phase"] = case["phase"]
        state["case_exit_reason"] = case["reason"]
        if (
            case["deadline_at_unix"] != request["case_deadline_at_unix"]
            or case["new_work_cutoff_unix"] != request["new_work_cutoff_unix"]
        ):
            return "CASE_CLOCK_BUDGET_CHANGED"
        if not case["active"] or case["phase"] != "OPEN":
            return case["reason"] or "CASE_CLOCK_EXIT"
        return None

    def check_claim(expected):
        actual = coordinator.get(job_id=job_id)
        if not actual or actual["released"] or actual["owner"] != owner or actual["state"] != expected:
            raise ValueError("Exclusive isolated claim unavailable")
        return actual

    def record_terminal_failure():
        if not request.get("output_root") or (
            not state.get("stop_reason") and state["status"] not in {
                "process_failed", "unknown_exit_code", "unknown_stop_unconfirmed",
            }
        ):
            return
        try:
            from .isolated_runtime import record_failure
            root = claim["request"]["output_root"]
            if root != request["output_root"]:
                raise ValueError("Recovery Memory output root differs from the exclusive claim")
            record_failure(root, claim, json.dumps(state, sort_keys=True))
        except Exception as exc:
            state["recovery_memory_error"] = repr(exc)
            try:
                atomic_write(state_path, state)
            except OSError as write_error:
                print(f"Unable to record Recovery Memory error: {write_error}", file=sys.stderr)

    create_authorized = False

    def pre_create():
        nonlocal create_authorized
        reason = observe_clock()
        if reason:
            state["stop_reason"] = reason
            raise RuntimeError(reason)
        check_claim("launching")
        verifier(request, folder)
        if wall() >= deadline or monotonic() >= mono_deadline:
            state["stop_reason"] = "FROZEN_DEADLINE"
            raise RuntimeError("FROZEN_DEADLINE")
        create_authorized = True

    # A second entry, including one after a supervisor crash, never starts native work.
    try:
        claim = check_claim("reserved")
        coordinator.transition(job_id, owner, "launching")
    except ValueError:
        return

    job = None
    input_guard = ExitStack()
    watchdog = None
    stop_lock = Lock()
    stop = {}
    phase = "launching"

    def stop_owned(reason):
        # Deadline termination is independent of SQLite and output I/O.
        with stop_lock:
            if stop:
                return
            stop.update(reason=reason, at=wall())
            try:
                job.terminate()
            except Exception as exc:
                stop["error"] = repr(exc)

    try:
        atomic_write(state_path, state)
        command = command_factory(request, folder)
        input_guard.enter_context(input_guard_factory(folder / "input.mph"))
        job = job_factory(command, folder, before_create=pre_create)
        timer = Timer(
            max(0, min(deadline - wall(), mono_deadline - monotonic())),
            lambda: stop_owned("FROZEN_DEADLINE"),
        )
        timer.daemon = True
        timer.start()
        watchdog = timer
        state.update(worker_pid=job.pid, worker_created_at=job.created_at)
        coordinator.transition(job_id, owner, "running", details={
            "worker_pid": job.pid, "worker_created_at": job.created_at
        })
        phase = "running"
        state.update(status="running", native_status="PROCESS_CREATED", native_created_at_unix=wall())
        atomic_write(state_path, state)
        reason = observe_clock()
        if not reason and not stop:
            verifier(request, folder)
            if wall() >= deadline or monotonic() >= mono_deadline:
                reason = "FROZEN_DEADLINE"
            elif not stop:
                job.resume()
                state.update(native_status="RUNNING", native_started_at_unix=wall())
        next_write = monotonic()
        while not reason and not stop:
            reason = observe_clock()
            if not reason:
                try:
                    check_claim("running")
                except Exception as exc:
                    state["coordination_error"] = repr(exc)
                    reason = "COORDINATION_UNAVAILABLE"
            if reason:
                break
            if job.active() == 0:
                break
            if monotonic() >= next_write:
                state["last_observed_at_unix"] = wall()
                atomic_write(state_path, state)
                next_write = monotonic() + 1
            sleep(min(POLL_SECONDS, max(0, mono_deadline - monotonic())))
    except BaseException as exc:
        state["error"] = repr(exc)
        reason = state.get("stop_reason", "SUPERVISOR_ERROR")

    if job is None:
        # Once authorized, CreateProcess may have run without returning an owned
        # handle to this monitor. Either way the consumed claim remains durable.
        status = "unknown_launch" if create_authorized else "launch_rejected"
        native_status = "UNKNOWN" if create_authorized else "NOT_RUN"
        state.update(status=status, stop_reason=reason, native_status=native_status)
        try:
            atomic_write(state_path, state)
        finally:
            input_guard.close()
        record_terminal_failure()
        return

    try:
        if reason:
            stop_owned(reason)
        if watchdog:
            watchdog.cancel()
            watchdog.join()
        reason = stop.get("reason")
        if reason:
            state.update(status="stopping", stop_reason=reason, stop_requested_at_unix=stop["at"])
            if "error" in stop:
                state["stop_error"] = stop["error"]
            if phase == "running":
                try:
                    coordinator.transition(job_id, owner, "stopping", details={"stop_reason": reason})
                    phase = "stopping"
                except Exception as exc:
                    state["coordination_error"] = repr(exc)
        try:
            for _ in range(int(STOP_CONFIRM_SECONDS / POLL_SECONDS) + 1):
                if job.active() == 0:
                    now = wall()
                    state.update(
                        native_stop_verified=True, native_stopped_at_unix=now, active_processes=0,
                        deadline_missed=now > deadline or monotonic() > mono_deadline,
                    )
                    break
                sleep(POLL_SECONDS)
        except Exception as exc:
            state["stop_observation_error"] = repr(exc)
        if state["native_stop_verified"]:
            state["native_status"] = "STOPPED"
            try:
                state["exit_code"] = job.exit_code()
            except Exception as exc:
                state["exit_code_error"] = repr(exc)
            if reason:
                state["status"] = "deadline_terminated" if reason == "FROZEN_DEADLINE" else "owned_stop_confirmed"
            elif "exit_code" in state:
                state["status"] = "process_completed" if state["exit_code"] == 0 else "process_failed"
            else:
                state["status"] = "unknown_exit_code"
        else:
            state.update(status="unknown_stop_unconfirmed", native_status="UNKNOWN")
    finally:
        try:
            job.close()
        except Exception as exc:
            state["close_error"] = repr(exc)
        finally:
            input_guard.close()

    atomic_write(state_path, state)
    if state["native_stop_verified"] and phase in {"running", "stopping"}:
        try:
            coordinator.release(job_id, owner, {
                "native_stopped": True, "evidence": {
                    "active_processes": 0, "observed_at_unix": state["native_stopped_at_unix"],
                    "worker_pid": job.pid, "worker_created_at": job.created_at,
                },
            })
        except Exception as exc:
            state["coordination_error"] = repr(exc)
            atomic_write(state_path, state)
    record_terminal_failure()


if __name__ == "__main__":
    supervise(Path(sys.argv[1]))
