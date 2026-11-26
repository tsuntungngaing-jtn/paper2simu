"""Offline recovery memory and original pack integrity checks."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/recovery_memory.py'

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'memory.sqlite3'
    def call(self,*args,ok=True,db=None):
        p=subprocess.run([sys.executable,str(SCRIPT),'--db',str(db or self.db),*args],capture_output=True,text=True,encoding='utf-8')
        if ok:
            self.assertEqual(p.returncode,0,p.stderr); return json.loads(p.stdout)
        self.assertNotEqual(p.returncode,0)
    def reserve(self,evidence=''):
        return self.call('reserve','--case','test','--build','6.3','--revision','a'*64,'--action','inspect-selection','--symptom','压力点选区为空','--evidence',evidence)
    def test_lookup(self):
        r=self.call('lookup','压力点选区为空'); self.assertTrue(r['cards_loaded']); self.assertTrue(r['cards']); self.assertTrue(any(x['id']=='P031-R16E' for x in r['history']))
    def test_duplicate(self):
        a,b=self.reserve(),self.reserve(); self.assertEqual((a['decision'],b['decision']),('NEW','HOLD')); self.assertEqual(a['id'],b['id']); self.assertEqual(self.reserve('b'*64)['decision'],'NEW'); self.assertEqual(self.reserve('B'*64)['decision'],'HOLD')
    def test_concurrency(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(lambda _:self.reserve(),range(4)))
        self.assertEqual(sum(r['decision']=='NEW' for r in results),1); self.assertEqual(len({r['id'] for r in results}),1)
    def test_finish(self):
        i=self.reserve()['id']; self.call('finish',i,'observed','readback'); self.call('finish',i,'observed','readback'); self.call('finish',i,'failed','conflict',ok=False); self.assertEqual(self.reserve()['prior_status'],'observed')
    def test_invalid_input(self):
        self.call('lookup','x',db=Path(self.temp.name)/'seed.json',ok=False); self.call('reserve','--case','c','--build','6.3','--revision','timestamp','--action','a','--symptom','x',ok=False)
    def test_manifest(self):
        counts=[]
        for name in ['Paper2Simu-Knowledge-r1','Paper2Simu-Solver-Knowledge-r2']:
            r=ROOT/'agent-knowledge/packs'/name; m=json.loads((r/'manifest.json').read_text(encoding='utf-8'))
            for p,h in m.get('sha256',m.get('files')).items(): self.assertEqual(hashlib.sha256((r/p).read_bytes()).hexdigest(),h,p)
            counts.append(sum(len([json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]) for p in r.rglob('rules.jsonl')))
        self.assertEqual(counts,[15,106])
if __name__=='__main__': unittest.main()
