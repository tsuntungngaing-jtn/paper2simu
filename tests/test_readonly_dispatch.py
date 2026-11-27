import hashlib
import json
import multiprocessing
from pathlib import Path

import pytest
from server.readonly_dispatch import append_event, snapshot, project


def node(ident,role="A01",**kw):
    return dict(dict(id=ident,owner_role=role,action="read",operation_scope="read_only",
                     completion_evidence="artifact",resource_domain="local",
                     revision_binding="r",attempt_budget=1,depends_on=[],failure_edges=[],
                     required_artifacts=["artifact"]),**kw)


def plan():
    return dict(task_id="t",work_schema="work-nodes/2",work_nodes=[node("n")])


def event(kind="dispatch_intent",eid="e",**kw):
    return dict(dict(event=kind,event_id=eid,task_id="t",node_id="n",revision_binding="r",
                     resource_domain="local",role="A01",worker_id="w",thread_id="th",
                     dispatch_id="d",receipt_id=eid),**kw)


def store(root,index,ident,payload):
    data=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
    (root/ident).write_bytes(data)
    index[ident]={"path":ident,"sha256":hashlib.sha256(data).hexdigest()}


def receipt(root,index,e):
    store(root,index,e["receipt_id"],dict(receipt_id=e["receipt_id"],event_projection=e))


def append(root,index,e,sha,allow=True):
    return append_event(plan(),root/"journal",e,expected_sha256=sha,root=root,
                        approved_index=index,authenticate=lambda e,r:allow,
                        ready_check=lambda p,events,n:True)


def contender(root,index,e,sha,queue):
    try:
        queue.put(append(Path(root),index,e,sha)["status"])
    except Exception as exc:
        queue.put(type(exc).__name__)


def test_cross_process_claim_and_restart(tmp_path):
    journal=tmp_path/"journal"
    journal.write_bytes(b"")
    idx={}
    e=event()
    receipt(tmp_path,idx,e)
    sha,_=snapshot(journal)
    assert append(tmp_path,idx,e,sha)["status"]=="RECORDED"
    ack=event("dispatch_ack","ack")
    receipt(tmp_path,idx,ack)
    assert append(tmp_path,idx,ack,snapshot(journal)[0])["status"]=="RECORDED"
    a=event("dispatch_claim","a")
    b=event("dispatch_claim","b")
    for x in (a,b):
        receipt(tmp_path,idx,x)
    sha,_=snapshot(journal)
    ctx=multiprocessing.get_context("spawn")
    queue=ctx.Queue()
    procs=[ctx.Process(target=contender,args=(str(tmp_path),idx,x,sha,queue)) for x in (a,b)]
    for p in procs:p.start()
    for p in procs:
        p.join(15)
        if p.is_alive():
            p.terminate()
            p.join()
            pytest.fail("contention test timed out")
        assert p.exitcode==0
    outcomes=[queue.get(timeout=2),queue.get(timeout=2)]
    assert outcomes.count("RECORDED")==1
    assert set(outcomes)<={"RECORDED","STALE_JOURNAL","WRITER_BUSY_OR_UNRESOLVED"}
    _,events=snapshot(journal)
    assert project(plan(),events)["dispatches"]["n"]["state"]=="CLAIMED"


def test_unknown_and_acl(tmp_path):
    journal=tmp_path/"journal"
    journal.write_bytes(b"")
    idx={}
    e=event()
    receipt(tmp_path,idx,e)
    sha,_=snapshot(journal)
    with pytest.raises(ValueError,match="ACL rejected"):
        append(tmp_path,idx,e,sha,allow=False)
    assert journal.read_bytes()==b""
    append(tmp_path,idx,e,sha)
    unknown=event("dispatch_unknown","u")
    receipt(tmp_path,idx,unknown)
    append(tmp_path,idx,unknown,snapshot(journal)[0])
    second=event(eid="new",dispatch_id="d2")
    receipt(tmp_path,idx,second)
    with pytest.raises(ValueError,match="existing dispatch"):
        append(tmp_path,idx,second,snapshot(journal)[0])
    assert project(plan(),snapshot(journal)[1])["dispatches"]["n"]["state"]=="OUTCOME_UNKNOWN"


def test_partial_tail_and_reservation(tmp_path):
    journal=tmp_path/"journal"
    journal.write_bytes(b"{")
    with pytest.raises(ValueError,match="partial journal"):
        snapshot(journal)
    journal.write_bytes(b"")
    (tmp_path/"journal.writer-reservation").mkdir()
    assert append(tmp_path,{},event(),snapshot(journal)[0])["status"]=="WRITER_BUSY_OR_UNRESOLVED"


def test_handoff_projection_rejects_duplicate_and_wrong_thread():
    p=plan()
    p["work_nodes"].append(node("m",role="A03"))
    events=[event(),event("dispatch_ack","a"),event("dispatch_claim","b"),event("dispatch_running","c"),
            event("dispatch_output","o",artifacts={"artifact":"a"*64})]
    common=dict(node_id="m",role="A03",worker_id="v",thread_id="th2",dispatch_id="d2")
    for kind,eid in [("dispatch_intent","m1"),("dispatch_ack","m2"),("dispatch_claim","m3"),("dispatch_running","m4")]:
        events.append(event(kind,eid,**common))
    h=event("handoff_adopted","h",**common,handoff_id="handoff",producer_node_id="n",
            producer_dispatch_id="d",producer_worker_id="w",producer_thread_id="th",
            artifact_id="artifact",artifact_sha256="a"*64,consumer_input_sha256="a"*64,
            disposition="ADOPTED",reviewer_worker_id="review")
    assert len(project(p,events+[h])["handoffs"])==1
    with pytest.raises(ValueError):
        project(p,events+[dict(h,thread_id="wrong")])
    with pytest.raises(ValueError,match="duplicate handoff"):
        project(p,events+[h,dict(h,event_id="other",handoff_id="other")])
