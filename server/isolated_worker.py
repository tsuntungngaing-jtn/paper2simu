"""Independent supervisor. No MPh, JVM queue, or MCP request lifetime dependency."""
import json
import os
from pathlib import Path
import sys
import time

from .windows_job import OwnedJob, process_identity


def atomic_write(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    # Windows readers may briefly hold a non-delete-sharing handle.
    for attempt in range(100):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 99:
                raise
            time.sleep(.005)


def supervise(folder):
    request = json.loads((folder/'request.json').read_text(encoding='utf-8'))
    deadline = request['deadline_at_unix']
    # Monotonic bound protects against wall clock moving backwards; UTC handles sleep/restart.
    mono_deadline = time.monotonic() + max(0, deadline-time.time())
    state = dict(operation_id=request['operation_id'], status='starting',
                 deadline_at_unix=deadline, supervisor_pid=os.getpid(),
                 supervisor_created_at=process_identity(os.getpid()),
                 submitted_at_unix=request['submitted_at_unix'],
                 max_active_processes=0, deadline_missed=False,
                 stop_requested_at_unix=None, native_stopped_at_unix=None)
    job = None
    try:
        if time.time() >= deadline-request['reserve_seconds']:
            state['status'] = 'expired_not_started'
            return
        job = OwnedJob(request['command'], folder)
        state.update(worker_pid=job.pid, worker_created_at=job.created_at,
                     status='running', native_started_at_unix=time.time())
        atomic_write(folder/'state.json', state)
        job.resume()
        terminating = False
        last_write = 0
        while True:
            active = job.active()
            now = time.time()
            state['active_processes'] = active
            state['max_active_processes'] = max(active, state['max_active_processes'])
            if active == 0:
                state.update(native_stopped_at_unix=now, exit_code=job.exit_code())
                state['status'] = ('deadline_terminated' if terminating else
                                   'process_completed' if state['exit_code'] == 0 else 'process_failed')
                state['deadline_missed'] = now > deadline
                return
            remaining = min(deadline-now, mono_deadline-time.monotonic())
            if not terminating and remaining <= request['reserve_seconds']:
                state['stop_requested_at_unix'] = now
                state['status'] = 'terminating'
                job.terminate()
                terminating = True
                atomic_write(folder/'state.json', state)
            if now-last_write >= 1:
                state['last_observed_at_unix'] = now
                state['deadline_missed'] = now > deadline
                atomic_write(folder/'state.json', state)
                last_write = now
            if terminating and now > deadline+10:
                state['status'] = 'unknown_stop_unconfirmed'
                state['deadline_missed'] = True
                return
            time.sleep(.02 if terminating else min(.1, max(.005, remaining/5)))
    except BaseException as exc:
        state.update(status='supervisor_error', error=f'{type(exc).__name__}: {exc}')
        if job:
            try:
                job.terminate()
                for _ in range(100):
                    if job.active() == 0:
                        state.update(active_processes=0, native_stopped_at_unix=time.time())
                        break
                    time.sleep(.02)
            except Exception as stop_error:
                state['stop_error'] = str(stop_error)
    finally:
        if job:
            job.close()
        atomic_write(folder/'state.json', state)


if __name__ == '__main__':
    supervise(Path(sys.argv[1]).resolve())
