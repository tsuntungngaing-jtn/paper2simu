"""Persistent task clock. Local operator-controlled DB, not native stop authority."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time
from contextlib import contextmanager

HEX=re.compile(r"^[0-9a-f]{64}$")
ID=re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

def number(v):
    return type(v) in (int,float) and math.isfinite(v)

class CaseClock:
    def __init__(self, path, now=time.time):
        self.path=Path(path).resolve()
        self.now=now
    @contextmanager
    def transaction(self, create=False):
        if not create and not self.path.is_file():
            raise ValueError("Case clock missing")
        if create: self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(str(self.path),timeout=3)
        db.row_factory=sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            if create:
                db.execute("""CREATE TABLE IF NOT EXISTS cases(
                    id TEXT PRIMARY KEY, started REAL NOT NULL, total REAL NOT NULL,
                    wrap REAL NOT NULL, solve REAL NOT NULL, stall REAL NOT NULL,
                    hard INTEGER NOT NULL, last_progress REAL NOT NULL,
                    last_seen REAL NOT NULL, phase TEXT NOT NULL, reason TEXT,
                    active INTEGER NOT NULL)""")
                db.execute("CREATE UNIQUE INDEX IF NOT EXISTS single_active ON cases(active) WHERE active=1")
                db.execute("CREATE TABLE IF NOT EXISTS progress(case_id TEXT, hash TEXT, observed REAL, PRIMARY KEY(case_id,hash))")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally: db.close()
    def _time(self):
        n=self.now()
        if not number(n) or n<0: raise ValueError("Invalid clock")
        return float(n)
    def _read(self, db, case_id=None):
        row=db.execute("SELECT * FROM cases WHERE active=1" if case_id is None else "SELECT * FROM cases WHERE id=?", () if case_id is None else (case_id,)).fetchone()
        if row is None: raise ValueError("No matching case clock")
        return dict(row)
    def _evaluate(self, db, row, n):
        phase,reason=row["phase"],row["reason"]
        if n<row["last_seen"] and phase!="EXIT":
            phase,reason="EXIT","CLOCK_REGRESSION"
        if phase=="OPEN":
            if n>=row["started"]+row["total"]:
                phase,reason="EXIT","CASE_DEADLINE"
            elif n>=row["last_progress"]+row["stall"]:
                phase,reason="EXIT","NO_VERIFIED_PROGRESS"
            elif n>=row["started"]+row["total"]-row["wrap"]:
                phase,reason="EXIT","WRAP_WINDOW"
        db.execute("UPDATE cases SET last_seen=?,phase=?,reason=? WHERE id=?",
                   (max(n,row["last_seen"]),phase,reason,row["id"]))
        row.update(phase=phase,reason=reason,last_seen=max(n,row["last_seen"]))
        return self._report(row,n)
    @staticmethod
    def _report(r,n):
        return {"case_id":r["id"],"phase":r["phase"],"reason":r["reason"],
                "active":bool(r["active"]),"started_at_unix":r["started"],
                "deadline_at_unix":r["started"]+r["total"],
                "new_work_cutoff_unix":r["started"]+r["total"]-r["wrap"],
                "last_verified_progress_at_unix":r["last_progress"],
                "last_seen_at_unix":r["last_seen"],
                "remaining_seconds":max(0,r["started"]+r["total"]-max(n,r["last_seen"])),
                "solve_limit_seconds":r["solve"],"stall_seconds":r["stall"],
                "require_hard_deadline":bool(r["hard"]),
                "native_stop_verified":False}
    def start(self,case_id,total,wrap,solve,stall,hard=True):
        if not isinstance(case_id,str) or not ID.fullmatch(case_id): raise ValueError("Invalid case ID")
        if type(hard) is not bool or not all(number(x) and x>0 for x in (total,wrap,solve,stall)) or wrap>=total or solve>total or stall>total:
            raise ValueError("Invalid immutable case budget")
        with self.transaction(create=True) as db:
            n=self._time()
            old=db.execute("SELECT * FROM cases WHERE id=?",(case_id,)).fetchone()
            if old:
                row=dict(old)
                if (row["total"],row["wrap"],row["solve"],row["stall"],bool(row["hard"]))!=(total,wrap,solve,stall,hard):
                    raise ValueError("Existing case budget is immutable")
                return self._evaluate(db,row,n)
            active=db.execute("SELECT * FROM cases WHERE active=1").fetchone()
            if active:
                state=self._evaluate(db,dict(active),n)
                if state["phase"]!="EXIT": raise ValueError("Prior case still open")
                db.execute("UPDATE cases SET active=0 WHERE active=1")
            db.execute("INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (case_id,n,total,wrap,solve,stall,int(hard),n,n,"OPEN",None,1))
            return self._report(self._read(db),n)
    def status(self,case_id=None):
        with self.transaction() as db:
            return self._evaluate(db,self._read(db,case_id),self._time())
    def observe(self,case_id,evidence_hash,observed_at):
        """Trusted observer supplies hash of NEW native progress bytes, not a polling receipt."""
        if not isinstance(evidence_hash,str) or not HEX.fullmatch(evidence_hash) or not number(observed_at):
            raise ValueError("Invalid progress evidence")
        with self.transaction() as db:
            n=self._time(); row=self._read(db,case_id)
            state=self._evaluate(db,row,n)
            if not state["active"] or state["phase"]!="OPEN": return dict(state,progress_accepted=False)
            if not row["last_progress"]<observed_at<=n: return dict(state,progress_accepted=False)
            if db.execute("SELECT 1 FROM progress WHERE case_id=? AND hash=?",(case_id,evidence_hash)).fetchone():
                return dict(state,progress_accepted=False)
            db.execute("INSERT INTO progress VALUES(?,?,?)",(case_id,evidence_hash,observed_at))
            db.execute("UPDATE cases SET last_progress=? WHERE id=?",(observed_at,case_id))
            row["last_progress"]=observed_at
            return dict(self._report(row,n),progress_accepted=True)
    def close(self,case_id,reason):
        if not isinstance(reason,str) or not reason.strip(): raise ValueError("Reason required")
        with self.transaction() as db:
            n=self._time(); row=self._read(db,case_id)
            result=self._evaluate(db,row,n)
            if result["phase"]=="OPEN":
                db.execute("UPDATE cases SET phase='EXIT',reason=? WHERE id=?",(reason,case_id))
                row.update(phase="EXIT",reason=reason)
                result=self._report(row,n)
            return result

def admission(path, case_id, now=time.time):
    """Only a local queue budget check. No native permission or stop capability."""
    try:
        state=CaseClock(path,now).status()
        if not isinstance(case_id,str) or case_id!=state["case_id"]:
            return {"allowed":False,"error":"CASE_CLOCK_ID_MISMATCH","clock":state}
        if state["phase"]!="OPEN":
            return {"allowed":False,"error":"CASE_CLOCK_EXIT","clock":state}
        if state["require_hard_deadline"]:
            return {"allowed":False,"error":"HARD_DEADLINE_UNSUPPORTED","clock":state}
        return {"allowed":True,"clock":state}
    except (OSError,sqlite3.Error,ValueError,TypeError) as exc:
        return {"allowed":False,"error":"CASE_CLOCK_UNAVAILABLE","detail":type(exc).__name__}

def watch(clock,case_id,interval,max_seconds):
    """Independent bounded local observer. Emits only status/exit; never kills jobs."""
    if not number(interval) or not 1<=interval<=60 or not number(max_seconds) or max_seconds<=0:
        raise ValueError("Invalid observer bounds")
    end=time.monotonic()+max_seconds
    while True:
        result=clock.status(case_id)
        print(json.dumps(result),flush=True)
        if result["phase"]=="EXIT" or not result["active"] or time.monotonic()>=end: return result
        time.sleep(min(interval,max(0,end-time.monotonic())))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db",required=True,type=Path)
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("start");s.add_argument("case_id")
    for name in ("total","wrap","solve","stall"): s.add_argument("--"+name,required=True,type=float,help="seconds")
    s.add_argument("--allow-soft",action="store_true",help="Only with explicit task authorization")
    s=sub.add_parser("status");s.add_argument("case_id",nargs="?")
    s=sub.add_parser("observe");s.add_argument("case_id");s.add_argument("evidence_hash");s.add_argument("observed_at",type=float)
    s=sub.add_parser("close");s.add_argument("case_id");s.add_argument("reason")
    s=sub.add_parser("watch");s.add_argument("case_id");s.add_argument("--interval",type=float,default=30);s.add_argument("--max-seconds",type=float,required=True)
    a=p.parse_args();c=CaseClock(a.db)
    if a.cmd=="start": result=c.start(a.case_id,a.total,a.wrap,a.solve,a.stall,not a.allow_soft)
    elif a.cmd=="status": result=c.status(a.case_id)
    elif a.cmd=="observe": result=c.observe(a.case_id,a.evidence_hash,a.observed_at)
    elif a.cmd=="close": result=c.close(a.case_id,a.reason)
    else: watch(c,a.case_id,a.interval,a.max_seconds);return
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
