from pathlib import Path
import pytest
from server.connection_supervisor import FLAGS, step, RELOAD_METHOD


def snapshot(**changes):
    s = dict.fromkeys(FLAGS, True)
    s.update(policy_denied=False, host_id="host", provider_id="fluent_local",
             thread_id="scheduled", turn_id="turn1", incident_id="incident1",
             solver="Fluent", context="actual_scheduled", observed_at=1000)
    s.update(changes)
    return s


@pytest.mark.parametrize("solver,provider", [("COMSOL","comsol"), ("Fluent","fluent_local")])
def test_catalog_loss_reload_not_recovery(tmp_path, solver, provider):
    calls = []
    def rpc(method, params):
        calls.append((method, params))
        return {}
    s = snapshot(solver=solver, provider_id=provider, catalog_ok=False)
    db = tmp_path / "state.db"
    out = step(db, s, rpc, now=1000)
    assert calls == [(RELOAD_METHOD, {})]
    assert out["action"] == "REFRESH_ACK_WAIT_NEXT_TURN"
    assert not out["native_execution_authorized"]
    assert step(db, s, rpc, now=1000)["action"] == "WAIT_FRESH_TURN"
    assert len(calls) == 1
    assert step(db, snapshot(turn_id="turn2", observed_at=1001), rpc,
                now=1001)["status"] == "CONNECTION_VERIFIED"


@pytest.mark.parametrize("key,status", [
    ("transport_ok","TRANSPORT_BLOCKED"), ("executor_ok","EXECUTOR_BLOCKED"),
    ("runtime_ok","RUNTIME_BLOCKED"), ("native_ok","NATIVE_BLOCKED"),
    ("history_ok","HISTORY_BLOCKED"), ("registered","CONFIG_BLOCKED")])
def test_blockers_never_reload(tmp_path, key, status):
    def fail(*args):
        pytest.fail("unexpected reload")
    out = step(tmp_path/"state.db", snapshot(**{key:False}), fail, now=1000)
    assert out["status"] == status
    assert not out["native_execution_authorized"]


def test_missing_host_and_unknown_evidence(tmp_path):
    db = tmp_path/"state.db"
    assert step(db, snapshot(catalog_ok=False), now=1000)["action"] == "HOST_REFRESH_UNAVAILABLE"
    assert step(db, snapshot(catalog_ok=None), lambda *a: {}, now=1000)["action"] == "COLLECT_ACTUAL_FAILURE"
    assert step(db, snapshot(catalog_ok=False, refresh_safe=False), lambda *a: {}, now=1000)["action"] == "HOST_REFRESH_NOT_ADMITTED"


def test_budget_and_failed_ack_persist(tmp_path):
    db = tmp_path/"state.db"
    def fail(*a):
        raise TimeoutError()
    for i, t in enumerate((1000, 1301)):
        out = step(db, snapshot(catalog_ok=False, turn_id="turn"+str(i),
                                observed_at=t), fail, now=t)
        assert out["action"] == "REFRESH_OUTCOME_UNKNOWN"
    assert step(db, snapshot(catalog_ok=False, turn_id="turn3", observed_at=1602),
                fail, now=1602)["action"] == "ESCALATE_ATTEMPTS_EXHAUSTED"


def test_cross_provider_cooldown(tmp_path):
    db = tmp_path/"state.db"
    step(db, snapshot(catalog_ok=False), lambda *a: {}, now=1000)
    out = step(db, snapshot(provider_id="comsol", solver="COMSOL", catalog_ok=False,
                            incident_id="other", turn_id="turn2"), lambda *a: {}, now=1000)
    assert out["action"] == "WAIT_FRESH_TURN"


def test_stale_or_wrong_context(tmp_path):
    for s in (snapshot(context="manual"), snapshot(observed_at=900)):
        with pytest.raises(ValueError):
            step(tmp_path/"state.db", s, now=1000)
