"""Durable exclusion for participating native Runtime operations.

Not a sandbox: operators, the local database and its parent directory are trusted.
Unregistered installations are outside this coordination domain.
"""
import functools
import json
import os
from pathlib import Path
import threading
from uuid import uuid4

from .coordination import Coordinator, CoordinationError


def blocked(error):
    return {'success': False, 'status': 'BLOCKED', 'error': str(error)}


def configure(runtime):
    runtime.tool_role = os.getenv('COMSOL_TOOL_ROLE', 'operator')
    runtime.coordination_path = os.getenv('PAPER2SIMU_COORDINATION_DB')
    runtime.resource_id = os.getenv('PAPER2SIMU_RESOURCE_ID')
    runtime.executor_id = os.getenv('PAPER2SIMU_EXECUTOR_ID')
    runtime.isolated_enabled = os.getenv('PAPER2SIMU_ALLOW_ISOLATED') == '1'
    runtime._native_context = threading.local()


def coordinator(runtime, required=False):
    if not runtime.coordination_path and not runtime.resource_id and not required:
        return None
    if not runtime.coordination_path or not runtime.resource_id:
        raise CoordinationError('COORDINATION_CONFIGURATION_REQUIRED')
    c = Coordinator(runtime.coordination_path, runtime.resource_id)
    if runtime.tool_role == 'operator':
        runtime.output_root.mkdir(parents=True, exist_ok=True)
        c.register_root(runtime.output_root)
    return c


def check_history(roots, jobs, operation_id=None):
    known = {j['job_id']: j for j in jobs}
    operations = {j['operation_id'] for j in jobs}
    seen = set()
    for root in roots:
        if not root.is_dir():
            raise CoordinationError('HISTORY_ROOT_UNAVAILABLE: '+str(root))
        # Explicit enumeration propagates permission/I/O errors; glob can hide them.
        entries = {p.name: p for p in root.iterdir()}
        manifests = entries.get('job-manifests')
        for path in ([] if manifests is None else manifests.iterdir()):
            if path.suffix != '.json':
                continue
            try:
                row = json.loads(path.read_text(encoding='utf-8'))
                if row['job_id'] != path.stem:
                    raise ValueError('identity mismatch')
                op = row.get('operation_id')
                if op and op in seen:
                    raise ValueError('duplicate historical operation')
                if op:
                    seen.add(op)
                if row.get('coordination_job_id') in known:
                    claim = known[row['coordination_job_id']]
                    req = claim['request']
                    if (claim['kind'] != 'shared_job' or claim['owner'] != row.get('runtime_id')
                            or req.get('native_job_id') != row['job_id']
                            or Path(req.get('output_root', '')) != root
                            or (op and claim['operation_id'] != op)):
                        raise ValueError('misbound coordinated history')
                    continue
                if op and (op in operations or op == operation_id):
                    raise ValueError('unlinked duplicate operation')
                if row.get('status') not in {'completed', 'cancelled'}:
                    raise ValueError('unresolved historical native state')
            except (OSError, ValueError, KeyError) as exc:
                raise CoordinationError('HISTORY_UNRESOLVED: '+str(path)) from exc
        isolated = entries.get('isolated-jobs')
        for folder in ([] if isolated is None else isolated.iterdir()):
            if not folder.is_dir():
                continue
            try:
                row = json.loads((folder/'request.json').read_text(encoding='utf-8'))
                claim = known.get(row.get('job_id'))
                if (not claim or claim['kind'] != 'isolated'
                        or Path(claim['request'].get('output_root', '')) != root
                        or claim['operation_id'] != row.get('operation_id')
                        or claim['owner'] != row.get('owner') or folder.name != claim['job_id']):
                    raise ValueError('unregistered isolated history')
            except (OSError, ValueError) as exc:
                raise CoordinationError('HISTORY_UNRESOLVED: '+str(folder)) from exc


def reserve(runtime, operation_id, request, kind):
    if runtime.tool_role != 'operator':
        raise CoordinationError('ROLE_FORBIDDEN')
    c = coordinator(runtime)
    if c is None:
        return None
    def admission(roots, jobs):
        check_history(roots, jobs, operation_id)
        if kind != 'shared_call':
            budget = runtime._submission_budget(len(runtime._active_jobs()), coordinated_jobs=jobs)
            if not budget['can_submit']:
                raise CoordinationError('SUBMISSION_BUDGET_EXHAUSTED: '+','.join(budget['block_reasons']))
    return c.reserve(operation_id, request, runtime.runtime_id, kind, check_history=admission)


def invoke(runtime, function, *args, claim=None, **kwargs):
    """Reentrant only on the thread currently executing this owned native call."""
    if runtime.tool_role != 'operator':
        return blocked('ROLE_FORBIDDEN')
    context = runtime._native_context
    if getattr(context, 'active', False):
        return function(*args, **kwargs)
    try:
        c = coordinator(runtime)
        if c is None:
            return function(*args, **kwargs)
        claim = claim or reserve(runtime, 'call-'+uuid4().hex,
                                 {'function': getattr(function, '__name__', type(function).__name__),
                                  'output_root': str(runtime.output_root)}, 'shared_call')
        c.transition(claim['job_id'], runtime.runtime_id, 'launching')
        c.transition(claim['job_id'], runtime.runtime_id, 'running')
    except (ValueError, OSError) as exc:
        return blocked(exc)
    context.active = True
    context.uncertain = False
    try:
        result = function(*args, **kwargs)
        # An error can be a lost native reply. Arbitrary operator code may spawn
        # background work, so it cannot prove idle merely by returning.
        failed = isinstance(result, dict) and (result.get('success') is False
            or result.get('connection_state') in {'unknown', 'busy', 'dead'}
            or result.get('status') in {'BLOCKED', 'unknown', 'recovery_pending'}
            or ('connected' in result and result['connected'] is None))
        if not failed and not context.uncertain:
            c.release(claim['job_id'], runtime.runtime_id,
                      {'native_stopped': True, 'evidence': 'Owned synchronous shared call returned'})
        return result
    finally:
        context.active = False


def native_entry(function):
    @functools.wraps(function)
    def guarded(self, *args, **kwargs):
        def operation():
            if function.__name__ == 'execute_code':
                self._native_context.uncertain = True
            return function(self, *args, **kwargs)
        operation.__name__ = function.__name__
        return invoke(self, operation)
    return guarded
