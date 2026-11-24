import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_portable_workflow import check_workflow


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = {"id": "evidence-1", "sha256": "a" * 64}
LINEAGE = {
    "input_revision": "inputs-1",
    "geometry_id": "geom-1",
    "mesh_id": "mesh-1",
    "solution_id": "sol-1",
    "dataset_id": "data-1",
}


class PortableWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "examples" / "portable-workflow-template.json").read_text())
        self.record = copy.deepcopy(self.plan)
        self.record.update(record_kind="WORKFLOW_RECORD", task_ref=REFERENCE,
                           workflow_id="workflow-1", contract_revision="rev-1",
                           states={"baseline": LINEAGE})
        self.record["native_recipes"] = [{
            "recipe_id": "comsol-1",
            "solver": "COMSOL",
            "build": "6.4",
            "platform": "windows",
            "provider_namespace": "comsol",
            "stages": [{"stage_id": "read", "capability_ref": REFERENCE, "recipe_ref": REFERENCE}],
        }]

    def declare_pass(self, check_name, **fields):
        item = {
            "kind": check_name.upper(),
            "contract_revision": "rev-1",
            "recipe_id": "comsol-1",
            "run_id": "reopen-1",
            "operation_id": "op-1",
            "state_id": "baseline",
            "lineage": dict(LINEAGE),
            "artifact": REFERENCE,
            **fields,
        }
        self.record["checks"][check_name].update(
            status="PASS", criteria_ref=REFERENCE, observations="Fixture observation",
            native_evidence=[item],
        )

    def test_plan_reports_no_native_work(self):
        report = check_workflow(self.plan)
        self.assertEqual(report["contract_status"], "PASS")
        self.assertEqual(set(report["declared_checks"].values()), {"NOT_RUN"})
        self.assertEqual(report["native_evidence_verification"], "NOT_RUN")
        self.plan["checks"]["archive_restore"]["status"] = "PASS"
        self.assertEqual(check_workflow(self.plan)["contract_status"], "FAIL")

    def test_readback_leaves_fresh_and_scientific_checks_unperformed(self):
        check = "zero_iteration_readback"
        self.declare_pass(check, source_run_id="original-1", new_solves=0)
        report = check_workflow(self.record)
        self.assertEqual(report["contract_status"], "PASS")
        self.assertEqual(report["declared_checks"][check], "PASS")
        self.assertEqual(report["declared_checks"]["fresh_parametric_replay"], "NOT_RUN")
        self.assertEqual(report["declared_checks"]["scientific_validation"], "NOT_RUN")
        self.assertEqual(report["native_evidence_verification"], "NOT_RUN")
        self.record["checks"][check]["native_evidence"][0]["new_solves"] = 1
        self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")

    def test_stale_geometry_and_wrong_evidence_kind_fail(self):
        check = "fresh_parametric_replay"
        self.declare_pass(check, new_solves=1)
        self.record["budgets"]["max_solves"] = 1
        self.assertEqual(check_workflow(self.record)["contract_status"], "PASS")
        evidence = self.record["checks"][check]["native_evidence"][0]
        evidence["lineage"]["geometry_id"] = "old-geom"
        evidence["kind"] = "ZERO_ITERATION_READBACK"
        report = check_workflow(self.record)
        self.assertEqual(report["contract_status"], "FAIL")
        self.assertTrue(any("lineage" in error for error in report["errors"]))
        self.assertTrue(any("evidence kind" in error for error in report["errors"]))

    def test_fresh_replay_cannot_reuse_saved_run_or_overspend_budget(self):
        check = "fresh_parametric_replay"
        self.declare_pass("zero_iteration_readback", source_run_id="original", new_solves=0)
        self.declare_pass(check, run_id="original", new_solves=1)
        report = check_workflow(self.record)
        self.assertTrue(any("distinct run" in error for error in report["errors"]))
        self.assertTrue(any("exceed task budget" in error for error in report["errors"]))

    def test_missing_assets_and_mismatched_hash_are_visible(self):
        data = b"material properties"
        self.record["assets"] = [{
            "relative_path": "material.txt", "sha256": hashlib.sha256(data).hexdigest(),
            "required": True, "purpose": "properties",
        }]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = check_workflow(self.record, root)
            self.assertEqual(report["bundle_check"], "FAIL")
            self.assertEqual(report["assets"][0]["status"], "MISSING")
            asset = root / "material.txt"
            asset.write_bytes(data)
            self.assertEqual(check_workflow(self.record, root)["bundle_check"], "PASS")
            asset.write_bytes(b"changed")
            self.assertEqual(check_workflow(self.record, root)["bundle_check"], "FAIL")

    def test_nonportable_paths_are_rejected_without_loading_the_bundle(self):
        for path in ("/outside", "C:/outside", "nested/../outside", r"..\outside", "out.txt:stream"):
            with self.subTest(path=path):
                self.record["assets"] = [{
                    "relative_path": path, "sha256": "a" * 64, "required": True, "purpose": "data",
                }]
                self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")

    def test_link_outside_bundle_is_rejected(self):
        self.record["assets"] = [{
            "relative_path": "redirect/material.txt", "sha256": "a" * 64,
            "required": True, "purpose": "properties",
        }]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "bundle"
            root.mkdir()
            try:
                (root / "redirect").symlink_to(Path(directory), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlink unavailable")
            report = check_workflow(self.record, root)
            self.assertEqual(report["bundle_check"], "FAIL")
            self.assertIn("symlinks", report["assets"][0]["reason"])

    def test_legacy_without_desktop_check(self):
        del self.record["checks"]["desktop_editability"]
        self.assertEqual(check_workflow(self.record)["contract_status"], "PASS")

    def desktop_fixture(self):
        edit = dict(LINEAGE, input_revision="inputs-2", geometry_id="geom-2",
                    mesh_id="mesh-2", solution_id=None, dataset_id=None)
        self.record["states"]["edited"] = edit
        artifact = {"id": "edited", "sha256": "b" * 64}
        receipt = dict(actor="engineer", build="6.4", native_path="Geometry / width",
                       layers=["setup", "geometry", "mesh"], expected="new width",
                       actual="new width read back", source_artifact=REFERENCE,
                       edited_artifact=artifact, reopen_artifact=artifact,
                       source_state_id="baseline")
        self.record["checks"]["desktop_editability"]["promised_layers"] = ["setup", "geometry", "mesh"]
        self.declare_pass("desktop_editability", state_id="edited", lineage=edit,
                          artifact=artifact, desktop_receipt=receipt)
        return self.record["checks"]["desktop_editability"]["native_evidence"][0]

    def test_desktop_unsolved_copy(self):
        self.desktop_fixture()
        result = check_workflow(self.record)
        self.assertEqual(result["contract_status"], "PASS")
        self.assertEqual(result["native_evidence_verification"], "NOT_RUN")

    def test_desktop_missing_receipt_or_layer_fails(self):
        item = self.desktop_fixture()
        receipt = item.pop("desktop_receipt")
        self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")
        item["desktop_receipt"] = receipt
        receipt["layers"] = ["setup"]
        self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")

    def test_desktop_stale_or_wrong_kind_fails(self):
        item = self.desktop_fixture()
        item["lineage"]["solution_id"] = LINEAGE["solution_id"]
        self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")
        item["lineage"]["solution_id"] = None
        item["kind"] = "ARCHIVE_RESTORE"
        self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")

    def test_desktop_pass_without_evidence_fails(self):
        self.record["checks"]["desktop_editability"]["status"] = "PASS"
        self.assertEqual(check_workflow(self.record)["contract_status"], "FAIL")
