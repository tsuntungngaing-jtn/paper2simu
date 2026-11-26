import json
import subprocess
import sys
from pathlib import Path

from server import historical_ledger
from server.coordination import Coordinator, initialize
from test_historical_evidence import build_packet


def test_history_observation_through_recovery_entrypoint(tmp_path, monkeypatch):
    output = tmp_path / "outputs"
    output.mkdir()
    packet, manifest, trust, _ = build_packet(output)
    trust = trust.rename(tmp_path / "authority.json")
    database = tmp_path / "coord.sqlite3"
    initialize(database, "lab", [output])
    coordinator = Coordinator(database, "lab")
    historical_ledger.initialize(coordinator, trust)
    monkeypatch.setenv("PAPER2SIMU_COORDINATION_DB", str(database))
    monkeypatch.setenv("PAPER2SIMU_RESOURCE_ID", "lab")
    monkeypatch.setenv("PAPER2SIMU_RECONCILIATION_TRUST", str(trust))
    script = Path(__file__).resolve().parents[1] / "scripts/recovery_memory.py"
    command = [sys.executable, str(script), "historical-status", str(manifest)]

    def observe():
        return json.loads(subprocess.check_output(command, cwd=tmp_path))

    assert observe() == {"historical_statement": None, "advisory_only": True}
    historical_ledger.append(coordinator, manifest, packet, trust)
    assert observe() == {"historical_statement": packet["statement"], "advisory_only": True}
    assert coordinator.inspect() == []
