"""Runtime admission and readback for the owned Windows executor.

Offline review candidates remain evidence, not provider permission. Local
operator configuration, current resource ownership and clock checks are required.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from types import SimpleNamespace

from .case_clock import CaseClock
from .coordination import Coordinator
from . import isolated_batch, shared_guard


def launch_binding(operation_id, case_id, source, digest, study, cores, resource_id,
                   executor_id, deadline, clock):
    return dict(operation_id=operation_id, case_id=case_id, source_file=str(source),
                input_sha256=digest, study_tag=study, cores=cores, resource_id=resource_id,
                executor_id=executor_id, deadline_at_unix=deadline,
                case_deadline_at_unix=clock['deadline_at_unix'],
                new_work_cutoff_unix=clock['new_work_cutoff_unix'])


def review(verification, workspace, binding):
    from scripts.verification_gate import verify, read_receipt, utc
    now = datetime.now(timezone.utc)
    result = verify(verification, workspace, now)
    if result.get('action') != 'EVIDENCE_BOUND_CANDIDATE':
        raise ValueError('REVIEW_REQUIRED: '+result.get('reason', 'missing evidence'))
    s = verification['snapshot']
    if (verification['mode'] != 'admit' or s['action'] != 'SOLVE'
            or s['actor_role'] != 'executor' or s['actor_id'] != binding['executor_id']
            or s['executor_id'] != binding['executor_id'] or s['case_id'] != binding['case_id']
            or s['action_id'] != binding['operation_id'] or s['revision'] != binding['input_sha256']):
        raise ValueError('REVIEW_REQUIRED: actual execution identity/model mismatch')
    expiries = [utc(s['deadline_utc'])]
    expiries.extend(utc(r['deadline_utc']) for r in s['reviews'].values())
    for ref in verification['receipts']:
        r = read_receipt(Path(workspace), ref, s, now)
        expiries.append(utc(r['expires_utc']))
        if r.get('launch_binding') != binding:
            raise ValueError('REVIEW_REQUIRED: receipt not bound to actual launch')
    if datetime.now(timezone.utc) >= min(expiries):
        raise ValueError('REVIEW_REQUIRED: evidence expired during verification')
    return min(expiries).timestamp()


def check_clock(path, case_id, deadline, frozen=None):
    now = time.time()
    clock = CaseClock(path).status(case_id)
    if clock['phase'] != 'OPEN' or not clock['active']:
        raise ValueError('CASE_CLOCK_EXIT')
    if not now < deadline <= min(clock['new_work_cutoff_unix'], now+clock['solve_limit_seconds']):
        raise ValueError('CASE_OR_SOLVE_DEADLINE_EXCEEDED')
    if frozen and any(clock[k] != frozen[k] for k in ('deadline_at_unix', 'new_work_cutoff_unix')):
        raise ValueError('CASE_CLOCK_CHANGED')
    return clock


def verify_launch(request, folder):
    """Immediately-before-CreateProcess checks; called again by detached worker."""
    folder = Path(folder).resolve()
    c = Coordinator(request['coordination_path'], request['resource_id'])
    row = c.get(job_id=request['job_id'])
    if not row or row['released'] or row['owner'] != request['owner'] or row['kind'] != 'isolated':
        raise ValueError('EXCLUSIVE_OWNER_REQUIRED')
    if row['state'] not in {'reserved', 'launching', 'running'}:
        raise ValueError('ORIGINAL_JOB_UNRESOLVED')
    stored = row['request']
    binding = request['binding']
    if stored['binding'] != binding or stored['verification'] != request['verification']:
        raise ValueError('IMMUTABLE_REQUEST_CHANGED')
    expected = {
        'operation_id': row['operation_id'], 'case_id': stored['case_id'],
        'deadline_at_unix': stored['deadline_at_unix'], 'study_tag': stored['study_tag'],
        'cores': stored['cores'], 'resource_id': stored['resource_id'],
        'executor_id': stored['executor_id'], 'case_clock_path': stored['case_clock_path'],
        'source_file': stored['source_file'], 'input_sha256': stored['input_sha256'],
        'case_deadline_at_unix': binding['case_deadline_at_unix'],
        'new_work_cutoff_unix': binding['new_work_cutoff_unix'],
    }
    if any(request.get(k) != v for k, v in expected.items()):
        raise ValueError('IMMUTABLE_LAUNCH_CHANGED')
    if Path(request['input_file']).resolve() != folder/'input.mph':
        raise ValueError('INPUT_SNAPSHOT_PATH_CHANGED')
    for source in (Path(request['source_file']), folder/'input.mph'):
        if hashlib.sha256(source.read_bytes()).hexdigest() != request['input_sha256']:
            raise ValueError('REVIEW_REQUIRED: model changed after review')
    bound = c.case(request['case_id'])
    if not bound or Path(bound['clock_path']) != Path(request['case_clock_path']).resolve():
        raise ValueError('CASE_CLOCK_RESOURCE_BINDING_REQUIRED')
    # Validate evidence first, then read the live case so a close during slow
    # hashing takes effect. Retain expiry for a final check after all DB I/O.
    expires = review(request['verification'], stored['output_root'], binding)
    clock = check_clock(request['case_clock_path'], request['case_id'], request['deadline_at_unix'],
                {'deadline_at_unix': request['case_deadline_at_unix'],
                 'new_work_cutoff_unix': request['new_work_cutoff_unix']})
    cutoff = min(expires, request['deadline_at_unix'], clock['new_work_cutoff_unix'],
                 clock['last_verified_progress_at_unix']+clock['stall_seconds'])
    if not clock['last_seen_at_unix'] <= time.time() < cutoff:
        raise ValueError('REVIEW_REQUIRED: clock or evidence expired before execution')


def record_failure(output_root, row, observation):
    """Idempotent Recovery Memory observation, never a resubmission grant."""
    from scripts.recovery_memory import run
    req = row['request']
    db = Path(output_root)/'recovery-memory.sqlite3'
    reservation = run(SimpleNamespace(command='reserve', db=db, case=req['case_id'],
        build='0.6.1', revision=req['input_sha256'], action=row['operation_id'],
        evidence=hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest(),
        symptom='isolated job '+row['job_id']))
    if reservation['decision'] == 'NEW' or reservation['prior_status'] == 'reserved':
        run(SimpleNamespace(command='finish', db=db, id=reservation['id'],
                            status='inconclusive', observation=observation))


def submit(runtime, input_file, study_tag, operation_id, deadline_at_unix, case_id, verification, cores=4):
    row = None
    try:
        if runtime.tool_role != 'operator':
            raise ValueError('ROLE_FORBIDDEN')
        c = shared_guard.coordinator(runtime, required=True)
        if not runtime.isolated_enabled or not runtime.executor_id:
            raise ValueError('ISOLATED_OPERATOR_OPT_IN_REQUIRED')
        if not isinstance(operation_id, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', operation_id):
            raise ValueError('INVALID_OPERATION_ID')
        if type(deadline_at_unix) not in (int, float) or not math.isfinite(deadline_at_unix):
            raise ValueError('FINITE_DEADLINE_REQUIRED')
        if not isinstance(study_tag, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', study_tag):
            raise ValueError('INVALID_STUDY_TAG')
        if type(cores) is not int or not 1 <= cores <= 4:
            raise ValueError('CORES_MUST_BE_1_TO_4')
        source = (runtime.output_root/Path(input_file)).resolve()
        if not source.is_relative_to(runtime.output_root) or source.suffix.lower() != '.mph':
            raise ValueError('INPUT_MUST_BE_MPH_WITHIN_OUTPUT_ROOT')
        original = c.get(operation_id=operation_id)
        if original:
            prior = original['request']
            values = dict(source_file=str(source), study_tag=study_tag, cores=cores,
                          deadline_at_unix=deadline_at_unix, case_id=case_id,
                          verification=verification, executor_id=runtime.executor_id)
            if original['kind'] != 'isolated' or any(prior.get(k) != v for k, v in values.items()):
                raise ValueError('OPERATION_ID_CONFLICT')
            return dict(status(runtime, operation_id=operation_id), existing_job=True)
        if operation_id in runtime.operations or runtime.journal_errors:
            raise ValueError('ORIGINAL_HISTORY_UNRESOLVED')
        isolated_batch.platform_check()
        budget = runtime._submission_budget(len(runtime._active_jobs()))
        if not budget['can_submit']:
            raise ValueError('SUBMISSION_BUDGET_EXHAUSTED: '+','.join(budget['block_reasons']))
        clock = check_clock(runtime.case_clock_path, case_id, deadline_at_unix)
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        binding = launch_binding(operation_id, case_id, source, digest, study_tag, cores,
                                 runtime.resource_id, runtime.executor_id, deadline_at_unix, clock)
        review(verification, runtime.output_root, binding)
        c.bind_case(case_id, runtime.case_clock_path, clock)
        request = dict(source_file=str(source), study_tag=study_tag, cores=cores,
                       deadline_at_unix=deadline_at_unix, case_id=case_id,
                       verification=verification, executor_id=runtime.executor_id,
                       resource_id=runtime.resource_id, input_sha256=digest, binding=binding,
                       output_root=str(runtime.output_root), case_clock_path=str(runtime.case_clock_path))
        row = shared_guard.reserve(runtime, operation_id, request, 'isolated')
        if row['existing']:
            return dict(status(runtime, operation_id=operation_id), existing_job=True)
        folder = runtime.output_root/'isolated-jobs'/row['job_id']
        folder.mkdir(parents=True, exist_ok=False)
        with (folder/'input.mph').open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        envelope = dict(request, operation_id=operation_id, job_id=row['job_id'], owner=row['owner'],
                        input_file=str(folder/'input.mph'), coordination_path=str(c.path),
                        case_deadline_at_unix=clock['deadline_at_unix'],
                        new_work_cutoff_unix=clock['new_work_cutoff_unix'])
        verify_launch(envelope, folder)
        result = isolated_batch.launch(folder, envelope)
        return dict(result, success=True, job_id=row['job_id'], operation_id=operation_id,
                    deadline_at_unix=deadline_at_unix, scientific_status='NOT_EVALUATED')
    except Exception as exc:
        result = shared_guard.blocked(exc)
        if row:
            result.update(job_id=row['job_id'], operation_id=operation_id, resource_retained=True)
            try:
                record_failure(runtime.output_root, row, str(exc))
            except Exception as recovery_error:
                result['recovery_memory_error'] = str(recovery_error)
        return result


def coordinated_status(runtime, *, operation_id=None, job_id=None):
    try:
        c = shared_guard.coordinator(runtime, required=True)
        row = c.get(operation_id=operation_id, job_id=job_id)
        if row is None and job_id is not None:
            matches = [r for r in c.inspect() if r['kind'] == 'shared_job'
                       and r['request'].get('native_job_id') == job_id]
            if len(matches) > 1:
                raise ValueError('AMBIGUOUS_JOB_ID')
            row = matches[0] if matches else None
        if row is None:
            return None
        if row['kind'] == 'isolated':
            folder = Path(row['request']['output_root'])/'isolated-jobs'/row['job_id']
            result = isolated_batch.status(folder)
            if (result.get('job_id') not in {None, row['job_id']}
                    or result.get('operation_id') not in {None, row['operation_id']}
                    or result.get('deadline_at_unix') not in {None, row['request']['deadline_at_unix']}):
                raise ValueError('ISOLATED_RECEIPT_IDENTITY_MISMATCH')
            proof = row.get('proof') or {}
            observed_stop = result.get('native_stop_verified') is True
            result['native_stop_verified'] = (observed_stop and row['released']
                and proof.get('native_stopped') is True and isinstance(proof.get('evidence'), dict)
                and proof['evidence'].get('active_processes') == 0)
            result.update(success=True, job_id=row['job_id'], operation_id=row['operation_id'],
                          resource_retained=not row['released'], coordination_state=row['state'],
                          deadline_at_unix=row['request']['deadline_at_unix'])
            if runtime.tool_role == 'operator' and (result.get('stop_reason') or result['status'] in {
                    'process_failed', 'unknown_supervisor_lost', 'unknown_supervisor_liveness', 'unknown_launch',
                    'unknown_stop_unconfirmed', 'launch_rejected', 'unknown_corrupt_state'}):
                try:
                    record_failure(row['request']['output_root'], row, json.dumps(result, sort_keys=True))
                except Exception as exc:
                    result['recovery_memory_error'] = str(exc)
            return result
        if row['kind'] == 'shared_job':
            native_id = row['request']['native_job_id']
            if native_id in runtime.jobs:
                native = dict(runtime.jobs[native_id])
            else:
                path = Path(row['request']['output_root'])/'job-manifests'/(native_id+'.json')
                native = json.loads(path.read_text(encoding='utf-8'))
            if (native.get('job_id') != native_id or native.get('coordination_job_id') != row['job_id']
                    or native.get('runtime_id') != row['owner']
                    or (native.get('operation_id') and native['operation_id'] != row['operation_id'])):
                raise ValueError('SHARED_RECEIPT_IDENTITY_MISMATCH')
            if row['released'] and native['status'] not in {'completed', 'cancelled'}:
                native['status'] = 'recovery_pending'
            return dict(native, success=True, resource_retained=not row['released'])
        return dict(success=True, job_id=row['job_id'], operation_id=row['operation_id'],
                    status=row['state'], resource_retained=not row['released'], kind=row['kind'])
    except Exception as exc:
        return shared_guard.blocked(exc)


def status(runtime, *, operation_id=None, job_id=None):
    return coordinated_status(runtime, operation_id=operation_id, job_id=job_id) or {
        'success': False, 'status': 'unknown_operation', 'operation_id': operation_id,
        'job_id': job_id, 'resubmission_authorized': False}
