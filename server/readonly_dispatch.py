"""Opt-in local read-only dispatch pilot, using the original journal.

All writers must use the same canonical journal and serialized writer protocol.
No production scheduler integration or native authorization. The supplied
trusted verifier must validate actual host receipts and ACL; synthetic tests
exercise the contract only. No automatic stale lock release.
"""
import hashlib
import json
import os
import stat
import time
import math
import uuid
from pathlib import Path

from server.task_liveness import validate_nodes, required_artifact_ids
from server.receipt_evidence import load_retained_bytes, load_receipt
from server.review_authority import content_digest, require_authority, require_verified

STEPS = {
    "dispatch_intent": (None, "INTENT"),
    "dispatch_ack": ("INTENT", "DISPATCHED"),
    "dispatch_claim": ("DISPATCHED", "CLAIMED"),
    "dispatch_running": ("CLAIMED", "RUNNING"),
    "dispatch_output": ("RUNNING", "OUTPUT_RECORDED"),
    "dispatch_failed": ("RUNNING", "FAILED"),
}
KINDS = set(STEPS) | {"dispatch_unknown", "handoff_adopted"}
READ_ROLES = {"A01","A02","A03","A05","A06","A07","A08","A09"}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _id(value):
    if not isinstance(value,str) or not value.strip():
        raise ValueError("missing stable identity")
    return value


def _scope(plan,node):
    return (plan["task_id"],node["id"],node["revision_binding"],
            node["resource_domain"])


def _event_scope(event):
    return tuple(_id(event.get(k)) for k in
                 ("task_id","node_id","revision_binding","resource_domain"))


