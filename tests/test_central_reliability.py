import hashlib
import pytest
from server.trace_evidence import consumption_view
from server.deployment_identity import verify, REQUIRED


def trace(disposition="ADOPTED"):
    ctx = dict(task_id="t",case_id="c",plan_revision="r",task_kind="paper",paper_id="P1",
               artifact_sha256="a"*64,source_receipt_id="receipt",thread_id="thread")
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


def test_liveness_set_order_and_duplicates():
    o = dict(node_states={"x":"READY"},blockers=["a","b"],
             verified_milestones=["m1","m2"],eligible_ready=["x","y"])
    other = dict(o,blockers=["b","a","a"],verified_milestones=["m2","m1"],
                 eligible_ready=["y","x"])
    assert repeated_observations([o,other]) == "REPLAN_READY_WORK"


def test_legacy_migration_preserves_native_gates(tmp_path):
    from server.task_liveness import migration_preview, reviewed_completion
    old = dict(task_id="t",work_nodes=[{"id":"x","action":"read"}])
    assert migration_preview(old,{})["status"] == "MIGRATION_INCOMPLETE"
    metadata = dict(owner_role="A06",operation_scope="read_only",completion_evidence="receipt",
                    resource_domain="host",revision_binding="r",attempt_budget=1,failure_edges=[])
    new = migration_preview(old,{"x":metadata})["plan"]
    assert "work_schema" not in old and new["work_nodes"][0]["id"] == "x"
    with pytest.raises(ValueError):
        migration_preview(old,{"x":dict(metadata,requires_submission=False)})
    event = reviewed_completion(new,"x","r",["receipt"],"review")
    with pytest.raises(ValueError,match="review index required"):
        work_progress(new,[event],[],False)
    import json
    receipt = dict(receipt_id="review",task_id="t",node_id="x",revision_binding="r",
                   evidence_refs=["receipt"],decision="ACCEPT_COMPLETION",
                   producer_role="A06",reviewer_role="A05",
                   producer_worker="worker-1",reviewer_worker="worker-2")
    data=json.dumps(receipt).encode()
    (tmp_path/"review.json").write_bytes(data)
    index={"review":{"path":"review.json","sha256":hashlib.sha256(data).hexdigest()}}
    assert work_progress(new,[event],[],False,review_context=(tmp_path,index))[0] is None
    with pytest.raises(ValueError):
        work_progress(new,[dict(event,evidence_refs=["other"])],[],False,review_context=(tmp_path,index))
    with pytest.raises(ValueError):
        work_progress(new,[dict(event,revision_binding="old")],[],False)


def test_replay_receipt_binding(tmp_path):
    import json
    from server.trace_evidence import replay_consumption
    from server.stdio_diagnostics import classify_receipts
    a,b = trace()
    a["source_receipt_id"]="ra"
    b["source_receipt_id"]="rb"
    idx={}
    def put(ident,payload):
        data=json.dumps(dict(payload,receipt_id=ident)).encode()
        (tmp_path/ident).write_bytes(data)
        idx[ident]={"path":ident,"sha256":hashlib.sha256(data).hexdigest()}
    put("ra",{"event_projection":a})
    put("rb",{"event_projection":b})
    result=replay_consumption([a,b],tmp_path,idx)
    assert result["receipt_bytes_verified"] and not result["authenticity_verified"]
    with pytest.raises(ValueError):
        replay_consumption([a,dict(b,disposition="HOLD")],tmp_path,idx)
    ctx=dict(host_id="h",turn_id="t",provider_id="p")
    put("s",dict(ctx,stage="configured",observed=True))
    assert classify_receipts(tmp_path,idx,["s"],ctx)["next_evidence"]=="environment_ok"
    with pytest.raises(ValueError):
        classify_receipts(tmp_path,idx,["s"],dict(ctx,turn_id="old"))
    (tmp_path/"ra").write_bytes(b"changed")
    with pytest.raises(ValueError):
        replay_consumption([a,b],tmp_path,idx)


def test_round2_empty_and_cross_thread(tmp_path):
    from server.trace_evidence import replay_consumption
    from server.stdio_diagnostics import classify_receipts
    empty = replay_consumption([{"event_id":"legacy","event":"legacy"}],tmp_path,{})
    assert not empty["receipt_bytes_verified"] and empty["unmapped_event_count"] == 1
    assert empty["coverage_status"] == "NO_MAPPED_EVENTS"
    ctx=dict(host_id="h",turn_id="t",provider_id="p")
    assert not classify_receipts(tmp_path,{},[],ctx)["receipt_bytes_verified"]
    a,b=trace()
    with pytest.raises(ValueError):
        consumption_view([a,dict(b,thread_id="other")])


def test_round2_known_stdio_failure_with_prior_gap(tmp_path):
    import json
    from server.stdio_diagnostics import classify_receipts
    ctx=dict(host_id="h",turn_id="t",provider_id="p")
    data=json.dumps(dict(ctx,receipt_id="r",stage="initialize_response",observed=False)).encode()
    (tmp_path/"r").write_bytes(data)
    result=classify_receipts(tmp_path,{"r":{"path":"r","sha256":hashlib.sha256(data).hexdigest()}},["r"],ctx)
    assert result["next_evidence"]=="configured"
    assert result["known_failed_stages"]==["initialize_response"]


def test_round2_distinct_turns_and_prose():
    from server.task_liveness import observation_replay
    row=dict(source_turn_id="t1",node_states={"x":"BLOCKED"},eligible_ready=[],
             verified_milestones=[],blockers=[dict(incident_id="i",resource_domain="h",
             node_id="x",code="transport_error",description="old")])
    assert observation_replay([row,row])["status"]=="INSUFFICIENT_OBSERVATIONS"
    other=dict(row,source_turn_id="t2",blockers=[dict(row["blockers"][0],description="new words")])
    assert observation_replay([row,other])["status"]=="WAIT_OR_ESCALATE_MINIMAL_BLOCKER"


def test_round2_incident_reclassification():
    p=dict(task_id="t",work_nodes=[node("x")])
    e=dict(incident_id="i",blocker_type="transport_error",next_action="inspect",resume_when="receipt")
    assert recovery_candidates(p,{"x":e})[0]["id"] == recovery_candidates(
        p,{"x":dict(e,blocker_type="capability_missing")})[0]["id"]


def test_round2_legacy_preview(tmp_path):
    from scripts.research_resume import legacy_journal_preview
    raw=b'{"status":"hold"}\n{"event":"work_blocked","node_id":"other"}\n{"event":"submitted","trial_id":"x"}\n'
    path=tmp_path/"old.jsonl"
    path.write_bytes(raw)
    out=legacy_journal_preview(dict(work_nodes=[node("x")]),path)
    assert [r["status"] for r in out["rows"]]==[
        "MISSING_EVENT_TYPE","UNKNOWN_NODE","RECONCILE_NATIVE_EVENT"]
    assert path.read_bytes()==raw
