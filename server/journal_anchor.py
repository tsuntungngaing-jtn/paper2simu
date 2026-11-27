"""Externally approved exact journal checkpoints for cooperating local writers.

A checkpoint is not self-authenticating. The trusted caller must obtain it
from an independent monotonically advancing source, not the journal under
test. No issuer, durable external checkpoint store or production ACL here.
"""
from dataclasses import dataclass, asdict
import hashlib
from server.review_authority import require_verified


@dataclass(frozen=True)
class JournalAnchor:
    task_id: str
    genesis_sha256: str
    journal_sha256: str
    sequence: int
    file_identity: tuple


def require_anchor(anchor,*,task_id,genesis_sha256,raw,events,identity,authority):
    if not isinstance(anchor,JournalAnchor) or authority is None:
        raise ValueError("independent journal checkpoint required")
    expected=JournalAnchor(task_id,genesis_sha256,hashlib.sha256(raw).hexdigest(),
                           len(events),tuple(identity))
    if anchor!=expected:
        raise ValueError("journal checkpoint/genesis mismatch")
    # The external verifier must reject old checkpoints even if they match
    # a truncated file. It must serialize issuance with accepted commits.
    require_verified(authority,"journal_checkpoint",asdict(anchor))
    return True
