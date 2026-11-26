"""Evidence-bound, offline verification. Never a live provider permission grant."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
try:
    from scripts.check_multi_agent_v051 import admit, acceptance
except ModuleNotFoundError:  # CLI execution from scripts/
    from check_multi_agent_v051 import admit, acceptance

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ('task_id','case_id','revision','spec_hash','snapshot_hash','stage','action_id')
HASH_FIELDS = ('revision','spec_hash','snapshot_hash')
KINDS = ('provider','lease','checkpoint','budget','supervisor','physics','reservation',
         'source_inputs','geometry','mesh','physics_model','solution','postprocessing','persistence','independent_acceptance')
BASE_CHECKS = {'provider','lease','checkpoint','budget','supervisor'}
STAGE_GATES = {'G1':{'source_inputs'},'G2':{'geometry','physics_model'},
               'G3':{'mesh','solution'},'G4':{'postprocessing','independent_acceptance'},'G5':{'persistence'}}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hash_ok(value):
    return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value) is not None


def nonempty(value):
    return isinstance(value,str) and bool(value.strip())


def utc(value):
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.utcoffset() is None or d.utcoffset().total_seconds()!=0:
        raise ValueError('UTC required')
    return d


def within(root, rel):
    if not nonempty(rel) or Path(rel).is_absolute():
        raise ValueError('Relative path required')
    p=(root/rel).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError('Missing or out-of-workspace artifact')
    return p


def read_receipt(root, ref, snapshot, now):
    p=within(root,ref['path']); data=p.read_bytes()
    if not hash_ok(ref.get('sha256')) or digest(data)!=ref['sha256']:
        raise ValueError('Receipt hash mismatch')
    r=json.loads(data)
    if r['kind'] not in KINDS or r['status']!='PASS':
        raise ValueError('Invalid kind or non-PASS receipt')
    if any(r.get(k)!=snapshot[k] for k in IDENTITY):
        raise ValueError('Receipt identity mismatch')
    if not all(nonempty(r.get(k)) for k in ('worker_id','source','observation')):
        raise ValueError('Receipt lacks provenance or observation')
    observed,expires=utc(r['observed_utc']),utc(r['expires_utc'])
    if not observed<=now<expires:
        raise ValueError('Stale/future receipt')
    # Hash the original recorded artifact, not just a PASS declaration.
    art=within(root,r['artifact_path'])
    if art==p or not hash_ok(r.get('artifact_sha256')) or digest(art.read_bytes())!=r['artifact_sha256']:
        raise ValueError('Observation artifact mismatch')
    return r


def verify(request, workspace, now=None):
    """Add artifact/revision binding to existing policy. Fail closed on invalid data."""
    now=now or datetime.now(timezone.utc); root=Path(workspace).resolve()
    result={'action':'BLOCK','execution_authorized':False,'native_verified':False,'reason':'invalid request'}
    try:
        s=request['snapshot']; mode=request['mode']
        if any(not nonempty(s.get(k)) for k in IDENTITY) or any(not hash_ok(s[k]) for k in HASH_FIELDS):
            raise ValueError('Snapshot requires complete identity and content hashes')
        if mode=='admit':
            prior=admit(s,now)
            if prior['action']!='ADMISSION_CANDIDATE':
                return prior
            required=set(BASE_CHECKS)
            if s['action'] in ('SOLVE','REPAIR') or s.get('parameter_level') in ('L2','L3'): required.add('physics')
            if s['action']=='REPAIR': required.add('reservation')
        elif mode=='acceptance':
            prior=acceptance(s,now)
            if prior['action']!='DECLARED_ACCEPTANCE_CANDIDATE': return prior
            required=set().union(*(STAGE_GATES[g] for g in s['required_gates']))
        else: raise ValueError('Unsupported verification mode')
        receipts={}
        for ref in request['receipts']:
            r=read_receipt(root,ref,s,now)
            if r['kind'] in receipts: raise ValueError('Duplicate receipt kind')
            receipts[r['kind']]=r
        missing=required-set(receipts)
        if missing: raise ValueError('Missing receipts: '+','.join(sorted(missing)))
        # Reviews must match the existing independent reviewer identity.
        for kind,role in [('supervisor','supervisor'),('physics','physics_reviewer'),('independent_acceptance','acceptance_agent')]:
            if kind in required and receipts[kind]['worker_id']!=s['reviews'][role]['worker_id']:
                raise ValueError('Receipt reviewer identity mismatch')
        if 'reservation' in required:
            r=receipts['reservation']
            # The recorded reservation must reference this action; host still rechecks live DB.
            record=json.loads(within(root,r['artifact_path']).read_text(encoding='utf-8'))
            if record.get('decision')!='NEW' or not hash_ok(record.get('id')) or record['id']!=s.get('reservation_id'):
                raise ValueError('No matching new recovery reservation')
        return {'action':'EVIDENCE_BOUND_CANDIDATE','prior_action':prior['action'],'receipts':sorted(required),
                'execution_authorized':False,'native_verified':False,'reason':'Local artifacts and declared gates matched; live host enforcement and independent source/physics checks still required'}
    except (KeyError,TypeError,ValueError,AttributeError,OSError,OverflowError) as exc:
        result['reason']=str(exc); return result


def validate_map(root=ROOT):
    root=Path(root).resolve(); payload=json.loads((root/'benchmarks/agent-feature-map.json').read_text(encoding='utf-8'))
    ids=set()
    registry=json.loads((root/'agent-knowledge/registry.json').read_text(encoding='utf-8'))
    for f in payload['features']:
        if not nonempty(f.get('id')) or f['id'] in ids or f.get('owner') not in registry['roles']:
            raise ValueError('Feature ID/owner invalid')
        ids.add(f['id'])
        for k in ('contract','test','failure_route'): within(root,f[k])
        if not f.get('observations') or not all(nonempty(x) for x in f['observations']):
            raise ValueError('Missing expected observations')
    if not ids: raise ValueError('Empty feature map')
    return {'status':'MAP_STRUCTURE_PASS','features':len(ids),'native_verified':False}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('verify');q.add_argument('request',type=Path);q.add_argument('workspace',type=Path)
    sub.add_parser('feature-map');a=p.parse_args()
    result=validate_map() if a.cmd=='feature-map' else verify(json.loads(a.request.read_text(encoding='utf-8')),a.workspace)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result.get('status')=='MAP_STRUCTURE_PASS' or result.get('action')=='EVIDENCE_BOUND_CANDIDATE' else 1)

if __name__=='__main__': main()
