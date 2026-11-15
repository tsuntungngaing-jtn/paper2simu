"""Local operator grants for the submission window of a single MCP process."""
from __future__ import annotations

import getpass
import json
from pathlib import Path
import re
import time
from uuid import uuid4


def authorize_renewal(output_root: Path, runtime_id: str, reason: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", runtime_id):
        raise ValueError("Copy the runtime_id from comsol_queue_status.")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValueError("Provide a renewal reason of 1 to 500 characters.")

    directory = output_root / "submission-window-grants" / runtime_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid4().hex}.json"
    record = {"runtime_id": runtime_id, "operator": getpass.getuser(), "reason": reason,
              "authorized_at_unix": time.time(), "authorized_at_monotonic": time.monotonic()}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return {"success": True, "runtime_id": runtime_id, "grant_path": str(path),
            "next_step": "Confirm the grant and remaining budget via comsol_queue_status."}


def latest_renewal(output_root: Path, runtime_id: str, started_at: float, now: float) -> tuple[float, str | None]:
    # Python 3.10+ shares the monotonic clock across processes on the same host.
    latest, grant = started_at, None
    for path in (output_root / "submission-window-grants" / runtime_id).glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            authorized_at = record["authorized_at_monotonic"]
            if record["runtime_id"] == runtime_id and latest < authorized_at <= now:
                latest, grant = authorized_at, path.stem
        except (OSError, ValueError, KeyError, TypeError):
            continue  # A damaged grant cannot extend the window.
    return latest, grant
