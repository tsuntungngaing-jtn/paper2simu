import multiprocessing
import sqlite3

import pytest

from server import coordination
from server.coordination import CoordinationError, Coordinator, initialize


@pytest.fixture
def ledger(tmp_path):
    path = tmp_path / "shared # resource.sqlite"
    initialize(path, "solver")
    return Coordinator(path, "solver")


def test_exclusive_across_clients_with_distinct_output_roots(ledger):
    other = Coordinator(ledger.path, "solver")
    first = ledger.reserve("one", {"output_root": "run-a"}, "A", "isolated")
    assert first["state"] == "reserved"
    assert first["request"] == {"output_root": "run-a"}
    with pytest.raises(CoordinationError):
        other.reserve("two", {"output_root": "run-b"}, "B", "shared")
    assert len(other.inspect()) == 1
    ledger.release(first["job_id"], "A", {"never_started": True})
    assert other.reserve("two", {"output_root": "run-b"}, "B", "shared")


def test_duplicate_uses_immutable_request_and_preserves_original_owner(ledger):
    request = {"x": [1], "other": "value"}
    first = ledger.reserve("same", request, "A", "isolated")
    request["x"].append(2)
    duplicate = ledger.reserve("same", {"other": "value", "x": [1]}, "B", "isolated")
    assert duplicate["existing"]
    assert duplicate["job_id"] == first["job_id"]
    assert duplicate["owner"] == "A"
    assert not first["existing"]
    with pytest.raises(CoordinationError):
        ledger.reserve("same", request, "A", "isolated")
    with pytest.raises(CoordinationError):
        ledger.reserve("same", first["request"], "B", "shared")


def test_missing_receipt_retains_claim_after_reopen(ledger):
    job = ledger.reserve("op", {}, "A", "isolated")["job_id"]
    ledger.transition(job, "A", "launching")
    reopened = Coordinator(ledger.path, "solver")
    for state in ("reserved", "launching", "stopping", "released"):
        with pytest.raises(CoordinationError):
            reopened.transition(job, "A", state)
    for proof in ({"never_started": True}, {"native_stopped": True, "evidence": "stop"}):
        with pytest.raises(CoordinationError):
            reopened.release(job, "A", proof)
    with pytest.raises(CoordinationError):
        reopened.reserve("other", {}, "B", "shared")
    assert reopened.get(operation_id="op")["state"] == "launching"


def test_owner_receipt_and_proof_gate_release(ledger):
    job = ledger.reserve("op", {}, "A", "isolated")["job_id"]
    with pytest.raises(CoordinationError):
        ledger.release(job, "B", {"never_started": True})
    with pytest.raises(CoordinationError):
        ledger.transition(job, "B", "launching")
    ledger.transition(job, "A", "launching")
    ledger.transition(job, "A", "running", {"pid": 123})
    ledger.transition(job, "A", "stopping")
    for proof in ({"native_stopped": True}, {"native_stopped": 1, "evidence": "stop"}, {}):
        with pytest.raises(CoordinationError):
            ledger.release(job, "A", proof)
    stopped = ledger.release(job, "A", {"native_stopped": True, "evidence": {"exit": 0}})
    assert stopped["released"]
    assert ledger.get(job_id=job) == stopped
    with sqlite3.connect(ledger.path) as db:
        assert [row[0] for row in db.execute("SELECT event FROM events ORDER BY id")] == [
            "reserved", "launching", "running", "stopping", "released"
        ]


@pytest.mark.parametrize("fault", ["missing", "corrupt", "incomplete", "wrong_domain", "directory"])
def test_bad_database_fails_closed(tmp_path, fault):
    path = tmp_path / "coordination.sqlite"
    if fault == "corrupt":
        path.write_bytes(b"not sqlite")
    if fault == "incomplete":
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE metadata (value TEXT)")
    if fault == "wrong_domain":
        initialize(path, "another-domain")
    if fault == "directory":
        path.mkdir()
    with pytest.raises(CoordinationError):
        Coordinator(path, "solver").reserve("op", {}, "owner", "isolated")
    if fault == "missing":
        assert not path.exists()


def test_reinitialization_cannot_replace_history(ledger):
    job = ledger.reserve("op", {}, "A", "isolated")
    with pytest.raises(CoordinationError):
        initialize(ledger.path, "solver")
    assert ledger.get(operation_id="op")["job_id"] == job["job_id"]


def test_history_loss_fails_closed(ledger):
    ledger.reserve("op", {}, "A", "isolated")
    with sqlite3.connect(ledger.path) as db:
        db.execute("DELETE FROM jobs")
    with pytest.raises(CoordinationError):
        ledger.reserve("another", {}, "B", "isolated")


