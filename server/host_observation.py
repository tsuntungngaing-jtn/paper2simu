"""Adapter contract for a supported host's read-only status observation.

No Codex endpoint is invented. The caller injects a supported read-only
observer and trusted authorization verifier; no dispatch or retry is invoked.
"""
import math
import time
from pathlib import Path
from server.receipt_evidence import load_receipt
from server.review_authority import require_authority, require_verified


def observe_dispatch(plan,*,dispatch,call_id,root,index,authority,observer=None,
                     journal=None,journal_anchor=None,revision_history=None,
                     minimum_sequence=None,max_age_seconds=60):
    """Validate retained call binding, then optionally observe exact call ID.

    Observer returns a retained receipt ID already present in the approved
    index. Real host enrollment/receipt issuance remains external.
    """
    require_authority(plan,index,authority)
    if not isinstance(call_id,str) or not call_id.strip():
        raise ValueError("actual host call ID required")
    binding={k:dispatch.get(k) for k in ("task_id","node_id","revision_binding","resource_domain",
                                      "worker_id","thread_id","dispatch_id","plan_sha256","role")}
    if any(not isinstance(v,str) or not v.strip() for v in binding.values()):
        raise ValueError("incomplete host observation scope")
    node=next((n for n in plan["work_nodes"] if n["id"]==binding["node_id"]),None)
    if (node is None or binding["task_id"]!=plan["task_id"] or
        binding["revision_binding"]!=node["revision_binding"] or binding["resource_domain"]!=node["resource_domain"] or
        binding["role"]!=node["owner_role"] or node["operation_scope"] not in {"read_only","independent_review"} or
        node["owner_role"] in {"A00","A04"} or binding["plan_sha256"]!=authority.plan_sha256):
        raise ValueError("host observation outside approved read-only scope")
    binding["call_id"]=call_id
    registration=load_receipt(root,index,dispatch.get("host_call_receipt_id"))
    if registration.get("host_binding")!=binding:
        raise ValueError("host call registration mismatch")
    require_verified(authority,"host_call_registration",registration)
    if observer is None:
        return {"status":"BLOCKED_HOST_ADAPTER","native_execution_authorized":False}
    if journal is None or journal_anchor is None:
        return {"status":"BLOCKED_JOURNAL_CONTEXT","native_execution_authorized":False,"completion_verified":False}
    from server.readonly_dispatch import _read,_file_identity,project,verify_historical_dispatch,KINDS
    from server.revision_transactions import active_segment,ACTIVATION
    from server.journal_anchor import require_anchor
    from server.review_authority import content_digest
    path=Path(journal).resolve(strict=True)
    identity=_file_identity(path.stat())
    raw,events=_read(path)
    genesis=revision_history.initial_plan_sha256 if revision_history is not None else content_digest(plan)
    require_anchor(journal_anchor,task_id=plan["task_id"],genesis_sha256=genesis,raw=raw,
                   events=events,identity=identity,authority=authority)
    if revision_history is None:
        if any(e.get("event")==ACTIVATION for e in events):
            raise ValueError("revision history required")
        for e in events:
            if e.get("event") in KINDS:
                verify_historical_dispatch(plan,e,root,index,authority)
        segment=events
    else:
        state=active_segment(revision_history,events,root,index,authority)
        if state["active_plan_sha256"]!=content_digest(plan):
            raise ValueError("inactive plan cannot be observed as current")
        segment=state["events"]
    view=project(plan,segment,require_bindings=True)["dispatches"].get(node["id"])
    if (view is None or view["identity"]!=(binding["dispatch_id"],binding["worker_id"],binding["thread_id"]) or
        view["state"] not in {"DISPATCHED","CLAIMED","RUNNING"}):
        raise ValueError("no matching active dispatch")
    if type(minimum_sequence) is not int or minimum_sequence<0 or type(max_age_seconds) not in (int,float) or not math.isfinite(max_age_seconds) or not 0<max_age_seconds<=300:
        raise ValueError("trusted observation floor and bounded freshness required")
    request=dict(binding,journal_sha256=journal_anchor.journal_sha256,minimum_sequence=minimum_sequence)
    require_verified(authority,"host_observation_floor",request)
    require_verified(authority,"host_observe_permission",request)
    started=time.time()
    ident=observer(call_id)
    receipt=load_receipt(root,index,ident)
    if receipt.get("host_binding")!=binding or receipt.get("status") not in {"DISPATCHED","RUNNING","RETURNED","FAILED","UNKNOWN"}:
        raise ValueError("host observation mismatch")
    seq,stamp=receipt.get("sequence"),receipt.get("observed_at")
    now=time.time()
    if (receipt.get("journal_sha256")!=journal_anchor.journal_sha256 or type(seq) is not int or seq<=minimum_sequence or
        type(stamp) not in (int,float) or not math.isfinite(stamp) or not started<=stamp<=now or now-stamp>max_age_seconds):
        raise ValueError("stale or unbound host observation")
    require_verified(authority,"host_observation",receipt)
    if _file_identity(path.stat())!=identity or path.read_bytes()!=raw:
        raise ValueError("journal changed during observation")
    require_authority(plan,index,authority)
    return {"status":receipt["status"],"receipt_id":ident,"sequence":seq,"observed_at":stamp,"native_execution_authorized":False,
            "completion_verified":False}
