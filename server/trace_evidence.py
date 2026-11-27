"""Explicit consumption linkage checks, not event authentication or authority."""
import json
import re

HEX = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z0-9_.:-]{1,200}\Z")


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("missing or invalid identity")
    return value


def _hash(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError("invalid SHA-256")
    return value


def consumption_view(events):
    """Only an explicit linked ADOPTED event creates a used edge."""
    artifacts, seen, decisions, edges = {}, {}, {}, []
    for event in events:
        eid = _id(event.get("event_id"))
        encoded = json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if eid in seen:
            if seen[eid] != encoded:
                raise ValueError("conflicting event identity")
            continue
        seen[eid] = encoded
        kind = event.get("event")
        if kind not in ("artifact_observed", "consumer_disposition"):
            continue
        ctx = tuple(_id(event.get(k)) for k in ("task_id","case_id","plan_revision"))
        paper = event.get("paper_id")
        if paper is not None:
            _id(paper)
        if event.get("task_kind") not in ("paper", "infrastructure"):
            raise ValueError("missing task kind")
        if (event["task_kind"] == "paper") != (paper is not None):
            raise ValueError("invalid paper binding")
        ctx += (event["task_kind"], paper, event.get("thread_id"))
        digest = _hash(event.get("artifact_sha256"))
        _id(event.get("source_receipt_id"))
        if kind == "artifact_observed":
            artifacts[eid] = (ctx, digest, _id(event.get("producer_step")))
            continue
        producer = _id(event.get("producer_event_id"))
        consumer = _id(event.get("consumer_step"))
        if producer not in artifacts or artifacts[producer][:2] != (ctx, digest):
            raise ValueError("unmatched producer, scope or artifact")
        disposition = event.get("disposition")
        if disposition not in ("ADOPTED", "REJECTED", "HOLD", "UNKNOWN"):
            raise ValueError("invalid disposition")
        key = (producer, consumer, ctx)
        if key in decisions:
            raise ValueError("multiple dispositions: review revision history")
        decisions[key] = disposition
        if disposition == "ADOPTED":
            if consumer == artifacts[producer][2]:
                raise ValueError("not a downstream edge")
            if _hash(event.get("consumer_input_sha256")) != digest:
                raise ValueError("consumer input differs")
            edges.append({"producer_event_id": producer, "consumer_step": consumer,
                          "artifact_sha256": digest, "evidence_event_id": eid})
    return {"used": edges, "dispositions": len(decisions),
            "artifact_count": len(artifacts), "authenticity_verified": False,
            "native_execution_authorized": False}


def replay_consumption(events, root, approved_index):
    """Check exact normalized event against retained receipt projection.

    Index must be independently approved; does not authenticate its collector.
    Keep structural-only consumption_view separate for legacy offline tests.
    """
    from server.receipt_evidence import load_receipt
    events = list(events)
    verified = set()
    ignored = 0
    for event in events:
        if event.get("event") not in ("artifact_observed","consumer_disposition"):
            ignored += 1
            continue
        _id(event.get("thread_id"))
        receipt = load_receipt(root, approved_index, event.get("source_receipt_id"))
        if receipt.get("event_projection") != event:
            raise ValueError("event does not match retained receipt projection")
        verified.add(event["event_id"])
    result = consumption_view(events)
    result["receipt_bytes_verified"] = bool(verified) and ignored == 0
    result["verified_event_count"] = len(verified)
    result["unmapped_event_count"] = ignored
    result["input_event_count"] = len(events)
    result["coverage_status"] = ("NO_MAPPED_EVENTS" if not verified else
                                 "PARTIAL" if ignored else "MAPPED_BYTES_CHECKED")
    return result
