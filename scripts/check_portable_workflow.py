"""Check declarations and optional bundle bytes without executing recipes or solvers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path, PureWindowsPath

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "portable-workflow.schema.json"
SAVED_CHECK = "zero_iteration_readback"
FRESH_CHECK = "fresh_parametric_replay"


def check_workflow(record: dict, bundle_root: Path | None = None) -> dict:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    errors = [
        f"{error.json_path}: {error.message}"
        for error in sorted(validator.iter_errors(record), key=lambda error: error.json_path)
    ]
    schema_valid = not errors
    assets = []
    if schema_valid:
        _check_evidence(record, errors)
        assets = _check_assets(record["assets"], bundle_root)
        for asset in assets:
            if asset.get("invalid_path"):
                errors.append(f"assets/{asset['relative_path']}: {asset['reason']}")
    asset_failure = any(
        result["status"] == "FAIL" or
        (result["required"] and result["status"] == "MISSING")
        for result in assets
    )
    return {
        "contract_status": "FAIL" if errors else "PASS",
        "errors": errors,
        "bundle_check": ("NOT_RUN" if bundle_root is None or not schema_valid
                         else "FAIL" if asset_failure else "PASS"),
        "assets": assets,
        "declared_checks": {key: check["status"] for key, check in record["checks"].items()}
        if not errors else None,
        "native_evidence_verification": "NOT_RUN",
    }


def _check_evidence(record: dict, errors: list[str]) -> None:
    plan = record["record_kind"] == "PLAN_TEMPLATE"
    if not plan:
        for key in ("workflow_id", "contract_revision", "task_ref"):
            if record[key] is None:
                errors.append(f"{key}: required for a workflow record")

    recipes = set()
    for recipe in record["native_recipes"]:
        recipe_id = recipe["recipe_id"]
        if recipe_id in recipes:
            errors.append(f"native_recipes: duplicate recipe_id {recipe_id}")
        recipes.add(recipe_id)
        prior_stages = set()
        for stage in recipe["stages"]:
            stage_id = stage["stage_id"]
            if stage_id in prior_stages or set(stage.get("depends_on", ())) - prior_stages:
                errors.append(f"{recipe_id}/{stage_id}: require unique stages in dependency order")
            prior_stages.add(stage_id)

    checks = record["checks"]
    saved_runs = {
        item.get("source_run_id")
        for item in checks[SAVED_CHECK]["native_evidence"]
    }
    fresh_operations = {}
    for check_name, check in checks.items():
        status, evidence = check["status"], check["native_evidence"]
        if plan or status in {"NOT_RUN", "NOT_APPLICABLE"}:
            if (plan and status != "NOT_RUN") or evidence:
                errors.append(f"{check_name}: unperformed checks cannot declare native evidence or outcomes")
        if status == "PASS" and (not check["criteria_ref"] or not check["observations"] or not evidence):
            errors.append(f"{check_name}: PASS requires criteria, observations and native evidence")
        if status in {"BLOCKED", "FAIL", "NOT_APPLICABLE"} and not check["observations"]:
            errors.append(f"{check_name}: record a reason or observation")
        if check_name == "scientific_validation" and status == "PASS" and not record["qoi_contract_ref"]:
            errors.append(f"{check_name}: PASS requires a frozen QoI contract reference")
        if check_name == "desktop_editability" and status == "PASS":
            covered = set()
            for item in evidence:
                receipt = item.get("desktop_receipt")
                if not receipt:
                    errors.append("desktop_editability: PASS requires desktop receipt")
                    continue
                covered.update(receipt["layers"])
                source = record["states"].get(receipt["source_state_id"])
                edited = item["lineage"]
                if not source or receipt["source_state_id"] == item["state_id"]:
                    errors.append("desktop_editability: distinct source and edited states required")
                elif source["input_revision"] == edited["input_revision"]:
                    errors.append("desktop_editability: input revision must change")
                if source and "geometry" in receipt["layers"] and source["geometry_id"] == edited["geometry_id"]:
                    errors.append("desktop_editability: geometry identity must change")
                if "mesh" in receipt["layers"] and (not edited["mesh_id"] or (source and source["mesh_id"] == edited["mesh_id"])):
                    errors.append("desktop_editability: rebuilt mesh identity required")
                if source and any(edited[k] is not None and edited[k] == source[k] for k in ("solution_id", "dataset_id")):
                    errors.append("desktop_editability: stale saved solution or dataset")
                if receipt["source_artifact"]["sha256"] == receipt["edited_artifact"]["sha256"]:
                    errors.append("desktop_editability: edited copy must differ from source")
                if receipt["edited_artifact"]["sha256"] != item["artifact"]["sha256"]:
                    errors.append("desktop_editability: artifact must identify edited copy")
                recipe = next((r for r in record["native_recipes"] if r["recipe_id"] == item["recipe_id"]), None)
                if recipe and receipt["build"] != recipe["build"]:
                    errors.append("desktop_editability: receipt build differs from recipe")
            if set(check["promised_layers"]) - covered:
                errors.append("desktop_editability: promised layers lack receipt evidence")
        for item in evidence:
            if item["kind"] != check_name.upper():
                errors.append(f"{check_name}: incompatible native evidence kind {item['kind']}")
            if item["recipe_id"] not in recipes:
                errors.append(f"{check_name}: unknown recipe {item['recipe_id']}")
            if item["contract_revision"] != record["contract_revision"]:
                errors.append(f"{check_name}: outdated workflow contract revision")
            if record["states"].get(item["state_id"]) != item["lineage"]:
                errors.append(f"{check_name}: missing state or mismatched input/geometry/mesh/solution/dataset lineage")
            if status == "PASS" and check_name not in {"archive_restore", "desktop_editability"}:
                if any(item["lineage"][key] is None for key in ("mesh_id", "solution_id", "dataset_id")):
                    errors.append(f"{check_name}: PASS requires mesh, solution and dataset identities")
            if check_name == SAVED_CHECK and (item.get("new_solves") != 0 or not item.get("source_run_id")):
                errors.append(f"{check_name}: evidence requires zero new solves and the source run")
            if check_name == FRESH_CHECK:
                operation = (item["run_id"], item.get("new_solves", 0))
                prior = fresh_operations.setdefault(item["operation_id"], operation)
                if operation != prior:
                    errors.append(f"{check_name}: inconsistent evidence for operation {item['operation_id']}")
                if status == "PASS" and (
                    operation[1] < 1 or item["run_id"] == item.get("source_run_id") or item["run_id"] in saved_runs
                ):
                    errors.append(f"{check_name}: PASS requires a new solve with a distinct run")
    if checks[FRESH_CHECK]["status"] == "PASS" and sum(
        solves for _, solves in fresh_operations.values()
    ) > record["budgets"]["max_solves"]:
        errors.append(f"{FRESH_CHECK}: declared solves exceed task budget")


def _check_assets(assets: list[dict], root: Path | None) -> list[dict]:
    resolved_root = root.resolve(strict=True) if root is not None else None
    if resolved_root is not None and not resolved_root.is_dir():
        raise ValueError("bundle root must be a directory")
    results = []
    seen = set()
    for asset in assets:
        name = asset["relative_path"]
        result = {"relative_path": name, "required": asset["required"], "status": "NOT_RUN"}
        parts = name.split("/")
        try:
            if any(
                part in {"", ".", ".."} or part.endswith((" ", "."))
                or re.search(r'[\\\\:*?"<>|\x00-\x1f]', part) or PureWindowsPath(part).is_reserved()
                for part in parts
            ):
                result["invalid_path"] = True
                raise ValueError("expected a portable relative path without traversal")
            path_key = name.casefold()
            if path_key in seen:
                result["invalid_path"] = True
                raise ValueError("duplicate portable asset path")
            seen.add(path_key)
            if resolved_root is not None:
                path = resolved_root
                for part in parts:
                    path = path / part
                    info = path.lstat()
                    reparse = getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                    if stat.S_ISLNK(info.st_mode) or reparse:
                        raise ValueError("symlinks and junctions are not accepted")
                if not path.is_file() or not path.resolve().is_relative_to(resolved_root):
                    raise ValueError("expected a regular file under the bundle root")
                digest = hashlib.sha256()
                with path.open("rb") as data:
                    for block in iter(lambda: data.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != asset["sha256"]:
                    raise ValueError("SHA-256 does not match")
                result["status"] = "PASS"
        except FileNotFoundError:
            result.update(status="MISSING", reason="bundle asset is missing")
        except (OSError, ValueError) as error:
            result.update(status="FAIL", reason=str(error))
        results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--bundle-root", type=Path)
    args = parser.parse_args()
    try:
        report = check_workflow(json.loads(args.record.read_text(encoding="utf-8")), args.bundle_root)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["contract_status"] == "FAIL" or report["bundle_check"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
