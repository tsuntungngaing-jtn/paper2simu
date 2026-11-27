"""Stage a newly returned receipt, then independently approve an additive index delta."""
import hashlib
import json
from pathlib import Path
from server.review_authority import content_digest,require_verified
from server.receipt_evidence import load_receipt,load_retained_bytes


def stage(root,receipt_id,data):
    if not isinstance(data,bytes) or not isinstance(receipt_id,str) or not receipt_id or len(receipt_id)>200:
        raise ValueError("actual retained receipt bytes required")
    obj=json.loads(data)
    if not isinstance(obj,dict) or obj.get("receipt_id")!=receipt_id:
        raise ValueError("receipt identity mismatch")
    root=Path(root).resolve(strict=True)
    digest=hashlib.sha256(data).hexdigest()
    name="staged-"+digest+".json"
    path=root/name
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            import os
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.is_symlink() or path.read_bytes()!=data:
            raise ValueError("staging collision")
    return {receipt_id:{"path":name,"sha256":digest}}


def approve_delta(root,index,delta,approval,authority):
    if authority.index_sha256!=content_digest(index):
        raise ValueError("old approved index mismatch")
    if not delta or set(index)&set(delta):
        raise ValueError("index delta must be additive")
    merged=dict(index,**delta)
    binding={"old_index_sha256":content_digest(index),"delta_sha256":content_digest(delta),
             "new_index_sha256":content_digest(merged),"plan_sha256":authority.plan_sha256}
    if approval.get("binding")!=binding or approval.get("decision")!="APPROVE_INDEX_DELTA":
        raise ValueError("delta approval mismatch")
    a,b=approval.get("producer_worker"),approval.get("reviewer_worker")
    if not all(isinstance(v,str) and v.strip() for v in (a,b)) or a==b or approval.get("reviewer_role") not in {"A03","A05","A07"}:
        raise ValueError("independent delta reviewer required")
    for ident in delta:
        load_receipt(root,merged,ident)
    require_verified(authority,"index_delta_approval",approval)
    # Caller must obtain a new trusted ReviewAuthority for this new digest.
    return {"index":merged,"index_sha256":binding["new_index_sha256"],
            "status":"APPROVED_BY_CALLER_NEW_AUTHORITY_REQUIRED"}
