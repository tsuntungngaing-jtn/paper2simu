"""Offline recovery memory. The host owns reservations and outcome writes."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import hashlib

ROOT = Path(__file__).resolve().parents[1]
SEED = json.loads((ROOT / "references/recovery-history.json").read_text(encoding="utf8"))

def tokens(text):
    text = text.casefold()
    for aliases in [("空集", "为空", "变空", "空了", "empty selection"), ("压力点", "pressure point")]:
        for alias in aliases:
            text = text.replace(alias, aliases[0])
    words = set(re.findall(r"[a-z0-9]+", text))
    for run in re.findall(r"[\u3400-\u9fff]+", text):
        words.update(run[i:i+2] for i in range(len(run)-1))
    return words

def run(a):
    if not all(v.strip() for k,v in vars(a).items() if isinstance(v,str) and k!="evidence"):
        raise ValueError("Nonempty identifiers required")
    db_path = a.db.resolve()
    if db_path.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
        raise ValueError("Use a private SQLite database (.sqlite/.sqlite3/.db), not a JSON seed")
    if db_path.is_relative_to(ROOT) and not db_path.is_relative_to(ROOT / "runtime"):
        raise ValueError("Database must be outside the repository or under ignored runtime/")
    if a.command == "reserve":
        for field in ("revision", "evidence"):
            value = getattr(a, field).strip()
            if (field == "revision" or value) and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
                raise ValueError(f"{field} must be a SHA-256 content hash")
    a.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(a.db, timeout=20) as db:
        db.execute("CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, body TEXT NOT NULL, status TEXT NOT NULL, observation TEXT NOT NULL)")
        if a.command in {"reserve", "finish"}:
            db.execute("BEGIN IMMEDIATE")
        if a.command=="lookup":
            records = list(SEED)
            for key,body,status,observation in db.execute("SELECT * FROM attempts"):
                records.append(dict(**json.loads(body), id=key,status=status,observation=observation))
            cards=a.cards
            if cards is None:
                packaged = ROOT / "agent-knowledge/packs/Paper2Simu-Solver-Knowledge-r2/rules.jsonl"
                cards = packaged if packaged.is_file() else None
            if cards:
                for line in cards.read_text(encoding="utf8").splitlines():
                    c=json.loads(line)
                    records.append(dict(id=c["id"],symptom=c["title"],status=c["status"],action=c["content"]["action"],editions=c["editions"],evidence=c["evidence"]))
            query=tokens(a.query)
            def score(r):
                return len(query & tokens(" ".join(str(r.get(k,"")) for k in ("symptom","action","observation"))))
            ranked=sorted((r for r in records if score(r)),key=score,reverse=True)
            return dict(history=[r for r in ranked if "editions" not in r][:8],cards=[r for r in ranked if "editions" in r][:8],cards_loaded=bool(cards))
        if a.command=="reserve":
            body={k:getattr(a,k).strip() for k in ("case","build","revision","action","evidence","symptom")}
            body["revision"] = body["revision"].lower()
            body["evidence"] = body["evidence"].lower()
            key=hashlib.sha256(json.dumps([body[k] for k in ("case","build","revision","action","evidence")],ensure_ascii=False).encode()).hexdigest()
            inserted=db.execute("INSERT OR IGNORE INTO attempts VALUES (?,?,?,?)",(key,json.dumps(body,ensure_ascii=False),"reserved","")).rowcount
            return dict(id=key,decision="NEW" if inserted else "HOLD",prior_status=db.execute("SELECT status FROM attempts WHERE id=?",(key,)).fetchone()[0])
        row=db.execute("SELECT status,observation FROM attempts WHERE id=?",(a.id,)).fetchone()
        if row is None or (row[0]!="reserved" and row!=(a.status,a.observation)):
            raise ValueError("Unknown reservation or conflicting terminal observation")
        db.execute("UPDATE attempts SET status=?,observation=? WHERE id=? AND status='reserved'",(a.status,a.observation,a.id))
        return dict(id=a.id,status=a.status)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,required=True)
    sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("lookup"); q.add_argument("query"); q.add_argument("--cards",type=Path)
    r=sub.add_parser("reserve")
    for field in ("case","build","revision","action","symptom"): r.add_argument("--"+field,required=True)
    r.add_argument("--evidence",default="")
    f=sub.add_parser("finish"); f.add_argument("id"); f.add_argument("status",choices=["failed","observed","inconclusive"]); f.add_argument("observation")
    print(json.dumps(run(p.parse_args()),ensure_ascii=False))
