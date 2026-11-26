"""Synthetic negative controls, no live solver or external service."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from scripts.verification_gate import verify, validate_map, BASE_CHECKS, STAGE_GATES
from scripts.verification_state import State, step, explore, invariant, edge_invariant, ACTIONS
from test_multi_agent_v051 import fixture, NOW


def build(root, mode='admit', action='SOLVE'):
    s=fixture(); s.update(revision='a'*64,spec_hash='b'*64,snapshot_hash='c'*64,action=action)
    for r in s['reviews'].values():
        for k in ('revision','spec_hash','snapshot_hash'): r[k]=s[k]
    required=set(BASE_CHECKS)|{'physics'}
    if mode=='acceptance':
        s.update(reproduction=True,required_gates=['G1','G2','G3','G4','G5'],desktop_promised=True)
        s['gates']={g:dict(status='PASS',snapshot_hash=s['snapshot_hash'],evidence_verified=True,evidence_refs=['source']) for g in s['required_gates']}
        required=set().union(*STAGE_GATES.values())
    if action=='REPAIR':
        s.update(official_source_verified=True,new_evidence=True,reservation_id='d'*64)
        required.add('reservation')
    refs=[]
    for kind in sorted(required):
        a=root/(kind+'.log'); a.write_text(json.dumps({'decision':'NEW','id':'d'*64}) if kind=='reservation' else 'synthetic observation',encoding='utf-8')
        r={k:s[k] for k in ('task_id','case_id','revision','spec_hash','snapshot_hash','stage','action_id')}
        r.update(kind=kind,status='PASS',worker_id={'supervisor':'sup','physics':'phy','independent_acceptance':'acc'}.get(kind,'observer'),source='mock',observation='synthetic only',observed_utc='2028-12-31T00:00:00Z',expires_utc='2030-01-01T00:00:00Z',artifact_path=a.name,artifact_sha256=hashlib.sha256(a.read_bytes()).hexdigest())
        p=root/(kind+'.json'); p.write_text(json.dumps(r),encoding='utf-8')
        refs.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return {'mode':mode,'snapshot':s,'receipts':refs}


def replace_receipt(root, req, kind, **changes):
    ref=next(r for r in req['receipts'] if r['path']==kind+'.json')
    p=root/ref['path']; obj=json.loads(p.read_text()); obj.update(changes);p.write_text(json.dumps(obj));ref['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()


def check_pass(req,root):
    r=verify(req,root,NOW)
    assert r['action']=='EVIDENCE_BOUND_CANDIDATE',r
    assert r['execution_authorized'] is False and r['native_verified'] is False


def check_block(req,root):
    assert verify(req,root,NOW)['action']!='EVIDENCE_BOUND_CANDIDATE'


def test_positive(tmp_path): check_pass(build(tmp_path),tmp_path)

@pytest.mark.parametrize('field,value',[('active_veto',True),('job','UNKNOWN'),('job','RUNNING'),('remaining_seconds',0),('remaining_solves',0),('writer_lease_verified',False),('actual_isolation_verified',False),('parameter_level','L0'),('revision','e'*64),('scope_authorized',False),('unresolved_operation',True)])
def test_existing_admission_stays_binding(tmp_path,field,value):
    req=build(tmp_path);req['snapshot'][field]=value;check_block(req,tmp_path)

@pytest.mark.parametrize('kind',sorted(BASE_CHECKS|{'physics'}))
def test_missing_receipt(tmp_path,kind):
    req=build(tmp_path); req['receipts']=[r for r in req['receipts'] if r['path']!=kind+'.json'];check_block(req,tmp_path)


def test_tamper_artifact(tmp_path):
    req=build(tmp_path); (tmp_path/'provider.log').write_text('modified');check_block(req,tmp_path)


def test_tamper_receipt(tmp_path):
    req=build(tmp_path); p=tmp_path/'provider.json'; obj=json.loads(p.read_text());obj['observation']='changed but still valid';p.write_text(json.dumps(obj));check_block(req,tmp_path)

@pytest.mark.parametrize('changes',[{'revision':'e'*64},{'expires_utc':'2028-01-01T00:00:00Z'},{'observed_utc':'2030-01-01T00:00:00Z'},{'worker_id':'ex'},{'status':'NOT_RUN'},{'artifact_path':'../outside.txt'}])
def test_invalid_review(tmp_path,changes):
    req=build(tmp_path);replace_receipt(tmp_path,req,'supervisor',**changes);check_block(req,tmp_path)


def test_acceptance_gate(tmp_path):
    req=build(tmp_path,'acceptance');check_pass(req,tmp_path);req['snapshot']['gates']['G4']['status']='NOT_RUN';check_block(req,tmp_path)


def test_acceptance_missing_readback(tmp_path):
    req=build(tmp_path,'acceptance'); req['receipts']=[r for r in req['receipts'] if r['path']!='persistence.json'];check_block(req,tmp_path)


def test_reservation_hold(tmp_path):
    req=build(tmp_path,action='REPAIR');check_pass(req,tmp_path)
    a=tmp_path/'reservation.log';a.write_text(json.dumps({'decision':'HOLD','id':'d'*64}));replace_receipt(tmp_path,req,'reservation',artifact_sha256=hashlib.sha256(a.read_bytes()).hexdigest());check_block(req,tmp_path)


def test_feature_map(): assert validate_map()['features']>=8


def test_model_exhaustive():
    r=explore(); assert r['status']=='BOUNDED_MODEL_PASS' and r['states']>100


def test_explicit_model_invariants():
    s=step(State(),'lease_a'); assert step(s,'lease_b') is None
    s=step(s,'review'); r=step(s,'submit'); assert step(r,'submit') is None
    r=step(r,'disconnect'); assert step(r,'submit') is None and step(r,'reconcile_idle') is None
    r=step(r,'reconcile_running'); r=step(r,'complete'); r=step(r,'accept'); assert r.accepted==0
    r=step(r,'review'); r=step(r,'edit'); assert r.accepted==r.review==r.solved==-1
    r=step(r,'review'); r=step(r,'veto'); assert step(r,'submit') is None
    r=step(r,'tick'); r=step(r,'tick'); assert step(r,'submit') is None


def test_paired_eval():
    from scripts.verification_eval import evaluate,fingerprint
    plan={'cases':[{'id':'a','split':'holdout'},{'id':'b','split':'holdout'}]}
    def row(i,ok,forbidden=False): return dict(id=i,outcome_correct=ok,forbidden_action=forbidden,false_acceptance=False,evidence_ref='synthetic')
    a=dict(plan_sha256=fingerprint(plan),configuration='base',results=[row('a',True),row('b',True,True)])
    b=dict(plan_sha256=fingerprint(plan),configuration='new',results=[row('a',True)])
    r=evaluate(plan,a,b);assert r['baseline']['forbidden_action_cases']==1 and r['candidate']['missing']==['b'] and r['paired_success_rate_delta']==0
