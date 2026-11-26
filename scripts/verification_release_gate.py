"""Run offline release gates; missing optional formal dependencies explicitly reported."""
import argparse, hashlib, importlib.util, json, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TESTS=['test_recovery_memory.py','test_release.py','test_multi_agent_v051.py','test_agent_coordination.py','test_supervision_decision.py','test_portable_workflow.py','test_verification_gate.py','test_verification_properties.py','test_runtime_reliability.py','test_runtime_recovery_gate.py','test_runtime_capability_contract.py','test_historical_evidence.py','test_historical_ledger.py','test_historical_recovery.py']


def invoke(args,cwd=ROOT,timeout=240):
    p=subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True,timeout=timeout)
    return p.stdout.strip()


def run(output,require_hypothesis=False,tlc_jar=None,require_tlc=False):
    has_hypothesis=importlib.util.find_spec('hypothesis') is not None
    if require_hypothesis and not has_hypothesis: raise RuntimeError('Hypothesis required')
    if require_tlc and not tlc_jar: raise RuntimeError('TLC JAR required')
    report={'native_integration':'NOT_RUN','real_agent_benchmark':'NOT_RUN','full_mutmut_campaign':'NOT_RUN'}
    report['pytest']=invoke([sys.executable,'-m','pytest','-q',*[str(Path('tests')/x) for x in TESTS]])
    report['hypothesis']='PASS' if has_hypothesis else 'NOT_RUN_DEPENDENCY_MISSING'
    report['feature_map']=json.loads(invoke([sys.executable,'scripts/verification_gate.py','feature-map']))
    report['bounded_python']=json.loads(invoke([sys.executable,'scripts/verification_state.py']))
    report['targeted_mutations']=json.loads(invoke([sys.executable,'scripts/verification_mutations.py'],timeout=600))
    report['tlc']='NOT_RUN_DEPENDENCY_MISSING'
    if tlc_jar:
        with tempfile.TemporaryDirectory() as tmp:
            log=invoke(['java','-cp',str(Path(tlc_jar).resolve()),'tlc2.TLC','-workers','1','-metadir',tmp,'-config','Coordination.cfg','Coordination.tla'],ROOT/'docs/formal')
            if 'No error has been found' not in log: raise RuntimeError('TLC success message missing')
            report['tlc']='PASS';report['tlc_output']=log[-5000:]
    output=Path(output).resolve()
    report['package']=json.loads(invoke([sys.executable,'scripts/release.py','--output',str(output)]))
    with zipfile.ZipFile(output) as z:
        if z.testzip(): raise ValueError('ZIP corruption')
        m=json.loads(z.read('paper2simu/RELEASE_MANIFEST.json'))
        names={r['path'] for r in m['files']}
        required={'scripts/verification_gate.py','scripts/verification_state.py','scripts/verification_eval.py','scripts/verification_release_gate.py','scripts/verification_mutations.py','docs/formal/Coordination.tla','docs/formal/Coordination.cfg','benchmarks/agent-feature-map.json','schemas/verification-receipt.schema.json','references/recovery-history.json'}
        required.update({'server/case_clock.py','server/reliability.py','benchmarks/runtime-capability-contract.json','docs/runtime-reliability-v0.6.1.md','tests/test_runtime_capability_contract.py'})
        required.update({'server/historical_evidence.py', 'server/historical_ledger.py', 'tests/test_historical_evidence.py', 'tests/test_historical_ledger.py', 'docs/historical-ledger.md', 'docs/historical-evidence.md', 'tests/test_historical_recovery.py'})
        required.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'agent-knowledge/packs').rglob('*') if p.is_file())
        if required-names: raise ValueError('Missing release artifacts: '+str(required-names))
        for r in m['files']:
            if hashlib.sha256(z.read('paper2simu/'+r['path'])).hexdigest()!=r['sha256']: raise ValueError('Manifest mismatch')
    report['status']='OFFLINE_RELEASE_CHECKS_PASS' if has_hypothesis and report['tlc']=='PASS' else 'LOCAL_CHECKS_PASS_OPTIONAL_GATES_NOT_RUN'
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-hypothesis',action='store_true');p.add_argument('--tlc-jar',type=Path);p.add_argument('--require-tlc',action='store_true');a=p.parse_args()
    print(json.dumps(run(a.output,a.require_hypothesis,a.tlc_jar,a.require_tlc),indent=2))
