"""Read-only verification of scope-limited historical reconciliation evidence."""
import base64
import hashlib
import json
import math
import re
from pathlib import Path
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _keys(value, names):
    _require(isinstance(value, dict) and set(value) == set(names.split()), "unexpected or missing fields")


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _file(ref):
    _keys(ref, "path sha256")
    p = Path(ref["path"])
    _require(p.is_absolute() and str(p.resolve(strict=True)) == ref["path"], "canonical evidence path required")
    data = p.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == ref["sha256"], "artifact hash mismatch")
    return data


def _signer(record, role, trust, statement, review=None):
    _keys(record, "principal signed_at signature")
    identity = record["principal"]
    entry = trust["principals"][identity]
    _keys(entry, "role public_key")
    _require(isinstance(identity, str) and identity.strip() and entry["role"] == role, "untrusted role")
    _require(_number(record["signed_at"]) and record["signed_at"] <= time.time(), "invalid signature time")
    body = dict(protocol="paper2simu-reconciliation-v1", role=role, statement=statement,
                principal=identity, signed_at=record["signed_at"])
    if review is not None:
        body["review"] = review
    public = base64.b64decode(entry["public_key"], validate=True)
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(record["signature"], validate=True), canonical(body))
    return public


def verify(packet, manifest_path, resource_id, trust_path):
    """Return the verified statement or raise ValueError. No state mutation."""
    try:
        return _verify(packet, manifest_path, resource_id, trust_path)
    except (OSError, KeyError, TypeError, OverflowError, InvalidSignature, ET.ParseError) as exc:
        raise ValueError("historical evidence could not be verified") from exc


def _boot_time(raw):
    # Windows event XML has a UTC SystemTime with up to seven fractional digits.
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})", raw)
    _require(match is not None, "invalid Windows SystemTime")
    whole, fraction, offset = match.groups()
    second = datetime.fromisoformat(whole + offset.replace("Z", "+00:00")).timestamp()
    return second + int((fraction or "").ljust(7, "0")) / 10_000_000


def _check_execution_times(manifest, boot_time):
    times = [manifest["submitted_at"]]
    for key in ("started_at", "executing_at", "completed_at", "finished_at", "native_started_at",
                "native_stopped_at", "solve_started_at", "execution_started_at"):
        for name in (key, key + "_unix"):
            if manifest.get(name) is not None:
                times.append(manifest[name])
    # Runtime._progress persists original worker events in this array. Polls and
    # in-memory historical journal recovery do not append worker events.
    events = manifest.get("events", [])
    _require(isinstance(events, list), "invalid worker event list")
    for event in events:
        _require(isinstance(event, dict) and "time" in event, "unknown worker event format")
        times.append(event["time"])
    _require(all(_number(t) and t < boot_time for t in times),
             "boot must follow all original execution timestamps")


def _verify(packet, manifest_path, resource_id, trust_path):
    _keys(packet, "statement review approval")
    s = packet["statement"]
    _keys(s, "job_id operation_id manifest_path manifest_sha256 host_id resource_id event_at "
             "historical_status process_lifecycle native_result resource_scope scientific_status "
             "historical_budget evidence")
    trust = json.loads(Path(trust_path).read_bytes())
    _keys(trust, "host_id resource_id principals")
    _require(s["host_id"] == trust["host_id"] == socket.gethostname().casefold(), "host mismatch")
    _require(s["resource_id"] == trust["resource_id"] == resource_id, "domain mismatch")
    p = Path(manifest_path).resolve(strict=True)
    _require(str(p) == s["manifest_path"] and p.stem == s["job_id"], "manifest identity mismatch")
    manifest = json.loads(_file({"path": str(p), "sha256": s["manifest_sha256"]}))
    _require(manifest["job_id"] == s["job_id"] and manifest.get("operation_id") == s["operation_id"]
             and manifest["status"] == s["historical_status"], "manifest fields changed")
    _require(s["process_lifecycle"] == "LOCAL_PROCESS_ENDED_BY_BOOT_BOUNDARY"
             and s["native_result"] == "LOST_UNVERIFIED"
             and s["resource_scope"] == "CLEAR_THIS_HISTORICAL_BLOCK_ONLY"
             and s["scientific_status"] == "UNVERIFIED" and s["historical_budget"] == "UNCHANGED",
             "unsupported conclusion or scope")
    _keys(s["evidence"], "origin boot")
    origin = json.loads(_file(s["evidence"]["origin"]))
    _keys(origin, "job_id operation_id model_name study_name host_id resource_id submitted_at execution_site source_artifacts")
    sources = origin["source_artifacts"]
    _require(isinstance(sources, list) and sources, "original execution-site records required")
    for source in sources:
        _require(_file(source), "empty original execution-site record")
    for key in ("job_id", "operation_id", "host_id", "resource_id"):
        _require(origin[key] == s[key], "origin identity mismatch")
    for key in ("model_name", "study_name", "submitted_at"):
        _require(origin[key] == manifest[key], "origin does not identify original job")
    _require(origin["execution_site"] == "LOCAL_ONLY", "remote or mixed execution is unsupported")
    for key in ("host_id", "resource_id", "execution_site"):
        if key in manifest:
            _require(manifest[key] == origin[key], "manifest conflicts with origin")
    boot = ET.fromstring(_file(s["evidence"]["boot"]))
    ns = "{http://schemas.microsoft.com/win/2004/08/events/event}"
    sys = boot.find(ns+"System")
    _require(boot.tag == ns+"Event" and sys is not None, "Windows event XML required")
    provider = sys.find(ns+"Provider")
    stamp = sys.find(ns+"TimeCreated")
    _require(provider is not None and provider.get("Name") == "Microsoft-Windows-Kernel-General"
             and sys.findtext(ns+"EventID") == "12" and sys.findtext(ns+"Channel") == "System"
             and (sys.findtext(ns+"Computer") or "").casefold() == s["host_id"]
             and stamp is not None, "wrong boot event")
    _require(_number(s["event_at"]) and _boot_time(stamp.attrib["SystemTime"]) == s["event_at"],
             "boot chronology invalid")
    _check_execution_times(manifest, s["event_at"])
    review, approval = packet["review"], packet["approval"]
    reviewer_key = _signer(review, "independent_reviewer", trust, s)
    admin_key = _signer(approval, "resource_admin", trust, s, review)
    _require(review["principal"] != approval["principal"] and reviewer_key != admin_key,
             "review and approval require independent principals and keys")
    _require(s["event_at"] <= review["signed_at"] <= approval["signed_at"], "approval chronology invalid")
    return s
