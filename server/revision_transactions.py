"""Opt-in single-journal revision activation for local read-only research.

No native history migration, automatic carry-forward, resource release or
solver authority. Every historical activation is rechecked against retained
plans and externally trusted approval receipts. One activation is one CAS row.
"""
from dataclasses import dataclass
from server.review_authority import content_digest, require_authority, require_verified
from server.receipt_evidence import load_receipt, load_retained_bytes
from server.task_liveness import validate_nodes

ACTIVATION="revision_activated"
WORK={"work_completed","work_blocked","work_unblocked"}


@dataclass(frozen=True)
class RevisionHistory:
    initial_plan_sha256: str
    plans: dict


def _plan(history,digest):
    p=history.plans.get(digest)
    if not isinstance(p,dict) or content_digest(p)!=digest or not validate_nodes(p):
        raise ValueError("missing or altered approved plan")
    for n in p["work_nodes"]:
        if n["operation_scope"] not in {"read_only","independent_review"} or n["owner_role"] in {"A00","A04"} or n.get("requires_submission") or n.get("requires_idle_solver"):
            raise ValueError("revision pilot excludes native and orchestrator nodes")
    return p


def _transition(old,new):
    # Preserve task-wide clock, queue and native controls byte-for-byte at
    # canonical JSON level. Pilot only changes the reviewed node definitions.
    if {k:v for k,v in old.items() if k!="work_nodes"}!={k:v for k,v in new.items() if k!="work_nodes"}:
        raise ValueError("task-wide plan fields cannot change in revision pilot")
    before={n["id"]:n for n in old["work_nodes"]}
    after={n["id"]:n for n in new["work_nodes"]}
    if set(before)!=set(after):
        raise ValueError("node addition/removal requires separate reviewed migration")
    for ident,n in before.items():
        m=after[ident]
        for k in ("resource_domain","attempt_budget","owner_role","operation_scope","requires_submission","requires_idle_solver"):
            if m.get(k)!=n.get(k):
                raise ValueError("original scope or budget changed")
        if m["revision_binding"]==n["revision_binding"]:
            raise ValueError("new node revision identity required")
    return before,after