def project(plan, events, *, require_bindings=False):
    """Pure view; retained records are not proof of authenticated host actions."""
    if not validate_nodes(plan):
        raise ValueError("pilot requires reviewed strict plan")
    nodes = {n["id"]:n for n in plan["work_nodes"]}
    active, seen, handoffs = {}, {}, {}
    for event in events:
        kind = event.get("event")
        if kind not in KINDS:
            continue
        eid = _id(event.get("event_id"))
        raw = json.dumps(event,sort_keys=True,allow_nan=False)
        if eid in seen:
            if seen[eid]!=raw:
                raise ValueError("conflicting event ID")
            continue
        seen[eid]=raw
        node=nodes.get(event.get("node_id"))
        if node is None or _event_scope(event)!=_scope(plan,node):
            raise ValueError("dispatch scope/revision mismatch")
        if node["operation_scope"] not in {"read_only","independent_review"} or node["owner_role"] not in READ_ROLES:
            raise ValueError("pilot permits only read-only specialist work")
        if event.get("role")!=node["owner_role"]:
            raise ValueError("role mismatch")
        if require_bindings and (event.get("plan_sha256")!=content_digest(plan) or
                                 event.get("action")!=node["operation_scope"]):
            raise ValueError("dispatch plan or action binding mismatch")
        if node.get("requires_idle_solver") or node.get("requires_submission"):
            raise ValueError("native gate node excluded from read-only pilot")
        _id(event.get("receipt_id"))
        worker, thread = _id(event.get("worker_id")), _id(event.get("thread_id"))
        dispatch = _id(event.get("dispatch_id"))
        current=active.get(node["id"])
        if kind=="handoff_adopted":
            if current is None or current["state"] not in {"RUNNING","OUTPUT_RECORDED"} or (dispatch,worker,thread)!=current["identity"]:
                raise ValueError("handoff consumer not bound to dispatch")
            producer=active.get(event.get("producer_node_id"))
            if producer is None or producer["state"]!="OUTPUT_RECORDED" or producer["identity"]!=(event.get("producer_dispatch_id"),event.get("producer_worker_id"),event.get("producer_thread_id")):
                raise ValueError("handoff producer not bound to output")
            producer_node=nodes[event["producer_node_id"]]
            if producer_node["revision_binding"]!=node["revision_binding"]:
                raise ValueError("cross-revision handoff requires reviewed carry-forward")
            if require_bindings and (event.get("producer_revision_binding")!=producer_node["revision_binding"] or
                                     event.get("producer_plan_sha256")!=content_digest(plan)):
                raise ValueError("producer plan or revision binding mismatch")
            artifact=_id(event.get("artifact_id"))
            if producer["artifacts"].get(artifact)!=event.get("artifact_sha256") or artifact not in producer["artifacts"]:
                raise ValueError("artifact not in recorded output")
            if event.get("disposition")!="ADOPTED" or event.get("consumer_input_sha256")!=event["artifact_sha256"]:
                raise ValueError("no matching actual consumption")
            reviewer=_id(event.get("reviewer_worker_id"))
            if reviewer in {worker,producer["identity"][1]}:
                raise ValueError("handoff review not independent")
            key=(_id(event.get("handoff_id")))
            edge=(producer["identity"][0],dispatch,artifact)
            if key in handoffs or any(v==edge for v in handoffs.values()):
                raise ValueError("duplicate handoff")
            handoffs[key]=edge
            continue
        old,new=STEPS.get(kind,(None,"OUTCOME_UNKNOWN"))
        if kind=="dispatch_unknown":
            if current is None or current["state"] not in {"INTENT","DISPATCHED","CLAIMED","RUNNING"}:
                raise ValueError("no unresolved dispatch")
        elif old is None:
            if current is not None:
                raise ValueError("existing dispatch; reconciliation required")
            if any(v["identity"][0]==dispatch for v in active.values()):
                raise ValueError("duplicate dispatch identity")
        elif current is None or current["state"]!=old:
            raise ValueError("invalid dispatch transition")
        if current is not None and current["identity"]!=(dispatch,worker,thread):
            raise ValueError("dispatch owner changed")
        artifacts={}
        if kind=="dispatch_output":
            artifacts=event.get("artifacts")
            if not isinstance(artifacts,dict) or not required_artifact_ids(node).issubset(artifacts):
                raise ValueError("incomplete output manifest")
            if not all(isinstance(k,str) and isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdef" for c in v) for k,v in artifacts.items()):
                raise ValueError("invalid artifact digest")
        active[node["id"]]={"state":new,"identity":(dispatch,worker,thread),"artifacts":artifacts}
    return {"dispatches":active,"handoffs":handoffs,"native_execution_authorized":False,
            "host_authenticity_verified":False}


def _read(path):
    raw=path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("partial journal tail: reconcile before append")
    events=[json.loads(line) for line in raw.decode("utf-8-sig").splitlines() if line.strip()]
    if any(not isinstance(e,dict) or not e.get("event") for e in events):
        raise ValueError("unmapped journal event")
    return raw,events


def _file_identity(info):
    if not stat.S_ISREG(info.st_mode) or info.st_ino<=0 or info.st_nlink!=1:
        raise ValueError("journal must be a single-link regular file with stable identity")
    return (info.st_dev,info.st_ino)


def snapshot(journal):
    path=Path(journal).resolve(strict=True)
    identity=_file_identity(path.stat())
    raw,events=_read(path)
    if _file_identity(path.stat())!=identity:
        raise ValueError("journal identity changed")
    return _digest(raw),events


def _grant(plan,node,event,root,index,authority):
    ident=_id(event.get("grant_id"))
    if ident==event.get("receipt_id"):
        raise ValueError("operation grant must be distinct from action receipt")
    grant=load_receipt(root,index,ident)
    binding={k:event.get(k) for k in ("event","event_id","task_id","node_id",
             "revision_binding","resource_domain","role","worker_id","thread_id",
             "dispatch_id","plan_sha256","action","operation_id")}
    if grant.get("operation_binding")!=binding or grant.get("decision")!="ALLOW":
        raise ValueError("operation grant scope mismatch")
    _id(event.get("operation_id"))
    if event.get("action")!=node["operation_scope"]:
        raise ValueError("operation is outside read-only node scope")
    issuer=_id(grant.get("issuer_worker_id"))
    if issuer==event.get("worker_id") or grant.get("issuer_role") not in {"A00","A07"}:
        raise ValueError("independent grant issuer required")
    now=time.time()
    start,expiry=grant.get("valid_from"),grant.get("expires_at")
    if (type(start) not in (int,float) or type(expiry) not in (int,float) or
        not math.isfinite(start) or not math.isfinite(expiry) or not start<=now<expiry):
        raise ValueError("operation grant missing or expired")
    require_verified(authority,"operation_grant",grant)


def _ready(plan,events,node,root,index,authority):
    # Existing journal is authoritative. An external callback can veto,
    # but can never override dependencies, existing completion or blockers.
    from scripts.research_resume import work_progress
    for e in events:
        if e.get("event")=="work_unblocked":
            receipt=load_receipt(root,index,e.get("source_receipt_id"))
            if receipt.get("event_projection")!=e or e.get("plan_sha256")!=content_digest(plan):
                raise ValueError("unblock review scope mismatch")
            require_verified(authority,"work_unblocked",receipt)
    state=work_progress(plan,events,[],False,review_context=(root,index,authority),
                        state_only=True)
    if node["id"] not in state["ready"]:
        raise ValueError("node not READY in authoritative journal")


def _reservation_metadata(lock,record):
    p=lock/"reservation.json"
    # The file is advisory evidence, never an automatic stale-lock rule.
    with p.open("x",encoding="utf-8") as stream:
        json.dump(record,stream,sort_keys=True,allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())



def _append_checked(journal,event,expected_sha256,validate):
    """One local cooperating writer protocol for all pilot event types."""
    from server.journal_reconciliation import current_process_identity
    path=Path(journal).resolve(strict=True)
    identity=_file_identity(path.stat())
    lock=path.with_name(path.name+".writer-reservation")
    try:
        lock.mkdir()
    except FileExistsError:
        return {"status":"WRITER_BUSY_OR_UNRESOLVED"}
    uncertain=False
    try:
        if _file_identity(path.stat())!=identity:
            raise ValueError("journal identity changed")
        raw,events=_read(path)
        if _digest(raw)!=expected_sha256:
            return {"status":"STALE_JOURNAL"}
        _reservation_metadata(lock,{"reservation_id":uuid.uuid4().hex,"pid":os.getpid(),
             "process_creation_identity":current_process_identity(),"observed_at":time.time(),
             "file_identity":list(identity),"original_sha256":_digest(raw),
             "original_length":len(raw),"event_sha256":content_digest(event),
             "phase":"PRE_APPEND","native_execution_authorized":False})
        result=validate(events)
        if result is not None:
            return dict(result,journal_sha256=_digest(raw))
        line=(json.dumps(event,sort_keys=True,allow_nan=False)+"\n").encode()
        with path.open("r+b") as stream:
            if (_file_identity(os.fstat(stream.fileno()))!=identity or
                    _file_identity(path.stat())!=identity or stream.read()!=raw):
                raise ValueError("journal changed before append")
            uncertain=True
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
            if (_file_identity(os.fstat(stream.fileno()))!=identity or
                    _file_identity(path.stat())!=identity):
                raise ValueError("journal identity changed: retain reservation")
            stream.seek(0)
            if stream.read()!=raw+line or path.read_bytes()!=raw+line:
                raise ValueError("journal changed during append: retain reservation")
        uncertain=False
        return {"status":"RECORDED","journal_sha256":_digest(raw+line),
                "native_execution_authorized":False}
    finally:
        if not uncertain:
            (lock/"reservation.json").unlink(missing_ok=True)
            lock.rmdir()


def append_event(plan,journal,event,*,expected_sha256,root,approved_index,authenticate,
                 ready_check, authority=None, revision_history=None):
    """Append a read-only event with trusted review and current-plan admission.

    revision_history is an independently supplied initial plan and retained
    plan map (see revision_transactions). No activation is inferred from a
    filename, caller's current plan or a revision label.
    """
    def validate(all_events):
        return _validate_dispatch(plan,all_events,event,root,approved_index,
                                  authenticate,ready_check,authority,revision_history)
    return _append_checked(journal,event,expected_sha256,validate)


def _validate_dispatch(plan,all_events,event,root,approved_index,authenticate,
                       ready_check,authority,revision_history):
    from server.revision_transactions import active_segment, ACTIVATION
    if revision_history is not None:
        # Replay prior revisions from approved plan bytes and scoped receipts.
        state=active_segment(revision_history,all_events,root,approved_index,authority)
        if state["active_plan_sha256"]!=content_digest(plan):
            raise ValueError("inactive plan cannot dispatch")
        events=state["events"]
    else:
        if any(e.get("event")==ACTIVATION for e in all_events):
            raise ValueError("revision history required; do not use stale plan")
        events=all_events
        state=None
    if event.get("event") not in KINDS:
        raise ValueError("unsupported pilot event")
    node=next((n for n in plan["work_nodes"] if n["id"]==event.get("node_id")),None)
    if node is None:
        raise ValueError("unknown work node")
    plan_sha=require_authority(plan,approved_index,authority)
    if event.get("plan_sha256")!=plan_sha:
        raise ValueError("dispatch plan digest mismatch")
    if node["operation_scope"] not in {"read_only","independent_review"} or node["owner_role"] not in READ_ROLES:
        raise ValueError("pilot permits only read-only specialist work")
    _grant(plan,node,event,root,approved_index,authority)
    receipt=load_receipt(root,approved_index,event.get("receipt_id"))
    if receipt.get("event_projection")!=event or authenticate(event,receipt) is not True:
        raise ValueError("trusted host receipt/ACL rejected")
    require_verified(authority,"dispatch_receipt",receipt)
    for old in all_events:
        if old.get("event_id")==event.get("event_id"):
            if old!=event:
                raise ValueError("conflicting event identity")
            return {"status":"ALREADY_RECORDED"}
    if any(old.get("operation_id")==event["operation_id"] for old in all_events if old.get("event") in KINDS):
        raise ValueError("operation identity already used")
    if event["event"]=="dispatch_intent":
        if state is not None and state["attempts"].get(node["id"],0)>=node["attempt_budget"]:
            raise ValueError("original attempt budget exhausted")
        _ready(plan,events,node,root,approved_index,authority)
        if ready_check(plan,events,node) is not True:
            raise ValueError("unverified dependencies or admission")
    if event["event"]=="dispatch_output":
        for ident,digest in event.get("artifacts",{}).items():
            if _digest(load_retained_bytes(root,approved_index,ident))!=digest:
                raise ValueError("output bytes mismatch")
    if event["event"]=="handoff_adopted":
        if _digest(load_retained_bytes(root,approved_index,event["artifact_id"]))!=event["artifact_sha256"]:
            raise ValueError("handoff bytes mismatch")
        for field in ("send_receipt_id","read_receipt_id","review_receipt_id"):
            ident=_id(event.get(field))
            if ident==event["receipt_id"]:
                raise ValueError("distinct handoff receipts required")
            part=load_receipt(root,approved_index,ident)
            binding={k:event[k] for k in ("handoff_id","task_id","revision_binding","plan_sha256",
                     "producer_revision_binding","producer_plan_sha256",
                     "producer_dispatch_id","dispatch_id","artifact_id","artifact_sha256",
                     "producer_worker_id","producer_thread_id","worker_id","thread_id","reviewer_worker_id")}
            if part.get("handoff_binding")!=binding or part.get("receipt_kind")!=field or authenticate(event,part) is not True:
                raise ValueError("handoff evidence rejected")
            require_verified(authority,field,part)
        if len({event[k] for k in ("send_receipt_id","read_receipt_id","review_receipt_id")})!=3:
            raise ValueError("handoff receipts must be distinct")
    project(plan,events+[event],require_bindings=True)
    require_authority(plan,approved_index,authority)
    return None
