"""Opt-in independent local SQLite checkpoint service.

Store belongs to a separate trusted administrator. It is NOT rollback-proof
if the database itself is restored or the caller controls its verifier.
A pending transaction blocks all later operations; no TTL or auto-clear.
"""
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from server.journal_anchor import JournalAnchor
from server.review_authority import require_verified


def _encode(anchor):
    if not isinstance(anchor,JournalAnchor):
        raise ValueError("checkpoint anchor required")
    return json.dumps(asdict(anchor),sort_keys=True,separators=(",",":"))


class CheckpointStore:
    def __init__(self,path):
        self.path=Path(path).resolve(strict=True)
        if not self.path.is_file():
            raise ValueError("independent checkpoint store missing")

    @classmethod
    def initialize(cls,path,anchor,authority):
        path=Path(path)
        require_verified(authority,"checkpoint_enrollment",asdict(anchor))
        if anchor.sequence!=0 or anchor.journal_sha256!="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
            raise ValueError("only empty genesis enrollment; historical migration requires review")
        with path.open("xb"):
            pass
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE checkpoint (slot INTEGER PRIMARY KEY CHECK(slot=1), anchor TEXT NOT NULL, pending TEXT)")
            db.execute("INSERT INTO checkpoint VALUES(1,?,NULL)",(_encode(anchor),))
        return cls(path)

    def _db(self):
        return sqlite3.connect(self.path.as_uri()+"?mode=rw",uri=True,timeout=10)

    def inspect(self):
        with closing(self._db()) as db:
            row=db.execute("SELECT anchor,pending FROM checkpoint WHERE slot=1").fetchone()
            if row is None:
                raise ValueError("checkpoint history missing")
            a=json.loads(row[0])
            a["file_identity"]=tuple(a["file_identity"])
            return JournalAnchor(**a),json.loads(row[1]) if row[1] else None

    def prepare(self,anchor,next_sha,event_sha):
        with closing(self._db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT anchor,pending FROM checkpoint WHERE slot=1").fetchone()
            if row is None or row[0]!=_encode(anchor) or row[1] is not None:
                raise ValueError("stale or pending independent checkpoint")
            db.execute("UPDATE checkpoint SET pending=? WHERE slot=1",
                       (json.dumps({"next_sha":next_sha,"event_sha":event_sha},sort_keys=True),))

    def finalize(self,anchor,next_sha,event_sha):
        from dataclasses import replace
        with closing(self._db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT anchor,pending FROM checkpoint WHERE slot=1").fetchone()
            expected={"next_sha":next_sha,"event_sha":event_sha}
            if row is None or row[0]!=_encode(anchor) or not row[1] or json.loads(row[1])!=expected:
                raise ValueError("checkpoint transaction mismatch")
            db.execute("UPDATE checkpoint SET anchor=?,pending=NULL WHERE slot=1",
                       (_encode(replace(anchor,journal_sha256=next_sha,sequence=anchor.sequence+1)),))

    def verify_checkpoint(self,payload):
        a,pending=self.inspect()
        return pending is None and payload==asdict(a)
