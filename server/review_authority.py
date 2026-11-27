"""Explicit host trust boundary for the opt-in review and dispatch contracts.

A digest is not a signature. Only the trusted host may construct this
context from an independently approved immutable plan/index and verifier.
Tests use synthetic verifiers. No production issuer is installed here.
"""
from dataclasses import dataclass
import hashlib
import json
from typing import Callable


def content_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),
                                     ensure_ascii=False,allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReviewAuthority:
    plan_sha256: str
    index_sha256: str
    verify: Callable


def require_authority(plan,index,authority):
    if not isinstance(authority,ReviewAuthority):
        raise ValueError("independently approved plan and index authority required")
    scope={"task_id":plan["task_id"],"plan_sha256":content_digest(plan),
           "index_sha256":content_digest(index)}
    if (authority.plan_sha256!=scope["plan_sha256"] or
            authority.index_sha256!=scope["index_sha256"]):
        raise ValueError("approved plan or index digest mismatch")
    if authority.verify("approved_context",scope) is not True:
        raise ValueError("trusted approval source rejected")
    return scope["plan_sha256"]


def require_verified(authority,kind,payload):
    if authority.verify(kind,payload) is not True:
        raise ValueError("trusted "+kind+" verification rejected")
