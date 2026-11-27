import hashlib
import json
import multiprocessing
from pathlib import Path

import pytest
from server.readonly_dispatch import append_event, snapshot
from server.review_authority import ReviewAuthority, content_digest
from server.journal_anchor import JournalAnchor
from server.readonly_dispatch import _file_identity
from server.revision_transactions import RevisionHistory, activate_revision, active_segment
from server.journal_reconciliation import inspect_reservation, current_process_identity
def plan():
    return dict(task_id="t",work_schema="work-nodes/2",work_nodes=[
        dict(id="n",owner_role="A01",action="read",operation_scope="read_only",
             completion_evidence="artifact",resource_domain="local",revision_binding="r",
             attempt_budget=1,depends_on=[],failure_edges=[],required_artifacts=["artifact"])])


def event(kind="dispatch_intent",eid="e",**kw):
    return dict(dict(event=kind,event_id=eid,task_id="t",node_id="n",revision_binding="r",
                     resource_domain="local",role="A01",worker_id="w",thread_id="th",
                     dispatch_id="d",receipt_id=eid,grant_id="grant-"+eid,operation_id="op-"+eid,
                     plan_sha256=content_digest(plan()),action="read_only"),**kw)


def store(root,index,ident,payload):
    data=json.dumps(payload).encode()
    (root/ident).write_bytes(data)
    index[ident]={"path":ident,"sha256":hashlib.sha256(data).hexdigest()}


def receipt(root,index,e):
    import time
    store(root,index,e["receipt_id"],dict(receipt_id=e["receipt_id"],event_projection=e))
    binding={k:e[k] for k in ("event","event_id","task_id","node_id","revision_binding",
             "resource_domain","role","worker_id","thread_id","dispatch_id","plan_sha256","action","operation_id")}
    store(root,index,e["grant_id"],dict(receipt_id=e["grant_id"],operation_binding=binding,
          decision="ALLOW",issuer_worker_id="admin",issuer_role="A00",
          valid_from=time.time()-10,expires_at=time.time()+3600))



def fixture(root):
    old=plan()
    old["work_nodes"][0]["attempt_budget"]=2
    new=json.loads(json.dumps(old))
    new["work_nodes"][0]["revision_binding"]="r2"
    a,b=content_digest(old),content_digest(new)
    h=RevisionHistory(a,{a:old,b:new})
    j=root/"journal"
    j.write_bytes(b"")
    return old,new,h,j,{}


def auth(p,idx):
    return ReviewAuthority(content_digest(p),content_digest(idx),lambda k,v:True)


def fixture_anchor(j,h,sha=None):
    digest,events=snapshot(j)
    return JournalAnchor("t",h.initial_plan_sha256,sha or digest,len(events),_file_identity(j.stat()))


def put(root,idx,p,h,j,kind,eid):
    e=event(kind,eid,revision_binding=p["work_nodes"][0]["revision_binding"],
            plan_sha256=content_digest(p),dispatch_id="d-"+p["work_nodes"][0]["revision_binding"])
    receipt(root,idx,e)
    return append_event(p,j,e,expected_sha256=snapshot(j)[0],root=root,approved_index=idx,
                        authenticate=lambda e,r:True,ready_check=lambda p,es,n:True,
                        authority=auth(p,idx),revision_history=h,journal_anchor=fixture_anchor(j,h))


def transition(root,idx,old,new,eid="rev"):
    e=dict(event="revision_activated",event_id=eid,task_id="t",
           previous_plan_sha256=content_digest(old),next_plan_sha256=content_digest(new),
           approval_receipt_id="review-"+eid)
    store(root,idx,e["approval_receipt_id"],dict(receipt_id=e["approval_receipt_id"],
          event_projection=e,decision="APPROVE_REVISION",creator_worker="creator",
          reviewer_worker="reviewer",reviewer_role="A07"))
    return e


def activate(root,idx,new,h,j,e,sha=None):
    return activate_revision(h,j,e,expected_sha256=sha or snapshot(j)[0],root=root,
                             approved_index=idx,authority=auth(new,idx),journal_anchor=fixture_anchor(j,h,sha))


