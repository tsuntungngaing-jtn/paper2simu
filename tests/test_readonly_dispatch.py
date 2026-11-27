import hashlib
import json
import multiprocessing
import os
import time
from pathlib import Path

import pytest
from server.readonly_dispatch import append_event, snapshot, project
from server.review_authority import ReviewAuthority, content_digest


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
                     dispatch_id="d",receipt_id=eid,grant_id="grant-"+eid,
                     operation_id="op-"+eid,plan_sha256=content_digest(plan()),action="read_only"),**kw)


def store(root,index,ident,payload):
    data=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
    (root/ident).write_bytes(data)
    index[ident]={"path":ident,"sha256":hashlib.sha256(data).hexdigest()}


def receipt(root,index,e,**overrides):
    store(root,index,e["receipt_id"],dict(receipt_id=e["receipt_id"],event_projection=e))
    binding={k:e.get(k) for k in ("event","event_id","task_id","node_id","revision_binding",
             "resource_domain","role","worker_id","thread_id","dispatch_id","plan_sha256",
             "action","operation_id")}
    grant=dict(receipt_id=e["grant_id"],operation_binding=binding,decision="ALLOW",
               issuer_worker_id="admin",issuer_role="A00",valid_from=time.time()-10,
               expires_at=time.time()+3600)
    store(root,index,e["grant_id"],dict(grant,**overrides))


def append(root,index,e,sha,allow=True):
    return append_event(plan(),root/"journal",e,expected_sha256=sha,root=root,
                        approved_index=index,authenticate=lambda e,r:allow,
                        ready_check=lambda p,events,n:True,
                        authority=ReviewAuthority(content_digest(plan()),content_digest(index),lambda k,v:True))


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


def test_hardlink_rejected_before_append(tmp_path):
    journal=tmp_path/"journal"
    journal.write_bytes(b"")
    alias=tmp_path/"alias"
    try:
        os.link(journal,alias)
    except OSError:
        pytest.skip("filesystem does not support hard links")
    e=event()
    idx={}
    receipt(tmp_path,idx,e)
    for path in (journal,alias):
        with pytest.raises(ValueError,match="single-link"):
            snapshot(path)
        with pytest.raises(ValueError,match="single-link"):
            append_event(plan(),path,e,expected_sha256=hashlib.sha256(b"").hexdigest(),
                         root=tmp_path,approved_index=idx,authenticate=lambda e,r:True,
                         ready_check=lambda p,events,n:True)
    assert journal.read_bytes()==b""


@pytest.mark.parametrize("change", [{"expires_at":1},{"issuer_worker_id":"w"}])
def test_grant_rejected_even_with_permissive_callback(tmp_path,change):
    (tmp_path/"journal").write_bytes(b"")
    e=event()
    idx={}
    receipt(tmp_path,idx,e,**change)
    with pytest.raises(ValueError):
        append(tmp_path,idx,e,snapshot(tmp_path/"journal")[0])
    assert (tmp_path/"journal").read_bytes()==b""


def test_blocked_and_dependency_are_not_overridden(tmp_path):
    p=plan()
    p["work_nodes"].append(node("parent"))
    p["work_nodes"][0]["depends_on"]=["parent"]
    j=tmp_path/"journal"
    j.write_bytes(b"")
    e=event(plan_sha256=content_digest(p))
    idx={}
    receipt(tmp_path,idx,e)
    with pytest.raises(ValueError,match="not READY"):
        append_event(p,j,e,expected_sha256=snapshot(j)[0],root=tmp_path,
                     approved_index=idx,authenticate=lambda e,r:True,
                     ready_check=lambda p,events,n:True,
                     authority=ReviewAuthority(content_digest(p),content_digest(idx),lambda k,v:True))
    assert j.read_bytes()==b""
    p=plan()
    b=dict(event="work_blocked",node_id="n",evidence_refs=["x"],blocker_type="input_missing",
           timestamp_utc="now",last_attempt="read",actual_return="missing",resume_when="data",next_action="inspect")
    j.write_text(json.dumps(b)+"\n")
    idx={}
    e=event()
    receipt(tmp_path,idx,e)
    with pytest.raises(ValueError,match="not READY"):
        append(tmp_path,idx,e,snapshot(j)[0])


def test_readonly_action_and_trust_boundary(tmp_path):
    j=tmp_path/"journal"
    j.write_bytes(b"")
    idx={}
    e=event(action="native_submission")
    receipt(tmp_path,idx,e)
    with pytest.raises(ValueError,match="outside read-only"):
        append(tmp_path,idx,e,snapshot(j)[0])
    e=event()
    receipt(tmp_path,idx,e)
    with pytest.raises(ValueError,match="authority required"):
        append_event(plan(),j,e,expected_sha256=snapshot(j)[0],root=tmp_path,
                     approved_index=idx,authenticate=lambda e,r:True,ready_check=lambda p,events,n:True)
    assert j.read_bytes()==b""
