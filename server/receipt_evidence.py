"""Read retained, redacted receipt bytes against a separately approved index.

This verifies bytes and explicit event linkage, not host authenticity or ACL.
No private reasoning, credential capture, process launch, or native authority.
"""
import hashlib
import json
from pathlib import Path
import re

HEX = re.compile(r"[0-9a-f]{64}\Z")


def load_retained_bytes(root, index, receipt_id):
    root = Path(root).resolve(strict=True)
    record = index.get(receipt_id)
    if not isinstance(record,dict):
        raise ValueError("receipt absent from approved index")
    name, expected = record.get("path"), record.get("sha256")
    if not isinstance(name,str) or not isinstance(expected,str) or not HEX.fullmatch(expected):
        raise ValueError("invalid receipt index entry")
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("receipt outside evidence root")
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("receipt outside evidence root")
    data = resolved.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("receipt hash mismatch")
    return data


def load_receipt(root, index, receipt_id):
    value = json.loads(load_retained_bytes(root,index,receipt_id))
    if not isinstance(value,dict) or value.get("receipt_id") != receipt_id:
        raise ValueError("receipt identity mismatch")
    return value
