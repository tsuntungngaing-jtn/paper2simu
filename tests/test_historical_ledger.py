"""Historical clearance through the same guard used by shared and isolated work."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from server import historical_ledger as ledger, shared_guard
from server.coordination import Coordinator, CoordinationError, initialize
from server.runtime import Runtime
from test_historical_evidence import build_packet


@pytest.fixture
def domain(tmp_path, monkeypatch):
    output = tmp_path / "outputs"
    output.mkdir()
    packet, manifest, trust, _ = build_packet(output)
    trust = trust.rename(tmp_path / "authority.json")
    db = tmp_path / "coord.sqlite3"
    initialize(db, "lab", [output])
    c = Coordinator(db, "lab")
    monkeypatch.setenv("PAPER2SIMU_COORDINATION_DB", str(db))
    monkeypatch.setenv("PAPER2SIMU_RESOURCE_ID", "lab")
    monkeypatch.setenv("PAPER2SIMU_RECONCILIATION_TRUST", str(trust))
    return c, packet, manifest, trust


def test_additive_migration_and_rollback(domain, monkeypatch):
    c, packet, path, trust = domain
    manifest = path.read_bytes()
    clock = path.parent.parent / "clock.db"
    c.bind_case("case", clock, {"started_at_unix": 1, "deadline_at_unix": 101,
                                "new_work_cutoff_unix": 90, "solve_limit_seconds": 50, "stall_seconds": 10})
    budget = c.case("case")
    original = c.path.read_bytes()
    ledger.initialize(c, trust)
    with pytest.raises((ValueError, OSError)):
        ledger.initialize(c, trust)
    first = ledger.append(c, path, packet, trust)
    assert not first["existing"]
    assert ledger.append(c, path, packet, trust) == {**first, "existing": True}
    assert ledger.lookup(c, path, trust) == packet["statement"]
    assert c.path.read_bytes() == original and path.read_bytes() == manifest
    assert c.case("case") == budget
    with closing(sqlite3.connect(ledger.sidecar(c))) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM receipts")
    monkeypatch.delenv("PAPER2SIMU_RECONCILIATION_TRUST")
    rt = Runtime(output_root=path.parent.parent)
    with pytest.raises(CoordinationError, match="HISTORY_UNRESOLVED"):
        shared_guard.reserve(rt, "new", {}, "shared_call")
    assert path.read_bytes() == manifest


def test_old_operation_and_other_job_stay_blocked(domain):
    c, packet, path, trust = domain
    ledger.initialize(c, trust)
    ledger.append(c, path, packet, trust)
    rt = Runtime(output_root=path.parent.parent)
    with pytest.raises(CoordinationError, match="HISTORY_UNRESOLVED"):
        shared_guard.reserve(rt, packet["statement"]["operation_id"], {}, "shared_call")
    other = path.with_name("unrelated.json")
    other.write_text(json.dumps({"job_id": other.stem, "status": "running"}))
    with pytest.raises(CoordinationError, match="HISTORY_UNRESOLVED"):
        shared_guard.reserve(rt, "new", {}, "shared_call")
    other.unlink()
    row = shared_guard.reserve(rt, "new", {}, "shared_call")
    assert not row["released"]
    ledger.append(c, path, packet, trust)
    assert not c.get(job_id=row["job_id"])["released"]


@pytest.mark.parametrize("change", ["manifest", "missing_manifest", "key_policy", "removed_sidecar",
                                     "corrupt_sidecar", "wrong_trust", "missing_origin"])
def test_reverify_before_every_admission(domain, monkeypatch, change):
    c, packet, path, trust = domain
    ledger.initialize(c, trust)
    ledger.append(c, path, packet, trust)
    if change == "manifest":
        path.write_text(json.dumps({**json.loads(path.read_bytes()), "status": "completed"}))
    elif change == "missing_manifest":
        path.unlink()
    elif change == "key_policy":
        trust.write_text("{}")
    elif change == "removed_sidecar":
        ledger.sidecar(c).unlink()
    elif change == "corrupt_sidecar":
        ledger.sidecar(c).write_bytes(b"corrupt")
    elif change == "wrong_trust":
        alternative = trust.with_name("another-policy.json")
        alternative.write_bytes(trust.read_bytes())
        monkeypatch.setenv("PAPER2SIMU_RECONCILIATION_TRUST", str(alternative))
    elif change == "missing_origin":
        Path(packet["statement"]["evidence"]["origin"]["path"]).unlink()
    with pytest.raises((ValueError, OSError)):
        shared_guard.reserve(Runtime(output_root=path.parent.parent), "fresh", {}, "shared_call")
    assert c.inspect() == []


def test_prior_database_replacement_invalidates_sidecar(domain):
    c, packet, path, trust = domain
    ledger.initialize(c, trust)
    ledger.append(c, path, packet, trust)
    c.path.rename(c.path.with_name("preserved-v061.db"))
    initialize(c.path, c.resource_id, [path.parent.parent])
    with pytest.raises(CoordinationError):
        ledger.lookup(c, path, trust)


def test_shared_queue_accepts_only_the_attested_original(domain, monkeypatch):
    from concurrent.futures import Future
    c, packet, path, trust = domain
    ledger.initialize(c, trust)
    rt = Runtime(output_root=path.parent.parent)
    queued = []
    def capture(call):
        queued.append(call)
        return Future()
    monkeypatch.setattr(rt.executor, "submit", capture)
    assert rt.submit_study("std", "model", "fresh")["status"] == "BLOCKED"
    ledger.append(c, path, packet, trust)
    assert rt.submit_study("std", "model", "fresh")["status"] == "queued"
    assert len(queued) == 1
    assert rt.jobs[path.stem]["status"] == "recovery_pending"


@pytest.mark.parametrize("target", ["trust", "coordination"])
def test_refuse_authority_files_in_writable_output(domain, target):
    c, packet, path, trust = domain
    if target == "trust":
        trust = trust.rename(path.parent.parent / "policy.json")
    else:
        c = Coordinator(c.path.rename(path.parent.parent / "domain.db"), c.resource_id)
    with pytest.raises(CoordinationError, match="output root"):
        ledger.initialize(c, trust)
    assert not ledger.sidecar(c).exists()


def test_newly_enrolled_root_invalidates_protected_paths(domain):
    c, packet, path, trust = domain
    policy_dir = trust.parent / "admin"
    policy_dir.mkdir()
    trust = trust.rename(policy_dir / "policy.json")
    ledger.initialize(c, trust)
    ledger.append(c, path, packet, trust)
    c.register_root(policy_dir)
    with pytest.raises(CoordinationError, match="output root"):
        ledger.lookup(c, path, trust)
    with pytest.raises(CoordinationError, match="output root"):
        ledger.append(c, path, packet, trust)
    rt = Runtime(output_root=path.parent.parent)
    rt.reconciliation_trust = str(trust)
    with pytest.raises(CoordinationError, match="output root"):
        shared_guard.reserve(rt, "test", {}, "shared_call")
    assert c.inspect() == []

@pytest.mark.parametrize("use_home_root", [True, False])
def test_receipts_consume_domain_submission_budget_once(domain, monkeypatch, use_home_root):
    c, packet, path, trust = domain
    ledger.initialize(c, trust)
    ledger.append(c, path, packet, trust)
    monkeypatch.setenv("COMSOL_MAX_SUBMISSIONS", "1")
    home = path.parent.parent
    rt = Runtime(output_root=home if use_home_root else home.parent / "another-output")
    budget = rt.queue_status()["submission_budget"]
    assert budget["submissions"]["used"] == 1
    assert budget["active_jobs"]["used"] == 0
    assert budget["block_reasons"] == ["TOTAL_SUBMISSION_LIMIT_REACHED"]
    for kind in ("isolated", "shared_job"):
        with pytest.raises(CoordinationError, match="TOTAL_SUBMISSION_LIMIT_REACHED"):
            shared_guard.reserve(rt, "attempt", {}, kind)
    assert c.inspect() == []
