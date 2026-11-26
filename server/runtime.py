"""One JVM thread, non-destructive sessions, and inspectable background jobs.

This runtime is an automation service, not a Python or COMSOL security sandbox.
Only expose it to the trusted user who owns the COMSOL installation.
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from . import __version__
from .submission_window import latest_renewal
from .case_clock import CaseClock, admission as case_clock_admission
from . import shared_guard
from .shared_guard import native_entry

_RESOURCES = Path(__file__).resolve().parent / 'resources'
ROOT = _RESOURCES if (_RESOURCES / 'vendor').is_dir() else Path(__file__).resolve().parents[1]
TERMINAL_JOB_STATES = {"completed", "failed", "cancelled"}


def inside(root: Path, value: str | Path) -> Path:
    """Resolve a path and reject traversal, including symlink escapes."""
    root = root.resolve()
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path must remain within {root}")
    return resolved


def jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return jsonable(value.tolist())
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class Runtime:
    def __init__(self, root: Path = ROOT, output_root: Path | None = None):
        self.root = root
        self.output_root = Path(output_root or os.getenv("COMSOL_OUTPUT_ROOT", str(Path.home() / "comsol-automatic-output"))).resolve()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="comsol-jvm")
        self.manager = None
        self.server = None
        self.client_handle = None
        self.last_endpoint = None
        self.connection_lost = False
        self.needs_model_rebind = False
        self.tracked_tags = {}
        self.jobs: dict[str, dict] = {}
        self.futures = {}
        self.latest_study_job = None
        self.lock = threading.Lock()
        self.desktop_process = None
        self.desktop_endpoint = None
        self.runtime_id = uuid4().hex
        self.started_at = time.monotonic()
        self.started_at_unix = time.time()
        self.transport = "unknown"
        self.journal_errors = []
        self.operations: dict[str, str] = {}
        self.ambiguous_operations: set[str] = set()
        digest = hashlib.sha256()
        for source in sorted(Path(__file__).resolve().parent.glob("*.py")):
            digest.update(source.name.encode() + b"\0" + source.read_bytes() + b"\0")
        self.runtime_source_sha256 = digest.hexdigest()
        self._restore_jobs()
        self.case_clock_path = self.output_root / 'case-clock.sqlite3'
        # A deployed task may require the clock even before a case is created.
        self.case_clock_required = os.getenv('PAPER2SIMU_REQUIRE_CASE_CLOCK') == '1'
        shared_guard.configure(self)

    def submit_isolated(self, input_file, study_tag, operation_id, deadline_at_unix,
                        task_case_id, verification, cores=4):
        from .isolated_runtime import submit
        return submit(self, input_file, study_tag, operation_id, deadline_at_unix,
                      task_case_id, verification, cores)

    def isolated_status(self, operation_id=None, job_id=None):
        from .isolated_runtime import status
        return status(self, operation_id=operation_id, job_id=job_id)

    def _restore_jobs(self):
        for path in (self.output_root / 'job-manifests').glob('*.json'):
            try:
                job = json.loads(path.read_text(encoding='utf-8'))
                if job['job_id'] != path.stem:
                    raise ValueError('Job identity mismatch')
                operation_id = job.get('operation_id')
                if operation_id and operation_id in self.operations:
                    self.ambiguous_operations.add(operation_id)
                job['historical'] = True
                if job['status'] not in TERMINAL_JOB_STATES and job['status'] != 'recovery_pending':
                    job['previous_status'] = job['status']
                    job['status'] = 'recovery_pending'
                job['recovery_note'] = 'Historical metadata only; verify server and solution identity. Never resubmit automatically.'
                self.jobs[job['job_id']] = job
                if operation_id:
                    self.operations[operation_id] = job['job_id']
            except Exception as error:
                self.journal_errors.append({'path':str(path), 'error':str(error)})

    def _persist(self, job_id):
        # Called with self.lock held. Atomic replacement prevents torn manifests.
        directory = inside(self.output_root, 'job-manifests')
        directory.mkdir(parents=True, exist_ok=True)
        path = inside(directory, job_id + '.json')
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.jobs[job_id], default=str, indent=2), encoding='utf-8')
        temporary.replace(path)

    def _finished(self, job_id):
        with self.lock:
            try:
                job = self.jobs[job_id]
                if self.futures.get(job_id) and self.futures[job_id].cancelled() and job.get('coordination_job_id'):
                    c = shared_guard.coordinator(self)
                    c.release(job['coordination_job_id'], self.runtime_id,
                              {'never_started': True, 'evidence': 'Future cancelled before worker entry'})
                self._persist(job_id)
            except Exception as error:
                self.jobs[job_id]['persistence_error'] = str(error)

    def queue_status(self):
        with self.lock:
            active = self._active_jobs()
            clock_required = self.case_clock_required or self.case_clock_path.exists()
            return {'success':True, 'busy':bool(active), 'active_jobs':active,
                    'metadata_nonblocking':True, 'java_reads_require_idle':True,
                    'case_clock_required':clock_required,
                    'recovery_pending':[j['job_id'] for j in self.jobs.values() if j['status']=='recovery_pending'],
                    'journal_errors':list(self.journal_errors),
                    'submission_budget':self._submission_budget(len(active)), **self.runtime_info()}

    def _active_jobs(self):
        return [job['job_id'] for job in self.jobs.values() if job['status'] in ('queued', 'running')]

    def runtime_info(self):
        return {'runtime_id': self.runtime_id, 'paper2simu_version': __version__,
                'runtime_root': str(self.root), 'python_executable': sys.executable,
                'output_root': str(self.output_root), 'runtime_started_at_unix': self.started_at_unix,
                'runtime_module_path': str(Path(__file__).resolve()),
                'runtime_source_sha256': self.runtime_source_sha256,
                'transport': self.transport, 'provider': 'paper2simu-comsol-mcp',
                'python_version': platform.python_version(),
                'os': platform.system(), 'os_release': platform.release()}

    def execution_capabilities(self):
        # This probe describes the running connector and never enters the JVM.
        observations = {
            'poll_metadata': ('supported', 'Python job journal, independent of the JVM executor'),
            'queued_cancel': ('supported', 'Cancels a future only before it starts'),
            'running_stop': ('unsupported', 'No independent running-stop path in this MCP'),
            'deadline_enforcement': ('unsupported', 'Shared JVM worker has no isolated deadline controller'),
            'desktop_identity': ('unsupported', 'Desktop display identity needs operator confirmation'),
        }
        for name in ('read_model', 'build_model', 'verify_effective_settings', 'solve',
                     'native_log', 'checkpoint_reopen'):
            observations[name] = ('unknown', 'Requires an observation from the selected native session')
        return {
            name: {'state': state, 'evidence': evidence, 'run_mode': 'mphserver',
                   'provider_version': __version__, 'observed_at_unix': time.time()}
            for name, (state, evidence) in observations.items()
        }

    def _submission_request_error(self, operation_id, require_hard_deadline):
        if self.tool_role != 'operator':
            return shared_guard.blocked('ROLE_FORBIDDEN')
        if operation_id is not None and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", operation_id):
            return {'success': False, 'status': 'BLOCKED', 'error': 'INVALID_OPERATION_ID'}
        if require_hard_deadline:
            return {'success': False, 'status': 'BLOCKED', 'error': 'HARD_DEADLINE_UNSUPPORTED',
                    'runtime_id': self.runtime_id, 'capability': self.execution_capabilities()['deadline_enforcement'],
                    'next_step': 'Continue independent modeling work or use a runtime with verified deadline enforcement.'}
        return None

    async def call(self, function, *args, **kwargs):
        if self.tool_role != 'operator':
            return shared_guard.blocked('ROLE_FORBIDDEN')
        with self.lock:
            if self._active_jobs():
                return {'success':False, 'status':'BLOCKED', 'error':'JVM_BUSY',
                        'retryable':True, 'next_step':'Poll job metadata; do not queue repair calls behind a solve.'}
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor,
            functools.partial(shared_guard.invoke, self, function, *args, **kwargs))

    def _submission_budget(self, active: int, coordinated_jobs=None) -> dict:
        # Call with self.lock held so status and admission use a consistent job count.
        limits = {}
        invalid = []
        for key, variable, parse, default in (
            ('active_jobs', 'COMSOL_MAX_ACTIVE_JOBS', int, '8'),
            ('submissions', 'COMSOL_MAX_SUBMISSIONS', int, '100'),
            ('window_seconds', 'COMSOL_SUBMISSION_WINDOW_SECONDS', float, '86400'),
        ):
            try:
                value = parse(os.getenv(variable, default))
                if value <= 0 or (parse is float and not math.isfinite(value)):
                    raise ValueError
                limits[key] = value
            except ValueError:
                invalid.append(variable)

        total = len(self.jobs) + len(self.journal_errors)
        if self.coordination_path or self.resource_id:
            try:
                rows = (shared_guard.coordinator(self).inspect()
                        if coordinated_jobs is None else coordinated_jobs)
                rows = [r for r in rows if r['kind'] in {'shared_job', 'isolated'}]
                represented = {j.get('coordination_job_id') for j in self.jobs.values()}
                total += sum(r['job_id'] not in represented for r in rows)
                active = max(active, sum(not r['released'] for r in rows))
            except (ValueError, OSError):
                invalid.append('PAPER2SIMU_COORDINATION_DB')
        budget = {'can_submit': False, 'active_jobs': {'used': active}, 'submissions': {'used': total},
                  'invalid_settings': invalid, 'block_reasons': []}
        if invalid:
            budget['block_reasons'] = ['INVALID_SUBMISSION_BUDGET']
            return budget

        now = time.monotonic()
        started_at, grant = latest_renewal(self.output_root, self.runtime_id, self.started_at, now)
        duration = limits['window_seconds']
        elapsed = now - started_at
        remaining = max(0.0, duration - elapsed)
        warning_seconds = min(3600.0, duration / 10)
        for key, used, code in (('active_jobs', active, 'ACTIVE_JOB_LIMIT_REACHED'),
                                ('submissions', total, 'TOTAL_SUBMISSION_LIMIT_REACHED')):
            limit = limits[key]
            budget[key].update(limit=limit, remaining=max(0, limit - used))
            if used >= limit:
                budget['block_reasons'].append(code)
        if remaining == 0:
            budget['block_reasons'].append('SUBMISSION_WINDOW_EXPIRED')
        budget.update(can_submit=not budget['block_reasons'], window={
            'duration_seconds': duration, 'elapsed_seconds': elapsed, 'remaining_seconds': remaining,
            'expires_at_unix': time.time() + duration - elapsed,
            'expires_soon': 0 < remaining <= warning_seconds, 'warning_seconds': warning_seconds,
            'renewal_grant_id': grant,
        })
        return budget

    def _queue_job(self, job: dict, run, *args) -> dict:
        job_id = job['job_id']
        operation_id = job.get('operation_id')
        with self.lock:
            if operation_id in self.ambiguous_operations:
                return {'success': False, 'status': 'BLOCKED', 'error': 'OPERATION_ID_AMBIGUOUS',
                        'operation_id': operation_id}
            if operation_id and operation_id in self.operations:
                original = self.jobs[self.operations[operation_id]]
                if original.get('request') != job.get('request') or original.get('task_case_id') != job.get('task_case_id'):
                    return {'success': False, 'status': 'BLOCKED', 'error': 'OPERATION_ID_CONFLICT',
                            'job_id': original['job_id'], 'operation_id': operation_id}
                return {'success': True, 'job_id': original['job_id'], 'status': original['status'],
                        'operation_id': operation_id, 'existing_job': True, 'poll_tool': 'comsol_job_status'}
            if self.journal_errors:
                return {'success': False, 'status': 'BLOCKED', 'error': 'OPERATION_JOURNAL_UNCERTAIN',
                        'operation_id': operation_id, 'next_step': 'Reconcile the unreadable job manifests first.'}
            budget = self._submission_budget(len(self._active_jobs()))
            if not budget['can_submit']:
                reasons = budget['block_reasons']
                actions = {
                    'ACTIVE_JOB_LIMIT_REACHED': 'Poll active jobs until a slot is available.',
                    'TOTAL_SUBMISSION_LIMIT_REACHED': 'Review the cumulative cap with the operator and keep the job journal.',
                    'SUBMISSION_WINDOW_EXPIRED': 'Save the checkpoint and obtain a local renewal grant for this runtime.',
                    'INVALID_SUBMISSION_BUDGET': 'Correct the listed connector environment settings and reload the runtime.',
                }
                return {'success': False, 'status': 'BLOCKED',
                        'error': 'Invalid submission budget' if budget['invalid_settings'] else 'SUBMISSION_BUDGET_EXHAUSTED',
                        'reason': reasons[0], 'submission_budget': budget, 'runtime_id': self.runtime_id,
                        'retryable': reasons == ['ACTIVE_JOB_LIMIT_REACHED'], 'inflight_cancelled': False,
                        'next_step': ' '.join(actions[reason] for reason in reasons)}
            pending = [j['job_id'] for j in self.jobs.values() if j['status'] == 'recovery_pending']
            if pending:
                return {'success': False, 'status': 'BLOCKED', 'error': 'UNRESOLVED_RECOVERY_JOBS',
                        'recovery_pending': pending, 'next_step': 'Reconcile original native jobs with the authorized local operator before new work.'}
            try:
                gate = shared_guard.case_admission(self, job.get('task_case_id'))
                if not gate['allowed']:
                    return dict(gate, success=False, status='BLOCKED')
            except (ValueError, OSError) as error:
                return shared_guard.blocked(error)
            try:
                request = {'request': job.get('request'), 'task_case_id': job.get('task_case_id'),
                           'output_root': str(self.output_root), 'native_job_id': job_id}
                c = shared_guard.coordinator(self)
                prior = c.get(operation_id=operation_id) if c and operation_id else None
                if prior:
                    if prior['kind'] != 'shared_job' or any(prior['request'].get(k) != request[k]
                        for k in ('request', 'task_case_id', 'output_root')):
                        return shared_guard.blocked('OPERATION_ID_CONFLICT')
                    return {'success':True, 'job_id':prior['request']['native_job_id'],
                            'status':prior['state'], 'existing_job':True, 'poll_tool':'comsol_job_status'}
                claim = shared_guard.reserve(self, operation_id or 'job-'+job_id, request, 'shared_job')
                if claim and claim.get('existing'):
                    return {'success': True, 'job_id': claim['job_id'], 'status': claim['state'],
                            'operation_id': operation_id, 'existing_job': True,
                            'poll_tool': 'comsol_job_status'}
                if claim:
                    job['coordination_job_id'] = claim['job_id']
            except (OSError, ValueError) as error:
                return shared_guard.blocked(error)
            self.jobs[job_id] = job
            try:
                self._persist(job_id)
            except (OSError, ValueError) as error:
                del self.jobs[job_id]
                return {'success': False, 'status': 'BLOCKED', 'error': 'JOB_JOURNAL_WRITE_FAILED',
                        'detail': str(error), 'next_step': 'Restore write access to the output root before submitting.'}
            if operation_id:
                self.operations[operation_id] = job_id
            try:
                def coordinated_run():
                    def execute():
                        gate = shared_guard.case_admission(self, job.get('task_case_id'))
                        if not gate['allowed']:
                            with self.lock:
                                self.jobs[job_id].update(status='recovery_pending', clock_error=gate)
                            return {'success': False}
                        run(*args)
                        return {'success': self.jobs[job_id]['status'] == 'completed'}
                    result = shared_guard.invoke(self, execute, claim=claim)
                    if isinstance(result, dict) and result.get('status') == 'BLOCKED':
                        with self.lock:
                            self.jobs[job_id].update(status='recovery_pending', coordination_error=result)
                future = self.executor.submit(coordinated_run)
            except RuntimeError as error:
                job.update(status='failed', error={'type': type(error).__name__, 'message': str(error)},
                           completed_at=time.time())
                try:
                    self._persist(job_id)
                except (OSError, ValueError) as persist_error:
                    job['persistence_error'] = str(persist_error)
                return {'success': False, 'status': 'failed', 'error': 'JOB_SCHEDULING_FAILED', 'job_id': job_id}
            self.futures[job_id] = future
            if job.get('kind') == 'study':
                self.latest_study_job = job_id
        future.add_done_callback(lambda _: self._finished(job_id))
        return {'success': True, 'job_id': job_id, 'status': 'queued', 'poll_tool': 'comsol_job_status',
                **({'operation_id': operation_id} if operation_id else {})}

    def installation_root(self, version: str | None = None) -> Path:
        import mph
        selected = version or (self.manager.client.version if self.manager and self.manager.is_connected
                               else os.getenv("COMSOL_VERSION") or None)
        discovered = Path(mph.discovery.backend(selected)["root"]).resolve()
        configured = os.getenv("COMSOL_ROOT")
        if configured:
            path = Path(configured).resolve()
            if not (path / "applications").is_dir():
                raise ValueError("COMSOL_ROOT must be the Multiphysics directory containing applications")
            if path != discovered:
                raise ValueError("COMSOL_ROOT does not match the installation selected by MPh discovery. Set COMSOL_VERSION to the matching installed release or repair COMSOL registration; COMSOL_ROOT alone does not select the JVM/server executable.")
            return path
        return discovered

    def doctor(self) -> dict:
        info = {"success": True, "python": sys.version.split()[0], **self.runtime_info(),
                "code_execution_enabled": os.getenv("COMSOL_ALLOW_CODE") == "1",
                "transport_warning": "Trusted single-user automation; not a sandbox or multi-tenant service."}
        for name in ("mph", "mcp", "JPype1"):
            try:
                info[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                info[name] = "missing"
                info["success"] = False
        try:
            root = self.installation_root()
            info.update(comsol_root=str(root), application_library=(root / "applications").is_dir())
        except Exception as error:
            info.update(success=False, error=str(error))
        info["license_checked"] = False
        info["license_note"] = "Installation discovery does not prove a COMSOL or add-on license is available."
        return info

    def bind_manager(self, manager):
        self.manager = manager
        # Patch the vendored instance, preserving its model CRUD semantics. Never
        # call Client.clear(): other clients may be viewing their own models.
        manager.start = self.start
        manager.connect = self.connect
        manager.disconnect = self.disconnect
        manager.get_status = self.status
        if hasattr(manager, "add_model"):
            add_model = manager.add_model

            def track_model(model):
                tag = str(model.java.tag())
                name = add_model(model)
                self.tracked_tags[name] = tag
                return name

            manager.add_model = track_model
        if hasattr(manager, "remove_model"):
            remove_model = manager.remove_model

            def untrack_model(name):
                removed = remove_model(name)
                if removed:
                    self.tracked_tags.pop(name, None)
                return removed

            manager.remove_model = untrack_model

    @staticmethod
    def _connection_error_state(error):
        if isinstance(error, (ConnectionError, EOFError)):
            return 'dead'
        message = str(error).lower()
        if any(reason in message for reason in ('server is busy', 'server busy', 'server is currently busy')):
            return 'busy'
        if any(reason in message for reason in (
            'not connected to a server', 'connection reset', 'connection refused', 'broken pipe',
            'socket is closed', 'java.io.eofexception',
        )):
            return 'dead'
        return 'unknown'

    def _forget_dead_connection(self):
        # MPh 1.4 only clears these fields if its Java disconnect call returns.
        # Use Python metadata after a definite connection loss and retain tags.
        self.manager._client = None
        self.manager._models = {}
        self.connection_lost = True
        if self.client_handle is not None:
            self.client_handle.host = None
            self.client_handle.port = None

    def _connection_probe(self):
        if not self.manager or not self.manager.is_connected:
            return 'detached', None
        try:
            available = {str(tag) for tag in self.manager.client.java.tags()}
            if self.needs_model_rebind:
                import mph
                current = self.manager.current_model
                refreshed = {name: mph.Model(self.client_handle.java.model(tag))
                             for name, tag in self.tracked_tags.items() if tag in available}
                self.manager._models = refreshed
                self.manager._current_model = current if current in refreshed else next(iter(refreshed), None)
                self.tracked_tags = {name: self.tracked_tags[name] for name in refreshed}
                self.needs_model_rebind = False
        except Exception as error:
            state = self._connection_error_state(error)
            if state == 'dead':
                self._forget_dead_connection()
            return state, str(error)
        return 'connected', None

    @native_entry
    def prepare_stdio_client(self):
        """Initialize only the JVM before MCP starts its blocking stdin reader.

        On Windows, HotSpot changes CRT stdio modes during startup; doing that
        after another thread starts reading stdin can deadlock. host=None uses
        COMSOL's client API without starting a server or checking out a model
        license. All later API calls still use this same executor thread.
        """
        import mph
        self.installation_root()
        if self.client_handle is None:
            self.client_handle = mph.Client(host=None, version=os.getenv("COMSOL_VERSION") or None)

    def _attach(self, port: int, host: str, version: str | None = None):
        import mph
        if self.client_handle is None:
            self.client_handle = mph.Client(host=None, version=version)
        self.client_handle.connect(port=port, host=host)
        self.manager._client = self.client_handle
        self.manager._models = {}
        self.needs_model_rebind = bool(self.tracked_tags)
        if self.last_endpoint is not None and self.last_endpoint != (host, port):
            # Old Java proxies must not be used against a different server. This
            # clears only Python tracking, never COMSOL's model collection.
            self.manager._current_model = None
            self.tracked_tags = {}
            self.needs_model_rebind = False
        self.last_endpoint = (host, port)
        self.connection_lost = False
        try:
            import jpype
            util = jpype.JClass("com.comsol.model.util.ModelUtil")
            util.setServerBusyHandler(jpype.JClass("com.comsol.model.util.ServerBusyHandler")(jpype.JInt(120000)))
        except Exception:
            pass  # Older releases may lack the busy-handler overload.

    @native_entry
    def start(self, cores=None, version=None, products=None) -> dict:
        if self.manager.is_connected or self.connection_lost:
            status = self.status()
            if status['connected'] is True:
                return dict(status, success=True, message="Reused session; existing models preserved.")
            return dict(status, success=False, error="Use comsol_connect with a verified existing endpoint; this runtime will not replace it.")
        import mph
        try:
            self.installation_root(version)
            requested_version = version or os.getenv("COMSOL_VERSION")
            if self.client_handle is not None and requested_version and self.client_handle.version != requested_version:
                raise ValueError("This process already initialized COMSOL " + self.client_handle.version +
                                 "; set COMSOL_VERSION and restart MCP to use another JVM version.")
            if self.server is None:
                self.server = mph.Server(cores=cores or int(os.getenv("COMSOL_CORES", "4")),
                                         version=version or os.getenv("COMSOL_VERSION") or None,
                                         port=0, multi=True, timeout=180)
            self._attach(self.server.port, "localhost", self.server.version)
            status = self.status()
            result = dict(status, success=status['connected'] is True)
            if products:
                result["products_note"] = "Licenses are requested by each physics interface; products is not a license bypass."
            return result
        except Exception as error:
            return {"success": False, "error": str(error)}

    @native_entry
    def connect(self, port: int, host: str = "localhost") -> dict:
        if self.manager.is_connected:
            status = self.status()
            if status['connection_state'] != 'dead':
                if self.last_endpoint == (host, port):
                    return dict(status, success=status['connected'] is True)
                return {"success": False, "error": "Existing connection is live or unresolved. Disconnect explicitly before changing server."}
        if not 1 <= port <= 65535:
            return {"success": False, "error": "Invalid TCP port."}
        try:
            self._attach(port, host, os.getenv("COMSOL_VERSION") or None)
            status = self.status()
            return dict(status, success=status['connected'] is True)
        except Exception as error:
            return {"success": False, "error": str(error)}

    @native_entry
    def disconnect(self) -> dict:
        if not self.manager.is_connected:
            return {"success": True, "message": "Already disconnected; models preserved."}
        try:
            self.client_handle.disconnect()
            self.manager._client = None
            # Tracked proxies are kept for reconnection to this same server.
            return {"success": True, "message": "Disconnected without deleting models or stopping the multi-client server."}
        except Exception as error:
            state = self._connection_error_state(error)
            if state == 'dead':
                self._forget_dead_connection()
                return {"success": True, "connection_state": state, "warning": str(error)}
            return {"success": False, "connection_state": state, "error": str(error)}

    @native_entry
    def status(self) -> dict:
        state, error = self._connection_probe()
        connected = None if state in {'busy', 'unknown'} else state == 'connected'
        result = {"connected": connected, "connection_state": state, "models": [], "current_model": None}
        if error:
            result['connection_error'] = error
        if connected is True:
            client = self.manager.client
            result.update(version=client.version, cores=client.cores, standalone=bool(client.standalone),
                          host=client.host, port=client.port,
                          models=[{"name": name} for name in self.manager.models],
                          current_model=self.manager.current_model,
                          note="Lists only this MCP session's tracked models; other desktop models are untouched.")
        return result

    @native_entry
    def open_desktop(self) -> dict:
        if not self.manager.is_connected:
            started = self.start()
            if not started.get("success"):
                return started
        else:
            state, error = self._connection_probe()
            if state != 'connected':
                return {"success": False, "connection_state": state, "error": error}
        endpoint = (self.manager.client.host, self.manager.client.port)
        visibility = {"desktop_process_started": True, "desktop_connected": "not_checked",
                      "displayed_model_verified": "not_checked"}
        if self.desktop_process is not None and self.desktop_process.poll() is None and self.desktop_endpoint == endpoint:
            return {"success": True, "already_open": True, "port": self.manager.client.port, **visibility}
        root = self.installation_root()
        executable = root / "bin" / "win64" / "comsolmphclient.exe"
        if not executable.exists():
            return {"success": False, "error": "Automatic desktop launch currently supports Windows.",
                    "host": self.manager.client.host, "port": self.manager.client.port,
                    "hint": "Open your COMSOL Desktop and connect it to this server manually."}
        self.desktop_process = subprocess.Popen([str(executable), "-server", self.manager.client.host,
                                                 "-port", str(self.manager.client.port)],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.desktop_endpoint = endpoint
        return {"success": True, "pid": self.desktop_process.pid, "port": self.manager.client.port, **visibility,
                "next_step": "Complete the simulation through MCP. At the end, the USER manually clicks File > COMSOL Multiphysics Server > Import App from Server and selects the returned model name. The agent must not use screen recognition, OCR, screenshots or UI automation."}

    def catalog(self) -> list[dict]:
        data = json.loads((self.root / "examples" / "catalog.json").read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else data["cases"]

    def list_cases(self, category: str | None = None, case_id: str | None = None, detail: bool = False) -> dict:
        cases = self.catalog()
        if category:
            cases = [case for case in cases if category.casefold() in case.get("category", "").casefold()]
        if case_id:
            cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            return {"success": False, "cases": [], "count": 0, "error": "No matching case. Omit filters to list available ids/categories."}
        try:
            library = self.installation_root() / "applications"
        except Exception:
            library = None
        output = []
        for original in cases:
            case = dict(original)
            relative = case.get("relative_path") or case.get("application_path")
            case["locally_available"] = bool(library and relative and inside(library, relative).is_file()) if relative else (self.root / "examples" / "original" / (case["id"] + ".py")).is_file()
            case["license_verified"] = False
            if not detail:
                compact_keys = {"id", "title", "title_zh", "category", "modules", "dimensions", "status", "locally_available", "license_verified"}
                case = {key: value for key, value in case.items() if key in compact_keys}
            output.append(case)
        return {"success": True, "cases": output, "count": len(output), "detail": detail,
                "hint": "Request case_id plus detail=true for one case's setup, study and validation instructions."}

    def submit_case(self, case_id: str, solve: bool = False, study: str | None = None,
                    show_desktop: bool = True, operation_id: str | None = None,
                    require_hard_deadline: bool = False, task_case_id: str | None = None) -> dict:
        error = self._submission_request_error(operation_id, require_hard_deadline)
        if error:
            return error
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", case_id):
            return {"success": False, "error": "Invalid case id."}
        entry = next((case for case in self.catalog() if case["id"] == case_id), None)
        if entry is None:
            return {"success": False, "error": "Unknown case; call comsol_list_cases."}
        job_id = uuid4().hex
        directory = inside(self.output_root, job_id + "_" + case_id)
        job = {"job_id": job_id, "case_id": case_id, "status": "queued", "events": [],
               "output_dir": str(directory), "submitted_at": time.time(), "runtime_id": self.runtime_id,
               "operation_id": operation_id, "task_case_id": task_case_id,
               "request": {"kind": "case", "case_id": case_id, "solve": solve, "study": study,
                           "show_desktop": show_desktop}}
        return self._queue_job(job, self._run_case, job_id, entry, directory, solve, study, show_desktop)

    def _progress(self, job_id: str, message: str):
        with self.lock:
            job = self.jobs[job_id]
            job["events"].append({"time": time.time(), "message": str(message)[:2000]})
            job["events"] = job["events"][-100:]
            self._persist(job_id)

    def _run_case(self, job_id, entry, directory, solve, study, show_desktop):
        with self.lock:
            self.jobs[job_id]["status"] = "running"
        try:
            directory.mkdir(parents=True, exist_ok=False)
            self._progress(job_id, "Starting a multi-client COMSOL session")
            started = self.start()
            if not started.get("success"):
                raise RuntimeError(started.get("error", "Session failed to start"))
            if show_desktop:
                self._progress(job_id, json.dumps(self.open_desktop(), ensure_ascii=False))
            relative = entry.get("relative_path") or entry.get("application_path")
            if relative:
                source = inside(self.installation_root() / "applications", relative)
                if not source.is_file() or source.suffix.lower() != ".mph":
                    raise FileNotFoundError(f"Installed Application Library model missing: {relative}. Install/download it in COMSOL first.")
                self._progress(job_id, f"Loading licensed local Application Library case: {relative}")
                model = self.manager.client.load(str(source))
                model.rename(f"Teaching_{entry['id']}_{job_id[:8]}")
                self.manager.add_model(model)
                self.manager.set_current_model(model.name())
                studies = list(model.studies())
                if solve:
                    if study:
                        self._progress(job_id, f"Solving selected study: {study}")
                        model.solve(study)
                    else:
                        self._progress(job_id, "Solving all existing study nodes in their stored order")
                        model.solve()
                intended_name = model.name()
                try:
                    model.save(str(directory / (entry["id"] + ".mph")))
                finally:
                    model.rename(intended_name)
                result = {"model_name": model.name(), "model_tag": str(model.java.tag()), "studies": studies,
                          "solved_this_run": solve, "validation": "solver_completed" if solve else "loaded_only",
                          "source": "User's licensed local COMSOL Application Library"}
            else:
                module_path = inside(self.root / "examples" / "original", entry["id"] + ".py")
                spec = importlib.util.spec_from_file_location("comsol_original_" + entry["id"], module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._progress(job_id, "Executing original teaching recipe: geometry, materials, physics, mesh, studies, results")
                result = module.build(self.manager.client, directory, lambda msg: self._progress(job_id, msg),
                                      solve=solve, study_name=study)
                name = result.get("model_name")
                # The builder may create several models; track its explicit result only.
                if name:
                    tag = result.get("model_tag")
                    model = next((m for m in self.manager.client.models()
                                  if str(m.java.tag()) == tag), None) if tag else next(
                                      (m for m in self.manager.client.models() if m.name() == name), None)
                    if model is not None:
                        actual_name = self.manager.add_model(model)
                        self.manager.set_current_model(actual_name)
                        result["model_name"] = actual_name
            result = jsonable(result)
            (directory / "job-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.lock:
                self.jobs[job_id].update(status="completed", result=result, completed_at=time.time())
        except Exception as error:
            detail = {"type": type(error).__name__, "message": str(error)[:12000]}
            with self.lock:
                self.jobs[job_id].update(status="failed", error=detail, completed_at=time.time())
            if directory.exists():
                (directory / "job-error.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    def job_status(self, job_id: str | None = None, operation_id: str | None = None) -> dict:
        if (job_id is None) == (operation_id is None):
            return {"success": False, "error": "Specify exactly one job_id or operation_id."}
        if self.coordination_path or self.resource_id:
            from .isolated_runtime import coordinated_status
            result = coordinated_status(self, operation_id=operation_id, job_id=job_id)
            if result is not None:
                return result
        with self.lock:
            if operation_id is not None:
                if operation_id in self.ambiguous_operations:
                    return {"success": False, "status": "unknown", "operation_id": operation_id,
                            "runtime_id": self.runtime_id, "error": "Multiple job manifests have this operation ID."}
                job_id = self.operations.get(operation_id)
                if job_id is None:
                    return {"success": False, "status": "unknown", "operation_id": operation_id,
                            "runtime_id": self.runtime_id, "error": "Operation not found in this job journal."}
            if job_id not in self.jobs:
                return {"success": False, "error": "Unknown job id; check the configured output root and manifest recovery errors."}
            return json.loads(json.dumps(dict(success=True, **self.jobs[job_id]), default=str))

    def submit_study(self, study_name: str | None, model_name: str | None,
                     operation_id: str | None = None, require_hard_deadline: bool = False, task_case_id: str | None = None) -> dict:
        error = self._submission_request_error(operation_id, require_hard_deadline)
        if error:
            return error
        requested_model = model_name
        model_name = model_name or (self.manager.current_model if self.manager else None)
        job_id = uuid4().hex
        job = {"job_id": job_id, "kind": "study", "status": "queued", "events": [],
               "model_name": model_name, "study_name": study_name, "submitted_at": time.time(),
               "runtime_id": self.runtime_id, "operation_id": operation_id, "task_case_id": task_case_id,
               "request": {"kind": "study", "model_name": requested_model, "study_name": study_name}}

        def solve():
            with self.lock:
                self.jobs[job_id]["status"] = "running"
            try:
                if not self.manager.is_connected:
                    raise RuntimeError("No active COMSOL session.")
                model = self.manager.get_model(model_name)
                if model is None:
                    raise ValueError("Model must be explicitly tracked by this MCP session.")
                self._progress(job_id, "Solving " + (study_name or "all existing study nodes"))
                model.solve(study_name)
                with self.lock:
                    self.jobs[job_id].update(status="completed", completed_at=time.time(),
                                             result={"model_name": model.name(), "study": study_name, "solved": True})
            except Exception as error:
                with self.lock:
                    self.jobs[job_id].update(status="failed", completed_at=time.time(),
                                             error={"type": type(error).__name__, "message": str(error)[:12000]})
        return self._queue_job(job, solve)

    async def wait_job(self, job_id: str | None, timeout: float | None = None) -> dict:
        if not job_id or job_id not in self.jobs:
            return {"success": False, "error": "No matching job."}
        duration = min(max(timeout if timeout is not None else 30.0, 0.0), 30.0)
        deadline = time.monotonic() + duration
        while True:
            state = self.job_status(job_id)
            if state["status"] in TERMINAL_JOB_STATES | {"recovery_pending"} or time.monotonic() >= deadline:
                return state
            await asyncio.sleep(0.1)

    def cancel_job(self, job_id: str | None) -> dict:
        if not job_id or job_id not in self.futures:
            return {"success": False, "error": "No matching job."}
        if self.futures[job_id].cancel():
            with self.lock:
                if self.jobs[job_id]['status'] != 'cancelled':
                    self.jobs[job_id].update(status="cancelled", completed_at=time.time())
                    self._persist(job_id)
            return dict(self.job_status(job_id), cancellation="cancelled_before_start")
        with self.lock:
            status = self.jobs[job_id]['status']
            if status in TERMINAL_JOB_STATES:
                return {"success": False, "job_id": job_id, "status": status, "error": "Job is already terminal."}
            self.jobs[job_id]['cancel_requested'] = True
            self.jobs[job_id]['cancellation'] = 'cancel_not_supported'
            self._persist(job_id)
        return {"success": False, "job_id": job_id, "cancel_requested":True,
                "cancellation":"cancel_not_supported", "status":self.job_status(job_id)['status'],
                "error": "Running Java calls cannot be safely interrupted from another Python thread. If needed, ask the USER to manually press COMSOL Desktop's Stop control; the agent must not use screen recognition or UI automation."}

    @native_entry
    def execute_code(self, model_name: str, code: str) -> dict:
        if os.getenv("COMSOL_ALLOW_CODE") != "1":
            return {"success": False, "error": "Disabled. A trusted local operator must set COMSOL_ALLOW_CODE=1 and restart the server. This executes arbitrary Python and is not sandboxed."}
        if not self.manager.is_connected:
            return {"success": False, "error": "No active COMSOL connection. Reconnect before using model proxies."}
        model = self.manager.get_model(model_name)
        if model is None:
            return {"success": False, "error": "Name must refer to a model explicitly created/loaded by this MCP session."}
        if len(code) > 100000:
            return {"success": False, "error": "Code exceeds 100,000 characters."}
        captured = []
        def bounded_print(*values, sep=" ", end="\n", **kwargs):
            if sum(map(len, captured)) < 16000:
                captured.append((sep.join(map(str, values)) + end)[:16000])
        environment = {"model": model, "java": model.java, "output_dir": self.output_root,
                       "print": bounded_print, "result": None}
        try:
            exec(compile(code, "<trusted-comsol-code>", "exec"), environment)
            return {"success": True, "result": jsonable(environment["result"]), "stdout": "".join(captured)[:16000]}
        except Exception as error:
            return {"success": False, "error": str(error)[:12000], "stdout": "".join(captured)[:16000]}


class SerializedRegistrar:
    """Preserve upstream signatures while moving every synchronous Java call to one thread."""
    def __init__(self, mcp, runtime: Runtime):
        self.mcp, self.runtime = mcp, runtime

    def _wrap(self, function):
        signature = inspect.signature(function)
        @functools.wraps(function)
        async def call(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = dict(bound.arguments)
            # Explicit output destinations prevent an export from silently using
            # a file path embedded in a model supplied by somebody else.
            if function.__name__ in {"model_save", "results_export_data", "results_export_image"}:
                value = arguments.get("file_path")
                if not value:
                    return {"success": False, "error": "Provide an explicit file_path inside COMSOL_OUTPUT_ROOT."}
                try:
                    path = inside(self.runtime.output_root, value)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    arguments["file_path"] = str(path)
                except ValueError as error:
                    return {"success": False, "error": str(error)}
            def invoke():
                if function.__name__ in {"model_save", "model_save_version"}:
                    model = self.runtime.manager.get_model(arguments.get("model_name"))
                    if model is not None:
                        if function.__name__ == "model_save_version":
                            from src.utils.versioning import safe_model_name
                            try:
                                name = safe_model_name(model.name())
                                inside(self.runtime.output_root, self.runtime.output_root / "versions" / name)
                            except ValueError as error:
                                return {"success": False, "error": str(error)}
                        label = str(model.java.label())
                        try:
                            result = function(**arguments)
                        finally:
                            model.java.label(label)
                        if isinstance(result, dict) and "model" in result:
                            result["model"] = model.name()
                        return result
                return function(**arguments)
            result = await self.runtime.call(invoke)
            return jsonable(result)
        call.__signature__ = signature
        return call

    def tool(self, *args, **kwargs):
        def decorator(function):
            if function.__name__ in {"study_solve", "study_solve_async", "study_get_progress", "study_wait", "study_cancel", "study_create"}:
                return function  # Replaced by the runtime's single-thread job tools.
            description = kwargs.copy()
            if function.__name__ == "comsol_disconnect":
                description["description"] = "Disconnect this MCP client while preserving every server model. Never clears models."
            if function.__name__ == "comsol_start":
                description["description"] = "Start/reuse a multi-client COMSOL server. Repeated calls preserve models. Use comsol_open_desktop to view the same server."
            self.mcp.tool(*args, **description)(self._wrap(function))
            return function
        return decorator

    def resource(self, *args, **kwargs):
        def decorator(function):
            self.mcp.resource(*args, **kwargs)(self._wrap(function))
            return function
        return decorator
