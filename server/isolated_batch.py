"""Private launch transport for Runtime-admitted isolated jobs."""
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

PATCH_VERSION = "windows-isolated-deadline-3"


def read_json(path):
    for attempt in range(100):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object in {path.name}")
            return value
        except PermissionError:
            if attempt == 99:
                raise
            time.sleep(.005)


def batch_executable():
    root = Path(os.environ.get("COMSOL_ROOT", r"D:\Program Files\COMSOL\COMSOL64\Multiphysics"))
    if not root.is_absolute():
        raise ValueError("COMSOL_ROOT must specify an absolute installation path")
    executable = (root / "bin" / "win64" / "comsolbatch.exe").resolve()
    if not executable.is_file() or executable.name.lower() != "comsolbatch.exe":
        raise RuntimeError("Configured COMSOL batch executable missing")
    return executable


def platform_check():
    if os.name != "nt":
        raise RuntimeError("Isolated execution requires Windows")
    try:
        from .windows_job import ATOMIC_JOB_ASSIGNMENT
    except ImportError as exc:
        raise RuntimeError("Isolated execution requires pywin32") from exc
    if not ATOMIC_JOB_ASSIGNMENT:
        raise RuntimeError("Atomic Windows Job Object assignment unavailable")
    batch_executable()


def process_identity(pid):
    if os.name != "nt":
        raise NotImplementedError("Windows supervisor liveness unavailable")
    from .windows_job import process_identity as windows_process_identity
    return windows_process_identity(pid)


def _supervisor_liveness(result):
    pid = result.get("supervisor_pid")
    created = result.get("supervisor_created_at")
    result["supervisor_liveness"] = "UNVERIFIED"
    if type(pid) is int and pid > 0 and type(created) in (int, float) and math.isfinite(created):
        try:
            observed = process_identity(pid)
        except (ImportError, NotImplementedError, OSError):
            pass
        else:
            if observed == created:
                result["supervisor_liveness"] = "OBSERVED"
            else:
                result.update(
                    previous_status=result["status"], status="unknown_supervisor_lost",
                    supervisor_liveness="LOST", native_status="UNKNOWN", native_stop_verified=False,
                )
            return
    if result["status"] != "unknown_starting":
        result.update(
            previous_status=result["status"], status="unknown_supervisor_liveness",
            native_status="UNKNOWN", native_stop_verified=False,
        )


def command_for(request, folder):
    study = request["study_tag"]
    cores = request["cores"]
    if not isinstance(study, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", study):
        raise ValueError("Native study tag required")
    if type(cores) is not int or not 1 <= cores <= 4:
        raise ValueError("cores must be 1..4")
    input_file = (folder / "input.mph").resolve()
    if Path(request["input_file"]) != input_file or input_file.parent != folder:
        raise ValueError("Isolated batch requires the admitted input snapshot")
    return [
        str(batch_executable()), "-np", str(cores), "-inputfile", str(input_file),
        "-outputfile", str(folder / "result.mph"), "-study", study,
        "-batchlog", str(folder / "native.log"),
    ]


def status(folder):
    """Read durable observations. A missing or corrupt receipt is never stop proof."""
    folder = Path(folder).resolve()
    result = {
        "job_directory": str(folder),
        "patch_version": PATCH_VERSION,
        "native_stop_verified": False,
        "scientific_status": "NOT_EVALUATED",
    }
    try:
        request = read_json(folder / "request.json")
        result.update(
            operation_id=request["operation_id"],
            job_id=request["job_id"],
            deadline_at_unix=request["deadline_at_unix"],
        )
    except FileNotFoundError:
        return dict(result, status="unknown_incomplete_manifest" if folder.exists() else "unknown_operation")
    except (OSError, ValueError, KeyError):
        return dict(result, status="unknown_corrupt_manifest")
    try:
        state = read_json(folder / "state.json")
        if any(state[key] != result[key] for key in ("operation_id", "job_id", "deadline_at_unix")):
            raise ValueError("Isolated state identity mismatch")
        if not isinstance(state["status"], str):
            raise ValueError("Invalid isolated status")
        result.update(state)
    except FileNotFoundError:
        try:
            launch_receipt = read_json(folder / "launch.json")
            result["status"] = "unknown_launch" if launch_receipt.get("spawn_error") else "unknown_starting"
            for key in ("supervisor_pid", "supervisor_created_at"):
                if key in launch_receipt:
                    result[key] = launch_receipt[key]
        except FileNotFoundError:
            result["status"] = "unknown_starting"
        except (OSError, ValueError):
            result["status"] = "unknown_launch"
    except (OSError, ValueError, KeyError):
        result["status"] = "unknown_corrupt_state"
    if result["status"] in {"starting", "running", "stopping", "unknown_starting"}:
        _supervisor_liveness(result)
    return result


def launch(folder, request):
    """Persist the admitted envelope before spawning a detached supervisor."""
    from .isolated_worker import atomic_write

    folder = Path(folder).resolve()
    platform_check()
    payload = json.dumps(request, ensure_ascii=False, allow_nan=False, indent=2)
    manifest = folder / "request.json"
    try:
        with manifest.open("x", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if read_json(manifest) != request:
            raise ValueError("Operation conflicts with original launch request")
        return status(folder)

    try:
        with (folder / "supervisor.log").open("ab") as stream:
            process = subprocess.Popen(
                [sys.executable, "-m", "server.isolated_worker", str(folder)],
                cwd=str(Path(__file__).resolve().parents[1]),
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.STDOUT,
                close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
    except OSError as exc:
        atomic_write(folder / "launch.json", {"spawn_error": str(exc)})
        raise
    try:
        created = process_identity(process.pid)
    except (ImportError, NotImplementedError, OSError):
        created = None
    atomic_write(folder / "launch.json", {
        "supervisor_pid": process.pid, "supervisor_created_at": created, "spawned_at_unix": time.time(),
    })
    return status(folder)
