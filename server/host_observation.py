"""Adapter contract for a supported host's read-only status observation.

No Codex endpoint is invented. The caller injects a supported read-only
observer and trusted authorization verifier; no dispatch or retry is invoked.
"""
from server.receipt_evidence import load_receipt
from server.review_authority import require_authority, require_verified


def observe_dispatch(plan,*,dispatch,call_id,root,index,authority,observer=None):
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
    require_verified(authority,"host_observe_permission",binding)
    ident=observer(call_id)
    receipt=load_receipt(root,index,ident)
    if receipt.get("host_binding")!=binding or receipt.get("status") not in {"DISPATCHED","RUNNING","RETURNED","FAILED","UNKNOWN"}:
        raise ValueError("host observation mismatch")
    require_verified(authority,"host_observation",receipt)
    require_authority(plan,index,authority)
    return {"status":receipt["status"],"receipt_id":ident,"native_execution_authorized":False,
            "completion_verified":False}