def active_segment(history,events,root,index,authority):
    """Replay exact active segment, prior views and cumulative dispatch budget.

    A trusted caller supplies pinned plan history and current approved index.
    Only the original single journal is used. Legacy/native/incident streams
    must be reconciled separately; never silently filter them during activation.
    """
    from server.readonly_dispatch import KINDS, project
    if not isinstance(history,RevisionHistory):
        raise ValueError("approved revision history required")
    current=history.initial_plan_sha256
    plan=_plan(history,current)
    if authority is None:
        raise ValueError("review authority required")
    require_verified(authority,"revision_genesis",{"task_id":plan["task_id"],"initial_plan_sha256":current})
    used={current}
    revisions={n["id"]:{n["revision_binding"]} for n in plan["work_nodes"]}
    seen,attempts,retired,segment,carry={},{},[],[],[]
    for e in events:
        kind=e.get("event")
        if kind not in KINDS|WORK|{ACTIVATION}:
            raise ValueError("unmapped or native history requires separate reconciliation")
        eid=e.get("event_id")
        if not isinstance(eid,str) or not eid:
            raise ValueError("stable revision journal event ID required")
        if eid in seen:
            if seen[eid]!=e:
                raise ValueError("conflicting revision journal event ID")
            continue
        seen[eid]=e
        if kind!=ACTIVATION:
            if e.get("plan_sha256")!=current:
                raise ValueError("event belongs to inactive or unbound plan")
            if kind=="dispatch_intent":
                node=next((n for n in plan["work_nodes"] if n["id"]==e.get("node_id")),None)
                if node is None:
                    raise ValueError("unknown budget scope")
                attempts[node["id"]]=attempts.get(node["id"],0)+1
                if attempts[node["id"]]>node["attempt_budget"]:
                    raise ValueError("original attempt budget exhausted")
            segment.append(e)
            continue
        next_sha=e.get("next_plan_sha256")
        if e.get("task_id")!=plan["task_id"] or e.get("previous_plan_sha256")!=current or next_sha in used:
            raise ValueError("stale predecessor or reused plan identity")
        new=_plan(history,next_sha)
        before,after=_transition(plan,new)
        if any(n["revision_binding"] in revisions[i] for i,n in after.items()):
            raise ValueError("reused node revision identity")
        view=project(plan,segment,require_bindings=True)
        if any(v["state"] not in {"OUTPUT_RECORDED","FAILED"} for v in view["dispatches"].values()):
            raise ValueError("unresolved dispatch blocks revision activation")
        # Existing scientific/work review events require a separate historical
        # review migration; activation must not drop blockers or completion.
        if any(x["event"] in WORK for x in segment):
            raise ValueError("historical work review migration required")
        receipt=load_receipt(root,index,e.get("approval_receipt_id"))
        if receipt.get("event_projection")!=e or receipt.get("decision")!="APPROVE_REVISION":
            raise ValueError("revision approval scope mismatch")
        creator,reviewer=receipt.get("creator_worker"),receipt.get("reviewer_worker")
        if (not all(isinstance(v,str) and v.strip() for v in (creator,reviewer)) or creator==reviewer or
                receipt.get("reviewer_role") not in {"A03","A05","A07"}):
            raise ValueError("independent revision reviewer required")
        require_verified(authority,"revision_approval",receipt)
        # Carries are evidence references only: never mark new nodes completed
        # or establish TRACE used without a new independent completion review.
        refs=e.get("carry_candidates",[])
        if not isinstance(refs,list):
            raise ValueError("invalid carry candidates")
        keys=set()
        for item in refs:
            node,artifact,digest=item.get("node_id"),item.get("artifact_id"),item.get("sha256")
            output=view["dispatches"].get(node,{})
            key=(node,artifact)
            if key in keys or output.get("state")!="OUTPUT_RECORDED" or output.get("artifacts",{}).get(artifact)!=digest or artifact not in output.get("artifacts",{}):
                raise ValueError("carry must reference original recorded output")
            if reviewer==output["identity"][1]:
                raise ValueError("carry reviewer not independent of producer")
            import hashlib
            if hashlib.sha256(load_retained_bytes(root,index,artifact)).hexdigest()!=digest:
                raise ValueError("carry artifact bytes changed")
            keys.add(key)
            carry.append(dict(item,from_plan_sha256=current,to_plan_sha256=next_sha,
                              status="CANDIDATE_NEW_REVIEW_REQUIRED"))
        retired.append({"plan_sha256":current,"dispatch_view":view,"events":list(segment)})
        current,plan,segment=next_sha,new,[]
        used.add(current)
        for i,n in after.items():
            revisions[i].add(n["revision_binding"])
    require_authority(plan,index,authority)
    project(plan,segment,require_bindings=True)
    return {"active_plan_sha256":current,"events":segment,"retired":retired,
            "attempts":attempts,"carry_candidates":carry,
            "native_execution_authorized":False,"host_authenticity_verified":False}


def activate_revision(history,journal,event,*,expected_sha256,root,approved_index,authority):
    """Atomically append one approved transition to the original local journal."""
    from server.readonly_dispatch import _append_checked
    if event.get("event")!=ACTIVATION:
        raise ValueError("revision activation event required")
    def validate(events):
        for old in events:
            if old.get("event_id")==event.get("event_id"):
                if old!=event:
                    raise ValueError("conflicting revision event ID")
                active_segment(history,events,root,approved_index,authority)
                return {"status":"ALREADY_RECORDED"}
        active_segment(history,events+[event],root,approved_index,authority)
        return None
    return _append_checked(journal,event,expected_sha256,validate)
