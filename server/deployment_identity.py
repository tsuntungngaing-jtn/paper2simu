"""Compare declared component bytes with independently approved inventory."""
import hashlib
from pathlib import Path
import re

REQUIRED = {"skill", "runtime", "roles", "prompt", "provider", "adapter", "schema"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def verify(manifest, root, observed_commit):
    """Never grants execution. Expected inventory must be independently approved."""
    root = Path(root).resolve(strict=True)
    if manifest.get("display_version") != "0.6.3":
        raise ValueError("wrong version")
    expected = manifest.get("commit")
    if not isinstance(expected,str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("invalid commit")
    if observed_commit != expected:
        return {"status":"COMMIT_MISMATCH", "native_execution_authorized":False}
    groups = manifest.get("groups")
    if not isinstance(groups, dict) or set(groups) != REQUIRED:
        raise ValueError("incomplete inventory")
    mismatches = []
    for group, entries in groups.items():
        if not isinstance(entries, dict) or not entries:
            raise ValueError("empty inventory")
        for name, expected_hash in entries.items():
            p = Path(name)
            if p.is_absolute() or ".." in p.parts or not isinstance(expected_hash,str) or not HEX.fullmatch(expected_hash):
                raise ValueError("invalid path or hash")
            try:
                full = (root / p).resolve(strict=True)
                if not full.is_relative_to(root) or not full.is_file():
                    raise ValueError("outside deployment root")
                actual = hashlib.sha256(full.read_bytes()).hexdigest()
            except OSError:
                actual = None
            if actual != expected_hash:
                mismatches.append({"group":group,"path":name})
    return {"status":"MISMATCH" if mismatches else "DECLARED_FILES_MATCH",
            "mismatches":mismatches,"native_execution_authorized":False}
