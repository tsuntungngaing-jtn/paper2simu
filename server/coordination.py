"""Durable admission ledger for cooperating clients of one native resource."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterable
from contextlib import closing, contextmanager
from pathlib import Path


class CoordinationError(ValueError):
    """The operation was denied or the coordination ledger is unavailable."""


_SCHEMA = {
    "metadata": """CREATE TABLE metadata (
        slot INTEGER PRIMARY KEY CHECK (slot = 1),
        resource_id TEXT NOT NULL,
        clock_high_water INTEGER NOT NULL CHECK (clock_high_water >= 0),
        event_count INTEGER NOT NULL CHECK (event_count >= 0),
        root_count INTEGER NOT NULL CHECK (root_count >= 0),
        case_count INTEGER NOT NULL CHECK (case_count >= 0)
    )""",
    "roots": "CREATE TABLE roots (path TEXT PRIMARY KEY NOT NULL)",
    "cases": """CREATE TABLE cases (
        case_id TEXT PRIMARY KEY NOT NULL,
        clock_path TEXT NOT NULL,
        started_at_unix REAL NOT NULL CHECK (started_at_unix >= 0),
        deadline_at_unix REAL NOT NULL,
        new_work_cutoff_unix REAL NOT NULL,
        solve_limit_seconds REAL NOT NULL CHECK (solve_limit_seconds > 0),
        stall_seconds REAL NOT NULL CHECK (stall_seconds > 0),
        CHECK (started_at_unix < new_work_cutoff_unix AND new_work_cutoff_unix < deadline_at_unix)
    )""",
    "jobs": """CREATE TABLE jobs (
        job_id TEXT PRIMARY KEY NOT NULL,
        operation_id TEXT UNIQUE NOT NULL,
        owner TEXT NOT NULL CHECK (length(trim(owner)) > 0),
        kind TEXT NOT NULL,
        request TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        state TEXT NOT NULL CHECK (state IN ('reserved', 'launching', 'running', 'stopping')),
        released INTEGER NOT NULL DEFAULT 0 CHECK (released IN (0, 1)),
        details TEXT,
        proof TEXT,
        created_ns INTEGER NOT NULL,
        updated_ns INTEGER NOT NULL CHECK (updated_ns >= created_ns),
        CHECK ((released = 1) = (proof IS NOT NULL))
    )""",
    "single_claim": "CREATE UNIQUE INDEX single_claim ON jobs (released) WHERE released = 0",
    "events": """CREATE TABLE events (
        id INTEGER PRIMARY KEY,
        job_id TEXT NOT NULL REFERENCES jobs(job_id),
        event TEXT NOT NULL CHECK (event IN ('reserved', 'launching', 'running', 'stopping', 'released')),
        recorded_ns INTEGER NOT NULL,
        data TEXT,
        UNIQUE (job_id, event)
    )""",
}
_VERSION = 1
_TRANSITIONS = {"reserved": "launching", "launching": "running", "running": "stopping"}
_PHASES = (*_TRANSITIONS, "stopping")
_BUDGET_FIELDS = (
    "started_at_unix", "deadline_at_unix", "new_work_cutoff_unix", "solve_limit_seconds", "stall_seconds",
)


def _nonempty(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CoordinationError(f"{label} must be a nonempty string")


def _encode(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise CoordinationError("ledger payload must be a dictionary")
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CoordinationError("ledger payload must be JSON serializable") from exc
    return encoded


def _digest(encoded: str) -> str:
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _open(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def _register_root(db: sqlite3.Connection, path: str | Path) -> None:
    canonical = os.path.normcase(Path(path).resolve())
    inserted = db.execute("INSERT OR IGNORE INTO roots VALUES (?)", (canonical,))
    if inserted.rowcount:
        db.execute("UPDATE metadata SET root_count = root_count + 1 WHERE slot = 1")


def initialize(path: str | Path, resource_id: str, roots: Iterable[str | Path] = ()) -> None:
    """Provision a new ledger at an explicit path. An existing path is retained."""
    _nonempty(resource_id, "resource ID")
    path = Path(path).resolve()
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(_open(path)) as db:
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            for statement in _SCHEMA.values():
                db.execute(statement)
            db.execute(f"PRAGMA user_version = {_VERSION}")
            db.execute("INSERT INTO metadata VALUES (1, ?, ?, 0, 0, 0)", (resource_id, time.time_ns()))
            for root in roots:
                _register_root(db, root)
            db.commit()
    except (OSError, sqlite3.Error) as exc:
        # A partial initialization remains visible and fails validation on use.
        raise CoordinationError("cannot initialize coordination ledger") from exc


def _job(row: sqlite3.Row) -> dict:
    result = dict(row)
    result.pop("request_hash")
    for key in ("request", "details", "proof"):
        if result[key] is not None:
            result[key] = json.loads(result[key])
    result["released"] = bool(result["released"])
    return result


class Coordinator:
    def __init__(self, path: str | Path, resource_id: str):
        _nonempty(resource_id, "resource ID")
        self.path = Path(path).resolve()
        self.resource_id = resource_id

    @contextmanager
    def _transaction(self):
        try:
            with closing(_open(self.path)) as db:
                db.execute("PRAGMA synchronous = FULL")
                db.execute("PRAGMA foreign_keys = ON")
                db.execute("BEGIN IMMEDIATE")
                clock = self._validate(db)
                yield db, clock
                db.commit()
        except (OSError, sqlite3.Error, UnicodeError, json.JSONDecodeError) as exc:
            raise CoordinationError("coordination ledger is unavailable or invalid") from exc

    def _validate(self, db: sqlite3.Connection) -> int:
        if db.execute("PRAGMA user_version").fetchone()[0] != _VERSION:
            raise CoordinationError("unsupported coordination ledger schema")
        actual_schema = dict(db.execute(
            "SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall())
        if actual_schema != _SCHEMA:
            raise CoordinationError("incomplete or incompatible coordination ledger schema")
        rows = db.execute("SELECT * FROM metadata").fetchall()
        if len(rows) != 1 or rows[0]["slot"] != 1 or rows[0]["resource_id"] != self.resource_id:
            raise CoordinationError("coordination ledger resource domain mismatch")
        clock = rows[0]["clock_high_water"]
        if not isinstance(clock, int) or clock < 0:
            raise CoordinationError("coordination ledger clock is invalid")
        if [row[0] for row in db.execute("PRAGMA integrity_check")] != ["ok"]:
            raise CoordinationError("coordination ledger integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise CoordinationError("coordination ledger contains unknown job history")
        if (
            db.execute("SELECT count(*) FROM events").fetchone()[0] != rows[0]["event_count"]
            or db.execute("SELECT count(*) FROM roots").fetchone()[0] != rows[0]["root_count"]
            or db.execute("SELECT count(*) FROM cases").fetchone()[0] != rows[0]["case_count"]
        ):
            raise CoordinationError("coordination ledger history is incomplete")
        for row in db.execute(
            """SELECT jobs.*, group_concat(events.event) AS recorded_events
               FROM jobs LEFT JOIN events USING (job_id) GROUP BY jobs.job_id"""
        ):
            expected_events = set(_PHASES[:_PHASES.index(row["state"]) + 1])
            if row["released"]:
                expected_events.add("released")
            if (
                set((row["recorded_events"] or "").split(",")) != expected_events
                or _digest(row["request"]) != row["request_hash"]
                or row["updated_ns"] > clock
            ):
                raise CoordinationError("coordination ledger job history is incomplete")
        return clock

    @staticmethod
    def _event(db: sqlite3.Connection, job_id: str, event: str, now: int, data: str | None):
        db.execute(
            "INSERT INTO events (job_id, event, recorded_ns, data) VALUES (?, ?, ?, ?)",
            (job_id, event, now, data),
        )
        db.execute(
            "UPDATE metadata SET clock_high_water = ?, event_count = event_count + 1 WHERE slot = 1",
            (now,),
        )

    def reserve(
        self,
        operation_id: str,
        request: dict,
        owner: str,
        kind: str,
        *,
        check_history: Callable[[list[Path], list[dict]], None] | None = None,
    ) -> dict:
        _nonempty(operation_id, "operation ID")
        _nonempty(owner, "owner")
        _nonempty(kind, "execution kind")
        encoded = _encode(request)
        request_hash = _digest(encoded)
        with self._transaction() as (db, clock):
            previous = db.execute("SELECT * FROM jobs WHERE operation_id = ?", (operation_id,)).fetchone()
            if previous is not None:
                if previous["request"] != encoded or previous["kind"] != kind:
                    raise CoordinationError("operation ID already binds a different request")
                return {**_job(previous), "existing": True}
            now = time.time_ns()
            if now < clock:
                raise CoordinationError("coordination ledger clock moved backwards")
            if db.execute("SELECT 1 FROM jobs WHERE released = 0").fetchone():
                raise CoordinationError("resource is already claimed")
            if check_history is not None:
                check_history(self._roots(db), self._jobs(db))
            job_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO jobs (
                       job_id, operation_id, owner, kind, request, request_hash, state, created_ns, updated_ns
                   ) VALUES (?, ?, ?, ?, ?, ?, 'reserved', ?, ?)""",
                (job_id, operation_id, owner, kind, encoded, request_hash, now, now),
            )
            self._event(db, job_id, "reserved", now, request_hash)
            row = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return {**_job(row), "existing": False}

    def get(self, job_id: str | None = None, operation_id: str | None = None) -> dict | None:
        if (job_id is None) == (operation_id is None):
            raise CoordinationError("specify one job ID or operation ID")
        with self._transaction() as (db, _):
            if job_id is not None:
                row = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            else:
                row = db.execute("SELECT * FROM jobs WHERE operation_id = ?", (operation_id,)).fetchone()
            return _job(row) if row is not None else None

    @staticmethod
    def _jobs(db: sqlite3.Connection) -> list[dict]:
        return [_job(row) for row in db.execute("SELECT * FROM jobs ORDER BY rowid")]

    def inspect(self) -> list[dict]:
        with self._transaction() as (db, _):
            return self._jobs(db)

    @staticmethod
    def _roots(db: sqlite3.Connection) -> list[Path]:
        return [Path(row[0]) for row in db.execute("SELECT path FROM roots ORDER BY path")]

    @contextmanager
    def history_snapshot(self):
        # Serialize receipt inspection and local administration with native reservations.
        with self._transaction() as (db, _clock):
            yield self._roots(db), self._jobs(db)

    def roots(self) -> list[Path]:
        with self._transaction() as (db, _):
            return self._roots(db)

    def register_root(self, path: str | Path) -> None:
        with self._transaction() as (db, _):
            _register_root(db, path)

    def bind_case(self, case_id: str, clock_path: str | Path, clock_dict: dict) -> dict:
        """Bind a case to one clock source and its original budget for this resource."""
        _nonempty(case_id, "case ID")
        if not isinstance(clock_dict, dict) or clock_dict.get("case_id", case_id) != case_id:
            raise CoordinationError("case clock identity mismatch")
        values = [clock_dict.get(field) for field in _BUDGET_FIELDS]
        if not all(type(value) in (int, float) and math.isfinite(value) for value in values):
            raise CoordinationError("invalid immutable case budget")
        started, deadline, cutoff, solve, stall = values
        if not (0 <= started < cutoff < deadline and solve > 0 and stall > 0):
            raise CoordinationError("invalid immutable case budget")
        canonical = os.path.normcase(Path(clock_path).resolve())
        requested = {"case_id": case_id, "clock_path": canonical, **dict(zip(_BUDGET_FIELDS, values))}
        with self._transaction() as (db, _):
            previous = db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            if previous is not None:
                if dict(previous) != requested:
                    raise CoordinationError("case clock path and budget are already bound")
                return dict(previous)
            db.execute("INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(requested.values()))
            db.execute("UPDATE metadata SET case_count = case_count + 1 WHERE slot = 1")
            return dict(db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone())

    def case(self, case_id: str) -> dict | None:
        _nonempty(case_id, "case ID")
        with self._transaction() as (db, _):
            row = db.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            return dict(row) if row is not None else None

    @staticmethod
    def _owned(db: sqlite3.Connection, job_id: str, owner: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None or row["owner"] != owner or row["released"]:
            raise CoordinationError("active claim ownership was not established")
        return row

    def transition(self, job_id: str, owner: str, state: str, details: dict | None = None) -> dict:
        encoded = None if details is None else _encode(details)
        with self._transaction() as (db, clock):
            row = self._owned(db, job_id, owner)
            if state is None or _TRANSITIONS.get(row["state"]) != state:
                raise CoordinationError(f"invalid claim phase transition from {row['state']} to {state}")
            now = max(clock, time.time_ns())
            db.execute(
                "UPDATE jobs SET state = ?, details = ?, updated_ns = ? WHERE job_id = ?",
                (state, encoded, now, job_id),
            )
            self._event(db, job_id, state, now, encoded)
            return _job(db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone())

    def release(self, job_id: str, owner: str, proof: dict) -> dict:
        encoded = _encode(proof)
        with self._transaction() as (db, clock):
            row = self._owned(db, job_id, owner)
            never_started = proof.get("never_started") is True and "native_stopped" not in proof
            evidence = proof.get("evidence")
            has_evidence = (isinstance(evidence, str) and bool(evidence.strip())) or (
                isinstance(evidence, dict) and bool(evidence)
            )
            native_stopped = proof.get("native_stopped") is True and "never_started" not in proof and has_evidence
            accepted = (row["state"] == "reserved" and never_started) or (
                row["state"] in ("running", "stopping") and native_stopped
            )
            if not accepted:
                raise CoordinationError("stop proof does not establish release for this claim phase")
            now = max(clock, time.time_ns())
            db.execute(
                "UPDATE jobs SET released = 1, proof = ?, updated_ns = ? WHERE job_id = ?",
                (encoded, now, job_id),
            )
            self._event(db, job_id, "released", now, encoded)
            return _job(db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["initialize"])
    parser.add_argument("path", type=Path)
    parser.add_argument("resource_id")
    parser.add_argument("--root", action="append", type=Path, default=[])
    args = parser.parse_args()
    try:
        initialize(args.path, args.resource_id, roots=args.root)
    except CoordinationError as exc:
        parser.exit(1, f"{exc}\n")
