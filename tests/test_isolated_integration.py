"""Offline integration controls. Never connects to a commercial solver."""
import asyncio
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from server.runtime import Runtime


def test_runtime_has_isolated_interface(tmp_path):
    runtime = Runtime(output_root=tmp_path)
    assert callable(getattr(runtime, 'submit_isolated', None))
    assert callable(getattr(runtime, 'isolated_status', None))


def test_missing_domain_blocks_isolated(tmp_path):
    runtime = Runtime(output_root=tmp_path)
    result = runtime.submit_isolated('input.mph', 'std1', 'op', time.time()+60, 'c', {})
    assert result['status'] == 'BLOCKED'


def test_reviewer_has_no_execution(tmp_path, monkeypatch):
    monkeypatch.setenv('COMSOL_TOOL_ROLE', 'reviewer')
    runtime = Runtime(output_root=tmp_path)
    called = Mock()
    assert asyncio.run(runtime.call(called))['status'] == 'BLOCKED'
    called.assert_not_called()
    assert runtime.submit_study(None, None, 'op')['error'] == 'ROLE_FORBIDDEN'
    assert runtime.submit_isolated('input.mph', 'std1', 'op', time.time()+60, 'c', {})['error'] == 'ROLE_FORBIDDEN'


def test_registration(tmp_path, monkeypatch):
    from server.main import create_server
    monkeypatch.setenv('COMSOL_TOOL_ROLE', 'operator')
    mcp, runtime = create_server(Runtime(output_root=tmp_path))
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {'comsol_isolated_batch_submit', 'comsol_isolated_batch_status'} <= names
    monkeypatch.setenv('COMSOL_TOOL_ROLE', 'reviewer')
    mcp, runtime = create_server(Runtime(output_root=tmp_path))
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert 'comsol_isolated_batch_status' in names
    assert 'comsol_isolated_batch_submit' not in names


def test_shared_capability_stays_unsupported(tmp_path):
    assert Runtime(output_root=tmp_path).execution_capabilities()['deadline_enforcement']['state'] == 'unsupported'


def domain(tmp_path, monkeypatch):
    from server.coordination import initialize, Coordinator
    path = tmp_path/'domain.sqlite3'
    initialize(path, 'host-license')
    monkeypatch.setenv('PAPER2SIMU_COORDINATION_DB', str(path))
    monkeypatch.setenv('PAPER2SIMU_RESOURCE_ID', 'host-license')
    return Coordinator(path, 'host-license')