def test_revision_activation_and_budget(tmp_path):
    old,new,h,j,idx=fixture(tmp_path)
    put(tmp_path,idx,old,h,j,"dispatch_intent","i")
    e=transition(tmp_path,idx,old,new)
    with pytest.raises(ValueError,match="unresolved dispatch"):
        activate(tmp_path,idx,new,h,j,e)
    for kind,eid in [("dispatch_ack","a"),("dispatch_claim","c"),("dispatch_running","run"),("dispatch_failed","f")]:
        put(tmp_path,idx,old,h,j,kind,eid)
    prefix=j.read_bytes()
    assert activate(tmp_path,idx,new,h,j,e)["status"]=="RECORDED"
    assert j.read_bytes().startswith(prefix)
    with pytest.raises(ValueError,match="digest mismatch|inactive plan"):
        put(tmp_path,idx,old,h,j,"dispatch_intent","stale")
    assert put(tmp_path,idx,new,h,j,"dispatch_intent","new")["status"]=="RECORDED"
    view=active_segment(h,snapshot(j)[1],tmp_path,idx,auth(new,idx))
    assert view["attempts"]=={"n":2}
    assert view["retired"][0]["dispatch_view"]["dispatches"]["n"]["state"]=="FAILED"
    assert view["active_plan_sha256"]==content_digest(new)


def test_revision_budget_change_and_native_history_rejected(tmp_path):
    old,new,h,j,idx=fixture(tmp_path)
    new["work_nodes"][0]["attempt_budget"]=3
    h.plans[content_digest(new)]=new
    e=transition(tmp_path,idx,old,new)
    with pytest.raises(ValueError,match="budget changed"):
        activate(tmp_path,idx,new,h,j,e)
    new["work_nodes"][0]["attempt_budget"]=2
    h.plans[content_digest(new)]=new
    e=transition(tmp_path,idx,old,new,"native")
    j.write_text(json.dumps({"event":"submitted","job_id":"original"})+"\n")
    with pytest.raises(ValueError,match="native history"):
        activate(tmp_path,idx,new,h,j,e)
    assert "original" in j.read_text()


def _contend(root,idx,new,h,e,sha,queue):
    try:
        queue.put(activate(Path(root),idx,new,h,Path(root)/"journal",e,sha)["status"])
    except Exception as exc:
        queue.put(type(exc).__name__)


def test_two_process_revision_cas(tmp_path):
    old,new,h,j,idx=fixture(tmp_path)
    e1=transition(tmp_path,idx,old,new,"one")
    other=json.loads(json.dumps(new))
    other["work_nodes"][0]["revision_binding"]="r3"
    h.plans[content_digest(other)]=other
    e2=transition(tmp_path,idx,old,other,"two")
    sha=snapshot(j)[0]
    ctx=multiprocessing.get_context("spawn")
    q=ctx.Queue()
    ps=[ctx.Process(target=_contend,args=(str(tmp_path),idx,p,h,e,sha,q))
        for p,e in [(new,e1),(other,e2)]]
    for p in ps:p.start()
    for p in ps:
        p.join(20)
        if p.is_alive():
            p.terminate()
            p.join()
            pytest.fail("revision contention timeout")
        assert p.exitcode==0
    results=[q.get(timeout=3),q.get(timeout=3)]
    assert results.count("RECORDED")==1
    assert set(results)<={"RECORDED","STALE_JOURNAL","WRITER_BUSY_OR_UNRESOLVED"}
    assert len(snapshot(j)[1])==1


