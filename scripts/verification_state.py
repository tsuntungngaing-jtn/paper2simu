"""Finite abstract coordination model, independently executable without TLC."""
from dataclasses import dataclass, replace
from collections import deque
import json

ACTIONS=('lease_a','lease_b','release','review','veto','clear_veto','submit','disconnect',
         'reconcile_idle','reconcile_running','complete','edit','accept','tick','close')

@dataclass(frozen=True)
class State:
    writer: str='NONE'
    job: str='IDLE'
    revision: int=0
    review: int=-1
    solved: int=-1
    accepted: int=-1
    veto: bool=False
    time: int=2
    submissions: int=0
    closed: bool=False


def step(s,a):
    if s.closed: return None
    if a in ('lease_a','lease_b') and s.writer=='NONE' and s.job=='IDLE' and s.time>0:
        return replace(s,writer=a[-1])
    if a=='release' and s.writer!='NONE' and s.job=='IDLE': return replace(s,writer='NONE',review=-1)
    if a=='review' and s.writer!='NONE' and s.job=='IDLE' and not s.veto and s.time>0: return replace(s,review=s.revision)
    if a=='veto' and not s.veto: return replace(s,veto=True,review=-1,accepted=-1)
    if a=='clear_veto' and s.veto and s.job=='IDLE': return replace(s,veto=False,review=-1)
    if a=='submit' and s.writer!='NONE' and s.job=='IDLE' and s.review==s.revision and not s.veto and s.time>0 and s.submissions<2:
        return replace(s,job='RUNNING',submissions=s.submissions+1,solved=-1,accepted=-1,review=-1)
    if a=='disconnect' and s.job in ('IDLE','RUNNING'): return replace(s,job='UNKNOWN_RUNNING' if s.job=='RUNNING' else 'UNKNOWN_IDLE',review=-1,accepted=-1)
    if a=='reconcile_idle' and s.job=='UNKNOWN_IDLE': return replace(s,job='IDLE')
    if a=='reconcile_running' and s.job=='UNKNOWN_RUNNING': return replace(s,job='RUNNING')
    if a=='complete' and s.job=='RUNNING': return replace(s,job='IDLE',solved=s.revision,review=-1)
    if a=='edit' and s.writer!='NONE' and s.job=='IDLE' and s.review==s.revision and not s.veto and s.time>0 and s.revision<2:
        return replace(s,revision=s.revision+1,review=-1,solved=-1,accepted=-1)
    if a=='accept' and s.job=='IDLE' and s.solved==s.revision and not s.veto:
        return replace(s,accepted=s.revision)
    if a=='tick' and s.time>0: return replace(s,time=s.time-1,review=-1 if s.time==1 else s.review)
    if a=='close' and s.time==0 and s.job=='IDLE': return replace(s,closed=True,writer='NONE',review=-1)
    return None


def invariant(s):
    return (s.writer in ('NONE','a','b') and 0<=s.time<=2 and 0<=s.submissions<=2 and
            (s.review==-1 or s.review==s.revision) and
            (s.solved==-1 or s.solved==s.revision) and
            (s.accepted==-1 or (s.accepted==s.revision==s.solved and s.job=='IDLE' and not s.veto)) and
            (s.job not in ('RUNNING','UNKNOWN_RUNNING') or s.writer!='NONE') and
            (not s.closed or (s.job=='IDLE' and s.time==0 and s.writer=='NONE')))


def edge_invariant(s,a,t):
    if not invariant(t): return False
    if t.submissions>s.submissions:
        if not (a=='submit' and s.job=='IDLE' and s.writer!='NONE' and not s.veto and s.review==s.revision and s.time>0): return False
    if s.revision!=t.revision and (t.review,t.solved,t.accepted)!=(-1,-1,-1): return False
    if t.time>s.time: return False
    return True


def explore():
    init=State(); seen={init}; q=deque([(init,[])]); edges=0
    while q:
        s,trail=q.popleft()
        if not invariant(s): raise AssertionError(trail)
        for a in ACTIONS:
            t=step(s,a)
            if t is None: continue
            edges+=1
            if not edge_invariant(s,a,t): raise AssertionError(trail+[a])
            if t not in seen: seen.add(t);q.append((t,trail+[a]))
    return {'status':'BOUNDED_MODEL_PASS','states':len(seen),'transitions':edges,'native_verified':False,'scope':'two writer candidates; two revisions, submissions and abstract ticks; not TLC or a live runtime proof'}

if __name__=='__main__': print(json.dumps(explore(),indent=2))