def test_clock_reversal_blocks_new_work_but_allows_owned_stop(ledger, monkeypatch):
    baseline = coordination.time.time_ns()
    monkeypatch.setattr(coordination.time, "time_ns", lambda: baseline + 100)
    job = ledger.reserve("op", {}, "A", "isolated")["job_id"]
    ledger.transition(job, "A", "launching")
    ledger.transition(job, "A", "running")
    monkeypatch.setattr(coordination.time, "time_ns", lambda: baseline)
    ledger.release(job, "A", {"native_stopped": True, "evidence": "confirmed"})
    with pytest.raises(CoordinationError, match="clock"):
        ledger.reserve("next", {}, "B", "isolated")
    monkeypatch.setattr(coordination.time, "time_ns", lambda: baseline + 101)
    assert ledger.reserve("next", {}, "B", "isolated")


def _reserve_in_process(path, start, results, operation):
    start.wait(timeout=15)
    try:
        Coordinator(path, "solver").reserve(operation, {}, operation, "isolated")
    except CoordinationError as exc:
        results.put(str(exc))
    else:
        results.put("reserved")


def test_process_race_gets_exactly_one_claim(ledger):
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    processes = [
        context.Process(target=_reserve_in_process, args=(ledger.path, start, results, op))
        for op in ("a", "b")
    ]
    try:
        for process in processes:
            process.start()
        start.set()
        outcomes = [results.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=15)
            assert process.exitcode == 0
        assert outcomes.count("reserved") == 1
        assert "resource is already claimed" in outcomes
        assert len(ledger.inspect()) == 1
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()


def test_registered_roots_and_history_guard_share_admission_transaction(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    path = tmp_path / "ledger"
    initialize(path, "solver", roots=[first_root])
    other = Coordinator(path, "solver")
    other.register_root(second_root)
    other.register_root(second_root)
    assert set(other.roots()) == {first_root, second_root}

    def block(roots, jobs):
        assert set(roots) == {first_root, second_root}
        assert jobs == []
        raise CoordinationError("unresolved external history")

    with pytest.raises(CoordinationError, match="unresolved external history"):
        other.reserve("op", {}, "owner", "isolated", check_history=block)
    assert other.inspect() == []


def test_lost_jobs_and_events_fail_closed(ledger):
    ledger.reserve("op", {}, "A", "isolated")
    with sqlite3.connect(ledger.path) as db:
        db.execute("DELETE FROM events")
        db.execute("DELETE FROM jobs")
    with pytest.raises(CoordinationError):
        ledger.reserve("next", {}, "B", "isolated")


def test_release_rolls_back_when_audit_write_fails(ledger, monkeypatch):
    job = ledger.reserve("op", {}, "A", "isolated")["job_id"]

    def fail(*args):
        raise sqlite3.OperationalError("I/O fault after job update")

    with monkeypatch.context() as patch:
        patch.setattr(ledger, "_event", fail)
        with pytest.raises(CoordinationError):
            ledger.release(job, "A", {"never_started": True})
    reopened = Coordinator(ledger.path, "solver")
    assert not reopened.get(job_id=job)["released"]
    with pytest.raises(CoordinationError, match="already claimed"):
        reopened.reserve("next", {}, "B", "isolated")


def test_case_budget_cannot_be_reset_from_another_output_root(ledger, tmp_path):
    first_path = tmp_path / "first" / "case-clock.json"
    second_path = tmp_path / "second" / "case-clock.json"
    clock = {
        "started_at_unix": 100.5,
        "deadline_at_unix": 1000.5,
        "new_work_cutoff_unix": 900.5,
        "solve_limit_seconds": 600,
        "stall_seconds": 50,
        "active": True,
    }
    first = ledger.bind_case("case-a", first_path, clock)
    other = Coordinator(ledger.path, "solver")
    assert other.case("case-b") is None
    assert other.bind_case("case-a", first_path, {**clock, "active": False}) == first
    with pytest.raises(CoordinationError):
        other.bind_case("case-a", second_path, clock)
    with pytest.raises(CoordinationError):
        other.bind_case("case-a", first_path, {**clock, "deadline_at_unix": 1100.5})
    assert other.case("case-a") == first
    assert first["deadline_at_unix"] == 1000.5
    assert first["started_at_unix"] == 100.5


def test_case_binding_history_loss_blocks_admission(ledger, tmp_path):
    clock = {
        "started_at_unix": 100,
        "deadline_at_unix": 1000,
        "new_work_cutoff_unix": 900,
        "solve_limit_seconds": 600,
        "stall_seconds": 50,
    }
    ledger.bind_case("case-a", tmp_path / "clock", clock)
    with sqlite3.connect(ledger.path) as db:
        db.execute("DELETE FROM cases")
    with pytest.raises(CoordinationError):
        ledger.reserve("op", {}, "owner", "shared")