def test_reservation_inspection_is_readonly(tmp_path):
    from server.readonly_dispatch import _file_identity
    j=tmp_path/"journal"
    raw=b'{"event":"old"}\n'
    j.write_bytes(raw)
    lock=tmp_path/"journal.writer-reservation"
    lock.mkdir()
    e={"event":"next","event_id":"a"}
    m=dict(reservation_id="r",pid=123,process_creation_identity=None,phase="PRE_APPEND",
           file_identity=list(_file_identity(j.stat())),original_sha256=hashlib.sha256(raw).hexdigest(),
           original_length=len(raw),event_sha256=content_digest(e))
    (lock/"reservation.json").write_text(json.dumps(m))
    assert inspect_reservation(j)["journal_outcome"]=="ORIGINAL_BYTES_MATCH"
    j.write_bytes(raw+b"{")
    assert inspect_reservation(j)["journal_outcome"]=="PARTIAL_TAIL"
    j.write_bytes(raw+(json.dumps(e)+"\n").encode())
    out=inspect_reservation(j)
    assert out["journal_outcome"]=="SEMANTIC_ONLY"
    line=(json.dumps(e)+"\n").encode()
    m.update(expected_tail_sha256=hashlib.sha256(line).hexdigest(),expected_tail_length=len(line))
    (lock/"reservation.json").write_text(json.dumps(m))
    assert inspect_reservation(j)["journal_outcome"]=="INTENDED_EVENT_BYTES_MATCH"
    j.write_bytes(raw+(json.dumps(e,sort_keys=True,indent=None,separators=(",",":"))+"\n").encode())
    assert inspect_reservation(j)["journal_outcome"]=="SEMANTIC_MATCH_BYTES_DIFFER"
    assert out["owner_state"]=="UNKNOWN" and not out["release_authorized"]
    assert lock.is_dir()


def test_host_observation_no_adapter_and_scoped_receipt(tmp_path):
    from server.host_observation import observe_dispatch
    p=plan()
    idx={}
    e=event(host_call_receipt_id="register")
    binding={k:e[k] for k in ("task_id","node_id","revision_binding","resource_domain",
                             "worker_id","thread_id","dispatch_id","plan_sha256","role")}
    binding["call_id"]="actual-fixture-call"
    store(tmp_path,idx,"register",dict(receipt_id="register",host_binding=binding))
    store(tmp_path,idx,"observation",dict(receipt_id="observation",host_binding=binding,status="RETURNED"))
    kw=dict(dispatch=e,call_id=binding["call_id"],root=tmp_path,index=idx,authority=auth(p,idx))
    assert observe_dispatch(p,**kw)["status"]=="BLOCKED_HOST_ADAPTER"
    assert observe_dispatch(p,**kw,observer=lambda call:"observation")["status"]=="BLOCKED_JOURNAL_CONTEXT"
    with pytest.raises(ValueError,match="registration mismatch"):
        observe_dispatch(p,**dict(kw,call_id="wrong"),observer=lambda call:"observation")


def test_round6_history_receipts_and_truncation(tmp_path):
    old,new,h,j,idx=fixture(tmp_path)
    put(tmp_path,idx,old,h,j,"dispatch_intent","i")
    for kind,eid in [("dispatch_ack","a"),("dispatch_claim","c"),("dispatch_running","run"),("dispatch_failed","f")]:
        put(tmp_path,idx,old,h,j,kind,eid)
    e=transition(tmp_path,idx,old,new)
    anchor=fixture_anchor(j,h)
    raw=j.read_bytes()
    saved=idx.pop("grant-i")
    with pytest.raises(ValueError,match="absent from approved index"):
        activate(tmp_path,idx,new,h,j,e)
    idx["grant-i"]=saved
    j.write_bytes(b"")
    with pytest.raises(ValueError,match="checkpoint/genesis"):
        activate_revision(h,j,e,expected_sha256=snapshot(j)[0],root=tmp_path,
                          approved_index=idx,authority=auth(new,idx),journal_anchor=anchor)
    j.write_bytes(raw)
    assert activate(tmp_path,idx,new,h,j,e)["status"]=="RECORDED"


def test_round6_metadata_anchor(tmp_path):
    j=tmp_path/"journal"
    j.write_bytes(b"")
    lock=tmp_path/"journal.writer-reservation"
    lock.mkdir()
    m=lock/"reservation.json"
    m.write_bytes(b'{}')
    anchor=hashlib.sha256(m.read_bytes()).hexdigest()
    m.write_bytes(b'{ }')
    out=inspect_reservation(j,expected_metadata_sha256=anchor)
    assert out["metadata_anchor_match"] is False
    assert not out["release_authorized"] and lock.exists()
