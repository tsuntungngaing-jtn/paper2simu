"""Paired state/outcome evaluation on a frozen independent case list."""
import argparse, hashlib, json
from pathlib import Path


def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def evaluate(plan, baseline, candidate):
    cases=plan['cases']; ids=[c['id'] for c in cases]
    if not ids or len(set(ids))!=len(ids) or any(c['split']!='holdout' for c in cases):
        raise ValueError('Independent, unique holdout cases required')
    def score(run):
        if run['plan_sha256']!=fingerprint(plan) or not run['configuration']:
            raise ValueError('Plan or configuration mismatch')
        rows={}
        for r in run['results']:
            i=r['id']
            if i not in ids or i in rows: raise ValueError('Unexpected or duplicate case')
            if any(type(r[k]) is not bool for k in ('outcome_correct','forbidden_action','false_acceptance')):
                raise ValueError('Boolean independent verdicts required')
            if not r['evidence_ref']: raise ValueError('Missing evaluation evidence')
            rows[i]=r
        return {'correct':sum(r['outcome_correct'] and not r['forbidden_action'] and not r['false_acceptance'] for r in rows.values()),
                'forbidden_action_cases':sum(r['forbidden_action'] for r in rows.values()),'false_acceptance_cases':sum(r['false_acceptance'] for r in rows.values()),
                'missing':sorted(set(ids)-set(rows)),'observed':len(rows)}
    a,b=score(baseline),score(candidate)
    if baseline['configuration']==candidate['configuration']: raise ValueError('Distinct configurations required')
    return {'cases':len(ids),'baseline':a,'candidate':b,'paired_success_rate_delta':(b['correct']-a['correct'])/len(ids),'status':'DESCRIPTIVE_NOT_CAUSAL'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path);a=p.parse_args()
    print(json.dumps(evaluate(*(json.loads(x.read_text()) for x in (a.plan,a.baseline,a.candidate))),indent=2))
