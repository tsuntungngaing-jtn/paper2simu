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


def inspect_reservation(journal):
    """Compare actual bytes against retained reservation; no liveness inference.

    Metadata may be absent, incomplete or caller-controlled. Even matching
    bytes are not proof of a terminated worker or authorized lock release.
    """
    from server.readonly_dispatch import _file_identity
    from server.review_authority import content_digest
    path=Path(journal).resolve(strict=True)
    lock=path.with_name(path.name+".writer-reservation")
    out={"status":"NO_RESERVATION","owner_state":"UNKNOWN","release_authorized":False,
         "native_execution_authorized":False,"journal_outcome":"UNKNOWN"}
    if not lock.exists() and not lock.is_symlink():
        return out
    out["status"]="UNRESOLVED"
    try:
        if lock.is_symlink() or not lock.is_dir():
            raise ValueError("invalid reservation path")
        meta=lock/"reservation.json"
        if meta.is_symlink():
            raise ValueError("invalid metadata path")
        m=json.loads(meta.read_bytes())
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
            if len(rows)==1 and content_digest(json.loads(rows[0]))==m.get("event_sha256"):
                out["journal_outcome"]="INTENDED_EVENT_BYTES_MATCH"
            else:
                out["journal_outcome"]="UNEXPECTED_TAIL"
        out["journal_sha256"]=hashlib.sha256(raw).hexdigest()
        out["metadata_sha256"]=content_digest(m)
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        out["diagnostic"]=str(exc)
    return out
