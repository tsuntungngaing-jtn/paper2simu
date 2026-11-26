"""Preserve registered entrypoints and honest capability reporting across upgrades."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from server.runtime import Runtime
from server import __version__

ROOT=Path(__file__).resolve().parents[1]

class CapabilityContractTests(unittest.TestCase):
    def test_contract_paths_and_registration(self):
        contract=json.loads((ROOT/"benchmarks/runtime-capability-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["version"],__version__)
        for p in contract["required_modules"]:
            self.assertTrue((ROOT/p).is_file(),p)
        tree=ast.parse((ROOT/"server/main.py").read_text(encoding="utf-8-sig"))
        registered={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                    and any(isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=="tool" for d in n.decorator_list)}
        self.assertTrue(set(contract["required_tools"])<=registered)
        for cap in contract["capabilities"]:
            if cap["test"]: self.assertTrue((ROOT/cap["test"]).is_file(),cap["id"])
    def test_shared_runtime_never_claims_hard_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            rt=Runtime(output_root=Path(tmp))
            try:
                cap=rt.execution_capabilities()
                self.assertEqual(cap["historical_resource_reconciliation"]["state"], "implemented_offline")
                self.assertEqual(cap["running_stop"]["state"],"unsupported")
                self.assertEqual(cap["deadline_enforcement"]["state"],"unsupported")
                self.assertEqual(rt.submit_study(None,None,require_hard_deadline=True)["error"],"HARD_DEADLINE_UNSUPPORTED")
                self.assertEqual(rt.queue_status()["active_jobs"],[])
            finally: rt.executor.shutdown()
if __name__=="__main__": unittest.main()
