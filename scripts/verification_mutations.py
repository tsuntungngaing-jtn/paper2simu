"""Targeted mutation regression on isolated copies of the actual Python gates.
This is not a full mutmut campaign. Every designated mutant must be killed.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MUTANTS={
    'skip_receipt_hash':('verification_gate.py',"if not hash_ok(ref.get('sha256')) or digest(data)!=ref['sha256']:","if False:"),
    'skip_artifact_hash':('verification_gate.py',"if art==p or not hash_ok(r.get('artifact_sha256')) or digest(art.read_bytes())!=r['artifact_sha256']:","if False:"),
    'skip_freshness':('verification_gate.py',"if not observed<=now<expires:","if False:"),
    'skip_missing_receipts':('verification_gate.py',"if missing: raise ValueError('Missing receipts: '+','.join(sorted(missing)))","if False: raise ValueError('Missing receipts')"),
    'ignore_hold':('verification_gate.py',"record.get('decision')!='NEW' or ","False or "),
    'ignore_veto':('check_multi_agent_v051.py',"if s.get(\"active_veto\") is not False:","if False:"),
    'keep_stale_acceptance':('verification_state.py',"revision=s.revision+1,review=-1,solved=-1,accepted=-1)","revision=s.revision+1,review=-1,solved=-1,accepted=s.accepted)"),
    'allow_duplicate_writer':('verification_state.py',"and s.writer=='NONE' and s.job=='IDLE' and s.time>0:","and s.job=='IDLE' and s.time>0:")
}

def run(root=ROOT):
    root=Path(root).resolve(); results=[]
    with tempfile.TemporaryDirectory(prefix='p2s-mutation-') as tmp:
        copy=Path(tmp)/'repo'
        shutil.copytree(root,copy,ignore=shutil.ignore_patterns('.git','.venv','runtime','runs','__pycache__','.pytest_cache','.hypothesis','dist','build'))
        test=['tests/test_verification_gate.py']
        cmd=[sys.executable,'-m','pytest','-q',*test]
        base=subprocess.run(cmd,cwd=copy,capture_output=True,text=True,timeout=120)
        if base.returncode: raise RuntimeError('Baseline failed: '+base.stdout[-3000:]+' '+base.stderr[-1000:])
        for name,(file,before,after) in MUTANTS.items():
            p=copy/'scripts'/file;original=p.read_text(encoding='utf-8')
            if original.count(before)!=1: raise RuntimeError('Mutation anchor missing or ambiguous: '+name)
            try:
                changed=original.replace(before,after,1)
                compile(changed,str(p),'exec')
                p.write_text(changed,encoding='utf-8')
                shutil.rmtree(p.parent/'__pycache__',ignore_errors=True)
                r=subprocess.run(cmd,cwd=copy,capture_output=True,text=True,timeout=120)
                status='KILLED' if r.returncode==1 and 'failed' in r.stdout else 'SURVIVED' if r.returncode==0 else 'ERROR'
                results.append({'id':name,'status':status,'summary':r.stdout.splitlines()[-1] if r.stdout else r.stderr[-250:]})
            finally:
                p.write_text(original,encoding='utf-8'); shutil.rmtree(p.parent/'__pycache__',ignore_errors=True)
    return {'status':'TARGETED_MUTATIONS_PASS' if all(r['status']=='KILLED' for r in results) else 'FAIL','mutants':results,'count':len(results),'killed':sum(r['status']=='KILLED' for r in results),'full_mutmut_campaign':'NOT_RUN'}

if __name__=='__main__':
    r=run();print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='TARGETED_MUTATIONS_PASS' else 1)