def test_cross_root_all_shared_calls_block(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    c.reserve('isolated', {}, 'owner', 'isolated')
    runtime = Runtime(output_root=tmp_path/'different')
    called = Mock()
    assert asyncio.run(runtime.call(called))['status'] == 'BLOCKED'
    called.assert_not_called()
    for name, args in [('start',()), ('connect',(1234,)), ('disconnect',()),
                       ('status',()), ('open_desktop',()), ('prepare_stdio_client',()),
                       ('execute_code',('m','pass'))]:
        assert getattr(runtime, name)(*args)['status'] == 'BLOCKED'
    assert runtime.submit_study(None, None, 'other')['status'] == 'BLOCKED'


def test_configured_database_loss_blocks(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    runtime = Runtime(output_root=tmp_path/'out')
    c.path.unlink()
    called = Mock()
    assert asyncio.run(runtime.call(called))['status'] == 'BLOCKED'
    called.assert_not_called()


def test_shared_exception_retains_claim(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    runtime = Runtime(output_root=tmp_path/'out')
    def fail():
        raise RuntimeError('lost native reply')
    with pytest.raises(RuntimeError):
        asyncio.run(runtime.call(fail))
    assert len([r for r in c.inspect() if not r['released']]) == 1
    assert asyncio.run(runtime.call(lambda: 1))['status'] == 'BLOCKED'


def approved(tmp_path, monkeypatch):
    from server.case_clock import CaseClock
    from test_verification_gate import build
    from server.isolated_runtime import launch_binding
    c = domain(tmp_path, monkeypatch)
    monkeypatch.setenv('PAPER2SIMU_EXECUTOR_ID', 'ex')
    monkeypatch.setenv('PAPER2SIMU_ALLOW_ISOLATED', '1')
    runtime = Runtime(output_root=tmp_path)
    source = tmp_path/'model.mph'
    source.write_bytes(b'synthetic model; NOT a commercial solver input')
    clock = CaseClock(runtime.case_clock_path).start('c', 14400, 1800, 9000, 900)
    deadline = time.time()+60
    req = build(tmp_path)
    s = req['snapshot']
    s['revision'] = hashlib.sha256(source.read_bytes()).hexdigest()
    for r in s['reviews'].values():
        r['revision'] = s['revision']
    binding = launch_binding('op', 'c', source, s['revision'], 'std1', 4,
                             'host-license', 'ex', deadline, clock)
    for ref in req['receipts']:
        p = tmp_path/ref['path']
        receipt = json.loads(p.read_text())
        receipt.update(revision=s['revision'], observed_utc='2020-01-01T00:00:00Z',
                       expires_utc='2099-01-01T00:00:00Z', launch_binding=binding)
        p.write_text(json.dumps(receipt))
        ref['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    monkeypatch.setattr('server.isolated_batch.platform_check', lambda: None)
    launcher = Mock(return_value={'status':'unknown_starting'})
    monkeypatch.setattr('server.isolated_batch.launch', launcher)
    return runtime, c, source, deadline, req, launcher


def test_admitted_launch_and_replay_keep_original_budget(tmp_path, monkeypatch):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    first = runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)
    assert first['success'], first
    second_runtime = Runtime(output_root=tmp_path)
    replay = second_runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)
    assert replay['job_id'] == first['job_id']
    assert replay['existing_job'] is True
    assert launch.call_count == 1
    stored = c.get(operation_id='op')['request']
    assert stored['deadline_at_unix'] == deadline
    assert second_runtime.job_status(operation_id='op')['job_id'] == first['job_id']


@pytest.mark.parametrize('change', ['model', 'evidence', 'identity', 'case_expired', 'missing_review', 'parameters'])
def test_launch_denies_invalid_binding(tmp_path, monkeypatch, change):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    study = 'std1'
    if change == 'model': source.write_bytes(b'changed')
    if change == 'evidence': (tmp_path/'physics.log').write_text('changed')
    if change == 'identity': runtime.executor_id = 'different'
    if change == 'case_expired':
        from server.case_clock import CaseClock
        CaseClock(runtime.case_clock_path).close('c', 'expired')
    if change == 'missing_review': req['snapshot']['reviews'].pop('supervisor')
    if change == 'parameters': study = 'std2'
    result = runtime.submit_isolated(str(source), study, 'op', deadline, 'c', req)
    assert result['status'] == 'BLOCKED', result
    launch.assert_not_called()


def test_launch_receipt_loss_never_resubmits(tmp_path, monkeypatch):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    launch.side_effect = OSError('receipt lost after spawn')
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['status'] == 'BLOCKED'
    assert not c.get(operation_id='op')['released']
    retry = Runtime(output_root=tmp_path).submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)
    assert retry['existing_job']
    assert launch.call_count == 1


def test_unknown_native_reply_keeps_claim(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    runtime = Runtime(output_root=tmp_path/'out')
    asyncio.run(runtime.call(lambda: {'connected': None, 'connection_state': 'unknown'}))
    assert not c.inspect()[0]['released']


def test_historical_operation_in_other_root_blocks(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    old = tmp_path/'old'
    manifests = old/'job-manifests'
    manifests.mkdir(parents=True)
    (manifests/'j.json').write_text(json.dumps({'job_id':'j','operation_id':'op','status':'completed'}))
    c.register_root(old)
    runtime = Runtime(output_root=tmp_path/'new')
    result = runtime.submit_study('std1', 'm', 'op')
    assert result['status'] == 'BLOCKED', result


def test_missing_enrolled_root_blocks(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    c.register_root(tmp_path/'unavailable')
    runtime = Runtime(output_root=tmp_path/'new')
    called = Mock()
    assert asyncio.run(runtime.call(called))['status'] == 'BLOCKED'
    called.assert_not_called()


def test_isolated_obeys_runtime_submission_budget(tmp_path, monkeypatch):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    monkeypatch.setenv('COMSOL_MAX_SUBMISSIONS', 'invalid')
    result = runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)
    assert result['status'] == 'BLOCKED', result
    launch.assert_not_called()


def test_worker_rejects_changed_snapshot_after_admission(tmp_path, monkeypatch):
    from server.isolated_runtime import verify_launch
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    folder, envelope = launch.call_args.args
    (folder/'input.mph').write_bytes(b'changed after review')
    with pytest.raises(ValueError, match='model changed'):
        verify_launch(envelope, folder)


def test_stop_observation_cannot_override_unreleased_claim(tmp_path, monkeypatch):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    folder, envelope = launch.call_args.args
    (folder/'request.json').write_text(json.dumps(envelope))
    (folder/'state.json').write_text(json.dumps(dict(operation_id='op', job_id=envelope['job_id'],
        deadline_at_unix=deadline, status='process_completed', native_stop_verified=True)))
    report = runtime.isolated_status(operation_id='op')
    assert not report['native_stop_verified']
    assert report['resource_retained']


def test_shared_original_ids_and_results_across_runtime_roots(tmp_path, monkeypatch):
    from types import SimpleNamespace
    c = domain(tmp_path, monkeypatch)
    runtime = Runtime(output_root=tmp_path/'a')
    model = SimpleNamespace(solve=lambda study: None, name=lambda: 'm')
    runtime.manager = SimpleNamespace(current_model='m', is_connected=True, get_model=lambda name: model)
    job = runtime.submit_study('std1', 'm', 'shared')
    assert job['success'], job
    runtime.executor.shutdown(wait=True)
    other = Runtime(output_root=tmp_path/'b')
    for lookup in ({'operation_id':'shared'}, {'job_id':job['job_id']}):
        result = other.job_status(**lookup)
        assert result['job_id'] == job['job_id'], result
        assert result['status'] == 'completed', result
        assert result['result']['solved'] is True
        assert not result['resource_retained']
    # Correctly linked historical completion must not wedge subsequent work.
    assert asyncio.run(other.call(lambda: {'success': True}))['success']


def test_shared_failure_holds_claim(tmp_path, monkeypatch):
    from types import SimpleNamespace
    c = domain(tmp_path, monkeypatch)
    runtime = Runtime(output_root=tmp_path/'a')
    runtime.manager = SimpleNamespace(current_model='m', is_connected=False)
    job = runtime.submit_study('std1', 'm', 'shared')
    runtime.executor.shutdown(wait=True)
    assert runtime.job_status(job_id=job['job_id'])['status'] == 'failed'
    assert not c.get(operation_id='shared')['released']


def test_reviewer_status_does_not_enroll_root_or_write_recovery(tmp_path, monkeypatch):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    before = c.roots()
    monkeypatch.setenv('COMSOL_TOOL_ROLE', 'reviewer')
    root = tmp_path/'reviewer'
    reviewer = Runtime(output_root=root)
    reviewer.isolated_status(operation_id='op')
    assert c.roots() == before
    assert not root.exists()


def test_expired_receipt_after_reservation_requires_review(tmp_path, monkeypatch):
    from server.isolated_runtime import verify_launch
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    folder, envelope = launch.call_args.args
    p = tmp_path/'supervisor.json'
    body = json.loads(p.read_text())
    body['expires_utc'] = '2020-01-01T00:00:00Z'
    p.write_text(json.dumps(body))
    with pytest.raises(ValueError, match='REVIEW_REQUIRED'):
        verify_launch(envelope, folder)


def test_failed_finished_job_records_recovery_even_after_release(tmp_path, monkeypatch):
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    folder, envelope = launch.call_args.args
    (folder/'request.json').write_text(json.dumps(envelope))
    (folder/'state.json').write_text(json.dumps(dict(operation_id='op', job_id=envelope['job_id'],
        deadline_at_unix=deadline, status='process_failed', native_stop_verified=True, exit_code=7)))
    c.transition(envelope['job_id'], envelope['owner'], 'launching')
    c.transition(envelope['job_id'], envelope['owner'], 'running')
    c.release(envelope['job_id'], envelope['owner'], {'native_stopped':True, 'evidence':{'active_processes':0}})
    assert runtime.isolated_status(operation_id='op')['native_stop_verified']
    import sqlite3
    with sqlite3.connect(tmp_path/'recovery-memory.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0] == 1


def test_unrelated_known_claim_cannot_hide_unresolved_manifest(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    claim = c.reserve('earlier', {}, 'owner', 'shared_call')
    c.release(claim['job_id'], 'owner', {'never_started':True})
    runtime = Runtime(output_root=tmp_path/'out')
    manifests = runtime.output_root/'job-manifests'
    manifests.mkdir(parents=True)
    (manifests/'foreign.json').write_text(json.dumps(dict(job_id='foreign',
        operation_id='unknown-native', status='running', coordination_job_id=claim['job_id'])))
    assert asyncio.run(runtime.call(lambda: None))['status'] == 'BLOCKED'


def test_global_clock_binding_rejects_same_case_new_output_root(tmp_path, monkeypatch):
    from server.case_clock import CaseClock
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    other = tmp_path/'new-case-root'/'case-clock.sqlite3'
    fresh = CaseClock(other).start('c',14400,1800,9000,900)
    with pytest.raises(ValueError):
        c.bind_case('c',other,fresh)


def test_recovery_reserved_write_resumes_after_interruption(tmp_path, monkeypatch):
    from server.isolated_runtime import record_failure
    import sqlite3
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    row = c.get(operation_id='op')
    record_failure(tmp_path, row, 'lost reply')
    with sqlite3.connect(tmp_path/'recovery-memory.sqlite3') as db:
        db.execute("UPDATE attempts SET status='reserved', observation=''")
    record_failure(tmp_path, row, 'recovered observation')
    with sqlite3.connect(tmp_path/'recovery-memory.sqlite3') as db:
        assert db.execute('SELECT status, observation FROM attempts').fetchone() == ('inconclusive','recovered observation')
    runtime.isolated_status(operation_id='op')
    with sqlite3.connect(tmp_path/'recovery-memory.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0] == 1


def test_registered_missing_root_is_not_recreated(tmp_path, monkeypatch):
    c = domain(tmp_path, monkeypatch)
    root = tmp_path/'old'
    root.mkdir()
    c.register_root(root)
    root.rename(tmp_path/'renamed-with-unresolved-history')
    runtime = Runtime(output_root=root)
    result = asyncio.run(runtime.call(lambda: {'success':True}))
    assert result['status'] == 'BLOCKED'
    assert not root.exists()


@pytest.mark.parametrize('expired', [False, True])
def test_shared_uses_global_case_clock_from_other_output_root(tmp_path, monkeypatch, expired):
    from server.case_clock import CaseClock
    c = domain(tmp_path, monkeypatch)
    path = tmp_path/'old'/'case-clock.sqlite3'
    clock = CaseClock(path)
    snapshot = clock.start('c',14400,1800,9000,900,hard=True)
    c.bind_case('c',path,snapshot)
    if expired:
        clock.close('c','budget reached')
    runtime = Runtime(output_root=tmp_path/'new')
    result = runtime.submit_study('std1','m','attempt',task_case_id='c')
    assert result['status'] == 'BLOCKED'
    assert result['error'] == ('CASE_CLOCK_EXIT' if expired else 'HARD_DEADLINE_UNSUPPORTED')
    assert c.get(operation_id='attempt') is None


def test_relative_coordination_config_blocks(tmp_path, monkeypatch):
    domain(tmp_path,monkeypatch)
    monkeypatch.setenv('PAPER2SIMU_COORDINATION_DB','domain.sqlite3')
    runtime = Runtime(output_root=tmp_path/'out')
    result = asyncio.run(runtime.call(lambda: True))
    assert result['status'] == 'BLOCKED'
    assert result['error'] == 'ABSOLUTE_COORDINATION_PATH_REQUIRED'


def test_expiry_after_last_database_read_is_checked(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from server import isolated_runtime
    from server.coordination import Coordinator
    runtime, c, source, deadline, req, launch = approved(tmp_path, monkeypatch)
    assert runtime.submit_isolated(str(source), 'std1', 'op', deadline, 'c', req)['success']
    folder, envelope = launch.call_args.args
    original = Coordinator.case
    delayed = [False]
    class Clock:
        @staticmethod
        def now(tz):
            return datetime(2100,1,1,tzinfo=timezone.utc) if delayed[0] else datetime.now(tz)
    def late_read(self, case_id):
        result = original(self,case_id)
        delayed[0] = True
        return result
    monkeypatch.setattr(Coordinator,'case',late_read)
    monkeypatch.setattr(isolated_runtime,'datetime',Clock)
    with pytest.raises(ValueError, match='REVIEW_REQUIRED'):
        isolated_runtime.verify_launch(envelope,folder)
