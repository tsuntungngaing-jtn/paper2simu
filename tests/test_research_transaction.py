import hashlib
import json
import pytest
from server.checkpoint_store import CheckpointStore
from server.journal_anchor import JournalAnchor
from server.review_authority import ReviewAuthority,content_digest
from server.artifact_dependencies import evaluate_carry
from server.dynamic_evidence import stage,approve_delta
from server.research_transaction import autonomy_metrics,cross_host_admission,ResearchTransaction


def authority(index):
    return ReviewAuthority("p",content_digest(index),lambda k,v:True)


def test_checkpoint_pending_and_stale(tmp_path):
    a=JournalAnchor("t","a"*64,hashlib.sha256(b"").hexdigest(),0,(1,2))
    s=CheckpointStore.initialize(tmp_path/"check.sqlite",a,authority({}))
    assert s.inspect()==(a,None)
    s.prepare(a,"b"*64,"c"*64)
    assert s.inspect()[1] is not None
    with pytest.raises(ValueError,match="pending"):
        s.prepare(a,"d"*64,"c"*64)
    s.finalize(a,"b"*64,"c"*64)
    assert s.inspect()[0].sequence==1
    with pytest.raises(ValueError,match="stale"):
        s.prepare(a,"d"*64,"c"*64)


def test_dependency_transitive_invalidation(tmp_path):
    idx={}
    manifest={}
    for ident,keys,parents in [("geometry",["size"],[]),("mesh",["mesh"],["geometry"]),("paper",["source"],[])]:
        data=ident.encode()
        (tmp_path/ident).write_bytes(data)
        d=hashlib.sha256(data).hexdigest()
        idx[ident]={"path":ident,"sha256":d}
        manifest[ident]={"sha256":d,"inputs":keys,"parents":parents}
    old={"size":"a"*64,"mesh":"b"*64,"source":"c"*64}
    new=dict(old,size="d"*64)
    result=evaluate_carry(old,new,manifest,root=tmp_path,index=idx,authority=authority(idx))
    assert result["geometry"]["status"]==result["mesh"]["status"]=="INVALIDATED"
    assert result["paper"]["status"]=="CANDIDATE_NEW_REVIEW_REQUIRED"
    assert not result["paper"]["completion_verified"]


def test_dynamic_evidence_additive(tmp_path):
    idx={}
    delta=stage(tmp_path,"r",b'{"receipt_id":"r"}')
    a=authority(idx)
    approval={"binding":{"old_index_sha256":content_digest(idx),"delta_sha256":content_digest(delta),
                         "new_index_sha256":content_digest(delta),"plan_sha256":a.plan_sha256},
              "decision":"APPROVE_INDEX_DELTA","producer_worker":"w","reviewer_worker":"review","reviewer_role":"A07"}
    result=approve_delta(tmp_path,idx,delta,approval,a)
    assert idx=={} and result["index"]==delta
    with pytest.raises(ValueError):
        approve_delta(tmp_path,idx,delta,dict(approval,reviewer_worker="w"),a)
    with pytest.raises(ValueError):
        approve_delta(tmp_path,delta,delta,approval,authority(delta))


def test_unknown_metrics_and_cross_host():
    e={"event_id":"i","event":"dispatch_intent"}
    result=autonomy_metrics([e,e])
    assert result["recorded_intents"]==1 and result["real_host_dispatch_count"] is None
    assert not cross_host_admission(local_domain="a",requested_domain="b",authority=None,binding={})["authorized"]


def test_integrated_checkpoint_append_and_truncation(tmp_path):
    import time
    from server.readonly_dispatch import _file_identity
    p=dict(task_id="t",work_schema="work-nodes/2",work_nodes=[
        dict(id="n",owner_role="A01",action="read",operation_scope="read_only",
             completion_evidence="artifact",resource_domain="local",revision_binding="r",
             attempt_budget=1,depends_on=[],failure_edges=[],required_artifacts=["artifact"])])
    j=tmp_path/"journal"
    j.write_bytes(b"")
    a=JournalAnchor("t",content_digest(p),hashlib.sha256(b"").hexdigest(),0,_file_identity(j.stat()))
    s=CheckpointStore.initialize(tmp_path/"checkpoint.sqlite",a,authority({}))
    tx=ResearchTransaction(j,s)
    idx={}
    def put(ident,obj):
        data=json.dumps(dict(obj,receipt_id=ident)).encode()
        (tmp_path/ident).write_bytes(data)
        idx[ident]={"path":ident,"sha256":hashlib.sha256(data).hexdigest()}
    e=dict(event="dispatch_intent",event_id="i",task_id="t",node_id="n",revision_binding="r",
           resource_domain="local",role="A01",worker_id="w",thread_id="th",
           dispatch_id="d",receipt_id="receipt",grant_id="grant",operation_id="op",
           plan_sha256=content_digest(p),action="read_only")
    put("receipt",{"event_projection":e})
    binding={k:e[k] for k in ("event","event_id","task_id","node_id","revision_binding",
              "resource_domain","role","worker_id","thread_id","dispatch_id","plan_sha256","action","operation_id")}
    put("grant",dict(operation_binding=binding,decision="ALLOW",issuer_worker_id="admin",
                     issuer_role="A00",valid_from=time.time()-10,expires_at=time.time()+3600))
    auth=ReviewAuthority(content_digest(p),content_digest(idx),
                         lambda k,v:s.verify_checkpoint(v) if k=="journal_checkpoint" else True)
    assert tx.candidates(p,root=tmp_path,index=idx,authority=auth)["candidates"]==["n"]
    kw=dict(root=tmp_path,approved_index=idx,authenticate=lambda e,r:True,
            ready_check=lambda p,es,n:True,authority=auth)
    assert tx.append(p,e,**kw)["status"]=="RECORDED"
    assert tx.anchor().sequence==1
    assert tx.anchor().journal_sha256==hashlib.sha256(j.read_bytes()).hexdigest()
    assert tx.candidates(p,root=tmp_path,index=idx,authority=auth)["candidates"]==[]
    j.write_bytes(b"")
    assert tx.append(p,e,**kw)["status"]=="STALE_JOURNAL"
    assert tx.anchor().sequence==1
