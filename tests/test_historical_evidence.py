"""Synthetic evidence and ephemeral authorities for verifier tests only."""
import base64
import hashlib
import json
import socket
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from server.historical_evidence import canonical, verify


def artifact(path, data):
    path.write_bytes(data)
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(data).hexdigest())


def sign(packet, keys):
    for role, field, now in [('independent_reviewer','review',110), ('resource_admin','approval',120)]:
        body = dict(protocol='paper2simu-reconciliation-v1', role=role, statement=packet['statement'],
                    principal=role, signed_at=now)
        if field == 'approval':
            body['review'] = packet['review']
        signature = base64.b64encode(keys[role].sign(canonical(body))).decode()
        packet[field] = dict(principal=role, signed_at=now, signature=signature)


def build_packet(tmp_path):
    host = socket.gethostname().casefold()
    path = tmp_path/'job-manifests'/'job-test.json'
    path.parent.mkdir(exist_ok=True)
    row = dict(job_id=path.stem, operation_id='op-test', status='running',
               submitted_at=10, model_name='demo', study_name='test')
    manifest = artifact(path, canonical(row))
    origin = {k:v for k,v in row.items() if k != 'status'}
    origin.update(host_id=host, resource_id='lab', execution_site='LOCAL_ONLY',
                  source_artifacts=[artifact(tmp_path/'connection.log', b'local-only test connection')])
    xml = (f'<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System>'
           f'<Provider Name="Microsoft-Windows-Kernel-General"/><EventID>12</EventID><Channel>System</Channel>'
           f'<Computer>{host}</Computer><TimeCreated SystemTime="1970-01-01T00:01:40Z"/></System></Event>')
    s = dict(job_id=row['job_id'], operation_id=row['operation_id'], manifest_path=manifest['path'],
             manifest_sha256=manifest['sha256'], host_id=host, resource_id='lab', event_at=100,
             historical_status='running', process_lifecycle='LOCAL_PROCESS_ENDED_BY_BOOT_BOUNDARY',
             native_result='LOST_UNVERIFIED', resource_scope='CLEAR_THIS_HISTORICAL_BLOCK_ONLY',
             scientific_status='UNVERIFIED', historical_budget='UNCHANGED',
             evidence={'origin':artifact(tmp_path/'origin.json',canonical(origin)),
                       'boot':artifact(tmp_path/'boot.xml',xml.encode())})
    keys = {r:Ed25519PrivateKey.generate() for r in ['resource_admin','independent_reviewer']}
    trust = tmp_path/'trust.json'
    trust.write_bytes(canonical(dict(host_id=host,resource_id='lab',principals={
        r:dict(role=r,public_key=base64.b64encode(k.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()) for r,k in keys.items()})))
    packet = dict(statement=s)
    sign(packet,keys)
    return packet,path,trust,keys


def test_valid(tmp_path):
    p,m,t,_ = build_packet(tmp_path)
    assert verify(p,m,'lab',t)['historical_budget'] == 'UNCHANGED'
    assert json.loads(m.read_bytes())['status'] == 'running'


@pytest.mark.parametrize('change',['missing_admin','missing_review','manifest','domain','host','replaced',
                                   'missing','source_changed','remote','scope','key','tamper','earlier','other_model'])
def test_invalid(tmp_path,change):
    p,m,t,keys = build_packet(tmp_path)
    s = p['statement']
    if change == 'missing_admin': del p['approval']
    elif change == 'missing_review': del p['review']
    elif change == 'manifest': m.write_bytes(m.read_bytes()+b' ')
    elif change == 'domain': s['resource_id']='elsewhere'; sign(p,keys)
    elif change == 'host': s['host_id']='another-host'; sign(p,keys)
    elif change == 'replaced': Path(s['evidence']['boot']['path']).write_bytes(b'<x/>')
    elif change == 'missing': Path(s['evidence']['origin']['path']).unlink()
    elif change == 'source_changed':
        (tmp_path/'connection.log').write_text('different connection')
    elif change in ('remote','other_model'):
        path=Path(s['evidence']['origin']['path'])
        origin=json.loads(path.read_bytes())
        origin.update({'execution_site':'REMOTE'} if change=='remote' else {'model_name':'other'})
        s['evidence']['origin']=artifact(path,canonical(origin)); sign(p,keys)
    elif change == 'scope': s['native_result']='completed'; sign(p,keys)
    elif change == 'key':
        keys['resource_admin']=keys['independent_reviewer']
        tr=json.loads(t.read_bytes()); tr['principals']['resource_admin']['public_key']=tr['principals']['independent_reviewer']['public_key']
        t.write_bytes(canonical(tr)); sign(p,keys)
    elif change == 'earlier':
        s['event_at']=5
        path=Path(s['evidence']['boot']['path'])
        s['evidence']['boot']=artifact(path,path.read_bytes().replace(b'00:01:40',b'00:00:05'))
        sign(p,keys)
    else: p['review']['signed_at']+=1
    with pytest.raises(ValueError): verify(p,m,'lab',t)


@pytest.mark.parametrize("fields", [
    {"started_at": 105}, {"completed_at": 101}, {"native_started_at_unix": 100},
    {"events": [{"time": 101, "message": "Solving study"}]},
])
def test_boot_must_follow_original_execution(tmp_path, fields):
    packet, path, trust, keys = build_packet(tmp_path)
    row = json.loads(path.read_bytes())
    row.update(fields)
    packet["statement"]["manifest_sha256"] = artifact(path, canonical(row))["sha256"]
    sign(packet, keys)
    with pytest.raises(ValueError, match="original execution timestamps"):
        verify(packet, path, "lab", trust)


def test_postboot_observation_and_windows_timestamp(tmp_path):
    packet, path, trust, keys = build_packet(tmp_path)
    s = packet["statement"]
    row = json.loads(path.read_bytes())
    row.update(recovered_at=102, last_polled_at=103, events=[{"time": 20, "message": "Solving study"}])
    s["manifest_sha256"] = artifact(path, canonical(row))["sha256"]
    boot = Path(s["evidence"]["boot"]["path"])
    s["evidence"]["boot"] = artifact(boot, boot.read_bytes().replace(b"40Z", b"40.1234567Z"))
    s["event_at"] = 100.1234567
    sign(packet, keys)
    assert verify(packet, path, "lab", trust) == s
