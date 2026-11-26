"""Read-only local transport diagnostic and live fingerprint comparison.

No credential handling, proxy reconfiguration, process restart, or native stop.
A metadata candidate is not execution authorization.
"""
from __future__ import annotations
import argparse
import http.client
import ipaddress
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

def loopback_probe(url,timeout=4):
    u=urlsplit(url)
    if u.scheme!="http" or u.username or u.password or u.query or u.fragment:
        raise ValueError("Use an uncredentialed registered loopback HTTP URL")
    host=u.hostname
    if host=="localhost": target="localhost"
    else:
        try: addr=ipaddress.ip_address(host or "")
        except ValueError: raise ValueError("Only localhost or loopback IP is accepted") from None
        if not addr.is_loopback: raise ValueError("Only loopback IP is accepted")
        target=str(addr)
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=10:
        raise ValueError("Invalid timeout")
    # No redirect, no proxy, no token, no MCP mutation. DNS for localhost is
    # constrained to a literal loopback endpoint; test the registered IP separately
    # if the service listens only on IPv6. Preserve the registered Host header.
    connection=http.client.HTTPConnection("127.0.0.1" if target=="localhost" else target,u.port or 80,timeout=timeout)
    try:
        connection.request("GET",u.path or "/",headers={"Host":u.netloc,"Connection":"close"})
        response=connection.getresponse()
        return {"status":"HTTP_RESPONSE","http_status":response.status,"mcp_verified":False,
                "route":"direct_loopback","localhost_probe_ipv4":target=="localhost"}
    except (OSError,http.client.HTTPException) as exc:
        return {"status":"DIRECT_UNREACHABLE","error_type":type(exc).__name__,"mcp_verified":False}
    finally: connection.close()

def diagnose(client_http_status,direct_http_status,proxy_log_match,tool_count,read_only_ok):
    if read_only_ok is True and type(tool_count) is int and tool_count>0:
        return "MCP_READONLY_REACHED"
    if client_http_status==502:
        if proxy_log_match is True and direct_http_status in (200,204,400,401,403,405,406):
            return "PROXY_MISROUTE_EVIDENCE"
        return "HTTP_502_CAUSE_UNCONFIRMED"
    if tool_count==0 or read_only_ok is not True: return "MCP_NOT_VERIFIED"
    return "TRANSPORT_UNVERIFIED"

def compare_live(expected,receipt,now=None):
    """Caller provides actual live tool results; paths and identity must match exactly."""
    now=time.time() if now is None else now
    reasons=[]
    def valid_time(v): return type(v) in (float,int) and math.isfinite(v)
    stamp=receipt.get("observed_at_unix")
    ttl=expected.get("max_age_seconds",60)
    if not valid_time(now) or not valid_time(stamp) or not valid_time(ttl) or not 0<ttl<=300 or not 0<=now-stamp<=ttl:
        reasons.append("STALE_OR_INVALID_OBSERVATION")
    q=receipt.get("queue") or {};c=receipt.get("capabilities_response") or {}
    if not isinstance(q,dict) or not isinstance(c,dict): return {"status":"HOLD","reasons":["INVALID_RESPONSE"]}
    if receipt.get("read_only_ok") is not True or type(receipt.get("tool_count")) is not int or receipt["tool_count"]<=0 or q.get("success") is not True:
        reasons.append("MCP_NOT_VERIFIED")
    for k in ("paper2simu_version","runtime_root","python_executable","output_root","runtime_source_sha256"):
        v=expected.get(k)
        if not isinstance(v,str) or not v or q.get(k)!=v or c.get(k)!=v:
            reasons.append("FINGERPRINT_MISMATCH:"+k)
    if not re.fullmatch(r"[0-9a-f]{64}",str(q.get("runtime_source_sha256",""))): reasons.append("INVALID_SOURCE_HASH")
    runtime_id=q.get("runtime_id")
    if not isinstance(runtime_id,str) or not runtime_id or c.get("runtime_id")!=runtime_id or (expected.get("runtime_id") and expected["runtime_id"]!=runtime_id):
        reasons.append("RUNTIME_ID_CHANGED_OR_UNKNOWN")
    if q.get("journal_errors")!=[] or q.get("recovery_pending")!=[]:
        reasons.append("UNRESOLVED_JOURNAL")
    if q.get("active_jobs")!=[]: reasons.append("ACTIVE_OR_UNKNOWN_QUEUE")
    if (q.get("submission_budget") or {}).get("can_submit") is not True: reasons.append("SUBMISSION_BUDGET_BLOCKED")
    if receipt.get("native_identity_verified") is not True or not receipt.get("native_evidence_ref"):
        reasons.append("NATIVE_IDENTITY_UNVERIFIED")
    if receipt.get("original_operation_id"):
        j=receipt.get("original_job") or {}
        if j.get("success") is not True or j.get("operation_id")!=receipt["original_operation_id"] or j.get("status") not in ("completed","failed","cancelled") or not j.get("job_id"):
            reasons.append("ORIGINAL_OPERATION_UNRESOLVED")
    if expected.get("require_hard_deadline") is not False:
        cap=(c.get("capabilities") or {}).get("deadline_enforcement") or {}
        if cap.get("state")!="supported" or cap.get("run_mode")!="isolated" or not receipt.get("native_deadline_test_ref"):
            reasons.append("HARD_DEADLINE_UNSUPPORTED")
    return {"status":"HOLD" if reasons else "METADATA_CANDIDATE","reasons":reasons,"native_authorization":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("loopback");s.add_argument("url")
    s=sub.add_parser("compare");s.add_argument("expected",type=Path);s.add_argument("receipt",type=Path)
    a=p.parse_args()
    result=loopback_probe(a.url) if a.cmd=="loopback" else compare_live(json.loads(a.expected.read_text(encoding="utf-8")),json.loads(a.receipt.read_text(encoding="utf-8")))
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
