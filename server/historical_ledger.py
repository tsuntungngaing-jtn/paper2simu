"""Append-only, opt-in evidence sidecar for one existing coordination database."""
import argparse
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import time

from .coordination import CoordinationError, Coordinator


_SCHEMA = {
    "domain": "CREATE TABLE domain (binding TEXT PRIMARY KEY)",
    "receipts": """CREATE TABLE receipts (
        manifest TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE,
        digest TEXT NOT NULL, packet TEXT NOT NULL, recorded_ns INTEGER NOT NULL)""",
}
for _table in ("domain", "receipts"):
    for _action in ("update", "delete"):
        _name = f"{_table}_no_{_action}"
        _SCHEMA[_name] = (f"CREATE TRIGGER {_name} BEFORE {_action} ON {_table} "
                          "BEGIN SELECT RAISE(ABORT, 'append-only'); END")


def sidecar(c):
    return c.path.with_name(c.path.name + ".historical.sqlite3")


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _trust(path):
    if not path or not Path(path).is_absolute():
        raise CoordinationError("absolute deployment reconciliation trust path required")
    path = Path(path)
    if path.resolve(strict=True) != path or not path.is_file():
        raise CoordinationError("invalid deployment reconciliation trust path")
    return os.path.normcase(str(path))


def _binding(c, trust, roots):
    protected = [Path(_trust(trust)), c.path, sidecar(c)]
    for root in roots:
        canonical = root.resolve(strict=True)
        if canonical != root or any(path.is_relative_to(canonical) for path in protected):
            raise CoordinationError("protected reconciliation files must be outside every output root")
    for path in protected:
        if path.exists() and path.stat().st_nlink != 1:
            raise CoordinationError("protected reconciliation file has an unverified filesystem alias")
    st = c.path.stat()
    if not st.st_ino:
        raise CoordinationError("coordination database file identity unavailable")
    return _canonical([os.path.normcase(str(c.path)), str(st.st_dev), str(st.st_ino),
                       socket.gethostname().casefold(), c.resource_id, str(protected[0])])


def initialize(c, trust_path):
    """Explicit additive migration. Refuse to replace any existing sidecar."""
    with c.history_snapshot() as (roots, _jobs):
        path = sidecar(c)
        binding = _binding(c, trust_path, roots)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            for sql in _SCHEMA.values():
                db.execute(sql)
            db.execute("INSERT INTO domain VALUES (?)", (binding,))
            db.execute("PRAGMA user_version = 1")


@contextmanager
def _open(c, trust, roots, writable=False):
    try:
        path = sidecar(c)
        if path.resolve(strict=True) != path:
            raise CoordinationError("unexpected reconciliation sidecar path")
        mode = "rw" if writable else "ro"
        with closing(sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True)) as db, db:
            db.execute("BEGIN IMMEDIATE" if writable else "BEGIN")
            if (dict(db.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")) != _SCHEMA
                    or db.execute("PRAGMA user_version").fetchone() != (1,)
                    or db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]
                    or db.execute("SELECT binding FROM domain").fetchall() != [(_binding(c, trust, roots),)]):
                raise CoordinationError("invalid historical reconciliation ledger")
            yield db
    except (OSError, sqlite3.Error) as exc:
        raise CoordinationError("historical reconciliation ledger unavailable") from exc


def _verify(c, path, trust, packet):
    from scripts.verification_gate import verify_historical_release
    if not trust or not Path(trust).is_absolute():
        raise CoordinationError("absolute deployment reconciliation trust path required")
    return verify_historical_release(packet, path, c.resource_id, trust)


def _manifest(path, roots):
    path = Path(path)
    if (not path.is_absolute() or path.resolve(strict=True) != path
            or path.suffix != ".json" or path.parent.name != "job-manifests"
            or path.parent.parent not in roots):
        raise CoordinationError("receipt is outside the enrolled historical manifests")
    return path


def append(c, manifest_path, packet, trust_path):
    """Admin-only local entry. Signed independent decisions are required on every call."""
    with c.history_snapshot() as (roots, jobs):
        path = _manifest(manifest_path, roots)
        with _open(c, trust_path, roots, writable=True) as db:
            statement = _verify(c, path, trust_path, packet)
            original = json.loads(path.read_bytes())
            if (original.get("coordination_job_id") or original["status"] in ("completed", "cancelled")
                    or any(j["request"].get("native_job_id") == statement["job_id"] for j in jobs)):
                raise CoordinationError("receipt applies only to unresolved uncoordinated history")
            encoded = _canonical(packet)
            digest = hashlib.sha256(encoded.encode()).hexdigest()
            key = os.path.normcase(str(path))
            row = db.execute("SELECT digest, packet FROM receipts WHERE manifest=?", (key,)).fetchone()
            if row and row != (digest, encoded):
                raise CoordinationError("conflicting historical reconciliation receipt")
            if not row:
                db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?)",
                           (key, statement["job_id"], digest, encoded, time.time_ns()))
            return {"job_id": statement["job_id"], "receipt_sha256": digest, "existing": bool(row)}


def verified_history(c, roots, trust_path):
    """Called under the coordination transaction. Verify even missing or renamed originals."""
    result = {}
    with _open(c, trust_path, roots) as db:
        for key, job_id, digest, encoded in db.execute("SELECT manifest, job_id, digest, packet FROM receipts"):
            if hashlib.sha256(encoded.encode()).hexdigest() != digest:
                raise CoordinationError("historical receipt digest mismatch")
            packet = json.loads(encoded)
            path = _manifest(Path(key), roots)
            statement = _verify(c, path, trust_path, packet)
            if job_id != statement["job_id"] or key != os.path.normcase(statement["manifest_path"]):
                raise CoordinationError("historical receipt identity mismatch")
            result[path] = statement
    return result


def lookup(coordinator, manifest_path, trust_path):
    with coordinator.history_snapshot() as (roots, _jobs):
        return verified_history(coordinator, roots, trust_path).get(Path(manifest_path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    add = sub.add_parser("append")
    add.add_argument("manifest", type=Path)
    add.add_argument("packet", type=Path)
    args = parser.parse_args(argv)
    try:
        db = Path(os.environ["PAPER2SIMU_COORDINATION_DB"])
        if not db.is_absolute() or os.environ.get("COMSOL_TOOL_ROLE", "operator") != "operator":
            raise CoordinationError("local operator and absolute coordination path required")
        c = Coordinator(db, os.environ["PAPER2SIMU_RESOURCE_ID"])
        if args.action == "init":
            initialize(c, os.environ["PAPER2SIMU_RECONCILIATION_TRUST"])
            result = {"initialized": str(sidecar(c))}
        else:
            result = append(c, args.manifest, json.loads(args.packet.read_bytes()),
                            os.environ["PAPER2SIMU_RECONCILIATION_TRUST"])
        print(json.dumps(result))
    except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
        parser.exit(1, f"Historical reconciliation blocked: {exc}\n")


if __name__ == "__main__":
    main()
