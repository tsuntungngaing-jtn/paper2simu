"""Read-only local reservation inspection. Never removes a reservation."""
import hashlib
import json
import os
from pathlib import Path


def current_process_identity():
    """Capture birth identity of the current process, not a recycled foreign PID."""
    try:
        if os.name=="nt":
            import ctypes
            from ctypes import wintypes
            k=ctypes.WinDLL("kernel32",use_last_error=True)
            get=k.GetCurrentProcess
            get.restype=wintypes.HANDLE
            query=k.GetProcessTimes
            query.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
            query.restype=wintypes.BOOL
            values=[wintypes.FILETIME() for _ in range(4)]
            if query(get(),*(ctypes.byref(v) for v in values)):
                creation=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
                if creation>0:
                    return {"source":"windows_current_process","creation_filetime":creation}
        elif Path("/proc/self/stat").is_file():
            # Linux stat field 22, after the parenthesized comm (may contain spaces).
            ticks=Path("/proc/self/stat").read_text().rsplit(")",1)[1].split()[19]
            boot=Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            if ticks.isdigit() and boot:
                return {"source":"linux_proc_self","start_ticks":int(ticks),"boot_id":boot}
    except (OSError,ValueError,IndexError,AttributeError,TypeError):
        pass
    return None


def inspect_reservation(journal, *, expected_metadata_sha256=None):
    """Compare actual bytes against retained reservation; no liveness inference.

    Metadata may be absent, incomplete or caller-controlled. Even matching
    bytes are not proof of a terminated worker or authorized lock release.
    """
    from server.readonly_dispatch import _file_identity
    from server.review_authority import content_digest
    path=Path(journal).resolve(strict=True)
    lock=path.with_name(path.name+".writer-reservation")
    out={"status":"NO_RESERVATION","owner_state":"UNKNOWN","release_authorized":False,
         "native_execution_authorized":False,"journal_outcome":"UNKNOWN",
         "bytes_match":None,"transition_valid":"UNKNOWN","metadata_anchor_match":None}
    if not lock.exists() and not lock.is_symlink():
        return out
    out["status"]="UNRESOLVED"
    try:
        if lock.is_symlink() or not lock.is_dir():
            raise ValueError("invalid reservation path")
        meta=lock/"reservation.json"
        if meta.is_symlink():
            raise ValueError("invalid metadata path")
        meta_raw=meta.read_bytes()
        out["metadata_bytes_sha256"]=hashlib.sha256(meta_raw).hexdigest()
        if expected_metadata_sha256 is not None:
            out["metadata_anchor_match"]=out["metadata_bytes_sha256"]==expected_metadata_sha256
            if not out["metadata_anchor_match"]:
                raise ValueError("reservation metadata anchor mismatch")
        m=json.loads(meta_raw)
        out["reservation"]=m
        if not isinstance(m,dict) or not m.get("reservation_id") or m.get("phase")!="PRE_APPEND":
            raise ValueError("incomplete reservation metadata")
        identity=_file_identity(path.stat())
        if list(identity)!=m.get("file_identity"):
            raise ValueError("file identity differs")
        with path.open("rb") as stream:
            if _file_identity(os.fstat(stream.fileno()))!=identity:
                raise ValueError("file identity differs")
            raw=stream.read()
            if _file_identity(path.stat())!=identity:
                raise ValueError("file identity differs")
        n=m.get("original_length")
        if type(n) is not int or n<0 or len(raw)<n or hashlib.sha256(raw[:n]).hexdigest()!=m.get("original_sha256"):
            raise ValueError("original prefix differs")
        tail=raw[n:]
        if not tail:
            out["journal_outcome"]="ORIGINAL_BYTES_MATCH"
        elif not tail.endswith(b"\n"):
            out["journal_outcome"]="PARTIAL_TAIL"
        else:
            rows=tail.splitlines()
            semantic=len(rows)==1 and content_digest(json.loads(rows[0]))==m.get("event_sha256")
            if semantic:
                expected=m.get("expected_tail_sha256")
                length=m.get("expected_tail_length")
                if expected is None and length is None:
                    out["journal_outcome"]="SEMANTIC_ONLY"
                elif (isinstance(expected,str) and len(expected)==64 and type(length) is int and
                      len(tail)==length and hashlib.sha256(tail).hexdigest()==expected):
                    out["journal_outcome"]="INTENDED_EVENT_BYTES_MATCH"
                    out["bytes_match"]=True
                else:
                    out["journal_outcome"]="SEMANTIC_MATCH_BYTES_DIFFER"
                    out["bytes_match"]=False
            else:
                out["journal_outcome"]="UNEXPECTED_TAIL"
                out["bytes_match"]=False
        out["journal_sha256"]=hashlib.sha256(raw).hexdigest()
        out["metadata_sha256"]=content_digest(m)
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        out["diagnostic"]=str(exc)
    return out


def reconcile_owner(journal,*,expected_metadata_sha256,root,index,authority,
                    observation_id,review_id):
    """Only a candidate, never release. Trusted verifier must authenticate the
    original metadata anchor, exact process exit and independent legal replay.
    """
    from server.receipt_evidence import load_receipt
    from server.review_authority import require_verified, content_digest
    out=inspect_reservation(journal,expected_metadata_sha256=expected_metadata_sha256)
    out["candidate"]="BLOCKED"
    if (out.get("metadata_anchor_match") is not True or
        out["journal_outcome"] not in {"ORIGINAL_BYTES_MATCH","INTENDED_EVENT_BYTES_MATCH"}):
        return out
    m=out["reservation"]
    if not isinstance(m.get("process_creation_identity"),dict) or not m["process_creation_identity"]:
        return out
    if not isinstance(expected_metadata_sha256,str) or observation_id==review_id:
        return out
    if authority is None or authority.index_sha256!=content_digest(index):
        raise ValueError("approved evidence index required")
    binding={k:m.get(k) for k in ("reservation_id","file_identity","pid","process_creation_identity")}
    binding.update(metadata_bytes_sha256=expected_metadata_sha256,
                   journal_sha256=out["journal_sha256"],journal_outcome=out["journal_outcome"])
    require_verified(authority,"reservation_anchor",binding)
    observation=load_receipt(root,index,observation_id)
    review=load_receipt(root,index,review_id)
    if (observation.get("binding")!=binding or observation.get("state")!="ORIGINAL_PROCESS_EXITED" or
        review.get("binding")!=binding or review.get("observation_id")!=observation_id or
        review.get("decision")!="APPROVE_RECONCILIATION_CANDIDATE" or review.get("transition_valid") is not True):
        return out
    observer,reviewer=observation.get("observer_worker"),review.get("reviewer_worker")
    if not all(isinstance(v,str) and v.strip() for v in (observer,reviewer)) or observer==reviewer:
        return out
    require_verified(authority,"reservation_owner_observation",observation)
    require_verified(authority,"reservation_independent_review",review)
    again=inspect_reservation(journal,expected_metadata_sha256=expected_metadata_sha256)
    if again.get("journal_sha256")!=out["journal_sha256"] or again.get("metadata_anchor_match") is not True:
        return out
    out["candidate"]="RELEASE_CANDIDATE_ONLY"
    out["owner_state"]="EXIT_ATTESTED_BY_CALLER"
    out["transition_valid"]="ATTESTED_BY_CALLER"
    return out
