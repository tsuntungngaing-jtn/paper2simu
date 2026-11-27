"""Reviewed input dependency graph: candidate reuse only, never acceptance."""
from graphlib import TopologicalSorter
from server.review_authority import content_digest,require_verified
from server.receipt_evidence import load_retained_bytes
import hashlib
import re

HEX=re.compile(r"[0-9a-f]{64}\Z")


def _hash(v):
    if not isinstance(v,str) or not HEX.fullmatch(v):
        raise ValueError("invalid dependency digest")
    return v


def evaluate_carry(old,new,manifest,*,root,index,authority):
    """Manifests explicitly list input keys and upstream artifact IDs.
    Missing keys fail closed; actual scientific scope requires new review.
    """
    binding={"old_inputs_sha256":content_digest(old),"new_inputs_sha256":content_digest(new),
             "manifest_sha256":content_digest(manifest)}
    require_verified(authority,"artifact_dependency_manifest",binding)
    graph={}
    for ident,item in manifest.items():
        keys=item.get("inputs")
        parents=item.get("parents")
        if not isinstance(keys,list) or not isinstance(parents,list) or not keys or len(set(keys))!=len(keys) or len(set(parents))!=len(parents):
            raise ValueError("explicit unique input and parent keys required")
        if any(p not in manifest for p in parents):
            raise ValueError("unknown upstream artifact")
        _hash(item.get("sha256"))
        graph[ident]=parents
    out={}
    for ident in TopologicalSorter(graph).static_order():
        item=manifest[ident]
        changed=[k for k in item["inputs"] if k not in old or k not in new or _hash(old[k])!=_hash(new[k])]
        upstream=[p for p in graph[ident] if out[p]["status"]!="CANDIDATE_NEW_REVIEW_REQUIRED"]
        actual=hashlib.sha256(load_retained_bytes(root,index,ident)).hexdigest()
        if actual!=item["sha256"]:
            raise ValueError("artifact bytes changed")
        out[ident]={"status":"INVALIDATED" if changed or upstream else "CANDIDATE_NEW_REVIEW_REQUIRED",
                    "changed_inputs":changed,"invalidated_parents":upstream,
                    "completion_verified":False,"trace_used":False}
    return out
