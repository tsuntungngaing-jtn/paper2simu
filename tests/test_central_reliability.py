import hashlib
import pytest
from server.trace_evidence import consumption_view
from server.deployment_identity import verify, REQUIRED


def trace(disposition="ADOPTED"):
    ctx = dict(task_id="t",case_id="c",plan_revision="r",task_kind="paper",paper_id="P1",
               artifact_sha256="a"*64,source_receipt_id="receipt")
    a = dict(ctx,event="artifact_observed",event_id="p",producer_step="s1")
    b = dict(ctx,event="consumer_disposition",event_id="d",producer_event_id="p",
             consumer_step="s2",consumer_input_sha256="a"*64,disposition=disposition)
    return a,b


@pytest.mark.parametrize("state,count",[("ADOPTED",1),("HOLD",0),("REJECTED",0),("UNKNOWN",0)])
def test_explicit_use(state,count):
    a,b = trace(state)
    assert len(consumption_view([a,b,b])["used"]) == count
    assert consumption_view([a])["used"] == []


@pytest.mark.parametrize("change",[{"paper_id":"P2"},{"artifact_sha256":"b"*64},
                                   {"consumer_input_sha256":"b"*64},{"consumer_step":"s1"}])
def test_bad_use(change):
    a,b = trace()
    with pytest.raises(ValueError):
        consumption_view([a,dict(b,**change)])


def test_fingerprint(tmp_path):
    (tmp_path/"source").write_bytes(b"approved")
    h = hashlib.sha256(b"approved").hexdigest()
    m = dict(display_version="0.6.3",commit="a"*40,groups={k:{"source":h} for k in REQUIRED})
    assert verify(m,tmp_path,"a"*40)["status"] == "DECLARED_FILES_MATCH"
    (tmp_path/"source").write_bytes(b"changed")
    assert verify(m,tmp_path,"a"*40)["status"] == "MISMATCH"
    assert verify(m,tmp_path,"b"*40)["status"] == "COMMIT_MISMATCH"

from server.task_liveness import validate_nodes, recovery_candidates, repeated_observations
from server.stdio_diagnostics import classify
from scripts.research_resume import work_progress


def node(ident,**kw):
    return dict(dict(id=ident,action="inspect",owner_role="A06",operation_scope="read_only",
                     completion_evidence="receipt",resource_domain="host",revision_binding="r",
                     attempt_budget=1,depends_on=[],failure_edges=[]),**kw)


def test_graph_recovery_and_independent_ready():
    plan = dict(task_id="task",work_schema="work-nodes/2",
                work_nodes=[node("read"),node("solve",owner_role="A04",operation_scope="native_submission",
                            requires_submission=True,depends_on=["read"])])
    assert validate_nodes(plan)
    b = dict(event="work_blocked",node_id="solve",incident_id="i",blocker_type="transport_error",
             next_action="inspect logs",resume_when="receipt",timestamp_utc="2026-11-27T00:00:00Z",
             last_attempt="status",actual_return="missing tools",evidence_refs=["log"])
    a = recovery_candidates(plan,{"solve":b})
    assert a == recovery_candidates(plan,{"solve":dict(b,timestamp="later")})
    assert not a[0]["native_execution_authorized"]
    action,waiting,lines = work_progress(plan,[b],["old"],False)
    assert action == "inspect" and waiting
    assert any(a[0]["id"] in line for line in lines)
    plan["work_nodes"][0]["failure_edges"]=["solve"]
    with pytest.raises(ValueError):
        validate_nodes(plan)


def test_read_only_not_solve_gate():
    p = dict(work_schema="work-nodes/2",work_nodes=[node("read",requires_submission=True)])
    with pytest.raises(ValueError):
        validate_nodes(p)


def test_heartbeat_not_progress():
    o = dict(node_states={"x":"READY"},blockers=[],verified_milestones=[],eligible_ready=["x"])
    assert repeated_observations([o,dict(o,trace_id="new")]) == "REPLAN_READY_WORK"
    assert repeated_observations([o,dict(o,verified_milestones=["observed"])]) == "STATE_CHANGED"


def test_stdio_unknown_not_inferred():
    assert classify({"configured":True})["next_evidence"] == "environment_ok"
    assert classify({"configured":True,"environment_ok":False})["status"] == "EXECUTABLE_ENV_INVALID"
    assert classify({})["status"] == "UNKNOWN"
